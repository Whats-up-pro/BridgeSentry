# A3: benign hard-negative (correct lock-mint bridge), re-run with the cluster build

Frozen record, 2026-11-28. **Supersedes `official_20261127_benign_bridge/`**, which was
compiled with solc 0.8.39 (the local `solc-select` default) instead of the pinned 0.8.20.
Same fixture, same design, same outcome.

## Provenance (`run_info.txt`)

- Commit `9c21535bff41bf14efeaee1da6e889a9103793ee`; fixture `benchmarks/benign_bridge`
  unchanged since `f51223d` (deterministic test `benign_bridge_official_no_alert` passes).
- Fuzzer: **the statically linked build of the cluster campaigns** (A-1, C3, C3b, DeepSeek,
  A5), sha256 `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848`, copied
  from `/datastore/dungtrt/bridgesentry/bin/` and hash-checked.
- solc 0.8.20 static, sha256 `0479d44fdf9c501c25337fdc540419f1593b884a87b47f023da4f1c700fda782`
  (same binary as the cluster's `bin/solc`).
- Host: developer workstation (WSL2, 16 vCPU), `xargs -P 7`, one shared empty RPC
  (`scripts/official/empty_rpc.py`): local fixtures, not a mainnet fork. The same design was
  submitted to the cluster as Slurm job 182954, which stayed pending behind the shared
  account's job limit (three long jobs of other users held every slot); if it completes,
  its result is added as a separate record.
- The binary predates `BRIDGESENTRY_OFFICIAL_SPEC`, so the unpaired ablation used a staging
  copy outside the repo whose `official/spec.json` is byte-identical to
  `benchmarks/benign_bridge/official/spec_unpaired.json` (hashes in `run_info.txt`).

## Design

20 random seeds (strict seeds off, as A-1) and 20 llm seeds (the single legitimate-deposit
scenario, strict on, as C3b), seeds 1042..20042, 300 s each, vulnerable variant
(`vulnerable == patched`); plus 2 llm runs with the asset pairing removed.

## Result (`summary.csv`)

| Condition | Runs | Runs with an alert | Runs with rc != 0 | Traces per run (min / median / max) |
| --- | --- | --- | --- | --- |
| Paired, random seeds | 20 | 0 | 0 | see `summary.csv` |
| Paired, llm seed | 20 | 0 | 0 | see `summary.csv` |
| **Paired, total** | **40** | **0** | **0** | 250,265 / 428,179 / 600,228 (17,245,122 in total) |
| Unpaired, llm seed | 2 | 2 (gain 190e18 DstToken each) | 0 | — |

False-positive rate **0/40**, exact 95% Clopper–Pearson interval **[0, 8.8%]**. With the
pairing removed, the same legitimate flow reports the 190e18 DstToken release as a gain, so
the bridge moves value and the cross-chain asset pairing is what nets it to zero.

## Limit

One benign bridge of the lock-mint design class, not a sample of production bridge code.
