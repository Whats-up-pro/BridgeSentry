# CrossCurve patched-control fix verification (A-0 part 2: sourceAddress binding)

Date: 2026-11-13. Binary: local release build, sha256 `cadd700c4c5aea2c…`.
Setup: `BRIDGESENTRY_EVALUATION_MODE=official`, `empty_rpc.py` (local-fixture
execution, NOT a mainnet fork), random seeds 1042/2042/3042 × 60 s.

## Change
CrossCurve `AxelarGateway` now attests the source address of a relayed command
(`approveContractCall(commandId, source)` / `validateContractCall(commandId,
expectedSource)`), and `ReceiverAxelar` stores `trustedSource` (= PortalSrc) and
binds both `execute` and `expressExecute` to `sourceAddress == trustedSource`.
The relay passes `ev:sender`. The only vulnerable/patched difference remains the
gateway `validateContractCall` on the express path.

## Result (after this fix + A-0 part 1 leak removal)
| variant | runs | valid-exploit | any-alert | median TTVE |
|---|---|---|---|---|
| vulnerable | 3 | 3/3 | 3/3 | 0.60 s |
| patched    | 3 | 0/3 | 0/3 | > budget |

Before (`experiments/official_20261106_hard_before_after`): patched **5/5 alert**
(a candidate drained the pre-funded liquidity via the faithfully-relayed,
attacker-sourced message on `execute`). After: patched **0/3 alert** — the
relay-path drain is closed on the patched variant, while random search still
reconstructs the documented express-path exploit on the vulnerable variant in
0.60 s with no leaked amount and no LLM seed. CrossCurve is now a valid
patched-control (C1) fixture.
