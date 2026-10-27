#!/usr/bin/env python3
"""Mode 4 minimal market data bridge. Python 3.11+. Public price data; no credentials.
Primary data: Yahoo Finance (yfinance). Fail closed on invalid/missing data.
"""
import json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

A=['0050','2881','2317','2382','2303']
B=['2330','2308','2891','2357','3711']
# Pre-committed C candidate *universe*, evaluated by identical objective rule.
# These are not guaranteed to be the five strongest stocks in Taiwan.
C_UNIVERSE=['006208','0056','00878','00919','2603','2618','2454','3037','2376','2324','2882','2886','5871','1301','1216']
ALL=list(dict.fromkeys(A+B+C_UNIVERSE))
TZ=ZoneInfo('Asia/Taipei')
OUTPUT=Path(os.getenv('MODE4_OUTPUT','data/mode4_latest.json'))

def f(v):
    try:
        x=float(v)
        return round(x, 5) if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def indicators(df):
    d=df.copy()
    c=d['close']; h=d['high']; l=d['low']; v=d['volume']
    tr=pd.concat([(h-l).abs(),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    d['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs=gain/loss.replace(0,float('nan')); d['rsi14']=100-100/(1+rs)
    low9=l.rolling(9).min(); high9=h.rolling(9).max()
    rsv=100*(c-low9)/(high9-low9).replace(0,float('nan'))
    d['kd_k']=rsv.ewm(alpha=1/3,adjust=False,min_periods=9).mean();d['kd_d']=d['kd_k'].ewm(alpha=1/3,adjust=False,min_periods=3).mean()
    for n in (5,20,60): d[f'ma{n}']=c.rolling(n).mean()
    d['volume_ma20']=v.rolling(20).mean()
    return d

def fetch(code):
    ticker=f'{code}.TW'
    raw=yf.download(ticker,period='8mo',interval='1d',auto_adjust=False,progress=False,threads=False)
    if raw is None or raw.empty: raise ValueError('no data')
    if isinstance(raw.columns,pd.MultiIndex):raw.columns=raw.columns.get_level_values(0)
    raw=raw.rename(columns=str.lower)
    need=['open','high','low','close','volume']
    if not all(k in raw.columns for k in need):raise ValueError('missing OHLCV columns')
    d=raw[need].copy();d.index=pd.to_datetime(d.index).tz_localize(None).normalize()
    d=d.sort_index();d=d[~d.index.duplicated(keep='last')].dropna(subset=need)
    d=d[(d['high']>=d['low'])&(d['high']>=d[['open','close']].max(axis=1))&(d['low']<=d[['open','close']].min(axis=1))&(d['volume']>0)&(d[need[:4]]>0).all(axis=1)]
    if len(d)<65:raise ValueError(f'only {len(d)} valid bars (<65)')
    d=indicators(d)
    latest=d.iloc[-1];bars=[]
    for ix,row in d.tail(90).iterrows():bars.append({'date':ix.strftime('%Y-%m-%d'),**{k:f(row[k]) for k in need}})
    keys=['ma5','ma20','ma60','atr14','rsi14','kd_k','kd_d','volume_ma20']
    obj={'code':code,'ticker':ticker,'source':'Yahoo Finance via yfinance (unofficial; verify against exchange before real orders)',
         'date':d.index[-1].strftime('%Y-%m-%d'),'bar_count':len(d),'ohlcv':bars,
         'indicators':{k:f(latest[k]) for k in keys},'recent_20d_high':f(d['high'].iloc[-21:-1].max()),
         'recent_20d_low':f(d['low'].iloc[-21:-1].min())}
    if any(v is None for v in obj['indicators'].values()):raise ValueError('incomplete indicators')
    return obj

def main():
    now=datetime.now(TZ)
    result={'schema':'mode4-ohlcv-v1','generated_at_taipei':now.isoformat(),'data_basis':'completed_daily_candles',
            'source_notice':'Yahoo Finance third-party EOD data; not live execution or a validated edge',
            'groups':{'A':A,'B':B,'C_rule':'Select top 5 eligible from predeclared C_UNIVERSE by 20d median traded value; requires 65+ daily bars. No post-hoc price-performance selection.','C_universe':C_UNIVERSE},'symbols':{},'errors':{},'selected_C':[]}
    for i,code in enumerate(ALL,1):
        try:
            s=fetch(code); result['symbols'][code]=s
            print(f'{i}/{len(ALL)} {code}: {s["date"]} ({s["bar_count"]} bars)',flush=True)
        except Exception as exc:
            result['errors'][code]=f'{type(exc).__name__}: {exc}';print(f'{code} failed: {exc}',file=sys.stderr,flush=True)
    # C liquidity rule uses 20d median NT$ turnover proxy: daily close * shares volume.
    candidates=[]
    for code in C_UNIVERSE:
        s=result['symbols'].get(code)
        if not s:continue
        b=s['ohlcv'][-20:]
        if len(b)<20:continue
        median=float(pd.Series([x['close']*x['volume'] for x in b]).median())
        if median>=50_000_000:candidates.append((median,code))
    result['selected_C']=[code for _,code in sorted(candidates,reverse=True)[:5]]
    # Critical fail-closed condition: don't overwrite existing good snapshot with no data.
    if not result['symbols']:
        print('FATAL: no symbols fetched; snapshot not overwritten',file=sys.stderr);sys.exit(2)
    dates=[x['date'] for x in result['symbols'].values()]
    result['latest_bar_date']=max(dates)
    result['date_counts']={date:dates.count(date) for date in sorted(set(dates))}
    result['coverage']={'A':sum(c in result['symbols'] for c in A),'B':sum(c in result['symbols'] for c in B),'C_selected':len(result['selected_C']),'all_fetched':len(result['symbols']),'all_attempted':len(ALL)}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',OUTPUT,'coverage',result['coverage'])

if __name__=='__main__':main()
