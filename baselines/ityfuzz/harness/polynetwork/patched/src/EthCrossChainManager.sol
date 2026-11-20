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
///
/// The message's source (`fromContract`) is supplied by the keeper and exposed
/// to the called contract through `fromContractContext()`, NOT appended to the
/// caller-controlled `args`, so a caller cannot smuggle a forged source into a
/// method's positional arguments.
contract EthCrossChainManager {
    EthCrossChainData public immutable eccd;
    address public fromContractContext;

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
        fromContractContext = fromContract;
        (bool ok, ) = toContract.call(abi.encodePacked(sel, args));
        fromContractContext = address(0);
        require(ok, "cross-chain exec failed");
    }
}
