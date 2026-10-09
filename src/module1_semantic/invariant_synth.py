"""Invariant synthesis via LLM + deterministic fallback.

Candidate properties are generated from the ATG and then passed through
structural and semantic admissibility checks before they can be used as search
objectives. The current artifact does not treat these checks as empirical
validation; that requires independently labelled normal/violating traces and
paired controls.

Core property families:

* ``asset_conservation`` — source/destination value relationship;
* ``authorization`` — mint/unlock requires the protocol's source/relay evidence;
* ``uniqueness`` — canonical message/transfer consumed at most once;
* ``timeliness`` — protocol-specific timeout/refund policy, generated only when
  the ATG carries explicit timeout + refund semantics.

When no LLM provider is configured, ``synthesize`` returns a deterministic
fallback containing only semantically admissible categories. It never invents
an implicit timeout/refund policy.
"""

from __future__ import annotations

import json
from typing import Any

from src.common.llm_client import LLMProvider, chat_completion_json, get_llm_client
from src.module1_semantic.prompts import load as load_prompt


_USER_PROMPT_TEMPLATE = """Analyze this bridge ATG and generate 15-20 candidate protocol properties.

ATG (truncated if long):
```json
{atg_json}
```

Generate candidates from these categories when their prerequisites are present:
1. **asset_conservation** — source/destination value preservation.
2. **authorization** — mint/unlock requires valid source + relay evidence.
3. **uniqueness** — each canonical message/transfer is consumed at most once.
4. **timeliness** — ONLY when the ATG explicitly contains a protocol timeout AND a refund/recovery rule. Do not infer a generic refund policy.

For each property provide:
- `invariant_id` (unique snake_case)
- `category` (one of the categories above)
- `description` (plain English)
- `predicate` (formal logical expression)
- `solidity_assertion` (candidate executable require/assert statement)
- `related_edges` (subset of ATG edge IDs this property depends on)

Return JSON: {{"invariants": [...]}}"""


