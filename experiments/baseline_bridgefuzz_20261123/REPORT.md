# Baseline run — BridgeFuzz (EuroSec 2026), public Zenodo artifact

Frozen record. We stood up BridgeFuzz's public artifact (doi 10.5281/zenodo.17093557,
Winkler et al., EuroSec 2026) and ran its random fuzzer, to characterise its oracle
under our evaluation lens. This is a run of BridgeFuzz on **its own prototype bridge**,
not a same-fixture head-to-head on our incidents (see Caveat).

## Environment & reproducibility fixes (the artifact does not run out of the box)

- Host: WSL Ubuntu-24.04, Docker Desktop (engine 28.4.0, compose v2.39.2), Bun 1.4.5,
  solc 0.8.20. Date 2026-11-23.
- `Start_compose.sh` builds 4 images (geth `ethereum/client-go:v1.13.14` x2, a 3-node
  Python Raft sidechain, a Node.js relayer) and brings up 7 containers (2 geth devnets,
  3 sidechain nodes, 2 relayers) + a Postgres `eval-db`.
- Fixes applied to make it run:
  1. `docker compose up` failed: `off_chain_network` (172.18.0.0/24) overlapped a
     dormant leftover network `deployments_default` (172.18.0.0/16). Removed the
     leftover (0 containers) and retried.
  2. Relayers crashed on missing `/smart_contracts/Router.abi` and `/SYSSEC.abi`
     (mounted from `smart_contracts/data`, which ships empty). Compiled
     `smart_contracts/contracts/Router.sol` with solc 0.8.20 (from the `contracts/`
     dir, since imports are bare) -> `Router.abi`/`.bin`; the relayer's token "SYSSEC"
     is the `SToken` contract, so `cp SToken.abi SYSSEC.abi`.
  3. The fuzzer and db modules ship as `.js` but are `require()`d as `.cjs` under
     `"type":"module"`: `cp e2e.js e2e.cjs` and `cp db/db.js db/db.cjs`.
  4. ABI read path `../../../smart_contracts/data/...` assumed a different nesting
     (the Zenodo zip adds an extra `artifact/` level); corrected to `../`.
  5. Fuzzer hard-codes internal container IPs `ws://172.18.0.100:8546` /
     `...101:8548`; from the host (Docker Desktop) these are unreachable, so pointed
     it at the exposed ports `ws://127.0.0.1:8546` / `:8548`.

## Result (random fuzzer, ~120 s)

- 13{,}292 transactions executed (~110/s), 7{,}316 events logged to `public.results`.
- Oracle = balance consistency per event (`accountbalances`, `accountlockedbalances`,
  `accountbalancestestcontract` -> `success` boolean + `errormsg`). An event with
  `success=false` is an alert ("Swap might be attacked ... != ...").
- **1{,}604 alerts** (success=false): `deposit_token` 1197/4916, `swap_with_permit`
  407/2398, `deposit` 0/2. Raw dump: `bridgefuzz_results.csv`.

## What this shows (for RQ2 / the oracle gap)

BridgeFuzz genuinely executes source + relay + destination together and detects bridge
inconsistencies by **raising alerts** (a balance mismatch), but it applies **no
patched-variant negative control** and **no attacker-net-gain / replay criterion**:
every one of its 1{,}604 alerts is an "assertion failed", not a trace shown to move
value to the adversary and rejected on a fixed variant. This is the oracle gap that
BridgeSentry's Definition-valid criterion closes, now demonstrated with a real run
rather than only characterised from the paper.

## Caveat (honesty)

This runs BridgeFuzz on its own prototype (`Router.sol` with injected bugs:
`deposit_token`, `swap_with_permit`), not on the real Qubit/QBridge contracts. The
shipped fuzzer references a `pnetwork` operation the shipped `Router.sol` does not
define (one skipped operation, a TypeError). A same-fixture head-to-head would require
porting an incident into its harness. So this is a demonstration of BridgeFuzz's
detection paradigm (alert oracle, no patched control), not a criterion-matched,
same-fixture comparison.
