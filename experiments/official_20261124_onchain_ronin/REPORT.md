# On-chain fork reconstruction — Ronin Bridge (Ethereum, August 2024)

Frozen record; do not edit after commit. Second external-validity case (after
Nomad): a real cross-chain bridge exploit reconstructed on the **actual deployed
Ethereum mainnet bytecode**, forked from archive state, under the same
execution-only official oracle and the same seven exploit-evidence gates. The
patched control here is the **real redeployed fixed implementation**, so the
paired difference is a genuine code-level fix, not a hand-set storage value.

## Provenance

- Repository commit: `0b9fd17` (branch `main`).
- Fuzzer: `cargo build --release`, rustc 1.100.0; binary sha256
  `942f28138b9aef1e0653676308bdbb23c2a7d57093ea226f54d296a392a44560`.
- RPC: Ethereum mainnet **archive** endpoint (Alchemy). The URL carries an API
  key and is NOT recorded here or anywhere in the repository; read at run time
  from an environment file outside the tree.
- Fork block: **20468847** (Ethereum), in the Aug-2024 vulnerable window,
  immediately before the real USDC-draining transaction (block 20468848).
- Evaluation mode: `BRIDGESENTRY_EVALUATION_MODE=official` (execution-only
  asset-conservation oracle; the Definition "valid exploit" criterion).
- Date: 2026-11-24.
- Hardware note: run on a developer workstation over a residential link; the
  time to a valid exploit is dominated by cold archive-state RPC round-trips,
  reported only to show the run terminates, not as a performance measurement.

## Incident and model

On 2024-08-06 a proxy upgrade moved the Ronin mainchain gateway from v2 to v4 but
ran only `initializeV4`, skipping `initializeV3`. `_totalOperatorWeight` stayed 0,
so `minimumVoteWeight()` collapsed and `submitWithdrawal` accepted a withdrawal
backed by non-operator signatures, draining ~4000 ETH and ~1.998M USDC
(whitehat/MEV; funds returned). Verified on-chain: the gateway proxy's ETH
balance drops 3996.09 ETH at block 20468679.

On-chain fixture (`benchmarks/ronin_2024/official/spec_onchain.json`, `mode:
onchain`):

| role | address | note |
|---|---|---|
| MainchainGateway (entrypoint) | `0x64192819ac13ef72bf6b5ae239ac672b43a9af08` | transparent proxy; `submitWithdrawal(Receipt,Signature[])` |
| implementation (vulnerable) | `0xfc274ec92bbb1a1472884558d1b5caac6f8220ee` | the deployed buggy impl (delegatecall target) |
| implementation (fixed) | `0x5019d41b0737e39b51fd6da4859f3e27579e4e69` | Ronin's redeployed impl; used as the patch code |
| USDC (asset) | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | drained token |

Seed = the real on-chain USDC withdrawal (receipt id 166633, recipient
`0x6980a47b…` [attacker-side, non-excluded], 1,998,046.875 USDC), taken from tx
`0xbce5b8548db486c561948e8a177c8ccaa72810f972cee3909ea50af015a60ad8`. The exact
`submitWithdrawal` calldata was lifted from the mainnet trace with `cast run`
(debug_trace is unavailable on the Alchemy tier) and verified to drain at the
fork block with `cast call`. The ETH drain (tx `0x26195700…`, 3996 ETH) is
**omitted**: it pays native ETH, which emits no ERC-20 `Transfer` log for the
execution-only oracle.

## Variants

- **vulnerable**: the real forked state and real buggy implementation.
- **patched**: the same block and seed, with `PatchSpec.code` overlaying the
  gateway implementation's runtime with the **real fixed implementation's**
  runtime bytecode (`0x5019d41b…`, 24 KB, fetched from mainnet). The fixed code
  rejects the null-weight withdrawal with `ErrNullTotalWeightProvided`. The two
  variants are identical in every other respect, so the patched run is a true
  paired control (identical addresses, identical calldata). This is faithful to
  the real fix, which was a redeploy, not a single storage flip (the `v3`
  reinitializer is version-locked by `initializeV4`).

## Results (release build, budget 75 s, 3 seeds per variant)

| variant | valid / runs | gain per valid run | entrypoint | seven gates |
|---|---|---|---|---|
| vulnerable | **3 / 3** | 1,998,046.875 USDC (`asset0:USDC = 1998046875000`, 6 decimals) | `MainchainGateway.submitWithdrawal` | all pass |
| patched | **0 / 3** | — | — | — |

Every vulnerable run passes all seven exploit-evidence gates
(`target_bytecode_executed, material_state_change, causal_path_valid,
capability_compliant, replayable, patched_rejected, impact_demonstrated`); the
paired patched run yields zero gain (`patched_control.patched_gain = {}`) because
the fixed implementation reverts the withdrawal. Per-run result JSONs under
`runs/`.

## What this shows

A second real, high-value cross-chain bridge exploit (distinct root cause from
Nomad: an operator-weight reinitialization defect vs. a message-root flag) is
reconstructed on the exact bytecode deployed on Ethereum mainnet, and the paired
control — the actual redeployed fixed implementation — is rejected. With Nomad,
this gives two independent incidents under the execution-only oracle on real
on-chain code, strengthening external validity beyond minimized re-implementations.
