// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Destination-chain Replica (Moonbeam side), reduced to the logic involved in
/// the August 2022 incident. Messages are proven by the updater (modelled by
/// the relayer). The June 2022 upgrade called initialize(0x00, ...), which set
/// confirmAt[0x00] = 1; unproven messages map to root 0x00 and were accepted.
contract NomadReplica {
    address public updater;
    bool public initialized;
    bytes32 public committedRoot;
    uint256 public optimisticSeconds;
    mapping(bytes32 => uint256) public confirmAt;
    mapping(bytes32 => bytes32) public messages;
    mapping(bytes32 => bool) public processed;

    event Proven(bytes32 indexed messageHash, bytes32 indexed root);
    event Processed(bytes32 indexed messageHash);

    function initialize(address updater_, bytes32 _committedRoot, uint256 _optimisticSeconds) external {
        require(!initialized, "already initialized");
        initialized = true;
        updater = updater_;
        committedRoot = _committedRoot;
        optimisticSeconds = _optimisticSeconds;
        confirmAt[_committedRoot] = 1; // VULNERABLE when _committedRoot == 0x00
    }

    function prove(bytes32 messageHash, bytes32 root) external {
        require(msg.sender == updater, "!updater");
        messages[messageHash] = root;
        if (confirmAt[root] == 0) {
            confirmAt[root] = block.timestamp + optimisticSeconds;
        }
        emit Proven(messageHash, root);
    }

    function acceptableRoot(bytes32 _root) public view returns (bool) {
        uint256 _time = confirmAt[_root];
        if (_time == 0) return false;
        return block.timestamp >= _time;
    }

    function process(bytes calldata message) external returns (bool) {
        bytes32 h = keccak256(message);
        require(!processed[h], "already processed");
        require(acceptableRoot(messages[h]), "!proven");
        processed[h] = true;
        emit Processed(h);
        return true;
    }
}
