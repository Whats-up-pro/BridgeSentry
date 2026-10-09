# A1 Runtime Oracle and Evidence Audit

**Date:** 2026-10-09  
**Scope:** BridgeSentry Option A — runtime/evidence correctness before any new effectiveness experiment  
**Binding spec:** `docs/PAPER_REVISION_OPTION_A.md`  
**Implementation plan:** `docs/superpowers/plans/2026-10-09-bridgesentry-option-a-a1.md`

## Executive finding

The current BridgeSentry fuzzing loop is not yet suitable for an official Valid Exploit Rate (VER) campaign. The main reason is not the invariant-distance equation anymore; it is evidence provenance. The stock BridgeSentry path still constructs oracle-facing semantic state from the intended scenario and then merges only a subset of real EVM observations. Consequently, an attack-looking scenario can contribute `locked`, `minted`, dispatch, or root-acceptance facts even when those facts were not established by successful target execution.

This is consistent with the legacy “hollow detection” behavior already disclosed in the manuscript. The fix is architectural: official evaluation must separate **guidance input** from **observed exploit evidence**.

## 1. Critical finding: scenario text currently creates oracle facts

### File
`src/module3_fuzzing/src/fuzz_loop.rs`

### Current behavior

The stock BridgeSentry loop executes a mutated scenario and then builds:

```rust
let mut state = crate::scenario_sim::global_state_from_scenario(&s_prime);
state.relay_state = relay.to_relay_snapshot();
if let Some(d) = dual.as_mut() {
    let onchain = d.collect_global_state();
    merge_balances(&mut state.source_state.balances, onchain.source_state.balances);
    merge_balances(&mut state.dest_state.balances, onchain.dest_state.balances);
}
```

The checker therefore receives a mixed object:
- scenario-derived semantic balances/flags;
- real relay snapshot;
- a subset of on-chain balances.

There is no type-level provenance boundary distinguishing those sources.

### Consequence

A predicate trigger cannot currently prove that every semantic fact used by the oracle came from executed bytecode or relay runtime state.

### Required ruling

`scenario_sim::global_state_from_scenario` is legacy/test-only for oracle purposes. It may remain useful for seed construction or legacy reconstruction diagnostics, but official evaluation must not feed it into the exploit validator.

---

## 2. Critical finding: `scenario_sim` intentionally synthesizes attack evidence

### File
`src/module3_fuzzing/src/scenario_sim.rs`

### Scenario-derived fields

The module derives at least:
- `__locked__` from source-side action names and parameters;
- `__minted__` from destination-side action names and parameters;
- `saw_dispatch` from recognized operations/relay actions;
- `replica.zero_root_accepted` from message text or attack-looking vulnerability classes.

It also contains an explicit fallback for attack scenarios with no concrete amount:

```text
assume the bug fires for at least one ETH equivalent
```

This is useful as a simulator heuristic, but it is incompatible with fail-closed official exploit evidence.

### Additional construct-validity issue

Waypoint evaluation can treat `step_N_executed` as satisfied when the scenario contains enough actions, independent of whether those actions successfully committed on the target runtime. This is acceptable only as legacy guidance; it is not execution evidence.

### Required ruling

Keep these heuristics behind `legacy`/simulation mode. Official mode uses observed transaction outcomes and runtime-derived semantic adapters only.

---

## 3. Critical finding: current real `GlobalState` is too weak for the paper's semantic invariants

### File
`src/module3_fuzzing/src/dual_evm.rs`

### Current `collect_global_state()`

It collects:
- native ETH balance for tracked addresses on source/destination;
- block number/timestamp;
- empty storage maps;
- an empty, faithful relay placeholder.

It does **not** directly provide:
- ERC-20 locked/minted values;
- canonical transfer/message identity;
- source→relay→destination causal bindings;
- verification status;
- consumed-message state;
- protocol-specific fee/rebase/refund semantics;
- committed per-action success/state-change evidence.

### Required ruling

Do not expand `collect_global_state()` into a universal semantic guesser. Build explicit runtime observation records and fixture-specific semantic mappings. When a property cannot be observed reliably, official evaluation abstains.

---

## 4. High finding: instrumentation needed for the fix already exists

### Files
- `src/module3_fuzzing/src/dual_evm.rs`
- `src/module3_fuzzing/src/storage_tracker.rs`
- `src/module3_fuzzing/src/coverage_tracker.rs`

### Existing reusable pieces

`TxOutcome` already retains:
- success/revert/halt status;
- output;
- committed logs;
- gas used.

`StorageTracker` already records SSTORE activity, and `XScopeInspector` already demonstrates a composite inspector that gathers coverage + storage in one EVM execution pass.

### Implication

A1 does not require replacing revm or building a new trace engine. The shortest correct path is to generalize the existing observation instrumentation to the stock BridgeSentry official mode.

---

## 5. Critical finding: checker semantics are still aggregate/heuristic in stock mode

### File
`src/module3_fuzzing/src/checker.rs`

