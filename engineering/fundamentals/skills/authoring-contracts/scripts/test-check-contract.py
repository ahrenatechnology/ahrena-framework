#!/usr/bin/env python3
"""Tests for check-contract.py.

A check that has never rejected anything is a claim, not a guardrail.

The script runs as a subprocess on purpose: that is what a pipeline runs, exit
code included. The two skeletons are read from `references/` as shipped, so a
skeleton edited into something the check refuses fails here and not in the
first project that copies it.

Usage:
    python3 engineering/fundamentals/skills/authoring-contracts/scripts/test-check-contract.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check-contract.py"
REFERENCES = HERE.parent / "references"

OPENAPI = json.loads((REFERENCES / "openapi-skeleton.json").read_text(encoding="utf-8"))
EVENT = json.loads((REFERENCES / "event-skeleton.json").read_text(encoding="utf-8"))


def openapi(change) -> str:
    """The shipped skeleton with exactly one thing changed."""
    document = json.loads(json.dumps(OPENAPI))
    change(document)
    return json.dumps(document)


def event(change) -> str:
    document = json.loads(json.dumps(EVENT))
    change(document)
    return json.dumps(document)


def drop_identifier(document: dict) -> None:
    del document["paths"]["/orders"]["post"]["operationId"]


def empty_identifier(document: dict) -> None:
    document["paths"]["/orders"]["post"]["operationId"] = ""


def repeat_identifier(document: dict) -> None:
    document["paths"]["/orders/{order_id}"]["get"]["operationId"] = "listOrders"


def add_webhook(document: dict) -> None:
    document["webhooks"] = {"orderPlaced": {"post": {"responses": {"204": {"description": "Taken."}}}}}


def drop_openapi_field(document: dict) -> None:
    del document["openapi"]


def without(attribute: str):
    def change(document: dict) -> None:
        document["required"].remove(attribute)

    return change


def drop_required(document: dict) -> None:
    del document["required"]


def require_more(document: dict) -> None:
    document["required"].append("time")


def case(name: str, args: list[str], files: dict[str, str], expect: tuple[int, list[str]]) -> tuple:
    return (name, args, files, expect)


CASES = [
    # covers #12/AC-2
    case(
        "the shipped OpenAPI skeleton passes",
        ["--openapi", str(REFERENCES / "openapi-skeleton.json")],
        {},
        (0, ["1 document(s) checked, no failures"]),
    ),
    # covers #12/AC-3
    case(
        "an operation with no operationId fails, named by method and path",
        ["--openapi", "openapi.json"],
        {"openapi.json": openapi(drop_identifier)},
        (1, ["[contract-first]", "POST /orders declares no `operationId`", "condition 3"]),
    ),
    case(
        "an empty operationId is no operationId",
        ["--openapi", "openapi.json"],
        {"openapi.json": openapi(empty_identifier)},
        (1, ["POST /orders declares no `operationId`"]),
    ),
    case(
        "an operation under webhooks is an operation",
        ["--openapi", "openapi.json"],
        {"openapi.json": openapi(add_webhook)},
        (1, ["POST orderPlaced declares no `operationId`"]),
    ),
    # covers #12/AC-4
    case(
        "an operationId used twice fails, naming both operations",
        ["--openapi", "openapi.json"],
        {"openapi.json": openapi(repeat_identifier)},
        (1, ["'listOrders' is shared by GET /orders and GET /orders/{order_id}"]),
    ),
    case(
        "a document with no openapi field is not read as one",
        ["--openapi", "openapi.json"],
        {"openapi.json": openapi(drop_openapi_field)},
        (1, ["is not an OpenAPI document"]),
    ),
    # covers #12/AC-5
    case(
        "the shipped event skeleton passes",
        ["--event", str(REFERENCES / "event-skeleton.json")],
        {},
        (0, ["1 document(s) checked, no failures"]),
    ),
    # covers #12/AC-6, once per attribute so each can only fail for its own
    *[
        case(
            f"an event schema that does not require `{attribute}` fails",
            ["--event", "event.json"],
            {"event.json": event(without(attribute))},
            (1, ["[contract-first]", f"`required` omits `{attribute}`", "condition 4"]),
        )
        for attribute in ("specversion", "id", "source", "type")
    ],
    case(
        "an event schema with no required list omits all four",
        ["--event", "event.json"],
        {"event.json": event(drop_required)},
        (1, ["omits `specversion`", "omits `id`", "omits `source`", "omits `type`", "4 failure(s)"]),
    ),
    # Pinned: the rule takes the specification's required set and stops there,
    # so requiring an optional attribute as well is the project's own choice.
    case(
        "requiring an optional attribute as well passes",
        ["--event", "event.json"],
        {"event.json": event(require_more)},
        (0, ["no failures"]),
    ),
    case(
        "both kinds are checked in one run",
        ["--openapi", "openapi.json", "--event", "event.json"],
        {"openapi.json": openapi(drop_identifier), "event.json": event(without("id"))},
        (1, ["declares no `operationId`", "omits `id`", "2 failure(s) in 2 document(s)"]),
    ),
    # covers #12/AC-10
    case(
        "a YAML document is not checked, and that is not a pass",
        ["--openapi", "openapi.yaml"],
        {"openapi.yaml": "openapi: 3.1.0\ninfo:\n  title: Orders\n  version: 1.0.0\npaths: {}\n"},
        (2, ["openapi.yaml", "not checked: is not JSON", "YAML"]),
    ),
    case(
        "a missing file is not checked",
        ["--event", "absent.json"],
        {},
        (2, ["absent.json", "not checked: could not be read"]),
    ),
    case(
        "a key written twice in one object is not checked",
        ["--event", "event.json"],
        {"event.json": '{"required": [], "required": ["specversion", "id", "source", "type"]}'},
        (2, ["not checked: the key 'required' appears twice"]),
    ),
    case(
        "an unread document outranks a failure in another",
        ["--openapi", "openapi.json", "--event", "event.yaml"],
        {"openapi.json": openapi(drop_identifier), "event.yaml": "type: object\n"},
        (2, ["declares no `operationId`", "not checked"]),
    ),
    case("no document named is not a pass", [], {}, (2, ["not checked: name at least one document"])),
]


def run(args: list[str], files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        for rel, content in files.items():
            (Path(tmp) / rel).write_text(content, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=tmp)
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: tuple[int, list[str]], code: int, output: str) -> list[str]:
    wanted, fragments = expect
    problems = [] if code == wanted else [f"expected exit {wanted}, got {code}"]
    problems += [f"expected {fragment!r} in the output" for fragment in fragments if fragment not in output]
    return problems


def main() -> int:
    failed = 0
    for name, args, files, expect in CASES:
        code, output = run(args, files)
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
