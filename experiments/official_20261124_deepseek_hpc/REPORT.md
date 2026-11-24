# DeepSeek-V3 grounded seeds on HPC-UIT (2026-11-24): second model for RQ3

Fuzzing campaign for the second model (DeepSeek-V3, `deepseek/deepseek-chat` via
OpenRouter), to close the paper's self-stated "single model" limitation. It
mirrors the gpt-oss-120b C3b campaign (`experiments/official_20261118_c3b_hpc`)
exactly; **only the seed-generating model differs**. Seeds: commit `0b9fd17`,
`experiments/official_20261124_deepseek_seedgen` (20 grounded sets, $0.375).

## Environment

- Jobs **136610** (vulnerable) + **136611** (patched), Slurm `account=uit,
  partition=normal, qos=mig2-35, 8 CPUs, 16 GB, CPU-only`, node h200node02,
  both `COMPLETED` (elapsed 4:50:20), 400/400 runs each, 0 failed, 0 seed
  fallback.
- HPC repo `repo_deepseek_0b9fd17` = a copy of the C3b repo `repo_c3b_093e5ae`
  (identical fixtures, specs, `run_official.sh`, `empty_rpc.py`,
  `aggregate_official.py`, `job_c3_llm.sh`) with the DeepSeek seed sets added, so
  the only difference from C3b is the seeds.
- Fuzzer: **the same binary as A-1, C3 and C3b** (musl static, sha256
  `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848`). Empty RPC
  (local fixtures, not a mainnet fork). Seeds 1042..20042 (20) x 300 s x
  {vulnerable, patched}, strict LLM seeds, `SEED_ALIAS=deepseek-grounded`.

## Results

### Patched variants — the negative control holds

**0 / 400** valid-exploit runs and **0 / 400** alert runs (5 fixtures x 4
regimes x 20 seeds). The execution-only oracle + patched control is as clean for
DeepSeek-written seeds as for gpt-oss (C3b was 0/400, A-1+C3 were 0/940).

### Vulnerable variants — valid-exploit runs / 20 (median TTVE, s)

| Fixture | Random (A-1) | DeepSeek known | exact | temporal | no_rag | gpt-oss C3b (all regimes) |
|---|---|---|---|---|---|---|
| CrossCurve (2026) | 20 · 0.19 | 20 · 0.003 | 20 · 0.004 | 20 · 0.005 | 20 · 0.008 | 20 |
| Verus (2026) | 20 · 1.06 | 20 · 0.0005 | 20 · 0.006 | 20 · 0.008 | 20 · 0.010 | 20 |
| Ronin bridge (2024) | 20 · 0.011 | 20 · 0.0007 | 20 · 0.002 | 20 · 0.003 | 20 · 0.0007 | 20 |
| **FEG SmartBridge (2024)** | **16 · 72.3** | **20 · 4.41** | **20 · 14.3** | **20 · 20.1** | **20 · 24.2** | 20 |
| **PolyNetwork (2021)** | **1 · >300** | **20 · 72.8** | **16 · 150.2** | **14 · 135.7** | **13 · 161.4** | 20 |

All actions resolved (`actions_resolved` = total in every configuration); 0 seed
fallback.

## Reading (honest)

1. **The grounded-seeding result replicates on an independent frontier model.**
   DeepSeek-V3 (a different lab and architecture from gpt-oss-120b, ~July-2024
   cutoff) solves all five incidents and, on the two incidents random seeds do
   not solve quickly (FEG, PolyNetwork), beats random: FEG 20/20 vs 16/20 and
   much faster than random's 72 s; PolyNetwork 13-20/20 vs 1/20. This closes the
   paper's self-stated single-model limitation.
2. **One honest difference from gpt-oss.** On PolyNetwork, DeepSeek leans on the
   target's own record: 20/20 with `known` but 13-16/20 once that record is
   removed (`exact`/`temporal`/`no_rag`), whereas gpt-oss was 20/20 in every
   regime. Even without the record DeepSeek far exceeds random (1/20), but for
   this model, on this hardest fixture, retrieving the target incident does help.
   The four easy fixtures and FEG are regime-insensitive (20/20 throughout).
3. **Same cutoff, so this is replication, not a new temporal point.** DeepSeek's
   ~July-2024 cutoff is essentially gpt-oss's 06/2024; the post-cutoff holdout
   set is the same four incidents. DeepSeek is a second, independent model at the
   same cutoff, not a different-cutoff probe.

## Files

`c3_deepseek-grounded_{vulnerable,patched}_20261124_163109/<regime>/official_runs/<bench>/<variant>/llm/seed_<n>.{json,log,rc}`,
HPC-written `summary_official.csv` per regime, `seed_provenance/`. Not
re-aggregated locally; the summaries are the HPC-written ones.
