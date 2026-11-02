#!/usr/bin/env python3
"""Decide whether a coordinator may hand one demand to a child session.

The conditions are condition 4 and 5 of engineering/delivery/rules/round-roles.md
and the brief's shape in skills/dispatching-sessions/SKILL.md. A dispatch is
refused when it has no issue, when its child would not run Athena, when it asks
for a model other than Sonnet without saying why, when its title and brief are
not in the person's language or the brief does not name its issue, or when it
hands a second, unrelated demand to a session that already holds one. A pull
request another tool owns is skipped, not dispatched.

Whether the brief is actually written in the language it declares is a reader's
call; this script checks that the dispatcher declared the person's language.

Usage:
    python3 check-dispatch.py DISPATCH.json

DISPATCH.json is one dispatch or a list of them. Each has: issue, title, brief,
language, person_language, model, model_reason, agent, tool, and optionally
session (an existing session, with the issue it holds) and pull_request (with
the tool that owns it).

Exit status: 0 every dispatch may go, 1 one was refused or skipped, 2 a usage
error. Standard library only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_MODEL = "sonnet"
CHILD_AGENT = "athena"


def problems_for(dispatch: dict) -> tuple[str, list[str]]:
    """The verdict, `dispatch`, `refuse` or `skip`, with the reasons for it."""
    issue = str(dispatch.get("issue", "")).strip()
    pr = dispatch.get("pull_request") or {}
    owner = pr.get("owner_tool")
    if owner and owner != dispatch.get("tool"):
        return "skip", [f"pull request #{pr.get('number')} is owned by {owner}; record its state and leave it"]
    found = []
    if not issue:
        found.append("no issue: no child session starts without one")
    if dispatch.get("agent") != CHILD_AGENT:
        found.append(f"the child runs {dispatch.get('agent')!r}, not {CHILD_AGENT}")
    reason = str(dispatch.get("model_reason", "")).strip()
    if dispatch.get("model", DEFAULT_MODEL) != DEFAULT_MODEL and not (reason and reason in str(dispatch.get("brief", ""))):
        found.append(f"model {dispatch.get('model')} without a reason in the brief; the default is {DEFAULT_MODEL}")
    if dispatch.get("language") != dispatch.get("person_language"):
        found.append(f"title and brief are in {dispatch.get('language')!r}, the person reads {dispatch.get('person_language')!r}")
    for field in ("title", "brief"):
        if not str(dispatch.get(field, "")).strip():
            found.append(f"no {field}")
    if issue and issue not in str(dispatch.get("brief", "")):
        found.append(f"the brief does not name {issue}")
    held = (dispatch.get("session") or {}).get("holds")
    if held and held != issue:
        found.append(f"the session already holds {held}; a second, unrelated demand goes to a new session")
    return ("refuse" if found else "dispatch"), found


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.split("Usage:")[1].split("DISPATCH.json is")[0].strip(), file=sys.stderr)
        return 2
    payload = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    dispatches = payload if isinstance(payload, list) else [payload]
    status = 0
    for dispatch in dispatches:
        verdict, reasons = problems_for(dispatch)
        target = "its session" if (dispatch.get("session") or {}).get("holds") else "a new session"
        label = dispatch.get("issue") or "(no issue)"
        if verdict == "dispatch":
            model = dispatch.get("model", DEFAULT_MODEL)
            print(f"dispatch: {label} to {target}, model {model}, title {dispatch['title']!r}")
            continue
        status = 1
        print(f"{verdict}: {label}")
        for reason in reasons:
            print(f"  {reason}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
