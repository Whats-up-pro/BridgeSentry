// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Faithful model of an Axelar-style gateway, deployed on each chain.
///   * source role: `callContract` emits a ContractCall event that the relayer
///     carries to the destination chain;
///   * destination role: the relayer `approveContractCall`s a genuinely-relayed
///     command together with the source address that emitted it, and
///     `validateContractCall` tells a receiver whether a given command was
///     attested AND came from the expected source address. Binding the attested
///     source is what lets a receiver reject a message the relayer faithfully
///     carried from an attacker-controlled source contract. A receiver that
///     never consults the gateway (or ignores the attested source) has no way
///     to tell a genuine message from a forged or mis-sourced one.
contract AxelarGateway {
    address public relayer;
    uint256 public nonce;
    mapping(bytes32 => bool) public approved;
    mapping(bytes32 => address) public approvedSource;

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
    function approveContractCall(bytes32 commandId, address source) external {
        require(msg.sender == relayer, "!relayer");
        approved[commandId] = true;
        approvedSource[commandId] = source;
    }

    function validateContractCall(bytes32 commandId, address expectedSource) external returns (bool) {
        if (approved[commandId] && approvedSource[commandId] == expectedSource) {
            approved[commandId] = false; // single-use, like Axelar's command execution
            approvedSource[commandId] = address(0);
            return true;
        }
        return false;
    }
}
