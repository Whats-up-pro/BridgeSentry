# C3b seed generation (2026-11-18)

Generation of the 20 grounded seed sets registered in docs/C3b_protocol.md
(commit c952e1f, before any set was generated). Seeds:
`benchmarks/<bench>/official/llm_outputs/gpt-oss-or-grounded/<regime>/`.

## Settings

openai/gpt-oss-120b via OpenRouter, temperature 0.3, top-k 5; retrieval
all-MiniLM-L6-v2 + FAISS (strict, HF offline); audited KB (50 records); regimes
known / exact / temporal / no_rag; `--grounded` with the deploy_log of
`official_20261114_a1_hpc/official_runs/<bench>/vulnerable/random/seed_1042.json`;
up to 2 static repair rounds; `PYTHONHASHSEED=0`, `python -P -s`. Code at
c952e1f; the working tree additionally held scripts/official/compare_campaigns.py
(analysis only, not used by generation). Each set's provenance.json records
what the model was shown and what was withheld, hashes, and per-invariant
repair logs. Ledgers: `c3b_ledger_<bench>.csv`; logs: `logs/`.

## Deviation: first attempt failed (insufficient OpenRouter credit)

The first attempt (2026-11-18 ~11:40 UTC) ran with an OpenRouter account that
had no purchased credit; every LLM call returned HTTP 402, so every set fell
back to templates (llm = 0). The attempt was stopped and none of its outputs is
used; its logs are kept in `attempt1_failed_402/`. A second check (canary) at
11:53 UTC failed the same way and stopped before any other set. After the user
added credit, the run of 12:04-12:52 UTC generated all 20 sets; it began with a
canary set (ronin_2024/known) that was then regenerated in the normal loop, so
the committed ronin_2024/known set is from the loop. No set was regenerated
after its result was seen.

## Outcome (`seed_inspection.txt`)

- 20/20 sets: every scenario produced by the LLM (no template fallback); every
  action compiled against the deployment and ABI. 0 scenarios needed a third
  round; repairs were used mostly on PolyNetwork (6-10 scenarios per set).
- Scenarios that contain the documented exploit mechanism (checked
  mechanically by `inspect_seeds.py`): FEG 66/73, PolyNetwork 8/68,
  Ronin 69/74, CrossCurve 68/68, Verus 9/66. The C3 sets contained none of the
  FEG op-code sequence or the PolyNetwork keeper method.
- Tokens: 2.70 M over the 20 sets (excluding the canary and the failed attempt).
- Local smoke (WSL, not HPC; HPC binary d9cf542e, strict LLM seeds, seed 1042,
  10 s, vulnerable variant): 20/20 runs rc=0, 0 seed fallback, a valid exploit
  in all 20 (`smoke_local/`). This is not a result; the registered campaign
  (20 seeds x 300 s, both variants, HPC) is.
