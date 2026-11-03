#!/usr/bin/env python3
"""Summarise <runs_root>/<bench>/<variant>/<seeds>/seed_*.json.

Usage: aggregate_official.py <runs_root>   (writes <runs_root>/summary_official.csv)

Time-to-valid-exploit is reported with non-triggering runs treated as
right-censored at the budget (median is "> budget" when more than half the
runs never produce a valid exploit).
"""
import glob
import json
import os
import statistics as st
import sys

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.getcwd(), "_exp", "official_runs")
rows = []
for bench in sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))):
    for variant in ("vulnerable", "patched"):
        for seeds in ("llm", "random"):
            files = sorted(glob.glob(os.path.join(ROOT, bench, variant, seeds, "seed_*.json")))
            logs = sorted(glob.glob(os.path.join(ROOT, bench, variant, seeds, "seed_*.log")))
            if not logs:
                continue
            ds = [json.load(open(f)) for f in files]
            budget = ds[0]["time_budget_s"] if ds else None
            ttve = [d["first_valid_exploit_s"] if d["first_valid_exploit_s"] is not None else float("inf") for d in ds]
            ttve_sorted = sorted(ttve)
            med = st.median(ttve_sorted) if ttve_sorted else None
            alerts = [d["candidates_total"] for d in ds]
            rows.append({
                "bench": bench,
                "variant": variant,
                "seeds": seeds,
                "runs": len(logs),
                "completed": len(ds),
                "runs_with_valid_exploit": sum(1 for d in ds if d["valid_exploits"] > 0),
                "runs_with_any_alert": sum(1 for a in alerts if a > 0),
                "median_ttve_s": ("> budget" if med == float("inf") else round(med, 4)) if med is not None else None,
                "max_ttve_s": (round(max(t for t in ttve if t != float("inf")), 4) if any(t != float("inf") for t in ttve) else None),
                "median_iterations": st.median([d["iterations"] for d in ds]) if ds else None,
                "median_unique_pcs": st.median([d["coverage"]["fixture_unique_pcs"] for d in ds]) if ds else None,
                "actions_resolved": f'{ds[0]["semantic_resolution"]["actions_resolved"]}/{ds[0]["semantic_resolution"]["actions_total"]}' if ds and seeds == "llm" else "-",
                "budget_s": budget,
            })

hdr = ["bench", "variant", "seeds", "runs", "completed", "runs_with_valid_exploit", "runs_with_any_alert",
       "median_ttve_s", "max_ttve_s", "median_iterations", "median_unique_pcs", "actions_resolved", "budget_s"]
out = os.path.join(ROOT, "summary_official.csv")
with open(out, "w") as f:
    f.write(",".join(hdr) + "\n")
    for r in rows:
        f.write(",".join(str(r[h]) for h in hdr) + "\n")
for r in rows:
    print(r)
print("wrote", out)
