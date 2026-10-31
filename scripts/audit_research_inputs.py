"""Read-only research-input audit. Counts records, not adjudicated incidents.

No LLM/RPC calls or credential inspection. Self-reported fixture flags never
certify execution. Invalid inputs remain visible and produce exit status 2.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common.generation_provenance import knowledge_base_snapshot_sha256


def _read_json(path: Path, root: Path, errors: list[dict]):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append({'path': path.relative_to(root).as_posix(),
                       'code': 'invalid_json', 'reason': type(exc).__name__})
        return None


def _revision(root: Path) -> str | None:
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _fingerprint(path: Path, root: Path, errors: list[dict], code: str) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        errors.append({'path': path.relative_to(root).as_posix(),
                       'code': code, 'reason': type(exc).__name__})
        return None


def build_inventory(repo_root: Path) -> dict:
    root = repo_root.resolve()
    errors: list[dict] = []
    records, rows, files = [], [], []
    raw_entry_count = 0
    ids: dict[str, list[str]] = defaultdict(list)
    kb_dir = root / 'src/module2_rag/data'
    if not kb_dir.is_dir():
        errors.append({'path': 'src/module2_rag/data', 'code': 'missing_kb'})
    for path in sorted(kb_dir.glob('*.json')):
        relative = path.relative_to(root).as_posix()
        digest = _fingerprint(path, root, errors, 'unreadable_kb')
        files.append({'path': relative, 'sha256': digest})
        payload = _read_json(path, root, errors)
        if payload is None and any(e['path'] == relative for e in errors):
            continue
        values = payload if isinstance(payload, list) else [payload]
        raw_entry_count += len(values)
        if not values:
            errors.append({'path': relative, 'code': 'empty_record_list'})
        for index, record in enumerate(values):
            location = f'{relative}#{index}'
            if not isinstance(record, dict):
                errors.append({'path': location, 'code': 'nonobject_record'})
                rows.append({'location': location, 'record_status': 'nonobject',
                             'incident_identity_review': 'not_adjudicated'})
                continue
            item = dict(record)
            # Support the loader's explicit legacy ID alias, without inventing identity.
            item.setdefault('exploit_id', item.get('id'))
            rid = item['exploit_id']
            if not isinstance(rid, str) or not rid.strip():
                errors.append({'path': location, 'code': 'invalid_id'})
            else:
                ids[rid].append(location)
            for field in ('bridge', 'vulnerability_class'):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append({'path': location, 'code': 'missing_record_field', 'field': field})
            records.append(item)
            rows.append({'location': location, 'exploit_id': rid,
                         'record_status': 'invalid' if any(e['path'] == location for e in errors) else 'valid',
                         'bridge': item.get('bridge'), 'date': item.get('date'),
                         'vulnerability_class': item.get('vulnerability_class'),
                         'source': item.get('source'),
                         'incident_identity_review': 'not_adjudicated'})
    if kb_dir.is_dir() and not files:
        errors.append({'path': 'src/module2_rag/data', 'code': 'empty_kb'})
    duplicates = [{'exploit_id': k, 'locations': v} for k, v in sorted(ids.items()) if len(v) > 1]
    for duplicate in duplicates:
        errors.append({'path': duplicate['locations'][0], 'code': 'duplicate_id',
                       'exploit_id': duplicate['exploit_id']})

    benchmarks = []
    bench_dir = root / 'benchmarks'
    if not bench_dir.is_dir():
        errors.append({'path': 'benchmarks', 'code': 'missing_benchmarks'})
    fixture_dirs = (sorted(p for p in bench_dir.iterdir()
                           if p.is_dir() and not p.name.startswith(('_', '.')))
                    if bench_dir.is_dir() else [])
    if bench_dir.is_dir() and not fixture_dirs:
        errors.append({'path': 'benchmarks', 'code': 'empty_benchmarks'})
    for fixture in fixture_dirs:
        path = fixture / 'metadata.json'
        relative = path.relative_to(root).as_posix()
        if not path.is_file():
            errors.append({'path': relative, 'code': 'missing_metadata'})
            data = {}
        else:
            data = _read_json(path, root, errors)
        metadata_is_object = isinstance(data, dict)
        if not metadata_is_object:
            if not any(e['path'] == relative for e in errors):
                errors.append({'path': relative, 'code': 'nonobject_metadata'})
            data = {}
        if path.is_file() and metadata_is_object and (
                not isinstance(data.get('benchmark_id'), str) or not data['benchmark_id'].strip()):
            errors.append({'path': relative, 'code': 'missing_benchmark_id'})
        status = data.get('status')
        status = status if isinstance(status, dict) else {}
        contracts = []
        for contract in sorted(fixture.glob('contracts/*.sol')):
            if not contract.is_file():
                errors.append({'path': contract.relative_to(root).as_posix(),
                               'code': 'nonfile_contract'})
                continue
            contracts.append({'path': contract.relative_to(root).as_posix(),
                              'sha256': _fingerprint(contract, root, errors, 'unreadable_contract')})
        benchmarks.append({
            'benchmark_id': data.get('benchmark_id', fixture.name),
            'metadata_path': relative,
            'metadata_sha256': _fingerprint(path, root, errors, 'unreadable_metadata') if path.is_file() else None,
            'contract_file_count': len(contracts),
            'contract_files': contracts,
            'self_reported_ready': status.get('ready_for_full_dual_evm_replay'),
            'execution_verified': False,
            'patched_revision': data.get('patched_revision'),
        })
    return {
        'schema_version': '1.0', 'source_revision': _revision(root),
        'input_valid': not errors, 'input_errors': errors,
        'scope': 'input_inventory_only_not_exploit_validation',
        'kb': {'file_count': len(files), 'record_count': len(records),
               'raw_entry_count': raw_entry_count,
               'nonobject_entry_count': sum(r['record_status'] == 'nonobject' for r in rows),
               'unique_incident_count': None,
               'snapshot_sha256': knowledge_base_snapshot_sha256(records),
               'files': files, 'records': rows, 'duplicate_ids': duplicates},
        'benchmarks': benchmarks,
    }


def write_inventory(report: dict, output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contents = {'inventory.json': json.dumps(report, ensure_ascii=False, indent=2) + '\n'}
    for filename, values, fields in [
        ('kb_inventory.csv', report['kb']['records'],
         ['location', 'record_status', 'exploit_id', 'bridge', 'date', 'vulnerability_class', 'source',
          'incident_identity_review']),
        ('benchmark_inventory.csv', report['benchmarks'],
         ['benchmark_id', 'metadata_path', 'contract_file_count', 'self_reported_ready',
          'execution_verified', 'patched_revision']),
    ]:
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(values)
        contents[filename] = stream.getvalue()
    if any((output_dir / name).is_symlink() for name in contents):
        raise ValueError('refusing to overwrite a symlink output file')
    for filename, content in contents.items():
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                             dir=output_dir, delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(content)
            # Replace directory entries; never follow destination symlinks/hardlinks.
            os.replace(temp_path, output_dir / filename)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.is_symlink():
        parser.error('--output directory must not be a symlink')
    root, output = args.repo_root.resolve(), args.output.resolve()
    for protected in (root / 'src/module2_rag/data', root / 'benchmarks'):
        if output.is_relative_to(protected.resolve()):
            parser.error('--output must be outside corpus and benchmark input directories')
    report = build_inventory(root)
    try:
        write_inventory(report, output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'audit output error: {exc}\n')
    print(json.dumps({'input_valid': report['input_valid'], 'records': report['kb']['record_count'],
                      'benchmarks': len(report['benchmarks']), 'errors': len(report['input_errors'])}))
    return 0 if report['input_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
