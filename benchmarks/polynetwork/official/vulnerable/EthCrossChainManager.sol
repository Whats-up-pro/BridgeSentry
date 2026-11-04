// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./EthCrossChainData.sol";

/// EthCrossChainManager (ECCM). Executes a cross-chain message by calling the
/// contract/method named in the message, after checking the message is carried
/// by the current keeper.
///
/// August 2021 root cause: `verifyHeaderAndExecuteTx` placed NO restriction on
/// which contract or method the message could invoke, so a message could target
/// ECCD.putCurEpochConPubKeyBytes (owner-only, and ECCM is the owner) and
/// replace the keeper. The keeper check is modelled as `msg.sender == keeper`:
/// the honest relay submits as the honest keeper; once the keeper is replaced
/// with the attacker, the attacker submits headers themselves — and can set the
/// message's `fromContract` to the registered proxy, which the honest relay
/// would never do (it reports the true source sender).
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
        // VULNERABLE: no restriction on toContract/method — a message may target
        // the privileged ECCD and replace the keeper.
        bytes4 sel = bytes4(keccak256(bytes(method)));
        (bool ok, ) = toContract.call(abi.encodePacked(sel, args, abi.encode(fromContract)));
        require(ok, "cross-chain exec failed");
    }
}
