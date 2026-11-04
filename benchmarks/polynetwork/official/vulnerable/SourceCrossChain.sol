// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Source-chain cross-chain manager: anyone may emit a cross-chain message. The
/// event carries the TRUE sender (fromContract), which the honest keeper relays
/// faithfully to the destination manager.
contract SourceCrossChain {
    uint256 public nonce;
    event CrossChainEvent(address indexed sender, address toContract, string method, bytes args);

    function crossChain(address toContract, string calldata method, bytes calldata args) external {
        nonce += 1;
        emit CrossChainEvent(msg.sender, toContract, method, args);
    }
}
