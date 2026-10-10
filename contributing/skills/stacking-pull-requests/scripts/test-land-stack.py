#!/usr/bin/env python3
"""Tests for land-stack.py.

The script reaches the forge only through `gh`, so each case puts a fake `gh`
first on PATH. The fake answers from a table of routes, each a command prefix
and a list of answers it gives in turn, the last repeating, and it logs every
call. A case runs the script as a subprocess and asserts on the exit code, the
output, and the calls that were and were not made.

The answers are shaped like the ones GitHub gave while stack 110 of
barte-ai-services/barte-ai-platform-monkey landed on 2026-09-29, and the suite
names #120's criteria beside the cases that cover them.

Usage:
    python3 contributing/skills/stacking-pull-requests/scripts/test-land-stack.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "land-stack.py"
REPO = "acme/widgets"
VERSION = "api -H X-GitHub-Api-Version: 2026-03-10"
URL = f"https://github.com/{REPO}/pull"

FAKE_GH = """\
import json, os, sys
routes_path, log_path = os.environ["FAKE_GH_ROUTES"], os.environ["FAKE_GH_LOG"]
command = " ".join(sys.argv[1:])
with open(log_path, "a", encoding="utf-8") as log:
    log.write(command + "\\n")
with open(routes_path, encoding="utf-8") as f:
    routes = json.load(f)
matches = [prefix for prefix in routes if command.startswith(prefix)]
if not matches:
    sys.stderr.write("fake gh: no route for " + command)
    sys.exit(1)
prefix = max(matches, key=len)
answers = routes[prefix]
answer = answers.pop(0) if len(answers) > 1 else answers[0]
with open(routes_path, "w", encoding="utf-8") as f:
    json.dump(routes, f)
