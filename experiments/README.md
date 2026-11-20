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

New campaigns: `scripts/official/run_matrix.sh experiments/official_<YYYYMMDD> <budget_s> <jobs> <bench>...`
