#!/usr/bin/env python3
"""Tests for diff-contract.py.

A comparison that has never found a difference is a claim, not a guardrail.

The script runs as a subprocess on purpose: that is what a pipeline runs, exit
code included. Every case is the same committed document against a published
one with exactly one thing changed, so a case can only fail for its reason.

Usage:
    python3 engineering/fundamentals/skills/comparing-published-contracts/scripts/test-diff-contract.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "diff-contract.py"

CONTRACT = {
    "openapi": "3.1.0",
    "info": {"title": "Orders", "version": "1.0.0"},
    "paths": {
        "/orders": {
            "get": {
                "operationId": "listOrders",
                "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer", "maximum": 100}}],
                "responses": {"200": {"description": "The orders."}},
            }
        }
    },
    "components": {"schemas": {"Order": {"type": "object", "required": ["order_id", "sku"]}}},
}
COMMITTED = json.dumps(CONTRACT, indent=2)
OPERATION = "/paths/~1orders/get"


def published(change) -> str:
    """The committed document with exactly one thing changed."""
    document = json.loads(COMMITTED)
    change(document)
    return json.dumps(document)


def reorder(value: object) -> object:
    """Every object's keys reversed, at every depth. Arrays keep their order."""
    if isinstance(value, dict):
        return {key: reorder(value[key]) for key in reversed(list(value))}
    if isinstance(value, list):
        return [reorder(item) for item in value]
    return value


def narrow(document: dict) -> None:
    document["paths"]["/orders"]["get"]["parameters"][0]["schema"]["maximum"] = 50


def add_description(document: dict) -> None:
    document["paths"]["/orders"]["get"]["description"] = "Lists them."


def drop_operation(document: dict) -> None:
    del document["paths"]["/orders"]["get"]


def reorder_array(document: dict) -> None:
    document["components"]["schemas"]["Order"]["required"].reverse()


def extend_array(document: dict) -> None:
    document["components"]["schemas"]["Order"]["required"].append("status")


def float_maximum(document: dict) -> None:
    document["paths"]["/orders"]["get"]["parameters"][0]["schema"]["maximum"] = 100.0


def retype(document: dict) -> None:
    document["info"] = "Orders 1.0.0"


def case(name: str, files: dict[str, str], expect: tuple[int, list[str]]) -> tuple:
    return (name, files, expect)


CASES = [
    # covers #12/AC-8
    case(
        "key order and whitespace are not a difference",
        {"committed.json": COMMITTED, "published.json": json.dumps(reorder(CONTRACT), separators=(",", ":"))},
        (0, ["equal after canonical serialisation"]),
    ),
    # covers #12/AC-9, one case per kind of difference
    case(
        "a changed value is named by its JSON Pointer",
        {"committed.json": COMMITTED, "published.json": published(narrow)},
        (1, ["[contract-first]", "condition 2", f"{OPERATION}/parameters/0/schema/maximum: committed 100, published 50", "1 difference(s)"]),
    ),
    case(
        "an addition is a difference: nothing is forgiven",
        {"committed.json": COMMITTED, "published.json": published(add_description)},
        (1, [f"{OPERATION}/description: only in the published description"]),
    ),
    case(
        "a removal is a difference",
        {"committed.json": COMMITTED, "published.json": published(drop_operation)},
        (1, [f"{OPERATION}: only in the committed contract"]),
    ),
    # Pinned: canonical is keys and whitespace. An array's order is content.
    case(
        "an array in a different order is a difference",
        {"committed.json": COMMITTED, "published.json": published(reorder_array)},
        (1, ["/components/schemas/Order/required/0: committed \"order_id\", published \"sku\"", "2 difference(s)"]),
    ),
    case(
        "a longer array is a difference",
        {"committed.json": COMMITTED, "published.json": published(extend_array)},
        (1, ["/components/schemas/Order/required/2: only in the published description"]),
    ),
    # Pinned: the comparison is over bytes, and 100 and 100.0 serialise apart.
    case(
        "an integer against the same number as a float is a difference",
        {"committed.json": COMMITTED, "published.json": published(float_maximum)},
        (1, ["maximum: committed 100, published 100.0"]),
    ),
    case(
        "a value of another type is a difference",
        {"committed.json": COMMITTED, "published.json": published(retype)},
        (1, ["/info: committed {", "published \"Orders 1.0.0\""]),
    ),
    case(
        "a difference at the root is named",
        {"committed.json": COMMITTED, "published.json": "[]"},
        (1, ["/: committed {", "published []"]),
    ),
    # covers #12/AC-10
    case(
        "a YAML document is not compared, and that is not a pass",
        {"committed.json": "openapi: 3.1.0\npaths: {}\n", "published.json": COMMITTED},
        (2, ["committed.json", "not checked: is not JSON", "YAML"]),
    ),
    case(
        "a missing published description is not compared",
        {"committed.json": COMMITTED},
        (2, ["published.json", "not checked: could not be read"]),
    ),
    case(
        "a key written twice in one object is not compared",
        {"committed.json": COMMITTED, "published.json": '{"openapi": "3.1.0", "openapi": "3.0.3"}'},
        (2, ["not checked: the key 'openapi' appears twice"]),
    ),
]


def run(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        for rel, content in files.items():
            (Path(tmp) / rel).write_text(content, encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "committed.json", "published.json"]
        result = subprocess.run(command, capture_output=True, text=True, cwd=tmp)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: tuple[int, list[str]], code: int, output: str) -> list[str]:
    wanted, fragments = expect
    problems = [] if code == wanted else [f"expected exit {wanted}, got {code}"]
    problems += [f"expected {fragment!r} in the output" for fragment in fragments if fragment not in output]
    return problems


def main() -> int:
    failed = 0
    for name, files, expect in CASES:
        code, output = run(files)
        problems = problems_for(expect, code, output)
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for line in problems + ["--- script output ---", *output.splitlines()]:
            print(f"        {line}")
    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
