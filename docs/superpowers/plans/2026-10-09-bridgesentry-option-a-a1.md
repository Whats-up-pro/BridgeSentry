# BridgeSentry Option A A1 Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make BridgeSentry's official evaluation path fail closed: exploit evidence must be derived from observed execution rather than scenario text, and every official result must carry enough provenance to distinguish real runtime evidence from legacy/synthetic reconstruction.

**Architecture:** Keep `scenario_sim` as a legacy/test-only seed and waypoint helper, but introduce an explicit official-evaluation boundary in Module 3. The official path builds oracle state and exploit-validity evidence from `TxOutcome`, coverage, storage writes, relay runtime state, and fixture-specific observation mappings; any missing observation becomes `unknown/unevaluable`. The Python orchestrator records model/retrieval provenance and rejects official reports that used a synthetic or silent fallback path.

**Tech Stack:** Rust/revm, Python 3, JSON schemas, pytest, cargo test.

**Spec:** `docs/PAPER_REVISION_OPTION_A.md`

## Global Constraints

- Do not use scenario-derived balances, message-verification flags, processed nonces, or success states as official oracle evidence.
- `scenario_sim::global_state_from_scenario` may remain for legacy fixtures/tests but must be unreachable from official evaluation mode.
- Official mode fails closed when a required property is unobservable.
- Reverted/halted transactions do not create committed logs/storage evidence or valid material state change.
- Relay tamper/replay is valid only when fixture capability metadata explicitly permits it.
- Timeliness/refundability is generated/evaluated only for fixtures with explicit timeout and refund semantics.
- LLM/provider/retrieval fallback is never silent in official artifacts.
- Existing legacy results remain historical evidence and are never retroactively relabelled as VER.
- No gold/fixture mutation after viewing official outcomes.

## Review Focus

- **Scenario-induced hollow trigger:** an attack-looking scenario with no successful target-bytecode execution must be ineligible for official exploit evidence.
- **Reverted execution:** a call that touches bytecode but reverts must not satisfy material-state-change or success gates.
- **Missing runtime observation:** an invariant whose required semantic field cannot be observed must return `unknown/unevaluable`, not safe or violated by default.
- **Forbidden relay capability:** replay/tamper requested by a scenario but not authorized in fixture metadata must be rejected before execution and retained as an ineligible attempt.
- **Silent fallback:** parser/LLM/RAG failures that use deterministic templates must be explicitly labelled and must not be aggregated with pinned LLM-guided runs unless the experiment protocol permits that mode.

---

### Task 1: Add explicit evaluation/evidence provenance types

**Files:**
- Modify: `src/module3_fuzzing/src/types.rs`
- Modify: `schemas/results.schema.json`
- Test: inline Rust tests in `src/module3_fuzzing/src/types.rs` plus schema tests under existing schema-validator tests

**Interfaces:**
- Produces: `EvaluationMode`, `EvidenceSource`, `ObservationStatus`, and per-run/per-violation evidence fields consumed by Tasks 2–5.
- Consumes: existing `FuzzingResults`, `Violation`, `TransactionResult`, `GlobalState`.

- [ ] **Step 1: Write failing serialization tests**

Add tests that require an official result to serialize:
- `evaluation_mode = "official" | "legacy"`;
- `oracle_state_source = "execution" | "synthetic_scenario" | "mixed"`;
- `official_eligible: bool`;
- an `ineligibility_reasons: Vec<String>` field;
- per-violation evidence gates for bytecode execution, causal path, material state change, capability compliance, replayability, impact, and patched rejection, each represented as `pass | fail | unknown` rather than bare booleans.

- [ ] **Step 2: Run Rust/schema tests and verify RED**

Run the focused `cargo test`/schema tests used by the repository for `types` and result-schema serialization. Expected: failure because the provenance fields/types do not exist.

- [ ] **Step 3: Implement the minimal provenance types**

Add strongly typed enums/structs in `types.rs`; extend `FuzzingResults`/`Violation` without inventing default `pass` values. Backward compatibility for legacy JSON may use serde defaults that resolve to `legacy`/`unknown`, never `official/pass`.

- [ ] **Step 4: Update `results.schema.json`**

Require the new fields for newly produced official artifacts while preserving a documented legacy compatibility path if existing fixture tests depend on historical JSON.

