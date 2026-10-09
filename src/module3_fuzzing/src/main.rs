//! BridgeSentry Dual-Chain Fuzzing Engine
//!
//! Synchronized dual-EVM fuzzer for cross-chain bridge vulnerability discovery.
//! Maintains paired EVM instances (source + destination) connected through a mock relay.

pub mod types;
pub mod config;
mod evidence;
mod execution_observation;
mod baselines;
mod contract_loader;
mod coverage_tracker;
mod dual_evm;
mod fuzz_loop;
mod mock_relay;
mod snapshot;
mod mutator;
mod checker;
mod scenario_sim;
mod storage_tracker;

use eyre::Context;

fn main() {
    // Explicit evaluation boundary for Option A. Legacy remains the default so
    // historical scripts are not relabelled. Until the execution-only oracle
    // is wired end-to-end, asking for official mode must fail before any
    // benchmark execution occurs.
    let raw_evaluation_mode = std::env::var("BRIDGESENTRY_EVALUATION_MODE").ok();
    let evaluation_mode = match evidence::parse_evaluation_mode(raw_evaluation_mode.as_deref()) {
        Ok(mode) => mode,
        Err(e) => {
            eprintln!("ERROR: {e}");
            std::process::exit(1);
        }
    };
    if let Err(e) = evidence::preflight_evaluation_mode(evaluation_mode) {
        eprintln!("ERROR: {e}");
        std::process::exit(1);
    }

    let ctx = match config::parse_and_load() {
        Ok(ctx) => ctx,
        Err(e) => {
            eprintln!("ERROR: Failed to initialize fuzzer: {:#}", e);
            std::process::exit(1);
        }
    };

    ctx.print_summary();

    let results = match fuzz_loop::run(&ctx) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("ERROR: Fuzz loop failed: {:#}", e);
            std::process::exit(1);
        }
    };

    if let Err(e) = write_results(&ctx.config.output_path, &results) {
        eprintln!("ERROR: Failed to write results JSON: {e:#}");
        std::process::exit(2);
    }

    println!(
        "\nFuzzer loop completed. Iterations={} Violations={} Corpus={} PoolPeak={} Output={}",
        results.stats.total_iterations,
        results.violations.len(),
        results.stats.corpus_size,
        results.stats.snapshot_pool_peak,
        ctx.config.output_path
    );
}

fn write_results(path: &str, results: &types::FuzzingResults) -> eyre::Result<()> {
    let output_path = std::path::Path::new(path);
    if let Some(parent) = output_path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .wrap_err_with(|| format!("Failed to create output dir: {}", parent.display()))?;
        }
    }

    // Until the official execution-derived path is wired, every newly
    // produced stock result is explicitly labelled legacy/mixed and every
    // per-violation exploit gate defaults to unknown. This prevents old
    // predicate triggers from being silently reinterpreted as VER evidence.
    let content = evidence::serialize_results_with_evidence(results)
        .wrap_err("Failed to serialize results with evidence provenance")?;
    std::fs::write(output_path, content)
        .wrap_err_with(|| format!("Failed to write output file: {}", output_path.display()))?;
    Ok(())
}
