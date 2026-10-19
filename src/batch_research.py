"""Manual, resumable research campaigns over a frozen universe; no LLM/API trading engine."""
from __future__ import annotations
import argparse
import csv
import io
import json
import math
import statistics
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

if __package__:
    from . import market_snapshot as ms
    from . import research_handoff as handoff
else:
    import market_snapshot as ms
    import research_handoff as handoff

PROFILES = {
 'stock_basic_v1': {'asset_type':'stock','dimensions':{'valuation':{'pe':False,'pb':False}},'weights':{'valuation':1.0},
   'label':'基礎估值研究優先度；不是五因子分數或買入訊號'},
 'stock_five_factor_v1': {'asset_type':'stock','dimensions':{
   'valuation':{'pe':False,'pb':False,'ev_ebitda':False,'fcf_yield':True},
   'quality':{'roe':True,'roic':True,'ocf_to_net_income':True,'debt_to_assets':False},
   'momentum':{'relative_return_3m':True,'relative_return_6m':True,'relative_return_12m':True},
   'sentiment':{'flow_20d':True,'flow_60d':True,'insider_change':True},
   'growth':{'revenue_growth_3m':True,'revenue_growth_ttm':True,'eps_growth_ttm':True,'margin_change':True}},
   'weights':{'valuation':.2,'quality':.25,'momentum':.2,'sentiment':.15,'growth':.2},
   'label':'既有五因子同組研究優先度；未經 alpha 回測'},
 'etf_vehicle_v1': {'asset_type':'etf','dimensions':{'vehicle':{'total_expense_ratio':False,'tracking_error':False,'turnover_twd':True}},
   'weights':{'vehicle':1.0},'label':'同曝險 ETF 載具研究優先度；不評底層進場吸引力'},
}
DEFAULT_POLICY = {'profiles':['stock_basic_v1','etf_vehicle_v1'],'max_quote_age_days':7,
    'min_turnover_twd':0,'minimum_peers':5,'shortlist_per_group':3,'deep_research_limit':5}
UNITS = {'close':'TWD/unit','turnover_twd':'TWD','pe':'multiple','pb':'multiple','ev_ebitda':'multiple'}


def now(): return datetime.now(timezone.utc).isoformat()


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY)|{'as_of'}:
        raise ValueError('Policy keys must match the documented campaign contract')
    stamp=datetime.fromisoformat(policy['as_of'].replace('Z','+00:00'))
    if stamp.tzinfo is None: raise ValueError('Policy as_of requires timezone')
    if not policy['profiles'] or len(set(policy['profiles']))!=len(policy['profiles']) or any(x not in PROFILES for x in policy['profiles']):
        raise ValueError('Unknown/duplicate screening profile')
    if len({PROFILES[p]['asset_type'] for p in policy['profiles']})!=len(policy['profiles']):
        raise ValueError('Choose one profile per asset type; do not duplicate a stock across rankings')
    for key in ['max_quote_age_days','minimum_peers','shortlist_per_group','deep_research_limit']:
        if isinstance(policy[key],bool) or not isinstance(policy[key],int) or policy[key]<0:
            raise ValueError('Policy budgets must be nonnegative integers')
    if policy['minimum_peers']<5 or policy['shortlist_per_group']<1:
        raise ValueError('At least five peers and one shortlist item per group required')
    if isinstance(policy['min_turnover_twd'],bool) or not isinstance(policy['min_turnover_twd'],(int,float)) or not math.isfinite(policy['min_turnover_twd']) or policy['min_turnover_twd']<0:
        raise ValueError('Turnover threshold must be finite/nonnegative')
    return stamp


def method_context(root=handoff.ROOT):
    sha,read,manifest=handoff.committed_materials(root)
    current=handoff.local_files(root)
    if any(current(p)!=read(p) for p in handoff.required_paths(manifest)):
        raise ValueError('Commit reviewed methodology and manifest before creating/resuming a campaign')
    return {'research_commit_sha':sha,'manifest_sha256':handoff.digest(read(handoff.MANIFEST)),
        'skill_versions':handoff.version_records(manifest,{'opportunity-screener','company-research'}),
        'engine_sha256':engine_fingerprint()}


def engine_fingerprint():
    return ms.sha({name:handoff.digest((Path(__file__).parent/name).read_bytes())
                   for name in ['batch_research.py','market_snapshot.py']})


