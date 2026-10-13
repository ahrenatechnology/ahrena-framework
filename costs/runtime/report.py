#!/usr/bin/env python3
"""Report what each issue of a repository cost, from the local ledger.

    python3 costs/runtime/report.py                      every issue of this repository
    python3 costs/runtime/report.py --issue 37           one issue
    python3 costs/runtime/report.py --repository o/n --json

For each issue: sessions, turns, tokens by kind, active and wall-clock hours, token cost in
dollars and in reais, the cost of the active hours at the configured hourly rate, and their
sum, the development cost. Then the total, and how much of it is unattributed.

A segment the hook could not attribute from its branch name is resolved here, when `gh` is
available and `--offline` is not given, through the pull request of that branch and the
issues it closes. A pull request that closes several issues is reported under all of them
together, as `#12+#15`: splitting its cost between them would be a guess.

Active hours are the union of the active intervals, so two sessions that ran at the same time
on one issue count that time once, and the total can be less than the sum of its rows.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import comment  # noqa: E402
import ledger  # noqa: E402
import money  # noqa: E402
import usage  # noqa: E402

UNATTRIBUTED = "unattributed"
NOT_CONFIGURED = "not configured"


@dataclass
class Group:
    """Everything attributed to one issue, or to none."""

    label: str
    sessions: set[str] = field(default_factory=set)
    turns: int = 0
    tokens: dict = field(default_factory=dict)
    intervals: list[tuple[float, float]] = field(default_factory=list)
    wall_seconds: float = 0.0
    unfinished: int = 0
    methods: set[str] = field(default_factory=set)
    branches: set[str] = field(default_factory=set)

    def take(self, session_id: str, segment: dict) -> None:
        self.sessions.add(session_id)
        self.turns += int(segment.get("turns") or 0)
        usage.merge_tokens(self.tokens, segment.get("tokens", {}))
        self.wall_seconds += float(segment.get("wall_seconds") or 0)
        self.unfinished += int(segment.get("unfinished_responses") or 0)
        for start, end in segment.get("active_intervals", []):
            first, last = usage.parse_time(start), usage.parse_time(end)
            if first is not None and last is not None:
                self.intervals.append((first, last))


def union_seconds(intervals: list[tuple[float, float]]) -> float:
    """The length of the union of intervals, so overlapping time is counted once."""
    total, reach = 0.0, float("-inf")
    for start, end in sorted(intervals):
        if end > reach:
            total += end - max(start, reach)
            reach = end
    return total


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report the cost of each issue from the local ledger.")
    parser.add_argument("--repository", help="owner/name (default: the origin remote of the current directory)")
    parser.add_argument("--issue", type=int, help="report this issue only")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--offline", action="store_true", help="do not ask gh for the pull request of an unattributed branch")
    parser.add_argument("--home", help="the ledger directory (default: $AHRENA_COSTS_HOME or the state directory)")
    return parser.parse_args(argv)


def closed_issues(repository: str, branch: str) -> tuple[list[int], int | None]:
    """The issues the pull requests of a branch close, and the first such pull request."""
    fields = "number,closingIssuesReferences"
    out = comment.gh(["pr", "list", "--repo", repository, "--head", branch, "--state", "all", "--json", fields, "--limit", "20"])
    pulls = json.loads(out or "[]")
    issues = sorted({int(ref["number"]) for pull in pulls for ref in pull.get("closingIssuesReferences") or []})
    return issues, (int(pulls[0]["number"]) if pulls else None)


class Resolver:
    """Attribution at report time: the branch name first, then the branch's pull request."""

    def __init__(self, repository: str, online: bool) -> None:
        self.repository = repository
        self.online = online
        self.cache: dict[str, tuple[str, str]] = {}
        self.failures: list[str] = []

    def lookup(self, branch: str) -> tuple[str, str]:
        if branch not in self.cache:
            try:
                issues, pull = closed_issues(self.repository, branch)
            except (comment.GhError, ValueError, KeyError, TypeError) as error:
                self.online = False
                self.failures.append(str(error))
                return UNATTRIBUTED, "unattributed"
            label = "+".join(f"#{n}" for n in issues) if issues else UNATTRIBUTED
            self.cache[branch] = (label, f"pull-request #{pull}" if issues else "unattributed")
        return self.cache[branch]

    def label(self, segment: dict) -> tuple[str, str]:
        found = segment.get("attribution") or {}
        if found.get("issue") is not None:
            return f"#{found['issue']}", "branch"
        branch = segment.get("branch")
        if self.online and branch and found.get("reason") == "no-issue-in-branch-name":
            return self.lookup(branch)
        return UNATTRIBUTED, "unattributed"


def collect(records: list[dict], resolver: Resolver) -> dict[str, Group]:
    """Group every segment of the repository by the issue it is attributed to."""
    groups: dict[str, Group] = {}
    for record in records:
        for segment in record.get("segments", []):
            if segment.get("repository") != resolver.repository:
                continue
            label, method = resolver.label(segment)
            group = groups.setdefault(label, Group(label))
            group.take(str(record.get("session_id")), segment)
            group.methods.add(method)
            if label == UNATTRIBUTED and segment.get("branch"):
                group.branches.add(segment["branch"])
    return groups


