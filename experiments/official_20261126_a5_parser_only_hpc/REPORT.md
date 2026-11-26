# A5 ablation — parser-only Module 1 (HPC fuzzing campaign)

Frozen record; do not edit after commit. The fuzzing half of A5: run the parser-only Module 1
seeds (`experiments/official_20261126_a5_parser_only_seedgen`, commit `36a7b47`) under the
execution-only official oracle and compare the valid-exploit rate and time-to-valid-exploit
against the grounded LLM Module 1 (C3b, `official_20261118_c3b_hpc`, no_rag) and the random
seeds (A1, `official_20261114_a1_hpc`). Isolates the LLM's contribution to the EXTRACTION step
(Module 1 = ATG + invariants), with Module 2 (grounded gpt-oss-120b) held identical to C3b.

## Setup
- HPC-UIT, partition normal, qos mig2-35, 8 CPUs, CPU-only; empty RPC (local fixtures).
- Jobs 167022 (vulnerable) + 167023 (patched), COMPLETED (~1h15 each), repo copy
  `repo_c3b_093e5ae`, SEED_ALIAS `gpt-oss-or-parser-only`, regime `no_rag`.
- Fuzzer binary sha256 `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848`
  (identical to C3b), 20 seeds (1042..20042) × 300 s × {vulnerable, patched} × 5 incidents.
- Parser-only Module 1 ran via the regex extractor (Slither cannot compile the multi-file
  fixtures under solc default allow-paths; see the seedgen REPORT) — the no-LLM extraction the
  deployed `--parser-only` mode delivers here.

## Valid-exploit rate (vulnerable / 20) + median TTVE
| incident | random A1 | parser-only A5 | grounded C3b |
|---|---|---|---|
| crosscurve | 20/20 (0.21 s) | 20/20 (0.6 ms) | 20/20 (1.2 ms) |
| ronin_2024 | 20/20 (14 ms) | 20/20 (0.5 ms) | 20/20 (0.5 ms) |
| verus | 20/20 (1.24 s) | 20/20 (0.5 ms) | 20/20 (1.2 ms) |
| feg_bridge_2024 | 16/20 (59 s) | 20/20 (3.2 ms) | 20/20 (1.1 ms) |
| polynetwork | 1/20 | **1/20** | **20/20** |
Patched (parser-only): **0 of 100** (0/20 each incident) — no false alerts, oracle stays specific.

## Statistics (Fisher exact on VER, log-rank on TTVE censored at 300 s, Holm per family)
F2 — parser-only vs grounded:
- crosscurve, ronin_2024, verus, feg_bridge_2024: Fisher p=1.0 (identical VER, all 20/20).
- **polynetwork: Fisher p=3.0e-10 (Holm 1.5e-9)** — the sole incident where removing the LLM from
  Module 1 significantly lowers the valid-exploit rate (1/20 vs 20/20).

F1 — parser-only vs random:
- VER identical everywhere except feg_bridge_2024 (20 vs 16), not significant after Holm (p=0.53).
- polynetwork: Fisher p=1.0 (1/20 both), log-rank p=0.99 (no difference).

Log-rank is extreme (p≈9e-12) on the easy incidents only because the TTVE distributions are very
tight (parser ~0.5 ms vs random 0.01-1.2 s); the absolute differences are milliseconds and have no
practical meaning, consistent with the paper's "medians differ by at most 2.2 ms".

## Reading
Removing the LLM from the extraction step (Module 1) does not change the valid-exploit rate on 4 of
5 incidents (Fisher p=1.0); a regex-only extractor suffices. The **only** incident where the LLM
Module 1 is decisive is **PolyNetwork** (grounded 20/20 vs parser-only 1/20, Holm 1.5e-9) — and
PolyNetwork is the one incident that predates the model's 06/2024 cutoff, so this advantage cannot
be separated from memorization of the well-known exploit. The LLM's contribution to extraction is
therefore narrow and concentrated on a memorization-suspect case. (Module 2, the grounded scenario
writer, is held fixed here and is what lifts FEG over random; it is not ablated in A5.)

## Files
- `c3_gpt-oss-or-parser-only_{vulnerable,patched}_<stamp>/no_rag/official_runs/<b>/<variant>/llm/seed_*.json`
- `.../summary_official.csv`, `.../run_info.txt`, `.../seed_staging.sha256`
- `a5_stats.py` (the statistics above)
