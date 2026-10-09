//! Threat-model capability gate for Option-A official relay actions.
//!
//! Fault-injection modes must be explicitly authorized by the fixture before
//! execution. Faithful delivery is the only default capability.

use crate::mock_relay::RelayMode;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct RelayCapabilityPolicy {
    pub allow_delay: bool,
    pub allow_tamper: bool,
    pub allow_replay: bool,
}

/// Authorize a relay mode before execution. This is intentionally a preflight
/// check: unauthorized fault injection must never run and then be filtered from
/// results after the fact.
pub fn authorize_relay_mode(
    policy: &RelayCapabilityPolicy,
    mode: RelayMode,
) -> Result<(), String> {
    match mode {
        RelayMode::Faithful => Ok(()),
        RelayMode::Delayed { .. } if policy.allow_delay => Ok(()),
        RelayMode::Tampered if policy.allow_tamper => Ok(()),
        RelayMode::Replayed if policy.allow_replay => Ok(()),
        RelayMode::Delayed { .. } => Err("relay delay is not authorized by fixture threat model".to_string()),
        RelayMode::Tampered => Err("relay tamper is not authorized by fixture threat model".to_string()),
        RelayMode::Replayed => Err("relay replay is not authorized by fixture threat model".to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::{authorize_relay_mode, RelayCapabilityPolicy};
    use crate::mock_relay::RelayMode;

    #[test]
    fn faithful_delivery_is_allowed_by_default() {
        assert!(authorize_relay_mode(
            &RelayCapabilityPolicy::default(),
            RelayMode::Faithful
        )
        .is_ok());
    }

    #[test]
    fn fault_injection_is_denied_by_default() {
        let policy = RelayCapabilityPolicy::default();
        assert!(authorize_relay_mode(&policy, RelayMode::Delayed { delta_blocks: 3 }).is_err());
        assert!(authorize_relay_mode(&policy, RelayMode::Tampered).is_err());
        assert!(authorize_relay_mode(&policy, RelayMode::Replayed).is_err());
    }

    #[test]
    fn each_nonfaithful_capability_requires_explicit_fixture_authorization() {
        let policy = RelayCapabilityPolicy {
            allow_delay: true,
            allow_tamper: true,
            allow_replay: true,
        };
        assert!(authorize_relay_mode(&policy, RelayMode::Delayed { delta_blocks: 5 }).is_ok());
        assert!(authorize_relay_mode(&policy, RelayMode::Tampered).is_ok());
        assert!(authorize_relay_mode(&policy, RelayMode::Replayed).is_ok());
    }

    #[test]
    fn authorizing_one_fault_mode_does_not_authorize_the_others() {
        let policy = RelayCapabilityPolicy {
            allow_delay: false,
            allow_tamper: true,
            allow_replay: false,
        };
        assert!(authorize_relay_mode(&policy, RelayMode::Tampered).is_ok());
        assert!(authorize_relay_mode(&policy, RelayMode::Delayed { delta_blocks: 1 }).is_err());
        assert!(authorize_relay_mode(&policy, RelayMode::Replayed).is_err());
    }

    #[test]
    fn rejection_reason_identifies_the_unauthorized_capability() {
        let err = authorize_relay_mode(&RelayCapabilityPolicy::default(), RelayMode::Replayed)
            .unwrap_err();
        assert!(err.contains("replay"));
        assert!(err.contains("not authorized"));
    }
}
