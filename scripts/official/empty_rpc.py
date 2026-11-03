#!/usr/bin/env python3
"""Minimal JSON-RPC endpoint that serves an EMPTY chain state at any block.

Used to run BridgeSentry's dual-EVM harness offline: revm's EthersDB asks this
server for balances/code/storage (all empty), while the benchmark's fixture
contracts are compiled and deployed locally by the fuzzer itself
(compile-and-deploy mode). No mainnet state is available, so this is a
"local fixture execution" setting, not a mainnet-fork replay.

Usage: empty_rpc.py <port> [timestamp]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
TS = int(sys.argv[2]) if len(sys.argv) > 2 else 1659312000
ZERO32 = "0x" + "00" * 32


def block(num_hex):
    try:
        n = int(num_hex, 16)
    except Exception:
        n = 1
    return {
        "number": hex(n),
        "hash": "0x" + format(n, "064x"),
        "parentHash": ZERO32,
        "nonce": "0x0000000000000000",
        "sha3Uncles": ZERO32,
        "logsBloom": "0x" + "00" * 256,
        "transactionsRoot": ZERO32,
        "stateRoot": ZERO32,
        "receiptsRoot": ZERO32,
        "miner": "0x" + "00" * 20,
        "difficulty": "0x0",
        "totalDifficulty": "0x0",
        "extraData": "0x",
        "size": "0x0",
        "gasLimit": hex(30_000_000),
        "gasUsed": "0x0",
        "timestamp": hex(TS),
        "transactions": [],
        "uncles": [],
        "baseFeePerGas": "0x1",
        "mixHash": ZERO32,
    }


def answer(method, params):
    if method == "eth_chainId":
        return "0x1"
    if method == "net_version":
        return "1"
    if method == "eth_blockNumber":
        return hex(30_000_000)
    if method in ("eth_getBalance", "eth_getTransactionCount"):
        return "0x0"
    if method == "eth_getCode":
        return "0x"
    if method == "eth_getStorageAt":
        return ZERO32
    if method == "eth_getBlockByNumber":
        return block(params[0] if params else "0x1")
    if method == "eth_getBlockByHash":
        return block("0x1")
    if method == "eth_gasPrice":
        return "0x1"
    return None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        reqs = body if isinstance(body, list) else [body]
        out = [{"jsonrpc": "2.0", "id": r.get("id"),
                "result": answer(r.get("method"), r.get("params", []))} for r in reqs]
        data = json.dumps(out if isinstance(body, list) else out[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
