#!/usr/bin/env python3
"""Mode4 v4.1 deterministic EOD signal research + forward paper simulation.
Does NOT record user executions, and never claims historical fills are broker fills.
"""
import json, math, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

P=Path("data/mode4_latest.json")
OUT=Path("data/mode4_v41_engine.json")
STATE=Path("data/mode4_v41_paper.json")
FEE=0.001425
TAX_STOCK=.003
TAX_ETF=.001
SLIP=.0005
CASH_START=100000.
RISK=400.
ETF={"0050","006208","0056","00878","00919"}
A=["0050","2881","2317","2382","2303"]
B=["2330","2308","2891","2357","3711"]
def signal(bars):
    if len(bars)<65: return []
    close=[b["close"] for b in bars]
    vol=[b["volume"] for b in bars]
    if not all(isinstance(x,(float,int)) and x>0 for x in close[-65:]+vol[-20:]):return []
    c=close[-1]; ma5=sum(close[-5:])/5; ma20=sum(close[-20:])/20
    prev_hi=max(b["high"] for b in bars[-21:-1])
    prev_low=min(b["low"] for b in bars[-21:-1])
    trs=[max(b["high"]-b["low"],abs(b["high"]-close[i-1]),abs(b["low"]-close[i-1])) for i,b in enumerate(bars) if i>0]
    atr=sum(trs[-14:])/14
    if atr<=0:return []
    vol_ratio=vol[-1]/(sum(vol[-20:])/20)
    results=[]
    # close-confirmed breakout; next-day limit order (no same-day fill)
    if c>prev_hi and vol_ratio>=1.2 and c>ma20:
        results.append(("BREAKOUT",c, max(c-1.5*atr,prev_low),c+2.2*atr,3))
    # pullback in rising short trend
    if ma5>ma20 and abs(c-ma5)<=.45*atr and c>ma20:
        results.append(("PULLBACK",c, c-1.4*atr,c+2*atr,4))
    # mean reversion: distance below 20d mean
    if c<ma20-1.5*atr and c>prev_low:
        results.append(("MEAN_REVERSION",c,c-1.2*atr,min(ma20,c+2*atr),3))
    return [(s,round(e,3),round(st,3),round(tp,3),days) for s,e,st,tp,days in results if st>0 and tp>e]
def costs(code,entry,exit_price,qty):
    tax=TAX_ETF if code in ETF else TAX_STOCK
    bval=entry*(1+SLIP)*qty; sval=exit_price*(1-SLIP)*qty
    return round(sval-bval-bval*FEE-sval*(FEE+tax),2)
def plan(code,bars,rule,cash):
    strategy,e,stop,tp,days=rule
    # next-session limit <= e; fill only when daily OPEN <= e, never on touch alone
    per_share=max(.01,e-stop)
    risk_one=per_share+(e+stop)*(FEE+SLIP)+stop*(TAX_ETF if code in ETF else TAX_STOCK)
    qty=int(min(cash/(e*(1+FEE+SLIP)),RISK/risk_one))
    if qty<1:return None
    loss=costs(code,e,stop,qty); win=costs(code,e,tp,qty)
    if loss>=0 or win<=0:return None
    return {"plan_id":f'{bars[-1]["date"]}-{code}-{strategy}',"symbol":code,"strategy":strategy,"signal_date":bars[-1]["date"],"entry_limit":e,"stop":stop,"target":tp,"max_hold_days":days,"shares":qty,"estimated_net_loss":loss,"estimated_net_win":win,"net_rr":round(win/abs(loss),3),"status":"RESEARCH_PENDING","execution_rule":"Next session open <= limit AND open > stop; fill at min(open, limit) with adverse slippage; otherwise unfilled; ambiguous daily bar treated conservatively."}

# A/B are SHADOW PAPER RESEARCH only, each with its own TWD100k baseline.
# A = low-entry on next open; B = require next day's close confirmation,
#     and only then enter on a subsequent open. Never fill retrospectively.
def ab_tick(code, price):
    if code in ETF: return 0.01  # indicative ETF rounding; exchange verification needed
    if price < 10: return .01
    if price < 50: return .05
    if price < 100: return .1
    if price < 500: return .5
    if price < 1000: return 1.
    return 5.

