#!/usr/bin/env python3
"""Pairwise comparison of two seed configurations per fixture (C3 / C3b protocols).

For each fixture, group A is compared with group B on the vulnerable variant:
log-rank test on time to first valid exploit (runs without one censored at the
budget; computed by analyze_official.py) and Fisher's exact test on valid-exploit
runs, with Holm correction over the whole family given on the command line.

Each comparison is ``LABEL=A_ROOT:B_ROOT``, where a root is an
``official_runs``-layout directory (``<bench>/vulnerable/<seeds>/seed_*.json``)
and the seed-type directory is detected (``llm`` or ``random``). Example
(C3b family F1, grounded vs random):

  python3 scripts/official/compare_campaigns.py --out analysis/F1_vs_random \\
    known=C3B/vulnerable/known/official_runs:A1/official_runs ...

The runs are copied into a temporary ``llm``/``random`` layout (A as ``llm``,
B as ``random``) because analyze_official.py compares those two labels; the
log-rank and Fisher statistics are symmetric, so the labels carry no meaning.
"""
from __future__ import annotations

import argparse
import csv
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BENCHES = ["ronin_2024", "crosscurve", "verus", "feg_bridge_2024", "polynetwork"]


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d

    def p(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    lo, hi, p0 = max(0, c1 - r2), min(r1, c1), p(a)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9)))


def holm(pvals: list[float]) -> list[float]:
    m, adj, running = len(pvals), [0.0] * len(pvals), 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda k: pvals[k])):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def seeds_dir(root: pathlib.Path, bench: str) -> pathlib.Path:
    base = root / bench / "vulnerable"
    found = [d for d in ("llm", "random") if (base / d).is_dir()]
    if len(found) != 1:
        raise SystemExit(f"expected exactly one of llm/random under {base}, found {found}")
    return base / found[0]


def read_csv(p: pathlib.Path) -> list[dict]:
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--benches", nargs="*", default=BENCHES)
    ap.add_argument("--a-name", default="A")
    ap.add_argument("--b-name", default="B")
    ap.add_argument("comparisons", nargs="+", help="LABEL=A_ROOT:B_ROOT")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    with tempfile.TemporaryDirectory(prefix="cmp_") as tmp:
        for spec in args.comparisons:
            label, _, pair = spec.partition("=")
            a_root, _, b_root = pair.partition(":")
            a_root, b_root = pathlib.Path(a_root), pathlib.Path(b_root)
            work = pathlib.Path(tmp) / label
            for b in args.benches:
                dst = work / b / "vulnerable"
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copytree(seeds_dir(a_root, b), dst / "llm")
                shutil.copytree(seeds_dir(b_root, b), dst / "random")
            res = out / f"analyze_{label}"
            r = subprocess.run([sys.executable, str(HERE / "analyze_official.py"), str(work), "--out", str(res)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"analyze_official failed for {label}: {r.stderr[-800:]}")
            ver = read_csv(res / "analysis_ver_fpr.csv")
            lr = {x["bench"]: x for x in read_csv(res / "logrank.csv")}
            for b in args.benches:
                A = next(x for x in ver if x["bench"] == b and x["seeds"] == "llm")
                B = next(x for x in ver if x["bench"] == b and x["seeds"] == "random")
                va, na, vb, nb = int(A["valid"]), int(A["completed"]), int(B["valid"]), int(B["completed"])
                o1, e1 = float(lr[b]["O1"]), float(lr[b]["E1"])
                rows.append({
                    "comparison": label, "bench": b,
                    f"{args.a_name}_valid": f"{va}/{na}", f"{args.a_name}_median_ttve_s": A["median_ttve_s"],
                    f"{args.b_name}_valid": f"{vb}/{nb}", f"{args.b_name}_median_ttve_s": B["median_ttve_s"],
                    "direction": ("A_faster" if o1 > e1 + 1e-9 else "A_slower" if o1 < e1 - 1e-9 else "equal"),
                    "logrank_p": float(lr[b]["p"]),
                    "fisher_p": fisher_two_sided(va, na - va, vb, nb - vb),
                    "a_failed": int(A["failed"]), "b_failed": int(B["failed"]),
                })
    for col in ("logrank_p", "fisher_p"):
        for r, adj in zip(rows, holm([r[col] for r in rows])):
            r[col + "_holm"] = adj
    for r in rows:
        for k in ("logrank_p", "logrank_p_holm", "fisher_p", "fisher_p_holm"):
            r[k] = round(r[k], 6)
    with (out / "comparisons.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    a, b = args.a_name, args.b_name
    print(f"family of {len(rows)} comparisons, Holm-corrected -> {out / 'comparisons.csv'}")
    for r in rows:
        print(f"{r['comparison']:10s} {r['bench']:16s} {a}={r[a + '_valid']:6s} med={r[a + '_median_ttve_s']:>9s} | "
              f"{b}={r[b + '_valid']:6s} med={r[b + '_median_ttve_s']:>9s} | {r['direction']:8s} "
              f"logrank p={r['logrank_p']:.4f} holm={r['logrank_p_holm']:.4f} | "
              f"fisher p={r['fisher_p']:.4f} holm={r['fisher_p_holm']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
