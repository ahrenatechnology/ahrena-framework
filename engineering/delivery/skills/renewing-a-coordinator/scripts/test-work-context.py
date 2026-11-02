#!/usr/bin/env python3
"""Tests for work-context.py.

The fixtures are a set of session states with the verdict each must get
(fixtures/states.json), a complete work context (fixtures/context.json) and a
Round issue's comments holding two work-context comments by the coordinator and
a newer one by someone else (fixtures/round-comments.json). The script runs as a subprocess on each. The
behaviour is pinned against #225's criterion:

    #225/AC-7  the coordinator writes its work context (goal, decisions, pull
               requests and branches, child sessions, next step, blockers) as
               a Round-issue comment before compacting at 200k and re-reads it
               after; a fresh session is proposed only at the day's turn or an
               account switch, from that comment, and the old one is archived
               only on the person's yes

Usage:
    python3 engineering/delivery/skills/renewing-a-coordinator/scripts/test-work-context.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "work-context.py"
FIXTURES = HERE / "fixtures"
STATES = json.loads((FIXTURES / "states.json").read_text(encoding="utf-8"))
CONTEXT = FIXTURES / "context.json"
COMMENTS = FIXTURES / "round-comments.json"
AUTHOR = "round-tl"


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def with_file(payload: object, *args: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "input.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return run(*args[:1], str(path), *args[1:])


def check_state(case: dict) -> list[str]:
    code, output = with_file(case["state"], "decide")
    found = []
    if code != 0 or not output.startswith(f"{case['verdict']}:"):
        found.append(f"verdict is not {case['verdict']}: {output.strip()}")
    if case.get("says") and case["says"] not in output:
        found.append(f"the report does not say '{case['says']}'")
    return found


def case_render() -> list[str]:
    """The comment carries the six parts, in order, with an explicit 'none'."""
    code, output = run("render", str(CONTEXT))
    if code != 0:
        return [f"render exited {code}: {output.strip()}"]
    expected = ["Objetivo", "Decisões", "PRs e branches", "Sessões filhas", "Próximo passo", "Bloqueios"]
    found = []
    if re.findall(r"^### (.+)$", output, re.MULTILINE) != expected:
        found.append(f"sections are {re.findall(r'^### (.+)$', output, re.MULTILINE)}")
    if "### Bloqueios\n\n- nenhum" not in output:
        found.append("an empty blockers list is not written as 'nenhum'")
    if "<!-- work-context: {" not in output:
        found.append("the comment carries no work-context block to find it by")
    return found


def case_render_refuses() -> list[str]:
    """A context without one of its parts is refused, not written short."""
    context = json.loads(CONTEXT.read_text(encoding="utf-8"))
    del context["children"]
    context["next_step"] = " "
    code, output = with_file(context, "render")
    found = []
    if code != 1:
        found.append(f"render exited {code} on a context missing parts")
    if "children" not in output or "next_step" not in output:
        found.append(f"the refusal does not name both missing parts: {output.strip()}")
    return found


def case_latest() -> list[str]:
    """After compacting, the newest work-context comment is what is re-read."""
    code, output = run("latest", str(COMMENTS), "--author", AUTHOR)
    found = []
    if code != 0:
        return [f"latest exited {code}: {output.strip()}"]
    if "objetivo atual" not in output or "primeiro objetivo" in output:
        found.append("latest did not return the newest work-context comment")
    code, output = with_file({"comments": [{"body": "Checkpoint.", "author": {"login": AUTHOR}}]}, "latest", "--author", AUTHOR)
    if code != 1:
        found.append("a Round issue with no work context did not exit 1")
    return found


def case_latest_ignores_others() -> list[str]:
    """A newer work-context comment by anyone but the coordinator is not re-read."""
    code, output = run("latest", str(COMMENTS), "--author", AUTHOR)
    found = []
    if code != 0:
        return [f"latest exited {code}: {output.strip()}"]
    if "objetivo alheio" in output:
        found.append("latest returned a work-context comment another author wrote")
    code, output = run("latest", str(COMMENTS), "--author", "nobody")
    if code != 1:
        found.append("an author with no work context on the issue did not exit 1")
    code, output = run("latest", str(COMMENTS))
    if code != 2:
        found.append(f"latest without --author exited {code}, not 2")
    return found


def case_round_trip() -> list[str]:
    """What render writes is what latest finds."""
    code, comment = run("render", str(CONTEXT))
    if code != 0:
        return [f"render exited {code}"]
    code, output = with_file({"comments": [{"body": comment, "author": {"login": AUTHOR}}]}, "latest", "--author", AUTHOR)
    return [] if code == 0 and output == comment else ["latest did not return the comment render wrote"]


CASES = [(f"{case['name']} (#225/AC-7)", lambda case=case: check_state(case)) for case in STATES] + [
    ("the work context has its six parts (#225/AC-7)", case_render),
    ("a work context missing a part is refused (#225/AC-7)", case_render_refuses),
    ("the newest work context is re-read after compacting (#225/AC-7)", case_latest),
    ("only the coordinator's own work context is re-read (#225/AC-7)", case_latest_ignores_others),
    ("what is written is what is re-read (#225/AC-7)", case_round_trip),
]


def main() -> int:
    failed = 0
    for name, case in CASES:
        problems = case()
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
