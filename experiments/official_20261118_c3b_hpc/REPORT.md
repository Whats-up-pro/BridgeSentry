# C3b on HPC-UIT (2026-11-18/19): grounded gpt-oss-120b seeds under four retrieval regimes

Registered campaign of `docs/C3b_protocol.md` (commit c952e1f, before any seed
set was generated). Seeds: commit 093e5ae, generation record
`experiments/official_20261118_c3b_seedgen/`. This is an **HPC run** (not a
local laptop run).

## Environment

| | Job 52245 (vulnerable) | Job 52246 (patched) |
|---|---|---|
| Slurm | `account=uit`, `partition=normal`, `qos=mig2-35`, 8 CPUs, 16 GB, `time=07:00:00`, CPU-only (no `--gres`) | same |
| Node | `h200node02` | `h200node02` |
| Time (VN) | 2026-11-18 21:57:14 -> 2026-11-19 02:47:34 (4:50:20) | 21:57:14 -> 02:47:31 (4:50:17) |
| End | `COMPLETED`, exit `0:0`, MaxRSS 75 MB | `COMPLETED`, exit `0:0`, MaxRSS 75 MB |
| Runs | 400/400 rc=0, 0 failed, 0 seed fallback | 400/400 rc=0, 0 failed, 0 seed fallback |
| `.err` | empty | empty |

- Code: `/datastore/dungtrt/bridgesentry/repo_c3b_093e5ae`, `git archive` of
  **093e5ae**. No change to `src/module3_fuzzing`, fixture specs or contracts,
  `run_official.sh`, `empty_rpc.py` or `aggregate_official.py` since 5a6536d
  (A-1); `job_c3_llm.sh` gained only `SEED_ALIAS` and cleanup of staged seeds.
- Fuzzer: musl static, sha256
  `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848` -- the
  binary of A-1 and C3. Empty RPC (local fixtures, **not** a mainnet fork).
- Seeds 1042..20042 (20), 300 s per run, strict LLM seeds
  (`BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1`), `SEED_ALIAS=gpt-oss-or-grounded`.
  Staged seed copies were cmp-checked (`<variant>/seed_staging.sha256`);
  provenance of the 20 sets is in `<variant>/seed_provenance/`.
- Transfer: each run directory was tarred on HPC, copied, and the archive
  sha256 matched (`a7ae4426...` vulnerable, `f535bfe9...` patched); 1227 files
  each. The eight `summary_official.csv` files are the HPC-written ones (sha256
  checked 8/8, not re-aggregated).

## Results

### Patched variants

**0/400** alert runs (5 fixtures x 4 regimes x 20 seeds). With A-1 and C3:
0/940 patched-variant runs raised an alert.

### Vulnerable variants: valid-exploit runs / 20 and median TTVE (s)

| Fixture | Random (A-1) | C3 known / exact / temporal / no_rag | **C3b known** | **C3b exact** | **C3b temporal** | **C3b no_rag** |
|---|---|---|---|---|---|---|
| Ronin bridge (2024) | 20 · 0.0109 | 20 / 20 / 20 / 20 | 20 · 0.0004 | 20 · 0.0008 | 20 · 0.0005 | 20 · 0.0005 |
| CrossCurve (2026) | 20 · 0.192 | 20 / 20 / 20 / 20 | 20 · 0.0010 | 20 · 0.0029 | 20 · 0.0011 | 20 · 0.0012 |
| Verus (2026) | 20 · 1.06 | 20 / 20 / 20 / 20 | 20 · 0.0005 | 20 · 0.0005 | 20 · 0.0011 | 20 · 0.0012 |
| **FEG SmartBridge (2024)** | **16 · 72.3** | 10 / 17 / 14 / 13 | **20 · 0.0011** | **20 · 0.0033** | **20 · 0.0028** | **20 · 0.0011** |
| **PolyNetwork (2021)** | **1 · >300** | 1 / 0 / 0 / 0 | **20 · 2.25** | **20 · 2.05** | **20 · 1.14** | **20 · 0.034** |

All C3b actions were resolved by the harness (`actions_resolved` = total in
every configuration).

### Registered tests (`analysis/F*/comparisons.csv`; Holm within each family)