def connect(run_dir):
    db=sqlite3.connect(Path(run_dir)/'campaign.sqlite')
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=5000')
    return db


def initialize(snapshot,run_dir,policy,methodology,source_dir=None):
    handoff.schema_validator(handoff.local_files(handoff.ROOT),'market-snapshot.schema.json').validate(snapshot)
    handoff.schema_validator(handoff.local_files(handoff.ROOT),'research-campaign.input.schema.json').validate(policy)
    ms.validate_snapshot(snapshot); validate_policy(policy)
    if datetime.fromisoformat(snapshot['captured_at'].replace('Z','+00:00')) > datetime.fromisoformat(policy['as_of'].replace('Z','+00:00')):
        raise ValueError('Snapshot was captured after research cutoff')
    if methodology['engine_sha256'] != engine_fingerprint():
        raise ValueError('Wrong campaign engine fingerprint')
    archived={}
    for source in snapshot['sources']:
        if source.get('raw_file'):
            relative=handoff.safe_path(source['raw_file'])
            if source_dir is None:raise ValueError('Raw evidence must be archived with the campaign')
            raw_path=Path(source_dir)/relative
            if not raw_path.resolve().is_relative_to(Path(source_dir).resolve()):
                raise ValueError('Raw evidence escapes snapshot directory')
            raw=raw_path.read_bytes()
            if handoff.digest(raw)!=source['raw_sha256']:raise ValueError('Raw source integrity mismatch')
            archived[relative]=raw
    run_dir=Path(run_dir); run_dir.mkdir(parents=True,exist_ok=True)
    if (run_dir/'campaign.sqlite').exists():
        raise ValueError('Campaign exists; use process/resume, never overwrite')
    metadata={'campaign_version':'1.0','snapshot_id':snapshot['snapshot_id'],'data_mode':snapshot['data_mode'],
        'scope':snapshot['scope'],'policy':policy,'methodology':methodology,'created_at':now(),
        'identity':ms.sha({'snapshot':snapshot['snapshot_id'],'policy':policy,'methodology':methodology})}
    with connect(run_dir) as db:
        db.executescript('''
          CREATE TABLE metadata(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, snapshot TEXT NOT NULL);
          CREATE TABLE assets(asset_id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL
            CHECK(status IN ('pending','evaluated','excluded','needs_data','failed')), result TEXT, attempts INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE drafts(asset_id TEXT NOT NULL REFERENCES assets(asset_id), version INTEGER NOT NULL,
            proposal TEXT NOT NULL,memo TEXT NOT NULL,content_hash TEXT NOT NULL,submitted_at TEXT NOT NULL,
            PRIMARY KEY(asset_id,version),UNIQUE(asset_id,content_hash));
        ''')
        db.execute('INSERT INTO metadata VALUES(1,?,?)',(ms.encode(metadata).decode(),ms.encode(snapshot).decode()))
        db.executemany('INSERT INTO assets(asset_id,payload,status) VALUES(?,?,?)',
            [(x['asset_id'],ms.encode(x).decode(),'pending') for x in sorted(snapshot['instruments'],key=lambda x:x['asset_id'])])
    for relative,raw in archived.items():
        path=run_dir/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return metadata


def load(db):
    row=db.execute('SELECT payload,snapshot FROM metadata WHERE id=1').fetchone()
    metadata,snapshot=json.loads(row['payload']),json.loads(row['snapshot'])
    ms.validate_snapshot(snapshot); validate_policy(metadata['policy'])
    identity=ms.sha({'snapshot':snapshot['snapshot_id'],'policy':metadata['policy'],'methodology':metadata['methodology']})
    if identity!=metadata['identity'] or snapshot['snapshot_id']!=metadata['snapshot_id']:
        raise ValueError('Frozen campaign metadata/snapshot was modified')
    if metadata['methodology']['engine_sha256']!=engine_fingerprint():
        raise ValueError('Engine changed; restore the pinned version or start a new campaign')
    actual=[(x['asset_id'],json.loads(x['payload'])) for x in db.execute('SELECT asset_id,payload FROM assets ORDER BY asset_id')]
    expected=sorted((x['asset_id'],x) for x in snapshot['instruments'])
    if actual!=expected:
        raise ValueError('Campaign universe was altered')
    return metadata,snapshot


