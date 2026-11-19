# BridgeSentry Phase 0 Status

Updated 2026-10-31. Branch: codex/phase0-reproducibility. Original source baseline: db20af7703654dd487f6d179070b0e7f664869cc.

## Completed checkpoint

- Read-only audit command: `python scripts/audit_research_inputs.py --output results/phase0`. Can be invoked from another directory with absolute script and --repo-root paths.
- Frozen input hashes and inventory under docs/phase0/2026-10-31: 48 KB object records and 12 benchmark directories. Unique incident count remains unadjudicated; 11 exact-reference overlap groups are review leads, not automatic merges.
- Strict malformed/missing input and duplicate-ID errors. Invalid raw entries retain CSV locations; raw_entry_count and object record_count are explicit. Self-reported ready flags never establish verified execution.
- Output containment resolves input roots, rejects output symlinks and uses atomic per-file replacement. Original KB and benchmark source files are unchanged.
- Fresh Python verification after recovery: 109 passed, 2 skipped, including 16 audit behavior tests. Frozen package versions and raw test output retained. No fresh Rust/EVM campaign claim is made by this checkpoint.
- Nomad source assessment identifies a minimum zero-root patch and unrestricted prove/mint confounders. The pair is not implemented or validated yet.

## Next gate

Build the controlled vulnerable/patched fixture with benign and negative controls, then connect execution-derived evidence. Keep the current official-mode preflight guard until that path is verified. The six-week roadmap retains 14/11 pilot, 30/11 manuscript draft, 10–15/12 conditional submission and 20/12 internal thesis freeze.

## Reproduction and interpretation

Use a fresh Python 3.12 environment with python-offline-freeze.txt, then `python -m pytest -q tests`. Optional Slither tooling accounts for two skipped tests. Full requirements.txt, embedding models, Solidity compiler, Rust runtime and live RPC/LLM settings are not asserted provisioned by this checkpoint; see environment.json.

The inventory source_revision identifies the commit when inputs were generated and includes exact KB, metadata and contract hashes. A successful input audit is not official campaign eligibility, an exploit proof or a generalization result. A1 runtime wiring, paired controls, adjudicated splits, external baseline reproduction and final thesis experiments remain open.
