"""Decision-contract consistency and small offline calculations; no market access or trades."""
from decimal import Decimal, localcontext
import math
from statistics import stdev

EVIDENCE_ITEMS = ('product_structure', 'total_cost', 'tracking_or_active_performance', 'liquidity',
    'current_price', 'nav_comparison', 'historical_total_return', 'drawdown_and_volatility',
    'underlying_valuation', 'forward_return_assumptions', 'downside_risk', 'alternatives', 'horizon_compatibility')
PARAMETERS = ('earnings_growth', 'starting_multiple', 'terminal_multiple', 'dividend_return',
    'annual_cost', 'fx_return', 'entry_premium', 'exit_premium', 'round_trip_cost')
QUESTIONS = ('why_not_invest', 'entry_mistake', 'better_alternative', 'history_not_promise',
             'flip_assumption', 'evidence_sufficient', 'wait_reassessment')
METRICS = ('exchange_price', 'nav', 'total_expense_ratio', 'historical_total_return',
           'tracking_difference', 'tracking_error', 'maximum_drawdown', 'annualized_volatility',
           'underlying_pe', 'underlying_earnings_yield')
FORMULA = ('W=(1+g)^H*(PE_T/PE_0)*(1+d)^H*(1-c)^H*(1+fx)^H*'
           '((1+p_exit)/(1+p_entry))*(1-k); TR=W-1; CAGR=W^(1/H)-1')


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError('Finite numeric input required')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Finite numeric input required')
    return result


def equity_etf_return(inputs, years):
    """Constant-input sensitivity model, not an expected-return estimator/probability model.

    g: earnings growth before dividend reinvestment, d: reinvested cash distribution return,
    c: fund cost, fx: underlying currency return in investor currency, p: premium to NAV,
    k: combined entry/exit execution cost. All rates are fractions, not percentage points.
    """
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 50:
        raise ValueError('Horizon must be an integer from 1 to 50')
    v = {key: number(inputs[key]) for key in PARAMETERS}
    if min(v['starting_multiple'], v['terminal_multiple']) <= 0:
        raise ValueError('Positive comparable earnings multiples required')
    if any(v[k] <= -1 for k in ['earnings_growth','dividend_return','fx_return','entry_premium','exit_premium']):
        raise ValueError('Growth/return/premium inputs must exceed -100%')
    if any(not 0 <= v[k] < 1 for k in ['annual_cost','round_trip_cost']):
        raise ValueError('Cost inputs must be in [0,1)')
    with localcontext() as ctx:
        ctx.prec = 40
        h = Decimal(years)
        common = ((1+v['earnings_growth'])**years * (1+v['dividend_return'])**years *
                  (1-v['annual_cost'])**years * (1+v['fx_return'])**years *
                  (1+v['exit_premium'])/(1+v['entry_premium']) * (1-v['round_trip_cost']))
        wealth = common*v['terminal_multiple']/v['starting_multiple']
        result = {'total_return': wealth-1, 'annualized_return': wealth**(1/h)-1,
                  'break_even_terminal_multiple': v['starting_multiple']/common}
        if any(not math.isfinite(float(x)) for x in result.values()):
            raise ValueError('Model overflow')
        return {k: float(x) for k,x in result.items()}


def historical_risk(wealth, periods_per_year):
    """Same-currency, dividend-reinvested, equally-spaced wealth; caller verifies provenance."""
    if not isinstance(periods_per_year, int) or isinstance(periods_per_year, bool) or periods_per_year <= 0:
        raise ValueError('Explicit positive observations/year required')
    v = [float(number(x)) for x in wealth]
    if len(v) < 3 or any(x <= 0 or not math.isfinite(x) for x in v):
        raise ValueError('At least three positive finite wealth observations required')
    returns = [b/a-1 for a,b in zip(v,v[1:])]
    peak = v[0]
    drawdowns = []
    for x in v:
        peak = max(peak,x)
        drawdowns.append(x/peak-1)
    return {'total_return': v[-1]/v[0]-1, 'maximum_drawdown': min(drawdowns),
            'annualized_volatility': stdev(returns)*math.sqrt(periods_per_year)}


def tracking_statistics(fund_returns, benchmark_returns, periods_per_year):
    """Aligned periodic NAV/benchmark total returns, matching currency and tax basis."""
    if not isinstance(periods_per_year,int) or isinstance(periods_per_year,bool) or periods_per_year <= 0:
        raise ValueError('Explicit positive observations/year required')
    if len(fund_returns) != len(benchmark_returns) or len(fund_returns) < 2:
        raise ValueError('At least two aligned return pairs required')
    f,b = [[float(number(x)) for x in seq] for seq in [fund_returns,benchmark_returns]]
    if any(x <= -1 or not math.isfinite(x) for x in f+b):
        raise ValueError('Periodic returns must exceed -100%')
    annual = lambda seq: math.exp(sum(math.log1p(x) for x in seq)*periods_per_year/len(seq))-1
    return {'tracking_difference': annual(f)-annual(b),
            'tracking_error': stdev([x-y for x,y in zip(f,b)])*math.sqrt(periods_per_year)}


