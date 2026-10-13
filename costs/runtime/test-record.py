#!/usr/bin/env python3
"""Tests of the recorder: what the hook reads from a transcript, what it writes to the ledger,
and what it does when anything goes wrong.

Every case runs `record.py` as a subprocess, the way Claude Code runs it, against a transcript
written by hand and a ledger in a temporary directory. No network, no `gh`, no real session.

The criteria of barte-ai-services/barte-forge#37 (origem deste plugin) these cases cover:
#37/AC-1 #37/AC-2 #37/AC-3 #37/AC-6 #37/AC-7 #37/AC-10

Run: python3 costs/runtime/test-record.py
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = load("support", HERE / "test-support.py")
import ledger  # noqa: E402
import usage  # noqa: E402

OPUS = "claude-opus-5-5"
ONE = {"input": 100, "output": 20, "cache_write_5m": 30, "cache_write_1h": 40, "cache_read": 500}


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.box = support.Sandbox(self.root, with_gh=False)
        self.transcript = self.root / "projects" / "p" / "sess-1.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def recorded(self, transcript: "support.Transcript", session: str = "sess-1", **env: str) -> dict:
        result = self.box.record(transcript.write(self.transcript), session, **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.box.session(session)

    def tokens(self, record: dict) -> dict:
        total: dict = {}
        for segment in record["segments"]:
            usage.merge_tokens(total, segment["tokens"])
        return total


class Usage(Case):
    """#37/AC-1: tokens by model and by kind, sub-agents included, nothing counted twice."""

    def test_tokens_are_recorded_by_model_and_kind(self) -> None:
        t = support.Transcript().prompt("2026-10-09T10:00:00.000Z")
        t.response("2026-10-09T10:00:10.000Z", "m1", ONE)
        t.response("2026-10-09T10:00:20.000Z", "m2", {"input": 7, "output": 3}, model="claude-haiku-4-5-20251001")
        record = self.recorded(t)
        self.assertEqual(self.tokens(record), {OPUS: ONE, "claude-haiku-4-5-20251001": {**usage.empty_tokens(), "input": 7, "output": 3}})
        self.assertEqual(record["responses"], 2)
        self.assertEqual(record["turns"], 1)

    def test_a_response_written_as_several_records_is_counted_once(self) -> None:
        t = support.Transcript().prompt("2026-10-09T10:00:00.000Z")
        for second in (10, 11, 12):
            t.response(f"2026-10-09T10:00:{second}.000Z", "m1", ONE)
        self.assertEqual(self.tokens(self.recorded(t)), {OPUS: ONE})

    def test_streaming_snapshots_keep_the_largest_counter_and_are_flagged(self) -> None:
        t = support.Transcript()
        t.response("2026-10-09T10:00:10.000Z", "m1", {**ONE, "output": 1}, stop=None)
        t.response("2026-10-09T10:00:11.000Z", "m1", {**ONE, "output": 9}, stop=None)
        record = self.recorded(t)
        self.assertEqual(self.tokens(record)[OPUS]["output"], 9)
        self.assertEqual(record["unfinished_responses"], 1)

    def test_sub_agent_transcripts_of_the_session_are_included(self) -> None:
        sub = support.Transcript(sidechain=True).response("2026-10-09T10:01:00.000Z", "sub-1", {"input": 11, "output": 1}, stop=None)
        sub.write(self.transcript.with_suffix("") / "subagents" / "agent-abc.jsonl")
        other = support.Transcript(sidechain=True).response("2026-10-09T10:01:00.000Z", "x", {"input": 999})
        other.write(self.transcript.parent / "another-session" / "subagents" / "agent-zzz.jsonl")
        record = self.recorded(support.Transcript().response("2026-10-09T10:00:10.000Z", "m1", ONE))
        self.assertEqual(self.tokens(record)[OPUS]["input"], 111)
        self.assertEqual(record["subagent_transcripts"], 1)

    def test_recording_twice_converges_on_one_identical_record(self) -> None:
        t = support.Transcript().prompt("2026-10-09T10:00:00.000Z").response("2026-10-09T10:00:10.000Z", "m1", ONE)
        self.recorded(t)
        first = (self.box.home / "sessions" / "sess-1.json").read_bytes()
        self.recorded(t)
        self.assertEqual((self.box.home / "sessions" / "sess-1.json").read_bytes(), first)
        self.assertEqual(len(list((self.box.home / "sessions").glob("*.json"))), 1)

    def test_a_priced_variant_gets_its_own_key(self) -> None:
        t = support.Transcript()
        t.response("2026-10-09T10:00:10.000Z", "m1", {"input": 100001}, model="claude-haiku-5-5")
        t.response("2026-10-09T10:00:11.000Z", "m2", {"input": 5}, model="claude-haiku-5-5")
        t.response("2026-10-09T10:00:12.000Z", "m3", {"input": 5}, usage={"speed": "fast"})
        self.assertEqual(sorted(self.tokens(self.recorded(t))), ["claude-haiku-5-5", "claude-haiku-5-5:over-100k", "claude-opus-5-5:fast"])


