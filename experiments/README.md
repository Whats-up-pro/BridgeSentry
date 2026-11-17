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

New campaigns: `scripts/official/run_matrix.sh experiments/official_<YYYYMMDD> <budget_s> <jobs> <bench>...`