- **F1 grounded vs random (20 comparisons).** Grounded seeds reach the first
  valid exploit sooner on every fixture in every regime (log-rank, Holm-adjusted
  p < 0.0001 in all 20). Valid-exploit rate: PolyNetwork 20/20 vs 1/20 (Fisher,
  Holm p < 0.0001, all regimes); FEG 20/20 vs 16/20 (Fisher p = 0.106, Holm 1.0:
  the rate difference is not significant, the time difference is).
- **F2 grounded vs ungrounded C3 (20 comparisons).** Grounded is faster in all
  20 (log-rank Holm p < 0.0001). Rate: PolyNetwork 20/20 vs 0-1/20 (Holm
  p < 0.0001 in all regimes); FEG known 20/20 vs 10/20 (Holm p = 0.007); FEG
  exact, temporal, no_rag not significant after Holm (0.23-1.0).
- **F3 regimes within grounded (15 comparisons; other regime vs known).**
  `known` is faster than exact on Ronin, CrossCurve and FEG, than temporal on
  Verus and FEG, and than no_rag on Ronin, CrossCurve and Verus (Holm p <= 0.004),
  but every one of these differences is at most 2.2 ms and every run succeeds.
  On PolyNetwork, no_rag is faster than known (0.034 s vs 2.25 s, Holm
  p < 0.0001); exact and temporal do not differ from known.

### Hypotheses

- **H1 (grounded faster than random on FEG SmartBridge and PolyNetwork):
  supported**, in every regime.
- **H2 (known not better than exact, temporal, no_rag): not supported as
  stated.** Allowing retrieval of the target's own record gives
  statistically significant speed-ups of at most 2.2 ms on four fixtures and no
  difference in success (20/20 everywhere). The one large regime effect goes
  the other way: PolyNetwork is solved fastest without retrieval.

## Cost (`../official_20261118_c3b_seedgen/`)

- Tokens: 2.70 M over 20 sets (1.14 M prompt, 1.55 M completion), 481 API
  calls; USD not recorded here (OpenRouter dashboard; the account balance could
  not be queried from behind the VPN).
- Generation wall-clock per set (Module 1 + Module 2 incl. repairs, five sets
  generated in parallel): median 240 s, range 146-1423 s. End-to-end time
  (generation + TTVE) is therefore minutes, dominated by generation: on FEG
  SmartBridge it is longer than the random-seed median TTVE (72 s), while on
  PolyNetwork random seeds found an exploit in only 1 of 20 runs of 300 s.

## Reading (honest)

1. **Where the gain comes from.** In C3 the model saw no code and the harness
   dropped most of what it wrote. With the comment-free source, ABI and
   deployment, the model writes the exploit itself: FEG SmartBridge and the
   three easy fixtures are solved at the first execution of a seed (about
   1 ms); PolyNetwork needs about 1-2 s of mutation from a near-complete seed.
   The fuzzer acts mainly as an execution-based validator of LLM-written
   exploits.
2. **Not memorisation or retrieval leakage, as far as these data show.** The
   three fixtures dated after the model's stated cutoff (FEG SmartBridge 12/2024,
   CrossCurve 01/2026, Verus 05/2026) are solved in every regime, including
   no_rag; the target's own record (known) buys at most milliseconds.
3. **Limits.** One model; five fixtures; minimal re-implementations with
   little distracting code and comment-free but small sources, which favours a
   model that reads the whole contract; the method was designed after observing
   C3 on these fixtures (registered before generation, but not a held-out test);
   end-to-end time is dominated by generation.
4. The patched-variant control holds with exploit-writing seeds: 0/400.

## Files

- `vulnerable/`, `patched/`: HPC run directories (`<regime>/official_runs/<bench>/<variant>/llm/seed_<n>.{json,log,rc}`,
  HPC-written `summary_official.csv`, `jobs.txt`, `run_info.txt`,
  `seed_staging.sha256`, `seed_provenance/`, `slurm_logs/c3_<job>.{out,err}`).
- `job_c3_llm.sh`: the job script as run (093e5ae).
- `analysis/<variant>_<regime>/`: `analyze_official.py` output (Clopper-Pearson,
  Kaplan-Meier, log-rank).
- `analysis/F1_vs_random/`, `analysis/F2_vs_c3/`, `analysis/F3_regimes/`:
  `scripts/official/compare_campaigns.py` output (`comparisons.csv` with Holm),
  plus the per-comparison `analyze_*` directories.
