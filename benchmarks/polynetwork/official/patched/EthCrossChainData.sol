// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// EthCrossChainData (ECCD): the privileged data store of the Poly bridge. Its
/// owner is the EthCrossChainManager (ECCM). The consensus book-keeper lives
/// here and is updated through the owner-only putCurEpochConPubKeyBytes.
///
/// In the real contract the keeper is `bytes` (packed consensus public keys);
/// this model represents the keeper by the ADDRESS authorised to submit
/// cross-chain headers, so the manager's keeper check can be enforced on-chain.
/// The function NAME (putCurEpochConPubKeyBytes) is kept from the incident; the
/// signature is adapted to (address newKeeper). The manager no longer appends
/// the message's fromContract to dispatched calls (it exposes it via a context
/// getter instead), so the setter takes only the new keeper.
contract EthCrossChainData {
    address public owner;
    address public keeper;

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address o) external {
        require(msg.sender == owner, "!owner");
        owner = o;
    }

    function initKeeper(address k) external {
        require(msg.sender == owner, "!owner");
        keeper = k;
    }

    /// Owner-only (owner == ECCM). Reaching this through a cross-chain message
    /// is the root cause of the August 2021 incident.
    function putCurEpochConPubKeyBytes(address newKeeper) external {
        require(msg.sender == owner, "!owner");
        keeper = newKeeper;
    }
}
