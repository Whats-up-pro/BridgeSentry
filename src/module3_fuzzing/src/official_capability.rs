//! Threat-model capability gate for Option-A official relay actions.
//!
//! Tests first. Fault-injection modes must be explicitly authorized by the
//! fixture before execution; faithful delivery is the only default capability.

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
