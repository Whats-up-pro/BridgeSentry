//! Fixture-specific runtime-to-semantic mapping for Option-A official evaluation.
//!
//! Missing, ambiguous, or unresolved mappings produce `Unknown`. This module
//! never invents zero/false defaults and never consumes a `Scenario`.

use std::collections::HashMap;

use crate::official_oracle::OfficialOracleInput;
use crate::types::ChainState;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChainSide {
    Source,
    Destination,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuntimeLocator {
    Balance {
        chain: ChainSide,
        address: String,
    },
    StorageSlot {
        chain: ChainSide,
        address: String,
        slot: String,
    },
    RelayProcessedContains {
        message_key: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticFieldMapping {
    pub semantic_field: String,
    pub locator: RuntimeLocator,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SemanticFactStatus {
    Observed,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SemanticFact {
    pub status: SemanticFactStatus,
    pub value: Option<String>,
    pub reason: Option<String>,
}

impl SemanticFact {
    fn observed(value: impl Into<String>) -> Self {
        Self {
            status: SemanticFactStatus::Observed,
            value: Some(value.into()),
            reason: None,
        }
    }

    fn unknown(reason: impl Into<String>) -> Self {
        Self {
            status: SemanticFactStatus::Unknown,
            value: None,
            reason: Some(reason.into()),
        }
    }
}

/// Resolve exactly the semantic fields requested by the official validator.
/// A field needs one and only one deterministic mapping. Missing or duplicate
/// mappings abstain instead of choosing an arbitrary source.
pub fn resolve_required_facts(
    oracle: &OfficialOracleInput,
    mappings: &[SemanticFieldMapping],
    required_fields: &[String],
) -> HashMap<String, SemanticFact> {
    let mut out = HashMap::new();

    for field in required_fields {
        let candidates: Vec<&SemanticFieldMapping> = mappings
            .iter()
            .filter(|mapping| mapping.semantic_field == *field)
            .collect();

        let fact = match candidates.as_slice() {
            [] => SemanticFact::unknown("missing_runtime_mapping"),
            [mapping] => resolve_locator(oracle, &mapping.locator),
            _ => SemanticFact::unknown("ambiguous_runtime_mapping"),
        };
        out.insert(field.clone(), fact);
    }

    out
}

fn resolve_locator(oracle: &OfficialOracleInput, locator: &RuntimeLocator) -> SemanticFact {
    match locator {
        RuntimeLocator::Balance { chain, address } => {
            let state = selected_chain(&oracle.after, *chain);
            match lookup_case_insensitive(&state.balances, address) {
                Some(value) => SemanticFact::observed(value.clone()),
                None => SemanticFact::unknown("runtime_balance_not_observed"),
            }
        }
        RuntimeLocator::StorageSlot {
            chain,
            address,
            slot,
        } => {
            let state = selected_chain(&oracle.after, *chain);
            let Some(storage) = lookup_case_insensitive(&state.storage, address) else {
                return SemanticFact::unknown("runtime_storage_address_not_observed");
            };
            match lookup_case_insensitive(storage, slot) {
                Some(value) => SemanticFact::observed(value.clone()),
                None => SemanticFact::unknown("runtime_storage_slot_not_observed"),
            }
        }
        RuntimeLocator::RelayProcessedContains { message_key } => SemanticFact::observed(
            oracle
                .after
                .relay_state
                .processed_set
                .iter()
                .any(|item| item == message_key)
                .to_string(),
        ),
    }
}

fn selected_chain(state: &crate::types::GlobalState, chain: ChainSide) -> &ChainState {
    match chain {
        ChainSide::Source => &state.source_state,
        ChainSide::Destination => &state.dest_state,
    }
}

fn lookup_case_insensitive<'a, V>(map: &'a HashMap<String, V>, key: &str) -> Option<&'a V> {
    map.get(key)
        .or_else(|| map.iter().find(|(candidate, _)| candidate.eq_ignore_ascii_case(key)).map(|(_, value)| value))
}

#[cfg(test)]
mod tests {
    use super::{
        resolve_required_facts, ChainSide, RuntimeLocator, SemanticFactStatus,
        SemanticFieldMapping,
    };
    use crate::official_oracle::OfficialOracleInput;
    use crate::types::{ChainState, GlobalState, RelaySnapshot};
    use std::collections::HashMap;

    fn chain(balance: &str, storage_value: &str) -> ChainState {
        ChainState {
            balances: HashMap::from([(
                "0x1111111111111111111111111111111111111111".to_string(),
                balance.to_string(),
            )]),
            storage: HashMap::from([(
                "0x2222222222222222222222222222222222222222".to_string(),
                HashMap::from([("0x01".to_string(), storage_value.to_string())]),
            )]),
            block_number: 100,
            timestamp: 1_700_000_000,
        }
    }

    fn global() -> GlobalState {
        GlobalState {
            source_state: chain("10", "7"),
            dest_state: chain("20", "9"),
            relay_state: RelaySnapshot {
                pending_messages: vec![],
                processed_set: vec!["msg-1".to_string()],
                mode: "faithful".to_string(),
                message_count: 1,
            },
        }
    }

    fn oracle() -> OfficialOracleInput {
        OfficialOracleInput::from_execution(global(), global(), vec![])
    }

    #[test]
    fn missing_mapping_abstains_instead_of_defaulting_to_zero() {
        let facts = resolve_required_facts(
            &oracle(),
            &[],
            &["locked_value".to_string(), "minted_value".to_string()],
        );
        assert_eq!(facts["locked_value"].status, SemanticFactStatus::Unknown);
        assert_eq!(facts["locked_value"].value, None);
        assert_eq!(facts["minted_value"].status, SemanticFactStatus::Unknown);
        assert_eq!(facts["minted_value"].value, None);
    }

    #[test]
    fn mapped_chain_balance_is_read_from_runtime_snapshot() {
        let mappings = vec![SemanticFieldMapping {
            semantic_field: "locked_value".to_string(),
            locator: RuntimeLocator::Balance {
                chain: ChainSide::Source,
                address: "0x1111111111111111111111111111111111111111".to_string(),
            },
        }];
        let facts = resolve_required_facts(
            &oracle(),
            &mappings,
            &["locked_value".to_string()],
        );
        assert_eq!(facts["locked_value"].status, SemanticFactStatus::Observed);
        assert_eq!(facts["locked_value"].value.as_deref(), Some("10"));
    }

    #[test]
    fn mapped_storage_slot_is_read_from_selected_chain() {
        let mappings = vec![SemanticFieldMapping {
            semantic_field: "minted_value".to_string(),
            locator: RuntimeLocator::StorageSlot {
                chain: ChainSide::Destination,
                address: "0x2222222222222222222222222222222222222222".to_string(),
                slot: "0x01".to_string(),
            },
        }];
        let facts = resolve_required_facts(
            &oracle(),
            &mappings,
            &["minted_value".to_string()],
        );
        assert_eq!(facts["minted_value"].status, SemanticFactStatus::Observed);
        assert_eq!(facts["minted_value"].value.as_deref(), Some("9"));
    }

    #[test]
    fn unresolved_address_or_slot_remains_unknown() {
        let mappings = vec![SemanticFieldMapping {
            semantic_field: "locked_value".to_string(),
            locator: RuntimeLocator::StorageSlot {
                chain: ChainSide::Source,
                address: "0x3333333333333333333333333333333333333333".to_string(),
                slot: "0xdead".to_string(),
            },
        }];
        let facts = resolve_required_facts(
            &oracle(),
            &mappings,
            &["locked_value".to_string()],
        );
        assert_eq!(facts["locked_value"].status, SemanticFactStatus::Unknown);
        assert_eq!(facts["locked_value"].value, None);
    }

    #[test]
    fn relay_processed_membership_is_runtime_derived() {
        let mappings = vec![SemanticFieldMapping {
            semantic_field: "message_processed".to_string(),
            locator: RuntimeLocator::RelayProcessedContains {
                message_key: "msg-1".to_string(),
            },
        }];
        let facts = resolve_required_facts(
            &oracle(),
            &mappings,
            &["message_processed".to_string()],
        );
        assert_eq!(facts["message_processed"].status, SemanticFactStatus::Observed);
        assert_eq!(facts["message_processed"].value.as_deref(), Some("true"));
    }

    #[test]
    fn duplicate_semantic_mapping_is_ambiguous_and_abstains() {
        let mappings = vec![
            SemanticFieldMapping {
                semantic_field: "locked_value".to_string(),
                locator: RuntimeLocator::Balance {
                    chain: ChainSide::Source,
                    address: "0x1111111111111111111111111111111111111111".to_string(),
                },
            },
            SemanticFieldMapping {
                semantic_field: "locked_value".to_string(),
                locator: RuntimeLocator::Balance {
                    chain: ChainSide::Destination,
                    address: "0x1111111111111111111111111111111111111111".to_string(),
                },
            },
        ];
        let facts = resolve_required_facts(
            &oracle(),
            &mappings,
            &["locked_value".to_string()],
        );
        assert_eq!(facts["locked_value"].status, SemanticFactStatus::Unknown);
        assert_eq!(facts["locked_value"].value, None);
    }
}
