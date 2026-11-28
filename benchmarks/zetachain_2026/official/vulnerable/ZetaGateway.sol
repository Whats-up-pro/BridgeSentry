// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../../_official_common/OfficialToken.sol"; // deployed by the spec; drained via low-level call

/// Source chain (ZetaChain zEVM). Faithful model of GatewayZEVM.call: any
/// account may request a cross-chain call, and the emitted event carries the
/// caller-chosen `isArbitraryCall` flag verbatim. The protocol validators (the
/// TSS) sign a destination transaction from this event; the harness models that
/// faithful delivery with its relay, executed under the relayer identity.
///
/// April 2026 root cause (SolidityScan): GatewayZEVM.call has no caller
/// authentication and propagates IsArbitraryCall from the caller, so an attacker
/// can have the TSS sign an arbitrary call on the destination chain.
contract GatewayZEVM {
    event Called(address indexed destination, bytes data, bool isArbitraryCall);

    function call(address destination, bytes calldata data, bool isArbitraryCall) external {
        emit Called(destination, data, isArbitraryCall);
    }
}

/// Destination chain (Ethereum). Faithful model of GatewayEVM.execute: callable
/// only by the TSS signer, but when the delivered message is an arbitrary call
/// it runs attacker-controlled calldata against an attacker-chosen target.
///
/// A token that any account had approved to this gateway (a normal precondition
/// for cross-chain deposits) is therefore drained by a relayed
/// transferFrom(victim, attacker, amount). The TSS_ROLE check does not help: the
/// TSS itself is the caller, because it legitimately signed the attacker's
/// cross-chain message.
contract GatewayEVM {
    address public immutable relayer;

    event Executed(address indexed destination);

    constructor(address relayer_) {
        relayer = relayer_;
    }

    function execute(address destination, bytes calldata data, bool isArbitraryCall) external returns (bytes memory) {
        require(msg.sender == relayer, "only TSS");
        require(destination != address(0), "zero destination");
        bytes memory result;
        if (isArbitraryCall) {
            // VULNERABLE: run the delivered calldata verbatim against the target.
            (bool ok, bytes memory ret) = destination.call(data);
            require(ok, "execution failed");
            result = ret;
        } else {
            // Authenticated path: deliver to the target's onCall interface only.
            (bool ok, bytes memory ret) = destination.call(abi.encodeWithSignature("onCall(bytes)", data));
            require(ok, "onCall failed");
            result = ret;
        }
        emit Executed(destination);
        return result;
    }
}
