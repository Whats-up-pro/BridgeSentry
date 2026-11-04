// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Destination-chain reserve that pays out on an authorised cross-chain
/// message. Only the registered receiver may release funds; the bug that
/// drained it lived in the receiver, not here.
contract PortalV2 {
    OfficialToken public immutable token;
    address public admin;
    address public receiver;

    constructor(address token_) {
        token = OfficialToken(token_);
        admin = msg.sender;
    }

    function setReceiver(address r) external {
        require(msg.sender == admin, "!admin");
        receiver = r;
    }

    function release(address to, uint256 amount) external {
        require(msg.sender == receiver, "!receiver");
        token.transfer(to, amount);
    }
}
