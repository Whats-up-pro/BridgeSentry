// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./VerusExportSurrogate.sol";
import "./VerusBridge.sol";
contract Inv { OfficialToken public token; address public holder; uint256 public leaked0; constructor(OfficialToken t, address h){ token=t; holder=h; leaked0=t.totalSupply()-t.balanceOf(h); } function invariant_bridgeSafe() public view { require(token.totalSupply()-token.balanceOf(holder) <= leaked0, "drained"); } }
contract Harness {
    bytes32 constant EXPORT_ID = bytes32(uint256(0x0b));
    OfficialToken public srcVRSC; VerusExportSurrogate public exportSrc;
    OfficialToken public dstToken; VerusBridge public bridge; Inv public inv;
    function targetSenders() public pure returns (address[] memory s){ s=new address[](2); s[0]=0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd; s[1]=0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb; }
    function setUp() external {
        srcVRSC = new OfficialToken("VRSC (surrogate)");
        exportSrc = new VerusExportSurrogate(address(srcVRSC));
        dstToken = new OfficialToken("Bridged VRSC (Ethereum)");
        bridge = new VerusBridge(address(dstToken), address(this)); // notary = Harness (non-caller)
        dstToken.mint(address(bridge), 1000000e18);
        bridge.recordExport(EXPORT_ID, 500e18);               // victim's attested export
        bridge.submitImports(address(0xAb01), 500e18, EXPORT_ID); // victim's legit import
        inv = new Inv(dstToken, address(bridge));              // leaked0 = 500e18 (legit baseline)
    }
}
