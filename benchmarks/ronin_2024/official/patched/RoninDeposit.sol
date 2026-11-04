// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Ronin-chain deposit side: locks tokens that back withdrawals on the Ethereum
/// mainchain gateway. Honest users deposit here; bridge operators then attest
/// the corresponding mainchain withdrawal.
contract RoninDeposit {
    OfficialToken public immutable token;
    uint256 public totalLocked;

    event Deposited(address indexed from, uint256 amount);

    constructor(address token_) {
        token = OfficialToken(token_);
    }

    function deposit(uint256 amount) external {
        require(amount > 0, "zero");
        token.transferFrom(msg.sender, address(this), amount);
        totalLocked += amount;
        emit Deposited(msg.sender, amount);
    }
}
