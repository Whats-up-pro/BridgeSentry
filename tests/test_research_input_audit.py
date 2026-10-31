"""Behavior checks for the read-only Phase 0 audit command."""
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def record(identity='a', bridge='Demo'):
    return {'exploit_id': identity, 'bridge': bridge, 'vulnerability_class': 'logic_bug'}


def fixture_repo(tmp_path):
    repo = tmp_path / 'repo'
    kb = repo / 'src/module2_rag/data'
    kb.mkdir(parents=True)
    bench = repo / 'benchmarks/demo'
    (bench / 'contracts').mkdir(parents=True)
    (bench / 'contracts/Demo.sol').write_text('contract Demo {}')
    (bench / 'metadata.json').write_text(json.dumps({
        'benchmark_id': 'demo', 'status': {'ready_for_full_dual_evm_replay': True}}))
    return repo, kb


def invoke(repo, output, cwd):
    return subprocess.run([sys.executable, str(ROOT / 'scripts/audit_research_inputs.py'),
                           '--repo-root', str(repo), '--output', str(output)],
                          cwd=cwd, capture_output=True, text=True)


def report_at(output):
    return json.loads((output / 'inventory.json').read_text())


def test_cli_retains_every_record_and_labels_readiness_as_self_reported(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    (kb / 'b.json').write_text(json.dumps([record('b'), record('c', 'Other')]))
    output = tmp_path / 'out'
    result = invoke(repo, output, tmp_path)
    assert result.returncode == 0, result.stderr
    report = report_at(output)
    assert report['kb']['file_count'] == 2
    assert report['kb']['record_count'] == 3
    assert report['kb']['unique_incident_count'] is None
    assert report['benchmarks'][0]['self_reported_ready'] is True
    assert report['benchmarks'][0]['execution_verified'] is False
    assert report['benchmarks'][0]['patched_revision'] is None
    with (output / 'kb_inventory.csv').open() as stream:
        assert [r['exploit_id'] for r in csv.DictReader(stream)] == ['a', 'b', 'c']
    assert len(report['kb']['snapshot_sha256']) == 64


def test_duplicate_identifiers_keep_both_locations_and_fail_audit(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    for name in ['a', 'b']:
        (kb / f'{name}.json').write_text(json.dumps(record('same')))
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert report['kb']['record_count'] == 2
    assert report['kb']['duplicate_ids'] == [{'exploit_id': 'same', 'locations': [
        'src/module2_rag/data/a.json#0', 'src/module2_rag/data/b.json#0']}]
    assert report['input_valid'] is False


def test_malformed_json_and_nonobject_entries_are_not_silently_dropped(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'bad.json').write_text('{')
    (kb / 'list.json').write_text(json.dumps([record('kept'), 42]))
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert report['kb']['file_count'] == 2
    assert report['kb']['record_count'] == 1
    assert {e['code'] for e in report['input_errors']} == {'invalid_json', 'nonobject_record'}


def test_missing_directories_are_invalid_input(tmp_path):
    repo = tmp_path / 'empty'
    repo.mkdir()
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    assert {e['code'] for e in report_at(output)['input_errors']} == {'missing_kb', 'missing_benchmarks'}


def test_inventory_does_not_leak_credentials_or_change_source(tmp_path, monkeypatch):
    repo, kb = fixture_repo(tmp_path)
    raw = json.dumps(record())
    source = kb / 'a.json'
    source.write_text(raw)
    monkeypatch.setenv('OPENAI_API_KEY', 'SECRET_DO_NOT_SERIALIZE')
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 0
    assert all('SECRET_DO_NOT_SERIALIZE' not in p.read_text() for p in output.iterdir())
    assert source.read_text() == raw


def test_null_metadata_is_rejected_instead_of_disappearing(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    (repo / 'benchmarks/demo/metadata.json').write_text('null')
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    assert {e['code'] for e in report_at(output)['input_errors']} == {'nonobject_metadata'}


def test_output_directory_inside_inputs_is_rejected(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    assert invoke(repo, kb, tmp_path).returncode == 2
    assert not (kb / 'inventory.json').exists()


def test_empty_object_records_remain_visible_but_invalid(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text('{}')
    (kb / 'b.json').write_text('[{}]')
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert report['kb']['record_count'] == 2
    assert {e['path'] for e in report['input_errors']} == {
        'src/module2_rag/data/a.json#0', 'src/module2_rag/data/b.json#0'}


def test_empty_metadata_is_not_validated_by_filename_fallback(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    (repo / 'benchmarks/demo/metadata.json').write_text('{}')
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    assert 'missing_benchmark_id' in {e['code'] for e in report_at(output)['input_errors']}


def test_output_file_symlinks_cannot_overwrite_inputs(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    raw = json.dumps(record())
    source = kb / 'a.json'
    source.write_text(raw)
    output = tmp_path / 'out'
    output.mkdir()
    (output / 'inventory.json').symlink_to(source)
    result = invoke(repo, output, tmp_path)
    assert source.read_text() == raw
    assert result.returncode == 2


def test_benchmark_missing_metadata_remains_in_inventory(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    incomplete = repo / 'benchmarks/missing/contracts'
    incomplete.mkdir(parents=True)
    (incomplete / 'Target.sol').write_text('contract Target {}')
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert len(report['benchmarks']) == 2
    assert {e['code'] for e in report['input_errors']} == {'missing_metadata'}
    assert report['benchmarks'][1]['benchmark_id'] == 'missing'


def test_symlinked_corpus_root_cannot_be_used_as_output(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    external = tmp_path / 'external_corpus'
    kb.rename(external)
    kb.symlink_to(external, target_is_directory=True)
    source = external / 'inventory.json'
    raw = json.dumps(record())
    source.write_text(raw)
    result = invoke(repo, external, tmp_path)
    assert source.read_text() == raw
    assert result.returncode == 2


def test_output_directory_symlink_is_rejected(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    actual = tmp_path / 'actual'
    actual.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(actual, target_is_directory=True)
    result = invoke(repo, alias, tmp_path)
    assert result.returncode == 2
    assert not (actual / 'inventory.json').exists()


def test_nonfile_solidity_input_is_retained_as_error(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    (repo / 'benchmarks/demo/contracts/Broken.sol').mkdir()
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert {e['code'] for e in report['input_errors']} == {'nonfile_contract'}
    assert report['benchmarks'][0]['contract_file_count'] == 1


def test_nonobject_entries_have_explicit_counts_and_csv_rows(tmp_path):
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps([record(), 42, None]))
    output = tmp_path / 'out'
    assert invoke(repo, output, tmp_path).returncode == 2
    report = report_at(output)
    assert report['kb']['record_count'] == 1
    assert report['kb']['raw_entry_count'] == 3
    assert report['kb']['nonobject_entry_count'] == 2
    with (output / 'kb_inventory.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert [r['location'] for r in rows] == [f'src/module2_rag/data/a.json#{i}' for i in range(3)]
    assert [r['record_status'] for r in rows] == ['valid', 'nonobject', 'nonobject']


def test_metadata_fingerprint_read_failure_is_reported(tmp_path, monkeypatch):
    from scripts.audit_research_inputs import build_inventory
    repo, kb = fixture_repo(tmp_path)
    (kb / 'a.json').write_text(json.dumps(record()))
    real_read = Path.read_bytes

    def read_bytes(path):
        if path.name == 'metadata.json':
            raise PermissionError('fingerprint unavailable')
        return real_read(path)

    monkeypatch.setattr(Path, 'read_bytes', read_bytes)
    report = build_inventory(repo)
    assert report['input_valid'] is False
    assert 'unreadable_metadata' in {e['code'] for e in report['input_errors']}
    assert report['benchmarks'][0]['metadata_sha256'] is None
