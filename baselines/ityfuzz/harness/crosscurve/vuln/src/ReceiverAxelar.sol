// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./AxelarGateway.sol";
import "./PortalV2.sol";

/// Destination-chain CrossCurve receiver.
///
/// January 2026 root cause: `expressExecute` (the fast path) executed the
/// relayed payload WITHOUT asking the Axelar gateway whether the command had
/// actually been attested (`validateContractCall`). The normal `execute` path
/// did consult the gateway; the express path did not, so anyone could call it
/// with a fabricated command and a payload paying themselves, and have PortalV2
/// release tokens that were never locked on the source chain.
///
/// Both paths keep a peer check that the message's sourceAddress is the trusted
/// source portal. On the normal path this is meaningful because the gateway
/// attests the real source, so the relayer cannot smuggle an attacker-sourced
/// message through. On the express path the sourceAddress is caller-supplied and
/// the attacker simply sets it to the trusted peer, so the peer check alone is
/// no defence — only the (missing) gateway attestation would be.
contract ReceiverAxelar {
    AxelarGateway public immutable gateway;
    PortalV2 public immutable portal;
    address public immutable trustedSource;

    constructor(address gateway_, address portal_, address trustedSource_) {
        gateway = AxelarGateway(gateway_);
        portal = PortalV2(portal_);
        trustedSource = trustedSource_;
    }

    function _execute(bytes memory payload) internal {
        (address recipient, uint256 amount) = abi.decode(payload, (address, uint256));
        portal.release(recipient, amount);
    }

    /// Normal path (both variants): the gateway must have attested this command
    /// AS COMING FROM the trusted source contract, so a message the relayer
    /// faithfully carried from any other (attacker-controlled) source is
    /// rejected.
    function execute(bytes32 commandId, address sourceAddress, bytes calldata payload) external {
        require(sourceAddress == trustedSource, "untrusted source");
        require(gateway.validateContractCall(commandId, sourceAddress), "not approved by gateway");
        _execute(payload);
    }

    /// Express path. VULNERABLE: only the caller-supplied peer check, no gateway
    /// attestation, so a forged command with sourceAddress set to the trusted
    /// peer is accepted.
    function expressExecute(bytes32 commandId, address sourceAddress, bytes calldata payload) external {
        require(sourceAddress == trustedSource, "untrusted source");
        _execute(payload);
    }
}
