"""Issue #1/#2 structured conversation and presentation acceptance; no LLM or market backtest."""
import copy
import json
import unittest
from jsonschema.exceptions import ValidationError
import test_research_handoff as prior
import test_investment_decision as decisions
from src import research_handoff as h
from src import research_interaction as ux
from src.investment_decision import blank_decision


class ResearchInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ResearchHandoffTests.setUpClass.__func__(cls)
        cls.fixture=h.decode(cls.read('tests/fixtures/research-interaction.mock.json'))

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    draft=prior.ResearchHandoffTests.draft

    def context(self,answers=None,**kwargs):
        return ux.prepare_context(self.fixture['known_answers'] if answers is None else answers,
            self.fixture['recorded_at'],read=self.read,**kwargs)

    def snapshot(self,context=None):
        context=context or self.context()
        rows=[]
        for instrument in self.fixture['candidate_instruments']:
            decision=blank_decision('MOCK: 缺當前價格／NAV、底層估值、風險序列與有據前瞻模型')
            months=context['conditions']['holding_period']['months']
            decision['investor_context']['horizon_years']=months/12 if months else None
            decision['recommended_next_action']='取得官方同日價格／NAV、費用／持股、含息風險與估值模型後重評，不配置資金'
            rows.append({'instrument':copy.deepcopy(instrument),'research_priority':{'level':'unranked','rationale':'MOCK 研究問題待核對，未作投資排名'},
                'research_stage':'screening','data_quality_status':'insufficient','investment_decision':decision,
                'core_reasons':[{'text':'MOCK：值得核對是否符合已記錄的元大 ETF／兩年持有條件','kind':'support','source_ids':[]},
                    {'text':'MOCK 反方：目前缺證據，無法支持現在買入','kind':'counterargument','source_ids':[]}],
                'entry_price':ux.unknown_price(),'return_basis':None,
                'risks':[{'text':'未取得可驗證曝險／回撤；不能判斷下行','window':None,'source_ids':[]}],
                'catalysts':[{'text':'待查公司／基金／產業公告，尚無可信催化劑','window':None,'source_ids':[]}],
                'alternatives':[{'text':'同目標替代及費用／曝險差異尚待核對','window':None,'source_ids':[]}],
                'key_missing_information':['同日價格／NAV','可重算兩年費後含息情境','完整持倉／風險承受／用款需求']})
        return {'schema_version':'1.0','artifact_type':'decision_snapshot','data_mode':'mock',
            'generated_at':'2026-10-19T18:00:00+08:00','data_cutoff':'2026-10-19T17:00:00+08:00',
            'research_context':context,'candidates':rows,'source_references':[],
            'deep_dive_offer':ux.deep_dive_offer(context)}

    def invalid(self,snapshot):
        with self.assertRaises((ValueError,ValidationError)):ux.validate_snapshot(snapshot,self.read)

    def test_unknown_five_conditions_collect_compact_form_before_screening(self):
        context=self.context({})
        plan=ux.question_plan(context,self.read)
        self.assertEqual(plan['mode'],'compact_form')
        self.assertEqual(set(plan['fields']),set(ux.FIELDS))
        self.assertEqual(context['screening_mode'],'awaiting_conditions')
        self.invalid(self.snapshot(context))
        text=ux.intake_text(context,self.read)
        self.assertIn('可部分填寫',text)
        self.assertNotIn('0050',text) # no fixed popular fund list during intake

    def test_known_yuanta_two_year_twenty_percent_high_risk_never_reasked(self):
        context=self.context()
        self.assertEqual(ux.question_plan(context,self.read),{'mode':'none','fields':[],'questions':[]})
        self.assertEqual(context['screening_mode'],'specified_screening')
        self.assertEqual(context['conditions'],self.fixture['known_answers'])

    def test_only_one_missing_condition_asks_one_question(self):
        answers=copy.deepcopy(self.fixture['known_answers']);del answers['entry_window']
        plan=ux.question_plan(self.context(answers),self.read)
        self.assertEqual(plan['mode'],'single');self.assertEqual(plan['fields'],['entry_window'])
        self.assertNotIn('可部分填寫',ux.intake_text(self.context(answers),self.read))

    def test_current_answer_merges_with_prior_conditions_without_reasking(self):
        answers=copy.deepcopy(self.fixture['known_answers']);answer=answers.pop('entry_window')
        earlier=self.context(answers)
        later=self.context({'entry_window':answer},previous=earlier)
        self.assertEqual(later['conditions'],self.fixture['known_answers'])
        self.assertEqual(ux.question_plan(later,self.read)['mode'],'none')
        self.assertEqual(earlier['conditions']['entry_window']['status'],'missing')

    def test_preferences_survive_followup_without_new_confirmation(self):
        earlier=self.context({},skip_questions=True,requested_depth='deep_dive')
        later=self.context({'entry_window':self.fixture['known_answers']['entry_window']},previous=earlier)
        self.assertTrue(later['skip_questions'])
        self.assertEqual(later['requested_depth'],'deep_dive')
        self.assertEqual(ux.question_plan(later,self.read)['mode'],'none')
        self.assertIsNone(ux.deep_dive_offer(later)['prompt'])

    def test_input_horizon_cannot_silently_replace_recorded_period(self):
        value=h.decode((h.ROOT/'tests/fixtures/company-research.input.json').read_bytes())
        value['research_context']=self.context();value['horizon_months']=60
        with self.assertRaises(ValueError):ux.validate_input(value,'company-research.input.schema.json',self.read)
        value['horizon_months']=24
        ux.validate_input(value,'company-research.input.schema.json',self.read)

    def test_no_return_target_is_valid_and_does_not_block(self):
        answers=copy.deepcopy(self.fixture['known_answers'])
        answers['return_target'].update(status='no_preference',text='無特定報酬目標')
        context=self.context(answers)
        self.assertEqual(context['screening_mode'],'specified_screening')
        self.assertEqual(ux.question_plan(context,self.read)['mode'],'none')
        ux.validate_snapshot(self.snapshot(context),self.read)

    def test_uncertain_answer_is_not_repeated_or_treated_as_user_target(self):
        answers=copy.deepcopy(self.fixture['known_answers'])
        answers['return_target'].update(status='uncertain',text='不確定報酬目標')
        context=self.context(answers)
        self.assertEqual(context['screening_mode'],'provisional_screening')
        self.assertEqual(ux.question_plan(context,self.read)['mode'],'none')

    def test_skip_questions_requires_provisional_not_invented_risk(self):
        context=self.context({},skip_questions=True)
        self.assertEqual(context['screening_mode'],'provisional_screening')
        self.assertEqual(ux.question_plan(context,self.read)['mode'],'none')
        snapshot=self.snapshot(context);ux.validate_snapshot(snapshot,self.read)
        for row in snapshot['candidates']:
            self.assertEqual(row['investment_decision']['portfolio_suitability']['status'],'Not Assessed')
            self.assertNotIn('allocation',row)
        self.assertEqual(context['conditions']['risk_preference']['status'],'missing')

    def test_only_material_missing_items_are_asked_and_exploration_is_explicit(self):
        answers=copy.deepcopy(self.fixture['known_answers'])
        answers['return_target']={'status':'missing','text':None,'origin':'unknown','source_ref':None,'material':False}
        context=self.context(answers)
        self.assertEqual(ux.question_plan(context,self.read)['mode'],'none')
        self.assertEqual(context['screening_mode'],'provisional_screening')
        explore=self.context({},exploratory_allowed=True)
        self.assertEqual(explore['screening_mode'],'provisional_screening')
        self.assertEqual(len(ux.question_plan(explore,self.read)['fields']),5)

    def test_assumption_must_not_be_relabeled_as_user_answer(self):
        answers=copy.deepcopy(self.fixture['known_answers'])
        answers['holding_period']={'status':'assumed','text':'暫以 24 個月探索','origin':'system_assumption','source_ref':None,'material':True,'months':24}
        context=self.context(answers)
        self.assertIn('本次假設：',ux.intake_text(context,self.read))
        answers['holding_period']['origin']='user'
        with self.assertRaises(ValidationError):self.context(answers)

    def test_unknown_field_and_forged_mode_rejected(self):
        with self.assertRaises(ValueError):self.context({'api_key':{}})
        answers=copy.deepcopy(self.fixture['known_answers']);answers['product_scope']['unexpected_key']='not permitted'
        with self.assertRaises(ValidationError):self.context(answers)
        context=self.context({},skip_questions=True);context['screening_mode']='specified_screening'
        with self.assertRaises(ValueError):ux.validate_context(context,self.read)

    def test_context_is_accepted_across_existing_inputs_outputs(self):
        for name in ['opportunity-screener.input','opportunity-screener.output','company-research.input','company-research.output']:
            value=h.decode((h.ROOT/'tests/fixtures'/(name+'.json')).read_bytes())
            value['research_context']=self.context()
            if '.input' in name:
                value['horizon_months']=24
                ux.validate_input(value,name+'.schema.json',self.read)
            else:h.schema_validator(self.read,name+'.schema.json').validate(value)

    def test_unquantified_horizon_requires_context_instead_of_fabricated_months(self):
        for name in ['opportunity-screener.input','company-research.input']:
            value=h.decode((h.ROOT/'tests/fixtures'/(name+'.json')).read_bytes());value['horizon_months']=None
            with self.assertRaises(ValidationError):h.schema_validator(self.read,name+'.schema.json').validate(value)
            value['research_context']=self.context({},skip_questions=True)
            h.schema_validator(self.read,name+'.schema.json').validate(value)

    def test_context_survives_conversion_to_unapproved_proposal(self):
        research=h.decode(self.read('tests/fixtures/company-research.output.json'));context=self.context()
        research['research_context']=context
        proposal=h.proposal_from_research(research,self.sha,self.read,self.manifest,'MOCK.md',data_mode='mock')
        self.assertEqual(proposal['research_context'],context)
        proposal['research_context']['conditions']['product_scope']['text']='Changed'
        self.assertEqual(research['research_context'],context) # no shared mutable state
        proposal['research_context']=context
        h.validate_proposal(proposal,self.sha,self.read,self.manifest)
        self.assertEqual(proposal['proposal_status'],'needs_information')
        self.assertIsNone(proposal['investment_decision']['market_metrics']['exchange_price']['value'])
        self.assertEqual(proposal['investment_decision']['decision_status'],'Insufficient Evidence')
        proposal['research_context']['recorded_at']='2099-01-01T00:00:00Z'
        with self.assertRaises(ValueError):h.validate_proposal(proposal,self.sha,self.read,self.manifest)

    def test_four_etf_regression_has_eight_columns_and_no_fake_forecast(self):
        snapshot=self.snapshot();result=ux.validate_snapshot(snapshot,self.read)
        self.assertFalse(result['deep_research_validated'])
        self.assertEqual([x['instrument']['ticker'] for x in snapshot['candidates']],['0050','00762','00965','009820'])
        text=ux.render_snapshot(snapshot,self.read)
        header=next(x for x in text.splitlines() if x.startswith('| 商品'))
        self.assertEqual(len(header.split('|')[1:-1]),8)
        self.assertEqual(text.count('未能可靠估計'),4)
        self.assertEqual(text.count('尚無可信估計'),4)
        self.assertIn('下一步：',text);self.assertIn('反方',text)
        self.assertIn('全部或指定哪些標的',text);self.assertIn('MOCK ONLY',text)
        self.assertNotIn('## 14.',text) # default is not a long Memo
        for row in snapshot['candidates']:
            self.assertIsNone(row['entry_price']['low'])
            self.assertTrue(all(s['total_return'] is None for s in row['investment_decision']['return_scenarios']))

    def test_explicit_deep_dive_no_reconfirmation(self):
        context=self.context(requested_depth='deep_dive');snapshot=self.snapshot(context)
        self.assertEqual(snapshot['deep_dive_offer'],{'mode':'already_requested','prompt':None})
        self.assertNotIn('全部或指定哪些標的',ux.render_snapshot(snapshot,self.read))
        snapshot['deep_dive_offer']={'mode':'ask_selection','prompt':'需要詳細版？'}
        self.invalid(snapshot)

    def test_default_snapshot_requires_deep_dive_offer(self):
        snapshot=self.snapshot();snapshot['deep_dive_offer']={'mode':'already_requested','prompt':None}
        self.invalid(snapshot)

    def test_missing_summary_fields_not_silent_blanks(self):
        for field in ['instrument','research_priority','core_reasons','entry_price','return_basis','risks','catalysts','alternatives','key_missing_information']:
            snapshot=self.snapshot();del snapshot['candidates'][0][field];self.invalid(snapshot)
        for field in ['risks','catalysts','alternatives','key_missing_information']:
            snapshot=self.snapshot();snapshot['candidates'][0][field]=[];self.invalid(snapshot)

    def test_reasons_require_counterargument_and_at_most_three(self):
        snapshot=self.snapshot();snapshot['candidates'][0]['core_reasons'][1]['kind']='support';self.invalid(snapshot)
        snapshot=self.snapshot();snapshot['candidates'][0]['core_reasons']*=2;self.invalid(snapshot)

    def test_unknown_price_cannot_smuggle_numbers_or_verified_claim(self):
        for key,value in [('low',95),('calculation_verified',True),('message','等回檔 5% 就是合理價')]:
            snapshot=self.snapshot();snapshot['candidates'][0]['entry_price'][key]=value;self.invalid(snapshot)

    def price_snapshot(self):
        snapshot=self.snapshot()
        snapshot['source_references']=[{'source_id':'mock-model','provider':'SYNTHETIC ONLY',
            'locator':'synthetic://not-real-valuation','data_period':'MOCK',
            'published_at':None,'published_date':'2026-10-19','time_precision':'date',
            'retrieved_at':'2026-10-19T16:30:00+08:00','retrieval':'user_provided','confidence':'low'}]
        snapshot['candidates'][0]['entry_price'].update(status='verified_estimate',low=90,high=100,
            as_of='2026-10-19',method='SYNTHETIC valuation identity test',formula='MOCK earnings 5 * multiple [18,20]',
            assumptions=['SYNTHETIC earnings and multiples; no investment validity'],source_ids=['mock-model'],
            calculation_verified=True,message='MOCK range only')
        return snapshot

    def test_estimated_price_requires_dated_recomputable_evidence(self):
        ux.validate_snapshot(self.price_snapshot(),self.read)
        for field,value in [('formula',None),('assumptions',[]),('source_ids',[]),('calculation_verified',False),('as_of',None)]:
            snapshot=self.price_snapshot();snapshot['candidates'][0]['entry_price'][field]=value;self.invalid(snapshot)
        text=ux.render_snapshot(self.price_snapshot(),self.read)
        for required in ['2026-10-19','mock-model','earnings 5','SYNTHETIC']:
            self.assertIn(required,text)

    def test_price_order_currency_future_date_rejected(self):
        for field,value in [('low',101),('currency','USD'),('as_of','2099-01-01')]:
            snapshot=self.price_snapshot();snapshot['candidates'][0]['entry_price'][field]=value;self.invalid(snapshot)

    def test_duplicate_asset_unknown_source_and_future_references_rejected(self):
        snapshot=self.snapshot();snapshot['candidates'].append(snapshot['candidates'][0]);self.invalid(snapshot)
        snapshot=self.price_snapshot();snapshot['candidates'][0]['entry_price']['source_ids']=['missing'];self.invalid(snapshot)
        for field in ['published_date','retrieved_at']:
            snapshot=self.price_snapshot();snapshot['source_references'][0][field]='2099-01-01' if field=='published_date' else '2099-01-01T00:00:00Z';self.invalid(snapshot)

    def test_short_output_cannot_bypass_existing_decision_gates(self):
        for status in ['Invest Now','Phased Entry','Wait for Conditions','Avoid']:
            snapshot=self.snapshot();snapshot['candidates'][0]['investment_decision']['decision_status']=status
            self.invalid(snapshot)

    def test_assessed_returns_reuse_existing_model_and_require_basis(self):
        proposal=decisions.DecisionSupportTests.complete(self)
        answers=copy.deepcopy(self.fixture['known_answers'])
        answers['holding_period'].update(text='MOCK 持有五年',months=60)
        snapshot=self.snapshot(self.context(answers,requested_depth='deep_dive'))
        snapshot['source_references']=proposal['source_references']
        snapshot['candidates']=snapshot['candidates'][:1]
        row=snapshot['candidates'][0]
        row.update(research_stage='deep_research',data_quality_status='sufficient',investment_decision=proposal['investment_decision'],
            return_basis='MOCK 五年累積含息再投資、基金費用與進出成本扣一次、TWD／fx=0 為假設，非承諾')
        ux.validate_snapshot(snapshot,self.read)
        text=ux.render_snapshot(snapshot,self.read)
        self.assertIn('5年累積含息',text);self.assertIn('mock-source',text)
        self.assertIn('fx=0',text)
        row['return_basis']=None;self.invalid(snapshot)
        row['return_basis']='MOCK'
        snapshot['research_context']['conditions']['holding_period']['months']=24
        self.invalid(snapshot)
        snapshot['research_context']['conditions']['holding_period']['months']=60
        row['return_basis']='MOCK';row['investment_decision']['return_scenarios'][0]['total_return']+=.01
        self.invalid(snapshot) # no independently invented return figure in a short summary


if __name__=='__main__':unittest.main()
