// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Ethereum side of the Verus bridge.
///
/// Patched: `checkCCEValues` now reconciles the Ethereum payout against the
/// value committed on the Verus side, so the cumulative payout for an export can
/// never exceed its attested committed value. An import that over-claims against
/// a small (or unrelated) export is rejected. This is the only change from the
/// vulnerable variant; honest imports (payout <= committed value) still succeed.
contract VerusBridge {
    OfficialToken public immutable token;
    address public notary;
    mapping(bytes32 => uint256) public committedExport;
    mapping(bytes32 => uint256) public claimed;

    event Imported(address indexed recipient, uint256 payout, bytes32 exportId);

    constructor(address token_, address notary_) {
        token = OfficialToken(token_);
        notary = notary_;
    }

    function recordExport(bytes32 exportId, uint256 sourceValue) external {
        require(msg.sender == notary, "!notary");
        committedExport[exportId] += sourceValue;
    }

    function submitImports(address recipient, uint256 payout, bytes32 exportId) external {
        require(committedExport[exportId] > 0, "unknown export");
        checkCCEValues(payout, exportId);
        claimed[exportId] += payout;
        token.transfer(recipient, payout);
        emit Imported(recipient, payout, exportId);
    }

    function checkCCEValues(uint256 payout, bytes32 exportId) internal view {
        // PATCH: reconcile the payout against the committed source value.
        require(claimed[exportId] + payout <= committedExport[exportId], "payout exceeds committed source value");
    }
}
