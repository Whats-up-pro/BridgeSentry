//! Fail-closed valid-exploit aggregation for Option-A official evaluation.
//!
//! Tests first. Runtime-observable base gates come from OfficialOracleInput;
//! causal/capability/replay/impact/patched-control evidence is supplied only by
//! dedicated validators/control runs.

#[cfg(test)]
mod tests {
    use super::{finalize_exploit_evidence, SupplementalExploitEvidence};
    use crate::evidence::{ExploitEvidenceGates, ObservationStatus};

    fn base_pass() -> ExploitEvidenceGates {
        ExploitEvidenceGates {
            target_bytecode_executed: ObservationStatus::Pass,
            material_state_change: ObservationStatus::Pass,
            ..ExploitEvidenceGates::default()
        }
    }

    fn supplemental_all_pass() -> SupplementalExploitEvidence {
        SupplementalExploitEvidence {
            causal_path_valid: ObservationStatus::Pass,
            capability_compliant: ObservationStatus::Pass,
            replayable: ObservationStatus::Pass,
            impact_demonstrated: ObservationStatus::Pass,
            patched_rejected: ObservationStatus::Pass,
        }
    }

    #[test]
    fn all_seven_gates_must_pass_for_valid_exploit() {
        let gates = finalize_exploit_evidence(base_pass(), supplemental_all_pass());
        assert!(gates.is_valid_exploit());
    }

    #[test]
    fn missing_supplemental_evidence_stays_unknown_and_fails_closed() {
        let gates = finalize_exploit_evidence(base_pass(), SupplementalExploitEvidence::default());
        assert_eq!(gates.causal_path_valid, ObservationStatus::Unknown);
        assert_eq!(gates.capability_compliant, ObservationStatus::Unknown);
        assert_eq!(gates.replayable, ObservationStatus::Unknown);
        assert_eq!(gates.impact_demonstrated, ObservationStatus::Unknown);
        assert_eq!(gates.patched_rejected, ObservationStatus::Unknown);
        assert!(!gates.is_valid_exploit());
    }

    #[test]
    fn any_failed_supplemental_gate_rejects_candidate() {
        for idx in 0..5 {
            let mut evidence = supplemental_all_pass();
            match idx {
                0 => evidence.causal_path_valid = ObservationStatus::Fail,
                1 => evidence.capability_compliant = ObservationStatus::Fail,
                2 => evidence.replayable = ObservationStatus::Fail,
                3 => evidence.impact_demonstrated = ObservationStatus::Fail,
                4 => evidence.patched_rejected = ObservationStatus::Fail,
                _ => unreachable!(),
            }
            assert!(!finalize_exploit_evidence(base_pass(), evidence).is_valid_exploit());
        }
    }

    #[test]
    fn supplemental_evidence_cannot_upgrade_failed_runtime_base_gate() {
        let mut base = base_pass();
        base.target_bytecode_executed = ObservationStatus::Fail;
        let gates = finalize_exploit_evidence(base, supplemental_all_pass());
        assert_eq!(gates.target_bytecode_executed, ObservationStatus::Fail);
        assert!(!gates.is_valid_exploit());
    }

    #[test]
    fn supplemental_evidence_only_fills_its_owned_gate_fields() {
        let mut base = base_pass();
        base.causal_path_valid = ObservationStatus::Fail;
        let gates = finalize_exploit_evidence(base, supplemental_all_pass());
        // A prior fail is sticky: a later validator cannot overwrite contrary
        // evidence simply by reporting Pass.
        assert_eq!(gates.causal_path_valid, ObservationStatus::Fail);
        assert!(!gates.is_valid_exploit());
    }
}
