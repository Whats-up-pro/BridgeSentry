# Ronin Bridge — official fixture (August 2024)

## Incident

- **Date (UTC):** 2024-08-06
- **Chains:** Ronin ⇄ Ethereum mainchain (exploit tx on the Ethereum gateway)
- **Loss:** ~$10M–$12M (~3,996 ETH + ~1,998,046 USDC). Whitehat; funds returned.
- **Flash loan:** no
- **Class:** uninitialised vote threshold (V1)

> Not to be confused with the **March 2022** Ronin incident (validator private-key
> compromise), which is a Group-B off-chain-key case and is not this fixture.

## Root cause (from the post-mortems)

A Ronin bridge upgrade added two initialisers, `initializeV3` and
`initializeV4`. `initializeV3` sets `totalOperatorWeight` — the sum of the
bridge operators' voting weights, which the withdrawal threshold is a
percentage of. During the upgrade the deployer ran **only `initializeV4`**, so
`totalOperatorWeight` stayed `0`. The withdrawal threshold `minimumVoteWeight()`
is computed from that total, so it became `0`, and a withdrawal cleared the
operator-vote check **with no approvals at all**. An attacker (here, a whitehat
MEV bot) withdrew the mainchain reserve by submitting a withdrawal with an empty
signer set. Verichains: *"The latest upgrade stores totalWeight in the
contract's storage under the variable `_totalOperatorWeight` … initialized in
`initializeV3()`, but the deployer only called `initializeV4`."*

The defect was in the **deployment procedure**, not the contract logic. No
operator signatures were forged.

### Faulty path

Skipped `initializeV3` → `totalOperatorWeight == 0` →
`RoninGatewayV3.minimumVoteWeight() == 0` → `RoninGatewayV3.withdraw(...)` passes
with no votes.

### Attack transaction (modelled)

`RoninGatewayV3.withdraw(attacker, amount, [] /* no signers */)`.

## The project's fix

Run `initializeV3` during the upgrade so `totalOperatorWeight` is set and the
real threshold is enforced.

Because the official harness runs a single shared `setup` for both variants, the
fixture reproduces the deployment mistake in `setup` (it calls **only**
`initializeV4`) and encodes the fix as a code-level end-state difference: the
patched `initializeV4` runs the `initializeV3` weight-initialisation. The patch
diff is exactly:

```diff
     function initializeV4() public {
         require(msg.sender == admin, "!admin");
         require(!v4, "v4");
         v4 = true;
+        initializeV3(); // PATCH: the upgrade must also run initializeV3
     }
```

## Harness / capability notes

- The attacker submits a withdrawal with an **empty operator signer set** — a
  legal call. No signatures are forged and no role is impersonated; the exploit
  is purely the zero threshold left by the skipped initialiser.
- Profit flows through the release entrypoint `RoninGatewayV3.withdraw`.
- Replay is deterministic; the patched variant rejects the same trace.
- **Execution is local-fixture** via `scripts/official/empty_rpc.py` (empty
  state) — **not** a mainnet fork; `metadata.fork.block_number` is a placeholder.

## Sources

- Cointelegraph / Verichains — upgrade deployment-script error:
  https://cointelegraph.com/news/ronin-bridge-hack-upgrade-script-verichains
- SolidityScan — Ronin Bridge Hack Analysis:
  https://blog.solidityscan.com/ronin-bridge-hack-analysis-d8f64b8fe683/
- Verichains (X): https://x.com/Verichains/status/1820810424159437261
- SmartContractsHacking — Ronin Bridge Hack (2024) $12.0M:
  https://smartcontractshacking.com/hacks/ronin-bridge-hack-2024

(Verified in-session via web search; direct page fetches were blocked by the
session network policy, so details come from the search-index summaries.)
