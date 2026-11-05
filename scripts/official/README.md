# Official-oracle runners

Reusable scripts for `BRIDGESENTRY_EVALUATION_MODE=official` campaigns. This is the
canonical runner: use it for every new campaign. The scripts inside
`experiments/official_*/` are frozen records of what produced each round's
numbers; do not edit them and do not use them for new runs.

| File | Purpose |
| --- | --- |
| `run_official.sh` | One job: `<bench> <vulnerable\|patched> <llm\|random> <seed> <budget_s> [out_root]`. Repo root from `git rev-parse`; source block from `fork.block_number`, destination block from `fork.dest_block_number` (falls back to `fork.block_number`). |
| `run_matrix.sh` | `<out_root> <budget_s> <parallel_jobs> <bench>...`: runs {vulnerable, patched} × {llm, random} × `$SEEDS` and aggregates. |
| `aggregate_official.py` | `<runs_root>` → `<runs_root>/summary_official.csv` (same columns as round 1; non-triggering runs are right-censored at the budget). |
| `empty_rpc.py` | JSON-RPC stub serving an empty chain state. |

Prerequisites: `cargo build --release` in `src/module3_fuzzing`, `solc` 0.8.20 on `PATH`, Python 3.

Example (5 seeds × 20 s, two jobs in parallel):

```bash
scripts/official/run_matrix.sh experiments/official_YYYYMMDD 20 2 nomad qubit
```

Reporting rules:

- With `empty_rpc.py` the run is **local-fixture execution, not a mainnet fork**; every report must say so. Set `RPC_URL` to use a real fork endpoint instead.
- Record commit hash, `rustc`/`solc` versions, the LLM that produced `benchmarks/<bench>/llm_outputs/` (currently gpt-oss-120b, April 2026), seeds and budget.
- Round 1 passed a fixed `--source-block/--dest-block 15259100` for every bench; these scripts read the block from metadata instead. With `empty_rpc.py` this only changes the block environment; the 2026-11-03 rerun reported identical outcomes for Nomad and Qubit.

## Build cho HPC (static binary)

The fuzzer is run on HPC from a **prebuilt static binary** — do not compile on
the HPC. Build a fully-static `x86_64-unknown-linux-musl` binary on a build host
and copy it over.

### Build steps (verified 2026-11-04)

```bash
# one-time: musl std + the musl C cross-compiler (blst / c-kzg / secp256k1-sys /
# keccak-asm / ring have cc-rs build scripts that need x86_64-linux-musl-gcc)
rustup target add x86_64-unknown-linux-musl
apt-get install -y musl-tools musl-dev        # provides /usr/bin/x86_64-linux-musl-gcc

cd src/module3_fuzzing
cargo build --release --target x86_64-unknown-linux-musl
```

Output: `src/module3_fuzzing/target/x86_64-unknown-linux-musl/release/bridgesentry-fuzzer`

### Verified build (2026-11-04)

- `rustc 1.97.0 (2d8144b78 2026-07-07)`, `cargo 1.97.0`
- `solc 0.8.20+commit.a1b79de6` (runtime, see below)
- `musl-tools 1.2.4-2`
- `file` → `ELF 64-bit LSB pie executable, x86-64, static-pie linked`
- `ldd` → `statically linked`
- `sha256(bridgesentry-fuzzer)` = `beeb1c9797ff5bbe1f79aa8c65e935fd3fcd2474f56fb7fa7a076e74af9bae43`
  (this hash is specific to the build host/toolchain; recompute on your own build).
- Regression with this static binary (1 seed, 15 s, `empty_rpc.py` on a spare
  port): Nomad and Qubit reproduce exactly — vulnerable → 1/1 valid exploit,
  patched → 0/0 (both `llm` and `random`). Command:
  ```bash
  RPC_URL=http://127.0.0.1:18546 \
  BIN=.../target/x86_64-unknown-linux-musl/release/bridgesentry-fuzzer \
  SEEDS="1042" scripts/official/run_matrix.sh experiments/<out> 15 2 nomad qubit
  ```

### What the static binary does NOT bundle

The static binary removes the glibc / libgcc / rustc runtime dependency, but the
official harness still shells out to external tools **at run time**:

- **`solc` 0.8.20** on `PATH` — `World::build` compiles each fixture's `.sol`
  with it. The HPC must have solc 0.8.20 available (a standalone static solc
  binary works).
- **`python3`** — only for `empty_rpc.py` / `aggregate_official.py`. If the HPC
  has no Python, point `RPC_URL` at any JSON-RPC endpoint (the binary itself
  needs none of Python).

Do **not** commit the binary to the repo; ship it out-of-band and record its
sha256 with each campaign.

### If musl cannot be built

The hard dependency is the musl C cross-compiler for the native crates above. If
`musl-tools` is unavailable, the observed error is:

```
error occurred in cc-rs: failed to find tool "x86_64-linux-musl-gcc": No such file or directory
```

Fallback: build inside an old-glibc container (e.g. manylinux2014) for a
portable dynamic binary instead. Do not change the crate dependencies to force a
musl build without first reporting the blocker.

## Failure handling and seed provenance (2026-11-05)

- `run_official.sh` exits with the fuzzer's exit status (97 if the fuzzer exits 0 without writing its result JSON) and records it in `seed_<n>.rc`.
- `run_matrix.sh` starts the empty RPC on `$RPC_PORT` or a free port, waits until it answers `eth_chainId`, always aggregates, and exits 1 if any run failed.
- `aggregate_official.py` counts a run as `completed` only if its JSON exists and its exit status is 0. Failed runs are excluded from every outcome column (never treated as "no exploit" and never censored) and counted in the appended `runs_failed` column. `runs_seed_fallback` counts runs whose requested seed source fell back to random. Columns 1–13 are unchanged, and records without `.rc` files (before 2026-11-05) aggregate exactly as before.
- Runs use `BRIDGESENTRY_OFFICIAL_STRICT_SEEDS=1`: a requested `llm` run whose scenarios do not map to any callable fixture function fails instead of silently running random seeds. Result JSON version 2 records `seed_source_requested`, `seed_source_effective` and `seed_fallback_to_random`; `seed_source` keeps its earlier meaning (requested mode).
- Fixture tests in `official_mode.rs` fail when solc 0.8.20 is not on `PATH`. `BRIDGESENTRY_ALLOW_MISSING_SOLC=1` turns this into an explicit "SKIPPED (not evidence)" and must not be used for acceptance. CI installs the official static solc 0.8.20 (sha256 `0479d44f...fda782`).
- Behaviour tests: `python3 -m pytest tests/test_official_runner.py`.