class InvariantSynthesizer:
    """Generate structurally valid and semantically admissible candidates."""

    REQUIRED_FIELDS = {
        "invariant_id",
        "category",
        "description",
        "predicate",
        "solidity_assertion",
    }
    VALID_CATEGORIES = {
        "asset_conservation",
        "authorization",
        "uniqueness",
        "timeliness",
        "state_consistency",
    }

    def __init__(self, model: str | None = None, temperature: float = 0.0):
        # `model` kept for orchestrator backward-compat; resolved provider wins.
        self.model = model
        self.temperature = temperature

    # ------------------------------------------------------------------ public

    def synthesize(self, atg: dict) -> list[dict]:
        """Generate → schema check → semantic admissibility → deduplication.

        This method deliberately does not call the result "empirically
        validated". Normal/violating trace controls are a later evaluation
        stage and are exposed separately through :meth:`validate`.
        """
        candidates = self._llm_generate_candidates(atg)
        if not candidates:
            return self._fallback_invariants(atg)

        admissible = self._filter_semantically_admissible(candidates, atg)
        filtered = self._filter_with_traces(admissible, normal_traces=[])
        consistent = self._cross_check_consistency(filtered)

        # If every LLM candidate was structurally/semantically rejected, use
        # the deterministic admissible fallback rather than an empty set.
        return consistent if consistent else self._fallback_invariants(atg)

    def validate(self, invariants: list[dict], normal_traces: list) -> list[dict]:
        """Trace-based filtering only; not a claim of full empirical validity."""
        return self._filter_with_traces(invariants, normal_traces)

    def compile_to_solidity(self, invariant: dict) -> str:
        """Return the candidate Solidity assertion string for an invariant."""
        assertion = (invariant.get("solidity_assertion") or "").strip()
        if assertion:
            return assertion
        predicate = invariant.get("predicate") or "true"
        return f"assert({predicate});"

    # --------------------------------------------------------- LLM generation

    def _llm_generate_candidates(self, atg: dict) -> list[dict]:
        """Ask the configured LLM for candidate properties."""
        provider = self._resolve_provider()
        if provider is None:
            return []

        system = load_prompt("system_verifier.txt")
        user = _USER_PROMPT_TEMPLATE.format(
            atg_json=json.dumps(atg, ensure_ascii=False, indent=2)[:8000]
        )

        try:
            content = chat_completion_json(
                provider,
                system=system,
                user=user,
                temperature=self.temperature,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[InvariantSynth] LLM call failed: {exc}")
            return []

        return self._parse_response(content)

    def _parse_response(self, content: str) -> list[dict]:
        """Extract and schema-check the `invariants` array from an LLM response."""
        if not content:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            stripped = content.strip().lstrip("```json").lstrip("```").rstrip("```")
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                return []

        raw = data.get("invariants") if isinstance(data, dict) else data
        if not isinstance(raw, list):
            return []

        valid: list[dict] = []
        for inv in raw:
            if not isinstance(inv, dict):
                continue
            if not self._is_well_formed(inv):
                continue
            inv.setdefault("related_edges", [])
            inv.setdefault("metadata", {})
            inv["metadata"].setdefault("lifecycle_stage", "schema_valid")
            valid.append(inv)
        return valid

    def _is_well_formed(self, inv: dict) -> bool:
        if not self.REQUIRED_FIELDS.issubset(inv.keys()):
            return False
        if inv["category"] not in self.VALID_CATEGORIES:
            cat = str(inv["category"]).lower().strip()
            if cat in self.VALID_CATEGORIES:
                inv["category"] = cat
            else:
                return False
        return True

    def _resolve_provider(self) -> LLMProvider | None:
        return get_llm_client()

    # ------------------------------------------------ semantic admissibility

    @staticmethod
    def _timeliness_semantics(atg: dict) -> dict[str, Any] | None:
        """Return explicit timeout/refund semantics or ``None``.

        We require both a strictly positive timeout and a concrete refund or
        recovery function. Partial hints are insufficient: official evaluation
        must abstain rather than guess a protocol policy.
        """
        block = (atg.get("protocol_semantics") or {}).get("timeout_refund")
        if not isinstance(block, dict):
            return None
        timeout = block.get("timeout_seconds")
        refund_fn = block.get("refund_function")
        if not isinstance(timeout, int) or timeout <= 0:
            return None
        if not isinstance(refund_fn, str) or not refund_fn.strip():
            return None
        return {
            "timeout_seconds": timeout,
            "refund_function": refund_fn.strip(),
        }

    def _filter_semantically_admissible(
        self, candidates: list[dict], atg: dict
    ) -> list[dict]:
        """Drop candidates whose protocol prerequisites are not evidenced."""
        timeout_refund = self._timeliness_semantics(atg)
        admissible: list[dict] = []
        for inv in candidates:
            if inv.get("category") == "timeliness":
                if timeout_refund is None:
                    continue
                metadata = inv.setdefault("metadata", {})
                metadata.update(
                    {
                        "lifecycle_stage": "semantically_admissible",
                        "prerequisite": "explicit_timeout_refund",
                        **timeout_refund,
                    }
                )
            else:
                inv.setdefault("metadata", {}).setdefault(
                    "lifecycle_stage", "semantically_admissible"
                )
            admissible.append(inv)
        return admissible

    # ------------------------------------------------------- trace filtering

    def _filter_with_traces(
        self, candidates: list[dict], normal_traces: list
    ) -> list[dict]:
        """Drop candidates explicitly contradicted by labelled normal traces."""
        if not normal_traces:
            return list(candidates)

        filtered = []
        for inv in candidates:
            if any(self._trace_violates(inv, tr) for tr in normal_traces):
                continue
            filtered.append(inv)
        return filtered

    def _trace_violates(self, invariant: dict, trace: dict) -> bool:
        inv_id = invariant.get("invariant_id")
        expected_false = trace.get("expected_false_invariants") or []
        return inv_id in expected_false

    def _cross_check_consistency(self, invariants: list[dict]) -> list[dict]:
        """Drop duplicate predicates and duplicate IDs.

        This is deduplication, not a proof of semantic consistency.
        """
        seen_predicates: set[str] = set()
        seen_ids: set[str] = set()
        unique: list[dict] = []
        for inv in invariants:
            pred_key = (inv.get("predicate") or "").lower().replace(" ", "")
            id_key = inv.get("invariant_id", "")
            if not pred_key or not id_key:
                continue
            if pred_key in seen_predicates or id_key in seen_ids:
                continue
            seen_predicates.add(pred_key)
            seen_ids.add(id_key)
            unique.append(inv)
        return unique

    # ----------------------------------------------------------------- fallback

    def _fallback_invariants(self, atg: dict) -> list[dict[str, Any]]:
        """Deterministic, prerequisite-gated fallback for offline use."""
        edges = atg.get("edges", [])
        edge_ids = [e.get("edge_id", "") for e in edges if e.get("edge_id")]
        has_lock = any(e.get("label") == "lock" for e in edges)
        has_mint = any(e.get("label") == "mint" for e in edges)
        has_unlock = any(e.get("label") == "unlock" for e in edges)

        common_metadata = {
            "generation_mode": "deterministic_fallback",
            "lifecycle_stage": "semantically_admissible",
        }
        invariants: list[dict[str, Any]] = [
            {
                "invariant_id": "inv_asset_conservation",
                "category": "asset_conservation",
                "description": "Observed destination value must not exceed the corresponding supported source value under fixture-specific accounting.",
                "predicate": "per_transfer(minted_or_unlocked <= supported_source_value)",
                "solidity_assertion": "",
                "related_edges": edge_ids,
                "metadata": dict(common_metadata),
            },
            {
                "invariant_id": "inv_authorization",
                "category": "authorization",
                "description": "Mint/unlock requires valid prior source-chain and relay evidence for the same canonical message.",
                "predicate": "mint_or_unlock(kappa) -> valid_source_and_relay(kappa)",
                "solidity_assertion": "",
                "related_edges": edge_ids,
                "metadata": dict(common_metadata),
            },
            {
                "invariant_id": "inv_uniqueness",
                "category": "uniqueness",
                "description": "Each canonical message/transfer key may be consumed at most once.",
                "predicate": "consume_count(kappa) <= 1",
                "solidity_assertion": "",
                "related_edges": edge_ids,
                "metadata": dict(common_metadata),
            },
        ]

        timeout_refund = self._timeliness_semantics(atg)
        if timeout_refund is not None:
            invariants.append(
                {
                    "invariant_id": "inv_timeliness",
                    "category": "timeliness",
                    "description": "For this protocol's explicit timeout policy, an expired incomplete transfer must follow the documented refund/recovery rule.",
                    "predicate": "expired(kappa, timeout) && !finalized(kappa) -> refundable(kappa)",
                    "solidity_assertion": "",
                    "related_edges": edge_ids,
                    "metadata": {
                        **common_metadata,
                        "prerequisite": "explicit_timeout_refund",
                        **timeout_refund,
                    },
                }
            )

        # Asset conservation is not admissible when the graph has no source
        # lock paired with a destination mint/unlock path.
        if not (has_lock and (has_mint or has_unlock)):
            invariants = [
                inv for inv in invariants if inv["category"] != "asset_conservation"
            ] + [
                {
                    "invariant_id": "inv_state_consistency",
                    "category": "state_consistency",
                    "description": "Observed cross-chain state transitions must correspond to an allowed protocol flow.",
                    "predicate": "observed_transition in allowed_transitions",
                    "solidity_assertion": "",
                    "related_edges": edge_ids,
                    "metadata": dict(common_metadata),
                }
            ]
        return invariants