def datum(item,key):
    value=item['metrics'].get(key,{}).get('value')
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value): return None
    if key in ('pe','pb','ev_ebitda','close') and value<=0: return None
    if key in ('turnover_twd','total_expense_ratio','tracking_error') and value<0: return None
    return value


def stage1(item,policy):
    profiles=[p for p in policy['profiles'] if PROFILES[p]['asset_type']==item['asset_type']]
    result={'asset_id':item['asset_id'],'reasons':[],'gaps':[],'profile':profiles[0] if profiles else None,
        'source_ids':sorted({item['master_source_id']}|{m['source_id'] for m in item['metrics'].values()}),
        'flags':list(item.get('limitations',[]))}
    if not profiles or item['currency']!='TWD':
        return 'excluded',{**result,'reasons':['Outside declared profile/currency scope; no unsupported currency comparison']}
    if item['trading_status'] in ('suspended','delisted'):
        return 'excluded',{**result,'reasons':['Official/imported record indicates suspended/delisted']}
    if item['trading_status']=='unknown':result['flags'].append('Trading restrictions/attention/disposition not independently verified')
    if item['asset_type']=='etf' and item.get('etf_structure')!='passive_unleveraged':
        return 'needs_data',{**result,'gaps':['ETF vehicle profile requires verified passive_unleveraged structure; active/bond/leveraged/derivative products need a separate method']}
    if result['profile']=='stock_five_factor_v1' and item.get('fundamental_model')!='non_financial':
        return 'needs_data',{**result,'gaps':['Five-factor implementation requires verified non-financial comparability; financial firms need their separate quality method']}
    if not item['comparison_group'] or item['comparison_group'].lower()=='unknown':result['gaps'].append('comparison_group')
    for key in ['close','turnover_twd']:
        value=datum(item,key)
        if value is None:result['gaps'].append(key);continue
        expected_unit=UNITS[key]
        metric=item['metrics'][key]
        if metric['unit']!=expected_unit:result['gaps'].append(key+':unit');continue
        age=(datetime.fromisoformat(policy['as_of'].replace('Z','+00:00')).astimezone(ms.TAIPEI).date()-date.fromisoformat(metric['as_of'])).days
        if not 0<=age<=policy['max_quote_age_days']:result['gaps'].append(key+':stale')
    if result['gaps']:return 'needs_data',result
    if datum(item,'turnover_twd')<policy['min_turnover_twd']:
        return 'excluded',{**result,'reasons':['Below user-declared daily turnover filter (not 20-day average)']}
    return 'evaluated',{**result,'reasons':['Eligible for declared preliminary comparison; not an investment recommendation']}


def process(run_dir,max_items=100,retry_failed=False,evaluator=stage1):
    if isinstance(max_items,bool) or not isinstance(max_items,int) or max_items<1:
        raise ValueError('max_items must be a positive processing budget')
    with connect(run_dir) as db:
        metadata,_=load(db)
        if retry_failed:db.execute("UPDATE assets SET status='pending',result=NULL WHERE status='failed'")
        db.commit()
        rows=db.execute("SELECT asset_id,payload FROM assets WHERE status='pending' ORDER BY asset_id LIMIT ?",(max_items,)).fetchall()
        for row in rows:
            try:
                status,result=evaluator(json.loads(row['payload']),metadata['policy'])
                if status not in ('evaluated','excluded','needs_data'):raise ValueError('Evaluator returned an invalid state')
            except Exception as error:
                status='failed'; result={'asset_id':row['asset_id'],'reasons':[type(error).__name__+': '+str(error)],'gaps':[]}
            # One atomic per-asset transition; a crash never erases the completed earlier batches.
            with db:
                db.execute("UPDATE assets SET status=?,result=?,attempts=attempts+1 WHERE asset_id=? AND status='pending'",
                    (status,ms.encode(result).decode(),row['asset_id']))
    return export(run_dir)


def percentile(value,values,higher):
    n=len(values); below=sum(x<value for x in values); equal=sum(x==value for x in values)
    score=10*(below+(equal-1)/2)/(n-1)
    return score if higher else 10-score


