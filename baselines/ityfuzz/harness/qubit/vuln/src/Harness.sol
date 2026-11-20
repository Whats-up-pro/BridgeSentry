// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./QBridgeETH.sol";
import "./QBridgeBSC.sol";
contract Inv { OfficialToken public token; address public holder; uint256 public leaked0; constructor(OfficialToken t, address h){ token=t; holder=h; leaked0=t.totalSupply()-t.balanceOf(h); } function invariant_bridgeSafe() public view { require(token.totalSupply()-token.balanceOf(holder) <= leaked0, "drained"); } }
contract Harness {
    address constant RELAYER = address(0xBEEF);
    OfficialToken public qToken; QBridgeETH public bridgeETH; OfficialToken public xToken; QBridgeBSC public bridgeBSC; Inv public inv;
    function targetSenders() public pure returns (address[] memory s){ s=new address[](2); s[0]=0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd; s[1]=0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb; }
    function setUp() external {
        qToken = new OfficialToken("Qubit (ETH)");
        bridgeETH = new QBridgeETH();
        xToken = new OfficialToken("xQubit (BSC)");
        bridgeBSC = new QBridgeBSC(address(xToken), RELAYER);
        xToken.setMinter(address(bridgeBSC), true);
        qToken.mint(address(0xAb01), 1000e18);
        inv = new Inv(xToken, address(bridgeBSC)); // xQubit minted on exploit; holder holds 0
    }
}
