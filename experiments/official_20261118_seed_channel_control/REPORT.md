# Seed-channel positive control (2026-11-18, LOCAL WSL run, not HPC)

Purpose: show that the grounded seed channel (src/module2_rag/seed_compiler.py)
carries a correct exploit to the unchanged fuzzer, before any grounded LLM seed
is generated (docs/C3b_protocol.md).

- Input: each fixture's documented exploit, transcribed from the deterministic
  Rust tests (tests/data/seed_channel_positive_control.json), compiled by
  scripts/official/seed_channel_control.py into compiled_seeds/<bench>/hypotheses.json
  (ATG: the fixture's existing llm_outputs/atg.json, which the oracle does not read).
- Fuzzer: musl binary sha256 d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848
  (the HPC binary of A-1 and C3); official mode, strict LLM seeds, seed 1042,
  10 s per run, empty RPC (local fixtures, not a mainnet fork); WSL Ubuntu 24.04.
- Result (summary_official.csv): every vulnerable variant had a valid exploit at
  the first execution of the seed (first_valid_exploit_s 0.0004-0.0024 s), with
  all actions resolved; every patched variant had no alert; 14/14 runs rc=0.

These seeds are a test artifact; they are never used in a campaign or shown to
an LLM.