def comparisons(rows,policy):
    groups=defaultdict(list)
    for row in rows:
        if row['status']=='evaluated':
            item=json.loads(row['payload']); result=json.loads(row['result'])
            groups[(result['profile'],item['comparison_group'])].append(item)
    results=[]
    for (profile,group),members in sorted(groups.items()):
        spec=PROFILES[profile]; factors={k:direction for dim in spec['dimensions'].values() for k,direction in dim.items()}
        # Do not quietly compare a stale quote with today's peers.
        comparable_date=max(item['metrics']['close']['as_of'] for item in members)
        pools={}
        for key in factors:
            # Comparing different dates/units is invalid, even if values look plausible.
            for item in members:
                metric=item['metrics'].get(key,{})
                if datum(item,key) is not None and metric.get('unit')==UNITS.get(key,'ratio') and metric.get('as_of')==comparable_date and item['metrics']['close']['as_of']==comparable_date:
                    pools.setdefault(key,[]).append(datum(item,key))
        ranked=[]
        for item in members:
            dimensions={}; coverage={}; sub={}; gaps=[]
            for dimension,fields in spec['dimensions'].items():
                values=[]
                for key,higher in fields.items():
                    metric=item['metrics'].get(key,{})
                    valid=(datum(item,key) is not None and metric.get('unit')==UNITS.get(key,'ratio') and
                           metric.get('as_of')==comparable_date and item['metrics']['close']['as_of']==comparable_date and len(pools.get(key,[]))>=policy['minimum_peers'])
                    if valid:
                        sub[key]=percentile(datum(item,key),pools[key],higher);values.append(sub[key])
                    else:gaps.append(key+': missing/invalid/date/unit/peer-count')
                coverage[dimension]=len(values)/len(fields)
                dimensions[dimension]=sum(values)/len(values) if values else None
            can_rank=all(x>=.75 for x in coverage.values())
            score=sum(dimensions[k]*spec['weights'][k] for k in dimensions) if can_rank else None
            ranked.append({'asset_id':item['asset_id'],'name':item['name'],'profile':profile,'comparison_group':group,
                'score':score,'rank':None,'dimension_scores':dimensions,'dimension_coverage':coverage,
                'factor_scores':sub,'comparison_as_of':comparable_date,
                'peer_evidence':{k:{'value':datum(item,k),'peer_median':statistics.median(pools[k]),
                    'direction':'higher' if factors[k] else 'lower','unit':UNITS.get(k,'ratio')}
                    for k in sub},
                'peer_counts':{k:len(pools.get(k,[])) for k in factors},'gaps':gaps,
                'reason':'同組可比資料的研究優先度；價格便宜不保證品質或報酬' if can_rank else '不可比／資料不足，不打零分、不排名'})
        ordered=sorted([x for x in ranked if x['score'] is not None],key=lambda x:(-x['score'],x['asset_id']))
        for rank,row in enumerate(ordered,1):row['rank']=rank
        results.extend(ordered+sorted([x for x in ranked if x['score'] is None],key=lambda x:x['asset_id']))
    return results


def choose_queue(ranking,policy):
    groups=defaultdict(list)
    for row in ranking:
        if row['rank'] is not None and row['rank']<=policy['shortlist_per_group']:
            groups[(row['profile'],row['comparison_group'])].append(row)
    picked=[]; keys=sorted(groups)
    for offset in range(policy['shortlist_per_group']):
        for key in keys:
            if len(picked)>=policy['deep_research_limit']:return picked
            if offset<len(groups[key]):picked.append(groups[key][offset])
    return picked


