// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "./OfficialToken.sol";
import "./EthCrossChainData.sol";
import "./EthCrossChainManager.sol";
import "./LockProxy.sol";
import "./SourceCrossChain.sol";
import "./SrcDeposit.sol";
contract Inv { OfficialToken public token; address public holder; uint256 public leaked0; constructor(OfficialToken t, address h){ token=t; holder=h; leaked0=t.totalSupply()-t.balanceOf(h); } function invariant_bridgeSafe() public view { require(token.totalSupply()-token.balanceOf(holder) <= leaked0, "drained"); } }
contract Harness {
    address constant RELAYER = address(0xBEEF);
    OfficialToken public ethToken; EthCrossChainData public eccd; LockProxy public lockProxy; EthCrossChainManager public eccm;
    OfficialToken public srcToken; SourceCrossChain public sourceCC; SrcDeposit public srcDeposit; Inv public inv;
    function targetSenders() public pure returns (address[] memory s){ s=new address[](2); s[0]=0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd; s[1]=0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb; }
    function setUp() external {
        ethToken = new OfficialToken("Bridged asset (dest)");
        eccd = new EthCrossChainData();
        lockProxy = new LockProxy(address(ethToken));
        eccm = new EthCrossChainManager(address(eccd));
        srcToken = new OfficialToken("Bridged asset (source)");
        sourceCC = new SourceCrossChain();
        srcDeposit = new SrcDeposit(address(srcToken), address(sourceCC), address(lockProxy));
        ethToken.mint(address(lockProxy), 1000000e18);
        eccd.initKeeper(RELAYER);
        eccd.transferOwnership(address(eccm));
        lockProxy.setManager(address(eccm));
        lockProxy.setRegisteredProxy(address(srcDeposit));
        inv = new Inv(ethToken, address(lockProxy));
    }
}
