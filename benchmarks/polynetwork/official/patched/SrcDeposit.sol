// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";
import "./SourceCrossChain.sol";

/// Source-chain lock proxy (the registered paired proxy). An honest user locks
/// tokens here; it emits a cross-chain unlock message whose sender is this
/// contract, so the destination LockProxy's registeredProxy check passes.
contract SrcDeposit {
    OfficialToken public immutable token;
    SourceCrossChain public immutable ccm;
    address public destLockProxy;

    constructor(address token_, address ccm_, address destLockProxy_) {
        token = OfficialToken(token_);
        ccm = SourceCrossChain(ccm_);
        destLockProxy = destLockProxy_;
    }

    function deposit(address recipient, uint256 amount) external {
        require(amount > 0, "zero");
        token.transferFrom(msg.sender, address(this), amount);
        bytes memory args = abi.encode(recipient, amount);
        ccm.crossChain(destLockProxy, "unlock(address,uint256)", args);
    }
}
