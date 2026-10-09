//! Official execution-only oracle input for Option A.
//!
//! The API intentionally accepts runtime observations and before/after runtime
//! snapshots only. It does not accept `Scenario`, waypoint predicates, or
//! scenario-simulator state, so intended actions cannot become oracle facts by
//! construction.

use crate::execution_observation::ActionObservation;
use crate::types::GlobalState;

#[derive(Debug, Clone)]
pub struct OfficialOracleInput {
    pub before: GlobalState,
    pub after: GlobalState,
    pub actions: Vec<ActionObservation>,
}

impl OfficialOracleInput {
    pub fn from_execution(
        before: GlobalState,
        after: GlobalState,
        actions: Vec<ActionObservation>,
    ) -> Self {
        Self {
            before,
            after,
            actions,
        }
    }

    /// At least one runtime inspector explicitly observed target bytecode.
    /// Transaction success or scenario intent is insufficient.
    pub fn target_bytecode_executed(&self) -> bool {
        self.actions
            .iter()
            .any(|observation| observation.target_bytecode_executed)
    }

    /// Conservative material-change predicate derived from committed runtime
    /// facts. Block-height/timestamp progression alone is intentionally ignored.
    pub fn material_state_change_observed(&self) -> bool {
        if self
            .actions
            .iter()
            .any(ActionObservation::material_state_change_observed)
        {
            return true;
        }

        if self.before.source_state.balances != self.after.source_state.balances
            || self.before.dest_state.balances != self.after.dest_state.balances
            || self.before.source_state.storage != self.after.source_state.storage
            || self.before.dest_state.storage != self.after.dest_state.storage
        {
            return true;
        }

        match (
            serde_json::to_value(&self.before.relay_state),
            serde_json::to_value(&self.after.relay_state),
        ) {
            (Ok(before), Ok(after)) => before != after,
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::OfficialOracleInput;
    use crate::dual_evm::TxOutcome;
    use crate::evidence::ObservationStatus;
    use crate::execution_observation::from_runtime_outcome;
    use crate::types::{ChainState, GlobalState, RelaySnapshot};
    use revm::primitives::Address;
    use std::collections::HashMap;

    fn chain(balance: &str) -> ChainState {
        ChainState {
            balances: HashMap::from([("0x1111111111111111111111111111111111111111".to_string(), balance.to_string())]),
            storage: HashMap::new(),
            block_number: 100,
            timestamp: 1_700_000_000,
        }
    }

    fn relay() -> RelaySnapshot {
        RelaySnapshot {
            pending_messages: vec![],
            processed_set: vec![],
            mode: "faithful".to_string(),
            message_count: 0,
        }
    }

    fn global(source_balance: &str, dest_balance: &str) -> GlobalState {
        GlobalState {
            source_state: chain(source_balance),
            dest_state: chain(dest_balance),
            relay_state: relay(),
        }
    }

    fn outcome(success: bool, status: &str) -> TxOutcome {
        TxOutcome {
            success,
            output: vec![],
            logs: vec![],
            gas_used: 21_000,
            status: status.to_string(),
        }
    }

    #[test]
    fn target_execution_comes_only_from_runtime_observation() {
        let obs = from_runtime_outcome(
            "source",
            Address::from([0x11; 20]),
            &outcome(true, "ok"),
            true,
            vec![],
            100,
            1_700_000_000,
        );
        let input = OfficialOracleInput::from_execution(global("10", "0"), global("10", "0"), vec![obs]);
        assert!(input.target_bytecode_executed());
    }

    #[test]
    fn successful_call_without_target_execution_does_not_pass_target_gate() {
        let obs = from_runtime_outcome(
            "source",
            Address::from([0x11; 20]),
            &outcome(true, "ok"),
            false,
            vec![],
            100,
            1_700_000_000,
        );
        let input = OfficialOracleInput::from_execution(global("10", "0"), global("10", "0"), vec![obs]);
        assert!(!input.target_bytecode_executed());
    }

    #[test]
    fn balance_delta_is_execution_derived_material_state_change() {
        let input = OfficialOracleInput::from_execution(
            global("10", "0"),
            global("9", "1"),
            vec![],
        );
        assert!(input.material_state_change_observed());
    }

    #[test]
    fn unchanged_snapshots_and_revert_do_not_create_material_change() {
        let obs = from_runtime_outcome(
            "destination",
            Address::from([0x22; 20]),
            &outcome(false, "reverted: denied"),
            true,
            vec![],
            100,
            1_700_000_000,
        );
        let input = OfficialOracleInput::from_execution(global("10", "0"), global("10", "0"), vec![obs]);
        assert!(!input.material_state_change_observed());
    }

    #[test]
    fn relay_state_delta_counts_as_material_cross_chain_state_change() {
        let before = global("10", "0");
        let mut after = global("10", "0");
        after.relay_state.message_count = 1;
        after.relay_state.processed_set.push("msg-1".to_string());
        let input = OfficialOracleInput::from_execution(before, after, vec![]);
        assert!(input.material_state_change_observed());
    }

    #[test]
    fn block_or_timestamp_progression_alone_is_not_material_impact() {
        let before = global("10", "0");
        let mut after = global("10", "0");
        after.source_state.block_number += 1;
        after.source_state.timestamp += 12;
        after.dest_state.block_number += 1;
        after.dest_state.timestamp += 12;
        let input = OfficialOracleInput::from_execution(before, after, vec![]);
        assert!(!input.material_state_change_observed());
    }

    #[test]
    fn relay_mode_switch_alone_is_not_material_exploit_impact() {
        let before = global("10", "0");
        let mut after = global("10", "0");
        after.relay_state.mode = "tampered".to_string();
        let input = OfficialOracleInput::from_execution(before, after, vec![]);
        assert!(!input.material_state_change_observed());
    }

    #[test]
    fn runtime_oracle_only_populates_observable_base_gates() {
        let obs = from_runtime_outcome(
            "source",
            Address::from([0x11; 20]),
            &outcome(true, "ok"),
            true,
            vec![],
            100,
            1_700_000_000,
        );
        let input = OfficialOracleInput::from_execution(global("10", "0"), global("9", "1"), vec![obs]);
        let gates = input.base_evidence_gates();

        assert_eq!(gates.target_bytecode_executed, ObservationStatus::Pass);
        assert_eq!(gates.material_state_change, ObservationStatus::Pass);
        assert_eq!(gates.causal_path_valid, ObservationStatus::Unknown);
        assert_eq!(gates.capability_compliant, ObservationStatus::Unknown);
        assert_eq!(gates.replayable, ObservationStatus::Unknown);
        assert_eq!(gates.impact_demonstrated, ObservationStatus::Unknown);
        assert_eq!(gates.patched_rejected, ObservationStatus::Unknown);
        assert!(!gates.is_valid_exploit());
    }
}
