# Official-oracle runners

Reusable scripts for `BRIDGESENTRY_EVALUATION_MODE=official` campaigns. This is the
canonical runner: use it for every new campaign. The scripts inside
`experiments/official_*/` are frozen records of what produced each round's
numbers; do not edit them and do not use them for new runs.

| File | Purpose |
| --- | --- |
| `run_official.sh` | One job: `<bench> <vulnerable\|patched> <llm\|random> <seed> <budget_s> [out_root]`. Repo root from `git rev-parse`; source block from `fork.block_number`, destination block from `fork.dest_block_number` (falls back to `fork.block_number`). |
| `run_matrix.sh` | `<out_root> <budget_s> <parallel_jobs> <bench>...`: runs {vulnerable, patched} × {llm, random} × `$SEEDS` and aggregates. |
| `aggregate_official.py` | `<runs_root>` → `<runs_root>/summary_official.csv` (same columns as round 1; non-triggering runs are right-censored at the budget). |
| `empty_rpc.py` | JSON-RPC stub serving an empty chain state. |

Prerequisites: `cargo build --release` in `src/module3_fuzzing`, `solc` 0.8.20 on `PATH`, Python 3.

Example (5 seeds × 20 s, two jobs in parallel):

```bash
scripts/official/run_matrix.sh experiments/official_YYYYMMDD 20 2 nomad qubit
```

Reporting rules:

- With `empty_rpc.py` the run is **local-fixture execution, not a mainnet fork**; every report must say so. Set `RPC_URL` to use a real fork endpoint instead.
- Record commit hash, `rustc`/`solc` versions, the LLM that produced `benchmarks/<bench>/llm_outputs/` (currently gpt-oss-120b, April 2026), seeds and budget.
- Round 1 passed a fixed `--source-block/--dest-block 15259100` for every bench; these scripts read the block from metadata instead. With `empty_rpc.py` this only changes the block environment; the 2026-11-03 rerun reported identical outcomes for Nomad and Qubit.