def build_report(db,metadata,snapshot):
    rows=db.execute('SELECT * FROM assets ORDER BY asset_id').fetchall();counts=Counter(r['status'] for r in rows)
    complete=counts['pending']==0
    ranking=comparisons(rows,metadata['policy']) if complete else []
    queue=choose_queue(ranking,metadata['policy']) if complete else []
    submissions=[dict(r) for r in db.execute('SELECT asset_id,MAX(version) AS version FROM drafts GROUP BY asset_id ORDER BY asset_id')]
    report={'campaign_version':'1.0','campaign_id':metadata['identity'],'snapshot_id':snapshot['snapshot_id'],
        'data_mode':metadata['data_mode'],'scope':metadata['scope'],'as_of':metadata['policy']['as_of'],
        'methodology':metadata['methodology'],'policy':metadata['policy'],
        'coverage':{'declared_count':len(rows),**{k:counts[k] for k in ['pending','evaluated','excluded','needs_data','failed']},
                    'processing_complete':complete,'research_complete':False},
        'status':'processing' if not complete else ('awaiting_deep_research' if queue else 'blocked_no_comparable_candidates'),
        'ranking':ranking,'deep_research_queue':[x['asset_id'] for x in queue],
        'queue_policy':'Round-robin across sorted profile/group keys, within-group rank; budget allocation is NOT a global investment ranking',
        'deferred_groups':sorted({x['comparison_group'] for x in ranking if x['rank'] is not None}-{x['comparison_group'] for x in queue}),
        'deferred_ranked_assets':[x['asset_id'] for x in ranking if x['rank'] is not None and x['asset_id'] not in {q['asset_id'] for q in queue}],
        'research_artifacts_complete':bool(queue) and {q['asset_id'] for q in queue}<={s['asset_id'] for s in submissions},
        'validated_drafts':submissions,'items':[{'asset_id':r['asset_id'],'status':r['status'],'attempts':r['attempts'],
            'details':json.loads(r['result']) if r['result'] else None} for r in rows],
        'sources':snapshot['sources'],
        'limitations':snapshot['limitations']+['No automatic LLM research, financial advice, approval or holdings mutation',
            'Queue packets are pending research; submitted drafts are format/provenance checked, not verified investment conclusions',
            'Five-factor scores, basic valuation and ETF vehicle scores must not be mixed across groups',
            'Single-day turnover is not ADV; product restrictions and source accuracy still require verification']}
    if report['research_artifacts_complete']:report['status']='ready_for_synthesis_not_approved'
    if sum(report['coverage'][k] for k in ['pending','evaluated','excluded','needs_data','failed'])!=len(rows):
        raise ValueError('Universe accounting does not reconcile')
    # Reconcile results and status before publishing a report.
    report['coverage']['ranked_count']=sum(x['rank'] is not None for x in ranking)
    report['coverage']['unranked_evaluated_count']=counts['evaluated']-report['coverage']['ranked_count'] if complete else counts['evaluated']
    return report


def markdown(report):
    c=report['coverage']; mode='MOCK ONLY — 非市場分析' if report['data_mode']=='mock' else '批次初篩，非投資建議'
    text=f"# Batch Research — {mode}\n\n截止：{report['as_of']}\n\n母體：{report['scope']['label']}；coverage={report['scope']['coverage']}。\n\n"
    text+='| 母體 | 待處理 | 初篩完成 | 排除 | 待補資料 | 失敗 | 可排名 | 已收件草稿 |\n|---|---|---|---|---|---|---|---|\n'
    text+=f"| {c['declared_count']} | {c['pending']} | {c['evaluated']} | {c['excluded']} | {c['needs_data']} | {c['failed']} | {c['ranked_count']} | {len(report['validated_drafts'])} |\n\n"
    text+='處理完成不代表深研完成。未完成全母體分類前不輸出暫時前幾名冒充完整比較。\n\n'
    if not c['processing_complete']:text+='本次預算用完，請 resume/process 接續；尚無完整排名。\n\n'
    if report['ranking']:
        text+='## 同組研究優先度比較\n\n| 標的 | 組別／方法 | 組內名次 | 研究分數 | 結論／缺口 |\n|---|---|---|---|---|\n'
        for x in report['ranking']:
            evidence='; '.join(f"{k}={v['value']} vs 組中位數 {v['peer_median']} ({v['direction']} preferable)" for k,v in x['peer_evidence'].items())
            text+=f"| {x['asset_id']} | {x['comparison_group']} / {x['profile']} | {x['rank'] if x['rank'] is not None else '未排名'} | {round(x['score'],2) if x['score'] is not None else 'N/A'} | {x['reason']}；{evidence}；{', '.join(x['gaps'])} |\n"
    text+='\n## 深研交接與決策邊界\n\n'
    text+='待研究：'+(', '.join(report['deep_research_queue']) or '無可比較候選')+'。\n\n'
    text+='名單由各組輪流分配有限研究預算，不是跨市場總排名。queue/ 下的 packet 包含同組比較、原始數值／日期／來源、缺口與研究指令，必須由 ChatGPT／研究者依 canonical company-research 完成 Memo 和 Proposal 再提交驗證。\n\n'
    text+='已收件草稿數不等於研究正確或已核准；缺持倉／風險資料仍可完成資產研究，但 Gate 3 Not Assessed，個人決策保持 Insufficient Evidence。\n\n'
    text+='## 全母體處理與排除紀錄\n\n'
    text+='完整帳目見 ledger.csv 和 campaign.json（包含每檔理由、缺口、來源與嘗試數），不能只展示留下的標的。\n\n'
    for item in report['items']:
        if item['status'] in ('excluded','needs_data','failed'):
            details=item['details'] or {}
            text+=f"- {item['asset_id']} — {item['status']}: {'; '.join(details.get('reasons',[])+details.get('gaps',[]))}\n"
    text+='\n## 來源、版本與限制\n\nResearch commit: '+report['methodology']['research_commit_sha']+'\n\n'
    text+='\n'.join(f"- {s['source_id']}: {s['locator']}；retrieved_at={s['retrieved_at']}" for s in report['sources'])+'\n\n'
    text+='研究預算尚未涵蓋的組別：'+(', '.join(report['deferred_groups']) or '無')+'。\n\n'
    text+='\n'.join('- '+x for x in report['limitations'])+'\n'
    return text


