#!/usr/bin/env python3
"""Aggregate _exp/runs/<cond>/<bench>/seed_*.json into a per-benchmark table."""
import csv
import glob
import json
import os
import statistics as st
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")
BENCHES = ["nomad", "qubit", "pgala", "polynetwork", "wormhole", "socket", "ronin",
           "harmony", "multichain", "orbit", "fegtoken", "gempad", "nomad_patched"]
CONDS = ["syn", "real", "exec"]

rows = []
for b in BENCHES:
    for c in CONDS:
        files = sorted(glob.glob(os.path.join(ROOT, c, b, "seed_*.json")))
        logs = sorted(glob.glob(os.path.join(ROOT, c, b, "seed_*.log")))
        if not files and not logs:
            continue
        n_runs = len(logs)
        ok = 0
        trig = 0
        viol, inv, first, bbs, bbd, iters = [], [], [], [], [], []
        err = ""
        for lf in logs:
            jf = lf[:-4] + ".json"
            if not os.path.exists(jf):
                txt = open(lf, errors="ignore").read()
                for line in txt.splitlines():
                    if "panic" in line or "ERROR" in line or "Deployment" in line:
                        err = line.strip()[:160]
                        break
                continue
            ok += 1
            d = json.load(open(jf))
            v = d.get("violations", [])
            viol.append(len(v))
            inv.append(len({x["invariant_id"] for x in v}))
            if v:
                trig += 1
                first.append(min(x["detected_at_s"] for x in v))
            cov = d.get("coverage", {})
            bbs.append(cov.get("basic_blocks_source", 0))
            bbd.append(cov.get("basic_blocks_dest", 0))
            iters.append(d.get("stats", {}).get("total_iterations", 0))
        rows.append({
            "bench": b, "cond": c, "runs": n_runs, "completed": ok,
            "runs_triggered": trig,
            "median_violations": st.median(viol) if viol else None,
            "median_distinct_invariants": st.median(inv) if inv else None,
            "median_first_trigger_s": round(st.median(first), 4) if first else None,
            "max_first_trigger_s": round(max(first), 4) if first else None,
            "median_bb_source": st.median(bbs) if bbs else None,
            "median_bb_dest": st.median(bbd) if bbd else None,
            "median_iterations": st.median(iters) if iters else None,
            "error": err,
        })

out = os.path.join(os.path.dirname(ROOT), "summary.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

fmt = "{:<14}{:<5}{:>5}{:>5}{:>6}{:>8}{:>6}{:>9}{:>8}{:>8}  {}"
print(fmt.format("bench", "cond", "runs", "done", "trig", "viol", "inv", "t1(s)", "bbSrc", "bbDst", "error"))
for r in rows:
    print(fmt.format(r["bench"], r["cond"], r["runs"], r["completed"], r["runs_triggered"],
                     str(r["median_violations"]), str(r["median_distinct_invariants"]),
                     str(r["median_first_trigger_s"]), str(r["median_bb_source"]),
                     str(r["median_bb_dest"]), r["error"]))
print("\nwrote", out)