class Attribution(Case):
    """#37/AC-2: the issue comes from the branch name, or the segment is unattributed. Never a guess."""

    def test_the_issue_is_the_number_the_branch_name_carries(self) -> None:
        record = self.recorded(support.Transcript(branch="fix/412-rounding").response("2026-10-09T10:00:10.000Z", "m1", ONE))
        self.assertEqual(record["segments"][0]["attribution"], {"issue": 412, "method": "branch"})

    def test_names_that_only_look_like_an_issue_are_not_attributed(self) -> None:
        for branch, reason in (("main", "default-branch"), ("HEAD", "no-branch"), ("feat/pr-review-agent-834dba", "no-issue-in-branch-name"),
                               ("fix-12-thing", "no-issue-in-branch-name"), ("feat/issue-12", "no-issue-in-branch-name"), ("12-thing", "no-issue-in-branch-name")):
            found = ledger.attribute(branch)
            self.assertEqual((found["issue"], found["method"], found["reason"]), (None, "unattributed", reason), branch)

    def test_an_unattributed_segment_keeps_its_branch_for_a_later_report(self) -> None:
        record = self.recorded(support.Transcript(branch="feat/pr-review-agent").response("2026-10-09T10:00:10.000Z", "m1", ONE))
        self.assertEqual(record["segments"][0]["branch"], "feat/pr-review-agent")

    def test_a_session_that_moves_between_branches_is_split_by_branch(self) -> None:
        t = support.Transcript(branch="feat/1-a").response("2026-10-09T10:00:10.000Z", "m1", {"input": 1})
        moved = support.Transcript(cwd="/work/other", branch="main").response("2026-10-09T10:00:20.000Z", "m2", {"input": 2})
        t.records += moved.records
        found = {s["branch"]: (s["attribution"]["issue"], s["tokens"][OPUS]["input"]) for s in self.recorded(t)["segments"]}
        self.assertEqual(found, {"feat/1-a": (1, 1), "main": (None, 2)})

    def test_the_branch_pattern_is_the_one_the_branch_name_gate_uses(self) -> None:
        gate = HERE.parents[1] / "contributing" / "hooks" / "check-branch-name.py"
        if not gate.is_file():
            self.skipTest("the contributing plugin is not in this checkout")
        self.assertEqual(ledger.BRANCH.pattern, load("check_branch_name", gate).BRANCH.pattern)

    def test_the_repository_is_read_from_the_origin_remote(self) -> None:
        for name, remote in (("ssh", "git@github.com:acme/widgets.git"), ("https", "https://github.com/acme/widgets")):
            clone = self.box.clone(name, remote, "feat/37-x")
            self.assertEqual(ledger.repository_of(str(clone)), "acme/widgets")
        gone = str(clone / ".claude" / "worktrees" / "removed")
        self.assertEqual(ledger.repository_of(gone), "acme/widgets")
        self.assertIsNone(ledger.repository_of(str(self.root / "never-existed")))

    def test_a_repository_resolved_once_survives_its_worktree(self) -> None:
        clone = self.box.clone("clone", "git@github.com:acme/widgets.git", "feat/37-x")
        t = support.Transcript(cwd=str(clone), branch="feat/37-x").response("2026-10-09T10:00:10.000Z", "m1", ONE)
        self.assertEqual(self.recorded(t)["segments"][0]["repository"], "acme/widgets")
        (clone / ".git").rename(clone / "gone")
        self.assertEqual(self.recorded(t)["segments"][0]["repository"], "acme/widgets")


class Time(Case):
    """#37/AC-3: wall-clock, and active time that leaves out gaps above the stated threshold."""

    def script(self) -> "support.Transcript":
        t = support.Transcript().prompt("2026-10-09T10:00:00.000Z")
        t.response("2026-10-09T10:02:00.000Z", "m1", ONE)
        t.tool_result("2026-10-09T10:06:00.000Z")
        return t.response("2026-10-09T11:06:00.000Z", "m2", ONE)

    def test_gaps_over_the_default_threshold_are_left_out(self) -> None:
        record = self.recorded(self.script())
        self.assertEqual(record["idle_threshold_seconds"], 300)
        self.assertEqual(record["wall_seconds"], 3960)
        self.assertEqual(record["active_seconds"], 360)
        self.assertEqual(record["segments"][0]["active_intervals"], [["2026-10-09T10:00:00Z", "2026-10-09T10:06:00Z"]])

    def test_the_threshold_is_configuration(self) -> None:
        self.assertEqual(self.recorded(self.script(), AHRENA_COSTS_IDLE_SECONDS="3600")["active_seconds"], 3960)
        self.box.home.mkdir(parents=True, exist_ok=True)
        (self.box.home / "config.json").write_text(json.dumps({"idle_threshold_seconds": 150}))
        self.assertEqual(self.recorded(self.script())["active_seconds"], 120)

    def test_events_out_of_order_do_not_produce_negative_time(self) -> None:
        t = support.Transcript().response("2026-10-09T10:01:00.000Z", "m1", ONE).prompt("2026-10-09T10:00:00.000Z")
        self.assertEqual(self.recorded(t)["active_seconds"], 60)


