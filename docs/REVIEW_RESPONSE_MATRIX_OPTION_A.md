# BridgeSentry Option-A — Reviewer Concern / Evidence Matrix

**Source review:** `BridgeSentry_Q1_Technical_Review.pdf`, 6 Aug 2026  
**Target framing:** leakage-aware semantic-guided cross-chain exploit reconstruction and validation  
**Rule:** a concern is marked resolved only when both manuscript wording and reproducible artifact evidence agree.

| # | Review concern | Severity | Manuscript status | Artifact / experiment status | Current verdict |
|---|---|---:|---|---|---|
| 1 | Full-knowledge RAG leaks the target incident/family/class | Fatal | Option-A Related Work, Methodology and Experiment Protocol define full-KB as diagnostic only and specify incident/family/class+temporal exclusions | Retrieval provenance primitives added; official holdout campaign not run yet | **Open — experiment required** |
| 2 | LLM/ATG/RAG pipeline not reproducibly end-to-end | Fatal | Methodology now describes hybrid parsing, optional LLM enrichment, explicit fallback and provenance | Current orchestrator connects Modules 1→2→3; stable generation/KB hash types added; scenario-level provenance still needs wiring | **Partial** |
| 3 | Invariant formalization / distance oracle inconsistent | Fatal | Option-A problem/methodology use per-transfer/message semantics and violation-oriented distance; timeliness is protocol-specific | Timeliness fallback now gated on explicit timeout+refund semantics; execution-only semantic mapping still incomplete | **Partial** |
| 4 | 12/12 predicate triggers include hollow detections | Fatal | Discussion explicitly treats zero-bytecode/vacuous triggers as hollow and ITR as an intermediate metric | `ExploitEvidenceGates` fail closed; execution-derived action observations and official-oracle input added; official loop not wired yet | **Partial** |
| 5 | Baselines are scientifically non-comparable | Major | Experiment protocol separates native tools, adapted harness modes and project reimplementations; BridgeFuzz is primary dynamic comparison | Common-subset official baseline campaign not run | **Open — experiment required** |
| 6 | Synchronized snapshot contribution unsupported | Major | Sync is demoted to implementation mechanism unless targeted rollback/reorg/finality controls show an effect | No targeted synchronization-specific control set yet | **Resolved as claim; open as optional experiment** |
| 7 | Positive-only saturated benchmark prevents precision/validity estimates | Fatal | RQ3 requires vulnerable, paired-patched, benign and hard-negative groups | Control population not completed | **Open — A2 blocker** |
| 8 | Reconstruction fidelity is heterogeneous / sometimes tautological | Major | Surrogate/scenario-layer/off-chain capability cases are explicitly separated; capability-gated interpretation retained | Per-fixture fidelity/capability manifest still needs official completion | **Partial** |
| 9 | 1.66 s success-only timing is not discovery performance | Major | Legacy timing is labelled fuzzing-only; official protocol requires censored TTVE, CIs and survival analysis | New official campaign not run | **Resolved as claim; open as measurement** |
| 10 | Reproducibility is insufficient | Fatal | Option-A text requires immutable provider/model, prompt, KB, retrieval, fork, seed and control provenance | Result evidence envelope, generation provenance hashes and KB snapshot hash exist; full experiment manifest + raw official runs pending | **Partial** |
| 11 | LLM-generated invariants lack independent ground truth | Major | RQ1 explicitly measures semantic/property fidelity; lifecycle separates generated/schema-valid/admissible/empirically-validated | Current code no longer calls structural filtering empirical validation; labelled invariant corpus not built | **Open — A2/RQ1** |
| 12 | LLM pretraining contamination is unaddressed | Major | Discussion separates RAG leakage from parametric contamination and limits interpretation | Parser-only/non-LLM ablations and model-cutoff control still pending | **Open — experiment required** |

## Evidence already committed

- `src/module3_fuzzing/src/evidence.rs` — legacy/official vocabulary, fail-closed seven-gate exploit evidence, legacy result provenance.
- `src/module3_fuzzing/src/execution_observation.rs` — successful/revert/halt runtime observations; failed executions cannot contribute committed logs/storage evidence.
- `src/module3_fuzzing/src/official_oracle.rs` — execution-only before/after snapshot boundary; deliberately no `Scenario` input.
- `src/module1_semantic/invariant_synth.py` — protocol-specific timeliness gating and explicit candidate-property lifecycle language.
- `src/common/generation_provenance.py` — stable prompt/KB hashes and distinct LLM vs deterministic-fallback provenance.
- `src/module2_rag/knowledge_base.py` — stable loaded-KB snapshot hash.
- `latex/submission/*_option_a.tex` — reviewer-driven scientific rewrite fragments.

## Non-negotiable submission gate

Do **not** call the manuscript submission-ready while `BRIDGESENTRY_EVALUATION_MODE=official` is intentionally rejected. The gate may be opened only after the stock/success path used for primary results no longer derives checker facts from `scenario_sim::global_state_from_scenario`, every required semantic field is mapped from execution/relay observations or marked unknown, and paired-control validity is represented in retained artifacts.

## Next critical path

1. Finish official-oracle base gate semantics and relay-mode exclusion.
2. Build fixture-specific execution→semantic adapters with abstention for unmapped fields.
3. Add fail-closed causal/capability/replay/impact/patched validators.
4. Wire a physically separate official evaluation path; keep legacy reconstruction intact.
5. Only then construct A2 populations and run holdout/control experiments.
