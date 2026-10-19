"""Task 2.2 batch/provenance acceptance, strictly synthetic and offline."""
import copy
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
from jsonschema.exceptions import ValidationError
import test_research_handoff as prior
from examples.batch_research_acceptance import mock_snapshot
from src import batch_research as b
from src import market_snapshot as ms
from src import research_handoff as h
from src import research_interaction as ux


def rehash(snapshot):
    snapshot.pop('snapshot_id',None);snapshot['snapshot_id']=ms.sha(snapshot)
    return snapshot


class BatchResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ResearchHandoffTests.setUpClass.__func__(cls)
        cls.method=b.method_context(cls.repo)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.run=Path(self.folder.name)/'run'
        self.snapshot=mock_snapshot()
        self.policy={**b.DEFAULT_POLICY,'as_of':self.snapshot['captured_at']}

    def init(self,**kwargs):return b.initialize(self.snapshot,self.run,self.policy,self.method,**kwargs)
    def finish(self):return b.process(self.run,1000)

    def test_120_assets_resumable_coverage_and_no_premature_ranking(self):
        self.init();first=b.process(self.run,17)
        self.assertEqual(first['coverage']['pending'],103)
        self.assertEqual(first['ranking'],[]);self.assertEqual(first['deep_research_queue'],[])
        self.assertFalse((self.run/'DECISION_SNAPSHOT.md').exists())
        report=first
        while report['coverage']['pending']:report=b.process(self.run,17)
        c=report['coverage']
        self.assertEqual({k:c[k] for k in ['declared_count','evaluated','excluded','needs_data','failed','ranked_count']},
            dict(declared_count=120,evaluated=116,excluded=1,needs_data=3,failed=0,ranked_count=115))
        self.assertEqual(len(report['items']),120)
        self.assertEqual(len(report['deep_research_queue']),5)
        self.assertEqual(len(report['deferred_groups']),1)
        self.assertFalse(c['research_complete']);self.assertFalse(report['research_artifacts_complete'])
        self.assertEqual(b.process(self.run,17)['ranking'],report['ranking'])
        self.assertTrue(all(row['attempts']==1 for row in report['items']))
        self.assertEqual(len((self.run/'ledger.csv').read_text().splitlines()),121)
        preview=h.decode((self.run/'decision-snapshot.json').read_bytes())
        ux.validate_snapshot(preview,self.read)
        for row in preview['candidates']:
            self.assertEqual(row['investment_decision']['decision_status'],'Insufficient Evidence')
            self.assertIsNone(row['entry_price']['low'])
        self.assertIn('全部或指定哪些標的',(self.run/'DECISION_SNAPSHOT.md').read_text())

    def test_batched_matches_single_pass_without_reprocessing(self):
        self.init();report=self.finish()
        other=Path(self.folder.name)/'other'
        b.initialize(self.snapshot,other,self.policy,self.method)
        for _ in range(8):batched=b.process(other,17)
        self.assertEqual(report['ranking'],batched['ranking'])
        self.assertEqual(report['deep_research_queue'],batched['deep_research_queue'])
        self.assertEqual(report['campaign_id'],batched['campaign_id'])

    def test_crash_keeps_prior_atomic_transitions_then_resumes(self):
        self.init();calls=0
        def interrupted(item,policy):
            nonlocal calls
            calls+=1
            if calls==5:raise KeyboardInterrupt('simulated process interruption')
            return b.stage1(item,policy)
        with self.assertRaises(KeyboardInterrupt):b.process(self.run,100,evaluator=interrupted)
        partial=b.export(self.run)
        self.assertEqual(partial['coverage']['pending'],116)
        final=self.finish()
        self.assertEqual(final['coverage']['pending'],0)
        self.assertTrue(all(x['attempts']==1 for x in final['items']))

    def test_failure_is_visible_until_explicit_retry(self):
        self.init()
        def broken(item,policy):
            if item['asset_id']=='TWSE:M0010':raise ValueError('MOCK adapter failure')
            return b.stage1(item,policy)
        report=b.process(self.run,1000,evaluator=broken)
        self.assertEqual(report['coverage']['failed'],1)
        row=next(x for x in report['items'] if x['asset_id']=='TWSE:M0010')
        self.assertIn('MOCK adapter failure',row['details']['reasons'][0])
        self.assertEqual(self.finish()['coverage']['failed'],1)
        fixed=b.process(self.run,1000,retry_failed=True)
        self.assertEqual(fixed['coverage']['failed'],0)
        self.assertEqual(next(x for x in fixed['items'] if x['asset_id']=='TWSE:M0010')['attempts'],2)
        actual={p.stem for p in (self.run/'queue').glob('*.json')}
        self.assertEqual(actual,{x.replace(':','-') for x in fixed['deep_research_queue']})

    def test_metadata_universe_and_engine_cannot_silently_change(self):
        self.init()
        with self.assertRaisesRegex(ValueError,'exists'):self.init()
        with patch.object(b,'engine_fingerprint',return_value='0'*64):
            with self.assertRaisesRegex(ValueError,'Engine changed'):self.finish()
        with b.connect(self.run) as db:
            db.execute("DELETE FROM assets WHERE asset_id='TWSE:M0010'")
        with self.assertRaisesRegex(ValueError,'universe'):self.finish()

    def test_pinned_methodology_cannot_silently_switch_to_another_manifest(self):
        wrong=copy.deepcopy(self.method);wrong['manifest_sha256']='0'*64
        b.initialize(self.snapshot,self.run,self.policy,wrong)
        with self.assertRaisesRegex(ValueError,'Methodology changed'):self.finish()

    def test_policy_and_snapshot_integrity_rejected(self):
        self.snapshot['instruments'][10]['metrics']['pe']['value']=1
        with self.assertRaisesRegex(ValueError,'integrity'):self.init()
        self.snapshot=mock_snapshot();self.policy['minimum_peers']=4
        with self.assertRaises((ValueError,ValidationError)):self.init()
        self.policy={**b.DEFAULT_POLICY,'as_of':self.snapshot['captured_at'],'profiles':['stock_basic_v1','stock_five_factor_v1']}
        with self.assertRaisesRegex(ValueError,'one profile'):self.init()

    def test_no_cross_group_or_cross_date_ranking_and_negative_pe_stays_null(self):
        self.snapshot['instruments'][10]['metrics']['pe']['unit']='ratio'
        self.snapshot['instruments'][11]['metrics']['pe']['as_of']='2026-10-18'
        for key in ['close','turnover_twd','pe','pb']:
            self.snapshot['instruments'][12]['metrics'][key]['as_of']='2026-10-18'
        rehash(self.snapshot);self.init();report=self.finish()
        rows={x['asset_id']:x for x in report['ranking']}
        for ticker in ['M0002','M0010','M0011','M0012']:self.assertIsNone(rows['TWSE:'+ticker]['score'])
        for row in report['ranking']:
            if row['score'] is not None:
                self.assertTrue(0<=row['score']<=10)
                self.assertTrue(all(n>=5 for n in row['peer_counts'].values()))
                self.assertTrue(row['peer_evidence'])
        for asset_id in report['deep_research_queue']:
            self.assertLessEqual(rows[asset_id]['rank'],self.policy['shortlist_per_group'])

    def test_small_comparison_groups_do_not_force_ranking(self):
        self.snapshot['instruments']=self.snapshot['instruments'][25:29]
        rehash(self.snapshot);self.init();report=self.finish()
        self.assertEqual(report['coverage']['evaluated'],4)
        self.assertTrue(all(row['score'] is None for row in report['ranking']))
        self.assertEqual(report['status'],'blocked_no_comparable_candidates')

    def test_zero_deep_budget_retains_comparison_without_false_no_candidate_claim(self):
        self.policy['deep_research_limit']=0;self.init();report=self.finish()
        self.assertGreater(report['coverage']['ranked_count'],100)
        self.assertEqual(report['status'],'screening_complete_no_deep_budget')
        self.assertEqual(report['deep_research_queue'],[])

    def test_unsupported_etf_and_misaligned_quotes_keep_explicit_gaps(self):
        for index in [101,102]:self.snapshot['instruments'][index]['underlying_asset_class']='bond'
        self.snapshot['instruments'][15]['metrics']['turnover_twd']['as_of']='2026-10-18'
        rehash(self.snapshot);self.init();report=self.finish()
        statuses={x['asset_id']:x for x in report['items']}
        for ticker in ['E0101','E0102','M0015']:
            row=statuses['TWSE:'+ticker]
            self.assertEqual(row['status'],'needs_data');self.assertTrue(row['details']['gaps'])

    def test_full_five_factor_requires_comparable_model_and_all_dimensions(self):
        self.snapshot['instruments']=self.snapshot['instruments'][25:35]
        for n,item in enumerate(self.snapshot['instruments']):
            item['fundamental_model']='non_financial'
            for dim in b.PROFILES['stock_five_factor_v1']['dimensions'].values():
                for key in dim:
                    item['metrics'][key]={'value':(n+1)/10,'unit':b.UNITS.get(key,'ratio'),'as_of':'2026-10-19','source_id':'mock-bulk'}
        self.snapshot['instruments'][0]['fundamental_model']='financial'
        del self.snapshot['instruments'][1]['metrics']['roic']
        del self.snapshot['instruments'][1]['metrics']['roe']
        rehash(self.snapshot);self.policy['profiles']=['stock_five_factor_v1'];self.init();report=self.finish()
        self.assertEqual(report['coverage']['needs_data'],1)
        rows={x['asset_id']:x for x in report['ranking']}
        self.assertIsNone(rows['TWSE:M0026']['score'])
        self.assertIsNotNone(rows['TWSE:M0027']['score'])
        self.assertEqual(set(rows['TWSE:M0027']['dimension_scores']),{'valuation','quality','momentum','sentiment','growth'})

    def test_context_passes_through_summary_packet_and_unapproved_submission(self):
        fixture=h.decode(self.read('tests/fixtures/research-interaction.mock.json'))
        context=ux.prepare_context(fixture['known_answers'],fixture['recorded_at'],requested_depth='deep_dive',read=self.read)
        self.policy['deep_research_limit']=1;self.init(research_context=context);report=self.finish()
        self.assertEqual(report['research_context'],context)
        asset_id=report['deep_research_queue'][0]
        packet=h.decode((self.run/'queue'/(asset_id.replace(':','-')+'.json')).read_bytes())
        self.assertEqual(packet['research_context'],context)
        self.assertNotIn('全部或指定哪些標的',(self.run/'DECISION_SNAPSHOT.md').read_text())
        item=next(x for x in self.snapshot['instruments'] if x['asset_id']==asset_id)
        name='company-research.output.json' if item['asset_type']=='etf' else 'company-research.stock.output.json'
        worksheet=h.decode(self.read('tests/fixtures/'+name))
        worksheet['instrument']={k:item[k] for k in ['ticker','name','market','asset_type','currency']}
        worksheet['meta']['as_of']=self.policy['as_of'];worksheet['research_context']=context
        proposal=h.proposal_from_research(worksheet,self.sha,self.read,self.manifest,'MOCK.md',data_mode='mock')
        memo='# MOCK ONLY '+asset_id+'\n'+''.join(f'\n## {n}. MOCK\n未完成實際市場研究。\n' for n in range(1,15))
        self.assertEqual(b.submit(self.run,asset_id,proposal,memo,self.read,self.manifest),1)
        self.assertEqual(b.submit(self.run,asset_id,proposal,memo,self.read,self.manifest),1)
        self.assertEqual(b.submit(self.run,asset_id,proposal,memo+'\n新增 MOCK 註解',self.read,self.manifest),2)
        final=b.export(self.run)
        self.assertEqual(final['status'],'ready_for_synthesis_not_approved')
        self.assertFalse(final['coverage']['research_complete'])
        self.assertEqual(len(list((self.run/'drafts'/asset_id.replace(':','-')).glob('*.json'))),2)
        for field,value in [('data_mode','public_sources'),('data_cutoff','2026-10-18T16:00:00+08:00'),('research_context',{})]:
            invalid=copy.deepcopy(proposal);invalid[field]=value
            with self.assertRaises(ValueError):b.submit(self.run,asset_id,invalid,memo,self.read,self.manifest)
        with self.assertRaises(ValueError):b.submit(self.run,'TWSE:NOTQUEUED',proposal,memo,self.read,self.manifest)
        with self.assertRaises(ValueError):b.submit(self.run,asset_id,proposal,'short invalid memo',self.read,self.manifest)

    def test_unresolved_context_cannot_be_presented_as_user_confirmed(self):
        context=ux.prepare_context({},self.snapshot['captured_at'],read=self.read)
        with self.assertRaisesRegex(ValueError,'material conditions'):self.init(research_context=context)


