#!/usr/bin/env python3
"""Tests of the money and of the report: the price table as data, what is computed from it,
what is said when a rate is not configured, and what the report prints for one issue and for
a repository.

The ledger is written by `record.py` from synthetic transcripts, in a temporary directory, and
`report.py` runs as a subprocess. `gh` is a stub; no case touches the network.

The criteria of #157 (carried from barte-ai-services/barte-forge#37) these cases cover:
#157/AC-2 #157/AC-4 #157/AC-5

Run: python3 costs/runtime/test-report.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from decimal import Decimal
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
report = load("report", HERE / "report.py")
import money  # noqa: E402
import usage  # noqa: E402

REPO = "acme/widgets"
MILLION = {"input": 1_000_000, "output": 1_000_000, "cache_write_5m": 1_000_000, "cache_write_1h": 1_000_000, "cache_read": 1_000_000}


class PriceTable(unittest.TestCase):
    """#157/AC-4: the price table is data, and every price names its source and its date."""

    def setUp(self) -> None:
        self.data = json.loads((HERE / "prices.json").read_text())

    def test_every_model_has_the_five_prices_a_source_and_a_date(self) -> None:
        self.assertGreater(len(self.data["models"]), 5)
        for model, entry in self.data["models"].items():
            for kind in usage.KINDS:
                self.assertGreater(Decimal(entry[kind]), 0, f"{model} {kind}")
            self.assertTrue(entry["source"].startswith("https://"), model)
            self.assertRegex(entry["read_on"], r"^\d{4}-\d{2}-\d{2}$", model)

    def test_every_alias_and_tier_points_at_an_entry(self) -> None:
        targets = [*self.data["aliases"].values(), *(tier["key"] for tier in self.data["prompt_tiers"].values())]
        for target in targets:
            self.assertIn(target, self.data["models"])

    def test_no_price_lives_in_code(self) -> None:
        for name in ("money.py", "usage.py", "ledger.py", "report.py", "comment.py", "publish.py", "record.py"):
            self.assertIsNone(re.search(r"claude-(opus|sonnet|haiku|fable)", (HERE / name).read_text()), name)


class Money(unittest.TestCase):
    """#157/AC-4: cost from the table; a missing price or rate is said, never zero."""

    def setUp(self) -> None:
        self.table = money.PriceTable(
            {"m": {"input": "4", "output": "20", "cache_write_5m": "5", "cache_write_1h": "8", "cache_read": "0.20"}}, {"m-dated": "m"}, {})

    def test_tokens_are_priced_by_kind_per_million(self) -> None:
        self.assertEqual(money.token_cost({"m": MILLION}, self.table).usd, Decimal("37.20"))
        self.assertEqual(money.token_cost({"m-dated": {"output": 500_000}}, self.table).usd, Decimal("10"))

    def test_a_model_with_no_price_is_named_and_left_out(self) -> None:
        cost = money.token_cost({"m": {"input": 1_000_000}, "mystery": {"input": 10, "output": 5}}, self.table)
        self.assertEqual((cost.usd, cost.unpriced), (Decimal("4"), {"mystery": 15}))

    def test_without_rates_only_the_dollar_token_cost_exists(self) -> None:
        parts = money.development_cost(Decimal("10"), Decimal("2"), money.Rates())
        self.assertEqual(parts["token_usd"], Decimal("10"))
        for name in ("token_brl", "time_usd", "time_brl", "development_usd", "development_brl"):
            self.assertIsNone(parts[name], name)

    def test_development_cost_is_tokens_plus_active_hours_at_the_hourly_rate(self) -> None:
        parts = money.development_cost(Decimal("10"), Decimal("2"), money.Rates(5.0, 200.0, "BRL"))
        self.assertEqual((parts["token_brl"], parts["time_brl"], parts["development_brl"]), (Decimal("50"), Decimal("400"), Decimal("450")))
        self.assertEqual((parts["time_usd"], parts["development_usd"]), (Decimal("80"), Decimal("90")))

    def test_an_hourly_rate_in_reais_without_an_exchange_rate_gives_no_sum(self) -> None:
        parts = money.development_cost(Decimal("10"), Decimal("2"), money.Rates(None, 200.0, "BRL"))
        self.assertEqual(parts["time_brl"], Decimal("400"))
        for name in ("token_brl", "time_usd", "development_usd", "development_brl"):
            self.assertIsNone(parts[name], name)

    def test_overlapping_active_time_is_counted_once(self) -> None:
        self.assertEqual(report.union_seconds([(0, 100), (50, 150), (300, 310)]), 160)


