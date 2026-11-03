// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Minimal ERC-20 with an owner-assigned minter. Used by the Option-A
/// official fixtures so that minting is never permissionless: only the
/// bridge contract (or the deployer during pre-incident setup) can mint.
contract OfficialToken {
    string public name;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    address public owner;
    mapping(address => bool) public minter;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory name_) {
        name = name_;
        owner = msg.sender;
        minter[msg.sender] = true;
    }

    function setMinter(address m, bool allowed) external {
        require(msg.sender == owner, "not owner");
        minter[m] = allowed;
    }

    function mint(address to, uint256 amount) external {
        require(minter[msg.sender], "not minter");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _move(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 a = allowance[from][msg.sender];
        require(a >= amount, "allowance");
        allowance[from][msg.sender] = a - amount;
        _move(from, to, amount);
        return true;
    }

    function _move(address from, address to, uint256 amount) internal {
        require(balanceOf[from] >= amount, "balance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
