//! Evidence provenance and fail-closed evaluation metadata.
//!
//! This module is introduced test-first. The tests below pin the public JSON
//! vocabulary required by the Option-A evaluation contract before the runtime
//! starts producing official results.

#[cfg(test)]
mod tests {
    use super::{
        EvaluationMode, EvidenceSource, ExploitEvidenceGates, ObservationStatus,
        RunEvidenceProvenance,
    };

    #[test]
    fn evaluation_vocabulary_serializes_to_stable_snake_case() {
        assert_eq!(
            serde_json::to_string(&EvaluationMode::Official).unwrap(),
            "\"official\""
        );
        assert_eq!(
            serde_json::to_string(&EvaluationMode::Legacy).unwrap(),
            "\"legacy\""
        );
        assert_eq!(
            serde_json::to_string(&EvidenceSource::Execution).unwrap(),
            "\"execution\""
        );
        assert_eq!(
            serde_json::to_string(&EvidenceSource::SyntheticScenario).unwrap(),
            "\"synthetic_scenario\""
        );
        assert_eq!(
            serde_json::to_string(&EvidenceSource::Mixed).unwrap(),
            "\"mixed\""
        );
        assert_eq!(
            serde_json::to_string(&ObservationStatus::Unknown).unwrap(),
            "\"unknown\""
        );
    }

    #[test]
    fn run_provenance_does_not_upgrade_legacy_or_mixed_evidence_to_official() {
        let provenance = RunEvidenceProvenance {
            evaluation_mode: EvaluationMode::Legacy,
            oracle_state_source: EvidenceSource::Mixed,
            official_eligible: false,
            ineligibility_reasons: vec!["synthetic_or_mixed_oracle_state".to_string()],
        };

        let value = serde_json::to_value(provenance).unwrap();
        assert_eq!(value["evaluation_mode"], "legacy");
        assert_eq!(value["oracle_state_source"], "mixed");
        assert_eq!(value["official_eligible"], false);
        assert_eq!(
            value["ineligibility_reasons"],
            serde_json::json!(["synthetic_or_mixed_oracle_state"])
        );
    }

    #[test]
    fn exploit_gates_are_tristate_not_boolean() {
        let gates = ExploitEvidenceGates {
            target_bytecode_executed: ObservationStatus::Pass,
            causal_path_valid: ObservationStatus::Unknown,
            material_state_change: ObservationStatus::Fail,
            capability_compliant: ObservationStatus::Pass,
            replayable: ObservationStatus::Unknown,
            impact_demonstrated: ObservationStatus::Unknown,
            patched_rejected: ObservationStatus::Unknown,
        };

        let value = serde_json::to_value(gates).unwrap();
        assert_eq!(value["target_bytecode_executed"], "pass");
        assert_eq!(value["causal_path_valid"], "unknown");
        assert_eq!(value["material_state_change"], "fail");
        assert_eq!(value["patched_rejected"], "unknown");
    }
}
