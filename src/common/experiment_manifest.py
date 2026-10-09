"""Strict Option-A experiment manifest and official-eligibility gate.

The manifest is intentionally conservative: headline/primary-table runs must
carry enough provenance to reconstruct the code revision, fixture/fork,
generation mode, retrieval snapshot, random seed, hardware allocation, oracle
version, and retained raw artifact. Missing mandatory provenance makes the run
ineligible rather than being filled from ambient defaults.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


_ALWAYS_REQUIRED = (
    "experiment_id",
    "git_commit",
    "benchmark_id",
    "vulnerable_revision",
    "patched_revision",
    "source_chain",
    "destination_chain",
    "source_block",
    "destination_block",
    "evaluation_mode",
    "oracle_version",
    "generation_mode",
    "kb_snapshot_sha256",
    "retrieval_regime",
    "retrieved_incident_ids",
    "fuzzer_seed",
    "time_budget_s",
    "hardware_id",
    "raw_artifact_path",
)

_LLM_REQUIRED = (
    "llm_provider",
    "llm_model",
    "prompt_sha256",
    "temperature",
    "retry_count",
)


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _dedupe_preserve_order(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_official_run_manifest(
    data: dict[str, Any],
    *,
    allowed_generation_modes: set[str] | frozenset[str],
) -> dict[str, Any]:
    """Return a normalized manifest with fail-closed eligibility fields.

    ``allowed_generation_modes`` is part of the pre-specified experiment
    protocol. A deterministic fallback therefore cannot silently enter an LLM
    treatment; parser-only and other ablations are eligible only when that mode
    is explicitly allowed for the run family.
    """
    manifest = deepcopy(data)
    reasons: list[str] = []

    for field in _ALWAYS_REQUIRED:
        if field not in manifest or _missing(manifest.get(field)):
            reasons.append(f"missing mandatory field: {field}")

    mode = manifest.get("evaluation_mode")
    if mode != "official":
        reasons.append("evaluation_mode must be official")

    generation_mode = manifest.get("generation_mode")
    if generation_mode not in allowed_generation_modes:
        reasons.append(
            "generation_mode is not allowed by the pre-specified experiment protocol"
        )

    if generation_mode == "llm":
        for field in _LLM_REQUIRED:
            if field not in manifest or _missing(manifest.get(field)):
                reasons.append(f"missing mandatory LLM field: {field}")

    # Non-LLM treatments must not accidentally inherit a provider/model label
    # from a previous run. Keeping them null makes aggregation unambiguous.
    if generation_mode != "llm":
        manifest["llm_provider"] = None
        manifest["llm_model"] = None
        manifest["temperature"] = None
        manifest.setdefault("retry_count", 0)

    retrieved = manifest.get("retrieved_incident_ids")
    if isinstance(retrieved, list):
        manifest["retrieved_incident_ids"] = _dedupe_preserve_order(retrieved)
    elif retrieved is not None:
        reasons.append("retrieved_incident_ids must be a list")

    # Basic value-domain checks catch ambiguous or unusable manifests without
    # pretending to validate the underlying benchmark itself.
    for field in ("source_block", "destination_block", "time_budget_s"):
        value = manifest.get(field)
        if value is not None and (not isinstance(value, int) or value <= 0):
            reasons.append(f"{field} must be a positive integer")

    seed = manifest.get("fuzzer_seed")
    if seed is not None and (not isinstance(seed, int) or seed < 0):
        reasons.append("fuzzer_seed must be a non-negative integer")

    retry_count = manifest.get("retry_count")
    if retry_count is not None and (
        not isinstance(retry_count, int) or retry_count < 0
    ):
        reasons.append("retry_count must be a non-negative integer")

    # De-duplicate reasons while preserving diagnostic order.
    reasons = list(dict.fromkeys(reasons))
    manifest["official_eligible"] = not reasons
    manifest["ineligibility_reasons"] = reasons
    return manifest
