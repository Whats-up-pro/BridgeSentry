# BridgeSentry Option-A manuscript revision

This directory contains the reviewer-driven Option-A rewrite for the ESWA manuscript.

## Scientific positioning

The revision treats BridgeSentry as a **leakage-aware semantic-guided cross-chain exploit reconstruction and validation framework**. It does **not** infer zero-day discovery from the legacy 12/12 invariant-trigger result. Generalization is an empirical research question that requires restricted-knowledge holdouts and fail-closed exploit validation.

## Current authoritative fragments

Apply these fragments to the latest Elsevier CAS manuscript source supplied by the authors:

1. `title_page_option_a.tex`
2. `abstract_option_a.tex`
3. `introduction_option_a.tex`
4. `related_work_option_a.tex`
5. `problem_statement_option_a.tex`
6. `methodology_option_a.tex`
7. `experiments_protocol_option_a.tex`
8. `discussion_conclusion_option_a.tex`
9. `highlights_option_a.tex`

The repository-root historical `latex/paper.tex` is an older IEEE-era draft and is **not** the scientific source of truth for the current submission. Do not copy its legacy claims (for example, broad “vulnerability discovery” language, stale incident counts, or superseded result tables) into the CAS manuscript.

## Claim gates

- **Legacy/full-knowledge reconstruction:** may support historical reconstruction claims only.
- **Incident/family/class/temporal holdout:** required before restricted-knowledge generalization claims.
- **Valid exploit:** requires target bytecode execution, cross-chain causal validity, material state change, capability compliance, replayability, demonstrated impact, and paired patched-version rejection.
- **Synchronized snapshots:** remain an implementation mechanism unless targeted rollback/reorganization/finality controls establish a measurable benefit.
- **Invariant trigger rate / ATG-derived coverage:** internal progress measures, not vulnerability-discovery metrics.

## Code/evidence synchronization rule

Paper text must not outrun the implementation. Whenever a methodological claim changes, the corresponding code path, artifact schema, or experimental protocol must be committed in the same revision stream. Unsupported quantities remain unavailable rather than estimated.

## Current A1 blocker

Official evaluation is intentionally fail-closed while the stock fuzzing loop still derives part of checker state from `scenario_sim::global_state_from_scenario`. `BRIDGESENTRY_EVALUATION_MODE=official` must remain rejected until the oracle consumes execution-derived observations only.
