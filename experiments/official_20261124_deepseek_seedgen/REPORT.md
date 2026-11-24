# DeepSeek grounded seed generation (2026-11-24): second model for RQ3

Second model for the leakage-controlled seed protocol (`docs/C3b_protocol.md`),
to close the paper's self-stated "single model" limitation. **Only the model is
changed from C3b; everything else (fixtures, mutator, oracle, fuzzer binary,
retrieval, audited KB, the four regimes, deploy-logs, prompts, repair loop) is
identical.** The fuzzing campaign that consumes these seeds is a separate,
CPU-only HPC run (not yet executed).

## Why DeepSeek (model pivot)

The intended frontier model was OpenAI (gpt-5.5 / gpt-6.1-terra). **Every
grounded exploit-writing call to OpenAI was refused** with HTTP 400 "This
content was flagged for possible cybersecurity risk ... apply for Daybreak
access" — an OpenAI org-policy gate on offensive-security generation, so *no*
OpenAI model works without an approval process. Evidence:
`../official_20261123_gpt61terra_seedgen/BLOCKER_openai_cyberfilter/`
(canary: 0/14 LLM scenarios, all template fallback, 14x the 400 refusal).

GLM and Gemini were considered and rejected for this role: GLM (Zhipu) publishes
no training cutoff (fails the model-selection criterion and undermines the
pre/post-cutoff holdout argument); Gemini carries the same later-cutoff weakness
plus a Google safety-filter refusal risk. **DeepSeek-V3 (`deepseek/deepseek-chat`)**
is frontier-class, permissive (runs the exact registered prompt, 0 refusals),
and lands at a ~July 2024 cutoff -- essentially gpt-oss-120b's (06/2024), so the
two models share the same clean holdout split (ronin_2024, FEG, CrossCurve,
Verus post-cutoff; PolyNetwork pre-cutoff).

## Settings

- Model: `deepseek/deepseek-chat` (DeepSeek-V3) via OpenRouter, temperature 0.3
  (effective: sent as 0.3; not a reasoning model), top-k 5.
- Served through the existing OpenRouter failover path (`generate_seeds.py
  --model gpt-oss-or`, OPENROUTER_* repointed into the NVIDIA slot).
  **Provenance label caveat:** `backend_alias` therefore reads `gpt-oss` and the
  ledger `backend` column reads `gpt-oss`; the authoritative field is
  `provenance.model = deepseek/deepseek-chat` (and the ledger `model` column).
- Retrieval all-MiniLM-L6-v2 + FAISS (strict, HF offline); audited KB (50
  records; fegtoken_20240220 and gempad_20240419 excluded); regimes known /
  exact / temporal / no_rag; `--grounded` with the deploy_log of
  `official_20261114_a1_hpc/official_runs/<bench>/vulnerable/random/seed_1042.json`;
  up to 2 static repair rounds; `PYTHONHASHSEED=0`,
  `BRIDGESENTRY_REQUIRE_SEMANTIC_EMBEDDING=1`, `HF_HUB_OFFLINE=1`.
- Generated locally in the WSL venv `/root/bsvenv` (sentence-transformers 6.3.0,
  torch 2.15.0+cpu, faiss-cpu 1.15.1, numpy 2.5.4, python 3.12.3) -- the same
  environment that generated the C3b gpt-oss sets. Seed generation uses the API;
  it does not run on HPC.
- Canary (ronin_2024/known) was generated and validated first (14/14 LLM, 25/25
  actions, 0 refusals) before the remaining 19 sets; no set was regenerated
  after its result was seen.

## Results (20 sets): llm/scenarios, fallback, actions mapped/total, tokens

| Fixture | Regime | llm/scn | fb | actions | prompt | compl |
|---|---|---|---|---|---|---|
| ronin_2024 | known | 14/14 | 0 | 25/25 | 38122 | 5070 |
| ronin_2024 | exact | 13/13 | 0 | 27/27 | 35425 | 4910 |
| ronin_2024 | temporal | 13/13 | 0 | 25/25 | 34873 | 4833 |
| ronin_2024 | no_rag | 15/15 | 0 | 31/31 | 40759 | 21664 |
| crosscurve | known | 11/11 | 0 | 33/33 | 45108 | 7612 |
| crosscurve | exact | 15/15 | 0 | 44/44 | 68137 | 9721 |
| crosscurve | temporal | 13/14 | 1 | 35/36 | 68196 | 8983 |
| crosscurve | no_rag | 12/12 | 0 | 37/37 | 45819 | 7338 |
| verus | known | 15/15 | 0 | 29/29 | 41702 | 6338 |
| verus | exact | 15/15 | 0 | 33/33 | 41252 | 6525 |
| verus | temporal | 15/15 | 0 | 33/33 | 41455 | 6721 |
| verus | no_rag | 15/15 | 0 | 32/32 | 35450 | 6050 |
| feg_bridge_2024 | known | 14/14 | 0 | 38/38 | 40754 | 6361 |
| feg_bridge_2024 | exact | 12/12 | 0 | 31/31 | 35290 | 5629 |
| feg_bridge_2024 | temporal | 11/11 | 0 | 32/32 | 32514 | 5566 |
| feg_bridge_2024 | no_rag | 10/10 | 0 | 31/31 | 25994 | 4823 |
| polynetwork | known | 14/14 | 0 | 41/41 | 47091 | 7656 |
| polynetwork | exact | 16/16 | 0 | 40/40 | 53891 | 7754 |
| polynetwork | temporal | 14/14 | 0 | 41/41 | 47428 | 7331 |
| polynetwork | no_rag | 13/13 | 0 | 38/38 | 38989 | 6469 |

- **19/20 sets**: every scenario LLM-written, every action compiled against the
  deployment and ABI. **crosscurve/temporal**: 1 of 14 scenarios fell back to a
  template and 1 of 36 actions did not compile -- a legitimate stochastic
  outcome, recorded in provenance, not re-rolled.
- Totals: 373 API calls, 858,249 prompt + 147,354 completion = **1,005,603
  tokens**. **Est. cost $0.375** (deepseek-chat $0.26/M in, $1.03/M out via
  OpenRouter). Ledgers: `ledger_<bench>.csv`.

## Next

HPC fuzzing campaign on these seeds: seeds 1042..20042 (20) x 300 s x
{vulnerable, patched}, strict LLM seeds, empty RPC, partition normal / qos
mig2-35 / 8 CPUs / CPU-only, `SEED_ALIAS=deepseek-grounded` -- identical to the
C3b gpt-oss run, only the seed alias differs. Results to be reported per-model
(never merged with gpt-oss) and compared: DeepSeek grounded vs random (A-1),
and DeepSeek grounded vs gpt-oss grounded (cross-model generalization).
