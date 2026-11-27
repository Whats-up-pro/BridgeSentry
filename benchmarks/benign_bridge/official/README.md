# benign_bridge — correct lock→mint bridge (benign hard-negative)

An **independent benign control**, not a re-implementation of any incident. It
exists to estimate the execution-only oracle's **false-positive rate on code
that is not an exploit**, which the exploit fixtures and their patched variants
cannot do on their own.

## What it is

A minimal but *correct* lock→mint bridge:

- **Source** `LockBridge.deposit(amount, recipient)` pulls `amount` of `SrcToken`
  from the caller with `transferFrom` (a real lock) and emits `Deposit(recipient, amount)`.
- The **faithful relay** delivers `Deposit` to the destination as
  `MintBridge.release(recipient, amount)`, executed by the bridge `relayer`.
- **Destination** `MintBridge.release` is `relayer`-only and pays exactly the
  delivered amount of `DstToken` to the recipient from a pre-funded pool.

There is **no path** that releases or mints value without a matching, funded
deposit, and the adversary is not the relayer, so an adversary holding only
ordinary accounts cannot obtain `DstToken` except by first locking an equal
amount of `SrcToken`. Under the paired assets `[SrcToken, DstToken]` a complete
deposit→release therefore nets to **zero**. `vulnerable == patched` (there is no
flaw to fix).

## Why it is a valid negative control

The oracle flags a trace only when the adversary's committed token transfers
show a **net positive gain in a bridged asset**. This fixture moves real value
across the relay (a legitimate deposit releases `DstToken` to the caller) yet
nets to zero, so a correct oracle must stay silent. The `asset_pairs` grouping
is what nets the source lock against the destination release; the
`spec_unpaired.json` ablation removes it and the same legitimate flow then shows
the release as a positive `DstToken` gain, which demonstrates both that value
genuinely moves and that the cross-chain accounting is what keeps the oracle
from a false alarm.

## How it is run

Local-fixture execution on an empty chain state (`scripts/official/empty_rpc.py`),
not a mainnet fork. Benign variant, `random` and `llm` seed modes:

```
RPC_URL=http://127.0.0.1:$PORT \
scripts/official/run_official.sh benign_bridge vulnerable random <seed> 300
```

`spec_unpaired.json` (via `BRIDGESENTRY_OFFICIAL_SPEC`) is the pairing-removed
ablation used only to show the released value. The `llm` seed is a single
legitimate-operation scenario (`llm_outputs/hypotheses.json`): the caller
deposits and names itself as recipient. It is **not** an exploit.

## Expected result

No alert on the benign variant under adversarial fuzzing (`candidates_total = 0`
across seeds); a positive `DstToken` gain only when the asset pairing is removed.
Results are recorded under `experiments/`.
