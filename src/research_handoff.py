"""Offline research-material packaging and proposal validation; no research or approvals."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'docs/SKILL_MANIFEST.json'
METADATA = 'BUNDLE_METADATA.json'
MAX_BUNDLE_BYTES = 10 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def reject_constant(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number')
        return number
    return json.loads(data, parse_constant=reject_constant, parse_float=finite_float, object_pairs_hook=unique_pairs)


def safe_path(path):
    if not isinstance(path, str) or '\\' in path:
        raise ValueError('Invalid bundle path')
    p = PurePosixPath(path)
    if p.is_absolute() or '..' in p.parts or str(p) != path or not p.parts:
        raise ValueError(f'Unsafe bundle path: {path}')
    return path


def local_files(root):
    def read(path):
        safe_path(path)
        full = root / path
        if not full.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Path escapes repository: {path}')
        return full.read_bytes()
    return read


def read_manifest(read):
    manifest = decode(read(MANIFEST))
    if manifest.get('manifest_version') != '1.0':
        raise ValueError('Unknown manifest version')
    skills = manifest.get('skills', [])
    if {s['name'] for s in skills} != {'opportunity-screener', 'company-research'} or len(skills) != 2:
        raise ValueError('Unknown or duplicate research Skill')
    for skill in skills:
        if not re.fullmatch(r'\d+\.\d+\.\d+', skill['revision']):
            raise ValueError('Unknown Skill revision')
        safe_path(skill['canonical_path'])
    return manifest


def required_paths(manifest):
    paths = {MANIFEST}
    for item in manifest['shared_dependencies']:
        paths.add(safe_path(item['path']))
    for skill in manifest['skills']:
        paths.add(safe_path(skill['canonical_path']))
        paths.update(safe_path(p) for p in skill['dependencies'])
    return paths


def check_materials(read):
    manifest = read_manifest(read)
    expected = {x['path']: x['sha256'] for x in manifest['shared_dependencies']}
    if len(expected) != len(manifest['shared_dependencies']):
        raise ValueError('Duplicate dependency')
    for skill in manifest['skills']:
        expected[skill['canonical_path']] = skill['sha256']
    if set(expected) != required_paths(manifest) - {MANIFEST}:
        raise ValueError('Missing dependency hash in manifest')
    for path, sha in expected.items():
        if digest(read(path)) != sha:
            raise ValueError(f'Material hash mismatch: {path}')
    return manifest


def refresh_manifest(root, revision):
    if not re.fullmatch(r'\d+\.\d+\.\d+', revision):
        raise ValueError('Revision must use X.Y.Z')
    read = local_files(root)
    manifest = read_manifest(read)
    for dependency in manifest['shared_dependencies']:
        dependency['sha256'] = digest(read(dependency['path']))
    for skill in manifest['skills']:
        skill['revision'] = revision
        skill['sha256'] = digest(read(skill['canonical_path']))
    (root / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    check_materials(local_files(root))
    return {'manifest_refreshed': True, 'revision': revision, 'execution': 'not_claimed'}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def committed_materials(root, commit=None):
    sha = commit or git(root, 'rev-parse', 'HEAD').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Research commit must be a full SHA')
    def read(path):
        return git(root, 'show', f'{sha}:{safe_path(path)}')
    manifest = check_materials(read)
    return sha, read, manifest


def build_bundle(root, output):
    sha, read, manifest = committed_materials(root)
    current = local_files(root)
    for path in required_paths(manifest):
        if current(path) != read(path):
            raise ValueError(f'Uncommitted methodology change: {path}; commit reviewed changes first')
    paths = sorted(required_paths(manifest))
    metadata = {'bundle_version': '1.0', 'repository': manifest['repository'],
                'research_commit_sha': sha, 'files': {p: digest(read(p)) for p in paths},
                'scope': 'Research instructions and contracts only; not a live research run'}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w') as archive:
        def write_member(name, data):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        for path in paths:
            write_member(path, read(path))
        write_member(METADATA, json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    return metadata


def bundle_materials(path, expected_commit=None):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 100 or sum(x.file_size for x in infos) > MAX_BUNDLE_BYTES:
            raise ValueError('Bundle exceeds size/file limit')
        names = [safe_path(x.filename) for x in infos]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate bundle members')
        if any((x.external_attr >> 16) & 0o170000 == 0o120000 for x in infos):
            raise ValueError('Symlink bundle members are forbidden')
        data = {x.filename: archive.read(x) for x in infos}
    metadata = decode(data[METADATA])
    if metadata.get('bundle_version') != '1.0' or not re.fullmatch('[0-9a-f]{40}', metadata['research_commit_sha']):
        raise ValueError('Unknown bundle revision')
    if expected_commit is not None and metadata['research_commit_sha'] != expected_commit:
        raise ValueError('Unexpected research commit')
    manifest = check_materials(data.__getitem__)
    paths = required_paths(manifest)
    if set(data) != paths | {METADATA} or set(metadata['files']) != paths:
        raise ValueError('Bundle dependencies incomplete or unexpected files present')
    if metadata['repository'] != manifest['repository']:
        raise ValueError('Bundle repository mismatch')
    for name in paths:
        if digest(data[name]) != metadata['files'][name]:
            raise ValueError(f'Bundle hash mismatch: {name}')
    return metadata['research_commit_sha'], data.__getitem__, manifest


def receipt(read, manifest, method):
    return {'manifest_sha256': digest(read(MANIFEST)),
            'files': [{'path': p, 'sha256': digest(read(p))} for p in sorted(required_paths(manifest))],
            'verification_method': method, 'integrity_status': 'verified',
            'origin_authentication': 'trusted_repository' if method == 'local_git' else 'not_verified',
            'capabilities': {'web_access': 'not_tested', 'python': 'not_tested', 'data_apis': 'not_tested'},
            'calculation_status': 'not_run',
            'limitations': ['Material checks do not prove that ChatGPT read, executed, or understood the Skill.']}


def version_records(manifest, names):
    return [{'skill_name': s['name'], 'revision': s['revision'], 'skill_sha256': s['sha256']}
            for s in manifest['skills'] if s['name'] in names]


def schema_validator(read, name):
    schemas = [decode(read(p)) for p in required_paths(read_manifest(read)) if p.startswith('schemas/')]
    registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
    schema = next(s for s in schemas if s['$id'].endswith('/' + name))
    if 'date-time' not in FormatChecker().checkers:
        raise ValueError('Install requirements-dev.txt for date-time format validation')
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def unique_ids(items, field):
    ids = [x[field] for x in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f'Duplicate {field}')
    return set(ids)


def validate_proposal(proposal, sha, read, manifest):
    schema_validator(read, 'thesis-proposal.schema.json').validate(proposal)
    if proposal['research_commit_sha'] != sha:
        raise ValueError('Unknown/unverifiable research commit')
    names = {s['skill_name'] for s in proposal['skill_versions']}
    required = {'opportunity-screener', 'company-research'} if proposal['research_stage'] == 'deep_research' else {'opportunity-screener'}
    if names != required or len(names) != len(proposal['skill_versions']):
        raise ValueError('Missing, duplicate or inapplicable Skill version')
    expected = {s['skill_name']: s for s in version_records(manifest, names)}
    for version in proposal['skill_versions']:
        if expected.get(version['skill_name']) != version:
            raise ValueError('Unknown/unverifiable Skill version')
    rec = proposal['methodology_receipt']
    if rec['manifest_sha256'] != digest(read(MANIFEST)):
        raise ValueError('Manifest digest mismatch')
    received = {x['path']: x['sha256'] for x in rec['files']}
    if len(received) != len(rec['files']) or set(received) != required_paths(manifest):
        raise ValueError('Missing or duplicate received dependencies')
    for path, file_sha in received.items():
        if file_sha != digest(read(path)):
            raise ValueError(f'Received dependency digest mismatch: {path}')
    sources = unique_ids(proposal['source_references'], 'source_id')
    pillars = unique_ids(proposal['investment_thesis'], 'claim_id')
    unique_ids(proposal['supporting_evidence'], 'claim_id')
    unique_ids(proposal['assumptions'], 'claim_id')
    kpis = unique_ids(proposal['monitoring_kpis'], 'kpi_id')
    definitions = {}
    for field in ['investment_thesis', 'supporting_evidence', 'assumptions']:
        for claim in proposal[field]:
            if claim['claim_id'] in definitions and definitions[claim['claim_id']] != claim:
                raise ValueError('Conflicting definitions for the same claim_id')
            definitions[claim['claim_id']] = claim
    for field, id_key in [('quantitative_triggers','trigger_id'), ('qualitative_triggers','trigger_id'),
                          ('invalidation_criteria','criterion_id'), ('risk_factors','risk_id')]:
        unique_ids(proposal[field], id_key)
    def check_refs(value):
        if isinstance(value, dict):
            if 'source_ids' in value and not set(value['source_ids']) <= sources:
                raise ValueError('Dangling source reference')
            for child in value.values():
                check_refs(child)
        elif isinstance(value, list):
            for child in value:
                check_refs(child)
    check_refs(proposal)
    for entry in proposal['supporting_evidence']:
        if entry['classification'] != 'verified_fact':
            raise ValueError('Supporting evidence must be verified_fact; inference belongs in thesis')
    if any(x['classification'] != 'assumption' for x in proposal['assumptions']):
        raise ValueError('Assumptions must be explicitly classified')
    for trigger in proposal['quantitative_triggers']:
        if trigger['kpi_id'] not in kpis:
            raise ValueError('Dangling KPI trigger')
        kpi = next(x for x in proposal['monitoring_kpis'] if x['kpi_id'] == trigger['kpi_id'])
        if kpi['status'] != 'configured':
            raise ValueError('Unconfigured KPI cannot trigger an assessment')
    for criterion in proposal['invalidation_criteria']:
        if criterion['thesis_pillar_id'] not in pillars or not set(criterion['linked_kpi_ids']) <= kpis:
            raise ValueError('Dangling thesis/KPI invalidation reference')
    quality = proposal['data_quality']
    if quality['status'] == 'insufficient' and not quality['missing_fields']:
        raise ValueError('Insufficient data must identify missing fields')
    if quality['status'] == 'conflicting' and not quality['conflicts']:
        raise ValueError('Conflicting data must identify conflicts')
    stamp = datetime.fromisoformat(proposal['research_timestamp'].replace('Z', '+00:00'))
    cutoff = datetime.fromisoformat(proposal['data_cutoff'].replace('Z', '+00:00'))
    if cutoff > stamp:
        raise ValueError('Data cutoff is after research timestamp')
    for source in proposal['source_references']:
        fetched = datetime.fromisoformat(source['retrieved_at'].replace('Z', '+00:00'))
        if fetched > stamp:
            raise ValueError('Source retrieved after research timestamp')
        published = source['published_at']
        if published is not None and datetime.fromisoformat(published.replace('Z','+00:00')) > min(cutoff, fetched):
            raise ValueError('Publication not available at cutoff/retrieval')
        if source['published_date'] is not None and source['published_date'] > cutoff.astimezone(ZoneInfo('Asia/Taipei')).date().isoformat():
            raise ValueError('Publication date after data cutoff')
    if proposal['asset_type'] == 'etf':
        etf = proposal['etf_analysis']
        if etf['overlap_status'] == 'full' and etf['holdings_coverage'] != 1:
            raise ValueError('Partial holdings cannot claim full overlap assessment')
    if quality['status'] == 'sufficient' and (quality['missing_fields'] or quality['conflicts']):
        raise ValueError('Sufficient quality cannot hide missing/conflicting information')
    for risk in proposal['risk_factors']:
        if sum(r['canonical_event_id'] == risk['canonical_event_id'] for r in proposal['risk_factors']) > 1:
            raise ValueError('Duplicate canonical event; merge its transmission paths')
    if proposal['proposal_status'] == 'ready_for_review':
        if rec['origin_authentication'] == 'not_verified':
            raise ValueError('Verify source revision before marking ready_for_review')
        if any(x['status'] != 'configured' for x in proposal['monitoring_kpis']):
            raise ValueError('Unconfigured KPI requires more information')
    if proposal['data_mode'] != 'mock' and any(k['threshold_basis'] == 'mock' for k in proposal['monitoring_kpis']):
        raise ValueError('Mock thresholds cannot enter real proposals')
    return {'structural_validity': True, 'provenance_consistency': True,
            'investment_accuracy': 'not_validated', 'approval': 'not_granted'}


def proposal_from_research(research, sha, read, manifest, memo_path, *, data_mode):
    """Map a Task 1 research record to a draft; never fabricate KPI thresholds."""
    schema_validator(read, 'company-research.output.schema.json').validate(research)
    sources = []
    for source in research['meta']['sources']:
        sources.append({**source, 'published_date': None, 'time_precision': 'timestamp'})
    pillars = copy.deepcopy(research['thesis_pillars'])
    result = {'schema_version': '1.0', 'proposal_id': research['meta']['run_id'] + '-proposal',
              'asset_id': research['instrument']['market'] + ':' + research['instrument']['ticker'],
              'asset_type': research['instrument']['asset_type'], 'proposal_status': 'needs_information',
              'research_stage': 'deep_research', 'research_timestamp': research['meta']['generated_at'],
              'data_cutoff': research['meta']['as_of'], 'data_mode': data_mode,
              'investment_thesis': pillars,
              'supporting_evidence': [p for p in pillars if p['classification'] == 'verified_fact'],
              'assumptions': [p for p in pillars if p['classification'] == 'assumption'],
              'monitoring_kpis': [], 'quantitative_triggers': [], 'qualitative_triggers': [],
              'invalidation_criteria': [{'criterion_id': f'criterion-{i}',
                  'thesis_pillar_id': c['thesis_pillar_id'],
                  'condition': f"{c['indicator']} / {c['threshold']} / {c['window']}",
                  'linked_kpi_ids': [], 'source_ids': c['source_ids'], 'action': 'request_human_review'}
                  for i, c in enumerate(research['kill_criteria'], 1)],
              'risk_factors': [{'risk_id': f'risk-{i}', 'canonical_event_id': x['event_id'],
                  'description': x['impact_or_scenario'], 'transmission': x['transmission'],
                  'source_ids': x['source_ids']} for i, x in enumerate(research['risks'], 1)],
              'data_quality': {'status': 'insufficient', 'confidence': research['meta']['confidence'],
                  'missing_fields': research['meta']['data_gaps'] + ['KPI definitions and threshold rationale require review'],
                  'conflicts': [], 'limitations': research['meta']['limitations']},
              'source_references': sources,
              'skill_versions': version_records(manifest, {'company-research','opportunity-screener'}),
              'research_commit_sha': sha, 'methodology_receipt': receipt(read, manifest, 'local_git'),
              'research_priority': {'level': 'unranked', 'rationale': 'Converted research draft; no ranking inferred',
                                    'missing_information': ['Human review and evidence-backed KPIs']},
              'scenarios': [], 'memo_path': memo_path}
    field = 'equity_analysis' if research['path'] == 'company' else 'etf_analysis'
    result[field] = copy.deepcopy(research['company_analysis' if research['path'] == 'company' else 'etf_analysis'])
    if research['path'] == 'company':
        scenarios = research['company_analysis']['valuation']['scenarios']
        for scenario in scenarios:
            result['scenarios'].append({'name': scenario['name'],
                'drivers': [a['text'] for a in scenario['assumptions']],
                'assessment': 'Original valuation values retained in equity_analysis; not independently recalculated',
                'source_ids': sorted({sid for a in scenario['assumptions'] for sid in a['source_ids']}),
                'limitations': ['Conservative conversion; inspect original calculation records']})
            for assumption in scenario['assumptions']:
                if assumption['classification'] == 'assumption' and assumption not in result['assumptions']:
                    result['assumptions'].append(copy.deepcopy(assumption))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-materials')
    refresh = sub.add_parser('refresh-manifest'); refresh.add_argument('--revision', required=True)
    bundle = sub.add_parser('bundle'); bundle.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('verify-bundle'); verify.add_argument('bundle', type=Path); verify.add_argument('--expected-commit')
    validate = sub.add_parser('validate'); validate.add_argument('proposal', type=Path); validate.add_argument('--bundle', type=Path); validate.add_argument('--expected-commit')
    convert = sub.add_parser('convert'); convert.add_argument('research', type=Path); convert.add_argument('--output', type=Path, required=True); convert.add_argument('--memo-path', required=True); convert.add_argument('--data-mode', choices=['mock','public_sources','user_documents'], required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'refresh-manifest':
            result = refresh_manifest(ROOT, args.revision)
        elif args.command == 'check-materials':
            manifest = check_materials(local_files(ROOT))
            result = {'materials_consistent': True, 'skills': [s['name'] for s in manifest['skills']], 'execution': 'not_claimed'}
        elif args.command == 'bundle':
            result = build_bundle(ROOT, args.output)
        elif args.command == 'verify-bundle':
            sha, read, manifest = bundle_materials(args.bundle, args.expected_commit)
            result = {'research_commit_sha': sha, 'receipt': receipt(read, manifest, 'bundle_hashes'),
                      'skill_versions': version_records(manifest, {'company-research','opportunity-screener'})}
        else:
            if args.command == 'validate' and args.bundle:
                sha, read, manifest = bundle_materials(args.bundle, args.expected_commit)
            else:
                commit = args.expected_commit if args.command == 'validate' else None
                sha, read, manifest = committed_materials(ROOT, commit)
            value = decode((args.proposal if args.command == 'validate' else args.research).read_bytes())
            if args.command == 'convert':
                value = proposal_from_research(value, sha, read, manifest, args.memo_path, data_mode=args.data_mode)
                validate_proposal(value, sha, read, manifest)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
                result = {'proposal_written': str(args.output), 'proposal_status': value['proposal_status']}
            else:
                result = validate_proposal(value, sha, read, manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ValidationError as error:
        print(f'NOT_VALIDATED: schema rule {error.validator} failed at /' + '/'.join(map(str, error.absolute_path)), file=sys.stderr)
        return 2
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f'NOT_VALIDATED: {error}', file=sys.stderr)
        return 2
    except Exception as error:
        # jsonschema/referencing errors are validation failures, never a success exit.
        print(f'NOT_VALIDATED: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
