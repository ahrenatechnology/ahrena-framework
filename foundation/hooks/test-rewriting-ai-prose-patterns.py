#!/usr/bin/env python3
"""Tests for the pattern data of the rewriting-ai-prose skill.

skills/rewriting-ai-prose/references/deterministic-patterns.json is a list a
project's lint imports, so a malformed entry breaks every importer. This test
parses it the way an importer would: it checks the schema, compiles every
regex, and runs each pattern against the positive and negative examples
embedded in the file, so a regex that stopped matching its own example fails
here and not in a consumer.

It also reads references/patterns-pt-br.md, the reader-facing list, and checks
that every pattern there carries a before and an after, and that every
deterministic id has its heading.

Usage:
    python3 foundation/hooks/test-rewriting-ai-prose-patterns.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "skills" / "rewriting-ai-prose"
DATA = SKILL / "references" / "deterministic-patterns.json"
LIST = SKILL / "references" / "patterns-pt-br.md"

FAMILIES = {"staging", "rhythm", "inflation", "formatting", "leftovers", "portuguese"}
STRENGTHS = {"strong", "medium", "weak"}
FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "u": 0}
ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
REQUIRED = ("id", "family", "strength", "language", "flags", "min_hits", "regex", "message", "fix", "examples")
# Constructs ECMAScript and Python read differently, so a pattern that uses
# one is not importable by both.
NOT_PORTABLE = (r"(?i)", r"(?P<", r"\w", r"\b", r"\B", r"(?<=\w", r"\A", r"\Z")
# The families the issue names under How, each of which a pattern must serve.
REQUIRED_IDS = {
    "not-x-but-y", "not-only-but-also", "staged-opener", "closer-phrase", "inflated-verbs",
    "inflated-words", "inflated-scene", "gerundismo", "dash-connector", "bold-labels",
    "decorative-headings", "chatbot-opener", "chatbot-closer", "chatbot-self-reference",
}


def compile_pattern(entry: dict) -> re.Pattern:
    flags = 0
    for letter in entry["flags"]:
        flags |= FLAGS[letter]
    return re.compile(entry["regex"], flags)


def check_schema(doc: dict) -> list[str]:
    errors = []
    if doc.get("version") != 1:
        errors.append("version is not 1")
    if doc.get("language") != "pt-BR":
        errors.append("language is not pt-BR")
    patterns = doc.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        return errors + ["patterns is not a non-empty list"]
    seen = set()
    for entry in patterns:
        pid = entry.get("id", "?")
        for key in REQUIRED:
            if key not in entry:
                errors.append(f"{pid}: missing {key}")
        if errors and any(e.startswith(f"{pid}: missing") for e in errors):
            continue
        if not ID.fullmatch(pid):
            errors.append(f"{pid}: id is not kebab-case")
        if pid in seen:
            errors.append(f"{pid}: duplicate id")
        seen.add(pid)
        if entry["family"] not in FAMILIES:
            errors.append(f"{pid}: unknown family {entry['family']}")
        if entry["strength"] not in STRENGTHS:
            errors.append(f"{pid}: unknown strength {entry['strength']}")
        if not isinstance(entry["flags"], list) or not set(entry["flags"]) <= set(FLAGS):
            errors.append(f"{pid}: flags are not a subset of i, m, s, u")
        if not isinstance(entry["min_hits"], int) or isinstance(entry["min_hits"], bool) or entry["min_hits"] < 1:
            errors.append(f"{pid}: min_hits is not an integer of at least 1")
        for key in ("regex", "message", "fix"):
            if not isinstance(entry[key], str) or not entry[key].strip():
                errors.append(f"{pid}: {key} is empty")
        examples = entry["examples"]
        for kind in ("positive", "negative"):
            items = examples.get(kind) if isinstance(examples, dict) else None
            if not isinstance(items, list) or not items or not all(isinstance(i, str) for i in items):
                errors.append(f"{pid}: examples.{kind} is not a non-empty list of strings")
    return errors


def check_patterns(doc: dict) -> list[str]:
    errors = []
    for entry in doc["patterns"]:
        pid = entry["id"]
        try:
            pattern = compile_pattern(entry)
        except re.error as error:
            errors.append(f"{pid}: regex does not compile ({error})")
            continue
        for fragment in NOT_PORTABLE:
            if fragment in entry["regex"]:
                errors.append(f"{pid}: regex uses {fragment}, which Python and ECMAScript read differently")
        if pattern.search(""):
            errors.append(f"{pid}: regex matches the empty string")
        for text in entry["examples"]["positive"]:
            if not pattern.search(text):
                errors.append(f"{pid}: does not match its positive example {text!r}")
        for text in entry["examples"]["negative"]:
            if pattern.search(text):
                errors.append(f"{pid}: matches its negative example {text!r}")
    return errors


def check_required(doc: dict) -> list[str]:
    ids = {entry["id"] for entry in doc["patterns"]}
    return [f"{missing}: required deterministic pattern is absent" for missing in sorted(REQUIRED_IDS - ids)]


def sections(markdown: str) -> dict[str, str]:
    """Map each pattern heading id to its section body."""
    found = {}
    parts = re.split(r"^### ", markdown, flags=re.MULTILINE)[1:]
    for part in parts:
        heading, _, body = part.partition("\n")
        match = re.search(r"\(`([a-z0-9-]+)`\)\s*$", heading)
        if match:
            found[match.group(1)] = body
    return found


def check_list(doc: dict) -> list[str]:
    errors = []
    found = sections(LIST.read_text(encoding="utf-8"))
    if not found:
        return [f"{LIST.name}: no pattern headings found"]
    for pid, body in found.items():
        for label in ("**Antes:**", "**Depois:**"):
            if label not in body:
                errors.append(f"{pid}: section has no {label}")
    for entry in doc["patterns"]:
        if entry["id"] not in found:
            errors.append(f"{entry['id']}: deterministic pattern has no section in {LIST.name}")
    return errors


# A deliberately broken copy of the data, to prove each check can fail.
def broken_cases(doc: dict) -> list[tuple[str, dict, str]]:
    def mutate(change) -> dict:
        copy = json.loads(json.dumps(doc))
        change(copy["patterns"][0])
        return copy

    return [
        ("a regex that does not compile", mutate(lambda p: p.update(regex="(")), "does not compile"),
        ("a positive example the regex misses", mutate(lambda p: p["examples"]["positive"].append("xyz")), "positive example"),
        ("a negative example the regex matches", mutate(lambda p: p["examples"]["negative"].append(p["examples"]["positive"][0])), "negative example"),
        ("an unknown family", mutate(lambda p: p.update(family="vibes")), "unknown family"),
        ("a missing key", mutate(lambda p: p.pop("fix")), "missing fix"),
        ("a regex that matches nothing to read", mutate(lambda p: p.update(regex="x*")), "empty string"),
        ("a construct the two engines read differently", mutate(lambda p: p.update(regex=r"\bfrete\b")), "read differently"),
    ]


def main() -> int:
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    failed = 0

    # #365/AC-4 the list parses, every regex compiles, and every pattern meets its own examples.
    checks = [("schema", check_schema(doc))]
    if not checks[0][1]:
        checks += [("patterns against their examples", check_patterns(doc)), ("required patterns", check_required(doc))]
    # #365/AC-2 every pattern of the pt-BR list carries a before and an after.
    checks.append(("pattern list has before and after", check_list(doc)) if not checks[0][1] else ("pattern list", []))
    for name, errors in checks:
        if errors:
            failed += 1
            print(f"FAIL  {name}")
            for error in errors:
                print(f"      {error}")
        else:
            print(f"ok    {name}")

    if not checks[0][1]:
        for name, broken, fragment in broken_cases(doc):
            errors = check_schema(broken) or check_patterns(broken)
            if any(fragment in error for error in errors):
                print(f"ok    rejects {name}")
            else:
                failed += 1
                print(f"FAIL  does not reject {name}: {errors}")

    print(f"\n{len(doc['patterns'])} patterns, {failed} failing checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
