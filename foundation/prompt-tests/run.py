#!/usr/bin/env python3
"""Prompt test for a rule a model reads: run it, then decide the output.

A rule with `enforcement: judgment` is text a model follows. Reading it shows
what it asks for; only an output shows what it produces. This runner gives a
model the rule and a situation, takes the text it writes for a person, and
decides that text twice:

    1. a script decides what a script can: the text's language, a protocol
       field pasted into it, an internal identifier, a closing with more than
       one question or an offer of further help, a filler adjective
    2. a second model call, the judge, decides the rule's numbered conditions
       against the same text and returns one verdict per condition

Each case runs `--samples` times and passes when most samples pass, because one
sample of a model is an anecdote. The report prints every output, so a reviewer
reads what was decided and not only the verdict.

The model is reached through the Claude Code CLI with no project settings, no
tools and no plugins, from the system's temporary directory, so no project
instruction file is in reach and the rule is the only instruction in play. Another
platform's command is passed with `--runner`; it receives the whole prompt on
standard input and prints the answer.

Exit 0 when every case passes, 1 when one fails, 2 when nothing was decided for
a case: the model could not be reached, or the judge's answer lacked a verdict
for a condition. The report keeps the cases decided before it. Standard library
only.

Usage:
    python3 foundation/prompt-tests/run.py foundation/prompt-tests/person-facing-text/cases.json
    python3 foundation/prompt-tests/run.py <cases.json> --samples 3 --model sonnet --out report.md
    python3 foundation/prompt-tests/run.py <cases.json> --baseline
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CLAUDE = [
    "claude", "-p", "--tools", "", "--setting-sources", "", "--strict-mcp-config",
    "--disable-slash-commands", "--no-session-persistence",
]

STOPWORDS = {
    "pt": {"de", "que", "não", "para", "uma", "com", "os", "em", "é", "da", "você", "sem"},
    "en": {"the", "and", "of", "to", "is", "that", "for", "with", "you", "this", "it", "are"},
}

PROTOCOL = re.compile(
    r"^(?:DONE|BLOCKED|NEEDS_APPROVAL)\s*$"
    r"|^(?:approve|recommendation|child|resume|exists|blocker|needs|layers|reviews|landed|left|injected):",
    re.M,
)

AGENTS = (
    "athena", "argos", "apollo", "iris", "clio", "janus", "erodos", "hermes",
    "themis", "hephaestus", "aglaia", "daedalus", "mnemosyne",
)

IDENTIFIERS = [
    ("a decision-record number", re.compile(r"\bADR-\d+")),
    ("a file and line", re.compile(r"\b[\w/.-]+\.(?:tsx?|jsx?|py|md|json|sql):\d+")),
    ("a path in code formatting", re.compile(r"`[^`\n]*/[^`\n]*`")),
    ("an agent's name", re.compile(r"\b(?:" + "|".join(AGENTS) + r")\b", re.I)),
]

REFERENCE = re.compile(r"#(\d+)")
OFFERS = re.compile(
    r"posso ajudar|qualquer d[uú]vida|fico [àa] disposi[cç][aã]o|se precisar de (?:mais )?algo"
    r"|let me know if|anything else|happy to help",
    re.I,
)
FILLERS = re.compile(r"\b(?:significativ\w+|robust\w+|divers[oa]s)\b", re.I)

JUDGED = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10")

WRITER = (
    "You are the agent of a coding session. You have no tools here. "
    "Write only the text the person will read, with nothing before or after it."
)

JUDGE = (
    "You review one text an agent wrote for a person, against the numbered conditions of the rule "
    "you are given. Decide each condition from 1 to 10 on the text alone. Answer `pass`, `fail`, or "
    "`na` when the situation gives the condition nothing to apply to. Quote the words that decided "
    "it. Fail a condition only on words that break it as the rule states it, counting what the "
    "condition itself allows; words the condition allows are a pass. Return one JSON object and nothing else, shaped as "
    '{"1": {"verdict": "pass", "evidence": "..."}, "2": {...}}.'
)


@dataclass
class Case:
    id: str
    situation: str
    language: str = "pt"
    allowed_refs: list[str] = field(default_factory=list)


@dataclass
class Sample:
    text: str
    scripted: list[str]
    judged: dict[str, dict]

    @property
    def failures(self) -> list[str]:
        failed = [f"condition {n}: {v.get('evidence', '')}" for n, v in self.judged.items() if v.get("verdict") == "fail"]
        return self.scripted + failed


class Unreachable(Exception):
    """The model could not be called, so nothing was observed."""


def language_of(text: str) -> str:
    words = re.findall(r"[a-zà-ú]+", text.lower())
    counts = {lang: sum(1 for w in words if w in stop) for lang, stop in STOPWORDS.items()}
    return max(counts, key=counts.get)


def closing_of(text: str) -> str:
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return paragraphs[-1] if paragraphs else ""


def scripted_failures(text: str, case: Case) -> list[str]:
    found = []
    if language_of(text) != case.language:
        found.append(f"premise: the text is not in the person's language ({case.language})")
    hit = PROTOCOL.search(text)
    if hit:
        found.append(f"condition 9: a protocol field was pasted: {hit.group(0).strip()!r}")
    for what, pattern in IDENTIFIERS:
        hit = pattern.search(text)
        if hit:
            found.append(f"condition 9: {what}: {hit.group(0)!r}")
    strangers = [f"#{n}" for n in REFERENCE.findall(text) if n not in case.allowed_refs]
    if strangers:
        found.append(f"condition 9: a reference the person need not open: {', '.join(sorted(set(strangers)))}")
    closing = closing_of(text)
    if closing.count("?") > 1:
        found.append("condition 10: the closing asks more than one question")
    hit = OFFERS.search(closing)
    if hit:
        found.append(f"condition 10: the closing offers further help: {hit.group(0)!r}")
    hit = FILLERS.search(text)
    if hit:
        found.append(f"condition 7: an adjective in a number's place: {hit.group(0)!r}")
    return found


def unreadable(why: str, answer: str) -> ValueError:
    return ValueError(f"{why}; the judge answered: {answer[:500]!r}")


def parse_verdicts(answer: str) -> dict[str, dict]:
    start = answer.find("{")
    if start < 0:
        raise unreadable("the judge returned no JSON object", answer)
    try:
        raw, _ = json.JSONDecoder().raw_decode(answer, start)
    except json.JSONDecodeError as error:
        raise unreadable(f"the judge's JSON could not be read ({error.msg})", answer) from error
    verdicts = {}
    for number in JUDGED:
        entry = raw.get(number) if isinstance(raw, dict) else None
        if not isinstance(entry, dict) or entry.get("verdict") not in ("pass", "fail", "na"):
            raise unreadable(f"the judge gave no verdict for condition {number}", answer)
        verdicts[number] = entry
    return verdicts


def passes(samples: list[bool]) -> bool:
    return sum(samples) * 2 > len(samples)


def ask(system: str, prompt: str, model: str, runner: str | None) -> str:
    if runner:
        command, stdin = shlex.split(runner), f"{system}\n\n{prompt}"
    else:
        command, stdin = [*CLAUDE, "--model", model, "--system-prompt", system], prompt
    try:
        done = subprocess.run(command, input=stdin, capture_output=True, text=True, timeout=300, cwd=tempfile.gettempdir())
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unreachable(str(error)) from error
    if done.returncode != 0 or not done.stdout.strip():
        raise Unreachable(done.stderr.strip() or "the model returned nothing")
    return done.stdout.strip()


def write_text(rule: str, case: Case, args: argparse.Namespace) -> str:
    system = WRITER if args.baseline else f"{WRITER}\n\nFollow this rule in everything you write for a person.\n\n{rule}"
    prompt = f"{case.situation}\n\nWrite the message you would now send to the person."
    return ask(system, prompt, args.model, args.runner)


def judge_text(rule: str, case: Case, text: str, args: argparse.Namespace) -> dict[str, dict]:
    prompt = f"<rule>\n{rule}\n</rule>\n\n<situation>\n{case.situation}\n</situation>\n\n<text>\n{text}\n</text>"
    return parse_verdicts(ask(JUDGE, prompt, args.judge_model, args.runner))


def run_case(rule: str, case: Case, args: argparse.Namespace) -> list[Sample]:
    samples = []
    for _ in range(args.samples):
        text = write_text(rule, case, args)
        samples.append(Sample(text, scripted_failures(text, case), judge_text(rule, case, text, args)))
    return samples


def load(path: Path) -> tuple[str, list[Case]]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    rule = (REPO / spec["rule"]).read_text(encoding="utf-8")
    return rule, [Case(**entry) for entry in spec["cases"]]


def report(case: Case, samples: list[Sample]) -> list[str]:
    ok = passes([not s.failures for s in samples])
    lines = [f"## {case.id}: {'passes' if ok else 'FAILS'} ({sum(not s.failures for s in samples)} of {len(samples)} samples)", ""]
    for number, sample in enumerate(samples, 1):
        lines += [f"### Sample {number}", "", *[f"> {line}" for line in sample.text.splitlines()], ""]
        lines += [f"- {failure}" for failure in sample.failures] or ["- no failure"]
        lines.append("")
    return lines


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a rule's prompt test.")
    parser.add_argument("cases", type=Path)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--judge-model", default="sonnet")
    parser.add_argument("--runner", help="a command that reads the prompt on stdin, instead of the Claude Code CLI")
    parser.add_argument("--baseline", action="store_true", help="write without the rule, to see what the rule changes")
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def finish(lines: list[str], args: argparse.Namespace) -> None:
    text = "\n".join(lines)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    rule, cases = load(args.cases)
    lines, failed = [f"# Prompt test: {args.cases}", "", f"baseline: {args.baseline}; samples: {args.samples}; model: {args.model}", ""], 0
    for case in cases:
        try:
            samples = run_case(rule, case, args)
        except (Unreachable, ValueError) as error:
            finish([*lines, f"not run: case {case.id}: {error}"], args)
            print(f"not run: case {case.id}: {error}", file=sys.stderr)
            return 2
        failed += not passes([not s.failures for s in samples])
        lines += report(case, samples)
    finish([*lines, f"{len(cases)} case(s), {failed} failure(s)."], args)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