class OfficialSnapshotAdapterTests(unittest.TestCase):
    def raws(self):
        return {'master':ms.encode([{'公司代號':str(1000+i),'公司名稱':'SYNTHETIC ONLY','產業別':'24'} for i in range(6)]),
            'quotes':ms.encode([{'Code':str(1000+i),'Date':'1151019','ClosingPrice':'30.5','TradeValue':'1,234,567'} for i in range(5)]),
            'valuation':ms.encode([{'Code':str(1000+i),'Date':'20261019','PEratio':'-5' if i==0 else '15','PBratio':'1.5'} for i in range(6)])}

    def test_official_shaped_fixture_preserves_master_missing_quotes_and_units(self):
        snapshot=ms.normalize_twse(self.raws(),'2026-10-19T16:00:00+08:00')
        self.assertEqual(len(snapshot['instruments']),6)
        self.assertEqual(snapshot['instruments'][-1]['metrics'].get('close'),None)
        first=snapshot['instruments'][0]
        self.assertIsNone(first['metrics']['pe']['value'])
        self.assertEqual(first['metrics']['turnover_twd']['value'],1234567)
        self.assertEqual(first['metrics']['close']['as_of'],'2026-10-19')
        self.assertEqual(first['metrics']['close']['unit'],'TWD/unit')
        h.schema_validator(h.local_files(h.ROOT),'market-snapshot.schema.json').validate(snapshot)
        self.assertIn('not all Taiwan',snapshot['scope']['label'])

    def test_schema_drift_duplicate_and_future_values_fail_closed(self):
        raw=self.raws();raw['master']=b'[{"WrongField":"1000"}]'
        with self.assertRaises(ValueError):ms.normalize_twse(raw,'2026-10-19T16:00:00+08:00')
        raw=self.raws();rows=json.loads(raw['quotes']);rows.append(rows[0]);raw['quotes']=ms.encode(rows)
        with self.assertRaises(ValueError):ms.normalize_twse(raw,'2026-10-19T16:00:00+08:00')
        raw=self.raws()
        with self.assertRaises(ValueError):ms.normalize_twse(raw,'2026-10-18T16:00:00+08:00')

    def test_failed_capture_keeps_diagnostics_and_never_substitutes_mock(self):
        with tempfile.TemporaryDirectory() as directory:
            def forbidden(url):raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden')
            with self.assertRaisesRegex(ValueError,'incomplete'):ms.capture_twse(directory,fetch=forbidden)
            trace=h.decode((Path(directory)/'fetch_attempt.json').read_bytes())
            self.assertEqual(len(trace['failures']),3)
            self.assertFalse((Path(directory)/'snapshot.json').exists())

    def test_capture_raw_archival_integrity_and_path_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source=folder/'source'
            raw=self.raws()
            snapshot=ms.capture_twse(source,fetch=lambda url:raw[next(k for k,v in ms.ENDPOINTS.items() if v==url)],now='2026-10-19T16:00:00+08:00')
            policy={**b.DEFAULT_POLICY,'as_of':snapshot['captured_at']}
            method={'research_commit_sha':'a'*40,'manifest_sha256':h.digest(h.local_files(h.ROOT)(h.MANIFEST)),'skill_versions':[], 'engine_sha256':b.engine_fingerprint()}
            b.initialize(snapshot,folder/'run',policy,method,source)
            self.assertEqual((folder/'run/raw/quotes.json').read_bytes(),raw['quotes'])
            (folder/'run/raw/quotes.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'Archived raw'):b.process(folder/'run',5)
            (source/'raw/quotes.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'integrity'):b.initialize(snapshot,folder/'bad',policy,method,source)
            snapshot['sources'][0]['raw_file']='campaign.sqlite';rehash(snapshot)
            with self.assertRaisesRegex(ValueError,'under raw'):b.initialize(snapshot,folder/'escape',policy,method,source)

    def test_403_never_retries_and_unregistered_endpoints_rejected(self):
        with patch.object(ms.urllib.request,'urlopen',side_effect=urllib.error.URLError('403 Forbidden')) as opened,patch.object(ms.time,'sleep') as delay:
            with self.assertRaises(urllib.error.URLError):ms.download(ms.ENDPOINTS['master'])
            self.assertEqual(opened.call_count,1);delay.assert_not_called()
        with self.assertRaises(ValueError):ms.download('https://unregistered.invalid/api')

    def test_transient_failures_retry_with_a_bound(self):
        response=MagicMock();response.geturl.return_value=ms.ENDPOINTS['master'];response.read.return_value=b'[]'
        response.__enter__.return_value=response
        error=urllib.error.HTTPError(ms.ENDPOINTS['master'],503,'Temporary failure',None,None)
        with patch.object(ms.urllib.request,'urlopen',side_effect=[error,response]) as opened,patch.object(ms.time,'sleep'):
            self.assertEqual(ms.download(ms.ENDPOINTS['master']),b'[]')
            self.assertEqual(opened.call_count,2)


if __name__=='__main__':unittest.main()
