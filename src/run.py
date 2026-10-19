"""Minimal offline data-contract and alert demonstration; NOT a live investment monitor."""
import argparse, json, pathlib, sys
from datetime import datetime, date

def load(path):
    with open(path, encoding='utf-8') as f: return json.load(f)

def valid_http(url):
    return isinstance(url, str) and url.startswith(('https://','http://'))

def evaluate(config, quotes, events, *, allow_demo=False, now=None):
    now = now or datetime.now().astimezone().date()
    mode=quotes.get('mode')
    if mode != events.get('mode'): raise ValueError('Quotes/events data modes differ.')
    if mode not in ('live','demo'): raise ValueError('Unrecognized mode.')
    if mode == 'demo' and not allow_demo: raise ValueError('DEMO data requires --allow-demo.')
    try: quote_date=date.fromisoformat(quotes['as_of'])
    except Exception as e: raise ValueError('Invalid quote date') from e
    if mode=='live' and (quote_date > now or (now-quote_date).days>5):
        raise ValueError('Live quote snapshot outside permitted 5-calendar-day freshness envelope; verify market holiday and provider timestamp.')
    qmap={q['asset_id']:q for q in quotes.get('quotes',[])}
    rows=[]
    for asset in config.get('assets',[]):
        code=asset['asset_id']; q=qmap.get(code)
        if not q:
            rows.append({'asset_id':code,'status':'INSUFFICIENT_DATA','reason':'missing quote'}); continue
        if mode=='live' and (not valid_http(q.get('source_url')) or not q.get('published_at')):
            rows.append({'asset_id':code,'status':'INSUFFICIENT_DATA','reason':'quote provenance missing'}); continue
        try:
            prev=float(q['prev_close']); close=float(q['close']); assert prev>0 and close>0
        except (KeyError,ValueError,TypeError,AssertionError):
            rows.append({'asset_id':code,'status':'INSUFFICIENT_DATA','reason':'invalid price'});continue
        daily_pct=(close/prev-1)*100
        evts=[e for e in events.get('events',[]) if code in e.get('asset_ids',[]) and (allow_demo or (e.get('verified') and valid_http(e.get('source_url'))))]
        sev={'info':0,'watch':10,'high':25}
        event_weight=max((sev.get(e.get('severity'),0) for e in evts),default=0)
        # DEMO ONLY: alert-priority heuristic, NOT portfolio risk or loss probability.
        price_weight=25 if daily_pct<=-6 else (10 if daily_pct<=-3 else 0)
        score=min(100, price_weight+event_weight)
        status='REVIEW' if score>=25 else ('WATCH' if score>=10 else 'NO_ALERT')
        rows.append({'asset_id':code,'status':status,'daily_move_pct':round(daily_pct,2),'alert_priority_demo_0_100':score,'events':[e['id'] for e in evts]})
    return {'mode':mode,'data_as_of':str(quote_date),'not_portfolio_risk':True,'not_automated_investment_advice':True,'items':rows}

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--quotes',required=True);p.add_argument('--events',required=True);p.add_argument('--allow-demo',action='store_true');p.add_argument('--output');args=p.parse_args()
    try:
        result=evaluate(load(args.config),load(args.quotes),load(args.events),allow_demo=args.allow_demo)
    except (ValueError,KeyError,FileNotFoundError) as e:
        print(f'NOT_MONITORED: {e}',file=sys.stderr);return 2
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        path=pathlib.Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text+'\n',encoding='utf-8')
    else:print(text)
    return 0
if __name__=='__main__':sys.exit(main())