def figures(group: Group, table: money.PriceTable, rates: money.Rates) -> dict:
    """One group as plain data: counters, hours and money, with None for what is not configured."""
    cost = money.token_cost(group.tokens, table)
    active = union_seconds(group.intervals)
    parts = money.development_cost(cost.usd, Decimal(str(active)) / 3600, rates)
    kinds = usage.sum_kinds(group.tokens)
    return {
        "issue": group.label,
        "attributed_by": sorted(group.methods),
        "sessions": len(group.sessions),
        "turns": group.turns,
        "tokens": {**kinds, "cache_write": kinds["cache_write_5m"] + kinds["cache_write_1h"], "total": sum(kinds.values())},
        "tokens_by_model": {model: dict(counts) for model, counts in sorted(group.tokens.items())},
        "active_hours": round(active / 3600, 4),
        "wall_clock_hours": round(group.wall_seconds / 3600, 4),
        "cost": {name: money.rounded(value) for name, value in parts.items()},
        "unpriced_models": dict(sorted(cost.unpriced.items())),
        "unfinished_responses": group.unfinished,
        "unresolved_branches": sorted(group.branches),
    }


def share(part: float, whole: float) -> float | None:
    return round(100 * part / whole, 2) if whole else None


def build(options: argparse.Namespace, root: Path) -> dict:
    """The whole report as data."""
    repository = options.repository or ledger.repository_of(str(Path.cwd()))
    if not repository:
        raise SystemExit("no repository: pass --repository owner/name, or run inside a clone with an origin remote")
    config = ledger.load_config(root)
    rates = money.Rates(config.brl_per_usd, config.hourly_rate, config.hourly_rate_currency)
    table = money.load_prices()
    resolver = Resolver(repository, not options.offline)
    groups = collect(ledger.all_records(root), resolver)
    everything = Group("total")
    for group in groups.values():
        everything.sessions |= group.sessions
        everything.turns += group.turns
        usage.merge_tokens(everything.tokens, group.tokens)
        everything.intervals += group.intervals
        everything.wall_seconds += group.wall_seconds
        everything.unfinished += group.unfinished
    total = figures(everything, table, rates)
    loose = figures(groups[UNATTRIBUTED], table, rates) if UNATTRIBUTED in groups else None
    wanted = f"#{options.issue}" if options.issue else None
    rows = [figures(g, table, rates) for label, g in sorted(groups.items()) if wanted is None or wanted in label.split("+")]
    return {
        "repository": repository,
        "ledger": str(root),
        "idle_threshold_seconds": config.idle_seconds,
        "configured": {"brl_per_usd": config.brl_per_usd, "hourly_rate": config.hourly_rate, "hourly_rate_currency": config.hourly_rate_currency},
        "issues": rows,
        "total": total,
        "unattributed": {
            "token_usd": loose["cost"]["token_usd"] if loose else 0.0,
            "share_of_token_cost_percent": share(loose["cost"]["token_usd"] if loose else 0.0, total["cost"]["token_usd"]),
            "share_of_tokens_percent": share(loose["tokens"]["total"] if loose else 0, total["tokens"]["total"]),
            "active_hours": loose["active_hours"] if loose else 0.0,
            "branches": loose["unresolved_branches"] if loose else [],
        },
        "lookup_failures": resolver.failures,
    }


def amount(value: float | None, symbol: str) -> str:
    return NOT_CONFIGURED if value is None else f"{symbol} {value:,.2f}"


def block(row: dict) -> list[str]:
    """One issue, or the total, as text."""
    tokens, cost = row["tokens"], row["cost"]
    by = f"  (attributed by: {', '.join(row['attributed_by'])})" if row["attributed_by"] else ""
    lines = [
        f"{row['issue']}{by}",
        f"  sessions {row['sessions']}   turns {row['turns']}",
        f"  tokens   input {tokens['input']:,}   output {tokens['output']:,}   cache write {tokens['cache_write']:,}   cache read {tokens['cache_read']:,}",
        f"  hours    active {row['active_hours']:.2f}   wall-clock {row['wall_clock_hours']:.2f}",
        f"  tokens cost       {amount(cost['token_usd'], 'USD')}   {amount(cost['token_brl'], 'BRL')}",
        f"  active-time cost  {amount(cost['time_usd'], 'USD')}   {amount(cost['time_brl'], 'BRL')}",
        f"  development cost  {amount(cost['development_usd'], 'USD')}   {amount(cost['development_brl'], 'BRL')}",
    ]
    lines += [f"  no price for model {model}: {count:,} tokens left out of the cost" for model, count in row["unpriced_models"].items()]
    if row["unfinished_responses"]:
        lines.append(f"  output is a lower bound: {row['unfinished_responses']:,} responses were recorded before they finished")
    return lines


def text(report: dict) -> str:
    loose = report["unattributed"]
    lines = [f"Cost per issue: {report['repository']}", f"ledger {report['ledger']}   idle threshold {report['idle_threshold_seconds']:.0f}s", ""]
    for row in report["issues"]:
        lines += [*block(row), ""]
    if not report["issues"]:
        lines += ["nothing recorded for this selection", ""]
    lines += [*block(report["total"]), ""]
    part = loose["share_of_token_cost_percent"]
    lines.append(
        f"unattributed: {amount(loose['token_usd'], 'USD')} of token cost"
        + (f", {part:.1f}% of the total" if part is not None else "")
        + f", {loose['active_hours']:.2f} active hours"
    )
    lines += [f"  unresolved branch: {branch}" for branch in loose["branches"]]
    lines += [f"  pull-request lookup failed, reported offline: {failure}" for failure in report["lookup_failures"][:1]]
    lines.append("token cost is the API list price applied to the tokens; it is not an invoice")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    options = arguments(argv)
    root = Path(options.home).expanduser() if options.home else ledger.home()
    report = build(options, root)
    print(json.dumps(report, indent=2) if options.json else text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