class Privacy(Case):
    """#37/AC-6: no prompt, no response, no tool input or output, no file content, no path."""

    def test_nothing_from_the_conversation_reaches_the_ledger(self) -> None:
        t = support.Transcript(cwd="/home/someone/private-project").prompt("2026-10-09T10:00:00.000Z")
        t.response("2026-10-09T10:00:10.000Z", "m1", ONE).tool_result("2026-10-09T10:00:20.000Z")
        self.recorded(t)
        written = "".join(p.read_text() for p in self.box.home.rglob("*") if p.is_file())
        for secret in (*support.SECRETS, "private-project", "/home/someone"):
            self.assertNotIn(secret, written)

    def test_a_record_holds_only_the_declared_fields(self) -> None:
        record = self.recorded(support.Transcript().response("2026-10-09T10:00:10.000Z", "m1", ONE))
        self.assertEqual(sorted(record), ["active_seconds", "first_event_at", "idle_threshold_seconds", "last_event_at", "responses", "schema",
                                          "segments", "session_id", "subagent_transcripts", "turns", "unfinished_responses", "wall_seconds"])
        self.assertEqual(sorted(record["segments"][0]), ["active_intervals", "active_seconds", "attribution", "branch", "first_event_at", "key",
                                                         "last_event_at", "repository", "responses", "tokens", "turns", "unfinished_responses", "wall_seconds"])


class NeverHurts(Case):
    """#37/AC-7: standard library only, and no input makes the hook fail the session."""

    def test_every_bad_input_exits_zero_and_is_logged(self) -> None:
        missing = json.dumps({"session_id": "s", "transcript_path": str(self.root / "absent.jsonl")})
        hostile = json.dumps({"session_id": "../../escape", "transcript_path": str(support.Transcript().write(self.transcript))})
        for stdin in ("", "not json", "[1, 2]", missing, hostile):
            result = self.box.run("record.py", "--foreground", stdin=stdin)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""), stdin)
        self.assertGreaterEqual(len((self.box.home / "errors.log").read_text().splitlines()), 5)
        self.assertFalse((self.root / "escape.json").exists())

    def test_an_unknown_flag_still_exits_zero(self) -> None:
        self.assertEqual(self.box.run("record.py", "--no-such-flag").returncode, 0)

    def test_broken_lines_in_a_transcript_are_skipped(self) -> None:
        t = support.Transcript().raw("{not json").raw("[]").raw('"text"').response("2026-10-09T10:00:10.000Z", "m1", ONE).raw("")
        self.assertEqual(self.tokens(self.recorded(t)), {OPUS: ONE})

    def test_the_hook_returns_at_once_and_a_detached_worker_records(self) -> None:
        path = support.Transcript().response("2026-10-09T10:00:10.000Z", "m1", ONE).write(self.transcript)
        result = self.box.run("record.py", stdin=json.dumps({"session_id": "bg", "transcript_path": str(path)}))
        self.assertEqual(result.returncode, 0)
        target = self.box.home / "sessions" / "bg.json"
        deadline = time.time() + 20
        while not target.exists() and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(target.exists())

    def test_without_gh_the_session_is_recorded_and_nothing_fails(self) -> None:
        """#37/AC-10, the offline half: no `gh` on PATH, the record is still written."""
        clone = self.box.clone("clone", "git@github.com:acme/widgets.git", "feat/37-x")
        t = support.Transcript(cwd=str(clone), branch="feat/37-x").response("2026-10-09T10:00:10.000Z", "m1", ONE)
        self.assertEqual(self.tokens(self.recorded(t)), {OPUS: ONE})
        self.assertFalse((self.box.home / "errors.log").exists())

    def test_the_runtime_imports_only_the_standard_library(self) -> None:
        local = {p.stem for p in HERE.glob("*.py")}
        for path in HERE.glob("*.py"):
            if path.name.startswith("test-"):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) else []
                for name in names:
                    top = str(name).split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top in local, f"{path.name} imports {name}")

    def test_the_plugin_declares_the_hook_on_both_events(self) -> None:
        declared = json.loads((HERE / "hooks.json").read_text())["hooks"]
        for event in ("Stop", "SessionEnd"):
            command = declared[event][0]["hooks"][0]["command"]
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/runtime/record.py", command)
        manifest = json.loads((HERE.parent / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["hooks"], "./runtime/hooks.json")


if __name__ == "__main__":
    unittest.main(verbosity=1)
