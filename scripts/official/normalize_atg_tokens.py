#!/usr/bin/env python3
"""Replace ``edges[].token: null`` with ``"UNKNOWN"`` in generated ``atg.json`` files.

Seed sets generated before the ATG builder fix (edge fields now follow the
nodes' ``or default`` rule) can carry ``"token": null``. The Rust fuzzer's
``AtgEdge.token`` is a required string, as in ``schemas/atg.schema.json``, so
such an ``atg.json`` does not parse and the run fails before fuzzing.

Only that one field is changed, to the builder's own default ``"UNKNOWN"``; the
scenarios in ``hypotheses.json`` are not touched. The official oracle does not
read the ATG. Each changed seed set records the change in ``provenance.json``
under ``atg_postprocess``. Running the script twice changes nothing.

Usage: python3 scripts/official/normalize_atg_tokens.py <seed_dir> [<seed_dir> ...]
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import sys


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalize(seed_dir: pathlib.Path) -> int:
    atg_p = seed_dir / "atg.json"
    atg = json.loads(atg_p.read_text(encoding="utf-8"))
    n = 0
    for edge in atg.get("edges", []):
        if edge.get("token", "") is None:
            edge["token"] = "UNKNOWN"
            n += 1
    if n == 0:
        return 0
    before = _sha(atg_p)
    atg_p.write_text(json.dumps(atg, ensure_ascii=False, indent=2), encoding="utf-8")
    prov_p = seed_dir / "provenance.json"
    prov = json.loads(prov_p.read_text(encoding="utf-8"))
    prov["atg_postprocess"] = {
        "edges_token_null_to_UNKNOWN": n,
        "atg_sha256_before": before,
        "atg_sha256_after": _sha(atg_p),
        "tool": "scripts/official/normalize_atg_tokens.py",
        "applied_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "reason": "Rust AtgEdge.token is a required string; atg_builder emitted null "
                  "for LLM edges without a token (fixed in the builder afterwards)",
    }
    prov_p.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    total = 0
    for d in argv:
        n = normalize(pathlib.Path(d))
        total += n
        print(f"{d}: {n} token null -> UNKNOWN")
    print(f"total edges changed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
