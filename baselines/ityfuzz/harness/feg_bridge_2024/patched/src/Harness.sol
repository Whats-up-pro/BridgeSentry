// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./WormholeCore.sol";
import "./FEGBridgeSrc.sol";
import "./FEGSmartBridge.sol";
contract Inv { OfficialToken public token; address public holder; uint256 public leaked0; constructor(OfficialToken t, address h){ token=t; holder=h; leaked0=t.totalSupply()-t.balanceOf(h); } function invariant_bridgeSafe() public view { require(token.totalSupply()-token.balanceOf(holder) <= leaked0, "drained"); } }
contract Harness {
    address constant RELAYER = address(0xBEEF);
    OfficialToken public srcFEG; WormholeCore public core; FEGBridgeSrc public bridgeSrc;
    OfficialToken public dstFEG; FEGSmartBridge public smartBridge; Inv public inv;
    function targetSenders() public pure returns (address[] memory s){ s=new address[](2); s[0]=0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd; s[1]=0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb; }
    function setUp() external {
        dstFEG = new OfficialToken("FEG (dest)");
        smartBridge = new FEGSmartBridge(address(dstFEG), RELAYER);
        srcFEG = new OfficialToken("FEG (source)");
        core = new WormholeCore();
        bridgeSrc = new FEGBridgeSrc(address(srcFEG), address(core));
        dstFEG.mint(address(smartBridge), 1000000e18);   // destination reserve
        smartBridge.setTrusted(address(bridgeSrc), true); // bootstrap legit source
        inv = new Inv(dstFEG, address(smartBridge));
    }
}
