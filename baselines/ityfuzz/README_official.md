# ItyFuzz baseline (official) — RQ2 / contribution C2

Single-chain fuzzer baseline for the execution-only evaluation. Shows what a
representative single-chain fuzzer (ItyFuzz, ISSTA 2023) achieves on the seven
on-chain fixtures under the **same success criterion** as BridgeSentry
(Definition "valid exploit", condition (v): a net adversary gain of a bridged
asset). A single-chain fuzzer cannot execute the relay, so the incidents whose
release entry point is gated by the relayer/keeper are out of its reach — the
direct evidence for C2 (dual-chain + relay reconstruction).

> The sibling files `INSTALL.md`, `adapter.sh`, `version.txt` and the
> `baselines/README.md` table are the **legacy 2026-04 effort** (onchain fork +
> Etherscan, 12 benchmarks, the withdrawn trigger-rate oracle). Do **not** use
> `adapter.sh`. This file is the current, execution-only approach.

## How it works

Each fixture is a Foundry project under `harness/<fixture>/{vuln,patched}/`:
`src/` holds the fixture's own contracts (vulnerable or patched) with the shared
`OfficialToken` flattened in, plus a `Harness.sol` that:

- `setUp()` deploys both chains' contracts on one clean chain and reproduces the
  exact pre-attack state of `benchmarks/<fixture>/official/spec.json` (reserves,
  initialisers, minters, legitimate pre-deposits/exports). The relayer / notary /
  keeper are set to a non-attacker address;
- `Inv` (deployed in `setUp`) carries the oracle
  `invariant_bridgeSafe()`, which **reverts** when
  `destToken.totalSupply() - destToken.balanceOf(bridgeHolder) > leaked0`, i.e.
  bridged value left the bridge (= condition (v)); ItyFuzz's `invariant` detector
  flags the revert;
- `targetSenders()` pins the fuzzer's callers to the two attacker EOAs
  (`0x8EF5…`, `0x35c9…`), so the "attacker" is never the relayer / notary /
  keeper / deployer (the threat model of Definition "capability matrix").
  `--concolic-caller` is **not** used.

Run: `ityfuzz evm -m src/Harness.sol:Harness -f --detectors invariant forge build`
(offline on the cluster: `forge build --offline` with a cached solc 0.8.20; the
erc20/flashloan oracle `-f` is on but the fixtures have no liquidation pair, so
the custom invariant is what fires).

## Files

- `harness/<fixture>/{vuln,patched}/` — the 7 fixtures × 2 variants (Foundry projects).
- `run_ityfuzz.sh` — one run: `<harness_dir> <variant> <seed> <budget_s> <out_dir>`.
- `aggregate_ityfuzz.py` — `seed_*.result` → per fixture×variant CSV (detected/N, median TTE).
- `../../scripts/official/job_ityfuzz.sh` — HPC CPU job (per `Huong_dan_HPC_dungtrt.pdf`):
  one VARIANT, 7 fixtures × 20 seeds × 300 s, `xargs -P 8`.

## Build

ItyFuzz builds with `cargo build --release` (z3 is a hard dep, `static-link-z3`;
needs cmake + clang/libclang; toolchain `nightly-2024-01-01`). Pin the commit.
For the cluster the binary must run on the compute node: verify its glibc, or
build a portable binary (older-glibc container) — see the campaign REPORT.

## Provisional local check (single run; not the campaign)

vuln DETECTED: Ronin 2024, Nomad, Verus (destination release callable from the
post-setup state). vuln none: Qubit, FEG SmartBridge, PolyNetwork (release gated
by `msg.sender == relayer/keeper`; ItyFuzz attempted the call and it reverted)
and CrossCurve (destination-direct but needs a structured ABI-encoded express
payload that byte-level mutation did not produce). All patched variants: none.
The registered campaign is 20 seeds × 300 s × {vuln, patched} on the cluster.
