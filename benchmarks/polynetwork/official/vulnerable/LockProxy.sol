// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Destination LockProxy: releases bridged funds, but only for a cross-chain
/// message whose source (fromContract) is the registered paired proxy. This
/// source check is why an attacker cannot simply ask for an unlock through the
/// honest relay — the honest relay reports the attacker's true source address,
/// not the registered proxy.
contract LockProxy {
    OfficialToken public immutable token;
    address public admin;
    address public manager;          // ECCM
    address public registeredProxy;  // the paired source proxy

    constructor(address token_) {
        token = OfficialToken(token_);
        admin = msg.sender;
    }

    function setManager(address m) external {
        require(msg.sender == admin, "!admin");
        manager = m;
    }

    function setRegisteredProxy(address p) external {
        require(msg.sender == admin, "!admin");
        registeredProxy = p;
    }

    /// Called by ECCM when executing a cross-chain message. `fromContract` is
    /// the message's source sender, appended by the manager.
    function unlock(address recipient, uint256 amount, address fromContract) external {
        require(msg.sender == manager, "!manager");
        require(fromContract == registeredProxy, "bad source proxy");
        token.transfer(recipient, amount);
    }
}
