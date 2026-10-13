#!/usr/bin/env python3
"""Publish the cost of one CI run on its pull request, from a claude-code-action execution file.

A workflow step calls this after the step that ran Claude. It needs `gh` with a token in the
environment (`GH_TOKEN`) and the standard library. It reads no ledger and writes none: the
passes already published are read back from the pull request's cost comment.

    python3 costs/runtime/publish.py \
        --execution-file "$EXECUTION_FILE" --repository "$GITHUB_REPOSITORY" \
        --pull-request "$PR_NUMBER" --kind review --run-id "$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"

The pass id is `ci:<run-id>:<kind>`, so publishing the same run twice changes nothing, and a
second attempt of a run is a second pass. The cost is computed from the tokens and this
plugin's price table, the same way a local session's is; the cost the action reports is kept
only to be shown beside it when the two differ.

A cost comment is never a reason to fail a pipeline: every failure is printed as a warning and
the exit code is 0, unless `--strict` is given.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import comment  # noqa: E402
import ledger  # noqa: E402
import money  # noqa: E402
import usage  # noqa: E402

KINDS = ("review", "auto-fix", "release-train", "development")


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish one CI run's cost on its pull request.")
    parser.add_argument("--execution-file", required=True, help="the action's execution_file output")
    parser.add_argument("--repository", required=True, help="owner/name")
    parser.add_argument("--pull-request", required=True, type=int)
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument("--run-id", required=True, help="stable for the run, e.g. <run id>-<attempt>")
    parser.add_argument("--branch", help="the pull request's head branch, to state the attribution")
    parser.add_argument("--brl-per-usd", type=float, help="exchange rate; default $AHRENA_COSTS_BRL_PER_USD")
    parser.add_argument("--dry-run", action="store_true", help="print the pass and stop; call nothing")
    parser.add_argument("--strict", action="store_true", help="exit 1 when publishing fails")
    return parser.parse_args(argv)


def run_pass(options: argparse.Namespace, table: money.PriceTable) -> dict:
    """The pass of this run, built from the execution file alone."""
    path = Path(options.execution_file)
    run = usage.read_execution(path, table.tiers)
    started = run.first if run.first is not None else path.stat().st_mtime
    ended = run.last if run.last is not None else started
    return {
        "id": f"ci:{options.run_id}:{options.kind}",
        "kind": options.kind,
        "runner": "ci",
        "run": str(options.run_id),
        "started_at": ledger.iso(started),
        "ended_at": ledger.iso(ended),
        "active_seconds": run.duration,
        "tokens": run.tokens,
        "reported_cost_usd": run.reported_cost,
        "source": run.source,
        "output_lower_bound": run.source != "result.modelUsage",
    }


def main(argv: list[str]) -> int:
    options = arguments(argv)
    try:
        table = money.load_prices()
        entry = run_pass(options, table)
        if options.dry_run:
            print(json.dumps(entry, indent=2, sort_keys=True))
            return 0
        rate = ledger.positive(options.brl_per_usd or os.environ.get("AHRENA_COSTS_BRL_PER_USD"))
        context = comment.Context(table, rate, options.branch)
        outcome = comment.publish(comment.Target(options.repository, options.pull_request), [entry], context)
        print(f"cost comment {outcome.action} on {options.repository}#{options.pull_request} for pass {entry['id']}")
    except (comment.GhError, OSError, ValueError, KeyError) as error:
        print(f"::warning::cost not published: {type(error).__name__}: {error}")
        return 1 if options.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
