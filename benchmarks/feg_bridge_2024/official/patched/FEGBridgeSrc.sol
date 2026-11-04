// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";
import "./WormholeCore.sol";

/// Legitimate FEG bridge endpoint on the source chain. A user deposits FEG
/// here; the endpoint locks the tokens and publishes a cross-chain RELEASE
/// message through Wormhole. Because this endpoint is the message emitter, its
/// address is the `sourceAddress` the destination SmartBridge is meant to
/// trust. Honest traffic always flows through here.
contract FEGBridgeSrc {
    OfficialToken public immutable feg;
    WormholeCore public immutable core;
    uint8 public constant OP_RELEASE = 2;

    constructor(address feg_, address core_) {
        feg = OfficialToken(feg_);
        core = WormholeCore(core_);
    }

    function deposit(address recipient, uint256 amount) external {
        require(amount > 0, "zero");
        feg.transferFrom(msg.sender, address(this), amount);
        bytes memory payload = abi.encode(OP_RELEASE, recipient, amount);
        core.publishMessage(payload);
    }
}
