# experiments/

Each `official_<YYYYMMDD>[_rN]/` directory is a frozen record of one campaign:
the raw JSON/logs, `summary_official.csv`, `REPORT.md`, and the exact scripts
that produced them. Do not edit a record after it is committed; if a script
needed a fix, the fix belongs in `scripts/official/` and the next campaign gets
a new directory.

| Directory | Campaign |
| --- | --- |
| `official_20261103/` | Round 1: Nomad, Qubit; 5 seeds × 20 s; empty RPC; fixed block 15259100. |
| `official_20261103_r2/` | Round 2 (regression): same matrix; blocks read from metadata. |
| `legacy_oracle_diagnosis_20261103/` | Diagnosis of the legacy (pre-official) oracle at `db20af7` + `diag_exec_only.patch`: 12 fixtures × {scenario-only, real bytecode, execution-only state} + patched Nomad; 3 seeds × 20 s; empty RPC. Shows the legacy oracle derives violations from scenario text. |
| `official_20261114_a1_hpc/` | A-1 on HPC (Slurm job 30578): 7 on-chain fixtures × {vulnerable, patched} × random seeds, 20 seeds × 300 s; empty RPC; repo 5a6536d, binary d9cf542e. |
| `official_20261115_c3_hpc/` | C3 on HPC (Slurm jobs 42012 vulnerable, 42013 patched): gpt-oss-120b seeds under 4 retrieval regimes (known, exact, temporal, no_rag) on ronin_2024, crosscurve, verus, feg_bridge_2024, polynetwork; 20 seeds × 300 s; empty RPC; repo 89c0dbe, binary d9cf542e; compared with official_20261114_a1_hpc. |
| `official_20261118_c3b_seedgen/` | C3b seed generation: 20 grounded gpt-oss-120b seed sets (docs/C3b_protocol.md), ledgers, logs incl. the discarded 402 attempt, local smoke. |
| `official_20261118_seed_channel_control/` | Positive control of the grounded seed channel (local WSL run): documented exploits compiled by seed_compiler give a valid exploit at the first execution on 7/7 fixtures, no alert on patched. |
| `official_20261118_c3b_hpc/` | C3b on HPC (Slurm jobs 52245 vulnerable, 52246 patched): grounded gpt-oss-120b seeds under 4 retrieval regimes on 5 fixtures; 20 seeds × 300 s; empty RPC; repo 093e5ae, binary d9cf542e; F1-F3 comparisons with random (A-1) and C3. |
| `official_20261120_ityfuzz_hpc/` | ItyFuzz (ISSTA 2023) single-chain baseline on HPC (14 per-fixture Slurm jobs itf_*): 7 on-chain fixtures × {vulnerable, patched} × 20 seeds × 300 s under the same valid-exploit criterion; ityfuzz 80e3b441, forge 1.9.0, solc 0.8.20. Reaches Ronin/Nomad/Verus, misses the relay/keeper-gated Qubit/FEG/PolyNetwork (C2 evidence) and CrossCurve (structured input); 0/140 patched alerts. First run discarded for a forge build-info race (fixed f5e4b73). |
| `official_20261113_crosscurve_sourceaddr_after/` | A-0 check of the CrossCurve patched control (sourceAddress binding); local WSL release build `cadd700c`; empty RPC. |
| `official_20261113_polynetwork_fromcontext_after/` | A-0 check of the PolyNetwork patched control (fromContract context); local WSL release build `cadd700c`; empty RPC; random seeds 1042/2042/3042 x 60 s. |
| `official_20261122_onchain_nomad/` | External validity: Nomad on deployed Ethereum bytecode (Alchemy archive fork); release build rustc 1.100.0 at `a9448c6`; 3 seeds x 75 s per variant; developer workstation (WSL2). |
| `official_20261123_atg_ablation/` | ATG-aware mutation on/off, FEG + PolyNetwork, random seeds, 20 x 300 s; Slurm jobs 111610/111611 (8 CPU, 16 GB), fixtures of `repo_c3b_093e5ae`; binary `bin/bridgesentry-fuzzer-8b53a55`, sha256 `5f219654985823741f628aa6a3a367bd80df4f6d29b79c10964e7294febd2a6c` (recovered 2026-11-28 from the sacct SubmitLine; the frozen REPORT omits it). |
| `official_20261123_gpt61terra_seedgen/` | Aborted OpenAI frontier-model seed generation (`BLOCKER_openai_cyberfilter`); no seed set from it is used in the paper. |
| `baseline_bridgefuzz_20261123/` | BridgeFuzz (EuroSec 2026) public artifact (Zenodo 17093557) run to characterise its oracle; RQ2 criterion comparison, not a same-fixture baseline. |
| `official_20261124_deepseek_seedgen/` | 20 grounded seed sets, `deepseek/deepseek-chat` (DeepSeek-V3) via OpenRouter, T=0.3, 2026-11-24; ledgers. |
| `official_20261124_deepseek_hpc/` | DeepSeek-V3 grounded seeds on HPC: 5 fixtures x 4 regimes x {vulnerable, patched} x 20 x 300 s; binary `d9cf542e`. |
| `official_20261124_onchain_ronin/` | External validity: Ronin bridge (2024) on deployed bytecode; release build rustc 1.100.0 at `0b9fd17`; 3 seeds x 75 s per variant; workstation. |
| `official_20261126_a5_parser_only_seedgen/` | A5: 5 parser-only (no-LLM Module 1) seed sets, `openai/gpt-oss-120b` via OpenRouter (`provider=nvidia` is the client label; base_url is OpenRouter), regime no_rag, 2026-11-26. |
| `official_20261126_a5_parser_only_hpc/` | A5 fuzzing on HPC: binary `d9cf542e`, 5 fixtures x {vulnerable, patched} x 20 x 300 s. |
| `official_20261126_onchain_fork_robustness/` | Nomad + Ronin forks, 10 seeds x {grounded, random, patched} x 75 s; binary `942f2813` (rustc 1.100.0) at `bf3c66b`; workstation. |
| `official_20261126_onchain_qubit/` | External validity: Qubit dual-chain (Ethereum + BSC archive forks); binary `942f2813` at `c09a393`; 3 seeds x 90 s per variant; workstation. |
| `official_20261127_benign_bridge/` | **Superseded by `official_20261128_benign_bridge/`** (compiled with solc 0.8.39, the local `solc-select` default, instead of the pinned 0.8.20). 0/40 alerts. Kept as history. |
| `official_20261127_reorg/` | **Superseded by `official_20261128_reorg/`** (solc 0.8.39, no binary hash). |
| `official_20261128_benign_bridge/` | A3 benign hard-negative re-run with the cluster build (binary `d9cf542e`, solc 0.8.20 `0479d44f`) at `9c21535`, on the workstation (WSL2, xargs -P 7): 40 paired runs (20 random + 20 llm) x 300 s, **0 with an alert** (exact 95% CI upper 8.8%), 0 runs with rc != 0, 17,245,122 executed traces; 2 unpaired runs, gain {"dest:0x9b137463d4e7986d7f535f9b79e28b4ef1938e9b": "190000000000000000000"}. Cluster job 182954 (same design) was queued behind the shared account's job limit. |
| `official_20261128_reorg/` | A6 reorg demonstration with full provenance: commit `9c21535`, release build `89fdbeb9` (rustc 1.100.0), solc 0.8.20; deterministic test (cargo test 196 + 177 passed) + 3 runs. |
| `official_20261128_a8_cost_latency/` | A8 analysis from committed ledgers/provenance (no new run): tokens, Module 1/2 latency, cost at OpenRouter list price (2026-11-28), seed-compiler repair rates. |
| `official_20261128_a7_survival/` | A7 analysis from committed per-run timings (no new run): Kaplan-Meier survival of the time to the first valid exploit for FEG SmartBridge and PolyNetwork, random vs grounded (no-retrieval) seeds, censored at 300 s; produces fig_survival_ttve.png. |

New campaigns: `scripts/official/run_matrix.sh experiments/official_<YYYYMMDD> <budget_s> <jobs> <bench>...`
