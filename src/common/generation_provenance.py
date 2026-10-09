"""Stable provenance records for LLM/RAG-generated BridgeSentry artifacts.

This module is deliberately provider-agnostic. Call sites must record the
*resolved* provider/model actually used, rather than the model name requested
by a wrapper class. Deterministic fallbacks are represented as a distinct
``generation_mode`` and can never masquerade as LLM output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 over a canonical JSON representation of ``value``."""
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def knowledge_base_snapshot_sha256(records: Iterable[dict[str, Any]]) -> str:
    """Hash a KB snapshot independent of record order.

    Records are sorted by canonical JSON bytes rather than only ``exploit_id``
    so duplicate/missing IDs cannot make two different snapshots collide under
    the ordering rule. The content itself is still hashed in full.
    """
    canonical_records = sorted(
        (json.loads(_canonical_json_bytes(record).decode("utf-8")) for record in records),
        key=lambda record: _canonical_json_bytes(record),
    )
    return canonical_sha256(canonical_records)


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


@dataclass(frozen=True)
class GenerationProvenance:
    generation_mode: str
    provider: str | None
    model: str | None
    prompt_sha256: str
    temperature: float | None
    retry_count: int
    retrieved_incident_ids: tuple[str, ...]
    kb_snapshot_sha256: str
    fallback_reason: str | None = None

    @classmethod
    def llm(
        cls,
        *,
        provider: str,
        model: str,
        prompt: str,
        temperature: float,
        retrieved_incident_ids: Iterable[str],
        kb_snapshot_sha256: str,
        retry_count: int = 0,
    ) -> "GenerationProvenance":
        if not provider.strip():
            raise ValueError("resolved LLM provider is required")
        if not model.strip():
            raise ValueError("resolved LLM model is required")
        if retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        return cls(
            generation_mode="llm",
            provider=provider.strip(),
            model=model.strip(),
            prompt_sha256=canonical_sha256(prompt),
            temperature=float(temperature),
            retry_count=retry_count,
            retrieved_incident_ids=tuple(_dedupe_preserve_order(retrieved_incident_ids)),
            kb_snapshot_sha256=kb_snapshot_sha256,
            fallback_reason=None,
        )

    @classmethod
    def deterministic_fallback(
        cls,
        *,
        prompt: str,
        retrieved_incident_ids: Iterable[str],
        kb_snapshot_sha256: str,
        reason: str,
    ) -> "GenerationProvenance":
        if not reason.strip():
            raise ValueError("fallback reason is required")
        return cls(
            generation_mode="deterministic_fallback",
            provider=None,
            model=None,
            prompt_sha256=canonical_sha256(prompt),
            temperature=None,
            retry_count=0,
            retrieved_incident_ids=tuple(_dedupe_preserve_order(retrieved_incident_ids)),
            kb_snapshot_sha256=kb_snapshot_sha256,
            fallback_reason=reason.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["retrieved_incident_ids"] = list(self.retrieved_incident_ids)
        return value
