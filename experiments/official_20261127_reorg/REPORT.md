# A6: source-chain reorganization demonstration

Date: 2026-11-27. Repo HEAD before this work: ba20efe. Oracle official.
Build: release bridgesentry-fuzzer (rustc 1.100.0, solc 0.8.39), local empty-RPC.

## Claim
Synchronized dual-EVM snapshots keep replay faithful; the SAME per-chain snapshot
primitive, used asynchronously (restore_source_only), lets the harness model a
source-chain reorganization that a single global snapshot cannot represent. A
correct lock-mint bridge (benchmarks/benign_bridge) that is safe under synchronized
execution becomes exploitable when a source reorg drops the source-committed
transfers after the destination release.

## Result (benign_bridge, legitimate 190-token transfer)
- transfers_executed: 2 (source lock + destination release).
- synchronized_gains: {}  -- net zero, no alert (the source lock offsets the dest release).
- source_reorged_gains: {asset0:SrcToken+DstToken: 190e18}  -- the destination release is
  left unbacked when the source lock is reorged out: a +190 unbacked gain.

## Mechanism
official_mode gates the demonstration on BRIDGESENTRY_OFFICIAL_REORG=source: it runs the
legitimate transfer once, computes the execution-only ledger over all records (synchronized)
and over the records with source-side transfers dropped (source reorged), and calls
DualEvm::restore_source_only to roll back only the source chain. See
src/module3_fuzzing/src/{dual_evm.rs (restore_source_only/restore_dest_only),
official_mode.rs (gains_from_records, reorg branch)}.

## Reproduce
RPC_URL=http://127.0.0.1:PORT BRIDGESENTRY_OFFICIAL_REORG=source \
  <fuzzer> --metadata benchmarks/benign_bridge/metadata.json ... (see run.sh)
