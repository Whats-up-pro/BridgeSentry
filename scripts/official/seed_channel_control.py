#!/usr/bin/env python3
"""Positive control for the grounded seed channel (C3b).

Compiles each fixture's documented exploit (tests/data/seed_channel_positive_control.json,
transcribed from the deterministic Rust tests) with src/module2_rag/seed_compiler.py
into ``hypotheses.json`` (with the fixture's existing ``llm_outputs/atg.json``). Running the unchanged fuzzer
on these seeds (strict LLM-seed mode) must yield a valid exploit on the
vulnerable variant at the first execution and nothing on the patched variant;
that shows the seed channel now carries a correct exploit end to end.

The control seeds are a test artifact: they are never used in a campaign and
never shown to an LLM.

Usage: python3 scripts/official/seed_channel_control.py <out_root> <deploy_log_root> [bench ...]
  writes <out_root>/<bench>/{atg.json,hypotheses.json}
  <deploy_log_root>/<bench>/vulnerable/random/seed_1042.json supplies deploy_log.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.module2_rag.grounding import build_context  # noqa: E402
from src.module2_rag.seed_compiler import SeedCompiler  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    out_root, log_root = pathlib.Path(argv[0]), pathlib.Path(argv[1])
    control = json.loads((REPO / "tests/data/seed_channel_positive_control.json").read_text())
    benches = argv[2:] or sorted(k for k in control if not k.startswith("_"))
    rc = 0
    for b in benches:
        log = json.loads((log_root / b / "vulnerable/random/seed_1042.json").read_text())["deploy_log"]
        ctx = build_context(b, REPO / f"benchmarks/{b}/official/vulnerable",
                            REPO / f"benchmarks/{b}/official/spec.json", log, REPO)
        actions, errors = SeedCompiler(ctx).compile_actions(control[b])
        if errors:
            print(f"{b}: COMPILE ERRORS {errors}")
            rc = 1
            continue
        d = out_root / b
        d.mkdir(parents=True, exist_ok=True)
        # The harness requires a non-empty ATG but its official oracle does not read
        # it; use the same ATG file that the random-seed A-1 runs loaded.
        (d / "atg.json").write_text((REPO / f"benchmarks/{b}/llm_outputs/atg.json").read_text())
        (d / "hypotheses.json").write_text(json.dumps({"bridge_name": b, "scenarios": [{
            "scenario_id": f"{b}_positive_control", "target_invariant": "control",
            "vulnerability_class": "control", "confidence": 1.0, "actions": actions,
            "waypoints": [], "retrieved_exploits": [],
        }]}, indent=2))
        print(f"{b}: {len(actions)} actions compiled -> {d}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
