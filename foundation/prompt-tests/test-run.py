#!/usr/bin/env python3
"""Tests for run.py: the part of a prompt test that needs no model.

The script-decided checks are pinned here by a text that must pass and a text
that must fail each one, and so are the judge's answer parsing and the rule
that a case passes on most of its samples. The model calls are not exercised:
they need a credential, and what they return is what the test is for.

Covers #291/AC-6.

Usage:
    python3 foundation/prompt-tests/test-run.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run", HERE / "run.py")
run = importlib.util.module_from_spec(spec)
sys.modules["run"] = run
spec.loader.exec_module(run)

GOOD = (
    "Com isso, o paciente troca o horário da consulta sozinho, pelo portal.\n\n"
    "Hoje, quem quer mudar a consulta liga para a recepção. Foram 340 ligações em outubro, "
    "pelo registro da recepção.\n\n"
    "Aprova as três entregas?"
)


def failures(text: str, **case) -> list[str]:
    return run.scripted_failures(text, run.Case(id="c", situation="s", **case))


def has(found: list[str], needle: str) -> bool:
    return any(needle in line for line in found)


def verdicts(**changed) -> str:
    answer = {n: {"verdict": "pass", "evidence": "x"} for n in run.JUDGED}
    answer.update(changed)
    return json.dumps(answer)


CASES = [
    ("a text that meets every scripted check has no failure", lambda: failures(GOOD) == []),
    ("a text in English fails the premise for a Portuguese reader",
     lambda: has(failures("The plan is ready and it is waiting for you to approve the three parts of it."), "premise")),
    ("a text in English passes for a reader who writes in English",
     lambda: not has(failures("The plan is ready and it is waiting for you to approve it.", language="en"), "premise")),
    ("a text in Portuguese fails for a reader who writes in English",
     lambda: has(failures(GOOD, language="en"), "premise")),
    ("a pasted first line of the protocol fails", lambda: has(failures("NEEDS_APPROVAL\n\n" + GOOD), "protocol field")),
    ("a pasted protocol field fails", lambda: has(failures(GOOD + "\n\nresume: relaunch com a aprovação"), "protocol field")),
    ("a word that only resembles a field passes",
     lambda: not has(failures("O que existe hoje é uma planilha.\n\n" + GOOD), "protocol field")),
    ("a decision-record number fails", lambda: has(failures("Segue a emenda do ADR-012.\n\n" + GOOD), "decision-record")),
    ("a file and line fails", lambda: has(failures("O erro está em Reschedule.tsx:142.\n\n" + GOOD), "file and line")),
    ("a path in code formatting fails", lambda: has(failures("Mexe em `web/portal`.\n\n" + GOOD), "path in code")),
    ("an agent's name fails", lambda: has(failures("O Argos pediu mudanças.\n\n" + GOOD), "agent's name")),
    ("a reference the person need not open fails", lambda: has(failures("A parte 1 entrou no #95.\n\n" + GOOD), "#95")),
    ("a reference the case allows passes",
     lambda: not has(failures("Abra o #131 e veja a tela.\n\n" + GOOD, allowed_refs=["131"]), "need not open")),
    ("two questions in the closing fail",
     lambda: has(failures(GOOD.replace("Aprova as três entregas?", "Aprova? Ou prefere só duas?")), "more than one question")),
    ("a question earlier in the text does not count against the closing",
     lambda: not has(failures("Por que isso importa? Porque a recepção atende 340 ligações.\n\n" + GOOD), "more than one")),
    ("a closing offer of help fails",
     lambda: has(failures(GOOD + "\n\nQualquer dúvida, é só chamar."), "offers further help")),
    ("a filler adjective fails", lambda: has(failures("O volume é significativo.\n\n" + GOOD), "adjective")),
    ("the judge's answer is read out of surrounding prose",
     lambda: run.parse_verdicts("Here it is:\n" + verdicts() + "\nDone.")["3"]["verdict"] == "pass"),
    ("a judged failure reaches the sample's failures",
     lambda: has(run.Sample(GOOD, [], run.parse_verdicts(verdicts(**{"4": {"verdict": "fail", "evidence": "no proposal"}}))).failures, "condition 4")),
    ("a verdict of na is not a failure",
     lambda: run.Sample(GOOD, [], run.parse_verdicts(verdicts(**{"3": {"verdict": "na", "evidence": ""}}))).failures == []),
    ("two of three samples passing passes the case", lambda: run.passes([True, True, False])),
    ("one of three samples passing fails the case", lambda: not run.passes([True, False, False])),
    ("one of two samples passing fails the case", lambda: not run.passes([True, False])),
]


def raises(call) -> bool:
    try:
        call()
    except ValueError:
        return True
    return False


CASES += [
    ("an answer with no JSON object is an error, not a pass", lambda: raises(lambda: run.parse_verdicts("all good"))),
    ("an answer missing a condition is an error, not a pass",
     lambda: raises(lambda: run.parse_verdicts(json.dumps({"1": {"verdict": "pass"}})))),
    ("an unknown verdict is an error, not a pass",
     lambda: raises(lambda: run.parse_verdicts(verdicts(**{"2": {"verdict": "maybe"}})))),
    ("the shipped cases load, each against a rule that exists",
     lambda: len(run.load(HERE / "person-facing-text" / "cases.json")[1]) == 5),
]


def not_run(runner: str, out: Path) -> tuple[int, str]:
    cases = str(HERE / "person-facing-text" / "cases.json")
    done = subprocess.run(
        [sys.executable, str(HERE / "run.py"), cases, "--samples", "1", "--runner", runner, "--out", str(out)],
        capture_output=True, text=True,
    )
    return done.returncode, done.stderr


def unreachable_names_its_case() -> bool:
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "report.md"
        code, stderr = not_run("false", out)
        return code == 2 and "not run: case plan-for-approval" in stderr and "not run: case plan-for-approval" in out.read_text()


def unparsed_judge_is_not_run() -> bool:
    with tempfile.TemporaryDirectory() as folder:
        code, stderr = not_run("echo no-verdicts-here", Path(folder) / "report.md")
        return code == 2 and "the judge returned no JSON object" in stderr


CASES += [
    ("a model that cannot be reached exits 2, names the case and still writes the report", unreachable_names_its_case),
    ("a judge whose answer cannot be read exits 2, not 1", unparsed_judge_is_not_run),
]


def main() -> int:
    failed = 0
    for name, check in CASES:
        ok = check()
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {name}")
    print(f"\n{len(CASES) - failed} cases passed." if not failed else f"\n{failed} of {len(CASES)} cases failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
