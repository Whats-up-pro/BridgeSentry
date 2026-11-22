# On-chain fork reconstruction — Nomad Bridge (Ethereum, August 2022)

Frozen record; do not edit after commit. It documents a reconstruction of a real
cross-chain bridge exploit on the **actual deployed mainnet bytecode**, forked
from Ethereum archive state, under the same execution-only official oracle used
for the local-reconstruction fixtures. It demonstrates external validity: the
harness, the seven exploit-evidence gates, and the patched control all operate
unchanged on real on-chain code.

## Provenance

- Repository commit: `a9448c6` (branch `main`).
- Fuzzer: `cargo build --release`, rustc 1.100.0; binary sha256
  `119986a1d2f09a03343245a870851df6d765b2a2a049630cc7f5ae43b0a670d9`.
- solc 0.8.20 present but unused in on-chain mode (no contract is compiled).
- RPC: Ethereum mainnet **archive** endpoint (Alchemy). The URL carries an API
  key and is NOT recorded here or anywhere in the repository; it is read at run
  time from an environment file outside the tree.
- Fork block: **15259100** (Ethereum, 2022-08-01), the block immediately before
  the first exploit transaction.
- Evaluation mode: `BRIDGESENTRY_EVALUATION_MODE=official` (execution-only
  asset-conservation oracle; the Definition "valid exploit" criterion).
- Date: 2026-11-22.
- Hardware note: run on a developer workstation over a residential link. The
  time-to-valid-exploit is dominated by cold archive-state RPC round-trips, not by
  compute; it is reported only to show the run terminates, not as a performance
  measurement.

## Incident and model

Nomad's Replica accepted any message because a botched initialization set
`confirmAt[bytes32(0)] = 1`, so `acceptableRoot(bytes32(0))` returned true and an
unproven message passed the `process(bytes)` guard, releasing bridge-held tokens
to the caller-specified recipient (~$190M drained across hundreds of copycat
transactions).

On-chain fixture (`benchmarks/nomad/official/spec_onchain.json`, `mode: onchain`):

| role | address | note |
|---|---|---|
| Replica (entrypoint) | `0x5d94309e5a0090b165fa4181519701637b6daeba` | beacon proxy; `process(bytes)` |
| BridgeRouter (custodian) | `0x88a69b4e698a4b090df6cf5bd7b2d47325ad30a3` | holds locked tokens; excluded from the attacker set |
| WBTC (asset) | `0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | drained token |

Seeds are the real on-chain `process(bytes)` exploit calldatas, taken verbatim
from mainnet:

| tx | recipient | drained |
|---|---|---|
| `0xb1fe26cc8892f58eb468f5208baaf38bac422b5752cca0b9c8a871855d63ae28` | `0xb5c55f76…590e` | 100 WBTC |
| `0xa5fe9d044e4f3e5aa5bc4c0709333cd2190cba0f4e7f16bcf73f49f83e4a5460` | `0xa8c83b1b…cd9d` (original attacker) | 100 WBTC |
| `0x498a0778cc8448a10054d71508dee1a65b5f336daebba8ef859e712000391db9` | `0xe4a4df7e…c5b3` | 100 WBTC |

## Variants

- **vulnerable**: the real forked state (`confirmAt[bytes32(0)] = 1`).
- **patched**: the same block and the same real bytecode, with the single storage
  slot whose misconfiguration *is* the vulnerability written to its correct value —
  `confirmAt[bytes32(0)]` at slot
  `0x235d629dc802037ded8c61cb27fb29e40fa01b299719d8f991ffe20bdcc59f4f` set from `1`
  to `0`. This is the minimal faithful patch: exactly the fix for the botched
  initialization. The two variants are identical in every other respect, so the
  patched run is a true paired control (identical addresses, identical calldata).

## Results (release build, budget 75 s, 3 seeds per variant)

| variant | valid / runs | gain per valid run | entrypoint | seven gates | TTVE median |
|---|---|---|---|---|---|
| vulnerable | **3 / 3** | 100 WBTC (`asset0:WBTC = 10000000000`, 8 decimals) | `Replica.process` | all pass | 44.75 s |
| patched | **0 / 3** | — | — | — | — |

Every vulnerable run passes all seven exploit-evidence gates
(`target_bytecode_executed, material_state_change, causal_path_valid,
capability_compliant, replayable, patched_rejected, impact_demonstrated`); the
paired patched run yields zero gain (`patched_control.patched_gain = {}`) because
with `confirmAt[bytes32(0)] = 0` the real `process` reverts at `acceptableRoot`.
Per-run result JSONs are under `runs/`.

## What this shows

The execution-only oracle and the full gate pipeline reconstruct a real,
high-value cross-chain bridge exploit on the exact bytecode deployed on Ethereum
mainnet — not a minimized re-implementation — and the minimal on-chain patch (one
storage slot, the literal fix) is rejected. This is direct evidence that the
method's reconstruction and patched-difference criterion are not artifacts of
simplified fixtures.
