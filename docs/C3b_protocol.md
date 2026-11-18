# C3b protocol: grounded LLM seeds (registered before seed generation)

Registered 2026-11-18, in the same commit as the code it evaluates and before
any grounded seed set is generated. Results will be reported whatever they show,
next to the earlier C3 configuration.

## Why C3b exists, and the caveat that follows

C3 (`experiments/official_20261115_c3_hpc/`) found no benefit of gpt-oss-120b
seeds over random seeds on the two fixtures that random seeds do not solve
quickly (FEG SmartBridge, PolyNetwork). Read-only analysis afterwards showed
that the C3 seed channel lost most of what the model wrote:

- the model saw no source, ABI or deployment, so it invented contract and
  function names (34-73% of actions unresolvable);
- the harness fills parameters by ABI name and accepts `bytes` only as hex, so
  structured payloads became empty bytes;
- in C3, Module 1 read the raw fixture sources, whose comments describe the root
  cause (`// VULNERABLE: ...`), and the old system prompt named past incidents.
  Neither helped the seeds, but both are leakage channels that C3 did not control.

C3b changes only seed generation (Python). It was designed **after** observing
C3 on the same five fixtures, so it is not a held-out test of the design; no
other fixture is available to hold out. To limit tuning to these fixtures, every
change is general (nothing in prompts, compiler or protocol names a fixture or
an exploit), the protocol is registered here first, and all five fixtures and
both configurations are reported.

## Method under test (code in this commit)

- `src/module2_rag/grounding.py`: the model sees the comment-free sources, the
  compiled ABI, the deployment, the relay rule and the pre-attack transactions
  of a fixture. Withheld: `spec.notes`, `release_entrypoints`, `victims`, the
  patched variant, README files, tests, directory names. Module 1 reads the
  comment-free copies as well.
- `src/module2_rag/prompts/system_adversary_grounded.txt`: typed actions
  (deployed instance, exact signature, positional args, structured `bytes`);
  names no incident.
- `src/module2_rag/seed_compiler.py`: validates actions against the deployment
  and ABI and ABI-encodes structured `bytes` with the deployed addresses; at most
  2 repair rounds that return only these static messages to the model. No
  execution, coverage or oracle feedback reaches the model.
- Unchanged: fixtures, mutator, oracle, fuzzer binary (musl, sha256
  `d9cf542ecf64263565833788d9bd1c7e8936de635e9c5377580dd7011aeba848`), job
  script logic, retrieval (all-MiniLM-L6-v2 + FAISS, strict), audited KB (50),
  the four regimes, model (openai/gpt-oss-120b via OpenRouter, temperature 0.3,
  top-k 5).
- Positive control (passed before registration, local WSL run): each fixture's
  documented exploit, compiled by `seed_compiler.py`, yields a valid exploit at
  the first execution on all seven vulnerable variants and no alert on the
  patched variants (`scripts/official/seed_channel_control.py`).

## Design

- Fixtures: ronin_2024, crosscurve, verus, feg_bridge_2024 (after the model's
  stated 06/2024 cutoff) and polynetwork (2021, before it), as in C3.
- Regimes: known, exact, temporal, no_rag; one seed set per fixture x regime,
  generated once, `benchmarks/<b>/official/llm_outputs/gpt-oss-or-grounded/<regime>/`.
- Runs: 20 fuzzing seeds (1042..20042) x 300 s x {vulnerable, patched}; strict
  LLM seeds; empty RPC; HPC-UIT partition normal, qos mig2-35, 8 CPUs, CPU-only.
- Baselines (existing, same binary, seeds and budget): random seeds
  `official_20261114_a1_hpc`; ungrounded LLM seeds `official_20261115_c3_hpc`.

## Hypotheses and analysis (fixed now)

- H1: grounded seeds reach a valid exploit sooner than random seeds on FEG
  SmartBridge and PolyNetwork.
- H2: the `known` regime is not better than `exact`, `temporal` or `no_rag`.
- Primary outcome: time to first valid exploit (fuzzing only), runs without one
  censored at 300 s; log-rank test. Secondary: valid-exploit runs out of 20,
  Fisher exact test. 95% Clopper-Pearson intervals for rates.
- Families, each Holm-corrected at 0.05:
  (F1) grounded(regime) vs random, 5 fixtures x 4 regimes = 20 comparisons;
  (F2) grounded(regime) vs ungrounded C3 (same regime), 20 comparisons;
  (F3) exact/temporal/no_rag vs known within grounded, 15 comparisons.
- Patched variants: every alert is a false alarm; reported as alert runs / 400.
- Cost: generation tokens, USD and wall-clock (including repair rounds) per seed
  set, and an end-to-end time = generation time + TTVE, reported next to the
  fuzzing-only TTVE.
- Seed-channel diagnostics: actions written vs resolved, repair rounds used,
  scenarios that fell back to templates.

## Stopping rule and deviations

One campaign. A run is repeated only for an infrastructure failure (non-zero rc
or missing result JSON), and then every condition of that job is rerun. Any
deviation from this protocol is recorded in the campaign REPORT.md with its
reason. If H1 fails, the negative result is reported; execution feedback to the
model (a further method change) would be a separate, newly registered campaign.
