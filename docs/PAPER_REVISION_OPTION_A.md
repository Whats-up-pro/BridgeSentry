# BridgeSentry Paper Revision Contract — Option A

**Date:** 2026-10-09  
**Status:** Accepted by the authors as the binding revision direction  
**Target framing:** leakage-aware semantic-guided cross-chain exploit reconstruction and validation

## 1. Core thesis

BridgeSentry is not evaluated as a zero-day vulnerability-discovery system unless future holdout experiments provide direct evidence for that claim. The paper is positioned as a semantic-guided framework for reconstructing and validating cross-chain exploit traces across explicit source, relay, and destination domains.

Primary framing:

> BridgeSentry translates heterogeneous bridge artifacts into an explicit source–relay–destination semantic representation, uses leakage-controlled historical knowledge to guide execution, and separates intermediate predicate triggers from fail-closed exploit evidence.

Generalization is a research question to be measured, not an assumption.

## 2. Contribution contract

### C1 — Semantic bridge representation (core)

Bridge artifacts are converted into an Atomic Transfer Graph (ATG), canonical transfer/message identities, protocol guards, and candidate invariants that can be compiled into executable security objectives.

Evidence required before strong claims:
- human-labelled semantic subset;
- entity/role precision, recall, and F1;
- ATG edge precision, recall, and F1;
- invariant validity, vacuity, redundancy, and abstention rates;
- parser-only versus LLM-enriched comparison.

### C2 — Leakage-aware guidance (core)

Historical incident knowledge is used under explicit retrieval regimes. Full-knowledge reconstruction is diagnostic only.

Required regimes:
1. full knowledge — diagnostic only;
2. leave-one-incident-out;
3. leave-one-bridge-family-out;
4. leave-vulnerability-class-out plus temporal cutoff.

Primary effectiveness claims must come from regimes 2–4.

### C3 — Fail-closed exploit validation (core)

A trace is counted as valid exploit evidence only when all required conditions are satisfied:

- target bytecode executed;
- valid cross-chain causal sequence;
- material runtime state change;
- actions are within the fixture capability/threat model;
- trace is reproducible;
- concrete security or financial impact is demonstrated;
- the same trace is rejected by the paired patched revision.

A missing condition makes the trace ineligible for Valid Exploit Rate (VER).

### C4 — Dual-EVM + explicit relay harness (supporting)

The dual-EVM harness and relay are enabling infrastructure for C1–C3. They are not claimed as standalone novelty solely because they coordinate two EVM instances.

### C5 — Synchronized snapshots (conditional)

Synchronized snapshots remain a research contribution only if targeted rollback/reorganization/finality experiments show measurable benefit, such as preventing invalid states, reducing false reports, increasing VER, or reaching valid traces missed by independent snapshots. Otherwise synchronization is described as an implementation design choice.

## 3. Research questions

### RQ1 — Semantic fidelity

**Can BridgeSentry recover security-relevant cross-chain semantics and executable invariants from bridge artifacts with sufficient fidelity?**

Primary outcomes:
- entity/role P/R/F1;
- ATG-edge P/R/F1;
- invariant precision;
- vacuity and redundancy rates;
- executable/compilable rate;
- unknown/abstention rate.

### RQ2 — Guidance generalization

**Does semantic and retrieval-based guidance improve valid exploit reconstruction when target-specific historical knowledge is excluded?**

Compare at minimum:
- deterministic/parser-only baseline;
- ATG without historical retrieval;
- ATG + generic scenarios;
- ATG + leakage-controlled RAG.

Primary outcomes: VER, time-to-first-valid-exploit (TTVE), and deduplicated valid trace count.

### RQ3 — Exploit validity and precision

**Do BridgeSentry findings distinguish vulnerable implementations from patched, benign, and hard-negative controls?**

Required populations:
- vulnerable historical targets;
- paired patched counterparts;
- benign implementations;
- hard negatives that resemble vulnerable paths while preserving the security property.

Primary outcomes: VER, patched rejection, false-positive rate, precision, specificity, and unique actionable root causes.

### RQ4 — Component attribution

**Which components materially contribute to valid exploit reconstruction?**

Ablations hold the harness, oracle, target population, budget, and capability matrix fixed. Candidate ablations are `-Semantic`, `-RAG`, `-LLM`, and `-Sync` only when synchronization-specific controls exist.

Invariant-trigger rate alone is not an acceptable primary ablation outcome.

