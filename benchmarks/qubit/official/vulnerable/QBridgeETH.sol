// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Source-chain QBridge (Ethereum). Root cause of the January 2022 incident:
/// the deposit path accepted token == address(0) (native ETH) without checking
/// that ETH was actually sent, yet emitted a Deposit event for `amount`, which
/// the relayer turned into an xQubit mint on BSC.
contract QBridgeETH {
    address public constant NATIVE = address(0);
    uint64 public nonce;
    uint256 public totalLocked;

    event Deposit(address indexed token, uint256 amount, address indexed recipient, uint64 nonce);

    function deposit(address token, uint256 amount, address recipient) external payable {
        require(amount > 0, "zero");
        if (token == NATIVE) {
            // VULNERABLE: legacy native path, msg.value is never compared with amount
            totalLocked += msg.value;
        } else {
            OfficialToken(token).transferFrom(msg.sender, address(this), amount);
            totalLocked += amount;
        }
        nonce += 1;
        emit Deposit(token, amount, recipient, nonce);
    }
}
