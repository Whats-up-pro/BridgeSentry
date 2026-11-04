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
/// with a fabricated command and payload and have PortalV2 pay out tokens that
/// were never locked on the source chain. (The express path's only guard was a
/// peer check on attacker-controlled sourceChain/sourceAddress, which provided
/// no real security; this model omits that useless check and keeps the real
/// defect — the missing gateway validation.)
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

    /// Normal path (both variants): a message is executed only once the gateway
    /// has attested it.
    function execute(bytes32 commandId, bytes calldata payload) external {
        require(gateway.validateContractCall(commandId), "not approved by gateway");
        _execute(payload);
    }

    /// Express path. VULNERABLE: no gateway validation — a forged command is
    /// accepted.
    function expressExecute(bytes32 commandId, bytes calldata payload) external {
        _execute(payload);
    }
}
