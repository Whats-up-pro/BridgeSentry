"""Read-only inspection of the 20 grounded seed sets (C3b) vs the C3 sets."""
import json, pathlib, collections
R = pathlib.Path("/mnt/d/HK1_2026-2027/NT505/BridgeSentry")
ATT = "0000000000000000000000000000000000000001"
BENCHES = ["ronin_2024", "crosscurve", "verus", "feg_bridge_2024", "polynetwork"]
REGIMES = ["known", "exact", "temporal", "no_rag"]


def words(h):
    h = h[2:] if h.startswith("0x") else h
    return [h[i:i + 64] for i in range(0, len(h), 64)]


def has_mechanism(b, scen):
    acts = scen["actions"]
    if b == "feg_bridge_2024":
        ops = []
        for a in acts:
            if a["contract"] == "WormholeCore" and a["function"].startswith("publishMessage"):
                w = words(a["params"].get("payload", "0x"))
                if len(w) >= 2 and w[1].endswith(ATT):
                    ops.append(int(w[0], 16))
        return 1 in ops and 2 in ops and ops.index(1) < len(ops) - 1 - ops[::-1].index(2) + 0 or (1 in ops and 2 in ops and ops.index(1) < max(i for i, o in enumerate(ops) if o == 2))
    if b == "polynetwork":
        s1 = any(a["contract"] == "SourceCrossChain" and "putCurEpochConPubKeyBytes" in str(a["params"].get("method", "")) for a in acts)
        s2 = any(a["contract"] == "EthCrossChainManager" and "unlock" in str(a["params"].get("method", "")) for a in acts)
        return s1 and s2
    if b == "ronin_2024":
        return any(a["contract"] == "RoninGatewayV3" and a["function"].startswith("withdraw") and a["params"].get("signers") == [] for a in acts)
    if b == "crosscurve":
        return any(a["contract"] == "ReceiverAxelar" and a["function"].startswith("expressExecute") for a in acts)
    if b == "verus":
        exp = [int(a["params"]["amount"]) for a in acts if a["contract"] == "VerusExportSurrogate" and a["function"].startswith("export")]
        sub = [int(a["params"]["payout"]) for a in acts if a["contract"] == "VerusBridge" and a["function"].startswith("submitImports")]
        return bool(exp and sub and max(sub) > min(exp))
    return False


print(f"{'bench':16s} {'regime':9s} scen llm fb  act/res  rounds(1/2/3) outcomes            mech  tok     | C3 res")
tot_tok = 0
for b in BENCHES:
    for r in REGIMES:
        d = R / f"benchmarks/{b}/official/llm_outputs/gpt-oss-or-grounded/{r}"
        prov = json.loads((d / "provenance.json").read_text())
        hyp = json.loads((d / "hypotheses.json").read_text())
        g = prov["grounded"]["per_invariant"]
        rounds = collections.Counter(len(e["rounds"]) for e in g)
        outc = collections.Counter(e.get("outcome") for e in g)
        mech = sum(has_mechanism(b, s) for s in hyp["scenarios"])
        m2 = prov["module2"]
        tok = prov["usage"]["total_tokens"]
        tot_tok += tok
        c3 = json.loads((R / f"benchmarks/{b}/official/llm_outputs/gpt-oss-or/{r}/provenance.json").read_text())["module2"]
        print(f"{b:16s} {r:9s} {m2['n_scenarios']:4d} {m2['n_llm']:3d} {m2['n_fallback']:2d} "
              f"{m2['actions_total']:4d}/{m2['actions_mapped']:<4d} {rounds.get(1,0)}/{rounds.get(2,0)}/{rounds.get(3,0)}        "
              f"{dict(outc)!s:22s} {mech:2d}/{len(hyp['scenarios']):<2d} {tok:7d} | {c3['actions_mapped']}/{c3['actions_total']}")
print("total tokens", tot_tok)