def export(run_dir):
    run_dir=Path(run_dir)
    with connect(run_dir) as db:
        metadata,snapshot=load(db);report=build_report(db,metadata,snapshot)
        drafts=[dict(row) for row in db.execute('SELECT * FROM drafts ORDER BY asset_id,version')]
    handoff.schema_validator(handoff.local_files(handoff.ROOT),'research-campaign.output.schema.json').validate(report)
    ms.atomic_json(run_dir/'campaign.json',report)
    (run_dir/'REPORT.md').write_text(markdown(report))
    stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['asset_id','status','attempts','reasons','gaps'])
    for row in report['items']:
        details=row['details'] or {};writer.writerow([row['asset_id'],row['status'],row['attempts'],json.dumps(details.get('reasons',[]),ensure_ascii=False),json.dumps(details.get('gaps',[]),ensure_ascii=False)])
    (run_dir/'ledger.csv').write_text(stream.getvalue())
    packets=run_dir/'queue';packets.mkdir(exist_ok=True)
    assets={x['asset_id']:x for x in snapshot['instruments']}
    ranking={x['asset_id']:x for x in report['ranking']}
    for asset_id in report['deep_research_queue']:
        row=ranking[asset_id];item=assets[asset_id]
        packet={'packet_version':'1.0','campaign_id':report['campaign_id'],'snapshot_id':snapshot['snapshot_id'],
            'data_mode':snapshot['data_mode'],'status':'pending_human_or_chatgpt_research','asset':item,
            'comparison':row,'peer_comparisons':[x for x in report['ranking'] if x['profile']==row['profile'] and x['comparison_group']==row['comparison_group']],
            'sources':snapshot['sources'],'research_commit_sha':metadata['methodology']['research_commit_sha'],
            'required_outputs':['Investment Memo with final Investment Decision','Thesis Proposal schema 2.0, never approved'],
            'instruction':'Load canonical company-research and manifest at this commit. Verify source evidence; compare peers and alternatives. Fill missing long-term/ETF data, three gates and adversarial review. If blocked, identify decisive gaps. Do not turn preliminary score into Invest Now. Return both artifacts for submit.',
            'gaps':row['gaps']+['long-term quality and financial statements','forward return assumptions and downside','investor holdings/risk/liquidity profile']}
        ms.atomic_json(packets/(asset_id.replace(':','-')+'.json'),packet)
    for draft in drafts:
        directory=run_dir/'drafts'/draft['asset_id'].replace(':','-');directory.mkdir(parents=True,exist_ok=True)
        ms.atomic_json(directory/f"v{draft['version']}.json",json.loads(draft['proposal']))
        (directory/f"v{draft['version']}.md").write_text(draft['memo'])
    brief=('# ChatGPT Batch Research Work Order\n\n研究 commit: '+metadata['methodology']['research_commit_sha']+
        '\n\n先載入同版 canonical Skills／manifest 與 REPORT.md、campaign.json、ledger.csv。確認全母體帳目與 processing_complete；未完成先接續 process，不能用前幾筆交付市場結論。\n\n'
        '完成後逐一讀 queue/ 的 packet，依 company-research 補證與反方，交付 Memo＋Proposal 2.0，再用 submit 收件驗證。pending packet 不是深研報告，研究優先度不是投資順位。缺個人資料仍可比較資產，但 Gate 3 Not Assessed，不自行配置資金。\n\n'
        '最後彙總各候選支持／反對證據、來源日期、產品品質、進場條件、替代方案、缺口與條件性結論；引用比較母體與已收件草稿，說明研究預算延後的組別。資料不足交有原因的 Insufficient Evidence，不編報酬。\n\n'
        '讀 GitHub 檔案本身不會啟動 Python 或背景工作；需要授權執行工具，或由使用者／Codex 執行後上傳本 run 的資料與報告。\n')
    (run_dir/'CHATGPT_RESEARCH_BRIEF.md').write_text(brief)
    return report


