//! Official execution-only oracle input for Option A.
//!
//! Tests are committed before production definitions. The API intentionally
//! accepts runtime observations and snapshots only; `Scenario` is not an input.

#[cfg(test)]
mod tests {
    use super::OfficialOracleInput;
    use crate::dual_evm::TxOutcome;
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
}
