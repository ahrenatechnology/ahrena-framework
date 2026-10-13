#!/usr/bin/env python3
"""Tests of the cost comment: the merge by pass id, the rendered text, the hidden data, the
execution-file adapter, and both publishers end to end against a stub `gh`.

The renderer and the merge are pure functions and are tested as such. The publishers,
`publish.py` for CI and `record.py` for a developer's machine, run as subprocesses with the
stub first on PATH. No case touches the network.

The criteria of #157 (carried from barte-ai-services/barte-forge#37) these cases cover:
#157/AC-6 #157/AC-8 #157/AC-9 #157/AC-10

Run: python3 costs/runtime/test-publish.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
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
import comment  # noqa: E402
import money  # noqa: E402
import usage  # noqa: E402

REPO = "acme/widgets"
TABLE = money.PriceTable({"m": {"input": "4", "output": "20", "cache_write_5m": "5", "cache_write_1h": "8", "cache_read": "0.20"}}, {}, {})


def a_pass(identity: str, started: str = "2026-10-09T10:00:00Z", **over: object) -> dict:
    tokens = {"m": {"input": 1_000_000, "output": 100_000, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}}
    return {"id": identity, "kind": "development", "runner": "local", "started_at": started, "ended_at": started,
            "active_seconds": 1800, "tokens": tokens, **over}


def body_of(passes: list[dict], **payload: object) -> str:
    return comment.render({"schema": 1, "passes": passes, "branch": None, "brl_per_usd": None, **payload}, REPO, TABLE)


class Merge(unittest.TestCase):
    """#157/AC-8: one row per pass, and the same pass published twice changes nothing."""

    def test_the_first_pass_creates_the_list(self) -> None:
        self.assertEqual([p["id"] for p in comment.merge_passes([], [a_pass("session:a")])], ["session:a"])

    def test_a_second_pass_is_added_in_time_order(self) -> None:
        merged = comment.merge_passes([a_pass("session:b", "2026-10-09T12:00:00Z")], [a_pass("ci:1:review", "2026-10-09T11:00:00Z")])
        self.assertEqual([p["id"] for p in merged], ["ci:1:review", "session:b"])

    def test_the_same_pass_replaces_itself(self) -> None:
        first = comment.merge_passes([], [a_pass("session:a", active_seconds=60)])
        again = comment.merge_passes(first, [a_pass("session:a", active_seconds=120)])
        self.assertEqual([(p["id"], p["active_seconds"]) for p in again], [("session:a", 120)])
        self.assertEqual(comment.merge_passes(again, [a_pass("session:a", active_seconds=120)]), again)

    def test_a_missing_or_malformed_block_is_rebuilt_not_fatal(self) -> None:
        broken = ("", "no block here", f"{comment.MARKER}\n{comment.DATA_OPEN}\n{{not json\n-->", f"{comment.DATA_OPEN}\n{{\"passes\": 7}}\n-->",
                  f"{comment.DATA_OPEN}\n{{\"passes\": [1, {{\"id\": 2}}, {{\"id\": \"x\"}}]}}\n-->")
        for body in broken:
            self.assertEqual(comment.parse_payload(body)["passes"], [], body)
        rebuilt = comment.merge_payload(comment.parse_payload(broken[2]), [a_pass("session:a")], comment.Context(TABLE))
        self.assertEqual([p["id"] for p in rebuilt["passes"]], ["session:a"])

    def test_the_hidden_block_round_trips_whatever_the_strings_hold(self) -> None:
        awkward = a_pass("session:a--b-->c", run="<x>--y")
        body = body_of([awkward], branch="feat/1-a--b")
        hidden = body[body.index(comment.DATA_OPEN):]
        self.assertEqual(hidden.count("-->"), 1)
        found = comment.parse_payload(body)
        self.assertEqual((found["passes"], found["branch"]), ([awkward], "feat/1-a--b"))