def ab_round(code, value, direction="down"):
    step=ab_tick(code,value)
    n=(math.ceil((value-1e-9)/step) if direction=="up" else math.floor((value+1e-9)/step))
    return round(n*step,2)

def ab_make_plan(original, version, entry=None, ready_date=None):
    code=original["symbol"]
    e=ab_round(code,entry if entry is not None else original["entry_limit"],"up")
    stop=ab_round(code,original["stop"],"down")
    target=ab_round(code,original["target"],"down")
    if not (stop>0 and stop<e<target):return None
    tax=TAX_ETF if code in ETF else TAX_STOCK
    risk_per_share=(e-stop)+(e+stop)*(FEE+SLIP)+stop*tax
    qty=int(min(CASH_START/(e*(1+FEE+SLIP)),RISK/risk_per_share))
    if qty<1:return None
    net_loss=costs(code,e,stop,qty)
    net_win=costs(code,e,target,qty)
    if net_loss >= 0 or net_win <= 0:return None
    return {
        "plan_id":original["plan_id"]+"-"+version,
        "pair_id":original["plan_id"],
        "version":version,
        "symbol":code,
        "strategy":"MEAN_REVERSION",
        "signal_date":original["signal_date"],
        "ready_date":ready_date or original["signal_date"],
        "entry_limit":e,"stop":stop,"target":target,
        "shares":qty,"max_hold_days":original["max_hold_days"],
        "estimated_net_loss":net_loss,"estimated_net_win":net_win,
        "net_rr":round(net_win/abs(net_loss),3),
        "status":"RESEARCH_BUY_CANDIDATE" if version=="A" else "CONFIRMED_RESEARCH_CANDIDATE",
        "source":"EOD completed OHLCV, unverified historical edge",
        "execution_rule":"Fill modeled only at next eligible session OPEN <= limit and OPEN > stop. No OHLC high-touch assumed filled."
    }

def ab_reversal(bar):
    rng=bar["high"]-bar["low"]
    if rng <= 0:return {"reversal_candle":False,"close_location":None}
    location=(bar["close"]-bar["low"])/rng
    wick=(min(bar["open"],bar["close"])-bar["low"])/rng
    return {"reversal_candle":location>=.55 and wick>=.2,
            "close_location":round(location,3)}

def ab_account(anchor_date):
    return {"cash":CASH_START,"position":None,"events":[],"daily_equity":[
        {"date":anchor_date,"cash":CASH_START,"position_market_value":0.0,"equity":CASH_START,
         "note":"Forward-only A/B baseline; not a historical execution"}],
        "pending":None,"unfilled_count":0,"realized_pnl":0.0}

def ab_close_position(account, date, px, reason, code):
    pos=account["position"]
    proceeds=px*(1-SLIP)*pos["shares"]
    fee=proceeds*(FEE+(TAX_ETF if code in ETF else TAX_STOCK))
    credit=proceeds-fee
    account["cash"]+=credit
    pnl=credit-pos["entry_debit"]
    account["realized_pnl"]=round(account["realized_pnl"]+pnl,2)
    account["events"].append({
        "event_id":pos["plan_id"]+"-"+date+"-MODELED_SELL",
        "date":date,"type":"MODELED_SELL","account":"PAPER_SHADOW_"+pos["version"],
        "symbol":code,"pair_id":pos["pair_id"],"shares":pos["shares"],
        "price":round(px*(1-SLIP),4),"reason":reason,
        "pnl":round(pnl,2),"evidence":"Conservative daily-OHLC modeled exit; not brokerage"})
    account["position"]=None

