"""Seed compiler for C3b: typed LLM actions -> literals the official harness parses."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from eth_abi import encode

from src.module2_rag.grounding import ATTACKER_ADDRESS, build_context
from src.module2_rag.seed_compiler import SeedCompiler, parse_int

REPO = Path(__file__).resolve().parents[1]
A1 = REPO / "experiments/official_20261114_a1_hpc/official_runs"
CONTROL = json.loads((Path(__file__).parent / "data/seed_channel_positive_control.json").read_text())
pytestmark = pytest.mark.skipif(shutil.which("solc") is None, reason="solc not on PATH")


def _compiler(bench: str) -> SeedCompiler:
    log = A1 / bench / "vulnerable/random/seed_1042.json"
    if not log.exists():
        pytest.skip(f"no A-1 result for {bench}")
    ctx = build_context(bench, REPO / "benchmarks" / bench / "official/vulnerable",
                        REPO / "benchmarks" / bench / "official/spec.json",
                        json.loads(log.read_text())["deploy_log"], REPO)
    return SeedCompiler(ctx)


@pytest.mark.parametrize("bench", sorted(k for k in CONTROL if not k.startswith("_")))
def test_documented_exploits_compile_without_errors(bench):
    actions, errors = _compiler(bench).compile_actions(CONTROL[bench])
    assert errors == [] and len(actions) == len(CONTROL[bench])
    for a in actions:
        assert a["chain"] in {"source", "destination"} and isinstance(a["params"], dict)


def test_feg_payloads_match_the_rust_exploit_bytes():
    actions, errors = _compiler("feg_bridge_2024").compile_actions(CONTROL["feg_bridge_2024"])
    assert not errors
    # official_mode.rs feg test: encode(&[Uint(1), attacker, Uint(0)]) and (2, attacker, 500000e18)
    assert actions[0]["params"] == {"payload": "0x" + encode(["uint256", "address", "uint256"], [1, ATTACKER_ADDRESS, 0]).hex()}
    assert actions[1]["params"]["payload"] == "0x" + encode(
        ["uint256", "address", "uint256"], [2, ATTACKER_ADDRESS, 500000 * 10**18]).hex()
    assert actions[0]["contract"] == "WormholeCore" and actions[0]["chain"] == "source"


def test_polynetwork_keeps_method_string_and_top_level_names():
    actions, errors = _compiler("polynetwork").compile_actions(CONTROL["polynetwork"])
    assert not errors
    a0, a1 = actions
    assert a0["params"]["toContract"] == "EthCrossChainData"
    assert a0["params"]["method"] == "putCurEpochConPubKeyBytes(address)"
    assert a0["params"]["args"] == "0x" + encode(["address"], [ATTACKER_ADDRESS]).hex()
    assert a1["params"]["fromContract"] == "SrcDeposit" and a1["chain"] == "destination"


def test_nested_addresses_resolve_to_hex_inside_tuples():
    c = _compiler("nomad")
    actions, errors = c.compile_actions(CONTROL["nomad"])
    assert not errors
    rep = c.ctx.address_of("Representation")
    assert actions[0]["params"]["b"] == ["2000", "1000", "1", ATTACKER_ADDRESS, ATTACKER_ADDRESS, rep,
                                          str(500 * 10**18)]


def test_bytes32_is_left_padded_like_the_harness():
    actions, _ = _compiler("verus").compile_actions(CONTROL["verus"])
    assert actions[0]["params"]["exportId"] == "0x" + "00" * 31 + "0a"


@pytest.mark.parametrize("action, needle", [
    ({"contract": "manager", "function": "relayMessage", "args": []}, "unknown contract"),
    ({"contract": "LockProxy", "function": "relayMessage", "args": []}, "does not exist"),
    ({"contract": "LockProxy", "function": "unlock", "args": ["attacker"]}, "takes 2 arguments"),
    ({"contract": "LockProxy", "function": "unlock", "args": ["attacker", "lots"]}, "expected an integer"),
    ({"contract": "LockProxy", "function": "unlock", "args": ["attacker", "-1"]}, "out of range"),
    ({"contract": "SourceCrossChain", "function": "crossChain",
      "args": ["LockProxy", "unlock(address,uint256)", "encoded {to: attacker}"]}, "abi_encode"),
    ({"contract": "LockProxy", "function": "unlock", "args": ["someone", "1"]}, "neither"),
])
def test_errors_are_reported_for_repair(action, needle):
    actions, errors = _compiler("polynetwork").compile_actions([action])
    assert actions == [] and errors and needle in errors[0], errors


def test_partial_scenarios_keep_valid_actions():
    c = _compiler("polynetwork")
    actions, errors = c.compile_actions([
        {"contract": "manager", "function": "x", "args": []},
        CONTROL["polynetwork"][1],
    ])
    assert len(actions) == 1 and actions[0]["step"] == 1 and errors[0].startswith("action 1")


@pytest.mark.parametrize("raw, want", [
    (5, 5), ("123", 123), ("0x1f", 31), ("5e18", 5 * 10**18), ("1.5e18", 15 * 10**17),
    ("1_000", 1000), ("-2", -2), (True, 1),
])
def test_parse_int(raw, want):
    assert parse_int(raw) == want


def test_abi_encode_call_prefixes_the_selector():
    c = _compiler("polynetwork")
    h = c.bytes_hex({"abi_encode_call": {"signature": "transfer(address,uint256)", "values": ["attacker", "1"]}})
    assert h.startswith("0xa9059cbb") and h[10:] == encode(["address", "uint256"], [ATTACKER_ADDRESS, 1]).hex()
