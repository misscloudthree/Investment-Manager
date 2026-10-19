"""Task 2.1 mock acceptance and financial identities, NOT live ETF recommendations."""
import copy
import unittest
from jsonschema.exceptions import ValidationError

import test_research_handoff as prior
from src import investment_decision as d
from examples import etf_decision_acceptance as acceptance


class DecisionSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ResearchHandoffTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    draft=prior.ResearchHandoffTests.draft
    validate=prior.ResearchHandoffTests.validate
    invalid=prior.ResearchHandoffTests.invalid

    def complete(self):
        p=prior.ResearchHandoffTests.complete_mock(self,'etf')
        p['proposal_status']='ready_for_review'
        decision=d.blank_decision('SYNTHETIC decision test only')
        decision['investor_context'].update(capital_twd=1000000,horizon_years=5,
            holdings_status='provided',risk_profile_status='provided',liquidity_needs_status='provided',
            portfolio_snapshot_ref='synthetic://confirmed-holdings',risk_profile_ref='synthetic://confirmed-risk-profile')
        for gate,status in [('asset_quality','Pass'),('entry_attractiveness','Attractive'),('portfolio_suitability','Suitable')]:
            decision[gate].update(status=status,rationale='SYNTHETIC documented test',source_ids=['mock-source'])
        decision['decision_status']='Invest Now'
        decision['underlying_asset_class']='equity'
        decision['confidence']='medium'
        for evidence in decision['evidence_checklist'].values():
            evidence.update(status='verified',source_ids=['mock-source'],rationale='SYNTHETIC evidence, not real data')
        decision['evidence_coverage'].update(verified_items=13,ratio=1)
        values={'exchange_price':100,'nav':100,'total_expense_ratio':0.004,'historical_total_return':0.2,
                'tracking_difference':-0.004,'tracking_error':0.002,'maximum_drawdown':-0.3,
                'annualized_volatility':0.18,'underlying_pe':20,'underlying_earnings_yield':0.05}
        for key,value in values.items():
            decision['market_metrics'][key].update(value=value,classification='verified_fact',quality='verified',source_ids=['mock-source'],period='SYNTHETIC')
        decision['pricing_alignment'].update(status='aligned',source_ids=['mock-source'],rationale='SYNTHETIC same time and currency')
        for scenario,growth,terminal in zip(decision['return_scenarios'],[0.08,0.04,-0.02],[24,20,14]):
            inputs=dict(earnings_growth=growth,starting_multiple=20,terminal_multiple=terminal,
                        dividend_return=0.02,annual_cost=0.004,fx_return=0,entry_premium=0,exit_premium=0,round_trip_cost=0.002)
            scenario.update(status='Assessed',method='underlying_equity_v1',horizon_years=5,inputs=inputs,
                input_evidence=[dict(input_key=k,source_ids=['mock-source'],rationale='SYNTHETIC assumption only') for k in d.PARAMETERS],
                formula=d.FORMULA,cost_basis='gross_before_fund_cost',source_ids=['mock-source'],
                limitations=['SYNTHETIC only; no predictive validity'],**d.equity_etf_return(inputs,5))
        decision['downside_risk'].update(status='Assessed',source_ids=['mock-source'],
            loss_fraction=decision['return_scenarios'][2]['total_return'],description='SYNTHETIC multiple/earnings stress; not maximum possible loss')
        decision['comparable_alternatives']=[dict(asset_id='synthetic:peer',comparison='SYNTHETIC same-objective peer',
            verified_total_expense=copy.deepcopy(decision['market_metrics']['total_expense_ratio']),source_ids=['mock-source'],limitations=['MOCK ONLY'])]
        decision['horizon_compatibility'].update(status='Compatible',source_ids=['mock-source'],rationale='SYNTHETIC five-year user mandate and loss tolerance')
        for key in ['entry_reassessment_conditions','key_evidence_that_could_change_decision']:
            decision[key][0].update(source_ids=['mock-source'],linked_kpi_ids=['kpi-1'],evidence_needed='SYNTHETIC KPI document')
        decision['adversarial_review'].update(completed=True,recommendation_supported=True)
        for q in decision['adversarial_review']['questions'].values():
            q.update(answer='SYNTHETIC documented challenge and response; not real advice',source_ids=['mock-source'],unresolved=False)
        p['investment_decision']=decision
        return p

    def test_three_target_etfs_with_one_million_and_missing_profile(self):
        proposals=acceptance.mock_proposals(self.sha,self.read,self.manifest)
        self.assertEqual([p['asset_id'] for p in proposals],['TWSE:0050','TWSE:00646','TWSE:00713'])
        for p in proposals:
            self.validate(p)
            x=p['investment_decision']
            self.assertEqual(p['data_mode'],'mock')
            self.assertEqual(x['investor_context']['capital_twd'],1000000)
            self.assertEqual(x['investor_context']['horizon_years'],5)
            self.assertEqual(x['asset_quality']['status'],'Pass') # Only mock product documents.
            self.assertEqual(x['entry_attractiveness']['status'],'Insufficient Evidence')
            self.assertEqual(x['portfolio_suitability']['status'],'Not Assessed')
            self.assertEqual(x['decision_status'],'Insufficient Evidence')
            self.assertEqual(p['research_priority']['level'],'unranked')
            self.assertIsNone(x['market_metrics']['exchange_price']['value'])
            self.assertIsNone(x['market_metrics']['nav']['value'])
            for scenario in x['return_scenarios']:
                for key in ['annualized_return','total_return','break_even_terminal_multiple']:
                    self.assertIsNone(scenario[key])
                self.assertTrue(all(value is None for value in scenario['inputs'].values()))
        report=acceptance.report(proposals)
        self.assertIn('非真實 ETF 投資建議',report)
        self.assertIn('目前不能判斷三者誰現在較值得投資',report)
        self.assertIn('不配置這 100 萬元',report)
        self.assertEqual(len({p['research_priority']['rationale'] for p in proposals}),3)

    def test_bundle_acceptance_does_not_claim_authenticated_git_access(self):
        from src import research_handoff as h
        sha,read,manifest=h.bundle_materials(self.bundle)
        proposals=acceptance.mock_proposals(sha,read,manifest,'bundle_hashes')
        for p in proposals:
            self.assertEqual(p['methodology_receipt']['verification_method'],'bundle_hashes')
            self.assertEqual(p['methodology_receipt']['origin_authentication'],'not_verified')
            h.validate_proposal(p,sha,read,manifest)

    def test_quality_pass_does_not_permit_buy_or_phase_or_fake_wait(self):
        for status in ['Invest Now','Phased Entry','Wait for Conditions']:
            p=acceptance.mock_proposals(self.sha,self.read,self.manifest)[0]
            p['investment_decision']['decision_status']=status
            self.invalid(p)

    def test_supported_invest_and_phased_entry_are_research_only(self):
        p=self.complete()
        self.assertEqual(self.validate(p)['approval'],'not_granted')
        p['investment_decision']['decision_status']='Phased Entry'
        p['investment_decision']['entry_attractiveness']['status']='Conditional'
        self.validate(p)
        self.assertNotEqual(p['proposal_status'],'approved')

    def test_supported_wait_has_conditions_not_missing_evidence(self):
        p=self.complete()
        p['investment_decision']['decision_status']='Wait for Conditions'
        p['investment_decision']['entry_attractiveness']['status']='Conditional'
        self.validate(p)
        p['investment_decision']['entry_reassessment_conditions']=[]
        self.invalid(p)

    def test_evidence_based_avoid_does_not_need_fabricated_returns(self):
        p=acceptance.mock_proposals(self.sha,self.read,self.manifest)[0]
        p['investment_decision']['asset_quality']['status']='Fail'
        p['investment_decision']['asset_quality']['rationale']='SYNTHETIC documented structural defect'
        p['investment_decision']['decision_status']='Avoid'
        self.validate(p)

    def test_missing_investor_data_cannot_be_suitable(self):
        for key in ['holdings_status','risk_profile_status','liquidity_needs_status']:
            p=self.complete()
            p['investment_decision']['investor_context'][key]='missing'
            self.invalid(p)

    def test_no_personal_data_even_with_attractive_entry_requires_insufficient(self):
        p=self.complete()
        p['proposal_status']='needs_information'
        p['investment_decision']['investor_context']['holdings_status']='missing'
        p['investment_decision']['portfolio_suitability']['status']='Not Assessed'
        p['investment_decision']['decision_status']='Insufficient Evidence'
        self.validate(p)
        p['investment_decision']['decision_status']='Invest Now'
        self.invalid(p)

    def test_missing_price_or_conflicting_inputs_prevents_entry(self):
        for status in ['missing','conflicting']:
            p=self.complete()
            p['investment_decision']['evidence_checklist']['current_price']['status']=status
            self.invalid(p)
        p=self.complete()
        p['investment_decision']['market_metrics']['exchange_price']=d.unknown_metric('exchange_price')
        self.invalid(p)

    def test_forecast_and_break_even_are_recomputed(self):
        for key in ['total_return','annualized_return','break_even_terminal_multiple']:
            p=self.complete()
            p['investment_decision']['return_scenarios'][0][key]+=0.01
            self.invalid(p)

    def test_missing_assumption_sources_or_doubled_fee_basis_rejected(self):
        for field,value in [('input_evidence',[]),('cost_basis','documented_other')]:
            p=self.complete()
            p['investment_decision']['return_scenarios'][0][field]=value
            self.invalid(p)

    def test_wrong_underlying_class_and_multiple_anchor_rejected(self):
        for asset_class in ['bond','commodity','unknown']:
            p=self.complete()
            p['investment_decision']['underlying_asset_class']=asset_class
            self.invalid(p)
        p=self.complete()
        p['investment_decision']['market_metrics']['underlying_pe']['value']=15
        self.invalid(p)

    def test_premium_anchor_and_currency_must_match(self):
        p=self.complete()
        p['investment_decision']['market_metrics']['nav']['value']=90
        self.invalid(p)
        p=self.complete()
        p['investment_decision']['market_metrics']['nav']['currency']='USD'
        self.invalid(p)

    def test_unaligned_nav_and_percent_units_rejected(self):
        p=self.complete()
        p['investment_decision']['pricing_alignment']['status']='unaligned'
        self.invalid(p)
        p=self.complete()
        p['investment_decision']['market_metrics']['annualized_volatility']['unit']='percent'
        self.invalid(p)

    def test_history_does_not_replace_forward_or_downside_evidence(self):
        for key in ['forward_return_assumptions','downside_risk']:
            p=self.complete()
            p['investment_decision']['evidence_checklist'][key]['status']='missing'
            self.invalid(p)
        p=self.complete()
        p['investment_decision']['return_scenarios'][0]=d.blank_decision()['return_scenarios'][0]
        self.invalid(p)

    def test_unresolved_adversarial_review_blocks_positive_recommendation(self):
        p=self.complete()
        p['investment_decision']['adversarial_review']['questions']['flip_assumption']['unresolved']=True
        self.invalid(p)
        p=self.complete()
        del p['investment_decision']['adversarial_review']['questions']['history_not_promise']
        self.invalid(p)

    def test_gate_fail_cannot_be_averaged_out(self):
        p=self.complete()
        p['investment_decision']['asset_quality']['status']='Fail'
        self.invalid(p)

    def test_coverage_cannot_hide_missing_data_or_waive_price(self):
        p=self.complete()
        p['investment_decision']['evidence_coverage']['ratio']=0.5
        self.invalid(p)
        p=self.complete()
        p['investment_decision']['evidence_checklist']['current_price']['status']='not_applicable'
        p['investment_decision']['evidence_coverage'].update(required_items=12,verified_items=12,ratio=1)
        self.invalid(p)

    def test_wrong_schema_version_and_missing_decision_rejected(self):
        p=self.complete()
        p['schema_version']='1.0'
        self.invalid(p)
        p=self.complete()
        del p['investment_decision']
        self.invalid(p)

    def test_future_monitor_links_cannot_dangle(self):
        p=self.complete()
        p['investment_decision']['entry_reassessment_conditions'][0]['linked_kpi_ids']=['unknown']
        self.invalid(p)


