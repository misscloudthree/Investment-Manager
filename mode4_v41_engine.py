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
    # Always process at most one once per market date, with previous-day pending plan.
    processed={x["date"] for x in state["daily_equity"]}
    if date not in processed:
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
    OUT.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n")
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
    print("Mode4 v4.1",date,"processable",snapshot["coverage"],"candidates",len(candidates),"events",len(state["events"]))
if __name__=="__main__":main()
