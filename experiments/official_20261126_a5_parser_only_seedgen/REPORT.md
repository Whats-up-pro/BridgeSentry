# A5 ablation — parser-only Module 1 seed generation

Frozen record; do not edit after commit. A5 isolates the contribution of the LLM to the
**extraction** step (Module 1: the Atomic Transfer Graph and invariants) by replacing it with
the pipeline's no-LLM path (Slither/regex), while keeping Module 2 (scenario generation)
identical to the grounded C3b campaign. This closes the paper's stated open limitation
("a parser-only variant of Module 1 ... has not been run").

## What differs from C3b
- Module 1: `--parser-only` → no LLM; the ATG and invariants come from Slither (or the regex
  fallback), not the model (`generate_seeds.py`, `parser_only=true`).
- Module 2: unchanged — grounded generation with gpt-oss-120b (openai/gpt-oss-120b via
  OpenRouter), regime `no_rag`, the same seed compiler and deploy-logs as C3b.
- Everything else (fixtures, deploy-logs from `official_20261114_a1_hpc`, model, fuzzer binary,
  budget, seed numbers) is held fixed, so the fuzzing comparison isolates Module 1.

Only the `no_rag` regime is generated: it removes retrieval as a variable entirely, so the
comparison is the cleanest possible isolation of Module 1 (parser vs LLM) with Module 2 held
grounded. C3b's grounded `no_rag` seeds (valid exploit in all 20 runs on each of the 5
incidents) and A1's random seeds are the baselines.

## Caveat (honest): Slither compilation on these fixtures
The five fixtures import a shared `_official_common/OfficialToken.sol`, which solc does not
resolve under its default allow-paths when Slither compiles a single fixture file, so Slither
compilation is partial and Module 1 relies on the **regex** extractor. This is the no-LLM
extraction the deployed `--parser-only` mode actually delivers on this benchmark; it is reported
as such rather than worked around, since a wider allow-paths attempt destabilised Slither and the
regex path is itself a legitimate "no-LLM Module 1". The seeds are nonetheless complete and
executable: every action maps to the fixture (see the ledgers).

## Seed sets (model openai/gpt-oss-120b via OpenRouter, regime no_rag, parser_only=true)
| incident | scenarios | all LLM | actions mapped | api_calls | tokens |
|---|---|---|---|---|---|
| ronin_2024 | 3 | 3/3 | 3/3 | 3 | 8,825 |
| crosscurve | 3 | 3/3 | 3/3 | 3 | 12,315 |
| verus | 3 | 3/3 | 4/4 | 3 | 9,481 |
| feg_bridge_2024 | 3 | 3/3 | 6/6 | 3 | 13,239 |
| polynetwork | 3 | 3/3 | 5/5 | 6 | 38,301 |

All 15 scenarios are LLM-produced (0 deterministic fallback) and 100% of actions map to the
fixtures. Seeds written to `benchmarks/<b>/official/llm_outputs/gpt-oss-or-parser-only/no_rag/`
(atg.json, hypotheses.json, provenance.json). Per-incident cost ledgers: `ledger_<b>.csv`.
Generated locally (WSL): Slither 0.11.6, solc 0.8.20, python-docx-free; date 2026-11-26.

## Next
Fuzzing campaign on HPC-UIT (same binary d9cf542…, 20 seeds 1042..20042 × 300 s × {vulnerable,
patched}, empty RPC), `SEED_ALIAS=gpt-oss-or-parser-only`, regime no_rag; compare valid-exploit
rate and TTVE against C3b grounded(no_rag) and A1 random.
