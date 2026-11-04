// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./EthCrossChainData.sol";

/// EthCrossChainManager (ECCM).
///
/// Patched: a cross-chain message may no longer target the privileged ECCD
/// (Poly's fix added limits/whitelists on the contracts and methods a message
/// may invoke). The keeper can no longer be replaced through a cross-chain
/// message, so the attacker never becomes the keeper and the later direct
/// `verifyHeaderAndExecuteTx` call fails the `msg.sender == keeper` check. This
/// is the only change from the vulnerable variant; honest unlock messages
/// (which target LockProxy, not ECCD) still execute.
contract EthCrossChainManager {
    EthCrossChainData public immutable eccd;

    constructor(address eccd_) {
        eccd = EthCrossChainData(eccd_);
    }

    function verifyHeaderAndExecuteTx(
        address toContract,
        string calldata method,
        bytes calldata args,
        address fromContract
    ) external {
        require(msg.sender == eccd.keeper(), "not current keeper");
        require(toContract != address(eccd), "forbidden target"); // PATCH
        bytes4 sel = bytes4(keccak256(bytes(method)));
        (bool ok, ) = toContract.call(abi.encodePacked(sel, args, abi.encode(fromContract)));
        require(ok, "cross-chain exec failed");
    }
}
