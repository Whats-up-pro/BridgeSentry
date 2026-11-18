"""Program grounding for Module 2: what an unprivileged adversary can see of a
deployed bridge, rendered as LLM context.

Grounded seed generation gives the LLM the same view of a fixture that an
attacker has of a deployed bridge, and nothing more:

* the Solidity source of the deployed contracts with every comment and NatSpec
  block removed (fixture sources carry comments that describe the root cause,
  e.g. ``// VULNERABLE: ...``, so raw sources would leak the answer);
* the compiled ABI of every deployed contract (exact callable signatures);
* the deployment (contract instance names, their type and chain);
* the relay rule (which source-chain event the bridge's honest relayer delivers
  to which destination function) -- protocol documentation, not the flaw;
* the public transactions that set up the state before the attack.

Deliberately NOT exposed: the fixture's ``notes``, ``release_entrypoints``,
``victims`` and ``variants`` entries, README files, tests, the patched variant,
and directory names (``vulnerable/``). The incident's documented root cause can
reach the model only through retrieval, which the holdout regimes control.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# dual_evm.rs::default_caller() -- the address the official harness uses as the
# adversary (official_mode.rs::attacker()).
ATTACKER_ADDRESS = "0x0000000000000000000000000000000000000001"

_IMPORT_RE = re.compile(r'import\s+(?:[^;"\']*?\s+from\s+)?["\']([^"\']+)["\']\s*;')
_DEPLOY_LOG_RE = re.compile(r"^(?P<name>[^=]+)=(?P<addr>0x[0-9a-fA-F]{40})@(?P<side>source|dest)\s+\((?P<contract>[^)]+)\)$")


# --------------------------------------------------------------------------
# Comment removal
# --------------------------------------------------------------------------

def strip_solidity_comments(src: str) -> str:
    """Remove ``//`` and ``/* */`` comments (incl. NatSpec) outside string literals.

    A small lexer: string literals (``"..."`` / ``'...'`` with backslash escapes,
    which also covers ``unicode"..."`` and ``hex"..."``) are copied verbatim; a
    block comment is replaced by one space so adjacent tokens never merge.
    Trailing whitespace is trimmed and runs of blank lines collapse to one.
    """
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c in ('"', "'"):
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if src[j] == "\n":  # unterminated literal: stop at end of line
                    break
                j += 1
            out.append(src[i:min(j + 1, n)])
            i = j + 1
        elif c == "/" and nxt == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j  # keep the newline itself
        elif c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        else:
            out.append(c)
            i += 1
    lines = [ln.rstrip() for ln in "".join(out).split("\n")]
    cleaned: list[str] = []
    for ln in lines:
        if not ln.strip():
            if cleaned and cleaned[-1] == "":
                continue
            cleaned.append("")
        else:
            cleaned.append(ln)
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def _resolve_imports(sol: Path) -> list[Path]:
    deps = []
    for rel in _IMPORT_RE.findall(sol.read_text(encoding="utf-8")):
        if rel.startswith("."):
            p = (sol.parent / rel).resolve()
            if p.is_file():
                deps.append(p)
    return deps


def source_closure(contracts_dir: Path) -> list[Path]:
    """The fixture's .sol files plus every file they import (relative imports)."""
    seen: dict[Path, None] = {}
    stack = sorted(p.resolve() for p in Path(contracts_dir).glob("*.sol"))
    while stack:
        p = stack.pop(0)
        if p in seen:
            continue
        seen[p] = None
        stack.extend(d for d in _resolve_imports(p) if d not in seen)
    return list(seen)


