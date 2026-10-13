#!/usr/bin/env python3
"""The Claude Code hook that records what a session cost, and publishes it when it can.

Claude Code runs this on `Stop`, at the end of each turn, and on `SessionEnd`. It receives the
hook input on stdin as JSON and uses three of its fields: `session_id`, `transcript_path` and
`cwd`. It reads that session's transcript and the transcripts of its sub-agents, and replaces
the session's record in the ledger. Running it again over the same transcript writes the same
record, so firing on every turn and again at the end converges.

Then, best-effort, it publishes: for each branch the session spent tokens on since the last
record, and for every branch of the session at `SessionEnd`, if `gh` is installed and
authenticated and the branch has an open pull request, every pass the ledger holds for that
branch is merged into the pull request's cost comment. Offline
it only records, and the next pass that can publish carries the earlier ones with it.

It never hurts the session it runs in. The hook process hands the work to a detached worker
and exits at once, because `SessionEnd` gives a hook 1.5 seconds. Every error, in either
process, is caught and written to `errors.log` beside the ledger, and the exit code is 0.

By hand, over one transcript, into a ledger of your choosing and without publishing:

    python3 costs/runtime/record.py --foreground --no-publish \
        --home /tmp/ledger --transcript ~/.claude/projects/<project>/<session>.jsonl

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import comment  # noqa: E402
import ledger  # noqa: E402
import money  # noqa: E402
import usage  # noqa: E402

TRUNK_LIKE = ledger.TRUNKS | {ledger.DETACHED}


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record one Claude Code session in the cost ledger.")
    parser.add_argument("--foreground", action="store_true", help="do the work in this process instead of a detached worker")
    parser.add_argument("--no-publish", action="store_true", help="record only; do not touch any pull request")
    parser.add_argument("--home", help="the ledger directory (default: $AHRENA_COSTS_HOME or the state directory)")
    parser.add_argument("--transcript", help="a transcript to record, instead of the hook input on stdin")
    parser.add_argument("--session-id", help="the session id, when it is not the transcript's file name")
    return parser.parse_args(argv)


def hook_input(options: argparse.Namespace, stdin_text: str) -> dict:
    """The session to record: from the flags when a transcript is named, else from stdin."""
    if options.transcript:
        path = Path(options.transcript).expanduser()
        return {"transcript_path": str(path), "session_id": options.session_id or path.stem}
    loaded = json.loads(stdin_text) if stdin_text.strip() else {}
    return loaded if isinstance(loaded, dict) else {}


def record(root: Path, event: dict, config: ledger.Config) -> tuple[dict, dict | None]:
    """Read the session and replace its record; return the new record and the one it replaced."""
    transcript = Path(str(event.get("transcript_path") or "")).expanduser()
    session_id = str(event.get("session_id") or "")
    if not transcript.is_file():
        raise FileNotFoundError("the hook input names no readable transcript")
    table = money.load_prices()
    reading = usage.read_session(transcript, config.idle_seconds, table.tiers)
    previous = ledger.read_session_record(root, session_id)
    current = ledger.session_record(session_id, reading, config.idle_seconds, previous)
    ledger.write_session_record(root, current)
    return current, previous


def branch_tokens(record_: dict | None) -> dict[tuple[str, str], dict]:
    """Tokens by (repository, branch) of one session record, for the branches that can have a pull request."""
    out: dict[tuple[str, str], dict] = {}
    for segment in (record_ or {}).get("segments", []):
        repository, branch = segment.get("repository"), segment.get("branch")
        if repository and branch and branch not in TRUNK_LIKE:
            usage.merge_tokens(out.setdefault((repository, branch), {}), segment.get("tokens", {}))
    return out


def session_pass(record_: dict, key: tuple[str, str]) -> dict | None:
    """One session's pass on one branch: its segments there, summed."""
    parts = [s for s in record_.get("segments", []) if (s.get("repository"), s.get("branch")) == key]
    tokens: dict = {}
    for part in parts:
        usage.merge_tokens(tokens, part.get("tokens", {}))
    if not tokens:
        return None
    return {
        "id": f"session:{record_['session_id']}",
        "kind": "development",
        "runner": "local",
        "started_at": min((p["first_event_at"] for p in parts if p.get("first_event_at")), default=None),
        "ended_at": max((p["last_event_at"] for p in parts if p.get("last_event_at")), default=None),
        "active_seconds": round(sum(float(p.get("active_seconds") or 0) for p in parts), 3),
        "tokens": tokens,
        "output_lower_bound": any(p.get("unfinished_responses") for p in parts),
    }


def publish_changed(root: Path, changed: list[tuple[str, str]], config: ledger.Config) -> None:
    """Publish every ledger pass of each changed branch that has an open pull request."""
    records = ledger.all_records(root)
    context = comment.Context(money.load_prices(), config.brl_per_usd)
    for key in changed:
        try:
            pull_request = comment.open_pull_request(*key)
            if pull_request is None:
                continue
            passes = [p for p in (session_pass(r, key) for r in records) if p]
            context.branch = key[1]
            comment.publish(comment.Target(key[0], pull_request), passes, context)
        except (comment.GhError, ValueError, KeyError) as error:
            ledger.log_error(root, f"publish skipped for {key[0]} {key[1]}: {error}")


def work(options: argparse.Namespace, event: dict) -> None:
    root = Path(options.home).expanduser() if options.home else ledger.home()
    config = ledger.load_config(root)
    with ledger.session_lock(root, str(event.get("session_id") or "")):
        current, previous = record(root, event, config)
        before, after = branch_tokens(previous), branch_tokens(current)
        closing = event.get("hook_event_name") == "SessionEnd"
        changed = [key for key, tokens in after.items() if closing or before.get(key) != tokens]
        if changed and config.publish and not options.no_publish and comment.gh_installed():
            publish_changed(root, changed, config)


def detach(argv: list[str], stdin_text: str) -> None:
    """Hand the same input to a worker that outlives this process."""
    worker = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--foreground", *argv],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, text=True,
    )
    if worker.stdin is not None:
        worker.stdin.write(stdin_text)
        worker.stdin.close()


def main(argv: list[str]) -> int:
    root = ledger.home()
    try:
        options = arguments(argv)
        root = Path(options.home).expanduser() if options.home else root
        stdin_text = "" if options.transcript or sys.stdin.isatty() else sys.stdin.read()
        if options.foreground:
            work(options, hook_input(options, stdin_text))
        else:
            detach(argv, stdin_text)
    except BaseException as error:  # noqa: BLE001
        if isinstance(error, SystemExit) and error.code in (0, None):
            return 0
        ledger.log_error(root, f"record: {type(error).__name__}: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
