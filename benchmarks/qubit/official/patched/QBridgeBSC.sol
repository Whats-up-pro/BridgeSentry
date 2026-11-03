// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Destination-chain QBridge (BSC): mints xQubit for relayed deposits.
contract QBridgeBSC {
    OfficialToken public immutable xToken;
    address public immutable relayer;
    mapping(uint64 => bool) public processed;

    event Minted(address indexed recipient, uint256 amount, uint64 nonce);

    constructor(address xToken_, address relayer_) {
        xToken = OfficialToken(xToken_);
        relayer = relayer_;
    }

    function process(address recipient, uint256 amount, uint64 nonce_) external {
        require(msg.sender == relayer, "!relayer");
        require(!processed[nonce_], "replay");
        processed[nonce_] = true;
        xToken.mint(recipient, amount);
        emit Minted(recipient, amount, nonce_);
    }
}
