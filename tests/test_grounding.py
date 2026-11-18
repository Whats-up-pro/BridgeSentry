"""Grounding context for C3b: comment removal must not leak the answer, must not
break the code, and the prompt must withhold the fixture's answer fields."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.module2_rag.grounding import (
    ATTACKER_ADDRESS,
    build_context,
    parse_deploy_log,
    source_closure,
    strip_solidity_comments,
    write_sanitized_tree,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURES = ["nomad", "qubit", "polynetwork", "ronin_2024", "feg_bridge_2024", "crosscurve", "verus"]
A1 = REPO / "experiments/official_20261114_a1_hpc/official_runs"
HAVE_SOLC = shutil.which("solc") is not None

# Words that only ever occur in the fixtures' explanatory comments.
LEAK_PATTERNS = [
    r"vulnerab", r"root\s*cause", r"exploit", r"incident", r"patched", r"\bbug\b",
    r"certik", r"peckshield", r"halborn", r"blocksec", r"\b20(21|22|23|24|25|26)\b",
]


def _deploy_log(bench: str) -> list[str]:
    p = A1 / bench / "vulnerable/random/seed_1042.json"
    if not p.exists():
        pytest.skip(f"no A-1 result for {bench}")
    return json.loads(p.read_text())["deploy_log"]


def test_strip_line_and_block_comments():
    src = 'contract A { // owner check\n  uint x = 1; /* VULNERABLE: no check */ uint y = 2;\n  /// @notice natspec\n}\n'
    out = strip_solidity_comments(src)
    assert "owner check" not in out and "VULNERABLE" not in out and "natspec" not in out
    assert "uint x = 1;" in out and "uint y = 2;" in out


def test_strip_keeps_comment_markers_inside_strings():
    src = 'string a = "http://x/*y*/"; string b = \'//c\'; string c = "q\\"//d";\n'
    out = strip_solidity_comments(src)
    assert '"http://x/*y*/"' in out and "'//c'" in out and '"q\\"//d"' in out


def test_strip_does_not_glue_tokens():
    assert strip_solidity_comments("uint/*x*/y;").strip() == "uint y;"


def test_parse_deploy_log():
    m = parse_deploy_log(["SrcFEG=0x9B137463d4E7986D7f535f9B79e28b4EF1938E9b@source (OfficialToken)"])
    assert m["SrcFEG"] == {"address": "0x9B137463d4E7986D7f535f9B79e28b4EF1938E9b",
                           "side": "source", "contract": "OfficialToken"}
    with pytest.raises(ValueError):
        parse_deploy_log(["garbage"])


@pytest.mark.parametrize("bench", FIXTURES)
def test_sanitized_sources_carry_no_answer_hints(bench):
    for p in source_closure(REPO / "benchmarks" / bench / "official/vulnerable"):
        text = strip_solidity_comments(p.read_text(encoding="utf-8"))
        for pat in LEAK_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            assert m is None, f"{bench}/{p.name}: {pat!r} survives comment removal: {m.group(0)!r}"


@pytest.mark.skipif(not HAVE_SOLC, reason="solc not on PATH")
@pytest.mark.parametrize("bench", FIXTURES)
def test_sanitized_tree_still_compiles_and_hides_directory(bench, tmp_path):
    files = write_sanitized_tree(REPO / "benchmarks" / bench / "official/vulnerable", tmp_path)
    assert files and all("vulnerable" not in str(f.relative_to(tmp_path)) for f in files)
    r = subprocess.run(["solc", "--combined-json", "abi", "--base-path", str(tmp_path),
                        "--allow-paths", str(tmp_path), *map(str, files)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:500]


@pytest.mark.skipif(not HAVE_SOLC, reason="solc not on PATH")
@pytest.mark.parametrize("bench", FIXTURES)
def test_prompt_withholds_answer_fields(bench):
    spec_path = REPO / "benchmarks" / bench / "official/spec.json"
    spec = json.loads(spec_path.read_text())
    ctx = build_context(bench, REPO / "benchmarks" / bench / "official/vulnerable", spec_path,
                        _deploy_log(bench), REPO)
    block = ctx.prompt_block()
    assert spec["notes"][:60] not in block
    for word in ("release_entrypoints", "victim", "patched", "vulnerable", "notes"):
        assert word not in block.lower(), word
    for pat in LEAK_PATTERNS:
        assert re.search(pat, block, re.IGNORECASE) is None, pat
    # every deployed instance is described, with its ABI
    for d in spec["deploy"]:
        assert f"- {d['name']}: {d['contract']}" in block
    assert ctx.attacker == ATTACKER_ADDRESS
    prov = ctx.provenance()
    assert "spec.notes" in prov["withheld"] and len(prov["sanitized_sources_sha256"]) == 64
