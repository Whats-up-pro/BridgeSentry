//! BridgeSentry Module 3 library.
//!
//! The crate exposes the existing legacy fuzzing components so the revised
//! Option-A evaluation can add an independent execution-derived official path
//! without entangling it with `scenario_sim` state synthesis. The legacy
//! binary remains available for historical reconstruction compatibility.

pub mod baselines;
pub mod checker;
pub mod config;
pub mod contract_loader;
pub mod coverage_tracker;
pub mod dual_evm;
pub mod evidence;
pub mod execution_observation;
pub mod fuzz_loop;
pub mod mock_relay;
pub mod mutator;
pub mod official_oracle;
pub mod official_semantics;
pub mod official_validator;
pub mod scenario_sim;
pub mod snapshot;
pub mod storage_tracker;
pub mod types;
