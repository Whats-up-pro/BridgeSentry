# On-chain fork reconstruction - Qubit (QBridge), January 2022 - DUAL-CHAIN

Frozen record; do not edit after commit. Third external-validity case and the first
genuinely **dual-chain** one: a real cross-chain bridge exploit reconstructed on the
**actual deployed bytecode of two different chains** (Ethereum source + BNB Smart Chain
destination), forked from archive state, under the same execution-only official oracle and
the same seven exploit-evidence gates. The attacker's gain is on the destination chain,
reached only through the faithful relay - exactly the dual-chain capability the harness claims.

## Provenance
- Repository commit: `c09a393` (branch `main`).
- Fuzzer: `src/module3_fuzzing/target/release/bridgesentry-fuzzer`, rustc 1.100.0;
  binary sha256 `942f28138b9aef1e0653676308bdbb23c2a7d57093ea226f54d296a392a44560`.
- RPC: Ethereum mainnet archive + BSC mainnet archive (Alchemy). The URLs carry API keys and
  are NOT recorded here or anywhere in the tree; read at run time from an env file outside it.
- Fork blocks: Ethereum **14090169** (pre-attack; from DeFiHackLabs `Qubit_exp.sol`), BSC
  **14738000** (pre-attack, before the deposit nonce is voted; the real mint tx is BSC 14742312).
- Evaluation mode: `BRIDGESENTRY_EVALUATION_MODE=official`; the Definition "valid exploit" criterion.
- Budget 90 s/run, seeds 1042/2042/3042, both variants. Date: 2026-11-26.
- Hardware: developer workstation (WSL2) over a residential link; times are RPC-bound and not reported.

## Incident and model
On 2022-01-27 an attacker drained ~$80M from Qubit Finance. The Ethereum QBridge's legacy
`deposit(uint8,bytes32,bytes)` routes to `QBridgeHandler.deposit`, which for the ETH resource
reads `resourceIDToTokenContractAddress[resourceID] = address(0)` and requires
`contractWhitelist[address(0)] = true`; its modified `safeTransferFrom` used a raw `.call()`
that does not revert on the zero address, so a **0-value deposit** still emits a `Deposit`
event. The Qubit relayer carried that event to the BSC QBridge `voteProposal`, which minted
qXETH to the attacker with no ETH locked. Verified on-chain this session (`cast`):
`contractWhitelist(0)=true` and `resourceIDToTokenContractAddress(RID)=address(0)` at the ETH fork.

On-chain fixture (`benchmarks/qubit/official/spec_onchain.json`, `mode: onchain`, `cross_chain: true`):

| role | address | side | note |
|---|---|---|---|
| QBridge (entry) | `0x20E5E35ba29dC3B540a1aee781D0814D5c77Bce6` | source (ETH) | `deposit` emits `Deposit(...,bytes data)` |
| QBridgeHandler | `0x17B7163cf1Dbd286E262ddc68b553D899B93f526` | source (ETH) | proxy; `contractWhitelist` / `resourceIDToTokenContractAddress` |
| QBridge | `0x4d8aE68fCAe98Bf93299548545933c0D273BA23a` | dest (BSC) | `voteProposal` mints on the relayed deposit |
| qXETH | `0xfd7a5506f434f5334c100efb765025243c39137c` | dest (BSC) | minted to the attacker (the gain) |

Seed: the real on-chain QBridge `deposit` calldata (ETH tx `0xac7292e7...`, selector `0x05e2ca17`,
deposit nonce 86, claimed 190 ETH), replayed verbatim; the faithful relay rule maps the emitted
`Deposit` event to `voteProposal(0, ev:depositNonce, ev:resourceID, ev:data)`. Because the real BSC
QBridge gates `voteProposal` to a registered relayer (`"QBridge: caller is not the relayer"`), the
harness relayer is granted RELAYER_ROLE in a setup call
`grantRole(0xe2b7fb3b...dc4, harnessRelayer)` from the on-chain admin `0xbeE39712...` (modeled: the
legitimate relayer delivers the message; the exploit abuses a faithful relay, not a compromised one).
The patched variant flips one storage slot, `contractWhitelist[address(0)]` (mapping base slot 105,
so `keccak(0.105)` = `0x5843af22...18cf41`) from true to false, so the handler's whitelist check
reverts the fake deposit; the two variants are otherwise identical.

## Result
| arm | result |
|---|---|
| vulnerable x grounded (real deposit calldata) | **3/3 valid**; gain 190 qXETH (`asset0:qXETH = 190000000000000000000`) via `QBridgeBSC.voteProposal@dest:Relay`; all 7 gates pass |
| patched x grounded (`contractWhitelist[0]=false`) | **0/3** (0 candidates; the deposit reverts, no event, no mint) |

All seven gates (`target_bytecode_executed`, `causal_path_valid`, `material_state_change`,
`capability_compliant`, `replayable`, `impact_demonstrated`, `patched_rejected`) pass on every
vulnerable run; the patched replay of every candidate is empty (`patched_gain = {}`). Data integrity:
0 synthetic fallbacks across all 6 runs (verified per run).

## Significance
This is the first reconstruction in which the attacker's gain is on the **destination chain**,
produced by the harness executing the source chain, the faithful relay, and the destination chain
together on real deployed bytecode of two separate networks. It exercises the dual-chain + relay
path (contribution C2) end to end on a real incident, where Nomad and the Ronin bridge are
destination-chain-only drains. All three fork reconstructions (Nomad, Ronin, Qubit) use the same
oracle, the same seven exploit-evidence gates, and the same patched-variant control.

## Files
- `runs/{vulnerable,patched}/seed_{1042,2042,3042}.{json,log}`
- `run_info.txt` (binary sha, commit, blocks, addresses)
- `derivation/run_qubit_campaign.sh`
- fixture: `benchmarks/qubit/official/spec_onchain.json`