def unknown_metric(name):
    return {'name':name,'value':None,'unit':'TWD/unit' if name in ('exchange_price','nav') else ('multiple' if name=='underlying_pe' else 'ratio'),
            'currency':'TWD' if name in ('exchange_price','nav') else None,'period':'not verified',
            'classification':'unknown','quality':'missing','source_ids':[],'formula':None}


def blank_decision(reason='Decision evidence was not collected'):
    condition = {'condition_id':'decision-evidence-1','condition':'Obtain dated price, valuation, return assumptions and investor profile',
                 'source_ids':[],'linked_kpi_ids':[],'evidence_needed':reason,'action':'request_human_review'}
    return {'contract_version':'1.0','underlying_asset_class':'unknown','investor_context':{'capital_twd':None,'horizon_years':None,
            'holdings_status':'missing','risk_profile_status':'missing','liquidity_needs_status':'missing',
            'portfolio_snapshot_ref':None,'risk_profile_ref':None},
        'asset_quality':{'status':'Insufficient Evidence','rationale':reason,'source_ids':[]},
        'entry_attractiveness':{'status':'Insufficient Evidence','rationale':reason,'source_ids':[]},
        'portfolio_suitability':{'status':'Not Assessed','rationale':'Holdings, risk tolerance and liquidity needs not supplied','source_ids':[]},
        'decision_status':'Insufficient Evidence','confidence':'low',
        'evidence_coverage':{'required_items':len(EVIDENCE_ITEMS),'verified_items':0,'ratio':0},
        'evidence_checklist':{k:{'status':'missing','source_ids':[],'rationale':reason} for k in EVIDENCE_ITEMS},
        'market_metrics':{k:unknown_metric(k) for k in METRICS},
        'pricing_alignment':{'status':'unknown','rationale':reason,'source_ids':[]},
        'recommended_next_action':'Collect decisive evidence and investor profile; do not infer allocation or trades',
        'entry_reassessment_conditions':[condition],
        'return_scenarios':[{'name':n,'status':'Not Assessed','method':'not_assessed','horizon_years':None,
            'inputs':{k:None for k in PARAMETERS},'input_evidence':[],'formula':'Not computed: missing inputs',
            'cost_basis':'not_assessed','annualized_return':None,'total_return':None,
            'break_even_terminal_multiple':None,'source_ids':[],'limitations':[reason],
            'external_calculation':{'formula':None,'inputs':[],'record':None,'status':'not_applicable'}}
            for n in ['bull','base','bear']],
        'downside_risk':{'status':'Not Assessed','description':reason,'loss_fraction':None,'source_ids':[],'limitations':[reason]},
        'entry_options':[{'option':o,'tradeoffs':t,'conditions':'Requires verified evidence before a personal recommendation','source_ids':[]}
            for o,t in [('Now','Immediate exposure also bears immediate drawdown risk'),
                        ('Phased','Reduces timing concentration but adds cash drag and may raise costs'),
                        ('Wait','Preserves liquidity but may forgo gains; waiting needs a re-evaluation condition')]],
        'comparable_alternatives':[],
        'horizon_compatibility':{'status':'Not Assessed','rationale':reason,'source_ids':[]},
        'key_evidence_that_could_change_decision':[dict(condition)],
        'adversarial_review':{'completed':False,'recommendation_supported':False,
            'questions':{q:{'answer':reason,'source_ids':[],'unresolved':True} for q in QUESTIONS},'limitations':[reason]}}