- [ ] **Step 5: Re-run focused tests and commit**

Commit message: `feat(eval): add explicit evidence provenance`

---

### Task 2: Separate official oracle state from `scenario_sim`

**Files:**
- Modify: `src/module3_fuzzing/src/fuzz_loop.rs`
- Modify: `src/module3_fuzzing/src/scenario_sim.rs`
- Modify: `src/module3_fuzzing/src/config.rs`
- Test: inline tests in `fuzz_loop.rs`/`scenario_sim.rs` or focused integration tests following repository conventions

**Interfaces:**
- Consumes: provenance types from Task 1.
- Produces: explicit `legacy` versus `official` state-construction paths.

- [ ] **Step 1: Write failing hollow-detection tests**

Pin these cases:
1. official mode + no `DualEvm`/real execution => no official violation, `official_eligible=false`;
2. official mode + scenario text that synthetically implies mint-without-lock + zero target basic blocks => no official violation;
3. legacy mode preserves current `scenario_sim` behavior for historical reconstruction tests;
4. official mode never calls `global_state_from_scenario` for oracle state.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: current code fails because `fuzz_loop::run` always creates `global_state_from_scenario` before merging partial on-chain balances.

- [ ] **Step 3: Add an explicit CLI/config evaluation mode**

Add an enum/CLI option such as `--evaluation-mode legacy|official`; default must remain `legacy` until all official observation mappings are implemented, preventing accidental relabelling of old runs.

- [ ] **Step 4: Refactor `fuzz_loop::run`**

Legacy path may continue to use `scenario_sim`. Official path must construct state/evidence exclusively from runtime observation interfaces introduced by Tasks 3–4. If those observations are unavailable, produce `unknown/unevaluable` and mark the finding ineligible rather than synthesizing values.

- [ ] **Step 5: Re-run focused tests and commit**

Commit message: `fix(eval): isolate synthetic scenario state from official oracle`

---

### Task 3: Build execution-derived observation record

**Files:**
- Modify: `src/module3_fuzzing/src/dual_evm.rs`
- Modify: `src/module3_fuzzing/src/storage_tracker.rs`
- Modify: `src/module3_fuzzing/src/fuzz_loop.rs`
- Modify: `src/module3_fuzzing/src/types.rs`
- Test: inline Rust tests for success/revert/log/storage/coverage evidence

**Interfaces:**
- Consumes: `TxOutcome`, `CoverageTracker`, `StorageTracker`, relay snapshot.
- Produces: an execution-derived observation/evidence record used by the checker and exploit validator.

- [ ] **Step 1: Write failing observation tests**

Require the runtime record to distinguish:
- successful call versus revert/halt;
- target address and target bytecode actually executed;
- emitted logs from committed execution only;
- SSTORE writes from committed/successful execution only;
- before/after tracked balances where available;
- source/destination block metadata;
- relay queue/processed state from the real `MockRelay` snapshot.

- [ ] **Step 2: Verify RED**

Current `collect_global_state` only exposes tracked ETH balances, empty storage, and an empty faithful relay placeholder; it is insufficient for official semantic evidence.

- [ ] **Step 3: Reuse composite inspectors instead of duplicating instrumentation**

Generalize the existing `XScopeInspector` pattern so BridgeSentry official mode can collect coverage + storage in one execution pass. Do not infer storage writes from scenario actions.

- [ ] **Step 4: Capture committed execution outcomes in `execute_scenario`**

The trace/evidence record must retain success status, target, logs, storage writes, and coverage for each action. Reverted/halted actions remain traceable but cannot satisfy material-state-change evidence.

- [ ] **Step 5: Re-run focused tests and commit**

Commit message: `feat(eval): derive oracle observations from EVM execution`

---

### Task 4: Add fixture-specific semantic observation mapping and abstention

**Files:**
- Modify: `src/module3_fuzzing/src/config.rs`
- Modify: `src/module3_fuzzing/src/checker.rs`
- Create or modify: a focused semantic-observation module under `src/module3_fuzzing/src/` (name chosen consistently with existing project conventions)
- Modify: benchmark `metadata.json` only where public, deterministic mapping evidence exists
- Test: checker tests for known/unknown observations and protocol-specific accounting

