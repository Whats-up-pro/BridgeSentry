// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../../_official_common/OfficialToken.sol"; // deployed by the spec; drained via low-level call

/// Source chain (ZetaChain zEVM); unchanged from the vulnerable variant.
contract GatewayZEVM {
    event Called(address indexed destination, bytes data, bool isArbitraryCall);

    function call(address destination, bytes calldata data, bool isArbitraryCall) external {
        emit Called(destination, data, isArbitraryCall);
    }
}

/// Destination chain (Ethereum), patched. The documented fix removes the
/// arbitrary-call branch: every delivered message is routed to the target's
/// onCall interface, so the gateway can no longer run attacker-chosen calldata
/// such as transferFrom against a token the victim had approved. This is the
/// only change from the vulnerable variant.
contract GatewayEVM {
    address public immutable relayer;

    event Executed(address indexed destination);

    constructor(address relayer_) {
        relayer = relayer_;
    }

    function execute(address destination, bytes calldata data, bool isArbitraryCall) external returns (bytes memory) {
        require(msg.sender == relayer, "only TSS");
        require(destination != address(0), "zero destination");
        isArbitraryCall; // retained in the signature; no longer selects a raw call
        // PATCH: no arbitrary-call branch; deliver only through onCall.
        (bool ok, bytes memory ret) = destination.call(abi.encodeWithSignature("onCall(bytes)", data));
        require(ok, "onCall failed");
        emit Executed(destination);
        return ret;
    }
}
