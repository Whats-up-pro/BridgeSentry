# ronin_2024

Ronin bridge August-2024 skipped-initializer withdrawal bypass (2024-08-06),
Group A (counts toward VER). Root cause, attack, the real fix and the patch diff
are in [`official/README.md`](official/README.md); the executable model is in
`official/`.

- **Oracle:** execution-only asset conservation (official mode).
- **Deterministic proof:** `official_mode::fixture_tests::ronin_2024_official_exploit_and_patch`.
- **Not** the March-2022 Ronin key-compromise incident (that is Group B).
- **Execution:** local-fixture via `scripts/official/empty_rpc.py`, not a mainnet fork.
- **LLM seeds:** none; `llm_outputs/hypotheses.json` is a labelled non-LLM placeholder (random-seed mode only).
