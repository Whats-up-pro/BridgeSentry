"""Official Option-A experiment-manifest eligibility tests."""

from __future__ import annotations

from src.common.experiment_manifest import build_official_run_manifest


def _complete(**overrides):
    data = dict(
        experiment_id="exp_holdout_family_nomad_seed42",
        git_commit="a" * 40,
        benchmark_id="nomad",
        vulnerable_revision="vuln-commit",
        patched_revision="patch-commit",
        source_chain="ethereum",
        destination_chain="moonbeam",
        source_block=15_000_000,
        destination_block=2_000_000,
        evaluation_mode="official",
        oracle_version="option-a-v1",
        llm_provider="openai",
        llm_model="gpt-example-2026-09-01",
        prompt_sha256="b" * 64,
        temperature=0.0,
        retry_count=0,
        generation_mode="llm",
        kb_snapshot_sha256="c" * 64,
        retrieval_regime="leave_one_bridge_family_out",
        retrieved_incident_ids=["qubit_2022", "harmony_2022"],
        fuzzer_seed=42,
        time_budget_s=600,
        hardware_id="runner-x86_64-01",
        raw_artifact_path="results/official/run_42.json",
    )
    data.update(overrides)
    return data


def test_complete_pinned_llm_run_is_officially_eligible():
    manifest = build_official_run_manifest(_complete(), allowed_generation_modes={"llm"})
    assert manifest["official_eligible"] is True
    assert manifest["ineligibility_reasons"] == []


def test_missing_mandatory_provenance_fails_closed():
    data = _complete()
    data["git_commit"] = ""
    data["patched_revision"] = None
    data["hardware_id"] = ""
    manifest = build_official_run_manifest(data, allowed_generation_modes={"llm"})
    assert manifest["official_eligible"] is False
    reasons = " ".join(manifest["ineligibility_reasons"])
    assert "git_commit" in reasons
    assert "patched_revision" in reasons
    assert "hardware_id" in reasons


def test_legacy_mode_can_never_be_officially_eligible():
    manifest = build_official_run_manifest(
        _complete(evaluation_mode="legacy"),
        allowed_generation_modes={"llm"},
    )
    assert manifest["official_eligible"] is False
    assert any("evaluation_mode" in r for r in manifest["ineligibility_reasons"])


def test_silent_fallback_is_ineligible_when_protocol_requires_llm():
    manifest = build_official_run_manifest(
        _complete(
            generation_mode="deterministic_fallback",
            llm_provider=None,
            llm_model=None,
            prompt_sha256="d" * 64,
        ),
        allowed_generation_modes={"llm"},
    )
    assert manifest["official_eligible"] is False
    assert any("generation_mode" in r for r in manifest["ineligibility_reasons"])


def test_parser_only_ablation_can_be_eligible_when_prespecified():
    manifest = build_official_run_manifest(
        _complete(
            generation_mode="parser_only",
            llm_provider=None,
            llm_model=None,
            temperature=None,
            retry_count=0,
        ),
        allowed_generation_modes={"parser_only"},
    )
    assert manifest["official_eligible"] is True


def test_llm_mode_requires_resolved_provider_model_and_prompt_hash():
    manifest = build_official_run_manifest(
        _complete(llm_provider=None, llm_model=None, prompt_sha256=None),
        allowed_generation_modes={"llm"},
    )
    assert manifest["official_eligible"] is False
    reasons = " ".join(manifest["ineligibility_reasons"])
    assert "llm_provider" in reasons
    assert "llm_model" in reasons
    assert "prompt_sha256" in reasons


def test_holdout_run_requires_retrieval_regime_and_kb_snapshot():
    manifest = build_official_run_manifest(
        _complete(retrieval_regime="", kb_snapshot_sha256=""),
        allowed_generation_modes={"llm"},
    )
    assert manifest["official_eligible"] is False
    reasons = " ".join(manifest["ineligibility_reasons"])
    assert "retrieval_regime" in reasons
    assert "kb_snapshot_sha256" in reasons


def test_manifest_preserves_failures_and_zero_retrieval_results():
    manifest = build_official_run_manifest(
        _complete(retrieved_incident_ids=[]),
        allowed_generation_modes={"llm"},
    )
    # An empty retrieval result is scientifically meaningful and must be
    # retained rather than treated as missing provenance.
    assert manifest["retrieved_incident_ids"] == []
    assert manifest["official_eligible"] is True
