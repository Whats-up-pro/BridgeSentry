# ItyFuzz single-chain baseline on HPC-UIT (2026-11-20): RQ2 / contribution C2

A representative single-chain EVM fuzzer (ItyFuzz, ISSTA 2023) evaluated on the
seven on-chain fixtures under **the same success criterion as BridgeSentry**
(Definition "valid exploit", condition (v): a net gain of a bridged asset to the
adversary). A single-chain fuzzer cannot execute the cross-chain relay, so the
incidents whose release entry point is gated by the relayer/keeper identity are
out of its reach -- the direct evidence for contribution **C2** (dual-chain +
relay reconstruction).

## Environment

- ItyFuzz: `fuzzland/ityfuzz` commit `80e3b44170573b592cd53b2c5ee9f36b21032b16`,
  release build, binary sha256 `c329a861fb5a6b8cdd56c4239c097d7caba2041b43cbd289c653beb160e47cb7`.
  forge 1.9.0, solc 0.8.20. Built in WSL (glibc 2.39); runs on the compute node
  (`h200node02`, Ubuntu glibc 2.39).
- Slurm: `account=uit`, `partition=normal`, `qos=mig2-35`, 8 CPUs, 16 GB,
  CPU-only (no `--gres`), per `Huong_dan_HPC_dungtrt.pdf`. One job per
  fixture x variant (14 jobs, `itf_*`, `xargs -P 8`), offline `forge build`
  with a cached solc 0.8.20.
- Campaign: 7 fixtures x {vulnerable, patched} x **20 seeds** (ItyFuzz `--seed`
  1042..20042) x **300 s** = 280 runs. Empty chain state (Foundry `setUp`),
  **not** a mainnet fork.
- Invocation per run: `ityfuzz evm -m src/Harness.sol:Harness -f
  --detectors invariant --seed <s> --work-dir <tmp> forge build`.

## Harness and fairness

Each fixture is a Foundry project (`baselines/ityfuzz/harness/<fixture>/{vuln,patched}/`)
whose `Harness.setUp()` deploys both chains' contracts on one clean chain and
reproduces the exact post-setup state of `benchmarks/<fixture>/official/spec.json`
(reserves, initialisers, minters, legitimate pre-deposits/exports). The relayer /
notary / keeper are non-attacker addresses.

- **Oracle = condition (v).** An `Inv` contract deployed in `setUp` carries
  `invariant_bridgeSafe()`, which **reverts** when
  `destToken.totalSupply() - destToken.balanceOf(bridgeHolder) > leaked0`, i.e.
  bridged value left the bridge to the adversary. ItyFuzz's `invariant` detector
  flags the revert. (ItyFuzz's native erc20/flashloan profit oracle needs a
  liquidation pair the fixtures lack, so the custom invariant is what fires.)
- **Threat model.** `Harness.targetSenders()` pins the fuzzer's callers to the
  two attacker EOAs (`0x8EF5…`, `0x35c9…`); the attacker is never the relayer /
  notary / keeper / deployer. `--concolic-caller` is **not** used.
- **Patched variants** are the negative control, exactly as for BridgeSentry.

## Results (detected runs / 20, median time-to-first-exploit)

| Incident | Path (BridgeSentry) | ItyFuzz vuln | median TTE | ItyFuzz patched |
|---|---|---|---|---|
| Ronin bridge (2024) | Destination | **20/20** | < 1 s | 0/20 |
| Nomad | Destination | **20/20** | < 1 s | 0/20 |
| Verus--Ethereum | Relay | **20/20** | 76.5 s | 0/20 |
| CrossCurve | Destination | 0/20 | --- | 0/20 |
| Qubit Finance | Relay | 0/20 | --- | 0/20 |
| FEG SmartBridge | Relay | 0/20 | --- | 0/20 |
| PolyNetwork | Relay | 0/20 | --- | 0/20 |

All 280 runs exited with rc 0 (a bug was found and ItyFuzz stopped) or rc 124
(the 300 s budget expired with no bug -- a censored run); no other rc. The
HPC-written `summary_ityfuzz_{vuln,patched}.csv` were reproduced exactly by
`baselines/ityfuzz/aggregate_ityfuzz.py` on the downloaded results.
**No patched-variant run raised an alert (0/140).**

