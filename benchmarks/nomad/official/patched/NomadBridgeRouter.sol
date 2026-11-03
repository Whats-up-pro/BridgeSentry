// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";
import "./NomadReplica.sol";

/// Destination-chain router: releases (mints) the representation token for a
/// message accepted by the Replica.
contract NomadBridgeRouter {
    NomadReplica public immutable replica;
    OfficialToken public immutable representation;

    struct Body {
        uint32 originDomain;
        uint32 destinationDomain;
        uint32 nonce;
        address sender;
        address recipient;
        address token;
        uint256 amount;
    }

    constructor(address replica_, address representation_) {
        replica = NomadReplica(replica_);
        representation = OfficialToken(representation_);
    }

    function processAndRelease(Body calldata b) external {
        bytes memory message = abi.encode(b.originDomain, b.destinationDomain, b.nonce, b.sender, b.recipient, b.token, b.amount);
        require(replica.process(message), "replica");
        representation.mint(b.recipient, b.amount);
    }
}
