//! Execution-derived observation record for Option-A official evaluation.
//!
//! This module records facts obtained from runtime execution. It deliberately
//! accepts `target_bytecode_executed` as an explicit observation rather than
//! inferring it from scenario intent or transaction success.

use revm::primitives::{Address, Log};

use crate::dual_evm::TxOutcome;
use crate::storage_tracker::StorageWrite;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExecutionDisposition {
    Success,
    Revert,
    Halt,
    UnknownFailure,
}

#[derive(Debug, Clone)]
pub struct ActionObservation {
    pub chain: String,
    pub target: Address,
    pub disposition: ExecutionDisposition,
    pub target_bytecode_executed: bool,
    pub committed_logs: Vec<Log>,
    pub committed_storage_writes: Vec<StorageWrite>,
    pub output: Vec<u8>,
    pub gas_used: u64,
    pub status: String,
    pub block_number: u64,
    pub block_timestamp: u64,
}

impl ActionObservation {
    /// Conservative first material-change signal. Balance deltas and other
    /// fixture-specific semantic observations will be added by the runtime
    /// adapter; logs/storage count only when the transaction committed.
    pub fn material_state_change_observed(&self) -> bool {
        self.disposition == ExecutionDisposition::Success
            && (!self.committed_logs.is_empty() || !self.committed_storage_writes.is_empty())
    }
}

pub fn from_runtime_outcome(
    chain: &str,
    target: Address,
    outcome: &TxOutcome,
    target_bytecode_executed: bool,
    observed_storage_writes: Vec<StorageWrite>,
    block_number: u64,
    block_timestamp: u64,
) -> ActionObservation {
    let disposition = if outcome.success {
        ExecutionDisposition::Success
    } else if outcome.status.starts_with("reverted") {
        ExecutionDisposition::Revert
    } else if outcome.status.starts_with("halted") {
        ExecutionDisposition::Halt
    } else {
        ExecutionDisposition::UnknownFailure
    };

    // Only committed success can contribute logs or storage mutations to
    // exploit evidence. Callers may still retain output/status for diagnosis.
    let (committed_logs, committed_storage_writes) = if outcome.success {
        (outcome.logs.clone(), observed_storage_writes)
    } else {
        (Vec::new(), Vec::new())
    };

    ActionObservation {
        chain: chain.to_string(),
        target,
        disposition,
        target_bytecode_executed,
        committed_logs,
        committed_storage_writes,
        output: outcome.output.clone(),
        gas_used: outcome.gas_used,
        status: outcome.status.clone(),
        block_number,
        block_timestamp,
    }
}

#[cfg(test)]
mod tests {
    use super::{from_runtime_outcome, ActionObservation, ExecutionDisposition};
    use crate::dual_evm::TxOutcome;
    use crate::storage_tracker::StorageWrite;
    use revm::primitives::{Address, B256, Log, LogData, U256};

    fn target() -> Address {
        Address::from([0x11; 20])
    }

    fn storage_write() -> StorageWrite {
        StorageWrite {
            address: target(),
            slot: B256::from([0x22; 32]),
            value: U256::from(7u64),
        }
    }

    fn committed_log() -> Log {
        Log {
            address: target(),
            data: LogData::new_unchecked(vec![B256::from([0x33; 32])], vec![0x44].into()),
        }
    }

    #[test]
    fn successful_runtime_outcome_retains_committed_evidence() {
        let outcome = TxOutcome {
            success: true,
            output: vec![1, 2, 3],
            logs: vec![committed_log()],
            gas_used: 21_000,
            status: "ok".to_string(),
        };

        let observation: ActionObservation = from_runtime_outcome(
            "source",
            target(),
            &outcome,
            true,
            vec![storage_write()],
            17,
            1_700_000_000,
        );

        assert_eq!(observation.disposition, ExecutionDisposition::Success);
        assert!(observation.target_bytecode_executed);
        assert_eq!(observation.committed_logs.len(), 1);
        assert_eq!(observation.committed_storage_writes.len(), 1);
        assert_eq!(observation.block_number, 17);
        assert_eq!(observation.block_timestamp, 1_700_000_000);
    }

    #[test]
    fn reverted_runtime_outcome_drops_uncommitted_evidence() {
        let outcome = TxOutcome {
            success: false,
            output: vec![0xde, 0xad],
            logs: vec![committed_log()],
            gas_used: 42_000,
            status: "reverted: 0xdead".to_string(),
        };

        let observation = from_runtime_outcome(
            "destination",
            target(),
            &outcome,
            true,
            vec![storage_write()],
            18,
            1_700_000_012,
        );

        assert_eq!(observation.disposition, ExecutionDisposition::Revert);
        assert!(observation.target_bytecode_executed);
        assert!(observation.committed_logs.is_empty());
        assert!(observation.committed_storage_writes.is_empty());
        assert!(!observation.material_state_change_observed());
    }

    #[test]
    fn halted_runtime_outcome_is_distinct_from_revert() {
        let outcome = TxOutcome {
            success: false,
            output: vec![],
            logs: vec![],
            gas_used: 50_000,
            status: "halted: OutOfGas".to_string(),
        };

        let observation = from_runtime_outcome(
            "source",
            target(),
            &outcome,
            true,
            vec![],
            19,
            1_700_000_024,
        );

        assert_eq!(observation.disposition, ExecutionDisposition::Halt);
        assert!(!observation.material_state_change_observed());
    }

    #[test]
    fn target_execution_is_never_inferred_from_success_alone() {
        let outcome = TxOutcome {
            success: true,
            output: vec![],
            logs: vec![],
            gas_used: 21_000,
            status: "ok".to_string(),
        };

        let observation = from_runtime_outcome(
            "source",
            target(),
            &outcome,
            false,
            vec![],
            20,
            1_700_000_036,
        );

        assert!(!observation.target_bytecode_executed);
        assert!(!observation.material_state_change_observed());
    }
}
