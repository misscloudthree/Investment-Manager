"""Structured intake and compact presentation; no conversation parser, market fetch or advice engine."""
from __future__ import annotations
import copy
import math
from datetime import datetime
from zoneinfo import ZoneInfo

if __package__:
    from . import research_handoff as h
else:
    import research_handoff as h

FIELDS = {
    'product_scope':'商品／範圍限制（可答不限）',
    'holding_period':'預計持有多久（可答長期／不確定）',
    'entry_window':'何時開始投入／投入期限',
    'return_target':'累積總報酬目標及期限（可答無特定目標）',
    'risk_preference':'風險傾向；可承受波動與最大虧損分開說明（可先定性）',
}


def screening_mode(context):
    conditions=context['conditions']
    unresolved=[v for v in conditions.values() if v['status'] not in ('provided','no_preference')]
    unanswered=any(v['status']=='missing' and v['material'] for v in unresolved)
    if unanswered and not context['skip_questions'] and not context['exploratory_allowed']:
        return 'awaiting_conditions'
    return 'provisional_screening' if unresolved else 'specified_screening'


def validate_context(context,read=None):
    h.schema_validator(read or h.local_files(h.ROOT),'research-context.schema.json').validate(context)
    if context['screening_mode']!=screening_mode(context):
        raise ValueError('Screening mode contradicts recorded answers/assumptions')
    holding=context['conditions']['holding_period']
    if holding['status']=='missing' and holding['months'] is not None:
        raise ValueError('Missing holding period cannot contain invented months')
    return context


def prepare_context(answers,recorded_at,*,previous=None,skip_questions=None,
                    exploratory_allowed=None,requested_depth=None,read=None):
    """The caller extracts explicit answers from conversation first; this does not interpret free text."""
    if set(answers)-set(FIELDS):raise ValueError('Unknown intake field')
    if previous:validate_context(previous,read)
    conditions=copy.deepcopy(previous['conditions']) if previous else {
        key:{'status':'missing','text':None,'origin':'unknown','source_ref':None,'material':True}
        for key in FIELDS}
    conditions.update(copy.deepcopy(answers))
    if not previous and 'holding_period' not in answers:conditions['holding_period']['months']=None
    context={'schema_version':'1.0','recorded_at':recorded_at,'conditions':conditions,
        'skip_questions':skip_questions if skip_questions is not None else (previous or {}).get('skip_questions',False),
        'exploratory_allowed':exploratory_allowed if exploratory_allowed is not None else (previous or {}).get('exploratory_allowed',False),
        'requested_depth':requested_depth if requested_depth is not None else (previous or {}).get('requested_depth','snapshot')}
    context['screening_mode']=screening_mode(context)
    return validate_context(context,read)


def question_plan(context,read=None):
    validate_context(context,read)
    missing=[] if context['skip_questions'] else [key for key,v in context['conditions'].items()
        if v['status']=='missing' and v['material']]
    return {'mode':'single' if len(missing)==1 else ('compact_form' if missing else 'none'),
            'fields':missing,'questions':[FIELDS[key] for key in missing]}


def validate_input(value,schema_name,read=None):
    if schema_name not in ('opportunity-screener.input.schema.json','company-research.input.schema.json'):
        raise ValueError('Expected a research input schema')
    read=read or h.local_files(h.ROOT)
    h.schema_validator(read,schema_name).validate(value)
    if 'research_context' in value:
        validate_context(value['research_context'],read)
        months=value['research_context']['conditions']['holding_period']['months']
        if months is not None and value['horizon_months']!=months:
            raise ValueError('Input horizon contradicts recorded holding period')
    return value


def intake_text(context,read=None):
    plan=question_plan(context,read)
    groups={'已知條件':[],'本次假設':[],'仍需確認':[]}
    for key,value in context['conditions'].items():
        label='已知條件' if value['status'] in ('provided','no_preference') else (
            '本次假設' if value['status']=='assumed' else '仍需確認')
        groups[label].append(FIELDS[key]+'：'+(value['text'] or '未提供'))
    text='\n'.join(label+'：'+('；'.join(values) or '無') for label,values in groups.items())
    text+='\n本次狀態：'+context['screening_mode']+'；記錄時間：'+context['recorded_at']
    if plan['mode']=='single':text+='\n請補充'+plan['questions'][0]+'。'
    elif plan['mode']=='compact_form':text+='\n可部分填寫，允許不確定／交由系統假設：\n'+'\n'.join('- '+q for q in plan['questions'])
    return text


def unknown_price(currency='TWD'):
    return {'status':'not_estimated','low':None,'high':None,'currency':currency,'as_of':None,
        'method':None,'formula':None,'assumptions':[],'source_ids':[],
        'calculation_verified':False,'message':'未能可靠估計'}


def deep_dive_offer(context):
    return {'mode':'already_requested','prompt':None} if context['requested_depth']=='deep_dive' else {
        'mode':'ask_selection','prompt':'需要對全部或指定哪些標的展開深度報告？沿用上述投資條件即可。'}


