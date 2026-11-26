# -*- coding: utf-8 -*-
# A5 statistics: parser-only vs grounded (C3b no_rag) vs random (A1).
# Fisher exact on valid-exploit rate; log-rank on TTVE (censored at 300s); Holm per family.
import json, glob, os, sys, math
from scipy.stats import fisher_exact, binomtest, chi2

REPO = "/mnt/d/HK1_2026-2027/NT505/BridgeSentry"
EXP = REPO + "/experiments"
A5_VULN = glob.glob(EXP + "/official_20261126_a5_parser_only_hpc/c3_gpt-oss-or-parser-only_vulnerable_*")[0]
INCIDENTS = ["crosscurve", "ronin_2024", "verus", "feg_bridge_2024", "polynetwork"]
BUD = 300.0

def load(pattern):
    """return list of (time, event) with censoring at BUD."""
    out = []
    for f in glob.glob(pattern):
        fv = json.load(open(f, encoding="utf-8")).get("first_valid_exploit_s")
        if fv is not None:
            out.append((float(fv), 1))
        else:
            out.append((BUD, 0))
    return out

def arm_paths(b):
    return {
        "parser": f"{A5_VULN}/no_rag/official_runs/{b}/vulnerable/llm/seed_*.json",
        "grounded": f"{EXP}/official_20261118_c3b_hpc/vulnerable/no_rag/official_runs/{b}/vulnerable/llm/seed_*.json",
        "random": f"{EXP}/official_20261114_a1_hpc/official_runs/{b}/vulnerable/random/seed_*.json",
    }

def ver(data):  # (valid, n)
    return sum(e for _, e in data), len(data)

def cp_ci(k, n):  # Clopper-Pearson 95%
    if n == 0: return (0.0, 0.0)
    lo = 0.0 if k == 0 else binomtest(k, n).proportion_ci(0.95, method="exact").low
    hi = 1.0 if k == n else binomtest(k, n).proportion_ci(0.95, method="exact").high
    return (lo, hi)

def logrank(a, b):
    """two-group log-rank, right-censored. a,b = list of (time,event). returns (chi2, p)."""
    times = sorted(set(t for t, e in a + b if e == 1))
    if not times: return (0.0, 1.0)
    O_E = 0.0; V = 0.0
    for t in times:
        n1 = sum(1 for tt, _ in a if tt >= t); n2 = sum(1 for tt, _ in b if tt >= t)
        d1 = sum(1 for tt, e in a if tt == t and e == 1); d2 = sum(1 for tt, e in b if tt == t and e == 1)
        n = n1 + n2; d = d1 + d2
        if n == 0: continue
        e1 = d * n1 / n
        O_E += (d1 - e1)
        if n > 1:
            V += d * (n1 / n) * (n2 / n) * (n - d) / (n - 1)
    if V == 0: return (0.0, 1.0)
    cs = (O_E ** 2) / V
    return (cs, 1 - chi2.cdf(cs, 1))

def holm(pvals):
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals); adj = [0.0] * m; run = 0.0
    for rank, i in enumerate(idx):
        a = min(1.0, (m - rank) * pvals[i]); run = max(run, a); adj[i] = run
    return adj

print("=== VALID-EXPLOIT RATE + median TTVE (vulnerable, no_rag) ===")
data = {}
for b in INCIDENTS:
    p = arm_paths(b); data[b] = {k: load(v) for k, v in p.items()}
    row = []
    for arm in ("random", "parser", "grounded"):
        k, n = ver(data[b][arm]); tts = sorted(t for t, e in data[b][arm] if e == 1)
        med = round(tts[len(tts)//2], 4) if tts else None
        lo, hi = cp_ci(k, n)
        row.append(f"{arm} {k}/{n} [{lo:.2f},{hi:.2f}] med={med}")
    print(f"{b:16s} | " + " | ".join(row))

def family(name, arm_a, arm_b):
    print(f"\n=== {name}: {arm_a} vs {arm_b} ===")
    fish_p = []; lr_p = []; labels = []
    for b in INCIDENTS:
        ka, na = ver(data[b][arm_a]); kb, nb = ver(data[b][arm_b])
        _, fp = fisher_exact([[ka, na - ka], [kb, nb - kb]])
        _, lp = logrank(data[b][arm_a], data[b][arm_b])
        fish_p.append(fp); lr_p.append(lp); labels.append(b)
    fadj = holm(fish_p); ladj = holm(lr_p)
    for i, b in enumerate(labels):
        print(f"  {b:16s} Fisher p={fish_p[i]:.4g} (Holm {fadj[i]:.4g}) | log-rank p={lr_p[i]:.4g} (Holm {ladj[i]:.4g})")

family("F1", "parser", "random")
family("F2", "parser", "grounded")
