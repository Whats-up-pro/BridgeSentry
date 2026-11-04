# polynetwork

Poly Network August-2021 unrestricted cross-chain call → keeper replacement →
drain (2021-08-10, ~$611M), Group A (counts toward VER). Root cause, attack
chain, the real fix and the patch diff are in
[`official/README.md`](official/README.md); the executable model is in
`official/`.

- **Oracle:** execution-only asset conservation (official mode).
- **Deterministic proof:** `official_mode::fixture_tests::polynetwork_2021_official_exploit_and_patch`
  (two steps: keeper replacement via the faithful relay, then a forged unlock as
  the new keeper).
- **No private key leaked** — this is an on-chain logic bug (Group A), unlike
  key-compromise incidents (Group B).
- **Execution:** local-fixture via `scripts/official/empty_rpc.py`, not a mainnet fork.
- **LLM seeds:** none; `llm_outputs/hypotheses.json` is a labelled non-LLM placeholder (random-seed mode only).
