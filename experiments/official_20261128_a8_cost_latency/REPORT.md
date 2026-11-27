# A8: cost, latency, and seed-compiler failure rate of seed generation

Frozen analysis record, 2026-11-28. **No new LLM call and no new fuzzing run.** Every
number is computed from committed artifacts by `a8_aggregate.py` and `a8_repairs.py`:

- ledgers: `experiments/official_20261118_c3b_seedgen/c3b_ledger_*.csv`,
  `experiments/official_20261124_deepseek_seedgen/ledger_*.csv`,
  `experiments/official_20261126_a5_parser_only_seedgen/ledger_*.csv`
  (per seed set: API calls, prompt/completion tokens, Module 1 and Module 2 latency,
  actions generated and mapped, fallback scenarios);
- `benchmarks/<b>/official/llm_outputs/<alias>/<regime>/provenance.json`
  (per invariant prompt: repair rounds, compile errors, outcome; for the ungrounded C3
  sets, which predate the ledgers, token usage only).

Cost is an **estimate at list price**, not a billed amount: OpenRouter public prices
fetched 2026-11-28 from `https://openrouter.ai/api/v1/models` —
`openai/gpt-oss-120b` $0.05/M input, $0.25/M output; `deepseek/deepseek-chat`
$0.2574/M input, $1.0287/M output (the DeepSeek price matches the one recorded in
`official_20261124_deepseek_seedgen/REPORT.md`, whose $0.375 estimate this reproduces).
Latency is wall-clock on the developer workstation calling the remote service, so it
includes network time.

## Result (`a8_cost_latency.csv`)

| Seed configuration | Sets | API calls | Tokens in / out | Tokens per set | Est. cost (USD) | Module 1 / Module 2 latency, median per set | End-to-end per set, median (max) | Actions mapped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ungrounded gpt-oss-120b (C3) | 20 | 370 | 945,161 / 305,098 | 62,513 | 0.12 | not recorded | not recorded | (fuzzer-side: 547/1,127, RQ3) |
| Grounded gpt-oss-120b (C3b) | 20 | 481 | 1,141,429 / 1,554,572 | 134,800 | 0.45 | 35.5 s / 200.5 s | 239.6 s (1,423.3 s) | 529 / 529 |
| Grounded DeepSeek-V3 | 20 | 373 | 858,249 / 147,354 | 50,280 | 0.37 | 61.7 s / 102.8 s | 173.1 s (759.0 s) | 676 / 677 |
| Grounded, parser-only Module 1 (A5, no retrieval) | 5 | 18 | 44,151 / 38,010 | 16,432 | 0.01 | 1.1 s / 31.6 s | 32.7 s (106.0 s) | 21 / 21 |

All seed generation behind the paper's LLM results costs about **US$0.95 at list price**
(the first C3b attempt, rejected by the service for insufficient credit, generated nothing).

## Seed-compiler failures and repair (grounded configurations)

| Configuration | Invariant prompts | Needed a repair round | First-round error | Not fully compiled |
| --- | --- | --- | --- | --- |
| gpt-oss-120b (C3b) | 349 | 48 (one round each) | 47 format (43 empty `actions` array, 4 not a single JSON object), 1 argument type | 0 |
| DeepSeek-V3 | 271 | 10 (2 one round, 8 two rounds) | mostly ABI shape (unnamed parameters of `callContract`, `bytes32` not hex), 1 format | 6 (5 partially compiled, 1 unusable) |
| parser-only (A5) | 15 | 3 (one round) | 3 format (empty `actions` array) | 0 |

Among the actions emitted in the first round, 99.8% (gpt-oss-120b), 98.2% (DeepSeek-V3)
and 100% (parser-only) compiled. The repair messages are static compiler errors; no
execution, coverage, or oracle result reaches the model.

## Reading

- A grounded seed set costs about two US cents at list price with either model
  (US$0.022 per set with gpt-oss-120b, US$0.019 with DeepSeek-V3), and takes a median of 3–4 minutes end to end, almost all
  of it in Module 2 generation; the parser-only Module 1 cuts extraction from about 36 s to
  1 s.
- The fuzzing budget per run (300 s) is of the same order as generating one seed set, and a
  seed set is reused for all 20 fuzzing seeds and both variants.
- gpt-oss-120b's first-attempt failures are format failures, which one static repair round
  fixes in every case; DeepSeek-V3's are ABI-shape errors, of which 6 of 271 remain
  uncompiled after two rounds.
