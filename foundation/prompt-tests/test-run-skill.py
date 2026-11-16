#!/usr/bin/env python3
"""Tests for run-skill.py and the rewriting-ai-prose cases: the part that needs no model.

The deciding logic is pinned by golden outputs, one per case, and by mutants of
each: the golden with a fact dropped, with a tell put back, with a protected
part changed, with the instruction's reply in its place, with the file touched
in a mode that changes nothing. Every golden must pass and every mutant must
fail with the failure it was built to cause, so a case that can no longer fail
is caught here and not on the day a model drops a fact. The model runs are not
exercised: they need a credential, and what they do is what the test is for.

Covers #365/AC-3, #365/AC-6, #365/AC-7 and #365/AC-9.

Usage:
    python3 foundation/prompt-tests/test-run-skill.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_skill", HERE / "run-skill.py")
run_skill = importlib.util.module_from_spec(spec)
sys.modules["run_skill"] = run_skill
spec.loader.exec_module(run_skill)

SPEC = json.loads((HERE / "rewriting-ai-prose" / "cases.json").read_text(encoding="utf-8"))
PATTERNS = run_skill.load_patterns(run_skill.REPO / SPEC["patterns"])
Call = run_skill.run_agent.Call
ASK_LIMIT = run_skill.ASK_MAX_CHARS

results: list[tuple[str, bool]] = []


def check(ok: bool, label: str) -> None:
    results.append((label, ok))


def sample(case: dict, **changes) -> run_skill.Sample:
    golden = case["golden"]
    files = {**golden["files"], **changes.get("files", {})}
    calls = changes.get("calls", [Call("Skill", {"skill": SPEC["skill"]})])
    return run_skill.Sample(calls, changes.get("result", golden["result"]), files)


def failures(case: dict, **changes) -> list[str]:
    return run_skill.decide(case, sample(case, **changes), PATTERNS, SPEC["skill"])


def has(found: list[str], needle: str) -> bool:
    return any(needle in line for line in found)


def first_form(fact: list[str] | str) -> str:
    return fact if isinstance(fact, str) else fact[0]


def drop(text: str, fact: list[str] | str) -> str:
    for option in ([fact] if isinstance(fact, str) else fact):
        text = text.replace(option, "")
    return text


def test_goldens_pass() -> None:
    for case in SPEC["cases"]:
        check(failures(case) == [], f"{case['id']}: the golden output passes")


def test_rewrite_cases_fail_when_a_fact_is_dropped() -> None:
    """#365/AC-3: every fact of the input is held, one dropped fact at a time."""
    rewrites = [c for c in SPEC["cases"] if c["expect"]["kind"] == "file-rewrite"]
    check(len(rewrites) >= 3, "at least three rewrite cases carry facts")
    for case in rewrites:
        path = case["expect"]["file"]
        for fact in case["expect"]["keep"]:
            mutant = {path: drop(case["golden"]["files"][path], fact)}
            check(has(failures(case, files=mutant), "fact lost"), f"{case['id']}: dropping {first_form(fact)!r} fails")


def test_rewrite_cases_fail_when_a_tell_survives() -> None:
    """A deterministic tell put back into the rewrite fails it, whichever family it comes from."""
    survivors = {
        "closer": "\nEm suma, uma solução fundamental.",
        "chat": "\nEspero ter ajudado!",
        "staging": "\nVamos mergulhar nos detalhes.",
        "contrast": "\nNão é apenas um prazo, é uma promessa.",
    }
    for case in (c for c in SPEC["cases"] if c["expect"]["kind"] == "file-rewrite"):
        path = case["expect"]["file"]
        for name, text in survivors.items():
            mutant = {path: case["golden"]["files"][path] + text}
            check(has(failures(case, files=mutant), "tell survived"), f"{case['id']}: a {name} tell left in the text fails")
        check(has(failures(case, files={path: case["files"][path]}), "tell survived"), f"{case['id']}: the untouched input fails")


