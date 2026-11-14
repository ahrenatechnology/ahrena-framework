#!/usr/bin/env python3
"""Prompt test for an agent that acts: run it on a sample project, then decide what it did.

`run.py` tests a rule by the text a model writes. A layer builder's prompt is
tested by its actions: which skills it invoked, what it read, in what order,
what it wrote and what it returned. This runner builds each case's sample
repository with a bare remote, runs the case's agent headless through the
Claude Code CLI with this checkout's plugins, reads the stream of tool calls,
and decides the case:

    1. the result is DONE and the case's branch reached the remote
    2. the language's writing skill was invoked before the first test was written
    3. the exposure rule was read before the first test was written
    4. the language's review skill was invoked after the first test was written
    5. on an exposure case, no added line outside a test matches a forbidden
       pattern, and the result's `left:` names the criterion it overrode

The agents run with the plugins copied out of this checkout, with no project or
user settings and no MCP server, so the prompt under test is the only build
instruction in play. A case runs once per `--samples` and passes when most
samples pass. The report prints, per sample, the decisive tool-call indexes and
the agent's result.

Exit 0 when every case passes, 1 when one fails, 2 when a run could not be
decided (the CLI could not be reached or returned no result). The model calls
need a credential and are not run in CI; `test-run-agent.py` pins the deciding
logic, which CI runs (#290).

Usage:
    python3 foundation/prompt-tests/run-agent.py foundation/prompt-tests/layer-builders/cases.json
    python3 foundation/prompt-tests/run-agent.py <cases.json> --only heph-python,aglaia-typescript --jobs 3 --out report.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = "Bash Skill Read Grep Glob Edit Write"
TEST_PATH = re.compile(r"(_test\.(py|go|rs)|\.test\.tsx?|(^|/)tests?/[^\s'\"]+|/tests\.rs)")
WRITE_IN_SHELL = re.compile(r"(cat|tee)\s*>{0,2}\s*['\"]?(\S+)|>\s*['\"]?(\S+)")
BRANCH = re.compile(r"^branch:\s*`?([\w./-]+)", re.M)


@dataclass
class Call:
    name: str
    args: dict


@dataclass
class Sample:
    calls: list[Call]
    result: str | None
    added_lines: list[tuple[str, str]] = field(default_factory=list)
    pushed: list[str] = field(default_factory=list)


def _events(lines: list[str]) -> list[dict]:
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _tool_calls(event: dict) -> list[Call]:
    blocks = event.get("message", {}).get("content", []) if event.get("type") == "assistant" else []
    return [Call(b.get("name", ""), b.get("input", {}) or {}) for b in blocks if b.get("type") == "tool_use"]


def parse_stream(lines: list[str]) -> tuple[list[Call], str | None]:
    """The tool calls in order, and the final result text, from stream-json lines."""
    calls, result = [], None
    for event in _events(lines):
        calls.extend(_tool_calls(event))
        if event.get("type") == "result":
            result = event.get("result")
    return calls, result


def writes_a_test(call: Call) -> bool:
    if call.name in ("Write", "Edit"):
        path = str(call.args.get("file_path", ""))
        body = str(call.args.get("content", "")) + str(call.args.get("new_string", ""))
        return bool(TEST_PATH.search(path)) or (path.endswith(".rs") and "#[cfg(test)]" in body)
    if call.name == "Bash":
        command = str(call.args.get("command", ""))
        for found in WRITE_IN_SHELL.finditer(command):
            target = found.group(2) or found.group(3) or ""
            if TEST_PATH.search(target) or (target.endswith(".rs") and "#[cfg(test)]" in command):
                return True
    return False


def reads_rule(call: Call, rule: str) -> bool:
    name = Path(rule).name
    if call.name == "Read":
        return str(call.args.get("file_path", "")).endswith(name)
    return call.name == "Bash" and name in str(call.args.get("command", ""))


def first(calls: list[Call], predicate) -> int | None:
    return next((i for i, c in enumerate(calls) if predicate(c)), None)


def invokes(skill: str):
    return lambda c: c.name == "Skill" and str(c.args.get("skill", "")) == skill


def _order_failures(marks: dict, expect: dict) -> list[str]:
    if marks["test"] is None:
        return ["2-4: no test was written"]
    failed = []
    if marks["writing"] is None or marks["writing"] > marks["test"]:
        failed.append(f"2: {expect['writing_skill']} was not invoked before the first test")
    if marks["rule"] is None or marks["rule"] > marks["test"]:
        failed.append("3: the exposure rule was not read before the first test")
    if marks["review"] is None or marks["review"] < marks["test"]:
        failed.append(f"4: {expect['reviewing_skill']} was not invoked after the first test")
    return failed


def _exposure_failures(sample: Sample, exposure: dict) -> list[str]:
    failed = [
        f"5: {path} adds `{line.strip()}`, which matches {pattern}"
        for path, line in sample.added_lines
        if not TEST_PATH.search(path)
        for pattern in exposure["forbidden"]
        if re.search(pattern, line)
    ]
    result = sample.result or ""
    left = result[result.find("left:"):] if "left:" in result else ""
    if exposure["criterion"] not in left:
        failed.append(f"5: left: does not name {exposure['criterion']}")
    return failed


def decide(sample: Sample, case: dict, rule: str) -> tuple[list[str], dict]:
    """The failed conditions of one sample, and the indexes that decided them."""
    expect = case["expect"]
    calls = sample.calls
    marks = {
        "writing": first(calls, invokes(expect["writing_skill"])),
        "rule": first(calls, lambda c: reads_rule(c, rule)),
        "test": first(calls, writes_a_test),
        "review": first(calls, invokes(expect["reviewing_skill"])),
    }
    result = sample.result or ""
    failed = [] if result.lstrip().startswith("DONE") else ["1: the result is not DONE"]
    branch = BRANCH.search(result)
    if branch is None or branch.group(1) not in sample.pushed:
        failed.append("1: the branch the result names is not on the remote")
    failed += _order_failures(marks, expect)
    if expect.get("exposure"):
        failed += _exposure_failures(sample, expect["exposure"])
    return failed, marks


def component_map(name: str, spec: dict) -> str:
    return (
        f"components:\n  - name: {name}\n    concern: {spec['concern']}\n    paths: [src]\n"
        f"    language: en\n    stack: {spec['stack']}\nconventions:\n  layout: layered\n"
        f"  folders: {spec['folders']}\ntesting:\n  {spec['testing']}\ndelivery: rest\n"
    )


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def build_project(root: Path, case: dict) -> Path:
    project, remote = root / case["id"], root / f"{case['id']}.git"
    project.mkdir(parents=True)
    (project / "component-map.yaml").write_text(component_map(case["id"], case["component_map"]))
    for rel, body in case["files"].items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    git("init", "-q", "--bare", str(remote), cwd=root)
    for args in (
        ("init", "-q", "-b", "main"),
        ("config", "commit.gpgsign", "false"),
        ("config", "user.name", "Prompt Test"),
        ("config", "user.email", "prompt-test@example.invalid"),
        ("remote", "add", "origin", str(remote)),
        ("add", "-A"),
        ("commit", "-q", "-m", "chore: initial project"),
        ("push", "-q", "origin", "main"),
    ):
        git(*args, cwd=project)
    return project


def added_lines(project: Path) -> list[tuple[str, str]]:
    diff = git("diff", "main", "--unified=0", "--no-color", cwd=project)
    lines, path = [], ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("+") and path:
            lines.append((path, line[1:]))
    return lines


def run_sample(case: dict, plugins: Path, names: list[str], model: str | None) -> Sample | None:
    with tempfile.TemporaryDirectory(prefix="ahrena-agent-test-") as tmp:
        project = build_project(Path(tmp), case)
        command = ["claude", "-p", "--agent", case["agent"], "--setting-sources", "", "--strict-mcp-config",
                   "--permission-mode", "acceptEdits", "--allowedTools", TOOLS, "--max-turns", "150",
                   "--output-format", "stream-json", "--verbose", "--add-dir", str(plugins)]
        for name in names:
            command += ["--plugin-dir", str(plugins / "engineering" / name)]
        if model:
            command += ["--model", model]
        try:
            done = subprocess.run(command + [case["brief"]], cwd=project, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=3600)
        except (OSError, subprocess.TimeoutExpired):
            return None
        calls, result = parse_stream(done.stdout.splitlines())
        if result is None:
            return None
        pushed = [ref.split("refs/heads/")[-1] for ref in git("ls-remote", "--heads", "origin", cwd=project).split()
                  if ref.startswith("refs/heads/")]
        return Sample(calls, result, added_lines(project), pushed)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases")
    parser.add_argument("--only", help="comma list of case ids")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--out")
    return parser.parse_args()


def _run_all(spec: dict, cases: list[dict], args: argparse.Namespace) -> list[tuple[dict, Sample | None]]:
    with tempfile.TemporaryDirectory(prefix="ahrena-plugins-") as tmp:
        plugins = Path(tmp)
        for name in spec["plugins"]:
            shutil.copytree(REPO / "engineering" / name, plugins / "engineering" / name)
        jobs = [c for c in cases for _ in range(args.samples)]
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            samples = list(pool.map(lambda c: run_sample(c, plugins, spec["plugins"], args.model), jobs))
    return list(zip(jobs, samples))


def _report_case(case: dict, mine: list[Sample | None], rule: str) -> tuple[list[str], int]:
    if any(s is None for s in mine):
        return [f"## {case['id']}: UNDECIDED, a run returned no result"], 2
    verdicts = [decide(s, case, rule) for s in mine]
    passed = sum(1 for failed, _ in verdicts if not failed)
    ok = passed * 2 > len(mine)
    lines = [f"## {case['id']}: {'PASS' if ok else 'FAIL'} ({passed}/{len(mine)} samples)"]
    for (failed, marks), sample in zip(verdicts, mine):
        lines.append(f"- calls: writing #{marks['writing']}, rule #{marks['rule']}, first test #{marks['test']}, review #{marks['review']}")
        lines.extend(f"  - failed {f}" for f in failed)
        lines.append("\n```text\n" + (sample.result or "").strip() + "\n```\n")
    return lines, 0 if ok else 1


def main() -> int:
    args = _arguments()
    spec = json.loads(Path(args.cases).read_text())
    wanted = set(args.only.split(",")) if args.only else None
    cases = [c for c in spec["cases"] if wanted is None or c["id"] in wanted]
    runs = _run_all(spec, cases, args)
    report, code = [], 0
    for case in cases:
        lines, case_code = _report_case(case, [s for c, s in runs if c is case], spec["rule"])
        report += lines
        code = max(code, case_code)
    text = "\n".join(report) + "\n"
    print(text)
    if args.out:
        Path(args.out).write_text(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