def validate_decision(proposal):
    """Check evidence/decision consistency, not truth of sources or investment accuracy."""
    d = proposal['investment_decision']
    checklist = d['evidence_checklist']
    required = sum(v['status'] != 'not_applicable' for v in checklist.values())
    verified = sum(v['status'] == 'verified' for v in checklist.values())
    ratio = verified/required if required else 0
    coverage = d['evidence_coverage']
    if coverage['required_items'] != required or coverage['verified_items'] != verified or not math.isclose(coverage['ratio'],ratio,abs_tol=1e-9):
        raise ValueError('Decision evidence coverage does not match checklist')
    for evidence in checklist.values():
        if evidence['status'] == 'verified' and not evidence['source_ids']:
            raise ValueError('Verified decision evidence needs sources')
    ctx = d['investor_context']
    if ctx['holdings_status']=='provided' and not ctx['portfolio_snapshot_ref']:
        raise ValueError('Provided holdings need a snapshot reference')
    if ctx['risk_profile_status']=='provided' and not ctx['risk_profile_ref']:
        raise ValueError('Provided risk profile needs a reference')
    personal_missing = (any(ctx[k]=='missing' for k in ['holdings_status','risk_profile_status','liquidity_needs_status']) or ctx['horizon_years'] is None)
    if personal_missing and d['portfolio_suitability']['status'] != 'Not Assessed':
        raise ValueError('Missing investor data requires Portfolio Suitability Not Assessed')
    for gate in ['asset_quality','entry_attractiveness','portfolio_suitability']:
        if d[gate]['status'] not in ('Insufficient Evidence','Not Assessed') and not d[gate]['source_ids']:
            raise ValueError('Assessed decision gate needs sources')
    def complete(keys):
        return all(checklist[k]['status'] in ('verified','not_applicable') for k in keys)
    mandatory = ['product_structure','liquidity','current_price','historical_total_return','drawdown_and_volatility','underlying_valuation','forward_return_assumptions','downside_risk','alternatives','horizon_compatibility']
    if any(checklist[k]['status']=='not_applicable' for k in mandatory):
        raise ValueError('Essential decision evidence cannot be marked not applicable')
    quality_keys = ['product_structure','total_cost','tracking_or_active_performance','liquidity']
    entry_keys = [k for k in EVIDENCE_ITEMS if k not in quality_keys]
    if d['asset_quality']['status']=='Pass' and not complete(quality_keys):
        raise ValueError('Missing product evidence cannot pass Asset Quality')
    entry = d['entry_attractiveness']['status']
    if entry != 'Insufficient Evidence' and not complete(entry_keys):
        raise ValueError('Missing entry evidence cannot produce an entry assessment')
    metrics = d['market_metrics']
    numeric = lambda key: metrics[key]['value'] is not None and metrics[key]['quality']=='verified' and metrics[key]['classification']=='verified_fact' and bool(metrics[key]['source_ids'])
    def require_metric(key):
        if not numeric(key):
            raise ValueError(f'Entry/quality evidence requires verified numeric metric: {key}')
    for key,metric in metrics.items():
        if metric['value'] is not None and key not in ('exchange_price','nav'):
            expected_unit='multiple' if key=='underlying_pe' else 'ratio'
            if metric['unit'] != expected_unit:
                raise ValueError('Decision metric uses incompatible unit')
    if numeric('exchange_price') and numeric('nav') and metrics['exchange_price']['currency'] != metrics['nav']['currency']:
        raise ValueError('Price and NAV currencies differ')
    for key in ('exchange_price','nav'):
        if metrics[key]['value'] is not None and metrics[key]['value'] <= 0:
            raise ValueError('Price and NAV must be positive')
    for key in ('total_expense_ratio','tracking_error','annualized_volatility'):
        if metrics[key]['value'] is not None and metrics[key]['value'] < 0:
            raise ValueError('Expense/error/volatility cannot be negative')
    if metrics['maximum_drawdown']['value'] is not None and not -1 <= metrics['maximum_drawdown']['value'] <= 0:
        raise ValueError('Maximum drawdown must be a loss fraction')
    mapping = {'current_price':['exchange_price'],'historical_total_return':['historical_total_return'],
               'drawdown_and_volatility':['maximum_drawdown','annualized_volatility']}
    if proposal['asset_type']=='etf':
        mapping.update(total_cost=['total_expense_ratio'],nav_comparison=['nav'])
        if checklist['tracking_or_active_performance']['status']=='verified':
            require_metric('tracking_difference'); require_metric('tracking_error')
        if checklist['nav_comparison']['status']=='verified' and d['pricing_alignment']['status']!='aligned':
            raise ValueError('Unaligned price/NAV cannot support entry')
        if any(checklist[k]['status']=='not_applicable' for k in ['total_cost','current_price','nav_comparison','underlying_valuation']):
            raise ValueError('ETF cost, price, NAV and underlying value cannot be waived')
    if checklist['underlying_valuation']['status']=='verified' and not any(numeric(k) for k in ['underlying_pe','underlying_earnings_yield']):
        # Non-earnings assets need an explicit, sourced other-method record, not a fictitious PE.
        if not all(s['method']=='documented_other' and s['external_calculation']['status']=='checked' for s in d['return_scenarios']):
            raise ValueError('Underlying valuation needs metrics or checked appropriate alternative model')
    for evidence_key,keys in mapping.items():
        if checklist[evidence_key]['status']=='verified':
            for key in keys: require_metric(key)
    for scenario in d['return_scenarios']:
        if scenario['status']=='Not Assessed': continue
        if not scenario['horizon_years'] or not scenario['source_ids']:
            raise ValueError('Return scenarios need a horizon and sources')
        if ctx['horizon_years'] is not None and scenario['horizon_years'] != ctx['horizon_years']:
            raise ValueError('Return scenario horizon differs from investor horizon')
        if scenario['method']=='underlying_equity_v1':
            if d['underlying_asset_class']!='equity':
                raise ValueError('Equity return decomposition requires equity underlying assets')
            if numeric('underlying_pe') and not math.isclose(scenario['inputs']['starting_multiple'],metrics['underlying_pe']['value'],abs_tol=1e-8):
                raise ValueError('Starting multiple must match current underlying valuation')
            if scenario['formula'] != FORMULA or scenario['cost_basis'] != 'gross_before_fund_cost':
                raise ValueError('Wrong return formula or double-counted cost basis')
            notes = scenario['input_evidence']
            if len(notes)!=len(PARAMETERS) or {x['input_key'] for x in notes} != set(PARAMETERS):
                raise ValueError('Every return assumption needs its own rationale and sources')
            if proposal['asset_type']=='etf' and numeric('exchange_price') and numeric('nav') and d['pricing_alignment']['status']=='aligned':
                actual_premium=metrics['exchange_price']['value']/metrics['nav']['value']-1
                if not math.isclose(scenario['inputs']['entry_premium'],actual_premium,abs_tol=1e-8):
                    raise ValueError('Scenario entry premium does not match current price/NAV')
            expected = equity_etf_return(scenario['inputs'],scenario['horizon_years'])
            for key,value in expected.items():
                if scenario[key] is None or not math.isclose(scenario[key],value,abs_tol=1e-8,rel_tol=1e-8):
                    raise ValueError('Return/break-even scenario does not match reproducible inputs')
        else:
            record = scenario['external_calculation']
            if record['status']!='checked' or not record['formula'] or not record['inputs'] or not record['record']:
                raise ValueError('Other models need an explicit checked calculation record')
            total=(1+scenario['annualized_return'])**scenario['horizon_years']-1
            if not math.isclose(total,scenario['total_return'],abs_tol=1e-8,rel_tol=1e-8):
                raise ValueError('Scenario annualized and cumulative returns conflict')
    all_assessed = all(s['status']=='Assessed' for s in d['return_scenarios'])
    if checklist['forward_return_assumptions']['status']=='verified' and not all_assessed:
        raise ValueError('No assessed return scenarios despite verified forward-return checklist')
    if entry!='Insufficient Evidence' and (not all_assessed or d['downside_risk']['status']!='Assessed' or not d['comparable_alternatives']):
        raise ValueError('Entry assessment needs three return scenarios, downside and alternatives')
    if d['downside_risk']['status']=='Assessed' and not d['downside_risk']['source_ids']:
        raise ValueError('Assessed downside needs sources')
    if checklist['horizon_compatibility']['status']=='verified' and d['horizon_compatibility']['status']=='Not Assessed':
        raise ValueError('Horizon compatibility was not assessed')
    status=d['decision_status']
    fatal = d['asset_quality']['status']=='Fail' or d['portfolio_suitability']['status']=='Unsuitable'
    incomplete = d['asset_quality']['status']=='Insufficient Evidence' or entry=='Insufficient Evidence' or d['portfolio_suitability']['status']=='Not Assessed'
    if incomplete and not (status=='Avoid' and fatal) and status!='Insufficient Evidence':
        raise ValueError('Missing decision evidence must yield Insufficient Evidence')
    if status=='Invest Now' and entry!='Attractive':
        raise ValueError('Invest Now requires attractive entry evidence')
    if status=='Wait for Conditions' and entry not in ('Conditional','Unattractive'):
        raise ValueError('Waiting is an evidence-based condition, not a substitute for missing data')
    if status=='Avoid' and not fatal and entry!='Unattractive':
        raise ValueError('Avoid needs a documented failure/unattractive assessment')
    if status in ('Invest Now','Phased Entry','Wait for Conditions'):
        if d['asset_quality']['status']!='Pass' or d['portfolio_suitability']['status']!='Suitable':
            raise ValueError('Action recommendation needs quality and personal suitability')
        if proposal['research_stage']!='deep_research' or proposal['data_quality']['status']!='sufficient':
            raise ValueError('No invest/phase/wait recommendation from screening or insufficient data')
        review=d['adversarial_review']
        if not review['completed'] or not review['recommendation_supported'] or any(q['unresolved'] for q in review['questions'].values()):
            raise ValueError('Unresolved adversarial review must downgrade decision')
        if any(not c['source_ids'] for c in d['entry_reassessment_conditions']):
            raise ValueError('Action recommendation needs sourced reassessment conditions')
    if d['portfolio_suitability']['status']=='Not Assessed' and d['confidence']=='high':
        raise ValueError('Unassessed suitability cannot carry high decision confidence')
