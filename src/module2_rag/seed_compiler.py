"""Compile typed LLM attack actions into seeds the official harness can execute.

The official harness (``official_mode.rs::llm_seeds``) resolves an action by the
contract instance name and the function NAME, then fills each ABI parameter by
looking up an LLM ``params`` key equal to the ABI parameter NAME; values must be
literals it can parse (``literal_token``): decimal/e-notation integers, ``0x``
hex for ``bytes``/``bytesN``, JSON arrays for arrays and tuples, plain strings,
and -- for top-level ``address`` parameters only -- ``"attacker"`` or a deployed
instance name. It never ABI-encodes nested ``bytes`` payloads.

This module therefore does, on the Python side and before fuzzing:

* validate every action against the fixture's deployment and ABI (instance
  exists, function exists and is state-changing, arity and value types match);
* ABI-encode structured ``bytes`` arguments (``{"abi_encode": ...}``,
  ``{"abi_encode_call": ...}``, ``{"abi_encode_packed": ...}``) with the real
  deployed addresses and the harness's adversary address;
* emit ``params`` keyed by the exact ABI parameter names, in literal forms the
  harness parses.

The fuzzer binary is unchanged. Validation errors are returned as plain
messages so the generator can ask the LLM to repair its scenario.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from eth_abi import encode as abi_encode
from eth_abi.packed import encode_packed
from eth_hash.auto import keccak

from .grounding import GroundingContext, callable_functions, canonical_type, signature

_UINT_RE = re.compile(r"^u?int(\d*)$")
_BYTESN_RE = re.compile(r"^bytes(\d+)$")
_HEX_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class ValueError_(ValueError):
    """A value that cannot be converted to the requested ABI type."""


def parse_int(v: Any) -> int:
    """Integers as the harness reads them: int, decimal, 0x-hex, ``5e18``, ``1.5e18``, ``1_000``."""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if not isinstance(v, str):
        raise ValueError_(f"expected an integer, got {v!r}")
    t = v.strip().replace("_", "").replace(",", "")
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if t.lower().startswith("0x"):
        return sign * int(t, 16)
    m = re.fullmatch(r"(\d+)(?:\.(\d+))?[eE](\d+)", t)
    if m:
        whole, frac, exp = m.group(1), m.group(2) or "", int(m.group(3))
        if len(frac) > exp:
            raise ValueError_(f"{v!r} is not an integer")
        return sign * int(whole + frac) * 10 ** (exp - len(frac))
    if re.fullmatch(r"\d+", t):
        return sign * int(t)
    raise ValueError_(f"expected an integer, got {v!r}")


def _array_parts(t: str) -> tuple[str, str] | None:
    """``uint256[2][]`` -> (``uint256[2]``, ``""``); ``(address,uint256)[]`` -> (``(address,uint256)``, ``""``)."""
    if not t.endswith("]"):
        return None
    i = t.rfind("[")
    return t[:i], t[i + 1:-1]


def _split_tuple(t: str) -> list[str]:
    assert t.startswith("(") and t.endswith(")")
    inner, parts, depth, cur = t[1:-1], [], 0, ""
    for ch in inner:
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        depth += ch == "("
        depth -= ch == ")"
        cur += ch
    if cur:
        parts.append(cur)
    return parts


@dataclass
class Compiled:
    """One compiled action, or the reasons it could not be compiled."""

    action: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)


class SeedCompiler:
    def __init__(self, ctx: GroundingContext):
        self.ctx = ctx

    # ------------------------------------------------------------- addresses
    def _address(self, v: Any, top_level: bool) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError_(f"expected an address, got {v!r}")
        s = v.strip()
        low = s.lower()
        if low in {"attacker", "adversary", "self", "me", "msg.sender"} or "attacker" in low:
            return "attacker" if top_level else self.ctx.attacker
        inst = self.ctx.instance(s)
        if inst is not None:
            return inst["name"] if top_level else inst["address"]
        if _HEX_ADDR_RE.match(s):
            return s
        raise ValueError_(
            f"address {v!r} is neither \"attacker\", a deployed instance "
            f"({', '.join(d['name'] for d in self.ctx.deployed)}), nor a 0x-hex address"
        )

    # ------------------------------------------------------- native (encode)
    def native(self, t: str, v: Any) -> Any:
        """Python value for eth_abi encoding of type ``t`` (addresses resolved to hex)."""
        arr = _array_parts(t)
        if arr:
            base, n = arr
            if not isinstance(v, list):
                raise ValueError_(f"expected a JSON array for {t}, got {v!r}")
            if n and len(v) != int(n):
                raise ValueError_(f"{t} needs exactly {n} elements, got {len(v)}")
            return [self.native(base, x) for x in v]
        if t.startswith("("):
            comps = _split_tuple(t)
            if not isinstance(v, list) or len(v) != len(comps):
                raise ValueError_(f"expected a JSON array of {len(comps)} values for tuple {t}, got {v!r}")
            return tuple(self.native(c, x) for c, x in zip(comps, v))
        if t == "address":
            return self._address(v, top_level=False)
        if _UINT_RE.match(t):
            x = parse_int(v)
            bits = int(_UINT_RE.match(t).group(1) or 256)
            if t.startswith("uint") and not (0 <= x < 2 ** bits):
                raise ValueError_(f"{v!r} out of range for {t}")
            if t.startswith("int") and not (-(2 ** (bits - 1)) <= x < 2 ** (bits - 1)):
                raise ValueError_(f"{v!r} out of range for {t}")
            return x
        if t == "bool":
            if isinstance(v, bool):
                return v
            if isinstance(v, str) and v.lower() in {"true", "false"}:
                return v.lower() == "true"
            raise ValueError_(f"expected true/false, got {v!r}")
        if t == "string":
            if not isinstance(v, str):
                raise ValueError_(f"expected a string, got {v!r}")
            return v
        if t == "bytes":
            return bytes.fromhex(self.bytes_hex(v)[2:])
        m = _BYTESN_RE.match(t)
        if m:
            n = int(m.group(1))
            return self._fixed_bytes(v, n)
        raise ValueError_(f"unsupported ABI type {t}")

    def _fixed_bytes(self, v: Any, n: int) -> bytes:
        if isinstance(v, int) or (isinstance(v, str) and not v.startswith("0x")):
            x = parse_int(v)
            return x.to_bytes(n, "big")
        if isinstance(v, str) and v.startswith("0x"):
            b = bytes.fromhex(v[2:] if len(v) % 2 == 0 else "0" + v[2:])
            if len(b) > n:
                raise ValueError_(f"{v!r} is longer than bytes{n}")
            return b.rjust(n, b"\0")  # the harness left-pads (official_mode.rs literal_token)
        raise ValueError_(f"expected 0x-hex for bytes{n}, got {v!r}")

    # ------------------------------------------------------------ bytes args
    def bytes_hex(self, v: Any) -> str:
        if isinstance(v, str):
            s = v.strip()
            if re.fullmatch(r"0x([0-9a-fA-F]{2})*", s):
                return s.lower()
            raise ValueError_(
                f"bytes value {v!r} is not 0x-hex; use {{\"abi_encode\": {{\"types\": [...], \"values\": [...]}}}}"
            )
        if isinstance(v, dict) and len(v) == 1:
            (kind, spec), = v.items()
            if not isinstance(spec, dict):
                raise ValueError_(f"{kind} needs an object with types/values")
            if kind in ("abi_encode", "abi_encode_packed"):
                types, values = spec.get("types"), spec.get("values")
                if not isinstance(types, list) or not isinstance(values, list) or len(types) != len(values):
                    raise ValueError_(f"{kind} needs equally long 'types' and 'values' lists")
                natives = [self.native(t, x) for t, x in zip(types, values)]
                data = abi_encode(types, natives) if kind == "abi_encode" else encode_packed(types, natives)
                return "0x" + data.hex()
            if kind == "abi_encode_call":
                sig, values = spec.get("signature"), spec.get("values")
                if not isinstance(sig, str) or "(" not in sig or not isinstance(values, list):
                    raise ValueError_("abi_encode_call needs 'signature' like f(uint256,address) and 'values'")
                name, _, rest = sig.partition("(")
                types = _split_tuple("(" + rest) if rest.rstrip(")") else []
                types = [t.strip().split(" ")[0] for t in types]
                if len(types) != len(values):
                    raise ValueError_(f"abi_encode_call {sig}: {len(types)} types but {len(values)} values")
                canon = f"{name.strip()}({','.join(types)})"
                natives = [self.native(t, x) for t, x in zip(types, values)]
                return "0x" + (keccak(canon.encode())[:4] + abi_encode(types, natives)).hex()
        raise ValueError_(
            f"bytes value {v!r} must be 0x-hex or one of abi_encode / abi_encode_call / abi_encode_packed"
        )

    # ------------------------------------------------------ harness literals
    def literal(self, t: str, v: Any, top_level: bool) -> Any:
        """JSON value in the form official_mode.rs literal_token / llm_value_token parses."""
        arr = _array_parts(t)
        if arr:
            base, n = arr
            if not isinstance(v, list):
                raise ValueError_(f"expected a JSON array for {t}, got {v!r}")
            if n and len(v) != int(n):
                raise ValueError_(f"{t} needs exactly {n} elements, got {len(v)}")
            return [self.literal(base, x, top_level=False) for x in v]
        if t.startswith("("):
            comps = _split_tuple(t)
            if not isinstance(v, list) or len(v) != len(comps):
                raise ValueError_(f"expected a JSON array of {len(comps)} values for tuple {t}, got {v!r}")
            return [self.literal(c, x, top_level=False) for c, x in zip(comps, v)]
        if t == "address":
            return self._address(v, top_level=top_level)
        if _UINT_RE.match(t):
            x = self.native(t, v)
            if x < 0:
                raise ValueError_(f"negative integers are not supported by the harness ({v!r})")
            return str(x)
        if t == "bool":
            return self.native(t, v)
        if t == "string":
            return self.native(t, v)
        if t == "bytes":
            return self.bytes_hex(v)
        m = _BYTESN_RE.match(t)
        if m:
            return "0x" + self._fixed_bytes(v, int(m.group(1))).hex()
        raise ValueError_(f"unsupported ABI type {t}")

    # --------------------------------------------------------------- actions
    def compile_action(self, a: Any, step: int, label: int | None = None) -> Compiled:
        where = f"action {label if label is not None else step}"
        if not isinstance(a, dict):
            return Compiled(None, [f"{where}: not a JSON object"])
        cname, fname = a.get("contract"), a.get("function")
        if not isinstance(cname, str) or not isinstance(fname, str):
            return Compiled(None, [f"{where}: needs string fields 'contract' and 'function'"])
        inst = self.ctx.instance(cname)
        if inst is None:
            return Compiled(None, [
                f"{where}: unknown contract {cname!r}; deployed instances are "
                + ", ".join(d["name"] for d in self.ctx.deployed)
            ])
        abi = self.ctx.abis[inst["name"]]
        fn_name = fname.split("(")[0].split(".")[-1].strip()
        avail = callable_functions(abi)
        matches = [f for f in avail if f["name"] == fn_name]
        if not matches:
            ro = [f for f in abi if f.get("type") == "function" and f["name"] == fn_name]
            why = "is read-only (view/pure)" if ro else "does not exist"
            return Compiled(None, [
                f"{where}: {inst['name']}.{fn_name} {why}; callable functions of {inst['name']}: "
                + "; ".join(signature(f) for f in avail)
            ])
        if len(matches) > 1:
            return Compiled(None, [f"{where}: {inst['name']}.{fn_name} is overloaded, which the harness cannot select"])
        fn = matches[0]
        # No fixture overloads a function, so the name selects it; the written
        # parameter list is not compared (arity and every value are checked below).
        types = [canonical_type(p) for p in fn["inputs"]]
        if any(not p.get("name") for p in fn["inputs"]):
            return Compiled(None, [f"{where}: {signature(fn)} has unnamed parameters, which the harness cannot fill"])

        raw = a.get("args", a.get("params", []))
        if isinstance(raw, dict):
            missing = [p["name"] for p in fn["inputs"] if p["name"] not in raw]
            if missing:
                return Compiled(None, [f"{where}: missing arguments {missing} for {signature(fn, True)}"])
            values = [raw[p["name"]] for p in fn["inputs"]]
        elif isinstance(raw, list):
            values = raw
        else:
            return Compiled(None, [f"{where}: 'args' must be a JSON array of positional values"])
        if len(values) != len(types):
            return Compiled(None, [
                f"{where}: {signature(fn, True)} takes {len(types)} arguments, got {len(values)}"
            ])

        params, errors = {}, []
        for p, t, v in zip(fn["inputs"], types, values):
            try:
                params[p["name"]] = self.literal(t, v, top_level=True)
            except (ValueError_, ValueError, TypeError, OverflowError) as exc:
                errors.append(f"{where}: argument {p['name']} ({t}): {exc}")
        if errors:
            return Compiled(None, errors)
        return Compiled({
            "step": step,
            "chain": "source" if inst["side"] == "source" else "destination",
            "contract": inst["name"],
            "function": signature(fn),
            "params": params,
            "description": str(a.get("description") or f"Step {step}"),
        })

    def compile_actions(self, actions: Any) -> tuple[list[dict[str, Any]], list[str]]:
        """Compile a list of actions; returns (valid compiled actions, all error messages)."""
        if not isinstance(actions, list) or not actions:
            return [], ["'actions' must be a non-empty JSON array"]
        out, errors = [], []
        for i, a in enumerate(actions, start=1):
            c = self.compile_action(a, step=len(out) + 1, label=i)
            if c.action is None:
                errors.extend(c.errors)
            else:
                out.append(c.action)
        return out, errors
