#!/usr/bin/env python3
"""Detector for the loop-bound conditions of engineering/llm-systems/rules/loop-bounds.md.

Decides, in Python source, the three conditions a parser can see:

    1. a hand-written loop that calls a model is a `for` over a bound, never
       `while True`
    2. `ClaudeAgentOptions(...)` sets `max_turns` or `max_budget_usd`, because
       the Claude Agent SDK applies no limit to either by default
    3. the Claude SDK's tool runner is given `max_iterations`, and the OpenAI
       Agents SDK's runner is not given `max_turns=None`

Each default it reads is the SDK's own documented one, linked from
engineering/llm-systems/docs/frameworks.md ("The loop bound each framework
starts with"). A call that passes `**kwargs` is not read, because the bound may
be in the mapping, and the hook reports nothing it cannot see.

What it does not decide: a loop in TypeScript or another language, LangGraph's
`recursion_limit` (its default is a number, so leaving it out is a bound, if a
large one), Strands' `limits`, and whether a bound is the right size. Those are
the rule's review conditions.

Usage:
    python3 engineering/llm-systems/hooks/check-loop-bounds.py [path ...]

With no path it reads the current directory. Exit 0 when nothing is found, 1
when something is, 2 when a path does not exist.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RULE = "loop-bounds"

# #352: the request calls of the Claude and OpenAI clients, by the last two names of the attribute path.
MODEL_CALLS = frozenset(
    {("messages", "create"), ("messages", "stream"), ("responses", "create"), ("responses", "stream")}
)

# #352: directories holding vendored code or build output.
SKIPPED_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "build", "dist"})


def attribute_path(node: ast.expr) -> list[str]:
    """`a.b.c` as ["a", "b", "c"]; a call or subscript in the chain ends it."""
    names: list[str] = []
    while isinstance(node, ast.Attribute):
        names.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        names.append(node.id)
    return list(reversed(names))


def keyword_names(call: ast.Call) -> set[str] | None:
    """The keyword arguments a call names, or None when it unpacks `**kwargs`."""
    names: set[str] = set()
    for keyword in call.keywords:
        if keyword.arg is None:
            return None
        names.add(keyword.arg)
    return names


def is_model_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    path = attribute_path(node.func)
    return len(path) >= 2 and (path[-2], path[-1]) in MODEL_CALLS


def is_constant_true(test: ast.expr) -> bool:
    return isinstance(test, ast.Constant) and bool(test.value) is True and test.value is not None


CONDITION_1 = (
    "condition 1: a `while True` loop calls a model; write it as "
    "`for turn in range(MAX_TURNS)` and handle the bound being reached"
)
CONDITION_2 = (
    "condition 2: ClaudeAgentOptions sets neither max_turns nor max_budget_usd; "
    "the Agent SDK applies no limit by default"
)
CONDITION_3_RUNNER = (
    "condition 3: the tool runner is called without max_iterations; "
    "it runs until the model stops calling tools"
)
CONDITION_3_OPENAI = (
    "condition 3: Runner is given max_turns=None, which removes the OpenAI Agents SDK's bound"
)


def unbounded_while(node: ast.While) -> bool:
    return is_constant_true(node.test) and any(is_model_call(inner) for inner in ast.walk(node))


def removes_openai_bound(call: ast.Call) -> bool:
    return any(
        keyword.arg == "max_turns" and isinstance(keyword.value, ast.Constant) and keyword.value.value is None
        for keyword in call.keywords
    )


def call_finding(call: ast.Call) -> str | None:
    """The condition a call breaks, or None; a call that unpacks **kwargs is not read."""
    path = attribute_path(call.func)
    names = keyword_names(call)
    if not path or names is None:
        return None
    if path[-1] == "ClaudeAgentOptions" and not names & {"max_turns", "max_budget_usd"}:
        return CONDITION_2
    if path[-1] == "tool_runner" and "max_iterations" not in names:
        return CONDITION_3_RUNNER
    if path[-2:] in (["Runner", "run"], ["Runner", "run_sync"], ["Runner", "run_streamed"]) and removes_openai_bound(call):
        return CONDITION_3_OPENAI
    return None


def findings_in(tree: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and unbounded_while(node):
            found.append((node.lineno, CONDITION_1))
        elif isinstance(node, ast.Call):
            message = call_finding(node)
            if message:
                found.append((node.lineno, message))
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
