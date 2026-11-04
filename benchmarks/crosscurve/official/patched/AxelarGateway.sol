// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Faithful model of an Axelar-style gateway, deployed on each chain.
///   * source role: `callContract` emits a ContractCall event that the relayer
///     carries to the destination chain;
///   * destination role: the relayer `approveContractCall`s a genuinely-relayed
///     command, and `validateContractCall` tells a receiver whether a given
///     command was attested. A receiver that never consults the gateway has no
///     way to tell a genuine message from a forged one — that is the Jan 2026
///     CrossCurve root cause.
contract AxelarGateway {
    address public relayer;
    uint256 public nonce;
    mapping(bytes32 => bool) public approved;

    event ContractCall(address indexed sender, bytes32 commandId, bytes payload);

    constructor(address relayer_) {
        relayer = relayer_;
    }

    // --- source side ---
    function callContract(string calldata, string calldata, bytes calldata payload) external returns (bytes32) {
        bytes32 commandId = keccak256(abi.encode(msg.sender, nonce, payload));
        nonce += 1;
        emit ContractCall(msg.sender, commandId, payload);
        return commandId;
    }

    // --- destination side ---
    function approveContractCall(bytes32 commandId) external {
        require(msg.sender == relayer, "!relayer");
        approved[commandId] = true;
    }

    function validateContractCall(bytes32 commandId) external returns (bool) {
        if (approved[commandId]) {
            approved[commandId] = false; // single-use, like Axelar's command execution
            return true;
        }
        return false;
    }
}
