#!/usr/bin/env python3
"""Compares a committed contract with the description a service published.

Decides condition 2 of engineering/fundamentals/rules/contract-first.md, given
the two documents it is stated over:

    2. the published contract and the committed contract are byte-equal after
       canonical serialisation

Canonical means object keys sorted and whitespace normalised. Nothing else is
forgiven: an array in a different order, `1` against `1.0`, an added
description and an added optional field are all differences, because the rule
chose equality over a tolerance and its doc argues why.

The script does not start the service or fetch anything. Which command starts
it and which address serves the description are the two inputs this plugin
cannot guess, so the pipeline job supplies them and hands over two files.

JSON only. The standard library carries no YAML parser and this plugin takes
no dependencies, so a YAML document is reported as not checked and the run
exits 2. Convert it with the project's own toolchain first.

Exit status: 0 when the two are equal, 1 when they differ, 2 when either could
not be read and so nothing was compared.

Usage:
    python3 diff-contract.py COMMITTED PUBLISHED
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RULE = "contract-first"
SHOWN = 60


class NotChecked(Exception):
    """A document could not be read, so nothing was compared."""


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
            "is converted with the project's own toolchain before it is compared"
        ) from error


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def shown(value: object) -> str:
    text = canonical(value)
    return text if len(text) <= SHOWN else text[: SHOWN - 3] + "..."


def pointer(parent: str, token: object) -> str:
    """RFC 6901: `~` and `/` inside a token are written `~0` and `~1`."""
    return f"{parent}/{str(token).replace('~', '~0').replace('/', '~1')}"


def members(value: object) -> dict | None:
    """An object's members by key and an array's by index; None for a scalar."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return dict(enumerate(value))
    return None


def differences(committed: object, published: object, at: str = "") -> list[str]:
    """One line per place the two differ, each led by its JSON Pointer."""
    ours, theirs = members(committed), members(published)
    if ours is None or theirs is None or isinstance(committed, list) != isinstance(published, list):
        if canonical(committed) == canonical(published):
            return []
        return [f"{at or '/'}: committed {shown(committed)}, published {shown(published)}"]
    found = []
    for key in sorted(set(ours) | set(theirs)):
        here = pointer(at, key)
        if key not in theirs:
            found.append(f"{here}: only in the committed contract")
        elif key not in ours:
            found.append(f"{here}: only in the published description")
        else:
            found.extend(differences(ours[key], theirs[key], here))
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("not checked: usage is diff-contract.py COMMITTED PUBLISHED")
        return 2
    documents = []
    for path in (Path(argv[0]), Path(argv[1])):
        try:
            documents.append(load(path))
        except NotChecked as reason:
            print(f"{path}\n    not checked: {reason}")
    if len(documents) != 2:
        return 2
    found = differences(documents[0], documents[1])
    if not found:
        print("The published description and the committed contract are equal after canonical serialisation.")
        return 0
    print(f"{argv[0]}\n    [{RULE}] differs from the published description {argv[1]} (condition 2)")
    for line in found:
        print(f"        {line}")
    print(f"\n{len(found)} difference(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
