"""Fail-closed provenance contract for Option-A generated artifacts."""

from __future__ import annotations

from src.common.generation_provenance import (
    GenerationProvenance,
    canonical_sha256,
    knowledge_base_snapshot_sha256,
)


def test_canonical_sha256_is_order_independent_for_json_objects():
    left = {"b": 2, "a": {"y": 1, "x": 0}}
    right = {"a": {"x": 0, "y": 1}, "b": 2}
    assert canonical_sha256(left) == canonical_sha256(right)


def test_kb_snapshot_hash_is_order_independent_but_content_sensitive():
    kb1 = [
        {"exploit_id": "b", "root_cause": "two"},
        {"exploit_id": "a", "root_cause": "one"},
    ]
    kb2 = list(reversed(kb1))
    kb3 = [
        {"exploit_id": "a", "root_cause": "changed"},
        {"exploit_id": "b", "root_cause": "two"},
    ]
    assert knowledge_base_snapshot_sha256(kb1) == knowledge_base_snapshot_sha256(kb2)
    assert knowledge_base_snapshot_sha256(kb1) != knowledge_base_snapshot_sha256(kb3)


def test_llm_provenance_records_resolved_backend_and_retrieval_ids():
    p = GenerationProvenance.llm(
        provider="openai",
        model="gpt-example-2026-09-01",
        prompt="system\nuser",
        temperature=0.0,
        retrieved_incident_ids=["nomad_2022", "qubit_2022"],
        kb_snapshot_sha256="a" * 64,
        retry_count=1,
    ).to_dict()

    assert p["generation_mode"] == "llm"
    assert p["provider"] == "openai"
    assert p["model"] == "gpt-example-2026-09-01"
    assert p["prompt_sha256"] == canonical_sha256("system\nuser")
    assert p["temperature"] == 0.0
    assert p["retry_count"] == 1
    assert p["retrieved_incident_ids"] == ["nomad_2022", "qubit_2022"]
    assert p["kb_snapshot_sha256"] == "a" * 64
    assert p["fallback_reason"] is None


def test_fallback_provenance_never_masquerades_as_llm_generation():
    p = GenerationProvenance.deterministic_fallback(
        prompt="system\nuser",
        retrieved_incident_ids=["nomad_2022"],
        kb_snapshot_sha256="b" * 64,
        reason="provider_unavailable",
    ).to_dict()

    assert p["generation_mode"] == "deterministic_fallback"
    assert p["provider"] is None
    assert p["model"] is None
    assert p["fallback_reason"] == "provider_unavailable"
    assert p["retrieved_incident_ids"] == ["nomad_2022"]


def test_retrieval_ids_are_deduplicated_without_reordering_first_occurrence():
    p = GenerationProvenance.deterministic_fallback(
        prompt="p",
        retrieved_incident_ids=["b", "a", "b", "a", "c"],
        kb_snapshot_sha256="c" * 64,
        reason="invalid_llm_response",
    ).to_dict()
    assert p["retrieved_incident_ids"] == ["b", "a", "c"]
