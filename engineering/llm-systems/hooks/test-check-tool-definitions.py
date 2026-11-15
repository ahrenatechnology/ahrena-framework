#!/usr/bin/env python3
"""Tests for check-tool-definitions.py.

Covers #352/AC-3: each condition the hook decides has a case it must reject
and the nearest case it must accept. Each case writes a throwaway file, runs
the hook as a subprocess and asserts on the exit code and the message.

Usage:
    python3 engineering/llm-systems/hooks/test-check-tool-definitions.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-tool-definitions.py"

CLAUDE_GOOD = '''
TOOLS = [{
    "name": "get_order",
    "description": "Look up one order by id. Use when the user names an order.",
    "strict": True,
    "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                     "required": ["order_id"], "additionalProperties": False},
}]
'''

CLAUDE_NO_DESCRIPTION = '''
TOOLS = [{"name": "get_order", "strict": True,
          "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}}]
'''

CLAUDE_OPEN = '''
TOOLS = [{"name": "get_order", "description": "d", "strict": True,
          "input_schema": {"type": "object", "properties": {
              "filter": {"type": "object", "properties": {}}},
              "additionalProperties": False}}]
'''

CLAUDE_NOT_STRICT = '''
TOOLS = [{"name": "get_order", "description": "d",
          "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}}]
'''

CLAUDE_GENERATED_SCHEMA = '''
TOOLS = [{"name": "get_order", "description": "d", "strict": True,
          "input_schema": Order.model_json_schema()}]
'''

RESPONSES_DEFAULT = '''
tools = [{"type": "function", "name": "get_weather", "description": "d",
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}]
'''

RESPONSES_STRICT = '''
tools = [{"type": "function", "name": "get_weather", "description": "d", "strict": True,
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}]
'''

RESPONSES_STRICT_OFF = '''
tools = [{"type": "function", "name": "get_weather", "description": "d", "strict": False,
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}]
'''

CHAT_NOT_STRICT = '''
tools = [{"type": "function", "function": {"name": "get_weather", "description": "d",
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
'''

CHAT_STRICT = '''
tools = [{"type": "function", "function": {"name": "get_weather", "description": "d", "strict": True,
          "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
'''

NOT_A_TOOL = '''
user = {"name": "Ada", "parameters": None}
config = {"name": "x", "type": "object"}
'''

results: list[tuple[str, bool]] = []


def run_hook(source: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "tools.py").write_text(source, encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(HOOK), tmp], capture_output=True, text=True, check=False)


def rejects(label: str, source: str, needle: str) -> None:
    proc = run_hook(source)
    results.append((label, proc.returncode == 1 and needle in proc.stdout))


def accepts(label: str, source: str) -> None:
    proc = run_hook(source)
    results.append((label, proc.returncode == 0 and "0 finding(s)" in proc.stdout))


def main() -> int:
    accepts("a complete strict Claude tool", CLAUDE_GOOD)
    rejects("condition 1: no description", CLAUDE_NO_DESCRIPTION, "no description")
    rejects("condition 1: a nested object left open", CLAUDE_OPEN, "additionalProperties")
    accepts("condition 1: a generated schema is not read", CLAUDE_GENERATED_SCHEMA)
    rejects("condition 2: a Claude tool without strict", CLAUDE_NOT_STRICT, "condition 2")
    rejects("condition 2: Responses tool with strict omitted may fall back to non-strict", RESPONSES_DEFAULT, "condition 2")
    accepts("condition 2: Responses tool with strict True", RESPONSES_STRICT)
    rejects("condition 2: Responses tool with strict False", RESPONSES_STRICT_OFF, "condition 2")
    rejects("condition 2: Chat Completions function without strict", CHAT_NOT_STRICT, "condition 2")
    accepts("condition 2: Chat Completions function with strict", CHAT_STRICT)
    accepts("a dict that is not a tool", NOT_A_TOOL)
    missing = subprocess.run([sys.executable, "-B", str(HOOK), "/nonexistent/path"], capture_output=True, text=True, check=False)
    results.append(("a missing path exits 2", missing.returncode == 2))

    failures = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    print(f"\n{'all passed' if not failures else f'{len(failures)} failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
