# feg_bridge_2024

FEG SmartBridge cross-chain message source-verification bypass (2024-12-29),
Group A (counts toward VER). The authoritative write-up, root cause, attack
chain, the real fix and the patch diff are in
[`official/README.md`](official/README.md); the executable model is in
`official/` (`spec.json`, `vulnerable/`, `patched/`).

- **Oracle:** execution-only asset conservation (official mode).
- **Deterministic proof:** `official_mode::fixture_tests::feg_bridge_2024_official_exploit_and_patch`
  in `src/module3_fuzzing` replays the recorded two-message attack and asserts
  profit on `vulnerable/`, none on `patched/`.
- **Execution:** local-fixture via `scripts/official/empty_rpc.py` (empty chain
  state), **not** a mainnet fork. See `metadata.json`.
- **LLM seeds:** none. `llm_outputs/hypotheses.json` is a non-LLM placeholder
  (`placeholder: true`) that only satisfies the runner's loader; the official
  matrix runs this fixture in `random` seed mode only.
