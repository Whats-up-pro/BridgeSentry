"""Module 1 (semantic extraction + invariant synthesis) tests."""

from __future__ import annotations

from src.module1_semantic.atg_builder import ATGBuilder
from src.module1_semantic.extractor import SemanticExtractor
from src.module1_semantic.invariant_synth import InvariantSynthesizer


SIMPLE_BRIDGE = """
contract MiniBridge {
    event Deposited(address indexed user, uint256 amount);
    uint256 public totalLocked;

    function deposit(uint256 amount) external {
        require(amount > 0, "amount");
        totalLocked += amount;
        emit Deposited(msg.sender, amount);
    }

    function mint(uint256 amount) external {
        // minimal mint stub for ATG coverage
    }

    function process() external {}
}
"""


def test_extractor_builds_semantics():
    extractor = SemanticExtractor()
    sem = extractor.extract(SIMPLE_BRIDGE, "MiniBridge")
    assert "entities" in sem
    assert "functions" in sem
    assert len(sem["functions"]) >= 2


def test_atg_builder_outputs_edges():
    extractor = SemanticExtractor()
    builder = ATGBuilder()
    sem = extractor.extract(SIMPLE_BRIDGE, "MiniBridge")
    atg = builder.build(sem)
    assert len(atg.nodes) >= 1
    assert len(atg.edges) >= 1


def test_invariant_synthesizer_outputs_core_categories():
    extractor = SemanticExtractor()
    builder = ATGBuilder()
    synth = InvariantSynthesizer()
    sem = extractor.extract(SIMPLE_BRIDGE, "MiniBridge")
    atg_json = builder.to_json(builder.build(sem))
    invariants = synth.synthesize(atg_json)
    categories = {inv["category"] for inv in invariants}
    assert "authorization" in categories
    assert "uniqueness" in categories


def _lock_mint_atg() -> dict:
    return {
        "bridge_name": "test",
        "nodes": [],
        "edges": [
            {"edge_id": "e1", "label": "lock", "src": "u", "dst": "b"},
            {"edge_id": "e2", "label": "mint", "src": "b", "dst": "u"},
        ],
    }


def test_invariant_synth_fallback_without_api_uses_only_admissible_core_categories():
    """Offline fallback must not invent a timeout/refund policy."""
    synth = InvariantSynthesizer()
    invariants = synth.synthesize(_lock_mint_atg())
    categories = {inv["category"] for inv in invariants}
    assert {"asset_conservation", "authorization", "uniqueness"} <= categories
    assert "timeliness" not in categories


def test_timeliness_requires_explicit_timeout_and_refund_semantics():
    synth = InvariantSynthesizer()
    atg = _lock_mint_atg()
    atg["protocol_semantics"] = {
        "timeout_refund": {
            "timeout_seconds": 3600,
            "refund_function": "refund(bytes32)",
        }
    }

    invariants = synth.synthesize(atg)
    timeliness = [inv for inv in invariants if inv["category"] == "timeliness"]
    assert len(timeliness) == 1
    assert timeliness[0]["metadata"]["prerequisite"] == "explicit_timeout_refund"
    assert timeliness[0]["metadata"]["timeout_seconds"] == 3600
    assert timeliness[0]["metadata"]["refund_function"] == "refund(bytes32)"


def test_partial_timeout_semantics_do_not_enable_timeliness():
    synth = InvariantSynthesizer()
    atg = _lock_mint_atg()
    atg["protocol_semantics"] = {"timeout_refund": {"timeout_seconds": 3600}}
    invariants = synth.synthesize(atg)
    assert "timeliness" not in {inv["category"] for inv in invariants}


def test_invariant_synth_consistency_drops_duplicates():
    synth = InvariantSynthesizer()
    candidates = [
        {
            "invariant_id": "a",
            "predicate": "x > 0",
            "category": "asset_conservation",
            "description": "",
            "solidity_assertion": "",
        },
        {
            "invariant_id": "b",
            "predicate": "x>0",  # same after whitespace normalization
            "category": "asset_conservation",
            "description": "",
            "solidity_assertion": "",
        },
        {
            "invariant_id": "c",
            "predicate": "y == 1",
            "category": "uniqueness",
            "description": "",
            "solidity_assertion": "",
        },
    ]
    result = synth._cross_check_consistency(candidates)
    ids = [inv["invariant_id"] for inv in result]
    assert ids == ["a", "c"]


def test_invariant_synth_parses_wrapped_json_response():
    synth = InvariantSynthesizer()
    content = """```json
{"invariants": [{"invariant_id": "inv_test", "category": "uniqueness",
  "description": "d", "predicate": "p", "solidity_assertion": "require(true);"}]}
```"""
    parsed = synth._parse_response(content)
    assert len(parsed) == 1
    assert parsed[0]["invariant_id"] == "inv_test"


def test_invariant_synth_rejects_missing_fields():
    synth = InvariantSynthesizer()
    content = '{"invariants": [{"invariant_id": "x", "category": "uniqueness"}]}'
    parsed = synth._parse_response(content)
    # Missing description/predicate/solidity_assertion -> filtered out.
    assert parsed == []
