# crosscurve

CrossCurve `ReceiverAxelar.expressExecute` cross-chain message validation bypass
(2026-01-31), Group A (counts toward VER). Root cause, attack chain, the real
fix and the patch diff are in [`official/README.md`](official/README.md); the
executable model is in `official/`.

- **Oracle:** execution-only asset conservation (official mode).
- **Deterministic proof:** `official_mode::fixture_tests::crosscurve_2026_official_exploit_and_patch`.
- **Execution:** local-fixture via `scripts/official/empty_rpc.py`, not a mainnet fork.
- **LLM seeds:** none; `llm_outputs/hypotheses.json` is a labelled non-LLM placeholder (random-seed mode only).