class Report(unittest.TestCase):
    """#157/AC-5: one issue or every issue of a repository, and the unattributed part of the total."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.box = support.Sandbox(self.root)
        self.clone = self.box.clone("clone", f"git@github.com:{REPO}.git", "main")
        self.session("s1", "feat/37-cost", "10", {"input": 1_000_000}, model="claude-opus-5-5")
        self.session("s2", "feat/37-cost", "10", {"output": 1_000_000}, model="claude-opus-5-5")
        self.session("s3", "fix/8-typo", "12", {"input": 500_000}, model="claude-opus-5-5")
        self.session("s4", "feat/review-agent", "14", {"input": 250_000}, model="claude-opus-5-5")
        self.session("s5", "main", "16", {"input": 250_000}, model="made-up-model")

    def tearDown(self) -> None:
        self.box.close()
        self.tmp.cleanup()

    def session(self, name: str, branch: str, hour: str, counts: dict, model: str) -> None:
        t = support.Transcript(cwd=str(self.clone), branch=branch).prompt(f"2026-10-09T{hour}:00:00.000Z")
        t.response(f"2026-10-09T{hour}:03:00.000Z", f"{name}-m", counts, model=model)
        path = t.write(self.root / "projects" / f"{name}.jsonl")
        self.assertEqual(self.box.record(path, name, "--no-publish").returncode, 0)

    def data(self, *arguments: str, **env: str) -> dict:
        result = self.box.run("report.py", "--repository", REPO, "--json", *arguments, **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_every_issue_of_the_repository_with_tokens_hours_and_money(self) -> None:
        found = {row["issue"]: row for row in self.data("--offline")["issues"]}
        self.assertEqual(sorted(found), ["#37", "#8", "unattributed"])
        issue = found["#37"]
        self.assertEqual((issue["sessions"], issue["turns"], issue["tokens"]["input"], issue["tokens"]["output"]), (2, 2, 1_000_000, 1_000_000))
        self.assertEqual(issue["cost"]["token_usd"], 24.0)
        self.assertEqual(issue["active_hours"], 0.05)
        self.assertEqual(issue["wall_clock_hours"], 0.1)

    def test_one_issue(self) -> None:
        report_ = self.data("--offline", "--issue", "8")
        self.assertEqual([row["issue"] for row in report_["issues"]], ["#8"])
        self.assertEqual(report_["issues"][0]["cost"]["token_usd"], 2.0)

    def test_the_unattributed_part_of_the_total_is_stated(self) -> None:
        report_ = self.data("--offline")
        self.assertEqual(report_["total"]["cost"]["token_usd"], 27.0)
        self.assertEqual(report_["unattributed"]["token_usd"], 1.0)
        self.assertEqual(report_["unattributed"]["share_of_token_cost_percent"], 3.7)
        self.assertEqual(report_["unattributed"]["branches"], ["feat/review-agent", "main"])

    def test_text_says_not_configured_and_names_the_unpriced_model(self) -> None:
        out = self.box.run("report.py", "--repository", REPO, "--offline").stdout
        self.assertIn("development cost  not configured   not configured", out)
        self.assertIn("no price for model made-up-model: 250,000 tokens left out of the cost", out)
        self.assertIn("unattributed: USD 1.00 of token cost, 3.7% of the total", out)
        self.assertNotIn("BRL 0.00", out)
        self.assertIsNone(self.data("--offline")["total"]["cost"]["development_brl"])

    def test_configured_rates_give_reais_and_the_development_cost(self) -> None:
        cost = self.data("--offline", AHRENA_COSTS_BRL_PER_USD="5", AHRENA_COSTS_HOURLY_RATE="200", AHRENA_COSTS_HOURLY_RATE_CURRENCY="BRL")["issues"][0]["cost"]
        self.assertEqual((cost["token_usd"], cost["token_brl"], cost["time_brl"], cost["development_brl"]), (24.0, 120.0, 10.0, 130.0))

    def test_a_zero_or_malformed_rate_is_not_a_rate(self) -> None:
        cost = self.data("--offline", AHRENA_COSTS_BRL_PER_USD="0", AHRENA_COSTS_HOURLY_RATE="abc")["total"]["cost"]
        self.assertEqual((cost["token_brl"], cost["time_usd"]), (None, None))

    def test_an_unattributed_branch_is_resolved_through_its_pull_request(self) -> None:
        """#157/AC-2, the second rung: the pull request of the branch and the issues it closes."""
        pull = {"number": 77, "state": "MERGED", "closingIssuesReferences": [{"number": 15}, {"number": 12}]}
        self.box.set_forge(pulls={REPO: {"feat/review-agent": [pull]}})
        found = {row["issue"]: row for row in self.data()["issues"]}
        self.assertEqual(sorted(found), ["#12+#15", "#37", "#8", "unattributed"])
        self.assertEqual(found["#12+#15"]["attributed_by"], ["pull-request #77"])
        self.assertEqual(self.data("--issue", "15")["issues"][0]["issue"], "#12+#15")
        self.assertEqual(self.data()["unattributed"]["branches"], ["main"])
        asked = [call for call in self.box.forge()["calls"] if "main" in call]
        self.assertEqual(asked, [])

    def test_a_pull_request_that_closes_nothing_leaves_the_branch_unattributed(self) -> None:
        self.box.set_forge(pulls={REPO: {"feat/review-agent": [{"number": 77, "closingIssuesReferences": []}]}})
        self.assertEqual(self.data()["unattributed"]["branches"], ["feat/review-agent", "main"])

    def test_when_gh_fails_the_report_is_the_offline_one(self) -> None:
        self.box.set_forge(fail=True)
        report_ = self.data()
        self.assertEqual(sorted(row["issue"] for row in report_["issues"]), ["#37", "#8", "unattributed"])
        self.assertEqual(len(report_["lookup_failures"]), 1)

    def test_another_repository_sees_nothing_of_this_one(self) -> None:
        result = self.box.run("report.py", "--repository", "acme/other", "--offline")
        self.assertIn("nothing recorded for this selection", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
