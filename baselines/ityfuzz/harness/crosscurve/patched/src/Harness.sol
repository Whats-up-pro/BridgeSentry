// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./AxelarGateway.sol";
import "./PortalSrc.sol";
import "./PortalV2.sol";
import "./ReceiverAxelar.sol";
contract Inv {
    OfficialToken public token; address public holder; uint256 public leaked0;
    constructor(OfficialToken t, address h){ token=t; holder=h; leaked0=t.totalSupply()-t.balanceOf(h); }
    function invariant_bridgeSafe() public view { require(token.totalSupply()-token.balanceOf(holder) <= leaked0, "drained"); }
}
contract Harness {
    address constant RELAYER = address(0xBEEF);
    OfficialToken public srcToken; AxelarGateway public gwSrc; PortalSrc public portalSrc;
    OfficialToken public dstToken; AxelarGateway public gwDst; PortalV2 public portalV2; ReceiverAxelar public receiver; Inv public inv;
    function targetSenders() public pure returns (address[] memory s){ s=new address[](2);
        s[0]=0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd; s[1]=0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb; }
    function setUp() external {
        srcToken = new OfficialToken("CrossCurve LP (source)");
        gwSrc = new AxelarGateway(RELAYER);
        portalSrc = new PortalSrc(address(srcToken), address(gwSrc));
        dstToken = new OfficialToken("CrossCurve LP (dest)");
        gwDst = new AxelarGateway(RELAYER);
        portalV2 = new PortalV2(address(dstToken));
        receiver = new ReceiverAxelar(address(gwDst), address(portalV2), address(portalSrc));
        dstToken.mint(address(portalV2), 1000000e18);
        portalV2.setReceiver(address(receiver));
        inv = new Inv(dstToken, address(portalV2));
    }
}
