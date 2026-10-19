"""Fixed-destination official bulk data capture and normalized snapshot validation.

No credentials, scraping scripts, or model-generated market data. TWSE common stocks
are the initial live scope; ETFs/TPEx can be imported through the same snapshot contract.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo('Asia/Taipei')
ENDPOINTS = {
    'master': 'https://openapi.twse.com.tw/v1/opendata/t187ap03_L',
    'quotes': 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL',
    'valuation': 'https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL',
}
MISSING = (None, '', '-', '--', 'N/A', 'NaN')


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(encode(value)).hexdigest()


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(encode(value) + b'\n')
    temp.replace(path)


def taiwan_date(value):
    text = str(value).replace('/', '').replace('-', '').strip()
    if len(text) == 7 and text.isdigit():
        return date(int(text[:3])+1911, int(text[3:5]), int(text[5:])).isoformat()
    if len(text) == 8 and text.isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:])).isoformat()
    raise ValueError('Unrecognized official date format')


def numeric(value):
    if value in MISSING:
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean is not a financial number')
    number = float(str(value).replace(',', '').strip())
    if not math.isfinite(number):
        raise ValueError('Non-finite official value')
    return number


def download(url, timeout=20, attempts=2):
    """Bounded retries on transient failures; never bypass proxy/TLS or retry a 403."""
    if url not in ENDPOINTS.values():
        raise ValueError('Only registered official bulk endpoints are supported')
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Investment-Manager-Research/0.1'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.geturl() != url:
                    raise ValueError('Unexpected redirect; review source before allowing it')
                raw = response.read(15_000_001)
            if len(raw) > 15_000_000:
                raise ValueError('Response exceeds capture limit')
            return raw
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts-1:
                raise
        except urllib.error.URLError as error:
            if '403' in str(error) or attempt == attempts-1:
                raise
        time.sleep(0.25 * (attempt+1))
    raise RuntimeError('Download did not complete')


def unique_rows(rows, code_key):
    result = {}
    for row in rows:
        code = str(row[code_key]).strip()
        if code in result:
            raise ValueError(f'Duplicate instrument code in source: {code}')
        result[code] = row
    return result


def normalize_twse(raws, captured_at):
    """Fail on schema drift; do not classify ETFs by code length/name heuristics."""
    master, quotes, valuation = [json.loads(raws[k]) for k in ('master','quotes','valuation')]
    if not all(isinstance(x,list) and x for x in [master,quotes,valuation]):
        raise ValueError('Official bulk source must be a nonempty JSON array')
    for rows, keys in [(master,['公司代號','公司名稱','產業別']),
                       (quotes,['Code','Date','ClosingPrice','TradeValue']),
                       (valuation,['Code','Date','PEratio','PBratio'])]:
        if any(not set(keys) <= row.keys() for row in rows):
            raise ValueError('Official schema drift: required columns missing')
    masters=unique_rows(master,'公司代號'); prices=unique_rows(quotes,'Code'); vals=unique_rows(valuation,'Code')
    quote_dates={taiwan_date(row['Date']) for row in quotes}
    if len(quote_dates)!=1:
        raise ValueError('Mixed quote dates require an explicit adapter revision')
    price_date=next(iter(quote_dates))
    sources=[]
    for key, raw in raws.items():
        sources.append({'source_id':'twse-'+key,'provider':'TWSE','locator':ENDPOINTS[key],
            'retrieved_at':captured_at,'data_as_of':price_date if key=='quotes' else None,
            'published_at':None,'raw_file':'raw/'+key+'.json',
            'raw_sha256':hashlib.sha256(raw).hexdigest()})
    instruments=[]
    for code,row in sorted(masters.items()):
        # This master documents listed companies; reject surprising identities rather than guessing.
        if not re.fullmatch(r'\d{4}',code):
            raise ValueError('Company-master identity requires manual review')
        q=prices.get(code); v=vals.get(code); metrics={}
        if q:
            for name,key in [('close','ClosingPrice'),('turnover_twd','TradeValue')]:
                metrics[name]={'value':numeric(q[key]),'as_of':price_date,'source_id':'twse-quotes','unit':'TWD/unit' if name=='close' else 'TWD'}
        if v:
            val_date=taiwan_date(v['Date'])
            for name,key in [('pe','PEratio'),('pb','PBratio')]:
                value=numeric(v[key])
                metrics[name]={'value':value if value is None or value>0 else None,'as_of':val_date,'source_id':'twse-valuation','unit':'multiple'}
        instruments.append({'asset_id':'TWSE:'+code,'ticker':code,'name':str(row['公司名稱']),
            'market':'TWSE','asset_type':'stock','currency':'TWD','comparison_group':'TWSE:stock:industry-'+str(row['產業別']),
            'master_source_id':'twse-master','trading_status':'unknown','metrics':metrics,
            'limitations':['Official attention/disposition and long-term fundamentals not captured by this basic adapter']})
    result={'schema_version':'1.0','data_mode':'public_sources','captured_at':captured_at,
        'scope':{'label':'TWSE listed common-company master (not all Taiwan securities)',
                 'coverage':'full','origin':'official_master','source_ids':['twse-master']},
        'sources':sources,'instruments':instruments,
        'limitations':['TWSE common companies only; no TPEx/ETF coverage claimed',
            'Latest master captured at retrieval; not a historical constituent universe',
            'Basic valuation data is not five-factor or investment-decision evidence']}
    result['snapshot_id']=sha(result)
    validate_snapshot(result)
    return result


def validate_snapshot(snapshot):
    if snapshot.get('schema_version')!='1.0' or snapshot.get('data_mode') not in ('mock','public_sources','user_documents'):
        raise ValueError('Unknown snapshot version/data mode')
    expected=dict(snapshot); supplied=expected.pop('snapshot_id',None)
    if supplied!=sha(expected):
        raise ValueError('Snapshot integrity mismatch')
    captured=datetime.fromisoformat(snapshot['captured_at'].replace('Z','+00:00'))
    if captured.tzinfo is None:
        raise ValueError('Snapshot time needs timezone')
    if snapshot['scope']['coverage'] not in ('full','sample'):
        raise ValueError('Scope must distinguish full and sample')
    if snapshot['scope']['origin'] not in ('official_master','user_declared','mock'):
        raise ValueError('Unknown universe origin')
    if snapshot['scope']['coverage']=='full' and snapshot['scope']['origin']=='user_declared':
        raise ValueError('User-declared sample cannot claim full-market coverage')
    source_ids=set()
    for s in snapshot['sources']:
        if s['source_id'] in source_ids:
            raise ValueError('Duplicate snapshot source')
        source_ids.add(s['source_id'])
        retrieved=datetime.fromisoformat(s['retrieved_at'].replace('Z','+00:00'))
        if retrieved.tzinfo is None or retrieved>captured:
            raise ValueError('Source retrieval is after snapshot capture')
        published=s.get('published_at')
        if published and datetime.fromisoformat(published.replace('Z','+00:00'))>retrieved:
            raise ValueError('Source was not available when retrieved')
    if not set(snapshot['scope']['source_ids']) <= source_ids:
        raise ValueError('Unknown universe source')
    seen=set()
    if not source_ids or not snapshot['scope']['source_ids']:
        raise ValueError('A universe needs explicit provenance')
    for item in snapshot['instruments']:
        key=item['asset_id']
        if key in seen:
            raise ValueError('Duplicate snapshot instrument')
        seen.add(key)
        if not re.fullmatch(r'(TWSE|TPEx):[0-9A-Z]+',key) or key!=item['market']+':'+item['ticker']:
            raise ValueError('Instrument identity mismatch')
        if item['asset_type'] not in ('stock','etf','other') or item['trading_status'] not in ('unknown','active','suspended','delisted'):
            raise ValueError('Unknown asset type/trading state')
        if not isinstance(item['comparison_group'],str):
            raise ValueError('Comparison group must be explicit')
        if item['master_source_id'] not in source_ids:
            raise ValueError('Unknown instrument source')
        for metric in item['metrics'].values():
            if metric['source_id'] not in source_ids:
                raise ValueError('Unknown metric source')
            day=date.fromisoformat(metric['as_of'])
            if day>captured.astimezone(TAIPEI).date():
                raise ValueError('Future-dated metric')
            if metric['value'] is not None:
                if isinstance(metric['value'],bool) or not isinstance(metric['value'],(int,float)):
                    raise ValueError('Normalized metric must be a JSON number or null')
                numeric(metric['value'])
    if not seen:
        raise ValueError('Empty universe is not a successful snapshot')
    return snapshot


def capture_twse(output, fetch=download, now=None):
    """Write raw sources and failure diagnostics; never replace a failed fetch with mock data."""
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'snapshot.json').exists():
        raise ValueError('Snapshot directory already contains a snapshot; choose a new capture directory')
    raw_dir=output/'raw'; raw_dir.mkdir(exist_ok=True)
    failures=[]; raws={}; started=now or datetime.now(timezone.utc).isoformat()
    for key,url in ENDPOINTS.items():
        try:
            raw=fetch(url)
            json.loads(raw)
            raws[key]=raw
            (raw_dir/(key+'.json')).write_bytes(raw)
        except Exception as error:
            failures.append({'source_id':'twse-'+key,'url':url,'error_type':type(error).__name__,'error':str(error)})
    captured=now or datetime.now(timezone.utc).isoformat()
    atomic_json(output/'fetch_attempt.json',{'started_at':started,'finished_at':captured,'failures':failures,'downloaded':sorted(raws)})
    if failures:
        raise ValueError('Official capture incomplete; inspect fetch_attempt.json and fix access/source failures')
    try:
        snapshot=normalize_twse(raws,captured)
    except Exception as error:
        atomic_json(output/'normalization_failure.json',{'error_type':type(error).__name__,'error':str(error)})
        raise
    atomic_json(output/'snapshot.json',snapshot)
    return snapshot
