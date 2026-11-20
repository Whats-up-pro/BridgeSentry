#!/usr/bin/env python3
"""Aggregate ItyFuzz baseline runs (RQ2/C2) into a per-fixture x variant table.

Reads <runs_root>/<fixture>/<variant>/seed_*.result (one line:
"<detected 0|1> <tte_s or -1> rc=<rc>") and prints a CSV:
  fixture,variant,runs,detected,median_tte_s,min_tte_s,rc_nonzero

Stdlib only (runs on the HPC compute node). Censored runs (not detected) are
excluded from the TTE median, which is reported as ">budget" when fewer than
half of the runs detected.
"""
import csv, glob, os, statistics, sys

runs_root = sys.argv[1] if len(sys.argv) > 1 else "runs"
budget = sys.argv[2] if len(sys.argv) > 2 else "300"

rows = []
for vdir in sorted(glob.glob(os.path.join(runs_root, "*", "*"))):
    if not os.path.isdir(vdir):
        continue
    variant = os.path.basename(vdir)
    fixture = os.path.basename(os.path.dirname(vdir))
    dets, ttes, rc_bad, n = [], [], 0, 0
    for rf in sorted(glob.glob(os.path.join(vdir, "seed_*.result"))):
        txt = open(rf).read()
        parts = txt.split()
        if len(parts) < 3:
            continue
        n += 1
        det = int(parts[0]); tte = float(parts[1])
        rc = parts[2].split("=", 1)[1] if "=" in parts[2] else "?"
        # rc 0 = detected & exited; rc 124 = timeout (normal censored run).
        # Anything else (forge/ItyFuzz crash, missing result) is an infra failure.
        if rc not in ("0", "124"):
            rc_bad += 1
        dets.append(det)
        if det and tte >= 0:
            ttes.append(tte)
    if n == 0:
        continue
    detected = sum(dets)
    if detected > n / 2 and ttes:
        med = f"{statistics.median(ttes):.3f}"
    else:
        med = f">{budget}"
    rows.append([fixture, variant, n, f"{detected}/{n}", med,
                 f"{min(ttes):.3f}" if ttes else "-", rc_bad])

w = csv.writer(sys.stdout)
w.writerow(["fixture", "variant", "runs", "detected", "median_tte_s",
            "min_tte_s", "rc_nonzero"])
w.writerows(rows)
