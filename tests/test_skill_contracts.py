"""Contract checks using synthetic fixtures; no market-data or investment tests."""
import copy
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {p.name: json.loads(p.read_text()) for p in (ROOT / 'schemas').glob('*.json')}
REGISTRY = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in SCHEMAS.values())


def validator(name):
    return Draft202012Validator(SCHEMAS[name], registry=REGISTRY, format_checker=FormatChecker())


def fixture(name):
    return json.loads((ROOT / 'tests/fixtures' / name).read_text())


class SkillContracts(unittest.TestCase):
    def assert_invalid(self, schema, value):
        self.assertTrue(list(validator(schema).iter_errors(value)))

    def test_schema_definitions(self):
        self.assertEqual(len(SCHEMAS), 5)
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)

    def test_synthetic_fixtures(self):
        for name in ['opportunity-screener.input', 'opportunity-screener.output',
                     'company-research.input', 'company-research.output']:
            with self.subTest(name=name):
                validator(name + '.schema.json').validate(fixture(name + '.json'))

    def test_ticker_retains_leading_zero(self):
        v = fixture('company-research.input.json')
        v['instrument']['ticker'] = '0050'
        validator('company-research.input.schema.json').validate(v)
        self.assertEqual(v['instrument']['ticker'], '0050')
        v['instrument']['ticker'] = 50
        self.assert_invalid('company-research.input.schema.json', v)

    def test_ticker_universe_cannot_be_empty(self):
        v = fixture('opportunity-screener.input.json')
        v['universe']['instruments'] = []
        self.assert_invalid('opportunity-screener.input.schema.json', v)

    def test_theme_requires_selector(self):
        v = fixture('opportunity-screener.input.json')
        v['universe']['mode'] = 'theme'
        self.assert_invalid('opportunity-screener.input.schema.json', v)

    def test_bad_date_rejected(self):
        self.assertIn('date-time', FormatChecker().checkers, 'Install requirements-dev.txt for RFC 3339 validation')
        v = fixture('company-research.input.json')
        v['as_of'] = '2026-99-31'
        self.assert_invalid('company-research.input.schema.json', v)

    def test_unknown_market_rejected(self):
        v = fixture('company-research.input.json')
        v['instrument']['market'] = 'NASDAQ'
        self.assert_invalid('company-research.input.schema.json', v)

    def test_cannot_smuggle_api_key(self):
        v = fixture('company-research.input.json')
        v['api_key'] = 'synthetic-placeholder-not-a-key'
        self.assert_invalid('company-research.input.schema.json', v)

    def test_incomplete_stock_cannot_have_rank_or_composite(self):
        for field in ['rank', 'composite']:
            v = fixture('opportunity-screener.output.json')
            v['stock_candidates'][0][field] = 1
            self.assert_invalid('opportunity-screener.output.schema.json', v)

    def test_ranked_stock_requires_all_dimensions_and_sources(self):
        v = fixture('opportunity-screener.output.json')
        row = v['stock_candidates'][0]
        row.update(status='ranked', rank=1, composite=5, coverage=1, source_ids=['synthetic-source'])
        self.assert_invalid('opportunity-screener.output.schema.json', v)
        row['dimension_scores'] = {k: 5 for k in row['dimension_scores']}
        validator('opportunity-screener.output.schema.json').validate(v)
        row['source_ids'] = []
        self.assert_invalid('opportunity-screener.output.schema.json', v)

    def test_score_bounds(self):
        v = fixture('opportunity-screener.output.json')
        v['stock_candidates'][0]['dimension_scores']['quality'] = 11
        self.assert_invalid('opportunity-screener.output.schema.json', v)

    def test_etf_cannot_get_stock_score(self):
        v = fixture('opportunity-screener.output.json')
        v['etf_candidates'][0]['composite'] = 9
        self.assert_invalid('opportunity-screener.output.schema.json', v)

    def test_etf_cannot_enter_company_path(self):
        v = fixture('company-research.output.json')
        v['path'] = 'company'
        self.assert_invalid('company-research.output.schema.json', v)
        v['path'] = 'etf'
        v['company_analysis'] = {}
        self.assert_invalid('company-research.output.schema.json', v)

    def test_research_output_cannot_claim_approval(self):
        v = fixture('company-research.output.json')
        v['meta']['approval_status'] = 'approved'
        self.assert_invalid('company-research.output.schema.json', v)

    def test_complete_research_needs_pillars_and_evidence(self):
        v = fixture('company-research.output.json')
        v['meta']['status'] = 'complete'
        self.assert_invalid('company-research.output.schema.json', v)

    def test_verified_metric_requires_source_and_value(self):
        metric = {'name': '合成指標', 'value': 1, 'unit': 'TWD/unit', 'currency': 'TWD',
                  'period': 'synthetic', 'classification': 'verified_fact',
                  'quality': 'verified', 'source_ids': ['synthetic-source'], 'formula': None}
        s = {'$ref': SCHEMAS['common.schema.json']['$id'] + '#/$defs/metric'}
        check = Draft202012Validator(s, registry=REGISTRY)
        check.validate(metric)
        for field, value in [('source_ids', []), ('value', None), ('quality', 'unverified')]:
            broken = copy.deepcopy(metric)
            broken[field] = value
            self.assertTrue(list(check.iter_errors(broken)))

    def test_unknown_metric_must_be_null(self):
        metric = {'name': '缺值', 'value': None, 'unit': '%', 'currency': None,
                  'period': 'unknown', 'classification': 'unknown', 'quality': 'missing',
                  'source_ids': [], 'formula': None}
        check = Draft202012Validator({'$ref': SCHEMAS['common.schema.json']['$id'] + '#/$defs/metric'}, registry=REGISTRY)
        check.validate(metric)
        metric['value'] = 0
        self.assertTrue(list(check.iter_errors(metric)))

    def test_company_branch_and_unique_three_scenarios(self):
        v = fixture('company-research.output.json')
        del v['etf_analysis']
        v['path'] = 'company'
        v['instrument']['asset_type'] = 'stock'
        analysis = {'business_model': '合成案例', 'financial_snapshot': [], 'financial_quality': [],
                    'moat_and_governance': [], 'five_vector_checks': dict.fromkeys(
                        ['accounting', 'expectations', 'operations', 'competition', 'macro'], '資料不足'),
                    'valuation': {'method': 'not_assessed', 'scenarios': [],
                                  'sensitivity_notes': [], 'calculation_records': [], 'limitations': ['未取數']}}
        v['company_analysis'] = analysis
        validator('company-research.output.schema.json').validate(v)
        analysis['valuation']['method'] = 'dcf'
        self.assert_invalid('company-research.output.schema.json', v)
        claim = {'claim_id': 'synthetic', 'text': '合成假設', 'classification': 'assumption',
                 'source_ids': [], 'counter_evidence': []}
        metric = {'name': '未計算', 'value': None, 'unit': 'TWD/unit', 'currency': 'TWD',
                  'period': 'synthetic', 'classification': 'assumption', 'quality': 'unverified',
                  'source_ids': [], 'formula': 'synthetic fixture only'}
        metric['value'] = 1
        analysis['valuation'].update(scenarios=[{'name': n, 'horizon_months': 36,
            'assumptions': [claim], 'fair_value_per_unit': metric, 'expected_return': metric}
            for n in ['bear', 'base', 'bull']], sensitivity_notes=['未計算'], calculation_records=['合成格式，非估值驗證'])
        validator('company-research.output.schema.json').validate(v)
        analysis['valuation']['scenarios'][2]['name'] = 'base'
        self.assert_invalid('company-research.output.schema.json', v)


