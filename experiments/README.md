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

New campaigns: `scripts/official/run_matrix.sh experiments/official_<YYYYMMDD> <budget_s> <jobs> <bench>...`