**Interfaces:**
- Consumes: execution observation record from Task 3 plus benchmark metadata.
- Produces: typed semantic observations for locked value, minted/released value, canonical message/transfer identity, verification/consumption state, fees/tolerances, and protocol-specific timeout/refund facts.

- [ ] **Step 1: Write failing checker tests for abstention**

Pin at minimum:
- missing lock/mint mapping => asset conservation `unknown`, not clean/violated;
- missing canonical message binding => authorization `unknown`;
- unrelated deposit cannot authorize a mint;
- fee/rebase/FOT adjustment absent => affected asset class `unknown/excluded`;
- timeliness invariant absent unless fixture explicitly defines timeout + refund semantics.

- [ ] **Step 2: Verify RED**

Current checker reads generic `__locked__`, `__minted__`, `saw_dispatch`, and heuristic zero-root flags; it cannot prove canonical per-message semantics for official mode.

- [ ] **Step 3: Implement typed semantic observation adapters**

Adapters may use fixture metadata to map concrete logs/storage slots/functions into canonical semantic fields. Metadata must identify the public/documented source of each mapping. Unsupported mappings abstain.

- [ ] **Step 4: Split checker behavior by evidence mode**

Legacy checker may retain generic heuristic fields for historical compatibility. Official checker accepts only typed execution-derived observations and returns `unknown` when prerequisites are absent.

- [ ] **Step 5: Re-run focused tests and commit**

Commit message: `fix(oracle): require observed protocol semantics in official mode`

---

### Task 5: Implement fail-closed exploit validator

**Files:**
- Create: `src/module3_fuzzing/src/exploit_validator.rs`
- Modify: `src/module3_fuzzing/src/fuzz_loop.rs`
- Modify: `src/module3_fuzzing/src/types.rs`
- Test: `exploit_validator.rs` inline unit tests and focused integration tests

**Interfaces:**
- Consumes: candidate invariant violation + execution evidence + fixture capability metadata + replay/patched-control result.
- Produces: `ExploitValidation` with the seven Option-A gates and final `valid_exploit` eligibility.

- [ ] **Step 1: Write failing validator truth-table tests**

For each gate, construct a candidate that passes all other gates and set exactly one gate to `fail` or `unknown`; assert `valid_exploit=false`. Assert `valid_exploit=true` only when every required gate is `pass`.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement pure fail-closed validator**

The validator must not rerun or infer missing evidence. It only aggregates explicit gate results.

- [ ] **Step 4: Wire validator into reporting without changing legacy metrics**

Legacy invariant triggers remain available under legacy fields. Official VER is computed only from `valid_exploit=true` findings.

- [ ] **Step 5: Re-run focused tests and commit**

Commit message: `feat(eval): add fail-closed exploit validation`

---

### Task 6: Make relay capabilities enforceable before execution

**Files:**
- Modify: `src/module3_fuzzing/src/config.rs`
- Modify: `src/module3_fuzzing/src/fuzz_loop.rs`
- Modify: `src/module3_fuzzing/src/mock_relay.rs` if needed
- Test: focused Rust tests around unauthorized replay/tamper/delay modes

**Interfaces:**
- Consumes: fixture capability matrix.
- Produces: pre-execution authorization decision plus retained ineligible-attempt reason.

- [ ] **Step 1: Write failing capability tests**

Require replay/tamper to be rejected before relay mutation when not authorized; faithful delivery remains allowed. The result must retain an audit reason instead of silently skipping the action.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement explicit `Authorized(action, capability_matrix)` gate**

Keep fault injection distinct from attacker capability in both runtime data and result JSON.

- [ ] **Step 4: Re-run tests and commit**

Commit message: `fix(threat-model): enforce relay capabilities before execution`

---

### Task 7: Pin LLM/RAG provenance and fallback mode in the Python pipeline

**Files:**
- Modify: `src/common/llm_client.py`
- Modify: `src/module1_semantic/extractor.py`
- Modify: `src/module1_semantic/invariant_synth.py`
- Modify: `src/module2_rag/scenario_gen.py`
- Modify: `src/orchestrator.py`
- Modify: schemas/report/output schemas as required
- Test: existing Python test suite plus new provenance/fallback tests

**Interfaces:**
- Produces: immutable per-run model/prompt/retrieval/fallback provenance consumed by official experiment aggregation.

