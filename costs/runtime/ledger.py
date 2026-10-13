"""The local ledger: where it lives, its configuration, and one record per session.

The ledger is a directory outside every repository, shared by all of them and by their
worktrees:

    <home>/sessions/<session-id>.json   one record per session, replaced whole on each write
    <home>/config.json                  optional configuration
    <home>/errors.log                   what the hook caught instead of failing

`<home>` is `$AHRENA_COSTS_HOME`, else `$XDG_STATE_HOME/ahrena-costs`, else
`~/.local/state/ahrena-costs`.

A session's record is a file named after the session and written by replacement, so recording
the same session twice converges on the same record instead of adding a second one.

A record holds identifiers, timestamps, counters and the repository and branch of each
segment. The working directory is kept only as a hash, which lets a later write recognise the
segment after its worktree has been removed. Standard library only.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

from usage import Reading, Segment, span

SCHEMA = 1
DEFAULT_IDLE_SECONDS = 300
LOG_LIMIT_BYTES = 1_000_000
SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
REMOTE = re.compile(r"[:/](?P<owner>[^/:]+)/(?P<name>[^/]+?)(?:\.git)?/?$")

BRANCH = re.compile(r"^(?P<type>[A-Za-z]+)/(?P<issue>[1-9][0-9]*)-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$")
"""The Forge's branch convention, `type/issue-slug`.

The same expression as `contributing/hooks/check-branch-name.py`. The two plugins install
apart, so this one cannot import the other; `test-ledger.py` fails when the two drift.
"""

WORKTREES = "/.claude/worktrees/"
"""Where Claude Code keeps the worktrees it creates, inside the repository they belong to.

A worktree there is often gone by the time a session is recorded; the repository it was cut
from is the directory above this marker.
"""

TRUNKS = frozenset({"main", "master"})
DETACHED = "HEAD"


def home() -> Path:
    """The ledger directory, from the environment or the default under the user's home."""
    explicit = os.environ.get("AHRENA_COSTS_HOME")
    if explicit:
        return Path(explicit).expanduser()
    state = os.environ.get("XDG_STATE_HOME")
    base = Path(state).expanduser() if state else Path.home() / ".local" / "state"
    return base / "ahrena-costs"


@dataclass
class Config:
    """Configuration. A money value left out stays None and is reported as not configured."""

    idle_seconds: float = DEFAULT_IDLE_SECONDS
    brl_per_usd: float | None = None
    hourly_rate: float | None = None
    hourly_rate_currency: str | None = None
    publish: bool = True


def positive(value: object) -> float | None:
    """A positive number, or None for anything else, a zero included."""
    try:
        number = float(str(value))
    except ValueError:
        return None
    return number if number > 0 else None


def load_config(root: Path) -> Config:
    """Read `config.json`, then let the environment override it."""
    stored: dict = {}
    try:
        loaded = json.loads((root / "config.json").read_text(encoding="utf-8"))
        stored = loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError):
        stored = {}
    env = os.environ
    currency = str(env.get("AHRENA_COSTS_HOURLY_RATE_CURRENCY") or stored.get("hourly_rate_currency") or "").upper()
    publish = env.get("AHRENA_COSTS_PUBLISH", "1" if stored.get("publish", True) else "0")
    return Config(
        idle_seconds=positive(env.get("AHRENA_COSTS_IDLE_SECONDS") or stored.get("idle_threshold_seconds")) or DEFAULT_IDLE_SECONDS,
        brl_per_usd=positive(env.get("AHRENA_COSTS_BRL_PER_USD") or stored.get("brl_per_usd")),
        hourly_rate=positive(env.get("AHRENA_COSTS_HOURLY_RATE") or stored.get("hourly_rate")),
        hourly_rate_currency=currency if currency in ("USD", "BRL") else None,
        publish=publish not in ("0", "false", "no", ""),
    )


def log_error(root: Path, message: str) -> None:
    """Append one line to the log beside the ledger; never raise."""
    try:
        root.mkdir(parents=True, exist_ok=True)
        log = root / "errors.log"
        if log.exists() and log.stat().st_size > LOG_LIMIT_BYTES:
            os.replace(log, root / "errors.log.1")
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{iso(datetime.now(timezone.utc).timestamp())} {message}\n")
    except OSError:
        pass