class Render(unittest.TestCase):
    """#157/AC-8: one comment, a row per pass, a running total, and the gaps said plainly."""

    def test_a_row_per_pass_and_a_total(self) -> None:
        ci = a_pass("ci:99-1:review", "2026-10-09T11:00:00Z", kind="review", runner="ci", run="99-1")
        body = body_of([a_pass("session:abcdef123456"), ci])
        self.assertTrue(body.startswith(comment.MARKER))
        self.assertIn("| 2026-10-09 10:00 | desenvolvimento | sessão local `abcdef12` | `m` | 1.000.000 | 100.000 | 0 | 0 | 30min | US$ 6,00 |", body)
        self.assertIn("| 2026-10-09 11:00 | revisão | CI, run [99-1](https://github.com/acme/widgets/actions/runs/99) |", body)
        self.assertIn("| **Total** | **2 passes** |  |  | 2.000.000 | 200.000 | 0 | 0 | 1h 00min | **US$ 12,00** |", body)

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(body_of([a_pass("session:a")]), body_of([a_pass("session:a")]))

    def test_a_pass_with_an_unpriced_model_shows_as_unpriced(self) -> None:
        mixed = a_pass("session:a")
        mixed["tokens"]["mystery-model"] = {"input": 500, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}
        body = body_of([mixed])
        self.assertIn("US$ 6,00 (parcial)", body)
        self.assertIn("Sem preço na tabela para o modelo `mystery-model`: 500 tokens ficaram fora do custo.", body)

    def test_reais_only_with_an_exchange_rate(self) -> None:
        self.assertIn("Custo de tokens em reais: câmbio não configurado.", body_of([a_pass("session:a")]))
        self.assertIn("Custo de tokens em reais: **R$ 32,10**, com câmbio de 5,35 por dólar.", body_of([a_pass("session:a")], brl_per_usd=5.35))

    def test_a_publisher_without_a_rate_keeps_the_one_already_there(self) -> None:
        kept = comment.merge_payload({"passes": [], "brl_per_usd": 5.35, "branch": "feat/37-x"}, [], comment.Context(TABLE))
        self.assertEqual((kept["brl_per_usd"], kept["branch"]), (5.35, "feat/37-x"))

    def test_the_attribution_is_stated(self) -> None:
        self.assertIn("Atribuição: issue #37, pelo nome do branch `feat/37-cost`.", body_of([], branch="feat/37-cost"))
        self.assertIn("Sem issue atribuída: o branch `feat/review-agent` não carrega número de issue.", body_of([], branch="feat/review-agent"))

    def test_the_runner_s_own_cost_appears_only_when_it_differs(self) -> None:
        self.assertNotIn("Conferência", body_of([a_pass("ci:1:review", reported_cost_usd=6.004)]))
        self.assertIn("o passe `ci:1:review` informou US$ 9,50 por conta própria; pela tabela de preços, os mesmos tokens dão US$ 6,00.",
                      body_of([a_pass("ci:1:review", reported_cost_usd=9.5)]))

    def test_older_passes_fold_into_one_row_and_stay_in_the_total(self) -> None:
        many = [a_pass(f"session:{n:03d}", f"2026-10-09T10:{n:02d}:00Z") for n in range(45)]
        body = body_of(many)
        self.assertIn("| **Passes anteriores** | **5 passes** |", body)
        self.assertIn("| **Total** | **45 passes** |", body)
        self.assertEqual(body.count("sessão local"), 40)
        self.assertEqual(len(comment.parse_payload(body)["passes"]), 45)

    def test_a_comment_over_the_limit_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            body_of([a_pass(f"session:{n}" + "x" * 300) for n in range(400)])


class Execution(unittest.TestCase):
    """#157/AC-9: the same record from the execution file claude-code-action leaves."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "claude-execution-output.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def assistant(self, identity: str, counts: dict, parent: str | None = None) -> dict:
        message = {"id": identity, "model": "m", "content": [{"type": "text", "text": support.SECRETS[1]}], "usage": support.usage_block(counts)}
        return {"type": "assistant", "session_id": "ci-session", "parent_tool_use_id": parent, "message": message}

    def write(self, *messages: dict) -> Path:
        self.path.write_text(json.dumps(list(messages), indent=2))
        return self.path

    def result(self, **over: object) -> dict:
        model_usage = {"m": {"inputTokens": 1000, "outputTokens": 900, "cacheReadInputTokens": 5000, "cacheCreationInputTokens": 300, "costUSD": 0.5}}
        return {"type": "result", "subtype": "success", "duration_ms": 90_000, "num_turns": 4, "total_cost_usd": 0.5,
                "result": support.SECRETS[1], "modelUsage": model_usage, **over}

    def test_the_result_message_is_the_source_and_covers_sub_agents(self) -> None:
        main = self.assistant("a", {"input": 400, "output": 1, "cache_write_1h": 200})
        sub = self.assistant("b", {"input": 100, "output": 1}, parent="toolu_1")
        run = usage.read_execution(self.write({"type": "system", "subtype": "init"}, main, main, sub, self.result()), {})
        self.assertEqual(run.tokens, {"m": {"input": 1000, "output": 900, "cache_write_5m": 100, "cache_write_1h": 200, "cache_read": 5000}})
        self.assertEqual((run.source, run.duration, run.turns, run.reported_cost), ("result.modelUsage", 90.0, 4, 0.5))

    def test_without_model_usage_the_messages_are_summed_once_each(self) -> None:
        main = self.assistant("a", {"input": 400, "output": 7})
        sub = self.assistant("b", {"input": 100, "output": 1}, parent="toolu_1")
        run = usage.read_execution(self.write(main, main, sub, {"type": "result", "duration_ms": 1000}), {})
        self.assertEqual((run.tokens["m"]["input"], run.tokens["m"]["output"], run.source), (500, 8, "assistant-messages"))

    def test_a_file_that_is_not_an_array_is_an_error(self) -> None:
        self.path.write_text("{}")
        with self.assertRaises(ValueError):
            usage.read_execution(self.path, {})


class Publishers(unittest.TestCase):
    """#157/AC-8, #157/AC-9, #157/AC-10: both publishers, end to end, against a stub forge."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.box = support.Sandbox(self.root)
        self.clone = self.box.clone("clone", f"git@github.com:{REPO}.git", "feat/37-cost")
        self.execution = self.root / "claude-execution-output.json"
        result = {"type": "result", "duration_ms": 60_000, "total_cost_usd": 0.004,
                  "modelUsage": {"claude-opus-5-5": {"inputTokens": 1000, "outputTokens": 0, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}}
        self.execution.write_text(json.dumps([{"type": "assistant", "message": {"id": "x", "content": [{"type": "text", "text": support.SECRETS[1]}]}}, result]))

    def tearDown(self) -> None:
        self.box.close()
        self.tmp.cleanup()

    def open_pull_request(self, branch: str = "feat/37-cost", number: int = 5) -> None:
        self.box.set_forge(pulls={REPO: {branch: [{"number": number, "state": "OPEN"}]}})

    def ci(self, run_id: str, *extra: str, kind: str = "review") -> "support.subprocess.CompletedProcess":
        return self.box.run("publish.py", "--execution-file", str(self.execution), "--repository", REPO, "--pull-request", "5",
                            "--kind", kind, "--run-id", run_id, *extra)

    def session(self, name: str, hour: str, branch: str = "feat/37-cost", *arguments: str) -> None:
        t = support.Transcript(cwd=str(self.clone), branch=branch).prompt(f"2026-10-09T{hour}:00:00.000Z")
        t.response(f"2026-10-09T{hour}:01:00.000Z", f"{name}-m", {"input": 1000})
        result = self.box.record(t.write(self.root / "projects" / f"{name}.jsonl"), name, *arguments)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def comments(self) -> list[dict]:
        return self.box.forge()["comments"]

    def passes(self) -> list[str]:
        return [p["id"] for p in comment.parse_payload(self.comments()[0]["body"])["passes"]]

    def writes(self) -> int:
        return sum(1 for call in self.box.forge().get("calls", []) if "--method" in call)

    def test_ci_creates_the_comment_then_publishing_the_same_run_changes_nothing(self) -> None:
        first = self.ci("900-1")
        self.assertIn("cost comment created on acme/widgets#5 for pass ci:900-1:review", first.stdout)
        body = self.comments()[0]["body"]
        self.assertIn("| revisão | CI, run [900-1](https://github.com/acme/widgets/actions/runs/900) | `claude-opus-5-5` | 1.000 |", body)
        again = self.ci("900-1")
        self.assertIn("cost comment unchanged", again.stdout)
        self.assertEqual((len(self.comments()), self.comments()[0]["body"], self.writes()), (1, body, 1))

    def test_ci_needs_no_ledger_and_adds_to_what_is_already_there(self) -> None:
        self.ci("900-1")
        self.ci("900-2")
        self.ci("901-1", kind="auto-fix")
        self.assertEqual(self.passes(), ["ci:900-1:review", "ci:900-2:review", "ci:901-1:auto-fix"])
        self.assertEqual(len(self.comments()), 1)
        self.assertFalse(self.box.home.exists())

    def test_ci_failure_is_a_warning_unless_strict(self) -> None:
        self.box.set_forge(fail=True)
        soft, hard = self.ci("900-1"), self.ci("900-1", "--strict")
        self.assertEqual((soft.returncode, hard.returncode), (0, 1))
        self.assertIn("::warning::cost not published", soft.stdout)

    def test_ci_dry_run_prints_the_pass_and_calls_nothing(self) -> None:
        printed = json.loads(self.ci("900-1", "--dry-run").stdout)
        self.assertEqual((printed["id"], printed["runner"], printed["active_seconds"]), ("ci:900-1:review", "ci", 60.0))
        self.assertNotIn("calls", self.box.forge())

    def test_the_hook_publishes_when_the_branch_has_an_open_pull_request(self) -> None:
        self.open_pull_request()
        self.session("s1", "10")
        self.assertEqual(self.passes(), ["session:s1"])
        self.assertIn("Atribuição: issue #37, pelo nome do branch `feat/37-cost`.", self.comments()[0]["body"])

    def test_firing_again_for_the_same_session_writes_nothing_more(self) -> None:
        self.open_pull_request()
        self.session("s1", "10")
        writes = self.writes()
        self.session("s1", "10")
        self.assertEqual((self.writes(), len(self.comments())), (writes, 1))

    def test_a_pull_request_opened_later_gets_the_passes_recorded_before_it(self) -> None:
        """#157/AC-10: offline, or before the pull request, it records; the next pass catches up."""
        self.session("early", "09")
        self.box.set_forge(fail=True)
        self.session("offline", "10")
        self.assertEqual(self.comments(), [])
        self.box.set_forge(fail=False)
        self.open_pull_request()
        self.session("late", "11")
        self.assertEqual(self.passes(), ["session:early", "session:offline", "session:late"])

    def test_session_end_publishes_a_branch_whose_last_turn_could_not(self) -> None:
        self.open_pull_request()
        self.box.set_forge(fail=True)
        self.session("s1", "10")
        self.box.set_forge(fail=False)
        self.session("s1", "10")
        self.assertEqual(self.comments(), [])
        t = self.root / "projects" / "s1.jsonl"
        self.assertEqual(self.box.record(t, "s1", EVENT="SessionEnd").returncode, 0)
        self.assertEqual(self.passes(), ["session:s1"])
        writes = self.writes()
        self.box.record(t, "s1", EVENT="SessionEnd")
        self.assertEqual(self.writes(), writes)

    def test_local_and_ci_passes_share_the_one_comment(self) -> None:
        self.open_pull_request()
        self.ci("900-1")
        self.session("s1", "10")
        self.assertEqual((len(self.comments()), sorted(self.passes())), (1, ["ci:900-1:review", "session:s1"]))

    def test_nothing_is_published_without_an_open_pull_request_or_on_trunk(self) -> None:
        self.session("s1", "10")
        self.open_pull_request(branch="main")
        self.session("s2", "11", "main")
        self.assertEqual(self.comments(), [])

    def test_no_publish_and_the_configuration_switch_keep_the_forge_untouched(self) -> None:
        self.open_pull_request()
        self.session("s1", "10", "feat/37-cost", "--no-publish")
        self.box.env["AHRENA_COSTS_PUBLISH"] = "0"
        self.session("s2", "11")
        self.assertNotIn("calls", self.box.forge())

    def test_two_comments_left_by_a_race_converge_on_one(self) -> None:
        first, second = body_of([a_pass("session:a")]), body_of([a_pass("session:b", "2026-10-09T12:00:00Z")])
        self.box.set_forge(comments=[{"id": 1, "pr": 5, "body": first}, {"id": 2, "pr": 5, "body": second}, {"id": 3, "pr": 5, "body": "a person's comment"}])
        self.ci("900-1")
        self.assertEqual([c["id"] for c in self.comments()], [1, 3])
        self.assertEqual(sorted(self.passes()), ["ci:900-1:review", "session:a", "session:b"])

    def test_no_text_of_the_run_or_the_session_reaches_the_comment(self) -> None:
        """#157/AC-6, for the published record."""
        self.open_pull_request()
        self.ci("900-1")
        self.session("s1", "10")
        body = self.comments()[0]["body"]
        for secret in (*support.SECRETS, str(self.clone), "/home/"):
            self.assertNotIn(secret, body)
        allowed = {"id", "kind", "runner", "run", "started_at", "ended_at", "active_seconds", "tokens", "reported_cost_usd", "source", "output_lower_bound"}
        for entry in comment.parse_payload(body)["passes"]:
            self.assertLessEqual(set(entry), allowed)


if __name__ == "__main__":
    unittest.main(verbosity=1)