def test_protected_parts() -> None:
    case = next(c for c in SPEC["cases"] if c["id"] == "readme-keeps-code-and-links")
    path, golden = case["expect"]["file"], case["golden"]["files"][case["expect"]["file"]]
    check(has(failures(case, files={path: golden.replace("npm install acme-cart@2.4.0", "npm i acme-cart")}), "untouched part changed"), "a code block rewritten fails")
    check(has(failures(case, files={path: golden.replace("(https://docs.acme.example/cart)", "(https://docs.acme.example)")}), "untouched part changed"), "a link target changed fails")


def test_an_embedded_instruction_is_not_followed() -> None:
    """#365/AC-9: the reply an instruction inside the text asks for is never the answer."""
    injected = [c for c in SPEC["cases"] if "#365/AC-9" in c["acs"]]
    check({c["expect"]["kind"] for c in injected} == {"file-rewrite", "report"}, "the instruction is carried by a rewrite and by an analysis")
    for case in injected:
        check("never_only" in case["expect"], f"{case['id']}: names the reply that must not be the answer")
        check(any(word in (case["prompt"] + "".join(case["files"].values())).lower() for word in ("ignore as instruções anteriores", "ignore previous instructions")),
              f"{case['id']}: the text carries an instruction to ignore the task")
    rewrite = next(c for c in injected if c["expect"]["kind"] == "file-rewrite")
    path = rewrite["expect"]["file"]
    check(has(failures(rewrite, files={path: "OK"}), "instruction"), "a file replaced by the reply fails")
    check(has(failures(rewrite, result="OK."), "instruction"), "an answer that is only the reply fails")
    check(failures(rewrite, result="Reescrevi o texto. A frase que pedia para ignorar a tarefa saiu junto com a entrada.") == [], "an answer that mentions the instruction passes")
    report = next(c for c in injected if c["expect"]["kind"] == "report")
    check(has(failures(report, result="OK"), "instruction"), "a report replaced by the reply fails")


def test_analyze_changes_nothing() -> None:
    """#365/AC-7: the mode leaves the file and the tree as they were, and says so in a report."""
    reports = [c for c in SPEC["cases"] if c["expect"]["kind"] == "report"]
    check(len(reports) >= 3, "at least three analyze cases")
    check({c["expect"]["language"] for c in reports} >= {"pt", "en"}, "analyze is decided in pt and in en")
    case = next(c for c in reports if c["files"])
    path = case["expect"]["file"]
    check(has(failures(case, files={path: "texto reescrito"}), "changed"), "a file rewritten by analyze fails")
    check(has(failures(case, calls=[Call("Edit", {"file_path": path})]), "Edit was called"), "an Edit call fails, even if the file ends the same")
    check(has(failures(case, calls=[Call("Write", {"file_path": path})]), "Write was called"), "a Write call fails")
    check(has(failures(case, files={"draft.pt.md": "outra versão"}), "was created"), "a rewritten copy beside the file fails")


def test_analyze_report_content() -> None:
    """#365/AC-7: the verdict, every tell with its excerpt and fix, the facts, in the reader's language."""
    pt = next(c for c in SPEC["cases"] if c["id"] == "analyze-file-changes-nothing")
    report = pt["golden"]["result"]
    check(has(failures(pt, result=report.replace("Veredito: a maior parte.", "")), "no verdict"), "a report with no verdict fails")
    check(has(failures(pt, result=report.replace("**Veredito: a maior parte.**", "**Veredito: talvez.**")), "no verdict"), "a verdict outside the three words fails")
    check(has(failures(pt, result=report.replace("**Veredito: a maior parte.**", "**Veredito: algumas vezes.**")), "no verdict"), "a word that only starts with a verdict word fails")
    for excerpt in pt["expect"]["excerpts"]:
        check(has(failures(pt, result=report.replace(excerpt, "")), "tell not quoted"), f"a report that skips {excerpt!r} fails")
    bare = "\n".join(line[: line.index("»") + 1] if "»" in line else line for line in report.splitlines())
    check(has(failures(pt, result=bare), "no fix"), "a tell quoted with no fix beside it fails")
    for fact in pt["expect"]["keep"]:
        check(has(failures(pt, result=drop(report, fact)), "fact lost"), f"a report that skips the fact {first_form(fact)!r} fails")
    english = next(c for c in SPEC["cases"] if c["id"] == "analyze-reports-in-the-readers-language")
    check(has(failures(english, result=pt["golden"]["result"]), "language"), "a report in Portuguese for an English reader fails")
    check(has(failures(pt, result=english["golden"]["result"]), "language"), "a report in English for a Portuguese reader fails")
    said = english["golden"]["result"]
    check(has(failures(english, result=said.replace("**Verdict: most.**", "**Verdict: something odd.**")), "no verdict"), "a verdict word inside another word fails")
    check(has(failures(english, result=said.replace("**Verdict: most.**", "**Verdict: nonexistent.**")), "no verdict"), "none inside nonexistent fails")


