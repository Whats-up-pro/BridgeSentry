# Aggregate the on-chain fork robustness campaign into a paper-ready summary.
# Usage: python3 aggregate_fork_robustness.py <runs_dir>
import json, glob, os, sys, statistics

runs = sys.argv[1] if len(sys.argv) > 1 else "."
ARMS = ["vulnerable_llm", "patched_llm", "vulnerable_random"]

def load(f):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}

print(f"# Fork robustness aggregation\nruns_dir: {runs}\n")
summary = {}
for arm in ARMS:
    fs = sorted(glob.glob(os.path.join(runs, arm, "seed_*.json")),
                key=lambda p: int(os.path.basename(p).split("_")[1].split(".")[0]))
    rows = []
    nvalid = 0; tts = []
    for f in fs:
        d = load(f)
        seed = os.path.basename(f).split("_")[1].split(".")[0]
        ve = d.get("valid_exploits")
        ct = d.get("candidates_total")
        tt = d.get("first_valid_exploit_s")
        gates = None
        cands = d.get("candidates") or []
        if cands:
            gates = cands[0].get("gates")
        if (ve or 0) > 0:
            nvalid += 1
            if tt is not None:
                tts.append(tt)
        rows.append((seed, ve, ct, tt, gates, d.get("_error")))
    med = round(statistics.median(tts), 4) if tts else None
    summary[arm] = (nvalid, len(fs), med)
    print(f"## {arm}: valid {nvalid}/{len(fs)}  median_ttve_s={med}")
    print("| seed | valid_exploits | candidates_total | first_valid_exploit_s | gates_first | err |")
    print("|---|---|---|---|---|---|")
    for seed, ve, ct, tt, gates, err in rows:
        g = "" if gates is None else (",".join(k for k, v in gates.items() if v) if isinstance(gates, dict) else str(gates))
        print(f"| {seed} | {ve} | {ct} | {tt} | {g} | {err or ''} |")
    print()

print("## HEADLINE")
for arm in ARMS:
    nv, n, med = summary[arm]
    print(f"- {arm}: {nv}/{n} valid" + (f", median TTVE {med}s" if med is not None else ""))
pv = summary.get("patched_llm", (None, None, None))
print(f"\nPATCHED CONTROL OK (expect 0/N): {'YES' if pv[0]==0 else 'NO -- INVESTIGATE'} ({pv[0]}/{pv[1]})")
