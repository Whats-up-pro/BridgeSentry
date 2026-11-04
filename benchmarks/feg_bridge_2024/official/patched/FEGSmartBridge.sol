// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Destination-chain FEG SmartBridge: holds the FEG reserve and releases it on
/// relayed cross-chain messages delivered by the Wormhole relayer.
///
/// Patched: the SET_TRUSTED op now also requires the message to originate from
/// an already-trusted `sourceAddress`, so only an existing trusted endpoint can
/// extend the whitelist. An attacker publishing from their own (untrusted)
/// contract can no longer whitelist themselves, and the subsequent RELEASE is
/// rejected. This is the only change from the vulnerable variant.
contract FEGSmartBridge {
    OfficialToken public immutable feg;
    address public admin;
    address public relayer;
    mapping(address => bool) public trustedSource;

    uint8 public constant OP_SET_TRUSTED = 1;
    uint8 public constant OP_RELEASE = 2;

    event Released(address indexed to, uint256 amount);
    event TrustedSet(address indexed src);

    constructor(address feg_, address relayer_) {
        feg = OfficialToken(feg_);
        admin = msg.sender;
        relayer = relayer_;
    }

    function setTrusted(address src, bool ok) external {
        require(msg.sender == admin, "!admin");
        trustedSource[src] = ok;
    }

    function receiveMessage(address sourceAddress, bytes calldata payload) external {
        require(msg.sender == relayer, "!relayer");
        (uint8 op, address account, uint256 amount) = abi.decode(payload, (uint8, address, uint256));
        if (op == OP_SET_TRUSTED) {
            require(trustedSource[sourceAddress], "untrusted source"); // PATCH
            trustedSource[account] = true;
            emit TrustedSet(account);
        } else if (op == OP_RELEASE) {
            require(trustedSource[sourceAddress], "untrusted source");
            feg.transfer(account, amount);
            emit Released(account, amount);
        }
    }
}