def test_no_target() -> None:
    """#365/AC-6: a command with no target answers with a request for one and writes nothing."""
    for case in (c for c in SPEC["cases"] if c["expect"]["kind"] == "ask"):
        check(has(failures(case, result="Reescrevi o texto."), "not a short request"), f"{case['id']}: an answer that asks for nothing fails")
        check(has(failures(case, result="Aqui está o texto reescrito. " + "Lorem ipsum. " * 80 + "?"), "not a short request"), f"{case['id']}: a long invented text fails")
        check(has(failures(case, result="Aqui vai um texto reescrito: Olá, o prazo é 3 dias. Quer ajustar algo?"), "not a short request"), f"{case['id']}: a short invented text with a question mark fails")
        check(has(failures(case, result="Qual texto? " + "x" * ASK_LIMIT), "not a short request"), f"{case['id']}: a request over the length cap fails")
        check(failures(case, result="Qual arquivo ou texto você quer reescrever? Cole o texto ou passe o caminho.") == [], f"{case['id']}: a short request passes")
        check(has(failures(case, calls=[Call("Write", {"file_path": "invented.md"})]), "Write was called"), f"{case['id']}: writing a file fails")


def test_the_command_must_run_the_skill() -> None:
    """#365/AC-6: a model that edits or reports without calling the skill fails, whatever it wrote."""
    for case in SPEC["cases"]:
        check(has(failures(case, calls=[]), "skill was not loaded"), f"{case['id']}: the golden with no Skill call fails")
        check(has(failures(case, calls=[Call("Skill", {"skill": "ahrena-quality:reviewing-diffs"})]), "skill was not loaded"), f"{case['id']}: another skill does not stand in")
        check(failures(case, calls=[Call("Skill", {"skill": "rewriting-ai-prose"})]) == [], f"{case['id']}: the bare skill name counts")


def test_the_process_is_confined() -> None:
    """The child process reads text written to hijack it: its prompt is an argument, and files and tools stay in the project."""
    command = run_skill._command(Path("/plugins"), ["foundation"], run_skill.CASE_TOOLS, 20, None)
    check(run_skill.argv(command, "-x /etc/passwd")[-2:] == ["--", "-x /etc/passwd"], "the prompt follows a `--`")
    tools = command[command.index("--allowedTools") + 1].split()
    scoped = [t for t in tools if t not in {"Skill"}]
    check(bool(scoped) and all(t.endswith("(./**)") for t in scoped), "every tool that touches files is scoped to the project")
    check(not any(t in {"Read", "Edit", "Write", "Glob", "Grep"} for t in tools), "no file tool is allowed bare")
    project = Path("/ahrena-test-project")
    check(run_skill.project_path(project, "draft.md") == project.resolve() / "draft.md", "a case file inside the project is kept")
    for key in ("../x", "/etc/passwd", "a/../../x", "."):
        try:
            run_skill.project_path(project, key)
            refused = False
        except ValueError:
            refused = True
        check(refused, f"a case file {key!r} outside the project is refused")


