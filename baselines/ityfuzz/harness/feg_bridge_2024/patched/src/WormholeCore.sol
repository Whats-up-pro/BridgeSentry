// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Faithful model of a Wormhole-style core messaging contract on the source
/// chain. Anyone may publish a message, and the emitted event carries the TRUE
/// emitter address (the `sourceAddress` the guardians later attest). Wormhole
/// itself is not the bug: the December 2024 incident was a logical error in
/// FEG's own SmartBridge, which acted on a relayed message without verifying
/// that this `sourceAddress` was a trusted FEG endpoint
/// (CertiK; PeckShield; Wormhole Foundation statement).
contract WormholeCore {
    uint64 public sequence;

    event LogMessagePublished(address indexed sender, uint64 sequence, bytes payload);

    function publishMessage(bytes calldata payload) external returns (uint64) {
        uint64 s = sequence;
        sequence = s + 1;
        emit LogMessagePublished(msg.sender, s, payload);
        return s;
    }
}
