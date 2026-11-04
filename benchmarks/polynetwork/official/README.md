# Poly Network — official fixture (August 2021)

## Incident

- **Date (UTC):** 2021-08-10
- **Chains:** Ethereum, BSC, Polygon (fixture models one source→dest pair)
- **Loss:** ~$611M (the largest crypto hack at the time; funds returned)
- **Flash loan:** no — **no private key was leaked** (this is an on-chain logic bug)
- **Class:** unrestricted cross-chain call → privilege escalation (V1)

## Root cause (from the post-mortems)

Poly Network's `EthCrossChainManager` (ECCM) executes a cross-chain message by
calling the contract and method named in the message. `verifyHeaderAndExecuteTx`
placed **no restriction** on which contract or method the message could invoke.
Crucially, ECCM is the **owner** of `EthCrossChainData` (ECCD), and ECCD's
`putCurEpochConPubKeyBytes` — which sets the consensus **keeper** — is
owner-only. So a cross-chain message could make ECCM call that setter and
**replace the keeper** (SlowMist; BlockSec). The real attacker brute-forced a
`_method` string (`f1121318093(bytes,bytes,uint64)`) whose 4-byte selector
collides with `putCurEpochConPubKeyBytes(bytes)` (Kudelski).

Why the two steps are both needed:

1. **Replace the keeper.** The honest relay faithfully delivers the attacker's
   crossChain message and reports its **true source sender**. The keeper setter
   is owner-only and ignores the source, so the message succeeds and the keeper
   becomes the attacker's.
2. **Forge an unlock.** `LockProxy.unlock` only pays out for a message whose
   `fromContract` is the **registered source proxy** — which the honest relay
   would never forge. But now that the attacker **is the keeper**, they submit a
   header directly and set `fromContract` to the registered proxy, so the unlock
   passes and the reserve is drained.

### Faulty function

`EthCrossChainManager.verifyHeaderAndExecuteTx` — no restriction on the
message's target contract/method, allowing it to reach the privileged ECCD.

### Attack transactions (modelled)

1. `SourceCrossChain.crossChain(ECCD, "putCurEpochConPubKeyBytes(address,address)", abi.encode(attacker))`
   → relay → `ECCM.verifyHeaderAndExecuteTx(ECCD, …)` → `ECCD.putCurEpochConPubKeyBytes(attacker, …)` → keeper = attacker.
2. `ECCM.verifyHeaderAndExecuteTx(LockProxy, "unlock(address,uint256,address)", abi.encode(attacker, amount), fromContract = registeredProxy)`
   → `LockProxy.unlock(attacker, amount, registeredProxy)` → drain.

## The project's fix

Restrict which contracts/methods a cross-chain message may invoke (Poly added
whitelists for callable contracts and methods). Modelled as forbidding any
message that targets the privileged ECCD:

```diff
         require(msg.sender == eccd.keeper(), "not current keeper");
+        require(toContract != address(eccd), "forbidden target"); // PATCH
         bytes4 sel = bytes4(keccak256(bytes(method)));
```

That is the only functional change; honest unlock messages (which target
`LockProxy`, not ECCD) still execute.

## Modelling notes (fidelity & deviations)

- **Keeper as address.** The real keeper is `bytes` (packed consensus public
  keys); the model represents it by the **address authorised to submit headers**
  so the `msg.sender == keeper` gate can be enforced on-chain. The honest keeper
  is the relayer; after step 1 the keeper is the attacker's address.
- **Function name kept.** `putCurEpochConPubKeyBytes` keeps the incident's name;
  the signature is adapted (`address,address`) because the manager appends the
  message's `fromContract`. Dispatch is by `bytes4(keccak256(method))`, so the
  "message selects the selector" mechanism — and the selector-collision story —
  is preserved. The step-5 deterministic test uses the real function name.
- **Capability compliance.** The attacker uses only legal actions: emitting a
  crossChain message (payload-controlled; the relay stays faithful), and — after
  the protocol *itself* makes them the keeper — submitting a header with their
  own key. No honest keeper signature is forged; the attacker never impersonates
  the honest keeper (that is exactly why step 1 is required).
- **Execution is local-fixture** via `scripts/official/empty_rpc.py` (empty
  state) — **not** a mainnet fork; `metadata.fork.block_number` is a placeholder.

## Sources

- SlowMist — The Root Cause Of Poly Network Being Hacked:
  https://slowmist.medium.com/the-root-cause-of-poly-network-being-hacked-ec2ee1b0c68f
- BlockSec (yajin gist): https://gist.github.com/yajin/0f1a7acfd54adce02422298a1dea8d89
- Kudelski Security — The Poly Network Hack Explained:
  https://kudelskisecurity.com/research/the-poly-network-hack-explained
- Mudit Gupta — Poly Network Hack Analysis:
  https://mudit.blog/poly-network-largest-crypto-hack/

(Verified in-session via web search; direct page fetches were blocked by the
session network policy, so details come from the search-index summaries.)
