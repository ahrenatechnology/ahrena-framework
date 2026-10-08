#!/usr/bin/env python3
"""Checks an authored contract for what the contract-first conditions key on.

Decides two properties of a contract somebody wrote, both of them things a
later condition in engineering/fundamentals/rules/contract-first.md cannot be
decided without:

    1. every operation in an OpenAPI document declares an `operationId`, and
       no two operations share one (condition 3 is a set difference over
       those identifiers)
    2. an event schema requires the four attributes CloudEvents 1.0 requires:
       `specversion`, `id`, `source` and `type` (condition 4)

It is not an OpenAPI validator or a JSON Schema validator. A document that
passes here can still be invalid against its own specification, and the
specification's own tooling is what says so.

Each document is named with the flag that says what it is. Nothing is
inferred from a file's name or contents, because a wrong guess is a check that
confidently read the wrong thing.

JSON only. The standard library carries no YAML parser and this plugin takes
no dependencies, so a YAML document is reported as not checked and the run
exits 2. Convert it with the project's own toolchain first.

Exit status: 0 when every document passes, 1 when one fails a property, 2 when
a document could not be read and so was not checked.

Usage:
    python3 check-contract.py [--openapi FILE]... [--event FILE]...
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "contract-first"
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
CLOUDEVENTS_REQUIRED = ("specversion", "id", "source", "type")


@dataclass
class Finding:
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] {self.message}"


class NotChecked(Exception):
    """The document could not be read, so nothing was decided about it."""


def reject_repeats(pairs: list[tuple[str, object]]) -> dict[str, object]:
    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise NotChecked(f"the key {key!r} appears twice in one object")
        seen[key] = value
    return seen


def load(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise NotChecked(f"could not be read: {error}") from error
    try:
        return json.loads(text, object_pairs_hook=reject_repeats)
    except json.JSONDecodeError as error:
        raise NotChecked(
            f"is not JSON (line {error.lineno}: {error.msg}). A YAML document "
            "is converted with the project's own toolchain before it is checked"
        ) from error


def path_items(document: dict) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for section in ("paths", "webhooks"):
        items = document.get(section)
        if isinstance(items, dict):
            found.extend(items.items())
    return found


def operations(document: dict) -> list[tuple[str, dict]]:
    """Every operation under `paths` and `webhooks`, labelled `METHOD path`."""
    return [
        (f"{method.upper()} {path}", item[method])
        for path, item in path_items(document)
        if isinstance(item, dict)
        for method in METHODS
        if isinstance(item.get(method), dict)
    ]


def check_openapi(path: Path, document: object) -> list[Finding]:
    if not isinstance(document, dict) or "openapi" not in document:
        return [Finding(str(path), "is not an OpenAPI document: it has no `openapi` field")]
    findings = []
    owners: dict[str, list[str]] = {}
    for label, operation in operations(document):
        identifier = operation.get("operationId")
        if isinstance(identifier, str) and identifier:
            owners.setdefault(identifier, []).append(label)
        else:
            findings.append(Finding(str(path), f"{label} declares no `operationId`, so no contract test can name it (condition 3)"))
    for identifier, labels in owners.items():
        if len(labels) > 1:
            findings.append(Finding(str(path), f"`operationId` {identifier!r} is shared by {' and '.join(labels)} (condition 3)"))
    return findings


def check_event(path: Path, document: object) -> list[Finding]:
    if not isinstance(document, dict):
        return [Finding(str(path), "is not an event schema: the document is not a JSON object")]
    required = document.get("required")
    declared = required if isinstance(required, list) else []
    return [
        Finding(str(path), f"`required` omits `{attribute}`, which CloudEvents 1.0 requires on every event (condition 4)")
        for attribute in CLOUDEVENTS_REQUIRED
        if attribute not in declared
    ]


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--openapi", action="append", default=[], type=Path, metavar="FILE")
    parser.add_argument("--event", action="append", default=[], type=Path, metavar="FILE")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = arguments(argv)
    subjects = [(path, check_openapi) for path in args.openapi] + [(path, check_event) for path in args.event]
    if not subjects:
        print("not checked: name at least one document with --openapi or --event")
        return 2
    findings: list[Finding] = []
    unread = 0
    for path, check in subjects:
        try:
            findings.extend(check(path, load(path)))
        except NotChecked as reason:
            unread += 1
            print(f"{path}\n    not checked: {reason}")
    for finding in findings:
        print(finding)
    if unread:
        return 2
    if findings:
        print(f"\n{len(findings)} failure(s) in {len(subjects)} document(s).")
        return 1
    print(f"{len(subjects)} document(s) checked, no failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
