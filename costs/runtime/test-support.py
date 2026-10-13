"""Synthetic fixtures shared by the three suites, which load this file by path: transcripts written by hand, and a stub `gh`.

Nothing here is copied from a real session. A transcript is built record by record with the
fields the reader uses, and with text planted where a real one holds a prompt, a response, a
tool call and a file, so a test can prove none of it reaches the ledger or a comment.

The stub `gh` is a script placed first on PATH. It keeps pull requests and comments in a JSON
file and answers the calls `comment.py` and `report.py` make, so no suite touches the network.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRETS = ("PROMPT-SECRET", "RESPONSE-SECRET", "TOOL-INPUT-SECRET", "TOOL-OUTPUT-SECRET", "FILE-CONTENT-SECRET")

STUB = r'''#!/usr/bin/env python3
import json, os, sys
path = os.environ["GH_STUB_STATE"]
state = json.load(open(path))
args = sys.argv[1:]
state.setdefault("calls", []).append(args)
def save():
    json.dump(state, open(path, "w"))
def flag(name):
    return args[args.index(name) + 1] if name in args else None
if state.get("fail"):
    save(); sys.stderr.write("gh: not authenticated\n"); sys.exit(1)
if args[:2] == ["pr", "list"]:
    pulls = state.get("pulls", {}).get(flag("--repo"), {}).get(flag("--head"), [])
    if flag("--state") == "open":
        pulls = [p for p in pulls if p.get("state", "OPEN") == "OPEN"]
    save(); print(json.dumps(pulls)); sys.exit(0)
if args[0] == "api":
    parts = args[1].split("/")
    comments = state.setdefault("comments", [])
    method = flag("--method") or "GET"
    if method == "GET":
        number = int(parts[4])
        save()
        for c in comments:
            if c["pr"] == number:
                print(json.dumps({"id": c["id"], "body": c["body"]}))
        sys.exit(0)
    if method == "POST":
        body = json.load(sys.stdin)["body"]
        state["next"] = state.get("next", 100) + 1
        comments.append({"id": state["next"], "pr": int(parts[4]), "body": body})
    elif method == "PATCH":
        body = json.load(sys.stdin)["body"]
        for c in comments:
            if c["id"] == int(parts[5]):
                c["body"] = body
    elif method == "DELETE":
        state["comments"] = [c for c in comments if c["id"] != int(parts[5])]
    save(); print("{}"); sys.exit(0)
save(); sys.exit(2)
'''


def usage_block(counts: dict, **extra: object) -> dict:
    """An API usage object from the five kinds."""
    written = counts.get("cache_write_5m", 0) + counts.get("cache_write_1h", 0)
    return {
        "input_tokens": counts.get("input", 0),
        "output_tokens": counts.get("output", 0),
        "cache_creation_input_tokens": written,
        "cache_read_input_tokens": counts.get("cache_read", 0),
        "cache_creation": {"ephemeral_5m_input_tokens": counts.get("cache_write_5m", 0), "ephemeral_1h_input_tokens": counts.get("cache_write_1h", 0)},
        "speed": "standard",
        **extra,
    }


class Transcript:
    """A transcript under construction: one place, one clock, records appended in order."""

    def __init__(self, cwd: str = "/work/repo", branch: str = "feat/37-cost-per-issue", sidechain: bool = False) -> None:
        self.cwd, self.branch, self.sidechain = cwd, branch, sidechain
        self.records: list[dict] = []

    def base(self, kind: str, at: str) -> dict:
        return {"type": kind, "timestamp": at, "cwd": self.cwd, "gitBranch": self.branch, "isSidechain": self.sidechain, "sessionId": "s", "uuid": f"u{len(self.records)}"}

    def prompt(self, at: str) -> "Transcript":
        self.records.append({**self.base("user", at), "message": {"role": "user", "content": f"{SECRETS[0]} please read /home/someone/private/{SECRETS[4]}.txt"}})
        return self

    def response(self, at: str, message_id: str, counts: dict, **options: object) -> "Transcript":
        """One record of an API response. Call it twice with one id to repeat the response."""
        usage = usage_block(counts, **options.get("usage", {}))
        content = [{"type": "text", "text": SECRETS[1]}, {"type": "tool_use", "name": "Read", "input": {"file_path": f"/secret/{SECRETS[2]}"}}]
        message = {"id": message_id, "model": options.get("model", "claude-opus-5-5"), "role": "assistant", "content": content, "stop_reason": options.get("stop", "tool_use"), "usage": usage}
        self.records.append({**self.base("assistant", at), "message": message, "requestId": f"req-{message_id}"})
        return self

    def tool_result(self, at: str) -> "Transcript":
        content = [{"type": "tool_result", "content": SECRETS[3]}]
        self.records.append({**self.base("user", at), "message": {"role": "user", "content": content}, "toolUseResult": {"file": {"content": SECRETS[4]}}})
        return self

    def raw(self, line: str) -> "Transcript":
        self.records.append({"__raw__": line})
        return self

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [r["__raw__"] if "__raw__" in r else json.dumps(r) for r in self.records]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


def runs(script: Path) -> bool:
    try:
        return subprocess.run([str(script), "--version"], capture_output=True, timeout=10, env={"GH_STUB_STATE": os.devnull}).returncode in (0, 1, 2)
    except OSError:
        return False


def install_stub(tools: Path) -> bool:
    """Write the stub `gh` into a directory; False when the filesystem will not execute it."""
    tools.mkdir(parents=True, exist_ok=True)
    stub = tools / "gh"
    stub.write_text(STUB.replace("#!/usr/bin/env python3", f"#!{sys.executable}"), encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    git = shutil.which("git")
    if git and not (tools / "git").exists():
        os.symlink(git, tools / "git")
    return runs(stub)


def gh_directory(root: Path) -> Path:
    """A PATH directory holding git and the stub `gh`.

    A temporary directory mounted `noexec` cannot hold the stub, so the next writable place
    that executes is used and removed with the sandbox.
    """
    for base in (root, Path("/var/tmp"), Path("/dev/shm")):
        if not base.is_dir() or not os.access(base, os.W_OK):
            continue
        tools = base / "tools-gh" if base == root else Path(tempfile.mkdtemp(prefix="ahrena-costs-test-", dir=base))
        if install_stub(tools):
            return tools
        shutil.rmtree(tools, ignore_errors=True)
    raise RuntimeError("no writable directory on this machine executes a script")


def git_directory(root: Path) -> Path:
    """A PATH directory holding git and nothing else: a machine with no `gh`."""
    tools = root / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    git = shutil.which("git")
    if git and not (tools / "git").exists():
        os.symlink(git, tools / "git")
    return tools


class Sandbox:
    """A temporary ledger, a stub forge and the environment that points the scripts at them."""

    def __init__(self, root: Path, with_gh: bool = True) -> None:
        self.root = root
        self.home = root / "ledger"
        self.state = root / "gh-state.json"
        self.state.write_text(json.dumps({"pulls": {}, "comments": []}), encoding="utf-8")
        self.tools = gh_directory(root) if with_gh else git_directory(root)
        self.env = {
            "PATH": str(self.tools),
            "HOME": str(root / "home"),
            "AHRENA_COSTS_HOME": str(self.home),
            "GH_STUB_STATE": str(self.state),
        }

    def close(self) -> None:
        if self.root not in self.tools.parents:
            shutil.rmtree(self.tools, ignore_errors=True)

    def forge(self) -> dict:
        return json.loads(self.state.read_text(encoding="utf-8"))

    def set_forge(self, **changes: object) -> None:
        self.state.write_text(json.dumps({**self.forge(), **changes}), encoding="utf-8")

    def run(self, script: str, *arguments: str, stdin: str = "", **env: str) -> subprocess.CompletedProcess:
        command = [sys.executable, str(HERE / script), *arguments]
        return subprocess.run(command, input=stdin, capture_output=True, text=True, env={**self.env, **env}, timeout=60)

    def record(self, transcript: Path, session_id: str, *arguments: str, **env: str) -> subprocess.CompletedProcess:
        event = json.dumps({"session_id": session_id, "transcript_path": str(transcript), "cwd": "/work/repo", "hook_event_name": env.pop("EVENT", "Stop")})
        return self.run("record.py", "--foreground", *arguments, stdin=event, **env)

    def session(self, session_id: str) -> dict:
        return json.loads((self.home / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

    def clone(self, name: str, remote: str, branch: str) -> Path:
        """A real git working copy with an `origin` remote, so the repository is read, not stubbed."""
        path = self.root / name
        path.mkdir(parents=True)
        for command in (["init", "-q", "-b", branch], ["remote", "add", "origin", remote]):
            subprocess.run(["git", "-C", str(path), *command], check=True, capture_output=True)
        return path
