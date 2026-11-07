#!/usr/bin/env python3
"""Statistical analysis of official-oracle fuzzing runs (todo A7).

Consumes the same frozen layout as aggregate_official.py
(<runs_root>/<bench>/<variant>/<seeds>/seed_*.{json,rc,log}) and produces, for
the paper:

  * VER (valid-exploit rate) and FPR (any-alert rate) per (bench, variant,
    seeds) with exact Clopper-Pearson 95% confidence intervals;
  * Kaplan-Meier survival of time-to-valid-exploit (censored at the budget for
    completed runs that never produced one) as a step table;
  * a two-group log-rank test (llm vs random) per bench on the vulnerable
    variant.

Run accounting matches aggregate_official.py exactly: a run counts only if its
JSON exists and seed_<n>.rc is 0 (or .rc absent but JSON present); every other
run is *failed* and excluded (never censored, never a "completed-without-
exploit").

No third-party dependency is required: the incomplete-beta inverse (Clopper-
Pearson) and the chi-square(1) tail (log-rank p) are implemented here. A PDF
survival plot is emitted only if matplotlib is importable; otherwise the step
table is the artifact. ``--selftest`` checks the statistics against textbook
values and exits.

Usage:
  python analyze_official.py <runs_root> [--out DIR] [--alpha 0.05] [--plot]
  python analyze_official.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import statistics as st
import sys

# --------------------------------------------------------------------------- #
# incomplete beta + Clopper-Pearson                                           #
# --------------------------------------------------------------------------- #

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the regularized incomplete beta (Numerical Recipes)."""
    MAXIT, EPS, FPMIN = 200, 3.0e-12, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def betainv(p: float, a: float, b: float) -> float:
    """Inverse of I_x(a,b) in x for given p via bisection (monotone in x)."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betainc(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided CI for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else betainv(alpha / 2.0, k, n - k + 1)
    hi = 1.0 if k == n else betainv(1.0 - alpha / 2.0, k + 1, n - k)
    return (lo, hi)


# --------------------------------------------------------------------------- #
# Kaplan-Meier + log-rank                                                     #
# --------------------------------------------------------------------------- #

def km_steps(times: list[float], events: list[int]) -> list[dict]:
    """Kaplan-Meier survival step table. events: 1=valid exploit, 0=censored."""
    order = sorted(range(len(times)), key=lambda i: times[i])
    n = len(times)
    at_risk = n
    surv = 1.0
    steps = [{"t": 0.0, "n_risk": n, "d": 0, "c": 0, "survival": 1.0}]
    i = 0
    ts = [times[o] for o in order]
    es = [events[o] for o in order]
    while i < n:
        t = ts[i]
        j = i
        d = c = 0
        while j < n and ts[j] == t:
            if es[j] == 1:
                d += 1
            else:
                c += 1
            j += 1
        if d > 0:
            surv *= (1.0 - d / at_risk)
        steps.append({"t": t, "n_risk": at_risk, "d": d, "c": c, "survival": surv})
        at_risk -= (d + c)
        i = j
    return steps


def logrank(times1, ev1, times2, ev2) -> dict:
    """Two-group log-rank test. Returns O1,E1,V,chi2,p (chi-square 1 df tail)."""
    all_event_times = sorted({t for t, e in zip(times1, ev1) if e == 1}
                             | {t for t, e in zip(times2, ev2) if e == 1})
    O1 = E1 = V = 0.0
    for t in all_event_times:
        n1 = sum(1 for x in times1 if x >= t)
        n2 = sum(1 for x in times2 if x >= t)
        d1 = sum(1 for x, e in zip(times1, ev1) if e == 1 and x == t)
        d2 = sum(1 for x, e in zip(times2, ev2) if e == 1 and x == t)
        n, d = n1 + n2, d1 + d2
        if n == 0:
            continue
        O1 += d1
        E1 += d * n1 / n
        if n > 1:
            V += d * (n - d) / (n - 1) * (n1 / n) * (1 - n1 / n)
    chi2 = ((O1 - E1) ** 2 / V) if V > 0 else 0.0
    p = math.erfc(math.sqrt(chi2 / 2.0)) if chi2 > 0 else 1.0
    return {"O1": O1, "E1": E1, "V": V, "chi2": chi2, "p": p}


# --------------------------------------------------------------------------- #
# run loading (mirrors aggregate_official.py accounting)                      #
# --------------------------------------------------------------------------- #

def _exit_status(json_path: str, rc_path: str) -> int:
    if os.path.exists(rc_path):
        try:
            return int(open(rc_path).read().strip())
        except ValueError:
            return -1
    return 0 if os.path.exists(json_path) else -1


def load_runs(run_dir: str):
    completed, failed = [], 0
    for log in sorted(glob.glob(os.path.join(run_dir, "seed_*.log"))):
        stem = log[: -len(".log")]
        js, rc = stem + ".json", stem + ".rc"
        if _exit_status(js, rc) == 0 and os.path.exists(js):
            try:
                completed.append(json.load(open(js)))
                continue
            except (OSError, ValueError):
                pass
        failed += 1
    return completed, failed


def _group_tte(runs: list[dict]):
    """(times, events) for TTVE: event=1 at first_valid_exploit_s, else censored at budget."""
    times, events = [], []
    for d in runs:
        fv = d.get("first_valid_exploit_s")
        if fv is not None:
            times.append(float(fv)); events.append(1)
        else:
            times.append(float(d.get("time_budget_s", 0.0))); events.append(0)
    return times, events


def analyze(root: str, out_dir: str, alpha: float, want_plot: bool):
    os.makedirs(out_dir, exist_ok=True)
    ver_rows, surv_rows, logrank_rows = [], [], []

    for bench in sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))):
        group_runs = {}
        for variant in ("vulnerable", "patched"):
            for seeds in ("llm", "random"):
                run_dir = os.path.join(root, bench, variant, seeds)
                if not glob.glob(os.path.join(run_dir, "seed_*.log")):
                    continue
                runs, failed = load_runs(run_dir)
                group_runs[(variant, seeds)] = runs
                comp = len(runs)
                valid = sum(1 for d in runs if d.get("valid_exploits", 0) > 0)
                alert = sum(1 for d in runs if d.get("candidates_total", 0) > 0)
                ver_lo, ver_hi = clopper_pearson(valid, comp, alpha)
                fpr_lo, fpr_hi = clopper_pearson(alert, comp, alpha)
                budget = runs[0].get("time_budget_s") if runs else None
                # median TTVE computed exactly as aggregate_official.py (censored -> inf)
                ttve_all = [d.get("first_valid_exploit_s") if d.get("first_valid_exploit_s") is not None
                            else float("inf") for d in runs]
                med = st.median(sorted(ttve_all)) if ttve_all else None
                median_ttve_s = (("> budget" if med == float("inf") else round(med, 4))
                                 if med is not None else None)
                ver_rows.append({
                    "bench": bench, "variant": variant, "seeds": seeds,
                    "completed": comp, "failed": failed,
                    "valid": valid, "VER": round(valid / comp, 4) if comp else None,
                    "VER_lo": round(ver_lo, 4), "VER_hi": round(ver_hi, 4),
                    "any_alert": alert, "FPR": round(alert / comp, 4) if comp else None,
                    "FPR_lo": round(fpr_lo, 4), "FPR_hi": round(fpr_hi, 4),
                    "median_ttve_s": median_ttve_s, "budget_s": budget,
                })
                times, events = _group_tte(runs)
                for s in km_steps(times, events):
                    surv_rows.append({"bench": bench, "variant": variant, "seeds": seeds, **s})

        # log-rank llm vs random on the vulnerable variant
        a = group_runs.get(("vulnerable", "llm"))
        b = group_runs.get(("vulnerable", "random"))
        if a and b:
            t1, e1 = _group_tte(a)
            t2, e2 = _group_tte(b)
            lr = logrank(t1, e1, t2, e2)
            logrank_rows.append({"bench": bench, "comparison": "vulnerable:llm_vs_random",
                                 "n_llm": len(a), "n_random": len(b),
                                 **{k: round(v, 6) for k, v in lr.items()}})

    _write_csv(os.path.join(out_dir, "analysis_ver_fpr.csv"), ver_rows)
    _write_csv(os.path.join(out_dir, "survival_steps.csv"), surv_rows)
    _write_csv(os.path.join(out_dir, "logrank.csv"), logrank_rows)
    if want_plot:
        _try_plot(surv_rows, out_dir)

    print("== VER / FPR (95% Clopper-Pearson) ==")
    for r in ver_rows:
        print(f"  {r['bench']:14s} {r['variant']:10s} {r['seeds']:6s} "
              f"VER={r['valid']}/{r['completed']}={r['VER']} "
              f"[{r['VER_lo']},{r['VER_hi']}]  FPR={r['any_alert']}/{r['completed']} "
              f"[{r['FPR_lo']},{r['FPR_hi']}]")
    if logrank_rows:
        print("== log-rank (vulnerable: llm vs random) ==")
        for r in logrank_rows:
            print(f"  {r['bench']:14s} chi2={r['chi2']} p={r['p']} (n={r['n_llm']}/{r['n_random']})")
    print(f"wrote analysis_ver_fpr.csv, survival_steps.csv, logrank.csv to {out_dir}")
    return ver_rows


def _write_csv(path, rows):
    if not rows:
        open(path, "w").close()
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _try_plot(surv_rows, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("[plot] matplotlib unavailable; survival_steps.csv is the artifact.")
        return
    benches = sorted({r["bench"] for r in surv_rows})
    for bench in benches:
        fig, ax = plt.subplots(figsize=(5, 3.2))
        for (variant, seeds) in sorted({(r["variant"], r["seeds"]) for r in surv_rows if r["bench"] == bench}):
            pts = [r for r in surv_rows if r["bench"] == bench and r["variant"] == variant and r["seeds"] == seeds]
            xs = [p["t"] for p in pts]
            ys = [p["survival"] for p in pts]
            ax.step(xs, ys, where="post", label=f"{variant}/{seeds}")
        ax.set_xlabel("time to valid exploit (s)")
        ax.set_ylabel("survival (no valid exploit yet)")
        ax.set_title(bench)
        ax.set_ylim(-0.02, 1.02)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, f"fig_survival_{bench}.pdf"))
        plt.close(fig)
    print(f"[plot] wrote fig_survival_*.pdf for {len(benches)} bench(es)")


# --------------------------------------------------------------------------- #
# self-test                                                                   #
# --------------------------------------------------------------------------- #

def selftest() -> int:
    ok = True

    def approx(a, b, tol=1e-3, what=""):
        nonlocal ok
        if abs(a - b) > tol:
            ok = False
            print(f"  FAIL {what}: {a} vs {b}")
        else:
            print(f"  PASS {what}: {a:.4f} ~ {b:.4f}")

    print("== Clopper-Pearson vs textbook ==")
    lo, hi = clopper_pearson(0, 10)
    approx(lo, 0.0, 1e-9, "CP(0/10) lo"); approx(hi, 0.3085, 1e-3, "CP(0/10) hi")
    lo, hi = clopper_pearson(10, 10)
    approx(lo, 0.6915, 1e-3, "CP(10/10) lo"); approx(hi, 1.0, 1e-9, "CP(10/10) hi")
    lo, hi = clopper_pearson(0, 20)
    approx(hi, 0.1684, 1e-3, "CP(0/20) hi")
    lo, hi = clopper_pearson(3, 10)
    approx(lo, 0.0667, 1e-3, "CP(3/10) lo"); approx(hi, 0.6525, 1e-3, "CP(3/10) hi")

    print("== betainc sanity ==")
    approx(betainc(2, 3, 0.5), 0.6875, 1e-4, "I_0.5(2,3)")

    print("== KM: all 5 events at distinct times, no censoring -> survival hits 0 ==")
    steps = km_steps([1, 2, 3, 4, 5], [1, 1, 1, 1, 1])
    approx(steps[-1]["survival"], 0.0, 1e-9, "KM final survival")
    approx(steps[1]["survival"], 0.8, 1e-9, "KM after first event")

    print("== KM with censoring: 1 event at t=1 of 4 at risk, rest censored ==")
    steps = km_steps([1, 2, 3, 4], [1, 0, 0, 0])
    approx(steps[1]["survival"], 0.75, 1e-9, "KM 1/4 event")

    print("== log-rank: identical groups -> chi2 ~ 0, p ~ 1 ==")
    lr = logrank([1, 2, 3], [1, 1, 1], [1, 2, 3], [1, 1, 1])
    approx(lr["chi2"], 0.0, 1e-6, "identical chi2"); approx(lr["p"], 1.0, 1e-6, "identical p")

    print("== log-rank: fast vs slow separable groups -> chi2 > 0 ==")
    lr = logrank([0.1, 0.2, 0.3, 0.4, 0.5], [1, 1, 1, 1, 1],
                 [10, 11, 12, 13, 14], [1, 1, 1, 1, 1])
    print(f"  chi2={lr['chi2']:.3f} p={lr['p']:.4g} (expect chi2>0, p<0.05)")
    if not (lr["chi2"] > 0 and lr["p"] < 0.05):
        ok = False; print("  FAIL separable groups")
    else:
        print("  PASS separable groups")

    print("\n" + ("ALL SELFTESTS PASSED" if ok else "SELFTEST FAILURES"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runs_root", nargs="?")
    ap.add_argument("--out", default=None)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.runs_root:
        ap.error("runs_root is required (or use --selftest)")
    root = os.path.abspath(args.runs_root)
    out = os.path.abspath(args.out) if args.out else root
    analyze(root, out, args.alpha, args.plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