def ab_progress(account, version, date, prices):
    if date in {p["date"] for p in account["daily_equity"]}:return False
    plan=account["pending"]
    # Only OPEN fills, and only strictly after plan was ready. No same-bar lookahead.
    if plan and date>plan["ready_date"] and not account["position"]:
        item=prices.get(plan["symbol"])
        bar=item["ohlcv"][-1] if item else None
        if bar and bar["date"]==date and bar["open"]<=plan["entry_limit"] and bar["open"]>plan["stop"]:
            qty=plan["shares"];price=bar["open"]*(1+SLIP)
            debit=price*qty*(1+FEE)
            if debit<=account["cash"]:
                account["cash"]-=debit
                account["position"]={
                    "version":version,"symbol":plan["symbol"],"pair_id":plan["pair_id"],
                    "plan_id":plan["plan_id"],"shares":qty,"entry_date":date,
                    "entry_price":round(price,4),"entry_debit":debit,"days_held":0,
                    "stop":plan["stop"],"target":plan["target"],
                    "max_hold_days":plan["max_hold_days"]}
                account["events"].append({
                    "event_id":plan["plan_id"]+"-"+date+"-MODELED_BUY","date":date,
                    "type":"MODELED_BUY","account":"PAPER_SHADOW_"+version,
                    "symbol":plan["symbol"],"pair_id":plan["pair_id"],
                    "shares":qty,"price":round(price,4),
                    "evidence":"Modeled next-session OPEN fill with slippage; not brokerage"})
        else:account["unfilled_count"]+=1
        account["pending"]=None
    pos=account["position"]
    if pos:
        item=prices.get(pos["symbol"])
        bar=item["ohlcv"][-1] if item else None
        if bar and bar["date"]==date:
            # OPEN precedes daily LOW. Conservative same-day stop takes priority over target.
            if bar["low"]<=pos["stop"]:
                exit_px=min(bar["open"],pos["stop"]) if date>pos["entry_date"] else pos["stop"]
                ab_close_position(account,date,exit_px,"STOP_OR_ENTRY_DAY_STOP",pos["symbol"])
            else:
                if date>pos["entry_date"]:pos["days_held"]+=1
                # High touching target alone is insufficient evidence of fill.
                # At hold expiry, close exit is modeled; target is not silently awarded.
                if pos["days_held"]>=pos["max_hold_days"]:
                    ab_close_position(account,date,bar["close"],"TIME_EXIT_CLOSE",pos["symbol"])
    pos=account["position"];market_value=0.0
    if pos and pos["symbol"] in prices:
        bar=prices[pos["symbol"]]["ohlcv"][-1]
        if bar["date"]==date:
            market_value=pos["shares"]*bar["close"]
    # mark-to-market includes estimated future selling fee/tax/slippage
    tax=TAX_ETF if pos and pos["symbol"] in ETF else TAX_STOCK
    estimated_liquidation=market_value*(1-SLIP)*(1-FEE-tax) if pos else 0
    account["daily_equity"].append({
        "date":date,"cash":round(account["cash"],2),
        "position_market_value":round(market_value,2),
        "equity":round(account["cash"]+estimated_liquidation,2),
        "mark_basis":"estimated liquidation, incl. fees and slippage"})
    return True

def ab_metrics(account):
    curve=account["daily_equity"]
    peak=CASH_START;max_dd=0.
    for obs in curve:
        peak=max(peak,obs["equity"])
        max_dd=max(max_dd,1-obs["equity"]/peak)
    buys=sum(e["type"]=="MODELED_BUY" for e in account["events"])
    exits=sum(e["type"]=="MODELED_SELL" for e in account["events"])
    equity=curve[-1]["equity"]
    return {"equity":equity,"cash":round(account["cash"],2),
            "unrealized_or_open":bool(account["position"]),
            "net_pnl":round(equity-CASH_START,2),
            "return_pct":round(100*(equity/CASH_START-1),3),
            "realized_pnl":round(account["realized_pnl"],2),
            "modeled_buys":buys,"modeled_sells":exits,
            "unfilled_attempts":account["unfilled_count"],
            "max_drawdown_pct_observed":round(100*max_dd,3),
            "equity_as_of":curve[-1]["date"]}

