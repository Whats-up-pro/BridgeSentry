"""Behavioural tests for the official-oracle runner scripts (scripts/official/).

A fake fuzzer binary (passed through the BIN environment variable) lets the
tests check exit-status propagation, failed-run accounting, empty-RPC start-up
and backward compatibility with the frozen 2026-11-03 record, without Rust,
solc or network access.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts" / "official"
BENCH = "ronin_2024"  # has metadata.json; any official fixture works

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="runner scripts need bash")


def _fake_bin(tmp_path: Path, mode: str) -> Path:
    """mode: ok | crash | nojson | flaky (crash only for seed 2042)."""
    p = tmp_path / f"fake_fuzzer_{mode}.py"
    p.write_text(
        f"""#!{sys.executable}
import json, sys
a = sys.argv
out = a[a.index("--output") + 1]
seed = a[a.index("--seed") + 1]
mode = {mode!r}
if mode == "crash" or (mode == "flaky" and seed == "2042"):
    print("simulated fuzzer crash", file=sys.stderr)
    sys.exit(3)
if mode == "nojson":
    sys.exit(0)
json.dump({{
    "evaluation_mode": "official", "time_budget_s": 1.0,
    "first_valid_exploit_s": 0.5, "candidates_total": 1, "valid_exploits": 1,
    "iterations": 10, "coverage": {{"fixture_unique_pcs": 7}},
    "semantic_resolution": {{"actions_resolved": 0, "actions_total": 0}},
    "seed_fallback_to_random": False,
}}, open(out, "w"))
"""
    )
    p.chmod(0o755)
    return p


def _run_one(tmp_path: Path, mode: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, BIN=str(_fake_bin(tmp_path, mode)), RPC_URL="http://127.0.0.1:1")
    return subprocess.run(
        ["bash", str(SCRIPTS / "run_official.sh"), BENCH, "vulnerable", "random", "1042", "1", str(tmp_path / "out")],
        env=env, capture_output=True, text=True, check=False,
    )


def _rc_file(tmp_path: Path) -> str:
    return (tmp_path / "out" / BENCH / "vulnerable" / "random" / "seed_1042.rc").read_text().strip()


def test_run_official_propagates_fuzzer_failure(tmp_path):
    r = _run_one(tmp_path, "crash")
    assert r.returncode == 3, r.stdout + r.stderr
    assert _rc_file(tmp_path) == "3"


def test_run_official_missing_json_is_a_failure(tmp_path):
    r = _run_one(tmp_path, "nojson")
    assert r.returncode == 97
    assert _rc_file(tmp_path) == "97"


def test_run_official_success(tmp_path):
    r = _run_one(tmp_path, "ok")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _rc_file(tmp_path) == "0"


def _summary(root: Path) -> list[dict]:
    with open(root / "summary_official.csv") as f:
        return list(csv.DictReader(f))


def test_run_matrix_reports_failed_runs_and_exits_nonzero(tmp_path):
    out = tmp_path / "matrix"
    env = dict(os.environ, BIN=str(_fake_bin(tmp_path, "flaky")), SEEDS="1042 2042 3042")
    env.pop("RPC_URL", None)
    env.pop("RPC_PORT", None)
    r = subprocess.run(
        ["bash", str(SCRIPTS / "run_matrix.sh"), str(out), "1", "2", BENCH],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    rows = {(row["variant"], row["seeds"]): row for row in _summary(out)}
    for variant in ("vulnerable", "patched"):
        row = rows[(variant, "random")]
        assert row["runs"] == "3"
        assert row["completed"] == "2"
        assert row["runs_failed"] == "1"
        assert row["runs_with_valid_exploit"] == "2"  # the crashed run is not counted, not censored


def test_run_matrix_all_ok_exits_zero(tmp_path):
    out = tmp_path / "matrix_ok"
    env = dict(os.environ, BIN=str(_fake_bin(tmp_path, "ok")), SEEDS="1042")
    env.pop("RPC_URL", None)
    r = subprocess.run(
        ["bash", str(SCRIPTS / "run_matrix.sh"), str(out), "1", "1", BENCH],
        env=env, capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert all(row["runs_failed"] == "0" for row in _summary(out))


def test_aggregate_reproduces_frozen_round1_columns(tmp_path):
    """Records without .rc files keep their meaning: first 13 columns unchanged."""
    frozen = REPO / "experiments" / "official_20261103"
    runs = tmp_path / "official_runs"
    shutil.copytree(frozen / "official_runs", runs)
    subprocess.run([sys.executable, str(SCRIPTS / "aggregate_official.py"), str(runs)],
                   check=True, capture_output=True, text=True)
    new = (runs / "summary_official.csv").read_text().splitlines()
    old = (frozen / "summary_official.csv").read_text().splitlines()
    assert len(new) == len(old)
    for n, o in zip(new, old):
        assert n.split(",")[:13] == o.split(",")[:13]
        if not n.startswith("bench,"):
            assert n.split(",")[13:] == ["0", "0"]
