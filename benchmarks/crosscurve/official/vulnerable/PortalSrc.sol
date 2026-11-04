// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";
import "./AxelarGateway.sol";

/// Source-chain portal: locks tokens and sends a cross-chain release message
/// through the Axelar gateway. Honest traffic flows through here.
contract PortalSrc {
    OfficialToken public immutable token;
    AxelarGateway public immutable gateway;

    constructor(address token_, address gateway_) {
        token = OfficialToken(token_);
        gateway = AxelarGateway(gateway_);
    }

    function deposit(address recipient, uint256 amount) external {
        require(amount > 0, "zero");
        token.transferFrom(msg.sender, address(this), amount);
        bytes memory payload = abi.encode(recipient, amount);
        gateway.callContract("arbitrum", "receiver", payload);
    }
}