## 4. Runtime evidence rule

Official exploit validation must derive security facts from observed execution state.

Scenario descriptions may be used for:
- seed construction;
- mutation guidance;
- waypoint guidance;
- action selection.

They must not fabricate oracle facts such as observed locked/minted values, message-verification status, processed nonces, successful calls, or runtime balances.

If a required property cannot be observed from EVM state, logs, traces, return status, or relay runtime state, the result is `unknown/unevaluable`, not implicitly satisfied.

Primary official runs must fail closed if synthetic scenario-derived state reaches the exploit validator.

## 5. Invariant lifecycle

Use four distinct statuses:

1. **Generated** — emitted by parser/LLM.
2. **Schema-valid** — fields and types pass structural validation.
3. **Semantically admissible** — required protocol semantics exist and no known protocol rule contradicts the predicate.
4. **Empirically validated** — passes labelled normal traces, violating traces, vacuity tests, and paired patched controls where applicable.

The paper must not call a candidate invariant “validated” before stage 4.

Timeliness/refundability is protocol-specific and is generated only when the fixture provides explicit timeout and refund semantics. Fee, rebasing, fee-on-transfer, and analogous accounting adjustments require protocol-specific deterministic evidence; otherwise the checker abstains.

## 6. Statistical protocol

For stochastic configurations:
- use a pre-specified common seed set;
- keep hardware allocation, timeout, fork, corpus snapshot, model, and decoding configuration fixed across paired comparisons;
- retain all non-trigger and failed runs;
- treat non-triggers as right-censored observations for TTVE;
- report success proportions with confidence intervals, medians/IQR where estimable, survival curves, and effect sizes.

Do not report mean time on successful runs alone as discovery performance.

## 7. Per-run provenance contract

Every official run must retain at least:

- experiment ID and git commit;
- benchmark ID and vulnerable/patched revision;
- source/destination chain and fork block;
- LLM provider, immutable model identifier/date, prompt hash, temperature, seed, retries, and fallback mode;
- knowledge-base hash and retrieval regime;
- retrieved incident IDs;
- fuzzer seed, time budget, hardware allocation;
- oracle/checker version;
- target-bytecode execution evidence;
- causal-path validity;
- capability/fault-injection status;
- material-state-change evidence;
- impact evidence;
- replay result;
- patched-control result.

Missing mandatory provenance makes the run ineligible for primary results.

## 8. Claim hierarchy

### Level 1 — reconstruction

May be claimed when supported by historical reconstruction evidence:

> BridgeSentry reconstructs documented cross-chain exploit behaviours under controlled historical settings.

### Level 2 — generalization under controlled holdout

May be claimed only after clean incident/family/class/temporal holdout experiments.

### Level 3 — unseen vulnerability discovery

May be claimed only with direct unseen-vulnerability evidence. It must not be inferred from historical reconstruction success.

## 9. Manuscript wording constraints

Do not use the following as current headline claims without new evidence:
- “proactively discovers cross-chain bridge vulnerabilities”;
- “zero-day discovery”;
- “detects 12/12 vulnerabilities” when the metric is only invariant trigger;
- “strictly necessary” from the saturated legacy ablation;
- synchronization as a validated contribution when the targeted ablation remains null;
- “rational/economically motivated adversary” unless an explicit utility/economic objective is modelled.

Prefer “threat-model-constrained adversarial action sequence” over “rational adversary” for the current implementation.

## 10. Submission-source synchronization

The repository `latex/paper.tex` currently lags behind the latest author manuscript. Before manuscript edits are committed, the latest author-provided CAS/Elsevier LaTeX source must be synchronized into the repository so that later commits do not reintroduce old discovery claims, stale 51-incident counts, or obsolete baseline results.

All submission-side files (main manuscript, highlights, title page, references, figures/captions) must ultimately use the same claim level and evaluation status.

## 11. Definition of paper-ready

The paper is not submission-ready until the following are green:
- formal invariant consistency;
- execution-derived official oracle;
- end-to-end Modules 1→3 campaign path;
- LLM/fallback provenance;
- incident holdout;
- family/class/temporal holdout;
- patched controls;
- benign/hard-negative controls;
- measured VER;
- scientifically comparable dynamic baseline on a supported common subset;
- pre-specified statistical protocol;
- immutable anonymous reproducibility artifact;
- synchronized claims across all submission files.

A negative or modest result is acceptable; unsupported positive claims are not.