out = answer.get("out")
sys.stdout.write(out if isinstance(out, str) else json.dumps(out) if out is not None else "")
sys.stderr.write(answer.get("err", ""))
sys.exit(answer.get("code", 0))
"""


def says(out: object = None, code: int = 0, err: str = "") -> dict:
    return {"out": out, "code": code, "err": err}


def pr(number: int, state: str = "OPEN", base: str = "main", review: str = "APPROVED") -> dict:
    return {
        "state": state,
        "baseRefName": base,
        "reviewDecision": review,
        "title": f"feat: layer {number}",
        "url": f"{URL}/{number}",
        "headRefOid": f"{number:040x}",
    }


SQUASHED = {"parents": [{"sha": "a"}], "commit": {"message": "feat: the last change (#99)\n\nCloses #98"}}
MERGE_COMMIT = {"parents": [{"sha": "a"}, {"sha": "b"}], "commit": {"message": "Merge pull request #99 from acme/feat/98-x"}}
PUSHED = {"parents": [{"sha": "a"}], "commit": {"message": "chore: pushed straight to main"}}


def stack(*numbers: int, squash: bool = True, merge: bool = True, rules: list | None = None, tip: dict = SQUASHED) -> dict:
    """Stack 110 of `numbers`, bottom first, on a repository allowing the methods given, whose main ends in `tip`."""
    settings = {"allow_squash_merge": squash, "allow_merge_commit": merge, "allow_rebase_merge": False}
    return {
        f"{VERSION} repos/{REPO}/commits?sha=main&per_page=1": [says([tip])],
        f"{VERSION} repos/{REPO}/stacks/110": [says({"base": {"ref": "main"}, "pull_requests": [{"number": n} for n in numbers]})],
        f"{VERSION} repos/{REPO}/rules/branches/main": [says(rules or [])],
        f"{VERSION} repos/{REPO}": [says(settings)],
    }


def view(number: int, *answers: dict) -> dict:
    return {f"pr view {number} --repo {REPO}": [says(a) for a in answers]}


def checks(number: int, listing: list | None = None, watch: int = 0) -> dict:
    """What `gh pr checks` lists for the layer, and how its watch exits."""
    listing = listing if listing is not None else [{"name": "artifact gate", "bucket": "pass"}]
    return {
        f"pr checks {number} --repo {REPO} --json": [says(listing, code=8 if any(c["bucket"] == "pending" for c in listing) else 0)],
        f"pr checks {number} --repo {REPO} --watch": [says(code=watch, err="artifact gate\tfail" if watch else "")],
    }


def merges(number: int, *statuses: dict) -> dict:
    """The PUT answers pending with an id, and the status polls answer `statuses` in turn."""
    uuid = f"uuid-{number}"
    return {
        f"{VERSION} -X PUT repos/{REPO}/pulls/{number}/merge-async": [
            says({"status": "pending", "details": {"uuid": uuid, "bypass_rules": False}})
        ],
        f"{VERSION} repos/{REPO}/pulls/{number}/merge-async/{uuid}": [says(s) for s in statuses],
    }


MERGED = {"status": "merged"}
PENDING = {"status": "pending"}


def ready(number: int) -> dict:
    """An open layer on main, approved, green, that merges."""
    return {**view(number, pr(number)), **checks(number), **merges(number, PENDING, MERGED)}


def put(number: int) -> str:
    return f"{VERSION} -X PUT repos/{REPO}/pulls/{number}/merge-async"


def case(name: str, args: list[str], routes: dict, expect: list[str], calls=(), never=(), unsaid=(), ok: bool = True) -> tuple:
    """`calls` must each start some gh call, `never` must be in none, `unsaid` must not be printed."""
    return (name, args, routes, expect, list(calls), list(never), list(unsaid), ok)


CASES = [
    # --- the dry run (#120/AC-1)
    case(
        "without --go each open layer is listed with its base, review and checks, and nothing merges",
        [],
        {
            **stack(101, 102),
            **view(101, pr(101)),
            **checks(101),
            **view(102, pr(102, base="feat/101-bottom", review="REVIEW_REQUIRED")),
            **checks(102, [{"name": "artifact gate", "bucket": "pending"}]),
        },
        ["dry run", "== #101", "base: main  review: APPROVED", "artifact gate: pass",
         "== #102", "base: feat/101-bottom  review: REVIEW_REQUIRED", "artifact gate: pending", "nothing merged"],
        never=["merge-async", "--watch", "pr edit"],
    ),
    # --- landing bottom to top (#120/AC-2)
    case(
        "with --go the layers land bottom to top, each through merge-async after its checks",
        ["--go"],
        {**stack(101, 102, 103), **ready(101), **ready(102), **ready(103)},
        ["#101 merged", "#102 merged", "#103 merged", "stack landed"],
        calls=[
            f"pr checks 101 --repo {REPO} --watch", put(101),
            f"pr checks 102 --repo {REPO} --watch", put(102),
            f"pr checks 103 --repo {REPO} --watch", put(103),
        ],
    ),
    case(
        "a layer waits for GitHub to retarget it when the branch below is deleted",
        ["--go"],
        {**stack(101), **ready(101), **view(101, pr(101, base="feat/100-below"), pr(101, base="feat/100-below"), pr(101))},
        ["#101 merged"],
        calls=[put(101)],
        never=["pr edit"],
    ),
    case(
        "a layer whose base is still the branch below is retargeted after the wait",
        ["--go"],
        {**stack(101), **ready(101), **view(101, pr(101, base="feat/100-below")), f"pr edit 101 --repo {REPO}": [says()]},
        ["retargeting #101 to main", "#101 merged"],
        calls=[f"pr edit 101 --repo {REPO} --base main", put(101)],
    ),
    # --- red checks stop the run (#120/AC-3)
    case(
        "the first layer whose checks fail stops the run, named with its URL, and the layers above stay open",
        ["--go"],
        {**stack(101, 102, 103), **ready(101), **ready(102), **checks(102, watch=1), **ready(103)},
        ["#101 merged", "the checks of #102 failed", f"{URL}/102", "artifact gate\tfail"],
        calls=[put(101)],
        never=[put(102), put(103), "pr checks 103"],
        ok=False,
    ),
    # --- the approval and the admin override (#120/AC-4)
    case(
        "without --admin a layer that is not approved stops the run",
        ["--go"],
        {**stack(101, 102), **ready(101), **ready(102), **view(102, pr(102, review="REVIEW_REQUIRED"))},
        ["#101 merged", "#102 is not approved (review: REVIEW_REQUIRED)", "--admin"],
        never=[put(102)],
        ok=False,
    ),
    case(
        "a layer with no review decision is not approved either",
        ["--go"],
        {**stack(101), **ready(101), **view(101, pr(101, review=""))},
        ["#101 is not approved (review: none)"],
        never=[put(101)],
        ok=False,
    ),
    case(
        "with --admin an unapproved layer lands, sending bypass_rules=true",
        ["--go", "--admin"],
        {**stack(101), **ready(101), **view(101, pr(101, review="REVIEW_REQUIRED"))},
        ["#101 merged"],
        calls=[f"{put(101)} -f merge_method=squash -f merge_action=direct_merge -f sha={101:040x} -F bypass_rules=true"],
    ),
    case(
        "without --admin the merge sends bypass_rules=false",
        ["--go"],
        {**stack(101), **ready(101)},
        ["#101 merged"],
        calls=[f"{put(101)} -f merge_method=squash -f merge_action=direct_merge -f sha={101:040x} -F bypass_rules=false"],
    ),
    # --- the async merge's status (#120/AC-5)
    case(
        "the status is read from details.uuid until it is merged",
        ["--go"],
        {**stack(101), **ready(101), **merges(101, PENDING, PENDING, MERGED)},
        ["#101 merged"],
        calls=[f"{VERSION} repos/{REPO}/pulls/101/merge-async/uuid-101"],
    ),
    case(
        "a merge the branch rules refuse comes back failed, and the forge's message is printed",
        ["--go"],
        {
            **stack(101, 102),
            **ready(101),
            **merges(101, PENDING, {"status": "failed", "details": {"message": "At least 1 approving review is required by reviewers with write access."}}),
            **ready(102),
        },
        ["the merge of #101 ended failed", "At least 1 approving review is required by reviewers with write access."],
        never=[put(102)],
        unsaid=["#101 merged"],
        ok=False,
    ),
    case(
        "a refused PUT stops the run with gh's error",
        ["--go"],
        {**stack(101), **ready(101), put(101): [says(code=1, err="HTTP 422: Head sha changed")]},
        ["HTTP 422: Head sha changed"],
        unsaid=["#101 merged"],
        ok=False,
    ),
    # --- a rerun resumes (#120/AC-6)
    case(
        "a rerun skips the layers already merged and goes on from the lowest open one",
        ["--go"],
        {**stack(101, 102, 103), **view(101, pr(101, "MERGED")), **view(102, pr(102, "MERGED")), **ready(103)},
        ["#101 already merged", "#102 already merged", "#103 merged", "stack landed"],
        calls=[put(103)],
        never=[put(101), put(102), "pr checks 101", "pr checks 102"],
    ),
    case(
        "a layer closed without merging stops the run",
        ["--go"],
        {**stack(101, 102), **view(101, pr(101, "CLOSED")), **ready(102)},
        ["#101 is closed"],
        never=["merge-async"],
        ok=False,
    ),
    # --- the merge method (#120/AC-7)
    case(
        "the caller's method is the one sent",
        ["--go", "--method", "merge"],
        {**stack(101), **ready(101)},
        ["by merge", "#101 merged"],
        calls=[f"{put(101)} -f merge_method=merge"],
    ),
    case(
        "without --method a repository that allows only merge commits lands with merge commits",
        ["--go"],
        {**stack(101, squash=False), **ready(101)},
        ["by merge", "#101 merged"],
        calls=[f"{put(101)} -f merge_method=merge"],
    ),
    case(
        "without --method a repository that allows several and lands with merge commits lands with merge commits",
        [],
        {**stack(101, tip=MERGE_COMMIT), **view(101, pr(101)), **checks(101)},
        ["by merge"],
    ),
    case(
        "without --method a repository that allows several and squashes lands by squash",
        [],
        {**stack(101, tip=SQUASHED), **view(101, pr(101)), **checks(101)},
        ["by squash"],
    ),
    case(
        "where the last commit says neither, squash comes first",
        [],
        {**stack(101, tip=PUSHED), **view(101, pr(101)), **checks(101)},
        ["by squash"],
    ),
    case(
        "a habit the repository no longer allows is not followed",
        [],
        {**stack(101, merge=False, tip=MERGE_COMMIT), **view(101, pr(101)), **checks(101)},
        ["by squash"],
    ),
    case(
        "a ruleset on the base that allows only merge commits wins over the settings",
        [],
        {**stack(101, rules=[{"type": "pull_request", "parameters": {"allowed_merge_methods": ["merge"]}}]), **view(101, pr(101)), **checks(101)},
        ["by merge"],
    ),
    case(
        "a token that cannot see the settings is told to pass --method",
        [],
        {**stack(101), f"{VERSION} repos/{REPO}": [says({"full_name": REPO})], **view(101, pr(101)), **checks(101)},
        ["pass --method"],
        never=["pr view"],
        ok=False,
    ),
]


def run(args: list[str], routes: dict) -> tuple[int, str, list[str]]:
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir, routes_path, log_path = Path(tmp) / "bin", Path(tmp) / "routes.json", Path(tmp) / "calls.log"
        bin_dir.mkdir()
        fake = bin_dir / "gh"
        fake.write_text(f"#!{sys.executable}\n{FAKE_GH}", encoding="utf-8")
        fake.chmod(0o755)
        routes_path.write_text(json.dumps(routes), encoding="utf-8")
        log_path.write_text("", encoding="utf-8")
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
        env.update(FAKE_GH_ROUTES=str(routes_path), FAKE_GH_LOG=str(log_path))
        command = [sys.executable, str(SCRIPT), REPO, "110", "--interval", "0", *args]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
        return result.returncode, result.stdout + result.stderr, log_path.read_text(encoding="utf-8").splitlines()


def problems_for(expected: tuple, code: int, output: str, calls: list[str]) -> list[str]:
    _, _, _, expect, made, never, unsaid, ok = expected
    found = []
    if ok and code != 0:
        found.append(f"expected the script to succeed, it exited {code}")
    if not ok and code == 0:
        found.append("expected the script to stop, it succeeded")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    found.extend(f"expected a call starting {prefix!r}" for prefix in made if not any(c.startswith(prefix) for c in calls))
    found.extend(f"expected no call containing {part!r}" for part in never if any(part in c for c in calls))
    found.extend(f"expected {fragment!r} not in the output" for fragment in unsaid if fragment in output)
    return found


def main() -> int:
    failed = 0
    for expected in CASES:
        code, output, calls = run(expected[1], expected[2])
        problems = problems_for(expected, code, output, calls)
        if not problems:
            print(f"ok    {expected[0]}")
            continue
        failed += 1
        print(f"FAIL  {expected[0]}")
        for problem in problems:
            print(f"        {problem}")
        print("      --- script output ---")
        for line in output.splitlines():
            print(f"      {line}")
        print("      --- gh calls ---")
        for line in calls:
            print(f"      {line}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
