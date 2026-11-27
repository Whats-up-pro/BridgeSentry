// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../../_official_common/OfficialToken.sol";

/// Source side of a CORRECT lock->mint bridge (benign hard-negative control).
/// A deposit pulls real tokens from the caller via transferFrom and emits a
/// Deposit event that the faithful relay delivers to the destination release.
/// No function here mints, releases, or returns value without a matching,
/// funded deposit, so an adversary holding only ordinary accounts cannot gain.
contract LockBridge {
    OfficialToken public immutable token;

    event Deposit(address recipient, uint256 amount);

    constructor(address token_) {
        token = OfficialToken(token_);
    }

    function deposit(uint256 amount, address recipient) external {
        require(recipient != address(0), "recipient");
        require(amount > 0, "amount");
        require(token.transferFrom(msg.sender, address(this), amount), "lock");
        emit Deposit(recipient, amount);
    }
}

/// Destination side: release from a pre-funded liquidity pool. Only the bridge
/// relayer may release, and each release pays exactly the delivered amount to
/// its recipient. The adversary is not the relayer, so the only way to receive
/// the wrapped token is through a relayed deposit that first locked an equal
/// amount on the source chain. The paired assets therefore net to zero.
contract MintBridge {
    OfficialToken public immutable token;
    address public immutable relayer;

    constructor(address token_, address relayer_) {
        token = OfficialToken(token_);
        relayer = relayer_;
    }

    function release(address recipient, uint256 amount) external {
        require(msg.sender == relayer, "only relayer");
        require(token.transfer(recipient, amount), "pay");
    }
}
