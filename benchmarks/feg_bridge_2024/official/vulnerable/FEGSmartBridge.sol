// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Destination-chain FEG SmartBridge: holds the FEG reserve and releases it on
/// relayed cross-chain messages delivered by the Wormhole relayer.
///
/// December 2024 root cause (CertiK / PeckShield): the message handler trusted
/// the relayed `sourceAddress` only on the RELEASE op, while the SET_TRUSTED op
/// (which extends the trusted-source whitelist) performed NO source check. An
/// attacker could therefore publish a message from their own contract to add
/// that contract to the whitelist, then publish a RELEASE message to drain the
/// reserve — without ever depositing on the source chain. The bug is confined
/// to FEG's SmartBridge; Wormhole faithfully delivered the attacker's true
/// `sourceAddress`.
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

    /// Admin bootstraps the one legitimate source endpoint during setup.
    function setTrusted(address src, bool ok) external {
        require(msg.sender == admin, "!admin");
        trustedSource[src] = ok;
    }

    /// Entry point for faithfully relayed Wormhole messages. `sourceAddress` is
    /// the true emitter attested on the source chain.
    function receiveMessage(address sourceAddress, bytes calldata payload) external {
        require(msg.sender == relayer, "!relayer");
        (uint8 op, address account, uint256 amount) = abi.decode(payload, (uint8, address, uint256));
        if (op == OP_SET_TRUSTED) {
            // VULNERABLE: the whitelist can be extended by a message from ANY
            // source, so an untrusted sourceAddress can whitelist itself.
            trustedSource[account] = true;
            emit TrustedSet(account);
        } else if (op == OP_RELEASE) {
            require(trustedSource[sourceAddress], "untrusted source");
            feg.transfer(account, amount);
            emit Released(account, amount);
        }
    }
}
