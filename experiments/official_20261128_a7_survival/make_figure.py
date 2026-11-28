import json, glob, os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = "/mnt/d/HK1_2026-2027/NT505/BridgeSentry"
BUDGET = 300.0
RANDOM = REPO + "/experiments/official_20261114_a1_hpc/official_runs/{b}/vulnerable/random/seed_*.json"
GROUND = REPO + "/experiments/official_20261118_c3b_hpc/vulnerable/no_rag/official_runs/{b}/vulnerable/llm/seed_*.json"
INCIDENTS = [("feg_bridge_2024", "FEG SmartBridge"), ("polynetwork", "PolyNetwork")]

def ttves(pattern, b):
    out = []
    for f in sorted(glob.glob(pattern.format(b=b))):
        d = json.load(open(f))
        t = d.get("first_valid_exploit_s")
        out.append(float(t) if (t is not None and d.get("valid_exploits", 0) and float(t) <= BUDGET) else None)
    return out

def km(times):
    """Right-censored survival: all censoring is at the budget (end of study),
    so S(t) = (# runs with no valid exploit found by time t) / n, a right-continuous
    step function that floors at the censored fraction."""
    n = len(times)
    ev = sorted(t for t in times if t is not None)
    xs, ys = [1e-4], [1.0]            # start just left of the first possible event (log x)
    solved = 0
    for t in ev:
        xs += [t, t]; ys += [ (n - solved) / n ]
        solved += 1
        ys += [ (n - solved) / n ]
    xs += [BUDGET]; ys += [ (n - solved) / n ]
    return np.array(xs), np.array(ys), n, solved

rows = []
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
C_R, C_G = "#C44E52", "#4C72B0"       # random (red), grounded (blue): colourblind-safe
for ax, (b, title) in zip(axes, INCIDENTS):
    for pat, label, color, ls in [(RANDOM, "Random seeds", C_R, "-"),
                                   (GROUND, "Grounded seeds (no retrieval)", C_G, "--")]:
        t = ttves(pat, b)
        xs, ys, n, solved = km(t)
        ax.step(xs, ys, where="post", color=color, ls=ls, lw=2.0, label="%s (%d/%d)" % (label, solved, n))
        allt = [x if x is not None else BUDGET for x in t]
        cens = n - solved
        med = float(np.median(allt))
        rows.append(dict(incident=title, seeds=label, n=n, solved=solved, censored=cens,
                         median_ttve_s=(">300" if cens > n/2 else round(med, 4))))
    ax.set_xscale("log")
    ax.set_xlim(1e-3, BUDGET)
    ax.set_ylim(-0.03, 1.03)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Time to first valid exploit (s, log scale)", fontsize=8)
    ax.grid(True, which="both", ls=":", lw=0.5, alpha=0.6)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="upper right", framealpha=0.9)
axes[0].set_ylabel("Runs without a valid exploit", fontsize=8)
fig.tight_layout()
out_png = REPO + "/latex/fig_survival_ttve.png"
fig.savefig(out_png, dpi=300)
fig.savefig("/mnt/d/HK1_2026-2027/NT505/Paper/fig_survival_ttve.png", dpi=300)
print("saved", out_png)

E = REPO + "/experiments/official_20261128_a7_survival"
os.makedirs(E, exist_ok=True)
with open(E + "/survival_ttve.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r)
