#!/usr/bin/env python3
"""A coordinator's work context: when to write it, how it reads, where it is.

Condition 6 of engineering/delivery/rules/round-roles.md keeps the PM and the TL
of a round to one session each for the day. Above the compaction threshold a
coordinator writes its work context to the Round issue, compacts, and re-reads
it; it is renewed in a fresh session only at the day's turn or on an account
switch, and the fresh session starts from that same comment.

    decide   reads the session's state and says what is due: renew, compact
             or continue; renewal outranks compaction, and nothing else renews
    render   writes the work-context comment, refusing one that lacks a part
    latest   finds the newest work-context comment the coordinator itself wrote
             on a Round issue, to re-read; anyone else's is ignored

The comment's six parts are the goal, the decisions, the pull requests and
branches, the child sessions, the next step and the blockers. Its labels follow
the person's language; its hidden block's keys stay English.

Usage:
    python3 work-context.py decide STATE.json [--threshold TOKENS]
    python3 work-context.py render CONTEXT.json
    python3 work-context.py latest COMMENTS.json --author LOGIN

STATE.json has context_tokens, session_day, today, session_account and
current_account. COMMENTS.json is `gh issue view N --json comments`.

Exit status: 0 done, 1 refused or nothing found, 2 a usage error.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

THRESHOLD = 200_000
MARK = "work-context"
PARTS = ("goal", "decisions", "pull_requests", "children", "next_step", "blockers")

LABELS = {
    "en": {
        "heading": "Work context · {role} · {when}",
        "goal": "Goal",
        "decisions": "Decisions",
        "pull_requests": "Pull requests and branches",
        "children": "Child sessions",
        "next_step": "Next step",
        "blockers": "Blockers",
        "nothing": "none",
    },
    "pt-BR": {
        "heading": "Contexto de trabalho · {role} · {when}",
        "goal": "Objetivo",
        "decisions": "Decisões",
        "pull_requests": "PRs e branches",
        "children": "Sessões filhas",
        "next_step": "Próximo passo",
        "blockers": "Bloqueios",
        "nothing": "nenhum",
    },
}


class Refused(Exception):
    """The input breaks a condition; the message says which."""


def decide(state: dict, threshold: int) -> tuple[str, str]:
    """What is due now, and why. Only the day's turn or an account switch renews."""
    if state["today"] != state["session_day"]:
        return "renew", f"the day turned ({state['session_day']} to {state['today']})"
    if state["current_account"] != state["session_account"]:
        return "renew", f"the account switched ({state['session_account']} to {state['current_account']})"
    if state["context_tokens"] >= threshold:
        return "compact", f"context at {state['context_tokens']} tokens, at or above {threshold}"
    return "continue", f"context at {state['context_tokens']} tokens, same day and account"


NEXT = {
    "renew": [
        "write the work context to the Round issue if the last one is stale",
        "propose a fresh session started from that comment, through /round-pm or /round-tl",
        "archive the old session only on the person's yes",
    ],
    "compact": [
        "write the work context to the Round issue",
        "compact this session; do not hand over",
        "after compacting, re-read the newest work-context comment",
    ],
    "continue": [],
}


def render(context: dict) -> str:
    words = LABELS.get(context.get("language", "en"))
    if words is None:
        raise Refused(f"no labels for language '{context.get('language')}'; known: {', '.join(LABELS)}")
    missing = [p for p in PARTS if p not in context]
    missing += [p for p in ("goal", "next_step") if p in context and not str(context[p]).strip()]
    if missing:
        raise Refused("the work context lacks: " + ", ".join(missing) + " (an empty list says 'none'; leaving a part out does not)")

    def lines(value: object) -> str:
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value) if value else f"- {words['nothing']}"
        return str(value)

    head = words["heading"].format(role=context.get("role", ""), when=context.get("when", ""))
    sections = "\n\n".join(f"### {words[part]}\n\n{lines(context[part])}" for part in PARTS)
    block = json.dumps(context, ensure_ascii=False, sort_keys=True)
    return f"## {head}\n\n{sections}\n\n<!-- {MARK}: {block} -->\n"


def latest(comments: list[dict], author: str) -> dict | None:
    for comment in reversed(comments):
        if (comment.get("author") or {}).get("login") != author:
            continue
        body = comment.get("body", "")
        if re.search(rf"<!-- {MARK}: \{{", body):
            return {"body": body, "createdAt": comment.get("createdAt", "")}
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("decide")
    p.add_argument("state")
    p.add_argument("--threshold", type=int, default=THRESHOLD)
    p = sub.add_parser("render")
    p.add_argument("context")
    p = sub.add_parser("latest")
    p.add_argument("comments")
    p.add_argument("--author", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "decide":
            verdict, why = decide(json.loads(Path(args.state).read_text(encoding="utf-8")), args.threshold)
            print(f"{verdict}: {why}")
            for step in NEXT[verdict]:
                print(f"  {step}")
            return 0
        if args.command == "render":
            print(render(json.loads(Path(args.context).read_text(encoding="utf-8"))), end="")
            return 0
        payload = json.loads(Path(args.comments).read_text(encoding="utf-8"))
        found = latest(payload.get("comments", []) if isinstance(payload, dict) else payload, args.author)
        if found is None:
            raise Refused(f"no work-context comment by {args.author} on this Round issue")
        print(found["body"], end="")
        return 0
    except Refused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
