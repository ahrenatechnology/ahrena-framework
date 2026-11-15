#!/usr/bin/env python3
"""Detector for the decidable part of engineering/llm-systems/rules/tool-definitions.md.

Reads tool definitions written as dict literals in Python source, the form
both providers' documentation shows, and decides:

    1. the definition has a `description`, and every object in its input
       schema is closed with `"additionalProperties": False`
    2. strict mode is on: a Claude tool (`name` and `input_schema`) sets
       `"strict": True`; an OpenAI function tool (`"type": "function"`, `name` and `parameters`) does
       not set `"strict": False`, and in the Chat Completions shape
       (`{"type": "function", "function": {...}}`) sets `"strict": True`, since
       only the Responses API turns strict on when it is omitted

A schema that is not a literal (a Pydantic model's `model_json_schema()`, a
variable) is not read, and the hook reports nothing it cannot see. Conditions 3
to 6 (validation in the handler, error text, authority, output bound) need a
reader and are the rule's review conditions.

Usage:
    python3 engineering/llm-systems/hooks/check-tool-definitions.py [path ...]

With no path it reads the current directory. Exit 0 when nothing is found, 1
when something is, 2 when a path does not exist.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RULE = "tool-definitions"

# #352: directories holding vendored code or build output.
SKIPPED_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "build", "dist"})

NO_DESCRIPTION = "condition 1: the tool '{name}' has no description"
OPEN_OBJECT = "condition 1: an object in the schema of '{name}' does not set additionalProperties to False"
CLAUDE_NOT_STRICT = "condition 2: the Claude tool '{name}' does not set strict to True"
OPENAI_STRICT_OFF = "condition 2: the function tool '{name}' sets strict to False"
CHAT_NOT_STRICT = "condition 2: the Chat Completions function '{name}' does not set strict to True"


def literal_keys(node: ast.Dict) -> dict[str, ast.expr]:
    """The string-keyed entries of a dict literal; `**spread` entries are skipped."""
    return {
        key.value: value
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def has_spread(node: ast.Dict) -> bool:
    return any(key is None for key in node.keys)


def constant(node: ast.expr | None) -> object:
    return node.value if isinstance(node, ast.Constant) else ...


def open_objects(schema: ast.Dict) -> int:
    """How many object schemas inside a literal schema are not closed."""
    count = 0
    for node in ast.walk(schema):
        if not isinstance(node, ast.Dict) or has_spread(node):
            continue
        entries = literal_keys(node)
        if constant(entries.get("type")) == "object" and constant(entries.get("additionalProperties")) is not False:
            count += 1
    return count


def definition_findings(entries: dict[str, ast.expr], name: str, schema_key: str) -> list[str]:
    found = []
    if "description" not in entries:
        found.append(NO_DESCRIPTION.format(name=name))
    schema = entries.get(schema_key)
    if isinstance(schema, ast.Dict) and open_objects(schema):
        found.append(OPEN_OBJECT.format(name=name))
    return found


def tool_findings(node: ast.Dict) -> list[str]:
    if has_spread(node):
        return []
    entries = literal_keys(node)
    function = entries.get("function")
    if constant(entries.get("type")) == "function" and isinstance(function, ast.Dict) and not has_spread(function):
        inner = literal_keys(function)
        name = str(constant(inner.get("name")))
        found = definition_findings(inner, name, "parameters")
        if constant(inner.get("strict")) is not True:
            found.append(CHAT_NOT_STRICT.format(name=name))
        return found
    if "name" not in entries:
        return []
    name = str(constant(entries.get("name")))
    if "input_schema" in entries:
        found = definition_findings(entries, name, "input_schema")
        if constant(entries.get("strict")) is not True:
            found.append(CLAUDE_NOT_STRICT.format(name=name))
        return found
    if "parameters" in entries and constant(entries.get("type")) == "function":
        found = definition_findings(entries, name, "parameters")
        if constant(entries.get("strict")) is False:
            found.append(OPENAI_STRICT_OFF.format(name=name))
        return found
    return []


def findings_in(tree: ast.AST) -> list[tuple[int, str]]:
    inner_functions = {
        id(value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for key, value in zip(node.keys, node.values)
        if isinstance(key, ast.Constant) and key.value == "function"
    }
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and id(node) not in inner_functions:
            found += [(node.lineno, message) for message in tool_findings(node)]
    return sorted(found)


def python_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in SKIPPED_DIRS for part in path.relative_to(root).parts)
    )


def main(argv: list[str]) -> int:
    roots = [Path(arg) for arg in argv] or [Path(".")]
    missing = [str(root) for root in roots if not root.exists()]
    if missing:
        for path in missing:
            print(f"{path}: no such file or directory", file=sys.stderr)
        return 2
    total = 0
    for root in roots:
        for path in python_files(root):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError) as error:
                print(f"{path}: not read: {error.__class__.__name__}", file=sys.stderr)
                continue
            for line, message in findings_in(tree):
                print(f"{path}:{line} [{RULE}] {message}")
                total += 1
    print(f"{total} finding(s).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