def validate_snapshot(snapshot,read=None):
    read=read or h.local_files(h.ROOT)
    h.schema_validator(read,'decision-snapshot.schema.json').validate(snapshot)
    validate_context(snapshot['research_context'],read)
    if snapshot['research_context']['screening_mode']=='awaiting_conditions':
        raise ValueError('Collect material conditions or explicitly permit provisional exploration first')
    generated=datetime.fromisoformat(snapshot['generated_at'].replace('Z','+00:00'))
    cutoff=datetime.fromisoformat(snapshot['data_cutoff'].replace('Z','+00:00'))
    recorded=datetime.fromisoformat(snapshot['research_context']['recorded_at'].replace('Z','+00:00'))
    if cutoff>generated or recorded>generated:raise ValueError('Snapshot timestamps are inconsistent')
    sources=h.unique_ids(snapshot['source_references'],'source_id')
    for source in snapshot['source_references']:
        retrieved=datetime.fromisoformat(source['retrieved_at'].replace('Z','+00:00'))
        published=source['published_at']
        if retrieved>generated:raise ValueError('Source fetched after snapshot generation')
        if published and datetime.fromisoformat(published.replace('Z','+00:00'))>min(cutoff,retrieved):
            raise ValueError('Source publication unavailable at cutoff/retrieval')
        if source['published_date'] and source['published_date']>cutoff.astimezone(ZoneInfo('Asia/Taipei')).date().isoformat():
            raise ValueError('Source date after cutoff')
    def check(value):
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('Non-finite snapshot value')
        if isinstance(value,dict):
            if 'source_ids' in value and not set(value['source_ids'])<=sources:raise ValueError('Dangling snapshot source')
            for child in value.values():check(child)
        elif isinstance(value,list):
            for child in value:check(child)
    check(snapshot)
    seen=set()
    for row in snapshot['candidates']:
        asset=row['instrument']['market']+':'+row['instrument']['ticker']
        if asset in seen:raise ValueError('Duplicate snapshot asset')
        seen.add(asset)
        d=row['investment_decision']
        months=snapshot['research_context']['conditions']['holding_period']['months']
        years=d['investor_context']['horizon_years']
        if months is not None and years is not None and not math.isclose(months,12*years):
            raise ValueError('Decision horizon contradicts recorded holding period')
        h.validate_decision({'investment_decision':d,'asset_type':row['instrument']['asset_type'],
            'research_stage':row['research_stage'],'data_quality':{'status':row['data_quality_status']}})
        if d['decision_status']=='Insufficient Evidence' and not row['key_missing_information']:
            raise ValueError('Insufficient Evidence must explain decisive missing information')
        price=row['entry_price']
        if price['currency']!=row['instrument']['currency']:raise ValueError('Entry price currency mismatch')
        if price['status']=='verified_estimate':
            if price['low']>price['high']:raise ValueError('Entry range is reversed')
            if price['as_of']>cutoff.astimezone(ZoneInfo('Asia/Taipei')).date().isoformat():raise ValueError('Future valuation date')
        assessed=[s for s in d['return_scenarios'] if s['status']=='Assessed']
        if assessed and not row['return_basis']:raise ValueError('Assessed returns require income/cost/currency basis')
    return {'snapshot_valid':True,'scope':'presentation, references and existing decision-gate consistency',
            'deep_research_validated':False,'investment_accuracy':'not_validated'}


def _cell(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def render_snapshot(snapshot,read=None):
    validate_snapshot(snapshot,read)
    text='# Decision Snapshot'+(' — MOCK ONLY，非投資建議' if snapshot['data_mode']=='mock' else '')+'\n\n'
    text+=intake_text(snapshot['research_context'],read)+'\n\n'
    text+='| 商品 | 決策／研究優先度 | 核心原因／下一步 | 合理進場價 | 預期總報酬／期限 | 主要風險／翻轉因素 | 催化劑 | 類似標的／取捨 |\n|---|---|---|---|---|---|---|---|\n'
    for row in snapshot['candidates']:
        d=row['investment_decision'];p=row['entry_price']
        price='未能可靠估計' if p['status']=='not_estimated' else f"{p['low']}–{p['high']} {p['currency']}；{p['as_of']}；{p['method']}；{p['formula']}；假設：{'; '.join(p['assumptions'])}；來源：{', '.join(p['source_ids'])}"
        assessed=[s for s in d['return_scenarios'] if s['status']=='Assessed']
        returns='尚無可信估計' if not assessed else '; '.join(f"{s['name']} {s['horizon_years']}年累積含息 {s['total_return']:.1%}（條件情境）；公式 {s['formula']}；來源 {', '.join(s['source_ids'])}" for s in assessed)+'；口徑：'+row['return_basis']
        if not assessed:returns+='；持有條件：'+(snapshot['research_context']['conditions']['holding_period']['text'] or '未確認')
        brief=lambda values:'；'.join(x['text']+('（'+x['window']+'）' if x['window'] else '')+(' ['+', '.join(x['source_ids'])+']' if x['source_ids'] else ' [待驗證／未知]') for x in values)
        status='Wait（等待條件）' if d['decision_status']=='Wait for Conditions' else d['decision_status']
        cells=[row['instrument']['ticker']+' '+row['instrument']['name'],status+'；研究優先 '+row['research_priority']['level']+'：'+row['research_priority']['rationale'],
            '；'.join({'support':'支持','counterargument':'反方','unknown':'未知'}[x['kind']]+'：'+x['text'] for x in row['core_reasons'])+'；下一步：'+d['recommended_next_action'],price,returns,
            brief(row['risks'])+'；翻轉：'+'；'.join(x['condition'] for x in d['key_evidence_that_could_change_decision']),brief(row['catalysts']),brief(row['alternatives'])]
        text+='| '+' | '.join(_cell(x) for x in cells)+' |\n'
    text+='\n資料截止：'+snapshot['data_cutoff']+'；產出：'+snapshot['generated_at']+'。研究優先度不是買入建議，摘要不代表完整深研或 Proposal 已驗證。\n'
    for row in snapshot['candidates']:
        text+='\n'+row['instrument']['ticker']+' 關鍵缺口：'+('；'.join(row['key_missing_information']) or '無已列關鍵缺口，仍須核對原始證據')+'。\n'
    if snapshot['deep_dive_offer']['prompt']:text+='\n'+snapshot['deep_dive_offer']['prompt']+'\n'
    return text
