# CrossCurve — official fixture (January 2026)

## Incident

- **Date (UTC):** 2026-01-31 (sources range 2026-01-31 … 2026-02-02)
- **Chains:** multi-chain; most losses on Arbitrum. Fixture models one source→dest pair.
- **Loss:** ~$1.4M–$3M (sources differ; recorded as a range)
- **Flash loan:** no
- **Class:** cross-chain message validation bypass (V1)

## Root cause (from the post-mortems)

CrossCurve is built on **Axelar** messaging. Its `ReceiverAxelar` contract had
a normal `execute` path that validated an incoming command with the Axelar
gateway (`validateContractCall`), and a fast **`expressExecute`** path that
**did not**. `expressExecute` was callable by anyone and acted on the supplied
payload directly, so an attacker could submit a **fabricated command and
payload** and have the `PortalV2` reserve release tokens that were never locked
on the source chain. Olympix/QuillAudits describe it as a missing access-control
/ gateway-validation check; its only guard was a peer check on
attacker-controlled `sourceChain`/`sourceAddress`, which gave no real security.

### Faulty function

`ReceiverAxelar.expressExecute(bytes32 commandId, bytes payload)` — executed the
payload without `gateway.validateContractCall(commandId)`.

### Attack transaction (modelled)

`ReceiverAxelar.expressExecute(forgedCommandId, abi.encode(attacker, amount))`
→ `PortalV2.release(attacker, amount)`. No source-chain deposit backs it.

## The project's fix

Validate every message with the gateway before acting on it — i.e. add the same
`validateContractCall` guard the normal path already had to the express path:

```diff
     function expressExecute(bytes32 commandId, bytes calldata payload) external {
+        require(gateway.validateContractCall(commandId), "not approved by gateway"); // PATCH
         _execute(payload);
     }
```

That is the only functional change between `vulnerable/` and `patched/`. Genuine,
gateway-attested messages still execute on both paths.

## Harness / capability notes

- The attacker uses only a legal public call (`expressExecute`); no role is
  impersonated and the faithful relay is untouched. The honest path
  (source deposit → gateway attests → `execute` releases to the real recipient)
  is exercised in setup and keeps working after the patch.
- Profit flows through the release entrypoint `ReceiverAxelar.expressExecute`
  on the destination chain.
- Replay is deterministic; the patched variant yields no profit on the same trace.
- **Execution is local-fixture** via `scripts/official/empty_rpc.py` (empty
  state) — **not** a mainnet fork; `metadata.fork.block_number` is a placeholder.

## Sources

- Halborn — Explained: The CrossCurve Hack (February 2026):
  https://www.halborn.com/blog/post/explained-the-crosscurve-hack-february-2026
- BlockSec — Weekly Web3 Security Incident Roundup (Feb 2–8 2026):
  https://blocksec.com/blog/weekly-web3-security-incident-roundup-feb-2-feb-8-2026
- QuillAudits — CrossCurve $1.4M Exploit:
  https://www.quillaudits.com/blog/hack-analysis/cross-curve-exploit
- Olympix — CrossCurve Exploit Post-Mortem:
  https://olympixai.medium.com/crosscurve-exploit-post-mortem-1-4m-lost-to-a-missing-access-control-check-c128e0aeb360

(Verified in-session via web search; direct page fetches were blocked by the
session network policy, so details come from the search-index summaries.)
