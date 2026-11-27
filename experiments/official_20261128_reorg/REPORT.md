# A6: source-chain reorganization demonstration (re-run with full provenance)

Frozen record, 2026-11-28. **Supersedes `official_20261127_reorg/`**, which was run
with solc 0.8.39 (the local `solc-select` default, not the pinned 0.8.20) and does not
record the binary hash. Same mechanism, same result.

## Provenance (`run_info.txt`)

- Commit `9c21535bff41bf14efeaee1da6e889a9103793ee` (clean `src/`).
- Fuzzer: `cargo build --release`, rustc 1.100.0, sha256
  `89fdbeb9517e73da444c2316cd5686c1a8b6f92eeba3e557bdefae9134868204`.
- solc 0.8.20 static, sha256 `0479d44fdf9c501c25337fdc540419f1593b884a87b47f023da4f1c700fda782`
  (the same binary as `bin/solc` on the UIT cluster).
- Host: developer workstation, WSL2, 16 vCPU. Empty RPC (`scripts/official/empty_rpc.py`),
  local fixtures, not a mainnet fork.

## Evidence

1. **Deterministic test** (`cargo_test.log`, exit 0; 196 + 177 passed, 0 failed):
   `benign_bridge_source_reorg_leaves_release_unbacked` asserts that
   - the synchronized ledger of a legitimate 190-token transfer is empty;
   - the ledger with the source-committed transfers dropped is 190e18;
   - after `DualEvm::restore_source_only(base)` the caller can again move all
     1000 SrcToken (the lock is undone) **and** can move the 190 DstToken released
     on the destination (the release survives);
   - after the global `restore_snapshot(base)` the 190 DstToken are gone.
2. **Runs** (`BRIDGESENTRY_OFFICIAL_REORG=source`, seeds 1042/2042/3042; the branch
   executes the first corpus sequence once and returns, so the seed does not matter):

| Seed | transfers executed | synchronized gains | source-reorged gains |
| --- | --- | --- | --- |
| 1042 | 2 | {} | asset0:SrcToken+DstToken = 190e18 |
| 2042 | 2 | {} | asset0:SrcToken+DstToken = 190e18 |
| 3042 | 2 | {} | asset0:SrcToken+DstToken = 190e18 |

## Claim and its limit

A correct lock-mint bridge (`benchmarks/benign_bridge`) that raises no alert under
synchronized execution leaves an unbacked destination release once a source-chain
reorganization drops the source-committed transfers. The per-chain snapshot primitive
expresses that state; a single global snapshot cannot. This demonstrates the mechanism
on a benign bridge. It is not a reorg-driven exploit of a documented incident.

## Files

`run_info.txt`, `build.log`, `cargo_test.log`, `cargo_test.rc`, `run.sh`,
`reorg_benign_bridge_s{1042,2042,3042}.{json,log}`.
