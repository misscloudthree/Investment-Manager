"""Synthetic contract/package integration tests; never validate investment accuracy."""
import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path

from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('handoff', ROOT / 'src/research_handoff.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class ResearchHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.temp.name) / 'repo'
        cls.repo.mkdir()
        read = h.local_files(ROOT)
        manifest = h.check_materials(read)
        for path in h.required_paths(manifest):
            target = cls.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(read(path))
        for args in [('init', '-q'), ('add', '.'),
                     ('-c', 'user.name=Contract Tests', '-c', 'user.email=tests@example.invalid',
                      '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Synthetic committed methods')]:
            subprocess.run(['git', '-C', str(cls.repo), *args], check=True, capture_output=True)
        cls.sha, read, cls.manifest = h.committed_materials(cls.repo)
        cls.read = staticmethod(read)
        cls.bundle = Path(cls.temp.name) / 'research.zip'
        h.build_bundle(cls.repo, cls.bundle)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def draft(self, asset_type='stock'):
        name = 'company-research.stock.output.json' if asset_type == 'stock' else 'company-research.output.json'
        research = json.loads((ROOT / 'tests/fixtures' / name).read_text())
        return h.proposal_from_research(research, self.sha, self.read, self.manifest,
                                        'SYNTHETIC-MEMO.md', data_mode='mock')

    def complete_mock(self, asset_type='stock'):
        value = self.draft(asset_type)
        value['proposal_status'] = 'ready_for_review'
        value['data_quality'] = {'status': 'sufficient', 'confidence': 'medium',
                                 'missing_fields': [], 'conflicts': [],
                                 'limitations': ['SYNTHETIC schema test, not real research']}
        value['source_references'] = [{'source_id': 'mock-source', 'provider': 'Synthetic source',
            'locator': 'synthetic://fixture/not-a-real-document', 'data_period': 'synthetic',
            'published_at': '2026-10-18T18:00:00+08:00', 'published_date': None,
            'time_precision': 'timestamp', 'retrieved_at': '2026-10-19T16:00:00+08:00',
            'retrieval': 'user_provided', 'confidence': 'medium'}]
        value['investment_thesis'] = [{'claim_id': f'pillar-{i}', 'text': 'SYNTHETIC claim only',
            'classification': 'verified_fact' if i == 1 else 'inference', 'source_ids': ['mock-source'],
            'counter_evidence': ['SYNTHETIC unresolved alternative']} for i in range(1, 4)]
        value['supporting_evidence'] = [copy.deepcopy(value['investment_thesis'][0])]
        value['monitoring_kpis'] = [{'kpi_id': 'kpi-1', 'metric_name': 'SYNTHETIC margin test',
            'unit': 'ratio', 'reporting_frequency': 'quarterly', 'source_ids': ['mock-source'],
            'comparison_operator': 'lt', 'threshold': 0.1, 'threshold_rationale': 'SYNTHETIC threshold for tests only',
            'threshold_basis': 'mock', 'observation_window': {'periods': 2, 'description': 'two synthetic quarters'},
            'freshness': {'max_age_days': 120, 'require_latest_publication': True, 'rationale': 'mock policy'},
            'missing_data_handling': 'mark_unknown_and_request_data', 'status': 'configured'}]
        value['quantitative_triggers'] = [{'trigger_id': 'quant-1', 'kpi_id': 'kpi-1', 'action': 'request_human_review'}]
        value['invalidation_criteria'] = [{'criterion_id': 'invalid-1', 'thesis_pillar_id': 'pillar-1',
            'condition': 'SYNTHETIC condition', 'linked_kpi_ids': ['kpi-1'], 'source_ids': ['mock-source'],
            'action': 'request_human_review'}]
        value['scenarios'] = [{'name': n, 'drivers': ['synthetic scenario driver'],
            'assessment': 'No price forecast; synthetic only', 'source_ids': ['mock-source'],
            'limitations': ['mock']} for n in ['bull', 'base', 'bear']]
        return value

    def validate(self, value):
        return h.validate_proposal(value, self.sha, self.read, self.manifest)

    def invalid(self, value):
        with self.assertRaises((ValueError, ValidationError)):
            self.validate(value)

    def rewritten_bundle(self, change):
        with zipfile.ZipFile(self.bundle) as z:
            files = {n: z.read(n) for n in z.namelist()}
        change(files)
        out = Path(self.temp.name) / 'broken.zip'
        with zipfile.ZipFile(out, 'w') as z:
            for name, data in files.items():
                z.writestr(name, data)
        return out

    def test_equity_proposal_and_conversion(self):
        value = self.draft('stock')
        self.assertEqual(value['proposal_status'], 'needs_information')
        self.assertEqual(value['monitoring_kpis'], [])
        self.assertEqual(self.validate(value)['investment_accuracy'], 'not_validated')
        self.validate(self.complete_mock('stock'))

    def test_etf_proposal_and_conversion(self):
        value = self.complete_mock('etf')
        self.validate(value)
        self.assertNotIn('equity_analysis', value)
        value['equity_analysis'] = self.draft()['equity_analysis']
        self.invalid(value)

    def test_insufficient_data_never_becomes_ready(self):
        value = self.draft()
        self.validate(value)
        value['proposal_status'] = 'ready_for_review'
        self.invalid(value)

    def test_conflicting_data_must_explain_conflict(self):
        value = self.draft()
        value['data_quality'].update(status='conflicting', conflicts=['SYNTHETIC two values disagree'])
        self.validate(value)
        value['data_quality']['conflicts'] = []
        self.invalid(value)

    def test_missing_required_field(self):
        value = self.draft()
        del value['research_commit_sha']
        self.invalid(value)

    def test_approval_is_not_a_proposal_status(self):
        value = self.draft()
        value['proposal_status'] = 'approved'
        self.invalid(value)

    def test_unknown_skill_revision(self):
        value = self.draft()
        value['skill_versions'][0]['revision'] = '999.0.0'
        self.invalid(value)

    def test_unknown_research_commit(self):
        value = self.draft()
        value['research_commit_sha'] = '0' * 40
        self.invalid(value)

    def test_tampered_skill_digest(self):
        value = self.draft()
        value['skill_versions'][0]['skill_sha256'] = '0' * 64
        self.invalid(value)

    def test_missing_receipt_dependency(self):
        value = self.draft()
        value['methodology_receipt']['files'].pop()
        self.invalid(value)

    def test_unknown_source_reference(self):
        value = self.complete_mock()
        value['investment_thesis'][1]['source_ids'] = ['no-such-source']
        self.invalid(value)

    def test_duplicate_source_id(self):
        value = self.complete_mock()
        value['source_references'] *= 2
        self.invalid(value)

    def test_conflicting_claim_definitions(self):
        value = self.complete_mock()
        value['supporting_evidence'][0]['text'] = 'Changed same claim ID'
        self.invalid(value)

    def test_unknown_kpi_and_pillar_links(self):
        for location, field in [('quantitative_triggers', 'kpi_id'), ('invalidation_criteria', 'thesis_pillar_id')]:
            value = self.complete_mock()
            value[location][0][field] = 'does-not-exist'
            self.invalid(value)

    def test_unconfigured_threshold_not_a_trigger(self):
        value = self.complete_mock()
        value['monitoring_kpis'][0].update(status='unconfigured', threshold=None,
            comparison_operator='unconfigured', threshold_basis='unconfigured')
        value['proposal_status'] = 'draft'
        self.invalid(value)
        value['quantitative_triggers'] = []
        self.validate(value)

    def test_missing_threshold_rationale(self):
        value = self.complete_mock()
        value['monitoring_kpis'][0]['threshold_rationale'] = ''
        self.invalid(value)

    def test_mock_threshold_cannot_enter_real_proposal(self):
        value = self.complete_mock()
        value['data_mode'] = 'public_sources'
        self.invalid(value)

    def test_future_publication_and_fetch_rejected(self):
        for field in ['published_at', 'retrieved_at']:
            value = self.complete_mock()
            value['source_references'][0][field] = '2099-01-01T00:00:00Z'
            self.invalid(value)

    def test_date_only_source_never_fakes_timestamp(self):
        value = self.complete_mock()
        value['source_references'][0].update(published_at=None, published_date='2026-10-18', time_precision='date')
        self.validate(value)
        value['source_references'][0]['published_at'] = '2026-10-18T00:00:00Z'
        self.invalid(value)

    def test_screening_is_not_ready_for_review(self):
        value = self.complete_mock()
        value['research_stage'] = 'screening'
        self.invalid(value)

    def test_duplicate_event_is_not_counted_twice(self):
        value = self.draft()
        value['risk_factors'] = [dict(risk_id=f'r{i}', canonical_event_id='same-event',
            description='SYNTHETIC event', transmission='synthetic path', source_ids=[]) for i in range(2)]
        self.invalid(value)

    def test_partial_etf_holdings_cannot_claim_full_overlap(self):
        value = self.draft('etf')
        value['etf_analysis'].update(holdings_coverage=0.5, overlap_status='full')
        self.invalid(value)

    def test_conversion_preserves_explicit_scenario_assumptions(self):
        research = json.loads((ROOT / 'tests/fixtures/company-research.stock.output.json').read_text())
        valuation = research['company_analysis']['valuation']
        claim = {'claim_id': 'scenario-assumption', 'text': 'SYNTHETIC growth assumption',
                 'classification': 'assumption', 'source_ids': [], 'counter_evidence': []}
        metric = {'name': 'synthetic price', 'value': 1, 'unit': 'TWD/unit', 'currency': 'TWD',
                  'period': 'synthetic', 'classification': 'assumption', 'quality': 'unverified',
                  'source_ids': [], 'formula': 'SYNTHETIC only'}
        valuation.update(method='normalized_earnings', calculation_records=['SYNTHETIC record'],
            sensitivity_notes=['SYNTHETIC note'], scenarios=[{'name': n, 'horizon_months': 36,
            'assumptions': [claim], 'fair_value_per_unit': metric, 'expected_return': metric}
            for n in ['bear','base','bull']])
        value = h.proposal_from_research(research, self.sha, self.read, self.manifest,
                                        'SYNTHETIC-MEMO.md', data_mode='mock')
        self.validate(value)
        self.assertEqual(value['assumptions'], [claim])
        self.assertEqual({s['name'] for s in value['scenarios']}, {'bear','base','bull'})

    def test_bundle_round_trip_and_offline_validation(self):
        sha, read, manifest = h.bundle_materials(self.bundle, self.sha)
        value = self.complete_mock('etf')
        value['methodology_receipt'] = h.receipt(read, manifest, 'bundle_hashes')
        value['proposal_status'] = 'draft'
        h.validate_proposal(value, sha, read, manifest)
        value['proposal_status'] = 'ready_for_review'
        with self.assertRaisesRegex(ValueError, 'Verify source revision'):
            h.validate_proposal(value, sha, read, manifest)

    def test_bundle_build_is_reproducible(self):
        second = Path(self.temp.name) / 'second-build.zip'
        h.build_bundle(self.repo, second)
        self.assertEqual(self.bundle.read_bytes(), second.read_bytes())

    def test_memo_template_has_all_thirteen_sections(self):
        import re
        text = (ROOT / 'docs/INVESTMENT_MEMO_TEMPLATE.md').read_text()
        self.assertEqual(re.findall(r'^## (\d+)\.', text, re.MULTILINE), [str(i) for i in range(1, 14)])
        self.assertIn('canonical', (ROOT / 'docs/CHATGPT_HANDOFF.md').read_text())

    def test_bundle_missing_dependency(self):
        path = self.rewritten_bundle(lambda f: f.pop('schemas/common.schema.json'))
        with self.assertRaises((KeyError, ValueError)):
            h.bundle_materials(path)

    def test_bundle_changed_bytes_and_unexpected_commit(self):
        path = self.rewritten_bundle(lambda f: f.update({'docs/PROJECT.md': b'tampered'}))
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            h.bundle_materials(path)
        with self.assertRaisesRegex(ValueError, 'Unexpected research commit'):
            h.bundle_materials(self.bundle, '0' * 40)

    def test_bundle_rejects_traversal_extra_files_and_duplicates(self):
        for bad in ['../escape', '/absolute', 'unexpected.txt']:
            path = self.rewritten_bundle(lambda f: f.update({bad: b'bad'}))
            with self.assertRaises(ValueError):
                h.bundle_materials(path)
        path = self.rewritten_bundle(lambda f: None)
        with zipfile.ZipFile(path, 'a') as z:
            # Deliberately malformed archive; silence expected duplicate warning.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('docs/PROJECT.md', 'duplicate')
        with self.assertRaisesRegex(ValueError, 'Duplicate bundle'):
            h.bundle_materials(path)

    def test_bundle_refuses_uncommitted_method_changes(self):
        path = self.repo / 'docs/PROJECT.md'
        previous = path.read_bytes()
        try:
            path.write_bytes(previous + b'changed')
            with self.assertRaisesRegex(ValueError, 'Uncommitted methodology'):
                h.build_bundle(self.repo, Path(self.temp.name) / 'not-built.zip')
        finally:
            path.write_bytes(previous)

    def test_json_rejects_duplicate_keys_and_nonfinite_values(self):
        for raw in ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}']:
            with self.assertRaises(ValueError):
                h.decode(raw)

    def test_cli_rejects_invalid_proposal_with_nonzero_exit(self):
        path = Path(self.temp.name) / 'invalid.json'
        path.write_text('{}')
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(h.main(['validate', str(path), '--bundle', str(self.bundle)]), 2)


if __name__ == '__main__':
    unittest.main()
