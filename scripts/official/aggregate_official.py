#!/usr/bin/env python3
"""Summarise <runs_root>/<bench>/<variant>/<seeds>/seed_*.{log,json,rc}.

Usage: aggregate_official.py <runs_root>   (writes <runs_root>/summary_official.csv)

A run is identified by its log file. It counts as *completed* only if its
result JSON exists and its recorded exit status (seed_<n>.rc, written by
run_official.sh) is 0; records produced before .rc files existed are treated
as exit status 0 when the JSON exists. Every other run is *failed* (crash,
missing JSON, configuration error) and is excluded from all outcome columns:
a failed run is never counted as "completed without a valid exploit" and is
never right-censored.

Time-to-valid-exploit is computed over completed runs, with completed runs
that never produce a valid exploit right-censored at the budget (median is
"> budget" when more than half of them are censored).

Columns 1-13 are unchanged from the 2026-11-03 version; `runs_failed` and
`runs_seed_fallback` (result version >= 2: runs whose requested seed source
fell back to random) are appended.
"""
import glob
import json
import os
import statistics as st
import sys


def exit_status(json_path, rc_path):
    if os.path.exists(rc_path):
        try:
            return int(open(rc_path).read().strip())
        except ValueError:
            return -1
    return 0 if os.path.exists(json_path) else -1


def load_runs(run_dir):
    completed, failed = [], 0
    for log in sorted(glob.glob(os.path.join(run_dir, "seed_*.log"))):
        stem = log[: -len(".log")]
        js, rc = stem + ".json", stem + ".rc"
        status = exit_status(js, rc)
        if status == 0 and os.path.exists(js):
            try:
                completed.append(json.load(open(js)))
                continue
            except (OSError, ValueError):
                pass
        failed += 1
    return completed, failed


def summarise(root):
    rows = []
    for bench in sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))):
        for variant in ("vulnerable", "patched"):
            for seeds in ("llm", "random"):
                run_dir = os.path.join(root, bench, variant, seeds)
                logs = glob.glob(os.path.join(run_dir, "seed_*.log"))
                if not logs:
                    continue
                ds, failed = load_runs(run_dir)
                budget = ds[0]["time_budget_s"] if ds else None
                ttve = [d["first_valid_exploit_s"] if d["first_valid_exploit_s"] is not None else float("inf") for d in ds]
                med = st.median(sorted(ttve)) if ttve else None
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
                    "runs_failed": failed,
                    "runs_seed_fallback": sum(1 for d in ds if d.get("seed_fallback_to_random")),
                })
    return rows


HDR = ["bench", "variant", "seeds", "runs", "completed", "runs_with_valid_exploit", "runs_with_any_alert",
       "median_ttve_s", "max_ttve_s", "median_iterations", "median_unique_pcs", "actions_resolved", "budget_s",
       "runs_failed", "runs_seed_fallback"]


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.getcwd(), "_exp", "official_runs")
    rows = summarise(root)
    out = os.path.join(root, "summary_official.csv")
    with open(out, "w") as f:
        f.write(",".join(HDR) + "\n")
        for r in rows:
            f.write(",".join(str(r[h]) for h in HDR) + "\n")
    for r in rows:
        print(r)
    print("wrote", out)
    failed = sum(r["runs_failed"] for r in rows)
    if failed:
        print(f"WARNING: {failed} failed run(s); see seed_*.rc / seed_*.log", file=sys.stderr)


if __name__ == "__main__":
    main()
