// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "../../../_official_common/OfficialToken.sol";

/// Ethereum mainchain gateway (withdrawal side) of the Ronin bridge.
///
/// August 2024 root cause: the upgrade added two initializers, initializeV3 and
/// initializeV4. initializeV3 sets `totalOperatorWeight` (the sum of the bridge
/// operators' voting weights); the withdrawal threshold is a percentage of it.
/// The deployer ran ONLY initializeV4, so `totalOperatorWeight` stayed 0,
/// `minimumVoteWeight()` evaluated to 0, and a withdrawal passed the vote check
/// with no operator approvals at all. An attacker could withdraw the reserve by
/// submitting a withdrawal with an empty signer set.
///
/// The defect was in the deployment procedure, not the contract logic. The
/// official harness runs one shared `setup` for both variants, so this fixture
/// encodes the mistake in `setup` (only initializeV4 is called) and the
/// VULNERABLE finalizer leaves the weight uninitialised; the patched finalizer
/// performs the initializeV3 weight-initialisation that the real fix restored.
contract RoninGatewayV3 {
    OfficialToken public token;
    address public admin;
    uint256 public totalOperatorWeight;   // _totalOperatorWeight (set by initializeV3)
    uint256 public numerator;             // threshold numerator  (70%)
    uint256 public denominator;           // threshold denominator (100)
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

    /// Sets the operator weight total. In the incident this was NOT run.
    function initializeV3() public {
        require(msg.sender == admin, "!admin");
        require(!v3, "v3");
        v3 = true;
        totalOperatorWeight = 100; // sum of bridge-operator voting weights
    }

    /// The only initializer the deployer actually ran during the upgrade.
    function initializeV4() public {
        require(msg.sender == admin, "!admin");
        require(!v4, "v4");
        v4 = true;
        // VULNERABLE: totalOperatorWeight was supposed to be set by initializeV3,
        // which was never called, so it remains 0.
    }

    /// ceil(totalOperatorWeight * numerator / denominator). Zero when the weight
    /// was never initialised.
    function minimumVoteWeight() public view returns (uint256) {
        return (totalOperatorWeight * numerator + denominator - 1) / denominator;
    }

    /// Withdraw bridged funds. Accepted when the summed weight of the provided
    /// operator signers meets the threshold. With totalOperatorWeight == 0 the
    /// threshold is 0 and an empty signer set passes.
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
