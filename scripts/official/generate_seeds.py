#!/usr/bin/env python3
"""Generate Module 1 (ATG + invariants) and Module 2 (attack scenarios) seed
artifacts for one official fixture under a chosen LLM backend and KB holdout
regime.

Writes ``atg.json``, ``hypotheses.json`` and ``provenance.json`` into the
output directory and appends one row to a CSV cost ledger. The generated
``atg.json`` / ``hypotheses.json`` are exactly what ``scripts/official/
run_official.sh`` consumes via its ``SEED_DIR`` override.

Design rules (match AGENTS.md evidence policy):
  * One LLM backend per run — the other provider's key is removed from the
    environment before resolution, so backends can never silently mix.
  * Leakage-aware KB: the retriever only sees ``src.module2_rag.holdout``'s
    regime pool; the exact dropped incident ids are recorded in provenance.
  * ``--parser-only`` runs *all* of Module 1 with no LLM (Slither/regex), while
    Module 2 still uses the backend (A5 ablation).
  * Honest token/latency accounting (A8): real API calls are counted at the
    OpenAI client boundary (cache disabled), split per module.
  * Deterministic fallbacks can never masquerade as LLM output: every scenario
    is tagged ``llm`` or ``deterministic_fallback`` and the counts are logged.

Usage:
  python -I scripts/official/generate_seeds.py \
      --bench nomad --model gpt-oss --regime exact \
      [--parser-only] [--temperature 0.3] [--top-k 5] \
      [--contracts-dir benchmarks/nomad/official/vulnerable] \
      [--out benchmarks/nomad/official/llm_outputs/gpt-oss/exact] \
      [--ledger experiments/<run>/cost_ledger.csv]
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as _dt
import json
import os
import pathlib
import platform
import socket
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

# Determinism + honest accounting knobs set before any LLM/embedding work.
os.environ["BRIDGESENTRY_LLM_CACHE"] = "0"          # count every real API call
os.environ["BRIDGESENTRY_EMBEDDING_CACHE"] = "0"    # reproducible retrieval label
os.environ.setdefault("PYTHONHASHSEED", "0")        # hash-fallback determinism

BACKENDS = {
    # alias -> (provider_name expected from get_llm_client, required env key)
    "gpt-oss": ("nvidia", "NVIDIA_API_KEY"),
    "gpt5": ("openai", "OPENAI_API_KEY"),
    "openai": ("openai", "OPENAI_API_KEY"),
}


def _repo_rel(p: pathlib.Path) -> str:
    """Repo-relative string for a path that may be relative (cwd==REPO) or absolute."""
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip()
    except Exception:
        return "unknown"


@contextlib.contextmanager
def _no_llm_env():
    """Temporarily remove provider keys so get_llm_client() returns None."""
    saved = {}
    for k in ("NVIDIA_API_KEY", "OPENAI_API_KEY"):
        if k in os.environ:
            saved[k] = os.environ.pop(k)
    try:
        yield
    finally:
        os.environ.update(saved)


def _install_usage_meter():
    """Wrap the OpenAI client create() so real API calls/tokens are counted.

    Returns (usage_dict, restore_fn). Cache is disabled above, so each counted
    call is a real network round-trip.
    """
    from openai.resources.chat import completions as _c

    orig = _c.Completions.create
    usage = {"calls": 0, "prompt": 0, "completion": 0}

    def wrapped(self, *a, **k):
        r = orig(self, *a, **k)
        u = getattr(r, "usage", None)
        if u is not None:
            usage["calls"] += 1
            usage["prompt"] += int(getattr(u, "prompt_tokens", 0) or 0)
            usage["completion"] += int(getattr(u, "completion_tokens", 0) or 0)
        return r

    _c.Completions.create = wrapped

    def restore():
        _c.Completions.create = orig

    return usage, restore


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench", required=True)
    ap.add_argument("--model", required=True, choices=sorted(BACKENDS))
    ap.add_argument("--regime", required=True)
    ap.add_argument("--parser-only", action="store_true")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--contracts-dir", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--ledger", default=None)
    args = ap.parse_args()

    from src.module2_rag.holdout import REGIMES
    if args.regime not in REGIMES:
        ap.error(f"--regime must be one of {REGIMES}")

    expected_provider, req_key = BACKENDS[args.model]

    # ---- enforce a single backend: drop the *other* provider's key ---------
    from src.common.llm_client import _is_placeholder  # type: ignore
    if _is_placeholder(os.getenv(req_key)):
        print(f"[generate_seeds] backend {args.model!r} needs a real {req_key}; "
              f"refusing to run (no silent fallback).", file=sys.stderr)
        return 2
    other_key = "OPENAI_API_KEY" if req_key == "NVIDIA_API_KEY" else "NVIDIA_API_KEY"
    os.environ.pop(other_key, None)

    from src.common.llm_client import get_llm_client, effective_temperature
    provider = get_llm_client(prefer=expected_provider)
    if provider is None or provider.provider_name != expected_provider:
        got = None if provider is None else provider.provider_name
        print(f"[generate_seeds] resolved provider {got!r} != expected "
              f"{expected_provider!r}; aborting to avoid backend mixing.",
              file=sys.stderr)
        return 2
    resolved_model = provider.model
    temp_eff = effective_temperature(resolved_model, args.temperature)

    contracts_dir = pathlib.Path(
        args.contracts_dir or f"benchmarks/{args.bench}/official/vulnerable"
    )
    sols = sorted(contracts_dir.glob("*.sol"))
    if not sols:
        print(f"[generate_seeds] no .sol under {contracts_dir}", file=sys.stderr)
        return 2

    out_dir = pathlib.Path(
        args.out
        or (f"benchmarks/{args.bench}/official/llm_outputs/{args.model}/"
            + (f"parser_only/{args.regime}" if args.parser_only else args.regime))
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- detect embedding backend label (sentence-transformers vs hash) ----
    try:
        import sentence_transformers  # noqa: F401
        emb_backend = "sentence_transformers:all-MiniLM-L6-v2"
    except Exception:
        emb_backend = "hash_fallback_256d"

    from src.module1_semantic.extractor import SemanticExtractor
    from src.module1_semantic.atg_builder import ATGBuilder
    from src.module1_semantic.invariant_synth import InvariantSynthesizer
    from src.module2_rag.scenario_gen import AttackScenarioGenerator
    from src.module2_rag.knowledge_base import ExploitKnowledgeBase
    from src.common.generation_provenance import (
        knowledge_base_snapshot_sha256,
        canonical_sha256,
    )
    from src.module2_rag.holdout import regime_pool

    usage, restore_meter = _install_usage_meter()
    try:
        # ---------------- Module 1 (optionally LLM-free for parser-only) ----
        t0 = time.time()
        ctx = _no_llm_env() if args.parser_only else contextlib.nullcontext()
        with ctx:
            ex = SemanticExtractor()
            ab = ATGBuilder()
            isy = InvariantSynthesizer()
            merged = {"entities": [], "functions": [], "asset_flows": [], "guards": []}
            for p in sols:
                sem = ex.extract_from_file(str(p))
                for key in merged:
                    merged[key].extend(sem.get(key, []))
            atg = ab.build(merged)
            atg_json = ab.to_json(atg)
            atg_json["bridge_name"] = args.bench
            inv = isy.synthesize(atg_json)
            inv = isy.validate(inv, normal_traces=[])
            atg_json["invariants"] = inv
        m1_calls_end = usage["calls"]
        t_m1 = time.time() - t0

        # ---------------- KB regime pool ------------------------------------
        kb = ExploitKnowledgeBase()
        kb.load()
        full_kb = list(kb.exploits)
        kb_full_sha = knowledge_base_snapshot_sha256(full_kb)
        pool, dropped_ids = regime_pool(full_kb, args.regime, args.bench)
        pool_ids = sorted(str(r.get("exploit_id") or r.get("id") or "") for r in pool)

        # ---------------- Module 2 (LLM backend + injected regime KB) -------
        gen = AttackScenarioGenerator(top_k=args.top_k, temperature=args.temperature)
        gen.kb.exploits = list(pool)
        gen._ensure_kb = lambda: None  # type: ignore[method-assign]  # we inject the KB ourselves
        if args.regime == "no_rag" or not pool:
            gen._kb_ready = False
        else:
            gen.embedder.build_index(pool)
            gen._kb_ready = True

        # tag each scenario's generation mode so fallbacks are never counted as LLM
        orig_try = gen._try_llm_generate
        orig_fb = gen._fallback_scenario

        def _try_tagged(atg_, inv_, retrieved_):
            s = orig_try(atg_, inv_, retrieved_)
            if s is not None and gen._scenario_usable(s):
                s["__gen_mode"] = "llm"
            return s

        def _fb_tagged(*a, **k):
            s = orig_fb(*a, **k)
            s["__gen_mode"] = "deterministic_fallback"
            return s

        gen._try_llm_generate = _try_tagged  # type: ignore[method-assign]
        gen._fallback_scenario = _fb_tagged  # type: ignore[method-assign]

        t1 = time.time()
        scenarios = gen.generate(atg_json, inv)
        t_m2 = time.time() - t1

        modes = [s.pop("__gen_mode", "llm") for s in scenarios]
        n_llm = sum(1 for m in modes if m == "llm")
        n_fallback = sum(1 for m in modes if m == "deterministic_fallback")
        actions_total = sum(len(s.get("actions", [])) for s in scenarios)
        actions_mapped = sum(
            1 for s in scenarios for a in s.get("actions", [])
            if a.get("contract") and a.get("function")
        )
        per_scenario = [
            {
                "scenario_id": s.get("scenario_id"),
                "gen_mode": m,
                "retrieved_exploits": s.get("retrieved_exploits", []),
                "n_actions": len(s.get("actions", [])),
            }
            for s, m in zip(scenarios, modes)
        ]
    finally:
        restore_meter()

    # ---------------- write artifacts ---------------------------------------
    (out_dir / "atg.json").write_text(
        json.dumps(atg_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "hypotheses.json").write_text(
        json.dumps({"bridge_name": args.bench, "scenarios": scenarios},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    provenance = {
        "schema": "generate_seeds/v1",
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "fixture": args.bench,
        "contracts": sorted(_repo_rel(p) for p in sols),
        "backend_alias": args.model,
        "provider": provider.provider_name,
        "model": resolved_model,
        "parser_only_module1": args.parser_only,
        "temperature_requested": args.temperature,
        "temperature_effective": temp_eff,  # null == omitted (reasoning model default)
        "top_k": args.top_k,
        "regime": args.regime,
        "kb_snapshot_sha256_full": kb_full_sha,
        "kb_pool_sha256": canonical_sha256(sorted(pool_ids)),
        "kb_pool_size": len(pool),
        "kb_pool_ids": pool_ids,
        "kb_dropped_ids": dropped_ids,
        "embedding_backend": emb_backend,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "module1": {
            "llm_used": not args.parser_only,
            "api_calls": m1_calls_end,
            "n_contracts": len(sols),
            "n_nodes": len(atg_json.get("nodes", [])),
            "n_edges": len(atg_json.get("edges", [])),
            "n_invariants": len(inv),
            "latency_s": round(t_m1, 3),
        },
        "module2": {
            "n_scenarios": len(scenarios),
            "n_llm": n_llm,
            "n_fallback": n_fallback,
            "actions_total": actions_total,
            "actions_mapped": actions_mapped,
            "latency_s": round(t_m2, 3),
            "per_scenario": per_scenario,
        },
        "usage": {
            "api_calls": usage["calls"],
            "prompt_tokens": usage["prompt"],
            "completion_tokens": usage["completion"],
            "total_tokens": usage["prompt"] + usage["completion"],
        },
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---------------- append cost-ledger row --------------------------------
    if args.ledger:
        ledger = pathlib.Path(args.ledger)
        ledger.parent.mkdir(parents=True, exist_ok=True)
        new = not ledger.exists()
        with ledger.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow([
                    "generated_at_utc", "fixture", "backend", "model", "regime",
                    "parser_only", "n_scenarios", "n_llm", "n_fallback",
                    "actions_total", "actions_mapped", "api_calls",
                    "prompt_tokens", "completion_tokens", "m1_latency_s",
                    "m2_latency_s", "embedding_backend", "kb_pool_size",
                ])
            w.writerow([
                provenance["generated_at_utc"], args.bench, args.model,
                resolved_model, args.regime, int(args.parser_only),
                len(scenarios), n_llm, n_fallback, actions_total, actions_mapped,
                usage["calls"], usage["prompt"], usage["completion"],
                round(t_m1, 3), round(t_m2, 3), emb_backend, len(pool),
            ])

    print(json.dumps({
        "out": str(out_dir), "provider": provider.provider_name,
        "model": resolved_model, "regime": args.regime,
        "parser_only": args.parser_only, "scenarios": len(scenarios),
        "llm": n_llm, "fallback": n_fallback, "actions_mapped": actions_mapped,
        "actions_total": actions_total, "kb_pool_size": len(pool),
        "dropped": len(dropped_ids), "api_calls": usage["calls"],
        "tokens": usage["prompt"] + usage["completion"],
        "embedding_backend": emb_backend,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