class OfflineFinancialIdentities(unittest.TestCase):
    def inputs(self):
        return dict(earnings_growth=0,starting_multiple=20,terminal_multiple=20,dividend_return=0,
                    annual_cost=0,fx_return=0,entry_premium=0,exit_premium=0,round_trip_cost=0)

    def test_flat_factors_have_zero_total_return(self):
        self.assertEqual(d.equity_etf_return(self.inputs(),5),dict(total_return=0,annualized_return=0,break_even_terminal_multiple=20))

    def test_multiple_compression_and_break_even_identity(self):
        v=self.inputs();v['terminal_multiple']=10
        self.assertAlmostEqual(d.equity_etf_return(v,5)['total_return'],-0.5)
        v.update(earnings_growth=.04,dividend_return=.02,annual_cost=.004,fx_return=-.01,
                 entry_premium=.01,exit_premium=0,round_trip_cost=.002)
        result=d.equity_etf_return(v,5)
        v['terminal_multiple']=result['break_even_terminal_multiple']
        self.assertAlmostEqual(d.equity_etf_return(v,5)['total_return'],0,places=12)

    def test_fees_and_entry_premium_reduce_return(self):
        v=self.inputs();v['annual_cost']=.01
        self.assertAlmostEqual(d.equity_etf_return(v,5)['total_return'],.99**5-1)
        v=self.inputs();v['entry_premium']=.1
        self.assertAlmostEqual(d.equity_etf_return(v,5)['total_return'],1/1.1-1)

    def test_invalid_financial_domains_rejected(self):
        for key,value in [('earnings_growth',-1),('starting_multiple',0),('terminal_multiple',-1),
                          ('annual_cost',1),('fx_return',None),('dividend_return',True)]:
            v=self.inputs();v[key]=value
            with self.assertRaises(ValueError):d.equity_etf_return(v,5)
        with self.assertRaises(ValueError):d.equity_etf_return(self.inputs(),0)

    def test_total_return_drawdown_and_sample_volatility(self):
        result=d.historical_risk([100,120,90,108],12)
        self.assertAlmostEqual(result['total_return'],.08)
        self.assertAlmostEqual(result['maximum_drawdown'],-.25)
        self.assertGreater(result['annualized_volatility'],0)
        with self.assertRaises(ValueError):d.historical_risk([100,0,10],12)

    def test_tracking_difference_and_error_are_distinct(self):
        result=d.tracking_statistics([.01,.01,.01],[.02,.02,.02],12)
        self.assertAlmostEqual(result['tracking_difference'],1.01**12-1.02**12)
        self.assertAlmostEqual(result['tracking_error'],0)
        with self.assertRaises(ValueError):d.tracking_statistics([.01],[.01,.02],12)
