#!/usr/bin/env python3
"""Land a native stack of pull requests bottom to top, one layer at a time.

`gh stack merge` lands a layer and every unmerged one below it in a single
operation. This lands them one by one instead, each only once its own checks
are green, and stops at the first layer that cannot land. For each open layer,
lowest first, it:

    1. waits for the layer's base to be the stack's base, which GitHub sets
       when the branch below is deleted on merge, and retargets it after a
       timeout;
    2. waits for its checks with `gh pr checks --watch --fail-fast`, and stops
       at the first red;
    3. stops unless its review decision is APPROVED or --admin was given;
    4. merges it through the async merge API, the only merge GitHub accepts for
       a layer of a stack, and polls the merge's status until it is `merged`.

A layer already merged is skipped, so a rerun goes on from the lowest open one.
Without --go nothing is merged: each open layer is listed with its base, its
review decision and its checks.

The merge method is the one given with --method. Without it, the method is one
the repository allows, in its settings and in any ruleset on the stack's base.
Where it allows several, the one it prefers is read from the last commit on the
base: a merge commit says merge, a subject ending in ` (#N)` says squash.
Where that says neither, squash comes first, as ADR-001 prefers, then merge,
then rebase.

--admin sends `bypass_rules=true`, the async API's equivalent of
`gh pr merge --admin`. The forge still refuses it to anyone who may not bypass.

Usage:
    python3 land-stack.py <owner/repo> <stack>                  list, merge nothing
    python3 land-stack.py <owner/repo> <stack> --go             land the stack
    python3 land-stack.py <owner/repo> <stack> --go --admin     land past required reviews
    python3 land-stack.py <owner/repo> <stack> --method merge   land with merge commits

Standard library only; the forge is reached through `gh`, which must be
authenticated with a token that can merge in the repository.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any

# Stacks and the async merge API are in preview, served under this version.
API_VERSION = "X-GitHub-Api-Version: 2026-03-10"

# The order a default is picked in when the repository allows several methods.
METHODS = ("squash", "merge", "rebase")
SETTING = {"squash": "allow_squash_merge", "merge": "allow_merge_commit", "rebase": "allow_rebase_merge"}

# The subject GitHub gives a squash commit ends in ` (#<number>)`.
SQUASH_SUBJECT = re.compile(r" \(#\d+\)$")

# How many polls a layer's base gets to become the stack's before it is
# retargeted, and how many an async merge gets to leave `pending`.
BASE_POLLS = 12
STATUS_POLLS = 60


class Stop(Exception):
    """The run cannot go on; the message says where it stopped and why."""


@dataclass(frozen=True)
class Options:
    repo: str
    stack: int
    go: bool
    admin: bool
    method: str | None
    interval: float


@dataclass(frozen=True)
class Stack:
    base: str
    layers: tuple[int, ...]
    method: str


# --- the forge, through gh


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh(*args: str) -> Any:
    """gh's answer parsed as JSON, or None when it printed nothing."""
    result = run(*args)
    if result.returncode != 0:
        raise Stop(f"`gh {' '.join(args)}` failed: {(result.stderr or result.stdout).strip()}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def api(*args: str) -> Any:
    return gh("api", "-H", API_VERSION, *args)


def layer(opts: Options, number: int) -> dict:
    fields = "state,baseRefName,reviewDecision,title,url,headRefOid"
    return gh("pr", "view", str(number), "--repo", opts.repo, "--json", fields)


# --- the merge method


def ruleset_methods(opts: Options, base: str) -> set[str] | None:
    """The methods a ruleset on `base` allows, or None when none restricts them."""
    try:
        rules = api(f"repos/{opts.repo}/rules/branches/{base}") or []
    except Stop:
        return None
    allowed: set[str] | None = None
    for rule in rules:
        listed = (rule.get("parameters") or {}).get("allowed_merge_methods")
        if rule.get("type") == "pull_request" and listed:
            allowed = set(listed) if allowed is None else allowed & set(listed)
    return allowed


def habit(opts: Options, base: str) -> str | None:
    """How the last change on `base` landed, where its commit says."""
    try:
        tip = (api(f"repos/{opts.repo}/commits?sha={base}&per_page=1") or [{}])[0]
    except Stop:
        return None
    if len(tip.get("parents") or []) > 1:
        return "merge"
    subject = ((tip.get("commit") or {}).get("message") or "").partition("\n")[0]
    return "squash" if SQUASH_SUBJECT.search(subject) else None


def default_method(opts: Options, base: str) -> str:
    settings = api(f"repos/{opts.repo}") or {}
    restricted = ruleset_methods(opts, base)
    known = [m for m in METHODS if SETTING[m] in settings]
    allowed = [m for m in METHODS if (settings.get(SETTING[m]) or m not in known) and (restricted is None or m in restricted)]
    if not known and restricted is None:
        raise Stop(f"the token cannot see which merge methods {opts.repo} allows: pass --method")
    if not allowed:
        raise Stop(f"{opts.repo} allows no merge method on {base}")
    preferred = habit(opts, base)
    return preferred if preferred in allowed else allowed[0]


def read_stack(opts: Options) -> Stack:
    found = api(f"repos/{opts.repo}/stacks/{opts.stack}") or {}
    base = (found.get("base") or {}).get("ref") or ""
    layers = tuple(int(pr["number"]) for pr in found.get("pull_requests") or [])
    if not layers:
        raise Stop(f"stack {opts.stack} has no pull request")
    return Stack(base, layers, opts.method or default_method(opts, base))


# --- without --go: what would land


def describe_checks(opts: Options, number: int) -> list[str]:
    # gh exits non-zero while a check is pending or red; the listing is what matters.
    result = run("pr", "checks", str(number), "--repo", opts.repo, "--json", "name,bucket")
    checks = json.loads(result.stdout) if result.stdout.strip() else []
    return [f"   {c['name']}: {c['bucket']}" for c in checks] or ["   no checks yet"]


def describe(opts: Options, number: int, pr: dict) -> None:
    print(f"   base: {pr['baseRefName']}  review: {pr.get('reviewDecision') or 'none'}")
    print("\n".join(describe_checks(opts, number)))


# --- with --go: land one layer


def wait_for_base(opts: Options, number: int, base: str) -> None:
    for _ in range(BASE_POLLS):
        if layer(opts, number)["baseRefName"] == base:
            return
        time.sleep(opts.interval)
    print(f"   retargeting #{number} to {base}")
    gh("pr", "edit", str(number), "--repo", opts.repo, "--base", base)


def wait_for_checks(opts: Options, number: int, url: str) -> None:
    print("   waiting for checks")
    interval = str(max(1, round(opts.interval)))
    result = run("pr", "checks", str(number), "--repo", opts.repo, "--watch", "--fail-fast", "--interval", interval)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise Stop(f"the checks of #{number} failed, so it and every layer above it stay open. See {url}\n{detail}")


def require_approval(opts: Options, number: int, review: str) -> None:
    if review == "APPROVED" or opts.admin:
        return
    raise Stop(f"#{number} is not approved (review: {review or 'none'}). Approve it and rerun, or pass --admin")


def await_merge(opts: Options, number: int, uuid: str) -> dict:
    status: dict = {}
    for _ in range(STATUS_POLLS):
        status = api(f"repos/{opts.repo}/pulls/{number}/merge-async/{uuid}") or {}
        if status.get("status") != "pending":
            return status
        time.sleep(opts.interval)
    return status


def reason(answer: dict) -> str:
    details = answer.get("details") or {}
    return answer.get("message") or details.get("message") or details.get("error") or json.dumps(answer)


def merge(opts: Options, number: int, sha: str, method: str) -> None:
    answer = api(
        "-X", "PUT", f"repos/{opts.repo}/pulls/{number}/merge-async",
        "-f", f"merge_method={method}", "-f", "merge_action=direct_merge", "-f", f"sha={sha}",
        "-F", f"bypass_rules={'true' if opts.admin else 'false'}",
    ) or {}
    uuid = (answer.get("details") or {}).get("uuid")
    if uuid:
        answer = await_merge(opts, number, uuid)
    if answer.get("status") != "merged":
        raise Stop(f"the merge of #{number} ended {answer.get('status') or 'without a status'}: {reason(answer)}")


def land(opts: Options, number: int, stack: Stack) -> None:
    wait_for_base(opts, number, stack.base)
    wait_for_checks(opts, number, layer(opts, number)["url"])
    pr = layer(opts, number)
    require_approval(opts, number, pr.get("reviewDecision") or "")
    merge(opts, number, pr["headRefOid"], stack.method)
    print(f"   #{number} merged")


# --- the run


def walk(opts: Options, stack: Stack) -> None:
    for number in stack.layers:
        pr = layer(opts, number)
        if pr["state"] == "MERGED":
            print(f"#{number} already merged")
            continue
        if pr["state"] != "OPEN":
            raise Stop(f"#{number} is {pr['state'].lower()}, so the stack cannot land past it. See {pr['url']}")
        print(f"\n== #{number} {pr['title']}  {pr['url']}")
        if opts.go:
            land(opts, number, stack)
        else:
            describe(opts, number, pr)


def parse(argv: list[str]) -> Options:
    parser = argparse.ArgumentParser(prog="land-stack.py", description="Land a native stack one layer at a time.")
    parser.add_argument("repo", help="owner/name")
    parser.add_argument("stack", type=int, help="the stack's number")
    parser.add_argument("--go", action="store_true", help="merge; without it nothing is merged")
    parser.add_argument("--admin", action="store_true", help="land without approval, sending bypass_rules=true")
    parser.add_argument("--method", choices=METHODS, help="the merge method; the repository's by default")
    parser.add_argument("--interval", type=float, default=5, help="seconds between polls (default 5)")
    found = parser.parse_args(argv)
    return Options(found.repo, found.stack, found.go, found.admin, found.method, found.interval)


def main(argv: list[str]) -> int:
    opts = parse(argv)
    try:
        stack = read_stack(opts)
        layers = " ".join(f"#{n}" for n in stack.layers)
        print(f"stack {opts.stack} in {opts.repo}, onto {stack.base}, by {stack.method}: {layers}")
        if not opts.go:
            print("(dry run: nothing will be merged; rerun with --go)")
        walk(opts, stack)
    except Stop as stop:
        print(f"\nstopped: {stop}", file=sys.stderr)
        return 1
    print("\nstack landed." if opts.go else "\nnothing merged.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