def iso(moment: float | None) -> str | None:
    if moment is None:
        return None
    return datetime.fromtimestamp(moment, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repository_of(cwd: str) -> str | None:
    """`owner/name` from the `origin` remote of a working directory, or None.

    A removed directory resolves only when it was one of Claude Code's own worktrees.
    """
    if not os.path.isdir(cwd):
        cwd = cwd.partition(WORKTREES)[0] if WORKTREES in cwd else ""
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        result = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    match = REMOTE.search(result.stdout.strip()) if result.returncode == 0 else None
    return f"{match.group('owner')}/{match.group('name')}" if match else None


def attribute(branch: str) -> dict:
    """The issue a branch name carries, or why there is none. Never a guess."""
    match = BRANCH.match(branch)
    if match:
        return {"issue": int(match.group("issue")), "method": "branch"}
    if not branch or branch == DETACHED:
        reason = "no-branch"
    elif branch in TRUNKS:
        reason = "default-branch"
    else:
        reason = "no-issue-in-branch-name"
    return {"issue": None, "method": "unattributed", "reason": reason}


def cwd_key(cwd: str) -> str:
    return hashlib.sha256(cwd.encode("utf-8")).hexdigest()[:16]


def segment_record(segment: Segment, known: dict[str, str]) -> dict:
    """One segment as it is stored: no path, only its hash, repository and branch."""
    key = cwd_key(segment.cwd)
    wall = (segment.last - segment.first) if segment.first is not None and segment.last is not None else 0.0
    return {
        "key": key,
        "repository": repository_of(segment.cwd) or known.get(key),
        "branch": segment.branch or None,
        "attribution": attribute(segment.branch),
        "first_event_at": iso(segment.first),
        "last_event_at": iso(segment.last),
        "wall_seconds": round(wall, 3),
        "active_seconds": round(segment.active, 3),
        "active_intervals": [[iso(start), iso(end)] for start, end in segment.intervals],
        "turns": segment.turns,
        "responses": segment.responses,
        "unfinished_responses": segment.unfinished,
        "tokens": {model: dict(counts) for model, counts in sorted(segment.tokens.items())},
    }


def session_record(session_id: str, reading: Reading, idle: float, previous: dict | None) -> dict:
    """The record of one session. Deterministic for a given transcript, so a rerun converges."""
    known = {s.get("key"): s.get("repository") for s in (previous or {}).get("segments", []) if s.get("repository")}
    segments = [segment_record(segment, known) for segment in reading.segments]
    first, last = span(reading)
    wall = (last - first) if first is not None and last is not None else 0.0
    return {
        "schema": SCHEMA,
        "session_id": session_id,
        "idle_threshold_seconds": idle,
        "first_event_at": iso(first),
        "last_event_at": iso(last),
        "wall_seconds": round(wall, 3),
        "active_seconds": round(reading.active, 3),
        "turns": sum(s["turns"] for s in segments),
        "responses": sum(s["responses"] for s in segments),
        "unfinished_responses": sum(s["unfinished_responses"] for s in segments),
        "subagent_transcripts": reading.subagents,
        "segments": segments,
    }


def session_path(root: Path, session_id: str) -> Path:
    if not SESSION_ID.match(session_id):
        raise ValueError("the session id is not a plain identifier")
    return root / "sessions" / f"{session_id}.json"


def read_session_record(root: Path, session_id: str) -> dict | None:
    try:
        loaded = json.loads(session_path(root, session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def write_session_record(root: Path, record: dict) -> Path:
    """Replace the session's record atomically, so a reader never sees half of one."""
    target = session_path(root, record["session_id"])
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(record, out, indent=2, sort_keys=True)
        out.write("\n")
    os.replace(temporary, target)
    return target


def all_records(root: Path) -> list[dict]:
    """Every session record in the ledger, skipping any file that does not parse."""
    records = []
    for path in sorted((root / "sessions").glob("*.json")):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(loaded, dict) and isinstance(loaded.get("segments"), list):
            records.append(loaded)
    return records


@contextlib.contextmanager
def session_lock(root: Path, session_id: str) -> Iterator[None]:
    """Hold the session's lock, so two firings of the hook for one session run in turn.

    Where the platform has no `fcntl` the lock is skipped: each write is still atomic, and
    the later firing reads at least as much of the transcript as the earlier one.
    """
    session_path(root, session_id)
    locks = root / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / f"{session_id}.lock").open("w") as handle:
        if fcntl is not None:
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield
