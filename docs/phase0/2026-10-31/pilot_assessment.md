# Nomad Pilot Fixture Assessment

Source baseline: db20af7703654dd487f6d179070b0e7f664869cc. This is a source assessment, not an executed exploit or completed paired benchmark.

## Candidate boundary

The Nomad-inspired EVM reconstruction has an explicit zero-root verification predicate and router path. It is a model, not byte-for-byte production Nomad. Existing Ethereum/Moonbeam labels do not prove the cached Ethereum execution is a complete two-chain causal exploit.

## Targeted patch and confounders

Replica.initialize(0x00, delay) sets confirmAt[0]=1. Unproven message hashes map to zero; acceptableRoot(0) then accepts after timestamp 1. A targeted control can reject root zero before the confirmation-time lookup, while preserving valid nonzero proven messages and processed-message rejection. Freeze patch diff, compiler settings and bytecode hashes before comparisons.

Replica.prove(hash, root) is public and checks no Merkle proof or authorized updater. A caller could use a different root and wait after a zero-root-only patch. Restrict this unmodeled proof oracle to trusted setup/relay actions under the pilot capability policy, or document a faithful proof adapter. Such a different root cause must not be mislabeled as failure of the targeted patch.

MockToken.mint(to, amount) is unrestricted. Direct minting does not demonstrate bridge exploitation. Require an enforceable minter role or callable-target policy and independently check the caller -> router -> replica -> token causal path. Balance changes alone are insufficient.

Router minting after Replica.process proves only a destination path. A cross-chain causal claim additionally needs a source receipt and canonical message binding. Otherwise restrict claims to destination authentication-bypass reconstruction. Initialization is trusted setup unless the studied bug explicitly concerns deployment initialization. Message.sol models message shape, not exact production encoding.

## Tests needed before pilot eligibility

- Unproven zero-root message: vulnerable succeeds, patched rejects.
- Proven valid nonzero message: both accept with trusted proof setup.
- Same-message and reused-nonce replay: both reject.
- Revert: no committed mint, logs or material effect.
- Unauthorized direct prove/mint: disallowed or adjudicated outside the target root cause.
- Missing bytecode or semantic mapping: evidence remains ineligible.
- Same execution with changed scenario prose: unchanged validator verdict.

No patched Solidity implementation or valid exploit is claimed complete here. No live on-chain transaction, LLM request or external RPC call was sent by the audit command.
