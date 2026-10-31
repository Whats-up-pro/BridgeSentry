# Phase 0 Recovery and Review Record

The local checkout and patch from the prior turn were unavailable when publication was authorized. This branch restores the intended Phase 0 behavior from source baseline db20af7703654dd487f6d179070b0e7f664869cc and regenerates the input reports. New commit hashes intentionally identify this recovered version. Missing prior Rust logs and Cargo.lock were not reconstructed or presented as fresh measurements.

The restored audit and its initial 11 regressions passed the full Python suite (104 passed, 2 skipped). A fresh read-only reviewer reproduced an output-containment bypass through symlinked input roots, unhandled malformed/unreadable contract and metadata fingerprints, and ambiguous omission of nonobject raw entries. Five regression tests were observed failing before a single fix pass. After fixes, 16 focused audit tests and the full 109-test Python suite passed; 2 optional-tooling tests remain skipped.

Fixes resolve protected input roots, reject symlink output directories/files, preserve invalid raw-entry rows/counts, and report fingerprint/contract errors without aborting inventory. Per-file atomic output replacement and LF CSV are retained. The fixes were verified by regression and full-suite runs; no second review round was requested.

Scope rulings: object-record count is separate from raw-entry count, and unique incident identity stays unadjudicated. No full-report transactional/concurrent-filesystem guarantee is asserted. Actual exploit validity, live-RPC behavior, A1 wiring and effectiveness are next-stage work. Current verification does not certify fresh Rust dependency/toolchain reproducibility. Costs of these boundaries are possible platform setup work, manual incident adjudication and pilot schedule revision before campaign.

The user explicitly authorized pushing codex/phase0-reproducibility and creating a draft PR. Main is not merged by this checkpoint.
