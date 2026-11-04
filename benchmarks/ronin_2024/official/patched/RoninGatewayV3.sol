// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Ethereum mainchain gateway (withdrawal side) of the Ronin bridge.
///
/// Patched: Ronin's fix was to run the missing initializeV3 so that
/// `totalOperatorWeight` is set during the upgrade. Because the official
/// harness runs one shared `setup` (which calls only initializeV4), this
/// variant encodes the fix by having initializeV4 run the initializeV3
/// weight-initialisation. With the weight set, `minimumVoteWeight()` is the
/// real 70% threshold, so a withdrawal with no operator votes is rejected.
/// This is the only change from the vulnerable variant.
contract RoninGatewayV3 {
    OfficialToken public token;
    address public admin;
    uint256 public totalOperatorWeight;
    uint256 public numerator;
    uint256 public denominator;
    mapping(address => uint256) public operatorWeight;
    bool public v3;
    bool public v4;

    event Withdrew(address indexed recipient, uint256 amount);

    constructor(address token_) {
        token = OfficialToken(token_);
        admin = msg.sender;
        numerator = 70;
        denominator = 100;
    }

    function initializeV3() public {
        require(msg.sender == admin, "!admin");
        require(!v3, "v3");
        v3 = true;
        totalOperatorWeight = 100;
    }

    function initializeV4() public {
        require(msg.sender == admin, "!admin");
        require(!v4, "v4");
        v4 = true;
        initializeV3(); // PATCH: the upgrade must also run initializeV3
    }

    function minimumVoteWeight() public view returns (uint256) {
        return (totalOperatorWeight * numerator + denominator - 1) / denominator;
    }

    function withdraw(address recipient, uint256 amount, address[] calldata signers) external {
        uint256 w = 0;
        for (uint256 i = 0; i < signers.length; i++) {
            w += operatorWeight[signers[i]];
        }
        require(w >= minimumVoteWeight(), "insufficient vote weight");
        token.transfer(recipient, amount);
        emit Withdrew(recipient, amount);
    }
}
