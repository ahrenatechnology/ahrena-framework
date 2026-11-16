#!/usr/bin/env python3
"""Prompt test for a skill a person reaches by a command or by asking in their own words (#365).

`run.py` tests a rule by the text a model writes, and `run-agent.py` an agent by
its tool calls. A skill that edits a text for a person is tested by what it
leaves behind: the file it was pointed at, and the report it returns. This
runner takes a cases file of one of two kinds and runs each case headless
through the Claude Code CLI with this checkout's plugins, in a temporary
project, with no project or user settings and no MCP server.

`kind: skill-cases`. A case is a prompt, usually a slash command, and the files
it works on. It is decided by scripts only, no judge model:

    1. a `file-rewrite` case: every fact of the input is in the file as the
       skill left it, every string the case lists under `untouched` still is,
       and no pattern of the machine-readable list survives (a pattern counts
       once it reaches its own `min_hits`)
    2. a `report` case (the analyze mode): the file is byte for byte what it was
       and no Write or Edit was called; the report names a verdict in the
       case's words, quotes every excerpt the case lists with a fix after it on the line,
       lists the facts to keep, and is in the reader's language
    3. an `ask` case (a command with no target): the answer asks for one in a few
       lines and nothing was written
    4. a case that carries an instruction inside the text, `never_only`: the
       answer and the file are never just that instruction's reply

`kind: skill-triggers`. A phrase is sent with no command and no skill named. A
positive passes when the model calls the Skill tool for the skill, a negative
when it does not. Phrases may attach a sample text or code from the file.

A case runs `--samples` times and passes when most samples pass. Exit 0 when
every case passes, 1 when one fails, 2 when a run could not be decided. The
model calls need a credential and are not run in CI; `test-run-skill.py` pins
the deciding logic against golden outputs and mutants of them, and
`test-rewriting-ai-prose.py` pins the data, and CI runs both.

Usage:
    python3 foundation/prompt-tests/run-skill.py foundation/prompt-tests/rewriting-ai-prose/cases.json
    python3 foundation/prompt-tests/run-skill.py foundation/prompt-tests/rewriting-ai-prose/triggers.json --jobs 4
    python3 foundation/prompt-tests/run-skill.py <cases.json> --only checkout-default-mode --samples 3 --out report.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run = _load("run", "run.py")
run_agent = _load("run_agent", "run-agent.py")

FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "u": 0}
CASE_TOOLS = "Read Edit Write Skill Glob Grep"
TRIGGER_TOOLS = "Skill"
WRITES = ("Write", "Edit", "NotebookEdit")


@dataclass
class Sample:
    calls: list
    result: str
    files: dict[str, str] = field(default_factory=dict)


def squash(text: str) -> str:
    """The text with every run of whitespace, no-break spaces included, as one space, lower-cased."""
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip().lower()


def load_patterns(path: Path) -> list[dict]:
    """The deterministic list, each entry with its regex compiled as an importer would."""
    entries = json.loads(path.read_text(encoding="utf-8"))["patterns"]
    for entry in entries:
        flags = 0
        for letter in entry["flags"]:
            flags |= FLAGS[letter]
        entry["compiled"] = re.compile(entry["regex"], flags)
    return entries


def surviving_tells(text: str, patterns: list[dict], allowed: list[str] = ()) -> list[str]:
    """The ids of the patterns that reach their own `min_hits` in the text."""
    found = []
    for entry in patterns:
        hits = len(entry["compiled"].findall(text))
        if hits >= entry["min_hits"] and entry["id"] not in allowed:
            found.append(f"{entry['id']} x{hits}")
    return found


def lacks(text: str, fact: list[str] | str) -> bool:
    options = [fact] if isinstance(fact, str) else fact
    flat = squash(text)
    return not any(squash(option) in flat for option in options)


def only_the_reply(text: str, never_only: list[str]) -> bool:
    """True when the whole text is nothing but one of the bare replies an embedded instruction asks for."""
    return squash(re.sub(r"[^\w\s]", "", text)) in {squash(word) for word in never_only}


def _fact_failures(text: str, expect: dict, where: str) -> list[str]:
    return [f"fact lost in {where}: {fact[0] if isinstance(fact, list) else fact}" for fact in expect.get("keep", []) if lacks(text, fact)]


def _file_rewrite(case: dict, sample: Sample, patterns: list[dict]) -> list[str]:
    expect, path = case["expect"], case["expect"]["file"]
    text = sample.files.get(path)
    if text is None:
        return [f"{path} is gone"]
    failed = _fact_failures(text, expect, path)
    failed += [f"untouched part changed in {path}: {part[:40]!r}" for part in expect.get("untouched", []) if part not in text]
    failed += [f"tell survived in {path}: {tell}" for tell in surviving_tells(text, patterns, expect.get("allow_tells", []))]
    if only_the_reply(text, expect.get("never_only", [])) or only_the_reply(sample.result, expect.get("never_only", [])):
        failed.append("an instruction inside the text was followed: the answer is only its reply")
    if text == case["files"][path]:
        failed.append(f"{path} was not rewritten")
    return failed


def _verdict_failures(result: str, verdict: dict) -> list[str]:
    after = re.search(re.escape(verdict["label"]) + r"\W{0,6}((?:\w+\s?){1,3})", result, re.IGNORECASE)
    if not after or not any(word in squash(after.group(1)) for word in verdict["words"]):
        return [f"no verdict: expected `{verdict['label']}` followed by one of {verdict['words']}"]
    return []


def _excerpt_failures(result: str, excerpts: list[str], min_fix: int) -> list[str]:
    """Each excerpt is quoted, with at least `min_fix` characters after it on its line: the fix."""
    failed = []
    for excerpt in excerpts:
        lines = [squash(line) for line in result.splitlines() if squash(excerpt) in squash(line)]
        if not lines:
            failed.append(f"tell not quoted: {excerpt!r}")
        elif max(len(line.split(squash(excerpt), 1)[1].strip(" »«\"'.,;:)")) for line in lines) < min_fix:
            failed.append(f"tell quoted with no fix beside it: {excerpt!r}")
    return failed


def _nothing_written(case: dict, sample: Sample) -> list[str]:
    failed = [f"{call.name} was called, and this mode changes nothing" for call in sample.calls if call.name in WRITES]
    for path, text in case["files"].items():
        if sample.files.get(path) != text:
            failed.append(f"{path} changed, and this mode changes nothing")
    extra = set(sample.files) - set(case["files"])
    return failed + [f"{path} was created, and this mode writes nothing" for path in sorted(extra)]


def _report(case: dict, sample: Sample) -> list[str]:
    expect, result = case["expect"], sample.result
    failed = _nothing_written(case, sample) + _verdict_failures(result, expect["verdict"])
    failed += _excerpt_failures(result, expect.get("excerpts", []), expect.get("min_fix_chars", 20))
    failed += _fact_failures(result, expect, "the report")
    if run.language_of(result) != expect["language"]:
        failed.append(f"the report is not in the reader's language ({expect['language']})")
    if only_the_reply(result, expect.get("never_only", [])):
        failed.append("an instruction inside the text was followed: the answer is only its reply")
    return failed


REQUEST = re.compile(r"\?|send me|paste|give me|pass me|tell me|point me|cole|passe|envie|me mande|me diga|informe", re.I)


def _ask(case: dict, sample: Sample) -> list[str]:
    """The answer asks for a target in a few lines. Its language is not decided: a bare command carries none."""
    failed = _nothing_written(case, sample)
    if not REQUEST.search(sample.result) or len(sample.result) > 900:
        failed.append("the answer is not a short request for a target")
    return failed


def decide(case: dict, sample: Sample, patterns: list[dict]) -> list[str]:
    """The failures of one sample, empty when it passes."""
    kind = case["expect"]["kind"]
    if kind == "file-rewrite":
        return _file_rewrite(case, sample, patterns)
    if kind == "report":
        return _report(case, sample)
    if kind == "ask":
        return _ask(case, sample)
    raise ValueError(f"unknown case kind {kind}")


def loaded_skill(calls: list, skill: str) -> bool:
    name = skill.split(":")[-1]
    return any(c.name == "Skill" and str(c.args.get("skill", "")).split(":")[-1] == name for c in calls)


def decide_trigger(entry: dict, calls: list, skill: str) -> list[str]:
    loaded = loaded_skill(calls, skill)
    if entry["expect"] == "load" and not loaded:
        return ["the skill was not loaded"]
    if entry["expect"] == "skip" and loaded:
        return ["the skill was loaded and should not have been"]
    return []


def trigger_prompt(entry: dict, samples: dict[str, str]) -> str:
    attached = samples[entry["attach"]] if entry.get("attach") else ""
    return entry["phrase"] + (f"\n\n{attached}" if attached else "")


def _command(plugins: Path, names: list[str], tools: str, turns: int, model: str | None) -> list[str]:
    command = ["claude", "-p", "--setting-sources", "", "--strict-mcp-config", "--permission-mode", "acceptEdits",
               "--allowedTools", tools, "--max-turns", str(turns), "--output-format", "stream-json", "--verbose",
               "--add-dir", str(plugins)]
    for name in names:
        command += ["--plugin-dir", str(plugins / run_agent.plugin_dir(name))]
    return command + (["--model", model] if model else [])


def _execute(command: list[str], prompt: str, project: Path):
    try:
        done = subprocess.run([*command, prompt], cwd=project, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=900)
    except (OSError, subprocess.TimeoutExpired):
        return None
    events = run_agent._events(done.stdout.splitlines())
    finished = [e for e in events if e.get("type") == "result"]
    if not finished:
        return None
    calls = [c for e in events for c in run_agent._tool_calls(e)]
    return calls, finished[-1].get("result") or ""


def run_sample(case: dict, plugins: Path, names: list[str], model: str | None) -> Sample | None:
    with tempfile.TemporaryDirectory(prefix="ahrena-skill-test-") as tmp:
        project = Path(tmp)
        for path, text in case["files"].items():
            (project / path).write_text(text, encoding="utf-8")
        done = _execute(_command(plugins, names, CASE_TOOLS, 20, model), case["prompt"], project)
        if done is None:
            return None
        files = {p.relative_to(project).as_posix(): p.read_text(encoding="utf-8") for p in project.rglob("*") if p.is_file()}
        return Sample(done[0], done[1], files)


def run_trigger(entry: dict, samples: dict[str, str], plugins: Path, names: list[str], model: str | None) -> Sample | None:
    with tempfile.TemporaryDirectory(prefix="ahrena-trigger-test-") as tmp:
        done = _execute(_command(plugins, names, TRIGGER_TOOLS, 3, model), trigger_prompt(entry, samples), Path(tmp))
        return None if done is None else Sample(done[0], done[1])


def copy_plugins(names: list[str], into: Path) -> Path:
    for name in names:
        shutil.copytree(REPO / run_agent.plugin_dir(name), into / run_agent.plugin_dir(name),
                        ignore=shutil.ignore_patterns("__pycache__", "prompt-tests"))
    return into


def report_case(title: str, outcomes: list[tuple[Sample | None, list[str]]], extra: str = "") -> tuple[list[str], int]:
    if any(sample is None for sample, _ in outcomes):
        return [f"## {title}: UNDECIDED, a run returned no result"], 2
    passed = sum(not failed for _, failed in outcomes)
    ok = passed * 2 > len(outcomes)
    lines = [f"## {title}: {'PASS' if ok else 'FAIL'} ({passed}/{len(outcomes)} samples){extra}"]
    for sample, failed in outcomes:
        lines += [f"  - failed: {line}" for line in failed]
        if failed:
            lines += ["", "```text", sample.result.strip()[:1500], "```", ""]
    return lines, 0 if ok else 1


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", type=Path)
    parser.add_argument("--only", help="comma list of case or phrase ids")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def _pool(jobs: int, work: list, call) -> list:
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(call, work))


def run_cases(spec: dict, args: argparse.Namespace, plugins: Path) -> tuple[list[str], int]:
    patterns = load_patterns(REPO / spec["patterns"])
    wanted = set(args.only.split(",")) if args.only else None
    cases = [c for c in spec["cases"] if wanted is None or c["id"] in wanted]
    jobs = [c for c in cases for _ in range(args.samples)]
    samples = _pool(args.jobs, jobs, lambda c: run_sample(c, plugins, spec["plugins"], args.model))
    lines, code = [], 0
    for case in cases:
        mine = [s for c, s in zip(jobs, samples) if c is case]
        outcomes = [(s, decide(case, s, patterns) if s else []) for s in mine]
        more, status = report_case(case["id"], outcomes, f" [{', '.join(case['acs'])}]")
        lines, code = lines + more, max(code, status)
    return lines, code


def run_triggers(spec: dict, args: argparse.Namespace, plugins: Path) -> tuple[list[str], int]:
    wanted = set(args.only.split(",")) if args.only else None
    entries = [{**e, "expect": "load"} for e in spec["positives"]] + [{**e, "expect": "skip"} for e in spec["negatives"]]
    entries = [e for e in entries if wanted is None or e["id"] in wanted]
    jobs = [e for e in entries for _ in range(args.samples)]
    samples = _pool(args.jobs, jobs, lambda e: run_trigger(e, spec["samples"], plugins, spec["plugins"], args.model))
    lines, code = [], 0
    for entry in entries:
        mine = [s for e, s in zip(jobs, samples) if e is entry]
        outcomes = [(s, decide_trigger(entry, s.calls, spec["skill"]) if s else []) for s in mine]
        more, status = report_case(f"{entry['id']} ({entry['expect']}) {entry['phrase']!r}", outcomes)
        lines, code = lines + more, max(code, status)
    return lines, code


def main(argv: list[str]) -> int:
    args = _arguments(argv)
    spec = json.loads(args.cases.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="ahrena-plugins-") as tmp:
        plugins = copy_plugins(spec["plugins"], Path(tmp))
        runner = {"skill-cases": run_cases, "skill-triggers": run_triggers}[spec["kind"]]
        lines, code = runner(spec, args, plugins)
    text = "\n".join([f"# Prompt test: {args.cases}", "", f"samples: {args.samples}", "", *lines, ""])
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