def ab_research_and_simulate(snapshot, existing_state, existing_candidates):
    day=snapshot["latest_bar_date"];prices=snapshot["symbols"]
    anchor=(existing_state.get("daily_equity") or [{"date":day}])[-1]["date"]
    if "ab_shadow_accounts" not in existing_state:
        existing_state["ab_shadow_accounts"]={"A":ab_account(anchor),"B":ab_account(anchor)}
        existing_state["ab_waiting_confirmation"]=None
        existing_state["ab_started_after_date"]=anchor
    accounts=existing_state["ab_shadow_accounts"]
    possible=[]
    for base in existing_candidates:
        if base["strategy"]!="MEAN_REVERSION":continue
        bar=prices[base["symbol"]]["ohlcv"][-1]
        flag=ab_reversal(bar)
        item={**base,**flag,"signal_high":bar["high"],
              "signal_low":bar["low"],"user_label":"A 積極低接研究 / B 反彈確認研究"}
        possible.append(item)
    # Preserve comparability: same base signal, same stop/target, same risk budget.
    possible.sort(key=lambda p:(not p["reversal_candle"],-p["net_rr"],p["symbol"]))
    selected=possible[0] if possible else None
    new_date=day not in {x["date"] for x in accounts["A"]["daily_equity"]}
    if new_date:
        for version in ("A","B"):ab_progress(accounts[version],version,day,prices)
        prev=existing_state.get("ab_waiting_confirmation")
        b_plan=None
        if prev and prev["signal_date"]<day:
            bar=prices.get(prev["symbol"],{}).get("ohlcv",[None])[-1]
            if bar and bar["date"]==day and bar["close"]>prev["signal_high"] and bar["close"]>bar["open"]:
                # confirmation only known after this day's close.
                candidate_entry=bar["close"] # cap at confirmed close, never chase unbounded gaps
                b_plan=ab_make_plan(prev,"B",entry=candidate_entry,ready_date=day)
            existing_state["ab_waiting_confirmation"]=None
        if not accounts["B"]["position"]:accounts["B"]["pending"]=b_plan
        if selected:
            a_plan=ab_make_plan(selected,"A",ready_date=day)
            if not accounts["A"]["position"]:accounts["A"]["pending"]=a_plan
            if not accounts["B"]["position"] and existing_state["ab_waiting_confirmation"] is None:
                existing_state["ab_waiting_confirmation"]=selected
        elif not accounts["A"]["position"]:
            accounts["A"]["pending"]=None
    # If re-running an old day, no new orders may be backdated.
    existing_state["ab_enabled"]=True
    result={
      "experiment":"A=early low entry, B=next-day close confirmed then subsequent open; independent, paired research accounts",
      "anchor_date":existing_state["ab_started_after_date"],
      "candidate_pairs":len(possible),
      "top_pair":({
          "symbol":selected["symbol"],"pair_id":selected["plan_id"],
          "signal_date":selected["signal_date"],
          "reversal_candle":selected["reversal_candle"],
          "close_location":selected["close_location"],
          "A_next_session_plan":ab_make_plan(selected,"A",ready_date=day),
          "B_status":"AWAIT_NEXT_SESSION_CLOSE_CONFIRMATION",
          "B_confirmation":"Next day's CLOSE > signal-day HIGH and CLOSE > OPEN; if true, only subsequent session OPEN can model fill"
        } if selected else None),
      "account_A":ab_metrics(accounts["A"]),
      "account_B":ab_metrics(accounts["B"]),
      "comparison_warning":"Research only, no historical OOS edge; two separate 100k shadow accounts, do not sum them or mix with REAL / legacy paper.",
      "execution_assumptions":"Yahoo EOD open used to model fills; tick rounding approximate for ETFs; corporate actions, order book, odd lots and minimum brokerage fees not independently verified."
    }
    return result

