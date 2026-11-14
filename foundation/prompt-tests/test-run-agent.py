#!/usr/bin/env python3
"""Tests for run-agent.py: the part of an agent prompt test that needs no model.

The deciding logic is pinned by synthetic tool-call streams, one that passes
every condition and one per condition that fails it, and the layer-builder
cases are checked against the tree: each names an agent, a writing skill and
a review skill that exist. The model runs are not exercised: they need a
credential, and what they do is what the test is for (#290).

Usage:
    python3 foundation/prompt-tests/test-run-agent.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("run_agent", HERE / "run-agent.py")
run_agent = importlib.util.module_from_spec(spec)
sys.modules["run_agent"] = run_agent
spec.loader.exec_module(run_agent)

RULE = "engineering/security/rules/layer-exposure.md"
# #290: built, so the traceability check does not read a criterion token here.
TOKEN = "#" + "10/AC-2"
CASE = {
    "id": "c",
    "expect": {
        "writing_skill": "ahrena-engineering-python:writing-python",
        "reviewing_skill": "ahrena-engineering-python:reviewing-python",
        "exposure": {"criterion": TOKEN, "forbidden": [r"str\((error|e)\)"]},
    },
}
DONE = f"DONE\nlayer: api\nbranch: feat/12-charge-api at f7998e8\nleft: {TOKEN} written in the rule's form"

results: list[tuple[str, bool]] = []


def check(ok: bool, label: str) -> None:
    results.append((label, ok))


def stream(*calls: tuple[str, dict], result: str = DONE) -> list[str]:
    lines = [json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": n, "input": a}]}})
             for n, a in calls]
    return lines + ["not json", json.dumps({"type": "result", "result": result})]


SKILL_W = ("Skill", {"skill": "ahrena-engineering-python:writing-python"})
SKILL_R = ("Skill", {"skill": "ahrena-engineering-python:reviewing-python"})
READ_RULE = ("Read", {"file_path": "/tmp/plugins/engineering/security/rules/layer-exposure.md"})
WRITE_TEST = ("Write", {"file_path": "src/payments/api_test.py", "content": "import unittest"})


def sample(
    *calls: tuple[str, dict],
    result: str = DONE,
    added: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    pushed: tuple[str, ...] = ("feat/12-charge-api",),
) -> run_agent.Sample:
    parsed, text = run_agent.parse_stream(stream(*calls, result=result))
    return run_agent.Sample(parsed, text, list(added), list(pushed))


def failed(s: run_agent.Sample) -> list[str]:
    return run_agent.decide(s, CASE, RULE)[0]


def test_conditions() -> None:
    good = sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R)
    check(failed(good) == [], "a run in the right order, DONE and pushed, passes")

    check(any(f.startswith("1:") for f in failed(sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R, result=f"BLOCKED\nleft: {TOKEN}"))),
          "1: a result that is not DONE fails")
    check(any("remote" in f for f in failed(sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R, pushed=()))),
          "1: a branch that is not on the remote fails")
    check(any(f.startswith("2:") for f in failed(sample(READ_RULE, WRITE_TEST, SKILL_W, SKILL_R))),
          "2: the writing skill after the first test fails")
    check(any(f.startswith("3:") for f in failed(sample(SKILL_W, WRITE_TEST, READ_RULE, SKILL_R))),
          "3: the rule read after the first test fails")
    check(any(f.startswith("4:") for f in failed(sample(SKILL_W, READ_RULE, SKILL_R, WRITE_TEST))),
          "4: the review skill before the first test fails")
    check(any(f.startswith("2-4:") for f in failed(sample(SKILL_W, READ_RULE, SKILL_R))),
          "2-4: a run that writes no test fails")

    leak = sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R, added=[("src/payments/api.py", "    return 502, {'error': str(error)}")])
    check(any(f.startswith("5:") and "api.py" in f for f in failed(leak)), "5: a forbidden line outside a test fails")
    in_test = sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R, added=[("src/payments/api_test.py", "self.assertNotIn(str(error), body)")])
    check(failed(in_test) == [], "5: the same pattern inside a test is not a leak")
    silent = sample(SKILL_W, READ_RULE, WRITE_TEST, SKILL_R, result="DONE\nbranch: feat/12-charge-api\nleft: none")
    check(any("left:" in f for f in failed(silent)), "5: left: that does not name the criterion fails")


def test_cases_patterns() -> None:
    spec_ = json.loads((HERE / "layer-builders" / "cases.json").read_text())
    rows = next(c for c in spec_["cases"] if c["id"] == "mnem-python")["expect"]["exposure"]["forbidden"]
    matches = lambda line: any(run_agent.re.search(p, line) for p in rows)
    check(not matches("                customers.append(_parse_row(row))"), "mnem-python: parsing a row is not an exit")
    check(matches('    logger.warning("bad row %s", row)'), "mnem-python: a row handed to a logger is an exit")
    check(matches("    print(row)"), "mnem-python: a row printed is an exit")


def test_test_detection() -> None:
    shell = run_agent.Call("Bash", {"command": "cat > orders/order_test.go <<'EOF'\npackage orders\nEOF"})
    check(run_agent.writes_a_test(shell), "a test written through a shell heredoc counts")
    code = run_agent.Call("Bash", {"command": "cat > orders/order.go <<'EOF'\npackage orders\nEOF"})
    check(not run_agent.writes_a_test(code), "a source file written through the shell is not a test")
    rust = run_agent.Call("Write", {"file_path": "src/order.rs", "content": "#[cfg(test)]\nmod tests {}"})
    check(run_agent.writes_a_test(rust), "a Rust file with an in-file test module counts")
    ts = run_agent.Call("Edit", {"file_path": "src/cart/state.test.ts", "new_string": "test()"})
    check(run_agent.writes_a_test(ts), "a TypeScript test edited in place counts")


def test_cases_match_the_tree() -> None:
    spec_ = json.loads((HERE / "layer-builders" / "cases.json").read_text())
    check((REPO / spec_["rule"]).is_file(), "the cases' rule exists")
    for case in spec_["cases"]:
        plugin, agent = case["agent"].split(":")
        folder = plugin.removeprefix("ahrena-engineering-")
        check((REPO / "engineering" / folder / "agents" / f"{agent}.md").is_file(), f"{case['id']}: agent {case['agent']} exists")
        for key in ("writing_skill", "reviewing_skill"):
            owner, skill = case["expect"][key].split(":")
            path = REPO / "engineering" / owner.removeprefix("ahrena-engineering-") / "skills" / skill / "SKILL.md"
            check(path.is_file(), f"{case['id']}: {case['expect'][key]} exists")
    traps = [c["id"] for c in spec_["cases"] if "exposure" in c["expect"]]
    check(len(traps) >= 1, "at least one case invites a dependency's error into an exit")


if __name__ == "__main__":
    test_conditions()
    test_test_detection()
    test_cases_patterns()
    test_cases_match_the_tree()
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    failures = [label for label, ok in results if not ok]
    print(f"\n{'all passed' if not failures else f'{len(failures)} failed'}")
    sys.exit(1 if failures else 0)
