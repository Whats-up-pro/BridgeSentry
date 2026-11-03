// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Source-chain side of the Nomad token bridge (Ethereum): locks canonical
/// tokens and dispatches a message whose hash the updater/relayer later proves
/// on the destination Replica.
contract NomadHome {
    OfficialToken public immutable token;
    uint32 public constant LOCAL_DOMAIN = 1000;
    uint32 public constant REMOTE_DOMAIN = 2000;
    uint32 public nonce;

    event Dispatch(bytes32 indexed messageHash, uint32 nonce, address recipient, uint256 amount, bytes message);

    constructor(address token_) {
        token = OfficialToken(token_);
    }

    function send(address recipient, uint256 amount) external {
        require(amount > 0, "zero");
        token.transferFrom(msg.sender, address(this), amount);
        nonce += 1;
        bytes memory message = abi.encode(LOCAL_DOMAIN, REMOTE_DOMAIN, nonce, msg.sender, recipient, address(token), amount);
        emit Dispatch(keccak256(message), nonce, recipient, amount, message);
    }
}