def main():
    j=json.loads(P.read_text()); date=j["latest_bar_date"]; names=A+B+j["selected_C"]
    errors={}; candidates=[]
    for code in dict.fromkeys(names):
        item=j["symbols"].get(code)
        if not item:errors[code]="missing";continue
        bars=item["ohlcv"]
        dates=[b["date"] for b in bars]
        if len(bars)<65 or dates[-1]!=date or len(set(dates))!=len(dates) or dates!=sorted(dates):
            errors[code]="stale/nonunique/incomplete";continue
        # Known anomaly: previous snapshot skipped 2026-10-27 for ETFs.
        if code in ("0050","0056") and date=="2026-10-28" and "2026-10-27" not in dates:
            errors[code]="missing Oct-27 bar";continue
        for rule in signal(bars):
            p=plan(code,bars,rule,CASH_START)
            if p:candidates.append(p)
    candidates.sort(key=lambda p:(-p["net_rr"],p["symbol"],p["strategy"]))
    state={"schema":"mode4-v41-paper-v1","cash":CASH_START,"position":None,"events":[],"daily_equity":[],"pending":None}
    if STATE.exists():state=json.loads(STATE.read_text())
    ab_result=ab_research_and_simulate(j,state,candidates)
    # Freeze legacy single PAPER account when A/B shadow study begins;
    # do not double count its previous pending order.
    # Always process at most one once per market date, with previous-day pending plan.
    processed={x["date"] for x in state["daily_equity"]}
    if not state.get("ab_enabled") and date not in processed:
        prev=state.get("pending")
        if prev and prev["signal_date"]<date and prev["symbol"] in j["symbols"]:
            bar=j["symbols"][prev["symbol"]]["ohlcv"][-1]
            if state["position"] is None and bar["date"]==date:
                if bar["open"]<=prev["entry_limit"] and bar["open"]>prev["stop"]:
                    px=bar["open"]*(1+SLIP); qty=prev["shares"]
                    debit=px*qty*(1+FEE)
                    if debit<=state["cash"]:
                        state["cash"]-=debit
                        state["position"]={"symbol":prev["symbol"],"shares":qty,"entry_price":px,"entry_date":date,"stop":prev["stop"],"target":prev["target"],"max_hold_days":prev["max_hold_days"],"days_held":0,"plan_id":prev["plan_id"]}
                        state["events"].append({"event_id":prev["plan_id"]+"-BUY","date":date,"account":"PAPER","type":"MODELED_BUY","shares":qty,"price":round(px,4),"evidence":"Next-day OHLC open; assumed modeled fill, not real execution"})
        pos=state["position"]
        if pos and pos["symbol"] in j["symbols"]:
            bar=j["symbols"][pos["symbol"]]["ohlcv"][-1]
            if bar["date"]==date:
                # No same-day exit on entry date because OHLC sequence unknown
                if pos["entry_date"]<date:
                    pos["days_held"]+=1
                    reason=None; sell=None
                    if bar["low"]<=pos["stop"]:
                        reason="STOP_OR_GAP";sell=min(bar["open"],pos["stop"])
                    elif bar["high"]>=pos["target"]:
                        reason="TARGET_TOUCH_UNCERTAIN";sell=None # cannot confirm target limit fill via daily high
                    elif pos["days_held"]>=pos["max_hold_days"]:
                        reason="TIME_EXIT_CLOSE";sell=bar["close"]
                    if sell is not None:
                        gross=sell*(1-SLIP)*pos["shares"]
                        fee=gross*(FEE+(TAX_ETF if pos["symbol"] in ETF else TAX_STOCK))
                        state["cash"]+=gross-fee
                        state["events"].append({"event_id":pos["plan_id"]+"-SELL","date":date,"account":"PAPER","type":"MODELED_SELL","reason":reason,"shares":pos["shares"],"price":round(sell*(1-SLIP),4),"evidence":"OHLC conservative modeled exit; not broker execution"})
                        state["position"]=None
        cash=state["cash"];pos=state["position"];mv=0
        if pos and pos["symbol"] in j["symbols"]:mv=j["symbols"][pos["symbol"]]["ohlcv"][-1]["close"]*pos["shares"]
        state["daily_equity"].append({"date":date,"cash":round(cash,2),"position_market_value":round(mv,2),"equity":round(cash+mv,2)})
        # new pending plan cannot activate until the next date
        state["pending"]= candidates[0] if state["position"] is None and candidates else None
    OUT.parent.mkdir(parents=True,exist_ok=True)
    snapshot={"schema":"mode4-v41-research-v1","generated_at_taipei":datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),"latest_bar_date":date,"source_sha_note":"GitHub price snapshot; third-party Yahoo Finance; no broker validation","coverage":{"target_count":len(names),"processable":len(set(names))-len(errors),"excluded":errors},"strategy_candidates":candidates[:12],"top_pending_plan":state.get("pending"),"paper":{"cash":round(state["cash"],2),"position":state["position"],"events_count":len(state["events"]),"last_equity":state["daily_equity"][-1] if state["daily_equity"] else None},"validation":{"backtest":"NOT_IMPLEMENTED; historical edge not established","execution":"OHLC modeled fills only; not broker-confirmed","issues":["daily OHLC cannot establish intraday order sequence","target touch is not assumed filled","historical C selection must be point-in-time for backtesting"]}}
    snapshot["ab_comparison"]=ab_result
    snapshot["paper"]["legacy_only"]=True
    snapshot["paper"]["as_of_note"]="Legacy PAPER frozen at A/B start; use ab_comparison for ongoing PAPER results"
    OUT.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n")
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
    print("Mode4 v4.1",date,"processable",snapshot["coverage"],"candidates",len(candidates),"events",len(state["events"]))
if __name__=="__main__":main()
