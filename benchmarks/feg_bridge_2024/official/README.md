# FEG SmartBridge — official fixture (December 2024)

## Incident

- **Date (UTC):** 2024-12-29
- **Chains:** Ethereum, BSC, Base (the fixture models one representative source→dest pair)
- **Loss:** ~$1.0M–$1.3M (sources differ; recorded as a range)
- **Flash loan:** no
- **Class:** cross-chain message source-verification bypass (V1)

## Root cause (from the post-mortems)

FEG's **SmartBridge** receives cross-chain messages relayed through **Wormhole**.
Wormhole faithfully attests and delivers the *true* emitter address
(`sourceAddress`) of each message. FEG's handler, however, checked that
`sourceAddress` was a trusted FEG endpoint **only on the token-release path**.
The op that *extends the trusted-source whitelist* performed no such check.

So the attacker:

1. published a Wormhole message **from their own contract** that added that
   contract to FEG's trusted-source whitelist (`sourceAddress` = attacker's
   contract — never verified for this op); then
2. published a second message invoking the withdraw/release path. Because the
   attacker's source was now "trusted", the SmartBridge released FEG from its
   reserve to the attacker **without any deposit on the source chain**.

CertiK: *"After the address of the attacker-controlled contract is added to the
whitelisted `sourceAddress`, the attacker can send a malicious message to invoke
`registerWithdraw` and set the FEG balance in the FEG SmartBridge to be
withdrawable by the attacker."* The Wormhole Foundation confirmed its own
contracts were unaffected — the defect was a logical error in FEG's relay
handling.

### Faulty function

`FEGSmartBridge.receiveMessage(address sourceAddress, bytes payload)` — the
`OP_SET_TRUSTED` branch (whitelist extension) with no `sourceAddress` guard.

### Attack transaction chain (modelled)

1. `WormholeCore.publishMessage(encode(SET_TRUSTED, attacker, 0))`  → relayer →
   `FEGSmartBridge.receiveMessage(attacker, …)` → `trustedSource[attacker]=true`.
2. `WormholeCore.publishMessage(encode(RELEASE, attacker, amount))` → relayer →
   `FEGSmartBridge.receiveMessage(attacker, …)` → `require(trustedSource[attacker])`
   now passes → `feg.transfer(attacker, amount)`.

## The project's fix

FEG restricted the trusted-source / whitelist-mutation path to already-trusted
sources (equivalently, validated the message `sourceAddress` on every op). In
this fixture the patch adds the same guard the RELEASE op already had to the
SET_TRUSTED op:

```diff
         if (op == OP_SET_TRUSTED) {
-            // VULNERABLE: the whitelist can be extended by a message from ANY
-            // source, so an untrusted sourceAddress can whitelist itself.
+            require(trustedSource[sourceAddress], "untrusted source"); // PATCH
             trustedSource[account] = true;
             emit TrustedSet(account);
         } else if (op == OP_RELEASE) {
```

That is the only functional change between `vulnerable/` and `patched/`.

## Harness / capability notes

- The attacker uses **only legal actions**: anyone may publish a Wormhole
  message, and the fixture's `WormholeCore` emits the attacker's *real* address
  as `sourceAddress`. No role is impersonated, no relay is tampered with.
- Profit flows through the protocol's **release entrypoint**
  (`FEGSmartBridge.receiveMessage`, executed by the faithful relayer).
- Replay is deterministic; on `patched/` the same trace yields no profit.
- **Execution is local-fixture** via `scripts/official/empty_rpc.py` (empty
  chain state). This is **not** a mainnet-fork replay; `metadata.fork.block_number`
  is a non-zero placeholder.

## Sources

- CertiK — FEG Bridge Exploit Technical Analysis:
  https://www.certik.com/resources/blog/feg-bridge-exploit-technical-analysis
- Halborn — Explained: The Feed Every Gorilla (FEG) Hack (December 2024):
  https://www.halborn.com/blog/post/explained-the-feed-every-gorilla-feg-hack-december-2024
- PeckShield (X): https://x.com/peckshield/status/1873786831868756036
- Wormhole Foundation statement (PANews): https://www.panewslab.com/en/articles/h3d1wi6g

(Verified in-session via web search; direct page fetches to certik.com / halborn.com
were blocked by the session network policy, so quotations are taken from the search
index summaries of those analyses.)
