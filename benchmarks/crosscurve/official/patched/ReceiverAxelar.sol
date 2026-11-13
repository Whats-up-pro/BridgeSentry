// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./AxelarGateway.sol";
import "./PortalV2.sol";

/// Destination-chain CrossCurve receiver.
///
/// Patched: the express path now also calls `gateway.validateContractCall`
/// before acting, so a forged command that the Axelar gateway never attested
/// (from the trusted source) is rejected. This is the only change from the
/// vulnerable variant; genuine, gateway-attested messages from the trusted
/// source still execute on both the normal and express paths.
///
/// Both paths keep the peer check that the message's sourceAddress is the
/// trusted source portal; combined with the gateway attestation (which binds
/// the real source), the relayer cannot smuggle an attacker-sourced message
/// through either path.
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

    function execute(bytes32 commandId, address sourceAddress, bytes calldata payload) external {
        require(sourceAddress == trustedSource, "untrusted source");
        require(gateway.validateContractCall(commandId, sourceAddress), "not approved by gateway");
        _execute(payload);
    }

    function expressExecute(bytes32 commandId, address sourceAddress, bytes calldata payload) external {
        require(sourceAddress == trustedSource, "untrusted source");
        require(gateway.validateContractCall(commandId, sourceAddress), "not approved by gateway"); // PATCH
        _execute(payload);
    }
}
