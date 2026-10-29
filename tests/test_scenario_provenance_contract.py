"""A1: generated attack scenarios retain actual retrieval and generation provenance."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.common.generation_provenance import canonical_sha256, knowledge_base_snapshot_sha256
from src.module2_rag.prompts import load as load_prompt
from src.module2_rag.scenario_gen import AttackScenarioGenerator


RECORD = {"exploit_id": "qubit_2022", "vulnerability_class": "fake_deposit", "summary": "test fixture"}
ATG = {"bridge_name": "nomad", "nodes": [{"node_id": "router", "node_type": "contract"}], "edges": []}
INV = {
    "invariant_id": "inv_authorization",
    "category": "authorization",
    "description": "Each mint needs source evidence",
    "predicate": "verified(kappa)",
}


def _generator():
    gen = AttackScenarioGenerator(top_k=1)
    gen._kb_ready = True
    gen.kb.exploits = [dict(RECORD)]
    gen.embedder.search = lambda query, top_k: [dict(RECORD)]
    return gen


def test_fallback_scenario_carries_actual_kb_hash_and_no_false_llm_identity(monkeypatch):
    monkeypatch.setattr("src.module2_rag.scenario_gen.get_llm_client", lambda: None)
    scenario = _generator().generate(ATG, [INV])[0]
    p = scenario["generation_provenance"]
    assert p["generation_mode"] == "deterministic_fallback"
    assert p["provider"] is None and p["model"] is None
    assert p["fallback_reason"] == "provider_unavailable"
    assert p["retrieved_incident_ids"] == ["qubit_2022"]
    assert p["kb_snapshot_sha256"] == knowledge_base_snapshot_sha256([RECORD])
    assert scenario["retrieved_exploits"] == ["qubit_2022"]


def test_llm_scenario_audits_actual_retrieval_ids_not_llm_claims(monkeypatch):
    monkeypatch.setattr(
        "src.module2_rag.scenario_gen.get_llm_client",
        lambda: SimpleNamespace(provider_name="openai", model="pinned-model-1"),
    )
    monkeypatch.setattr(
        "src.module2_rag.scenario_gen.chat_completion_json",
        lambda *args, **kwargs: json.dumps({
            "scenario_id": "llm-scenario",
            "actions": [{"step": 1, "chain": "source", "contract": "router",
                         "function": "deposit", "params": {"amount": "1"},
                         "description": "seed"}],
            "retrieved_exploits": ["hallucinated_incident"],
        }),
    )
    gen = _generator()
    scenario = gen.generate(ATG, [INV])[0]
    p = scenario["generation_provenance"]
    prompt = load_prompt("system_adversary.txt") + "\n" + gen._build_prompt(ATG, INV, [RECORD])
    assert p["generation_mode"] == "llm"
    assert p["provider"] == "openai" and p["model"] == "pinned-model-1"
    assert p["prompt_sha256"] == canonical_sha256(prompt)
    assert p["retrieved_incident_ids"] == ["qubit_2022"]
    assert scenario["retrieved_exploits"] == ["qubit_2022"]
    # Retry count is unknown until the shared client emits per-call attempt telemetry.
    assert p["retry_count"] is None


def test_invalid_llm_response_records_fallback_instead_of_model_success(monkeypatch):
    monkeypatch.setattr(
        "src.module2_rag.scenario_gen.get_llm_client",
        lambda: SimpleNamespace(provider_name="openai", model="pinned-model-1"),
    )
    monkeypatch.setattr(
        "src.module2_rag.scenario_gen.chat_completion_json", lambda *args, **kwargs: "{}"
    )
    p = _generator().generate(ATG, [INV])[0]["generation_provenance"]
    assert p["generation_mode"] == "deterministic_fallback"
    assert p["provider"] is None and p["model"] is None
    assert p["fallback_reason"] == "llm_invalid_or_failed"
