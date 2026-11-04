# verus

Verus-Ethereum bridge missing source↔payout reconciliation in `checkCCEValues`
(2026-05-18, ~$11.58M), Group A (counts toward VER). Root cause, attack, the
real fix and the patch diff are in [`official/README.md`](official/README.md);
the executable model is in `official/`.

- **Oracle:** execution-only asset conservation (official mode).
- **Deterministic proof:** `official_mode::fixture_tests::verus_2026_official_exploit_and_patch`
  (small honest export, then an over-claimed import).
- **Non-EVM source:** `VerusExportSurrogate` is a surrogate for the Verus side; notary attestation is honest.
- **Execution:** local-fixture via `scripts/official/empty_rpc.py`, not a mainnet fork.
- **LLM seeds:** none; `llm_outputs/hypotheses.json` is a labelled non-LLM placeholder (random-seed mode only).
