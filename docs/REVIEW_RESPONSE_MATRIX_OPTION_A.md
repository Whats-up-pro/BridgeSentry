# BridgeSentry Option-A — Reviewer Concern / Evidence Matrix

**Source review:** `BridgeSentry_Q1_Technical_Review.pdf`, 6 Aug 2026  
**Target framing:** leakage-aware semantic-guided cross-chain exploit reconstruction and validation  
**Rule:** a concern is marked resolved only when both manuscript wording and reproducible artifact evidence agree.

| # | Review concern | Severity | Manuscript status | Artifact / experiment status | Current verdict |
|---|---|---:|---|---|---|
| 1 | Full-knowledge RAG leaks the target incident/family/class | Fatal | Option-A Related Work, Methodology and Experiment Protocol define full-KB as diagnostic only and specify incident/family/class+temporal exclusions | Stable prompt/KB/retrieval provenance primitives exist; scenario-level provenance wiring and official holdout campaign still pending | **Open — experiment required** |
| 2 | LLM/ATG/RAG pipeline not reproducibly end-to-end | Fatal | Methodology describes hybrid parsing, optional LLM enrichment, explicit fallback and provenance | Current orchestrator connects Modules 1→2→3; generation/KB hash types are implemented and tested; scenario-level provenance still needs wiring | **Partial** |
| 3 | Invariant formalization / distance oracle inconsistent | Fatal | Option-A problem/methodology use per-transfer/message semantics and violation-oriented distance; timeliness is protocol-specific | Timeliness generation is gated on explicit timeout+refund semantics; official runtime semantic adapter now abstains (`Unknown`) when deterministic mapping is missing/ambiguous; fixture mappings still need population | **Partial — core primitives GREEN** |
| 4 | 12/12 predicate triggers include hollow detections | Fatal | Discussion treats zero-bytecode/vacuous triggers as hollow and ITR as an intermediate metric | Seven fail-closed exploit gates, execution-derived action observations, execution-only oracle input, runtime base-gate derivation and fail-closed evidence aggregation are implemented/tested; official execution loop still not wired | **Partial — validator primitives GREEN** |
| 5 | Baselines are scientifically non-comparable | Major | Experiment protocol separates native tools, adapted harness modes and project reimplementations; BridgeFuzz is primary dynamic comparison | Common-subset official baseline campaign not run | **Open — experiment required** |
| 6 | Synchronized snapshot contribution unsupported | Major | Sync is demoted to implementation mechanism unless targeted rollback/reorg/finality controls show an effect | No targeted synchronization-specific control set yet | **Resolved as claim; open as optional experiment** |
| 7 | Positive-only saturated benchmark prevents precision/validity estimates | Fatal | RQ3 requires vulnerable, paired-patched, benign and hard-negative groups | Control population not completed | **Open — A2 blocker** |
| 8 | Reconstruction fidelity is heterogeneous / sometimes tautological | Major | Surrogate/scenario-layer/off-chain capability cases are explicitly separated; capability-gated interpretation retained | Default-deny relay capability policy exists and is tested; fixture policy loading + per-fixture fidelity manifest still need wiring | **Partial** |
| 9 | 1.66 s success-only timing is not discovery performance | Major | Legacy timing is labelled fuzzing-only; official protocol requires censored TTVE, CIs and survival analysis | New official campaign not run | **Resolved as claim; open as measurement** |
| 10 | Reproducibility is insufficient | Fatal | Option-A text requires immutable provider/model, prompt, KB, retrieval, fork, seed and control provenance | Result evidence envelope, generation provenance hashes and KB snapshot hash exist; full official experiment manifest + raw official runs pending | **Partial** |
| 11 | LLM-generated invariants lack independent ground truth | Major | RQ1 measures semantic/property fidelity; lifecycle separates generated/schema-valid/admissible/empirically-validated | Structural filtering is no longer described as empirical validation; protocol prerequisites fail closed; labelled invariant corpus not built | **Open — A2/RQ1** |
| 12 | LLM pretraining contamination is unaddressed | Major | Discussion separates RAG leakage from parametric contamination and limits interpretation | Parser-only/non-LLM ablations and model-cutoff control still pending | **Open — experiment required** |

## A1 primitives verified by CI

- `src/module3_fuzzing/src/evidence.rs` — legacy/official vocabulary and seven-gate VER eligibility; unknown/failed gates fail closed.
- `src/module3_fuzzing/src/execution_observation.rs` — success/revert/halt runtime observations; failed executions cannot contribute committed logs/storage evidence.
- `src/module3_fuzzing/src/official_oracle.rs` — execution-only before/after runtime boundary; no `Scenario` input; harness relay-mode changes do not count as material impact; only directly observable base gates are populated.
- `src/module3_fuzzing/src/official_semantics.rs` — deterministic runtime semantic locators with explicit abstention for missing, unresolved, or duplicate mappings.
- `src/module3_fuzzing/src/official_validator.rs` — fail-closed aggregation of runtime and supplemental causal/capability/replay/impact/patch evidence; conflicting evidence is fail-dominant.
- `src/module3_fuzzing/src/official_capability.rs` — default-deny policy for delayed/tampered/replayed relay fault injection; faithful mode is the only default capability.
- `src/module1_semantic/invariant_synth.py` — protocol-specific timeliness gating and explicit candidate-property lifecycle language.
- `src/common/generation_provenance.py` — stable prompt/KB hashes and distinct LLM vs deterministic-fallback provenance.
- `src/module2_rag/knowledge_base.py` — stable loaded-KB snapshot hash.

## Paper state

- `latex/paper_option_a.tex` is the integrated Elsevier CAS working draft.
- `latex/submission/*_option_a.tex` are the section-level reviewer-driven source fragments.
- `latex/paper.tex` is a historical IEEE-era draft and is not the current scientific source of truth.

## Non-negotiable submission gate

Do **not** call the manuscript submission-ready while `BRIDGESENTRY_EVALUATION_MODE=official` is intentionally rejected. The gate may be opened only after the primary execution path no longer derives checker facts from `scenario_sim::global_state_from_scenario`, required fixture semantic mappings are supplied or explicitly abstain, relay capability policy is enforced before execution, the remaining causal/replay/impact/patched validators are wired to retained evidence, and official run manifests are complete.

## Next critical path

1. Wire relay capability policy into fixture metadata and reject unauthorized fault injection before execution.
2. Wire generation provenance into every Module 1/2 artifact and add a complete official experiment manifest.
3. Build the physically separate official execution path using `ActionObservation` → `OfficialOracleInput` → runtime semantic adapter → fail-closed validator; keep legacy reconstruction intact.
4. Populate per-fixture semantic maps and paired-control metadata.
5. Only then unlock official mode, construct A2 populations, and run holdout/control experiments.
