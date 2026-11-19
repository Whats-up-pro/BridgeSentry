# Phase 0 Research Input Audit Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for the approved roadmap. This checkpoint implements input audit prerequisites, not the later A1 runtime campaign.

**Goal:** Freeze auditable inputs and readiness blockers before the paired pilot.

**Architecture:** Read-only standard-library CLI fingerprints inputs and enumerates malformed or incomplete records explicitly. It preserves unknown incident identity and self-reported readiness, with no conversion to exploit evidence.

**Tech Stack:** Python 3, pytest, JSON/CSV, existing provenance hash helper.

**Spec:** docs/PAPER_REVISION_OPTION_A.md and the approved six-week roadmap.

## Constraints

No changes to corpus/fixture source metadata; no LLM/RPC calls or credential values; no automatic incident merging; official mode stays disabled. Symlink output protection applies to resolved input roots and individual output files. Malformed/unreadable contract entries remain input errors.

## Task 1 Audit command and regressions

- [x] Add behavior tests before implementation and observe missing-command failures.
- [x] Implement build_inventory(repo_root: Path) -> dict and write_inventory(report: dict, output_dir: Path) -> None in scripts/audit_research_inputs.py.
- [x] CLI --repo-root and --output; exit 2 for malformed/missing/duplicate input.
- [x] Preserve object count separately from raw entry count, with invalid CSV locations.
- [x] Exercise ordinary and symlinked input/output boundaries, incomplete fixtures, read errors and secret omission.
- [x] Run focused tests and full primary Python suite.

## Task 2 Frozen checkpoint

- [x] Generate inventory.json, KB/benchmark CSV, reference overlap review and claim ledger.
- [x] Record actual recovery environment, package versions and fresh Python results.
- [x] Assess Nomad root cause and prove/mint confounders without certifying an exploit.
- [x] Record review, recovery boundaries and unresolved next-stage requirements.

## Verification

16 audit tests pass. Full primary Python suite: 109 passed, 2 skipped. Audit succeeds from a different cwd; git diff --check must pass before publication. Rust and full exploit campaign are separate verification work, not substitutes for or implied by this checkpoint.
