#!/usr/bin/env python3
"""Tests for check-loop-bounds.py.

Each condition is pinned by a fixture the hook must reject and by the nearest
case it must let through: a bounded `for` beside the `while True`, a `while`
with a real test, options that set a bound, a `**kwargs` call the hook cannot
see into, the OpenAI runner's own default. Each case writes a throwaway file,
runs the hook as a subprocess and asserts on the exit code and the message.

Covers #352/AC-3: every condition the hook decides has a failing case here.

Usage:
    python3 engineering/llm-systems/hooks/test-check-loop-bounds.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-loop-bounds.py"

# #352, condition 1: a hand-written loop that calls a model is bounded

WHILE_TRUE_ANTHROPIC = '''
def run(client, messages):
    while True:
        response = client.messages.create(model="m", max_tokens=1024, messages=messages)
        if response.stop_reason != "tool_use":
            return response
'''

WHILE_TRUE_OPENAI = '''
def run(client, items):
    while True:
        response = client.responses.create(model="m", input=items)
        if not response.output:
            return response
'''

FOR_RANGE = '''
MAX_TURNS = 8

def run(client, messages):
    for _ in range(MAX_TURNS):
        response = client.messages.create(model="m", max_tokens=1024, messages=messages)
        if response.stop_reason != "tool_use":
            return response
    raise RuntimeError("turn limit reached")
'''

WHILE_WITH_TEST = '''
def run(client, messages, budget):
    while budget.remaining() > 0:
        client.messages.create(model="m", max_tokens=1024, messages=messages)
'''

WHILE_TRUE_NO_MODEL = '''
def drain(queue):
    while True:
        item = queue.get()
        if item is None:
            return
'''

# #352, condition 2: ClaudeAgentOptions sets a bound

OPTIONS_UNBOUNDED = '''
from claude_agent_sdk import ClaudeAgentOptions
options = ClaudeAgentOptions(allowed_tools=["Read"])
'''

OPTIONS_MAX_TURNS = '''
from claude_agent_sdk import ClaudeAgentOptions
options = ClaudeAgentOptions(allowed_tools=["Read"], max_turns=12)
'''

OPTIONS_BUDGET = '''
import claude_agent_sdk
options = claude_agent_sdk.ClaudeAgentOptions(max_budget_usd=2.0)
'''

OPTIONS_KWARGS = '''
from claude_agent_sdk import ClaudeAgentOptions
options = ClaudeAgentOptions(**settings)
'''

# #352, condition 3: the tool runner and the OpenAI runner keep a bound

RUNNER_UNBOUNDED = '''
runner = client.beta.messages.tool_runner(model="m", max_tokens=1024, tools=[lookup], messages=messages)
'''

RUNNER_BOUNDED = '''
runner = client.beta.messages.tool_runner(model="m", max_tokens=1024, tools=[lookup], messages=messages, max_iterations=6)
'''

OPTIONS_NONE = '''
from claude_agent_sdk import ClaudeAgentOptions
options = ClaudeAgentOptions(max_turns=None)
'''

RUNNER_NONE = '''
runner = client.beta.messages.tool_runner(model="m", max_tokens=1024, tools=[lookup], messages=messages, max_iterations=None)
'''

OPENAI_NONE = '''
from agents import Runner
result = Runner.run_sync(agent, "hello", max_turns=None)
'''

OPENAI_DEFAULT = '''
from agents import Runner
result = Runner.run_sync(agent, "hello")
'''

OPENAI_SET = '''
from agents import Runner
result = await Runner.run(agent, "hello", max_turns=5)
'''

SYNTAX_ERROR = "def broken(:\n"

results: list[tuple[str, bool]] = []


def run_hook(source: str, name: str = "agent.py") -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / name).write_text(source, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(HOOK), tmp], capture_output=True, text=True, check=False
        )


def rejects(label: str, source: str, needle: str) -> None:
    proc = run_hook(source)
    results.append((label, proc.returncode == 1 and needle in proc.stdout))


def accepts(label: str, source: str) -> None:
    proc = run_hook(source)
    results.append((label, proc.returncode == 0 and "0 finding(s)" in proc.stdout))


def main() -> int:
    rejects("condition 1: while True around messages.create", WHILE_TRUE_ANTHROPIC, "condition 1")
    rejects("condition 1: while True around responses.create", WHILE_TRUE_OPENAI, "condition 1")
    accepts("condition 1: a for over range is a bound", FOR_RANGE)
    accepts("condition 1: a while with a real test is read by review", WHILE_WITH_TEST)
    accepts("condition 1: while True with no model call is not this rule's", WHILE_TRUE_NO_MODEL)

    rejects("condition 2: ClaudeAgentOptions with no bound", OPTIONS_UNBOUNDED, "condition 2")
    accepts("condition 2: max_turns is a bound", OPTIONS_MAX_TURNS)
    accepts("condition 2: max_budget_usd is a bound", OPTIONS_BUDGET)
    accepts("condition 2: **kwargs is not read", OPTIONS_KWARGS)
    rejects("condition 2: max_turns=None is no bound", OPTIONS_NONE, "condition 2")

    rejects("condition 3: tool_runner without max_iterations", RUNNER_UNBOUNDED, "condition 3")
    accepts("condition 3: tool_runner with max_iterations", RUNNER_BOUNDED)
    rejects("condition 3: tool_runner with max_iterations=None", RUNNER_NONE, "condition 3")
    rejects("condition 3: Runner with max_turns=None", OPENAI_NONE, "condition 3")
    rejects("condition 3: Runner left on the SDK's default", OPENAI_DEFAULT, "condition 3")
    accepts("condition 3: Runner with max_turns set", OPENAI_SET)

    proc = run_hook(SYNTAX_ERROR)
    results.append(("a file that does not parse is reported, not fatal", proc.returncode == 0 and "not read" in proc.stderr))
    missing = subprocess.run(
        [sys.executable, "-B", str(HOOK), "/nonexistent/path"], capture_output=True, text=True, check=False
    )
    results.append(("a missing path exits 2", missing.returncode == 2))

    failures = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    print(f"\n{'all passed' if not failures else f'{len(failures)} failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