def write_sanitized_tree(contracts_dir: Path, out_root: Path) -> list[Path]:
    """Write comment-free copies of the fixture sources for Module 1.

    The copies keep the relative layout (so relative imports still resolve for
    Slither/solc) but the fixture directory is renamed to ``contracts`` so that no
    path mentions ``vulnerable``. Returns the copies of the fixture's own files.
    """
    contracts_dir = Path(contracts_dir).resolve()
    bench_root = contracts_dir.parents[2]          # .../benchmarks
    own = {p.resolve() for p in contracts_dir.glob("*.sol")}
    written: list[Path] = []
    for p in source_closure(contracts_dir):
        rel = p.relative_to(bench_root)
        parts = list(rel.parts)
        if p in own:
            parts[-2] = "contracts"
        dst = Path(out_root) / "benchmarks" / Path(*parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(strip_solidity_comments(p.read_text(encoding="utf-8")), encoding="utf-8")
        if p in own:
            written.append(dst)
    return sorted(written)


# --------------------------------------------------------------------------
# ABI compilation and deployment
# --------------------------------------------------------------------------

def compile_abis(contracts_dir: Path, repo_root: Path, solc: str = "solc") -> dict[str, list[dict]]:
    """ABI of every contract defined in the fixture's sources (``solc --combined-json abi``)."""
    sols = sorted(str(p) for p in Path(contracts_dir).glob("*.sol"))
    r = subprocess.run(
        [solc, "--combined-json", "abi", "--base-path", str(repo_root), "--allow-paths", str(repo_root), *sols],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"solc failed for {contracts_dir}: {r.stderr[:800]}")
    out: dict[str, list[dict]] = {}
    for key, v in json.loads(r.stdout)["contracts"].items():
        abi = v["abi"] if isinstance(v["abi"], list) else json.loads(v["abi"])
        out[key.split(":")[-1]] = abi
    return out


def parse_deploy_log(lines: list[str]) -> dict[str, dict[str, str]]:
    """``['SrcFEG=0x9B13…@source (OfficialToken)', …]`` -> {name: {address, side, contract}}."""
    out = {}
    for ln in lines:
        m = _DEPLOY_LOG_RE.match(ln.strip())
        if not m:
            raise ValueError(f"unrecognised deploy_log line: {ln!r}")
        out[m["name"]] = {"address": m["addr"], "side": m["side"], "contract": m["contract"]}
    return out


def canonical_type(inp: dict) -> str:
    """ABI input -> canonical type string, expanding tuples: ``(address,uint256)[]``."""
    t = inp["type"]
    if t.startswith("tuple"):
        inner = ",".join(canonical_type(c) for c in inp.get("components", []))
        return f"({inner}){t[len('tuple'):]}"
    return t


def signature(fn: dict, with_names: bool = False) -> str:
    if with_names:
        args = ", ".join(f"{canonical_type(p)} {p.get('name') or '_'}" for p in fn["inputs"])
    else:
        args = ",".join(canonical_type(p) for p in fn["inputs"])
    return f"{fn['name']}({args})"


def callable_functions(abi: list[dict]) -> list[dict]:
    return [f for f in abi if f.get("type") == "function" and f.get("stateMutability") not in ("view", "pure")]


# --------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------

def _render_value(v: Any) -> str:
    if isinstance(v, str) and v.startswith("$"):
        return v[1:]
    return json.dumps(v) if not isinstance(v, str) else v


@dataclass
class GroundingContext:
    """Everything the grounded prompt and the seed compiler know about a fixture."""

    bench: str
    deployed: list[dict[str, str]]                 # [{name, contract, side, address}]
    abis: dict[str, list[dict]]                     # deployed name -> ABI
    sources: dict[str, str]                         # file name -> comment-free source
    relay_rules: list[str]
    history: list[str]
    attacker: str = ATTACKER_ADDRESS
    deploy_log_source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    # ---- lookups used by the seed compiler ----
    def address_of(self, name: str) -> str | None:
        for d in self.deployed:
            if d["name"] == name:
                return d["address"]
        return None

    def instance(self, name: str) -> dict[str, str] | None:
        key = re.sub(r"[^0-9a-z]", "", name.lower())
        for d in self.deployed:
            if re.sub(r"[^0-9a-z]", "", d["name"].lower()) == key:
                return d
        return None

    # ---- provenance ----
    def provenance(self) -> dict[str, Any]:
        def sha(obj: Any) -> str:
            return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return {
            "sanitized_sources_sha256": sha(self.sources),
            "abi_sha256": sha(self.abis),
            "deployed": self.deployed,
            "deploy_log_source": self.deploy_log_source,
            "relay_rules": self.relay_rules,
            "history_lines": len(self.history),
            "attacker": self.attacker,
            "exposed": ["comment-free sources", "ABI", "deployment", "relay rule", "pre-attack transactions"],
            "withheld": ["spec.notes", "spec.release_entrypoints", "spec.victims", "patched variant",
                         "README", "tests", "directory names"],
        }

    # ---- prompt block ----
    def prompt_block(self) -> str:
        parts = ["## Deployed contracts (instance name: contract type, chain)"]
        for d in self.deployed:
            chain = "source chain" if d["side"] == "source" else "destination chain"
            parts.append(f"- {d['name']}: {d['contract']}, {chain}")
        parts.append("\n## Relay (operated honestly by the bridge; you cannot control, forge or replay it)")
        parts.extend(f"- {r}" for r in self.relay_rules)
        parts.append("\n## Public transactions executed before the attack")
        parts.extend(f"- {h}" for h in self.history)
        parts.append("\n## Callable functions (exact signatures; use these verbatim)")
        for d in self.deployed:
            for f in callable_functions(self.abis[d["name"]]):
                pay = " payable" if f.get("stateMutability") == "payable" else ""
                parts.append(f"- {d['name']}.{signature(f, with_names=True)}{pay}")
        parts.append("\n## Source code (comments removed)")
        for fname, text in self.sources.items():
            parts.append(f"### {fname}\n```solidity\n{text}```")
        return "\n".join(parts)


def build_context(
    bench: str,
    contracts_dir: Path,
    spec_path: Path,
    deploy_log: list[str],
    repo_root: Path,
    deploy_log_source: str = "",
    solc: str = "solc",
) -> GroundingContext:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    by_type = compile_abis(contracts_dir, repo_root, solc=solc)
    addrs = parse_deploy_log(deploy_log)

    deployed, abis = [], {}
    for d in spec["deploy"]:
        name, ctype = d["name"], d["contract"]
        if name not in addrs:
            raise ValueError(f"{bench}: deployed instance {name} missing from deploy_log")
        if ctype not in by_type:
            raise ValueError(f"{bench}: no ABI for contract type {ctype}")
        deployed.append({"name": name, "contract": ctype, "side": d["side"], "address": addrs[name]["address"]})
        abis[name] = by_type[ctype]

    sides = {d["name"]: d["side"] for d in deployed}
    relay_rules = []
    for r in spec.get("relay", []):
        args = ", ".join(a.replace("ev:", "event.") for a in r.get("args", []))
        relay_rules.append(
            f"When {r['emitter']} ({'source' if sides.get(r['emitter']) == 'source' else 'destination'} chain) "
            f"emits {r['event']}, the relayer calls {r['to']}.{r['fn']}({args}) on the "
            f"{'destination' if sides.get(r['to']) == 'dest' else 'source'} chain."
        )

    history = []
    for s in spec.get("setup", []):
        args = ", ".join(_render_value(a) for a in s.get("args", []))
        history.append(f"{_render_value(s.get('from', 'deployer'))}: {_render_value(s['to'])}.{s['fn']}({args})")

    sources = {}
    for p in source_closure(Path(contracts_dir)):
        sources[p.name] = strip_solidity_comments(p.read_text(encoding="utf-8"))

    return GroundingContext(
        bench=bench, deployed=deployed, abis=abis, sources=sources,
        relay_rules=relay_rules, history=history, deploy_log_source=deploy_log_source,
    )