## Reading (honest)

ItyFuzz reaches an incident when its release/claim entry point can be driven to a
net adversary gain from the post-setup state by an attacker EOA:

1. **Reached (3): Ronin, Nomad, Verus.** Ronin `withdraw` and Nomad
   `processAndRelease` are unpermissioned and their guards are already satisfied
   in the pre-attack state (a zero vote threshold; a pre-confirmed zero root), so
   ItyFuzz drains/mints almost immediately (< 1 s). Verus `submitImports` is
   unpermissioned and over-claims against the *legitimate* committed export that
   the pre-attack state contains; ItyFuzz finds it, but needs a median of 76.5 s
   to supply the right export identifier -- against BridgeSentry's ~1 ms with
   grounded seeds and ~1 s with random seeds (`official_20261118_c3b_hpc`,
   `official_20261114_a1_hpc`). The relay in Verus's path only establishes that
   export during setup; the attacker's own action is destination-direct.
2. **Missed, relay/keeper-gated (3): Qubit, FEG SmartBridge, PolyNetwork.** Their
   release entry points require `msg.sender == relayer` (Qubit `process`, FEG
   `receiveMessage`) or `msg.sender == keeper` (PolyNetwork
   `verifyHeaderAndExecuteTx`). A single-chain fuzzer whose callers are ordinary
   attacker EOAs can never assume the relay/keeper identity, so it cannot deliver
   the cross-chain message that the exploit needs. ItyFuzz *attempted* these
   entry points in every run (31--57% instruction coverage of the gating
   contract) and they reverted on the guard. **This is the structural evidence
   for C2:** BridgeSentry reconstructs all three (Qubit 20/20, Verus 20/20, FEG
   20/20 grounded, PolyNetwork 20/20 grounded) because it executes the relay;
   a single-chain fuzzer cannot.
3. **Missed, structured input (1): CrossCurve.** `expressExecute` is
   unpermissioned and destination-direct, but its payload must be a valid
   `abi.encode(address,uint256)` with the attacker's address and a drainable
   amount, together with `sourceAddress` set to the trusted source portal.
   ItyFuzz's byte-level mutation did not synthesise this structured payload in
   300 s (it reached 57% instruction coverage of `ReceiverAxelar`). This is an
   input-structure limitation, not a relay limitation; BridgeSentry solves
   CrossCurve from its argument vocabulary (ABI-encoded `bytes`).

## Limits of this comparison

One single-chain fuzzer; the fixtures are minimal re-implementations on an empty
chain state; time is granular to 1 s in ItyFuzz's log. The point is the
reached/missed structure under a common criterion, not a millisecond race:
ItyFuzz, a strong single-chain fuzzer, reconstructs 3 of 7 incidents and misses
every incident whose exploit must cross the relay, which is what C2 claims.

## Operational notes

- The **first** campaign (jobs 76073--76086) was **discarded**: ItyFuzz's
  `from_command("forge build")` creates and removes a `.tmp-build-info-<seconds>`
  dir in the project cwd, so 8 seeds of one fixture running in one shared dir
  raced (`src/evm/mod.rs:682` "Failed to build the project", rc=101 on 144/280
  runs, depressing the detected counts). Fixed by running each seed in a private
  `mktemp -d` copy of the project (`run_ityfuzz.sh`, commit `f5e4b73`; the
  redundant pre-build was later dropped, `3e2796a`). The re-run (this record)
  has 0 rc=101.
- `feg_bridge_2024/patched` was re-run alone (job 78391, 1 h limit) because the
  all-censored relay-gated fixtures sit near the 40 min per-job limit and that
  job lost 3 of 20 runs to a TIMEOUT kill on the first re-run.

## Files

- `runs_vuln/`, `runs_patched/`: `<fixture>/<variant>/seed_<n>.{log,result}`
  (result line: `<detected 0|1> <tte_s or -1> rc=<rc>`).
- `summary_ityfuzz_vuln.csv`, `summary_ityfuzz_patched.csv`: HPC-written
  aggregates (reproduced locally).
