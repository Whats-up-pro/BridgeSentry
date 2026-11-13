# PolyNetwork patched-control fix verification (A-0 part 2: fromContract context)

Date 2026-11-13. Binary: local release build `cadd700c4c5aea2c…`. Setup:
`BRIDGESENTRY_EVALUATION_MODE=official`, `empty_rpc.py` (local-fixture, NOT a
mainnet fork), random seeds 1042/2042/3042 × 60 s. (Local WSL run, not HPC.)

## Root cause of the residual patched alert
The destination `EthCrossChainManager` appended the message's `fromContract`
AFTER the caller-controlled `args` (`encodePacked(sel, args, encode(fromContract))`).
An attacker could pad `args` with a forged `fromContract` = the registered proxy;
`LockProxy.unlock` read that forged positional word and ignored the appended true
source, so a message the relayer faithfully carried from the attacker's own
source drained LockProxy on BOTH variants. A-0 part 1 only removed the leaked
drain amount; the hole remained with a generic amount (patched 3/3 alert).

## Change
The manager now exposes the source through `fromContractContext()` (set before
dispatch to the keeper-supplied `fromContract`, cleared after) and calls
`toContract.call(sel, args)` without appending. `LockProxy.unlock(recipient,
amount)` reads the source from `manager.fromContractContext()`, so it cannot be
forged through positional args. Signatures become `unlock(address,uint256)` and
`putCurEpochConPubKeyBytes(address)`. Patched still forbids messages targeting
ECCD (the documented root cause) — the only vulnerable/patched difference.

## Result
| variant | runs | valid-exploit | any-alert |
|---|---|---|---|
| vulnerable | 3 | 0/3 | 0/3 |
| patched    | 3 | 0/3 | 0/3 |

Before (A-0 pt1 only): patched 3/3 alert, vulnerable 2/3 alert (both the
args-injection shortcut). After: patched 0/3 alert (clean control); the spurious
shortcut is gone from the vulnerable variant too, leaving the documented two-step
exploit (replace the keeper, then unlock). That exploit is proven on the
vulnerable variant by the deterministic replay test
`polynetwork_2021_official_exploit_and_patch`; random search does not reach it
within 60 s (median > budget), which is expected for a pre-cutoff two-step attack
and is exactly where LLM-seeded search (C3) is evaluated.