- [ ] **Step 1: Write failing provenance tests**

Require artifacts to expose:
- provider + resolved model ID;
- prompt/version hash;
- temperature;
- retry count/failure path;
- generation mode (`llm`, `parser_only`, `deterministic_fallback`);
- KB snapshot hash and retrieval regime;
- retrieved incident IDs for every scenario.

- [ ] **Step 2: Verify RED**

Current shared provider resolution can override class-level model names and deterministic fallbacks may occur without an experiment-level eligibility distinction.

- [ ] **Step 3: Implement run manifest/provenance propagation**

Do not remove useful developer fallbacks; make them explicit. Official experiment configuration may choose to fail closed instead of fallback.

- [ ] **Step 4: Re-run Python tests and commit**

Commit message: `feat(provenance): pin LLM retrieval and fallback metadata`

---

### Task 8: Gate protocol-specific invariant synthesis

**Files:**
- Modify: `src/module1_semantic/invariant_synth.py`
- Modify: prompts/schema if required
- Test: Python invariant-synthesis tests

**Interfaces:**
- Consumes: ATG/semantic prerequisites.
- Produces: generated invariants with lifecycle status and explicit abstention reasons.

- [ ] **Step 1: Write failing tests**

Require:
- timeliness omitted when timeout/refund semantics are absent;
- timeliness generated only when both are evidenced;
- fee/rebase/FOT assumptions never default silently;
- lifecycle labels distinguish generated, schema-valid, semantically-admissible, and empirically-validated.

- [ ] **Step 2: Verify RED**

Current deterministic fallback always includes a generic timeliness invariant and `validate(..., normal_traces=[])` is effectively a no-op.

- [ ] **Step 3: Implement prerequisite gating and honest lifecycle status**

- [ ] **Step 4: Re-run tests and commit**

Commit message: `fix(invariants): gate protocol-specific properties`

---

### Task 9: Add official experiment manifest and eligibility gate

**Files:**
- Create/modify: experiment runner under existing `scripts/` conventions
- Modify: `src/orchestrator.py`
- Create: schema for official run manifest if no suitable schema exists
- Test: Python tests for incomplete/complete manifests

**Interfaces:**
- Consumes: provenance from Tasks 1–8.
- Produces: one retained manifest per run plus `official_eligible`.

- [ ] **Step 1: Write failing manifest tests**

An official run is ineligible when any mandatory field from `docs/PAPER_REVISION_OPTION_A.md` §7 is absent.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement manifest generation and strict eligibility check**

- [ ] **Step 4: Re-run tests and commit**

Commit message: `feat(eval): add official run manifest gate`

---

### Task 10: Verification and paper synchronization gate

**Files:**
- No code design change unless verification exposes a defect.
- Update: `docs/PAPER_REVISION_OPTION_A.md` status table only after evidence exists.
- Later update: latest author manuscript synchronized into `latex/paper.tex`.

**Interfaces:**
- Consumes: all A1 tasks.
- Produces: A1 completion evidence and the boundary for A2 benchmark/control construction.

- [ ] **Step 1: Run full Python tests**

Expected: all non-network tests pass.

- [ ] **Step 2: Run full Rust tests**

Expected: all non-network tests pass.

- [ ] **Step 3: Run explicit anti-hollow official-mode smoke**

Expected: attack-looking scenario without successful runtime evidence cannot produce an official valid exploit.

- [ ] **Step 4: Run one execution-backed smoke where runtime evidence is observable**

Expected: result records execution-derived provenance and remains ineligible until every fail-closed gate, including paired patch evidence where required, is supplied.

- [ ] **Step 5: Record A1 completion commit and freeze interfaces before A2**

Do not start official effectiveness experiments during A1.

## Self-review notes

- Spec coverage: runtime-only oracle, fail-closed exploit validity, protocol-specific invariant gating, capability enforcement, provenance, and official eligibility are mapped to tasks.
- Interface consistency: Task 1 defines provenance types; Tasks 2–6 consume them; Task 7 covers Python/LLM provenance; Task 9 aggregates all fields.
- Highest-risk unresolved engineering detail: semantic observation adapters are fixture-specific. Task 4 deliberately requires abstention rather than inventing a universal mapper.
- No task authorizes changing historical gold labels/results after outcomes are observed.
