// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./RoninGatewayV3.sol";
import "./RoninDeposit.sol";

/// Invariant checker deployed by setUp. ItyFuzz registers invariant_ functions
/// and flags a bug when the call REVERTS (Foundry convention).
contract Inv {
    OfficialToken public token; address public holder; uint256 public leaked0;
    constructor(OfficialToken t, address h) { token = t; holder = h; leaked0 = t.totalSupply() - t.balanceOf(h); }
    /// Reverts when bridged value left the holder = net adversary gain (condition (v)).
    function invariant_bridgeSafe() public view {
        require(token.totalSupply() - token.balanceOf(holder) <= leaked0, "drained");
    }
}

contract Harness {
    function targetSenders() public pure returns (address[] memory s) {
        s = new address[](2);
        s[0] = 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd;
        s[1] = 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb;
    }
    OfficialToken public roninToken; RoninDeposit public roninDeposit;
    OfficialToken public ethToken; RoninGatewayV3 public gateway; Inv public inv;
    function setUp() external {
        roninToken = new OfficialToken("Ronin-chain WETH");
        roninDeposit = new RoninDeposit(address(roninToken));
        ethToken = new OfficialToken("Mainchain WETH");
        gateway = new RoninGatewayV3(address(ethToken));
        ethToken.mint(address(gateway), 1000000e18);
        gateway.initializeV4();
        inv = new Inv(ethToken, address(gateway));
    }
}
