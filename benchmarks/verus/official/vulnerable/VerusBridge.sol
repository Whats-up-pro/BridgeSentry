// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Ethereum side of the Verus bridge.
///
/// May 2026 root cause: `checkCCEValues` verified notary signatures and Merkle
/// proofs (the export is real) but did NOT reconcile the Ethereum payout against
/// the value actually committed in the Verus export. An attacker could reference
/// a real (small) export yet claim a far larger payout, and the bridge paid it.
/// Notary attestation is modelled by `recordExport`, callable only by the honest
/// notary (the relayer); the attacker cannot fabricate an export, only over-claim
/// against an attested one.
contract VerusBridge {
    OfficialToken public immutable token;
    address public notary;
    mapping(bytes32 => uint256) public committedExport; // notary-attested source value
    mapping(bytes32 => uint256) public claimed;          // already paid out per export

    event Imported(address indexed recipient, uint256 payout, bytes32 exportId);

    constructor(address token_, address notary_) {
        token = OfficialToken(token_);
        notary = notary_;
    }

    /// Honest notary relays a Verus export's committed value.
    function recordExport(bytes32 exportId, uint256 sourceValue) external {
        require(msg.sender == notary, "!notary");
        committedExport[exportId] += sourceValue;
    }

    /// Anyone may submit an import claiming a payout against an attested export.
    function submitImports(address recipient, uint256 payout, bytes32 exportId) external {
        require(committedExport[exportId] > 0, "unknown export"); // notary-attested export exists
        checkCCEValues(payout, exportId);
        claimed[exportId] += payout;
        token.transfer(recipient, payout);
        emit Imported(recipient, payout, exportId);
    }

    /// Reconcile the cross-chain-export (CCE) values.
    function checkCCEValues(uint256 payout, bytes32 exportId) internal view {
        // VULNERABLE: the Ethereum payout is never reconciled against the value
        // committed on the Verus side (committedExport[exportId]). Any payout is
        // accepted as long as some attested export exists.
        payout; exportId; // silence unused-variable warnings
    }
}