def submit(run_dir,asset_id,proposal,memo,read,manifest):
    with connect(run_dir) as db:
        metadata,snapshot=load(db);report=build_report(db,metadata,snapshot)
        if asset_id not in report['deep_research_queue']:
            raise ValueError('Asset is not in this completed campaign research queue')
        if proposal['asset_id']!=asset_id or proposal['data_mode']!=metadata['data_mode']:
            raise ValueError('Proposal identity or mock/real data mode mismatch')
        if proposal['research_stage']!='deep_research':raise ValueError('Submission must be a deep-research draft')
        if proposal['data_cutoff']!=metadata['policy']['as_of']:
            raise ValueError('Proposal cutoff differs from frozen campaign; start a new campaign for later evidence')
        if handoff.digest(read(handoff.MANIFEST))!=metadata['methodology']['manifest_sha256']:
            raise ValueError('Submission must use the campaign pinned manifest')
        handoff.validate_proposal(proposal,metadata['methodology']['research_commit_sha'],read,manifest)
        import re
        if re.findall(r'^## (\d+)\.',memo,re.MULTILINE)!=[str(i) for i in range(1,15)] or asset_id not in memo:
            raise ValueError('Memo must identify the asset and retain all 14 template sections')
        content_hash=ms.sha({'proposal':proposal,'memo':memo})
        found=db.execute('SELECT version FROM drafts WHERE asset_id=? AND content_hash=?',(asset_id,content_hash)).fetchone()
        if found:return found['version']
        version=db.execute('SELECT COALESCE(MAX(version),0)+1 FROM drafts WHERE asset_id=?',(asset_id,)).fetchone()[0]
        db.execute('INSERT INTO drafts VALUES(?,?,?,?,?,?)',(asset_id,version,ms.encode(proposal).decode(),memo,content_hash,now()))
    export(run_dir)
    return version


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    fetch=sub.add_parser('capture-twse');fetch.add_argument('--output-dir',type=Path,required=True)
    init=sub.add_parser('init');init.add_argument('--snapshot',type=Path,required=True);init.add_argument('--run-dir',type=Path,required=True);init.add_argument('--policy',type=Path)
    proc=sub.add_parser('process');proc.add_argument('--run-dir',type=Path,required=True);proc.add_argument('--max-items',type=int,default=100);proc.add_argument('--retry-failed',action='store_true')
    exp=sub.add_parser('export');exp.add_argument('--run-dir',type=Path,required=True)
    deliver=sub.add_parser('submit');deliver.add_argument('--run-dir',type=Path,required=True);deliver.add_argument('--asset-id',required=True);deliver.add_argument('--proposal',type=Path,required=True);deliver.add_argument('--memo',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='capture-twse':
            snapshot=ms.capture_twse(args.output_dir);result={'snapshot_id':snapshot['snapshot_id'],'instruments':len(snapshot['instruments'])}
        elif args.command=='init':
            snapshot=handoff.decode(args.snapshot.read_bytes())
            policy=handoff.decode(args.policy.read_bytes()) if args.policy else {**DEFAULT_POLICY,'as_of':snapshot['captured_at']}
            result=initialize(snapshot,args.run_dir,policy,method_context(),args.snapshot.parent)
        elif args.command=='process':result=process(args.run_dir,args.max_items,args.retry_failed)
        elif args.command=='export':result=export(args.run_dir)
        else:
            with connect(args.run_dir) as db:metadata,_=load(db)
            _,read,manifest=handoff.committed_materials(handoff.ROOT,metadata['methodology']['research_commit_sha'])
            version=submit(args.run_dir,args.asset_id,handoff.decode(args.proposal.read_bytes()),args.memo.read_text(),read,manifest)
            result={'draft_version':version,'approval':'not_granted'}
        if 'coverage' in result:result={k:result[k] for k in ['campaign_id','status','coverage','deep_research_queue']}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as error:
        print('BATCH_NOT_COMPLETED: '+str(error),file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
