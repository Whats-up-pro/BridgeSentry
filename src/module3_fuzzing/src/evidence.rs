//! Evidence provenance and fail-closed evaluation metadata.
//!
//! These types intentionally separate legacy/synthetic reconstruction from
//! execution-derived evidence. Legacy runtime DTOs remain backward-compatible;
//! result serialization adds an explicit evidence envelope instead of silently
//! upgrading historical structs to official evidence.

use serde::{Deserialize, Serialize};

use crate::types::FuzzingResults;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvaluationMode {
    Legacy,
    Official,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceSource {
    Execution,
    SyntheticScenario,
    Mixed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ObservationStatus {
    Pass,
    Fail,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunEvidenceProvenance {
    pub evaluation_mode: EvaluationMode,
    pub oracle_state_source: EvidenceSource,
    pub official_eligible: bool,
    pub ineligibility_reasons: Vec<String>,
}

impl Default for RunEvidenceProvenance {
    fn default() -> Self {
        Self {
            evaluation_mode: EvaluationMode::Legacy,
            oracle_state_source: EvidenceSource::Mixed,
            official_eligible: false,
            ineligibility_reasons: vec!["unvalidated_legacy_or_mixed_evidence".to_string()],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExploitEvidenceGates {
    pub target_bytecode_executed: ObservationStatus,
    pub causal_path_valid: ObservationStatus,
    pub material_state_change: ObservationStatus,
    pub capability_compliant: ObservationStatus,
    pub replayable: ObservationStatus,
    pub impact_demonstrated: ObservationStatus,
    pub patched_rejected: ObservationStatus,
}

impl Default for ExploitEvidenceGates {
    fn default() -> Self {
        Self {
            target_bytecode_executed: ObservationStatus::Unknown,
            causal_path_valid: ObservationStatus::Unknown,
            material_state_change: ObservationStatus::Unknown,
            capability_compliant: ObservationStatus::Unknown,
            replayable: ObservationStatus::Unknown,
            impact_demonstrated: ObservationStatus::Unknown,
            patched_rejected: ObservationStatus::Unknown,
        }
    }
}

/// Decorate a legacy `FuzzingResults` value with explicit fail-closed evidence
/// metadata for JSON output. This deliberately does not mutate the legacy DTO:
/// old fixtures remain readable, while every newly serialized run states that
/// it is legacy/ineligible until later A1 tasks provide execution-derived gates.
pub fn serialize_results_with_evidence(results: &FuzzingResults) -> serde_json::Result<String> {
    let mut value = serde_json::to_value(results)?;
    let Some(root) = value.as_object_mut() else {
        unreachable!("FuzzingResults always serializes as a JSON object");
    };

    root.insert(
        "evidence".to_string(),
        serde_json::to_value(RunEvidenceProvenance::default())?,
    );

    if let Some(violations) = root.get_mut("violations").and_then(|v| v.as_array_mut()) {
        for violation in violations {
            if let Some(obj) = violation.as_object_mut() {
                obj.insert(
                    "evidence".to_string(),
                    serde_json::to_value(ExploitEvidenceGates::default())?,
                );
            }
        }
    }

    serde_json::to_string_pretty(&value)
}

#[cfg(test)]
mod tests {
    use super::{
        serialize_results_with_evidence, EvaluationMode, EvidenceSource, ExploitEvidenceGates,
        ObservationStatus, RunEvidenceProvenance,
    };
    use crate::types::FuzzingResults;

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

    #[test]
    fn defaults_are_fail_closed_and_legacy() {
        let run = RunEvidenceProvenance::default();
        assert_eq!(run.evaluation_mode, EvaluationMode::Legacy);
        assert_eq!(run.oracle_state_source, EvidenceSource::Mixed);
        assert!(!run.official_eligible);
        assert!(!run.ineligibility_reasons.is_empty());

        let gates = ExploitEvidenceGates::default();
        assert_eq!(gates.target_bytecode_executed, ObservationStatus::Unknown);
        assert_eq!(gates.causal_path_valid, ObservationStatus::Unknown);
        assert_eq!(gates.material_state_change, ObservationStatus::Unknown);
        assert_eq!(gates.capability_compliant, ObservationStatus::Unknown);
        assert_eq!(gates.replayable, ObservationStatus::Unknown);
        assert_eq!(gates.impact_demonstrated, ObservationStatus::Unknown);
        assert_eq!(gates.patched_rejected, ObservationStatus::Unknown);
    }

    #[test]
    fn legacy_results_serialize_with_fail_closed_evidence_defaults() {
        let result: FuzzingResults = serde_json::from_value(serde_json::json!({
            "bridge_name": "legacy_fixture",
            "run_id": 0,
            "time_budget_s": 1,
            "violations": [{
                "invariant_id": "inv_legacy",
                "detected_at_s": 0.1,
                "trigger_scenario": "s1",
                "trigger_trace": [],
                "state_diff": {}
            }],
            "coverage": {
                "xcc_atg": 0.0,
                "basic_blocks_source": 0,
                "basic_blocks_dest": 0
            },
            "stats": {
                "total_iterations": 1,
                "snapshots_captured": 1,
                "mutations_applied": 0
            }
        }))
        .unwrap();

        let rendered = serialize_results_with_evidence(&result).unwrap();
        let value: serde_json::Value = serde_json::from_str(&rendered).unwrap();
        assert_eq!(value["evidence"]["evaluation_mode"], "legacy");
        assert_eq!(value["evidence"]["oracle_state_source"], "mixed");
        assert_eq!(value["evidence"]["official_eligible"], false);
        assert_eq!(
            value["violations"][0]["evidence"]["target_bytecode_executed"],
            "unknown"
        );
        assert_eq!(
            value["violations"][0]["evidence"]["patched_rejected"],
            "unknown"
        );
    }
}
