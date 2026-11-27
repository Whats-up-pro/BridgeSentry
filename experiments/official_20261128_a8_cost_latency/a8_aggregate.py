"""A8: seed-generation cost, latency, and seed-compiler failure rates, computed only
from committed artifacts (ledgers + provenance.json). No LLM call is made."""
import csv, glob, json, os, statistics as st, sys

REPO = sys.argv[1]
OUT = sys.argv[2]
# OpenRouter public list prices (USD per token), fetched 2026-11-28 from
# https://openrouter.ai/api/v1/models ; the DeepSeek price equals the one in
# experiments/official_20261124_deepseek_seedgen/REPORT.md ($0.26/M in, $1.03/M out).
PRICE = {'openai/gpt-oss-120b': (0.00000005, 0.00000025),
         'deepseek/deepseek-chat': (0.0000002574, 0.0000010287)}

CONFIGS = [
    ('ungrounded gpt-oss-120b (C3)', None, 'gpt-oss-or'),
    ('grounded gpt-oss-120b (C3b)', 'experiments/official_20261118_c3b_seedgen/c3b_ledger_*.csv', 'gpt-oss-or-grounded'),
    ('grounded DeepSeek-V3', 'experiments/official_20261124_deepseek_seedgen/ledger_*.csv', 'deepseek-grounded'),
    ('grounded gpt-oss-120b, parser-only Module 1 (A5)', 'experiments/official_20261126_a5_parser_only_seedgen/ledger_*.csv', 'gpt-oss-or-parser-only'),
]
BENCHES = ['ronin_2024', 'feg_bridge_2024', 'crosscurve', 'verus', 'polynetwork']

def med(xs):
    return st.median(xs) if xs else None

rows_out = []
for name, ledger_glob, alias in CONFIGS:
    prov = []
    for b in BENCHES:
        for p in sorted(glob.glob(os.path.join(REPO, 'benchmarks', b, 'official', 'llm_outputs', alias, '*', 'provenance.json'))):
            prov.append((b, p.split(os.sep)[-2], json.load(open(p))))
    model = sorted({d.get('model') for _, _, d in prov})
    led = []
    if ledger_glob:
        for f in sorted(glob.glob(os.path.join(REPO, ledger_glob))):
            led += list(csv.DictReader(open(f)))
    # tokens: ledger if present, else provenance usage
    if led:
        pt = sum(int(r['prompt_tokens']) for r in led); ct = sum(int(r['completion_tokens']) for r in led)
        calls = sum(int(r['api_calls']) for r in led)
        m1 = [float(r['m1_latency_s']) for r in led]; m2 = [float(r['m2_latency_s']) for r in led]
        e2e = [a + b for a, b in zip(m1, m2)]
        at = sum(int(r['actions_total']) for r in led); am = sum(int(r['actions_mapped']) for r in led)
        fb = sum(int(r['n_fallback']) for r in led); nsc = sum(int(r['n_scenarios']) for r in led)
        nsets = len(led)
    else:
        u = [d.get('usage', {}) for _, _, d in prov]
        pt = sum(x.get('prompt_tokens', 0) for x in u); ct = sum(x.get('completion_tokens', 0) for x in u)
        calls = sum(x.get('api_calls', 0) for x in u)
        m1 = m2 = e2e = []
        at = am = fb = nsc = None
        nsets = len(prov)
    # seed-compiler repair statistics (grounded only)
    inv = rep = dropped = r0a = r0c = 0
    for _, _, d in prov:
        g = d.get('grounded') or {}
        for pi in g.get('per_invariant', []):
            inv += 1
            rounds = pi.get('rounds', [])
            if len(rounds) > 1:
                rep += 1
            if pi.get('outcome') != 'compiled':
                dropped += 1
            if rounds:
                r0a += rounds[0].get('n_actions', 0); r0c += rounds[0].get('n_compiled', 0)
    pin, pout = PRICE.get(model[0], (None, None)) if len(model) == 1 else (None, None)
    cost = (pt * pin + ct * pout) if pin is not None else None
    rows_out.append(dict(
        config=name, model=';'.join(model), seed_sets=nsets, api_calls=calls,
        prompt_tokens=pt, completion_tokens=ct, tokens_per_set=round((pt + ct) / nsets) if nsets else None,
        cost_usd=round(cost, 4) if cost is not None else None,
        m1_median_s=round(med(m1), 1) if m1 else None, m2_median_s=round(med(m2), 1) if m2 else None,
        e2e_median_s=round(med(e2e), 1) if e2e else None, e2e_max_s=round(max(e2e), 1) if e2e else None,
        scenarios=nsc, fallback_scenarios=fb, actions_total=at, actions_mapped=am,
        invariants=inv or None, inv_needing_repair=rep if inv else None, inv_not_compiled=dropped if inv else None,
        first_round_compile_rate=round(r0c / r0a, 3) if r0a else None))

os.makedirs(OUT, exist_ok=True)
keys = list(rows_out[0].keys())
with open(os.path.join(OUT, 'a8_cost_latency.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows_out)
for r in rows_out:
    print(json.dumps(r))