class DocumentationChecks(unittest.TestCase):
    def test_priority_skills_have_metadata_and_real_schema_paths(self):
        for name in ['opportunity-screener', 'company-research']:
            text = (ROOT / '.agents/skills' / name / 'SKILL.md').read_text()
            self.assertTrue(text.startswith('---\nname: ' + name + '\n'))
            self.assertIn('description:', text)
            self.assertIn('docs/PROJECT.md', text)
            for direction in ['input', 'output']:
                path = f'schemas/{name}.{direction}.schema.json'
                self.assertIn(path, text)
                self.assertTrue((ROOT / path).exists())

    def test_local_markdown_links_exist(self):
        docs = [ROOT / 'README.md', ROOT / 'AGENTS.md', *(ROOT / 'docs').glob('*.md')]
        for path in docs:
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                with self.subTest(path=path.name, target=target):
                    self.assertTrue((path.parent / target.split('#')[0]).exists())

    def test_upstream_skill_links_are_commit_pinned(self):
        text = (ROOT / 'docs/skill-provenance.md').read_text()
        links = re.findall(r'https://github.com/[^\s)]+/blob/([^/]+)/[^\s)]+SKILL.md', text)
        self.assertGreaterEqual(len(links), 15)
        for commit in links:
            self.assertRegex(commit, r'^[0-9a-f]{40}$')
        licenses = list((ROOT / 'docs/third-party-licenses').glob('*-MIT.txt'))
        self.assertEqual(len(licenses), 3)
        for path in licenses:
            self.assertIn('Permission is hereby granted', path.read_text())

    def test_project_first_and_no_automatic_trading(self):
        self.assertIn('先讀 `docs/PROJECT.md`', (ROOT / 'AGENTS.md').read_text())
        self.assertIn('不自動下單', (ROOT / 'docs/PROJECT.md').read_text())


if __name__ == '__main__':
    unittest.main()