### Current stock fields

The checker reads generic keys such as:
- `__locked__`;
- `__minted__`;
- `__meta__.saw_dispatch`;
- `replica.zero_root_accepted`.

Asset conservation uses an implicit tolerance:

```rust
let fee_tolerance = locked / 1000 + 1;
```

Authorization can degrade to “mint activity without observed source deposit” or aggregate minted-vs-locked ratio. Uniqueness can also reduce to the same aggregate imbalance.

### Mismatch with revised paper formalization

The latest manuscript correctly defines per-transfer/per-message semantics using canonical key `kappa` and says fee/rebase/FOT adjustments must be protocol-specific. The stock checker has not yet caught up to that formalization.

### Required ruling

Official checker inputs must be typed semantic observations bound to a canonical message/transfer identity. Generic aggregate logic may remain as legacy diagnostics, not as official VER evidence.

---

## 6. High finding: `processed_set` duplicate logic is not a sufficient uniqueness oracle

The stock uniqueness checker searches for duplicate strings in `relay_state.processed_set` and otherwise falls back to economic imbalance. A well-implemented processed set is normally unique by construction; duplicate delivery/consumption must instead be established from execution/relay history tied to the same canonical transfer key.

### Required fix

Track delivery and consumption events/counts explicitly per canonical message key in the observation record. Do not infer replay only from aggregate minting or a Vec duplicate artifact.

---

## 7. High finding: protocol-specific invariant policy and code still diverge

### File
`src/module1_semantic/invariant_synth.py`

The latest paper correctly marks timeliness/refundability as protocol-specific. The deterministic fallback still emits a generic timeliness invariant whenever LLM generation is unavailable.

`validate(invariants, normal_traces=[])` also provides no empirical filtering when the orchestrator supplies an empty normal-trace set.

### Required fix

- gate timeliness on explicit timeout + refund semantics;
- never silently assume fee/rebase/FOT behavior;
- distinguish generated/schema-valid/semantically-admissible/empirically-validated lifecycle states;
- use “validated” in the paper only for the final state.

---

## 8. High finding: LLM model labels in the paper can drift from runtime resolution

### Files
- `src/common/llm_client.py`
- `src/module1_semantic/extractor.py`
- `src/module1_semantic/invariant_synth.py`
- `src/module2_rag/scenario_gen.py`

The shared client resolves provider/model from environment and can override class-level model labels. Generation paths also contain deterministic fallbacks when the LLM is absent or unusable.

### Risk

A manuscript sentence such as “Gemini is used for extraction and GPT-4o for scenario generation” is not scientifically auditable unless the official campaign pins exactly those resolved model IDs and fallback behavior.

### Required fix

Each run records the actual resolved provider/model, prompt hash, decoding parameters, retry/failure path, and generation mode. Official LLM-guided results cannot silently include deterministic fallback runs.

---

## 9. High finding: official versus legacy mode is currently implicit

The repo contains useful legacy reconstruction experiments, baseline reimplementations, replay modes, and simulator-backed tests, but there is no single runtime flag/type that prevents those modes from being mistaken for official fail-closed evidence.

### Required fix

Add explicit `evaluation_mode = legacy | official` plus result-level `official_eligible`. Backward compatibility defaults to `legacy`, never `official`.

---

## 10. Paper implications now, before new experiments

The following statements are defensible in the manuscript now:
- 12/12 is a legacy, target-aware invariant-trigger result;
- 11/12 bytecode-backed triggers exclude the zero-block GemPad case but are not yet VER;
- the benchmark is saturated for invariant-trigger rate;
- synchronization has no measured benefit in the current legacy experiment;
- holdout/patch/benign results are unavailable.

The following must remain out of headline claims until A1/A2/A3 complete:
- vulnerability-discovery rate;
- zero-day capability;
- validated exploit rate;
- precision/specificity;
- time-to-exploit as an end-to-end metric;
- causal attribution to individual modules;
- synchronization benefit.

## 11. A1 exit criteria

A1 is complete only when all are true:

1. Official oracle path cannot call scenario-derived semantic state.
2. Successful/reverted/halted actions are distinguishable in retained evidence.
3. Target-bytecode execution is retained per finding.
4. Storage/log/relay observations are available to semantic adapters.
5. Missing semantic observations yield `unknown`, not guessed values.
6. Canonical message/transfer binding is supported where a fixture is eligible.
7. Relay fault injection is capability-gated before execution.
8. Fail-closed exploit validator exposes all required gates.
9. LLM/RAG/fallback provenance is explicit.
10. Legacy results retain their historical labels and are not upgraded retroactively.

## 12. Priority order

**P0:** official/legacy mode boundary → execution-derived observation record → fail-closed exploit validator.  
**P1:** canonical semantic adapters + invariant prerequisite gating.  
**P1:** LLM/retrieval/fallback provenance.  
**P2:** synchronization-specific controls; only needed if synchronization remains a research contribution.
