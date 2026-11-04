# Verus-Ethereum Bridge — official fixture (May 2026)

## Incident

- **Date (UTC):** 2026-05-18
- **Chains:** Verus (non-EVM) ⇄ Ethereum
- **Loss:** ~$11.58M
- **Flash loan:** no
- **Class:** missing source↔payout reconciliation (V1)

## Root cause (from the post-mortems)

The Verus-Ethereum bridge imports value from Verus to Ethereum. On the Ethereum
side, `checkCCEValues` verified the **notary signatures and Merkle proofs** of an
incoming import — proving an export really happened on Verus — but it **did not
reconcile the Ethereum payout against the value actually committed in that
export**. An attacker could reference a small (or crafted) attested export yet
claim a far larger payout, and the bridge paid it out (Blockaid; Merkle Science;
Halborn). BlockSec frames the same gap as a supplemental/primary export
type-confusion; either way, a payout not backed by a matching committed export
value was accepted. The reported fix was about ten lines of Solidity.

### Faulty function

`VerusBridge.checkCCEValues` — no reconciliation of `payout` against the
committed Verus export value.

### Attack transaction (modelled)

1. `VerusExportSurrogate.export(id, attacker, 1e18)` → honest notary relays
   `VerusBridge.recordExport(id, 1e18)`.
2. `VerusBridge.submitImports(attacker, 500000e18, id)` → the attested export
   exists, `checkCCEValues` does not compare the payout to it → pays `500000e18`.

## The project's fix

Reconcile the payout against the committed source value:

```diff
     function checkCCEValues(uint256 payout, bytes32 exportId) internal view {
-        // VULNERABLE: the Ethereum payout is never reconciled against the value
-        // committed on the Verus side (committedExport[exportId]).
-        payout; exportId;
+        // PATCH: reconcile the payout against the committed source value.
+        require(claimed[exportId] + payout <= committedExport[exportId], "payout exceeds committed source value");
     }
```

That is the only functional change; honest imports (payout ≤ committed value)
still succeed.

## Modelling notes (fidelity & deviations)

- **Non-EVM source.** Verus is not an EVM chain. `VerusExportSurrogate` is a
  SURROGATE on the source EVM standing in for a Verus export; `metadata.source_chain`
  uses `chain_id: 0` to flag this.
- **Honest notary.** Notary signatures / Merkle proofs are treated as honest:
  the harness relay faithfully delivers attested exports via `recordExport`
  (notary-only). The attacker **cannot fabricate** an export — only over-claim
  against a real one. That is exactly the modelled defect.
- **Capability compliance.** The attacker uses only legal actions (a genuine
  small export, then a public `submitImports`). No signature is forged and the
  relay is untouched.
- Profit flows through the release entrypoint `VerusBridge.submitImports`.
- **Execution is local-fixture** via `scripts/official/empty_rpc.py` (empty
  state) — **not** a mainnet fork; `metadata.fork.block_number` is a placeholder.

## Sources

- Halborn — Explained: The Verus-Ethereum Bridge Hack (May 2026):
  https://www.halborn.com/blog/post/explained-the-verus-ethereum-bridge-hack-may-2026
- Merkle Science — Hack Track: The $11.58M Verus Bridge Hack:
  https://www.merklescience.com/blog/hack-track-the-11-58m-verus-bridge-hack
- BlockSec — Web3 Security: Verus, RetoSwap & More:
  https://blocksec.com/blog/web3-security-verus-bridge-retoswap-more
- CryptoMode — Verus-Ethereum Bridge Hacked For $11.58M:
  https://cryptomode.com/news/crypto/verus-ethereum-bridge-hack/

(Verified in-session via web search; direct page fetches were blocked by the
session network policy, so details come from the search-index summaries.)