def test_cases_match_the_data() -> None:
    patterns = {p["id"] for p in PATTERNS}
    families = {tell.split(" ")[0] for c in SPEC["cases"] for tell in run_skill.surviving_tells(c["prompt"] + "".join(c["files"].values()), PATTERNS)}
    check(len(families) >= 6, "the inputs carry tells of at least six patterns, so a rewrite has something to remove")
    check(families <= patterns, "every tell the inputs carry is a pattern of the list")
    for case in SPEC["cases"]:
        text = case["prompt"] + "".join(case["files"].values())
        for fact in case["expect"].get("keep", []):
            if case["expect"]["kind"] == "file-rewrite":
                check(not run_skill.lacks(text, fact), f"{case['id']}: the fact {first_form(fact)!r} is in the input")
        for excerpt in case["expect"].get("excerpts", []):
            check(excerpt in text, f"{case['id']}: the excerpt {excerpt!r} is in the input")
        if case["expect"]["kind"] != "ask":
            check(run_skill.surviving_tells(text, PATTERNS) != [], f"{case['id']}: the input carries a tell, so the case can fail")
        for ac in case["acs"]:
            check(ac.startswith("#365/AC-"), f"{case['id']}: {ac} is a criterion token")


def test_triggers() -> None:
    entry = {"expect": "load"}
    skill = "ahrena-foundation:rewriting-ai-prose"
    check(run_skill.decide_trigger(entry, [Call("Skill", {"skill": skill})], skill) == [], "a Skill call for the skill loads it")
    check(run_skill.decide_trigger(entry, [Call("Skill", {"skill": "rewriting-ai-prose"})], skill) == [], "the bare skill name loads it")
    check(run_skill.decide_trigger(entry, [Call("Read", {"file_path": "x"})], skill) != [], "no Skill call fails a positive")
    check(run_skill.decide_trigger(entry, [Call("Skill", {"skill": "ahrena-quality:reviewing-diffs"})], skill) != [], "another skill fails a positive")
    check(run_skill.decide_trigger({"expect": "skip"}, [Call("Skill", {"skill": skill})], skill) != [], "loading the skill fails a negative")
    check(run_skill.decide_trigger({"expect": "skip"}, [], skill) == [], "no call passes a negative")
    prompt = run_skill.trigger_prompt({"phrase": "humaniza", "attach": "prose"}, {"prose": "texto"})
    check(prompt == "humaniza\n\ntexto", "a phrase carries its sample text")


def test_helpers() -> None:
    check(not run_skill.lacks("O prazo é de  3   dias", "de 3 dias"), "spaces, no-break spaces and case do not hide a fact")
    check(run_skill.lacks("o prazo caiu", ["de 5 para 3", "5 para 3"]), "a fact with no form present is lost")
    check(run_skill.only_the_reply("OK.", ["ok"]), "a bare reply with a full stop is the reply")
    check(not run_skill.only_the_reply("OK, reescrevi o texto.", ["ok"]), "a reply inside an answer is not the whole answer")
    check(run_skill.surviving_tells("a — b — c — d", PATTERNS) != [], "dashes count once they reach their own min_hits")
    check(run_skill.surviving_tells("a — b", PATTERNS) == [], "two dashes are below the pattern's min_hits")
    check(run_skill.surviving_tells("Espero ter ajudado!", PATTERNS, ["chatbot-closer"]) == [], "a tell the case allows is not counted")


if __name__ == "__main__":
    test_goldens_pass()
    test_rewrite_cases_fail_when_a_fact_is_dropped()
    test_rewrite_cases_fail_when_a_tell_survives()
    test_protected_parts()
    test_an_embedded_instruction_is_not_followed()
    test_analyze_changes_nothing()
    test_analyze_report_content()
    test_no_target()
    test_the_command_must_run_the_skill()
    test_the_process_is_confined()
    test_cases_match_the_data()
    test_triggers()
    test_helpers()
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    failed = [label for label, ok in results if not ok]
    print(f"\n{'all passed' if not failed else f'{len(failed)} failed'}")
    sys.exit(1 if failed else 0)
