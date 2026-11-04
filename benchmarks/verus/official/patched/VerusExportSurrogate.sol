// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// SURROGATE for the Verus side of the bridge. Verus is NOT an EVM chain; this
/// contract stands in for a Verus "export" so the dual-EVM harness can model the
/// cross-chain flow. An export locks value and commits an (exportId, amount)
/// that the honest notary attests and relays to the Ethereum bridge. Notary
/// signatures are treated as honest (the harness relay is faithful); the bug is
/// on the Ethereum side, in how the import reconciles against this committed
/// value.
contract VerusExportSurrogate {
    OfficialToken public immutable token;

    event ExportEvent(bytes32 indexed exportId, address recipient, uint256 amount);

    constructor(address token_) {
        token = OfficialToken(token_);
    }

    function export(bytes32 exportId, address recipient, uint256 amount) external {
        require(amount > 0, "zero");
        token.transferFrom(msg.sender, address(this), amount); // lock on the (surrogate) Verus side
        emit ExportEvent(exportId, recipient, amount);
    }
}
