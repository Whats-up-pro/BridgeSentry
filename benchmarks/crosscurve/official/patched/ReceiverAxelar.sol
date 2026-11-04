// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./AxelarGateway.sol";
import "./PortalV2.sol";

/// Destination-chain CrossCurve receiver.
///
/// Patched: the express path now also calls `gateway.validateContractCall`
/// before acting, so a forged command that the Axelar gateway never attested
/// is rejected. This is the only change from the vulnerable variant; genuine,
/// gateway-attested messages still execute on both the normal and express
/// paths.
contract ReceiverAxelar {
    AxelarGateway public immutable gateway;
    PortalV2 public immutable portal;

    constructor(address gateway_, address portal_) {
        gateway = AxelarGateway(gateway_);
        portal = PortalV2(portal_);
    }

    function _execute(bytes memory payload) internal {
        (address recipient, uint256 amount) = abi.decode(payload, (address, uint256));
        portal.release(recipient, amount);
    }

    function execute(bytes32 commandId, bytes calldata payload) external {
        require(gateway.validateContractCall(commandId), "not approved by gateway");
        _execute(payload);
    }

    function expressExecute(bytes32 commandId, bytes calldata payload) external {
        require(gateway.validateContractCall(commandId), "not approved by gateway"); // PATCH
        _execute(payload);
    }
}
