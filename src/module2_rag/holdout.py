"""Holdout regime filtering for leakage-aware seed generation.

A *regime* decides which historical incident records from the knowledge base
are visible to the RAG retriever when generating attack scenarios for a target
fixture. Separating the regimes lets us tell apart two leakage channels — what
RAG retrieves vs. what the model already remembers — and report a clean
temporal holdout (a fixture whose incident post-dates the model's training
cutoff, generated with a KB that contains no record on/after that incident).

Regimes
-------
* ``known``    — the full KB (the target incident's own record is present).
* ``no_rag``   — retrieval disabled entirely (empty pool).
* ``exact``    — drop the target incident and all its aliases.
* ``family``   — ``exact`` plus every record sharing its ``vulnerability_class``.
* ``temporal`` — ``exact`` plus every record dated on/after the incident and
                 every undated record, i.e. only strictly-earlier incidents
                 survive.

The incident registry is keyed by fixture name. ``aliases`` lists every KB
``exploit_id`` that refers to the *same* incident (duplicate curations and
``*_xscope`` mirrors). A record for a *different* incident on the same bridge
(e.g. the 2022 Ronin validator key-compromise vs. the 2024 Ronin skipped
initializer) is deliberately NOT an alias; the seed generator writes the exact
set of dropped ids into provenance, so this choice is always auditable.
"""
from __future__ import annotations

from typing import Any

REGIMES: tuple[str, ...] = ("known", "no_rag", "exact", "family", "temporal")

INCIDENTS: dict[str, dict[str, Any]] = {
    "nomad": {
        "date": "2022-08-01",
        "vulnerability_class": "fake_deposit",
        "aliases": ["nomad_20220801"],
    },
    "qubit": {
        "date": "2022-01-27",
        "vulnerability_class": "fake_deposit",
        "aliases": ["qubit_20220127", "qbridge_20220128", "qubit_bridge_xscope"],
    },
    "polynetwork": {
        "date": "2021-08-10",
        "vulnerability_class": "key_compromise",
        "aliases": ["polynetwork_20210810", "polynetwork_xscope"],
    },
    "ronin_2024": {
        "date": "2024-08-06",
        "vulnerability_class": "logic_bug",
        "aliases": ["ronin_20240806"],
    },
    "feg_bridge_2024": {
        "date": "2024-12-29",
        "vulnerability_class": "logic_bug",
        "aliases": ["feg_bridge_20241229"],
    },
    "crosscurve": {
        "date": "2026-01-31",
        "vulnerability_class": "logic_bug",
        "aliases": ["crosscurve_20260131"],
    },
    "verus": {
        "date": "2026-05-18",
        "vulnerability_class": "logic_bug",
        "aliases": ["verus_20260518"],
    },
}


def incident_for(fixture: str) -> dict[str, Any]:
    if fixture not in INCIDENTS:
        raise KeyError(
            f"no incident registry entry for fixture {fixture!r}; add it to "
            f"INCIDENTS in holdout.py before holdout seed generation"
        )
    return INCIDENTS[fixture]


def _eid(rec: dict) -> str:
    return str(rec.get("exploit_id") or rec.get("id") or "")


def regime_pool(
    records: list[dict], regime: str, fixture: str
) -> tuple[list[dict], list[str]]:
    """Return ``(pool, dropped_ids)`` for ``fixture`` under ``regime``.

    ``records`` is the full loaded KB. ``pool`` is the ordered subset of
    records visible to retrieval; ``dropped_ids`` is the sorted set of
    ``exploit_id``s removed relative to ``known`` (``[]`` for ``known``; all
    ids for ``no_rag``). ISO ``YYYY-MM-DD`` dates compare lexicographically.
    """
    if regime not in REGIMES:
        raise ValueError(f"unknown regime {regime!r}; expected one of {REGIMES}")

    all_ids = [i for i in (_eid(r) for r in records) if i]

    if regime == "known":
        return list(records), []
    if regime == "no_rag":
        return [], sorted(set(all_ids))

    inc = incident_for(fixture)
    alias = set(inc["aliases"])
    kept = [r for r in records if _eid(r) not in alias]

    if regime == "family":
        vc = inc.get("vulnerability_class")
        kept = [r for r in kept if r.get("vulnerability_class") != vc]
    elif regime == "temporal":
        cutoff = str(inc["date"])
        kept = [r for r in kept if r.get("date") and str(r["date"]) < cutoff]

    kept_ids = {_eid(r) for r in kept}
    dropped = sorted({i for i in all_ids if i not in kept_ids})
    return kept, dropped
