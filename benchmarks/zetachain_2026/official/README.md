# zetachain_2026 — ZetaChain GatewayEVM arbitrary-call drain (held-out incident)

A re-implementation of the ZetaChain GatewayEVM incident of 26 April 2026
(SolidityScan, "ZetaChain Gateway Hack Analysis"), added as a **held-out** test
for grounded seed generation: it was not among the five incidents used to design
grounded generation, and it postdates the training cutoff of both generating
models. The grounded pipeline is used unchanged; see
`docs/heldout_zetachain_protocol.md`.

## Root cause (source → relay → destination)

- **Source (ZetaChain zEVM)** `GatewayZEVM.call` is unauthenticated and copies
  the caller's `isArbitraryCall` flag into the emitted `Called` event.
- **Relay** the protocol validators (TSS) sign a destination transaction from
  that event; the harness models this faithful delivery, executed as the
  relayer identity.
- **Destination (Ethereum)** `GatewayEVM.execute` is callable only by the
  relayer, but its arbitrary-call branch runs attacker-supplied calldata against
  an attacker-chosen target. A token that a victim had approved to the gateway
  is drained by a relayed `transferFrom(victim, attacker, amount)`.

The patched variant removes the arbitrary-call branch: every delivery is routed
through the target's `onCall` interface, so attacker calldata cannot run.

## Reconstruction

The documented exploit is one source action — `GatewayZEVM.call(Token,
transferFrom(victim, attacker, amount), isArbitraryCall = true)` — whose relayed
delivery drains the victim's approved balance on the destination chain. The
deterministic test `zetachain_2026_official_exploit_and_patch` checks that it
satisfies all seven gates on the vulnerable variant and gains nothing on the
patched variant. Local-fixture execution on an empty chain state, not a mainnet
fork.
