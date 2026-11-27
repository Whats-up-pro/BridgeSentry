# Benign hard-negative: correct lock→mint bridge (false-positive rate)

**Date:** 2026-11-27  **Fixture:** `benchmarks/benign_bridge`  **Repo HEAD:** `ba20efe` (main)
**Oracle:** `BRIDGESENTRY_EVALUATION_MODE=official` (`execution_only_asset_conservation`)
**Build:** release `bridgesentry-fuzzer` sha256 `942f28138b9aef1e0653…`, rustc 1.100.0, solc 0.8.39 (pragma `^0.8.20`)
**Execution:** local-fixture on an empty chain state (`scripts/official/empty_rpc.py`), **not** a mainnet fork.

## Purpose

Estimate the execution-only oracle's **false-positive rate on code that is not an
exploit**. The seven incident fixtures and their patched variants show the oracle
stays silent when a documented flaw is *fixed*; they do not show its behaviour on
an **independent** bridge that was never vulnerable. This fixture fills that gap
and closes the paper's limitation "apart from the patched variants, the benchmark
has no benign bridges or hard negatives, so it cannot estimate a false-positive
rate on unrelated code."

## The control

A minimal but **correct** lock→mint bridge (`official/vulnerable/BenignBridge.sol`,
`vulnerable == patched`):

- **Source** `LockBridge.deposit(amount, recipient)` pulls `amount` of `SrcToken`
  from the caller with `transferFrom` (a real lock) and emits `Deposit(recipient, amount)`.
- The **faithful relay** delivers `Deposit` → `MintBridge.release(recipient, amount)`,
  executed by the bridge `relayer`.
- **Destination** `MintBridge.release` is `relayer`-only and pays exactly the
  delivered amount of `DstToken` from a pre-funded pool.

No path releases value without a matching, funded deposit, and the adversary
(`0x…0001`) is not the relayer, so the only way to obtain `DstToken` is to first
lock an equal amount of `SrcToken`. Under the paired assets `[SrcToken, DstToken]`
a complete deposit→release nets to **zero**.

## Results

### Paired (as the bridge is specified) — false-positive rate

| Seed mode | Seeds | Runs with an alert | Iterations (min / median / max) |
| --- | --- | --- | --- |
| random    | 20 (1042–20042) | 0 | 355k / 405k / 549k |
| llm (legit deposit) | 20 (1042–20042) | 0 | 216k / 312k / 451k |
| **Total** | **40** | **0** | **14,607,756 total** |

**FPR = 0/40.** Exact (Clopper–Pearson) 95% confidence interval on the per-run
alert rate: **[0, 8.8%]**. Every run executed the benign bridge for 300 s and
explored 2,106 unique fixture program counters; no run produced a trace with a
net gain for the adversary in a bridged asset.

### Unpaired ablation — the value genuinely moves, and the pairing nets it

`official/spec_unpaired.json` is identical but with `asset_pairs` removed, so
`SrcToken` and `DstToken` count as distinct assets. The same legitimate
deposit→release then reports a positive gain:

| Seed | candidates | gain |
| --- | --- | --- |
| 1042 | 3 | `DstToken` (`0x9b13…8e9b`) = 190e18 |
| 2042 | 3 | `DstToken` (`0x9b13…8e9b`) = 190e18 |

So the destination release genuinely delivers 190 `DstToken` to the caller (the
result is not vacuous), and the **only** reason the paired run nets to zero is the
cross-chain asset pairing that offsets the source lock against the destination
release. A tool that scored a destination mint without pairing it to the source
lock would raise a false alarm here; BridgeSentry's oracle does not.

## Reading

- The oracle does not raise a false alert on an independent correct bridge, over
  40 adversarial campaigns and 14.6M executed traces (FPR 0/40, 95% CI upper
  bound 8.8%). Combined with the patched-variant controls (0/940 across the
  incident fixtures), this is the paper's evidence that an alert is not an
  artifact of the harness.
- The result rests on **one** benign bridge, not a broad sample of production
  bridge code; it estimates a false-positive rate on a correct lock→mint design,
  which is the design class of the on-chain incidents studied.

## Reproduce

```
# per run: start empty_rpc on a free port, point both RPCs at it
RPC_URL=http://127.0.0.1:$PORT \
  scripts/official/run_official.sh benign_bridge vulnerable random <seed> 300
# unpaired ablation:
BRIDGESENTRY_OFFICIAL_SPEC=spec_unpaired.json RPC_URL=http://127.0.0.1:$PORT \
  scripts/official/run_official.sh benign_bridge vulnerable llm <seed> 300
```

`runs/` holds the 42 raw result JSONs and logs; `summary.csv` the per-run table;
`campaign.sh` the exact driver.
