# On-chain fork robustness + unguided-search campaign (Nomad, Ronin)

Frozen record; do not edit after commit. Extends the two external-validity fork
reconstructions (`experiments/official_20261122_onchain_nomad`,
`experiments/official_20261124_onchain_ronin`, each n=3, seeded with the verbatim
exploit calldata) with an **n=10** robustness campaign on the **same deployed
mainnet bytecode**, adding an **unguided-search** arm. Same execution-only official
oracle, same seven exploit-evidence gates, same paired patched-variant control.

## What this campaign adds over the n=3 reconstructions
- n: 3 -> **10** seeds per arm, so the patched-variant hard-negative is **0/10** (not
  0/3) and the vulnerable reconstruction is shown seed-robust.
- A new **random (unguided) arm**: `BRIDGESENTRY_OFFICIAL_SEEDS=random` builds 20 random
  call sequences and does NOT read the LLM hypotheses or the verbatim exploit calldata
  (verified in `official_mode.rs::build_initial_corpus`: `random_seeds(world, rng, 20)`;
  the shared mutation dictionary "encodes no fixture-specific exploit"). So this arm is a
  genuine SEARCH on the real deployed bytecode, not a replay of the known transaction. The
  grounded (`llm`) arm continues to seed from the fixture's recorded exploit material.

## Provenance
- Repository commit: `bf3c66b` (branch `main`).
- Fuzzer: `src/module3_fuzzing/target/release/bridgesentry-fuzzer`, rustc 1.100.0;
  binary sha256 `942f28138b9aef1e0653676308bdbb23c2a7d57093ea226f54d296a392a44560`
  (recorded per fork in `<fork>/run_info.txt`).
- RPC: Ethereum mainnet **archive** endpoint (Alchemy). The URL carries an API key and is
  NOT recorded here or anywhere in the tree; it is read at run time from an environment
  file outside the tree.
- Fork blocks: Ronin **20468847**; Nomad **15259100** (both pre-incident).
- Evaluation mode: `BRIDGESENTRY_EVALUATION_MODE=official`; the Definition "valid exploit"
  criterion (seven exploit-evidence gates).
- Budget: 75 s/run, 1 run/seed, seeds 1042..10042. Date: 2026-11-26.
- Hardware: developer workstation (WSL2) over a residential link; the time to a valid
  exploit is dominated by cold archive-state RPC round-trips, reported only to show runs
  terminate, not as a performance measurement.

## Data integrity
A transient WSL DNS failure ("Temporary failure in name resolution") can make a run fall
back to synthetic state instead of the fork; such a run does NOT execute the deployed
bytecode and is invalid. We detect it by the log line "Dual-EVM init failed, fallback to
synthetic state" and exclude/retry it. Ronin: 2 grounded seeds (3042, 4042) hit this on the
first pass and were re-run to clean forks (`derivation/rerun_flaked_seeds.sh`); the other 28
forked on the first attempt. Nomad: the runner retries on fallback automatically; all 30 runs
forked on the first attempt (0 retries). Every recorded run below genuinely forked: verified
per run, **0 fallbacks** in the final set.

## Ronin bridge (2024) -- Ethereum archive fork @ block 20468847
Gateway proxy + implementation + USDC loaded at their on-chain addresses. The vulnerable
upgrade ran only one of two initializers, so total operator weight stayed 0, the vote-weight
threshold collapsed, and `submitWithdrawal` accepts a withdrawal backed by non-operator
signatures. Patched control = the **real redeployed fixed implementation** overlaid on the
implementation address (a genuine code-level fix), which reverts the zero-weight withdrawal.

| arm | result | median TTVE (s) | note |
|---|---|---|---|
| vulnerable x grounded | **10/10** valid | 42.3 | all 7 gates pass every run; gain 1,998,046.875 USDC via `MainchainGateway.submitWithdrawal` |
| vulnerable x random (unguided search) | **10/10** valid | 41.4 | search reconstructs the withdrawal on real bytecode without the verbatim calldata |
| patched x grounded | **0/10** (0 candidates) | -- | real fixed implementation; `patched_gain = {}` every run |

Gain is identical across seeds (1,998,046.875 USDC), consistent with a single documented
withdrawal path. All seven gates (`target_bytecode_executed`, `causal_path_valid`,
`material_state_change`, `capability_compliant`, `replayable`, `impact_demonstrated`,
`patched_rejected`) pass on every valid run.

## Nomad (2022) -- Ethereum archive fork @ block 15259100
Deployed Replica (beacon proxy), BridgeRouter (custodian), and WBTC loaded at their on-chain
addresses. A botched initialization set `confirmAt[bytes32(0)] = 1`, so `acceptableRoot(0)`
returned true and an unproven message passed `process(bytes)`, releasing bridge-held tokens.
Patched control = the same fork with the single misconfigured storage slot set to its correct
value (paired control, identical addresses).

| arm | result | median TTVE (s) | note |
|---|---|---|---|
| vulnerable x grounded | **10/10** valid | 30.7 | all 7 gates pass every run; gain 100 WBTC via `Replica.process` |
| vulnerable x random (unguided search) | **10/10** valid | 46.4 | search reconstructs the exploit on real bytecode; slower than grounded because it must assemble the crafted `process(bytes)` message |
| patched x grounded | **0/10** (0 candidates) | -- | root-cause slot fixed; `patched_gain = {}` every run |

All seven gates pass on every valid run; gain 100 WBTC (`asset0:WBTC = 10000000000`, 8 decimals)
through `Replica.process`.

## Reading
- The patched-variant control holds on real deployed/fixed bytecode at n=10 (**0/10 each
  fork**): the execution-only oracle + paired patched control (contribution C1) is robust and
  specific, not an artifact of n=3 or of the minimized fixtures.
- The exploit is reconstructed on the real bytecode by **unguided search** (random arm, 10/10
  on both forks), not only by replaying the known calldata -- a stronger external-validity
  statement than the n=3 runs.
- Grounded vs random: on Ronin they are indistinguishable (median ~41-42 s, RPC-bound); on
  Nomad grounded is modestly faster (median 30.7 vs 46.4 s) because random must assemble the
  crafted `process(bytes)` message. Both arms reconstruct every run, so semantic seed guidance
  gives no change in success and at most a modest TTVE effect on one fork -- consistent with
  RQ3 and the LLM-excluded title.

## Files
- `ronin/runs/{vulnerable_llm,patched_llm,vulnerable_random}/seed_<n>.{json,log}` (n=10 each)
- `nomad/runs/{vulnerable_llm,patched_llm,vulnerable_random}/seed_<n>.{json,log}` (n=10 each)
- `<fork>/run_info.txt` (binary sha, commit, rustc, date)
- `derivation/` (campaign runners + the flaked-seed re-run + aggregator)
