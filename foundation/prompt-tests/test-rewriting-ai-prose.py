#!/usr/bin/env python3
"""Tests for the /humanize command and the triggers of the rewriting-ai-prose skill.

What a model does with a phrase is what `run-skill.py` measures, and needs a
credential. What a script can hold offline is held here: the command's shape,
and the trigger data against the skill's description, which is the text that
makes the skill load. A phrase the data expects to load the skill must be one
the description addresses, a typo or a missing accent must still point at the
phrase it varies, and every phrasing the issue names must be in the data, in
both languages, with the cases the skill leaves alone beside it.

Covers #365/AC-1, #365/AC-6 and #365/AC-8.

Usage:
    python3 foundation/prompt-tests/test-rewriting-ai-prose.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOUNDATION = HERE.parent
SKILL = FOUNDATION / "skills" / "rewriting-ai-prose" / "SKILL.md"
COMMAND = FOUNDATION / "commands" / "humanize.md"
TRIGGERS = json.loads((HERE / "rewriting-ai-prose" / "triggers.json").read_text(encoding="utf-8"))
CASES = json.loads((HERE / "rewriting-ai-prose" / "cases.json").read_text(encoding="utf-8"))

# #365 every phrasing the issue lists under What, as a person writes it.
WHAT = (
    "humaniza esse texto", "torna esse texto mais humano", "tira a cara de IA", "parece escrito por robô",
    "melhora a qualidade do texto dessa documentação", "melhora a redação", "deixa o texto melhor",
    "simplifica o texto", "deixa mais simples", "deixa mais claro", "deixa mais direto",
    "torna esse texto mais palatável para humanos", "deixa mais fácil de ler", "mais natural",
    "menos corporativo", "menos robótico", "revisa o texto do README",
)
FORMS = ("canonical", "typo", "no-accents", "imperative", "question")
PASTED_ONLY_FORMS = ("file", "pr", "message")
CATEGORIES = ("translate", "summarize", "review-code", "code-comment")
# Words every phrase shares, which say nothing about what is asked.
COMMON = {"this", "that", "make", "text", "with", "mais", "para", "esse", "essa", "texto", "deixa", "torna", "you", "can", "could", "the"}

results: list[tuple[str, bool]] = []


def check(ok: bool, label: str) -> None:
    results.append((label, ok))


def fold(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in plain if unicodedata.category(c) != "Mn")


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    block = text.split("\n---\n", 1)[0].removeprefix("---\n")
    fields: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"^([a-z-]+):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"')
    return fields


def body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("\n---\n", 2)[-1]


def words(text: str) -> set[str]:
    return {w[:4] for w in re.findall(r"[a-z]{4,}", fold(text)) if w not in COMMON}


def test_skill_passes_the_gate() -> None:
    """#365/AC-1: the skill exists and the foundation gate, run over the whole corpus, finds nothing."""
    check(SKILL.is_file(), "the skill's SKILL.md exists")
    gate = FOUNDATION / "hooks" / "validate-artifacts.py"
    done = subprocess.run([sys.executable, "-B", str(gate), str(FOUNDATION.parent)], capture_output=True, text=True)
    check(done.returncode == 0 and "no failures" in done.stdout, "the foundation gate passes over the corpus, the skill and the command with it")


def test_command_shape() -> None:
    """#365/AC-6: the command takes a mode and a target and runs the skill."""
    meta, text = frontmatter(COMMAND), body(COMMAND)
    check(meta.get("name") == "humanize" and COMMAND.stem == "humanize", "the command is named humanize, as its file")
    check(meta.get("type") == "command" and meta.get("clade") == "foundation", "the command is a foundation command")
    check("analyze" in meta.get("argument-hint", "") and "rewrite" in meta.get("argument-hint", ""), "the argument hint names both modes")
    check(meta.get("description", "").strip() != "", "the command has a description")
    check((FOUNDATION / "skills" / "rewriting-ai-prose" / "SKILL.md").is_file(), "the skill the command runs exists")
    check("skills/rewriting-ai-prose/SKILL.md" in meta.get("references", "") or "skills/rewriting-ai-prose/SKILL.md" in COMMAND.read_text(encoding="utf-8").split("---")[1],
          "the command references the skill and nothing else")
    check(re.search(r"^Invoke `rewriting-ai-prose`", text, re.M) is not None, "the command invokes rewriting-ai-prose")
    rows = {m.group(1): m.group(0) for m in re.finditer(r"^\| `(\w+)` \|.*$", text, re.M)}
    check(set(rows) == {"mode", "target"}, "the command takes a mode and a target and no more")
    check("analyze" in rows.get("mode", "") and "rewrite" in rows.get("mode", "") and "Defaults to `rewrite`" in rows.get("mode", ""), "the mode is analyze or rewrite and defaults to rewrite")
    check("changes nothing" in rows.get("mode", ""), "the command says analyze changes nothing")
    check("asks for one" in rows.get("target", ""), "with no target the command says it asks for one")
    check(len(text.splitlines()) < 40, "the command holds no logic of its own")


def test_command_cases() -> None:
    """The command's cases call it by the name the file has, with one of its modes or none."""
    prompts = [c["prompt"] for c in CASES["cases"]]
    check(all(p.startswith("/humanize") for p in prompts), "every case runs the command")
    modes = {re.match(r"/humanize(?: (analyze|rewrite))?", p).group(1) for p in prompts}
    check(modes == {None, "analyze", "rewrite"}, "the cases run the default mode, analyze and rewrite")
    check({"/humanize", "/humanize analyze"} <= set(prompts), "the cases run the command with no target, with and without a mode")


def test_triggers_shape() -> None:
    positives, negatives = TRIGGERS["positives"], TRIGGERS["negatives"]
    ids = [e["id"] for e in positives + negatives]
    check(len(ids) == len(set(ids)), "every phrase has its own id")
    check(set(TRIGGERS["samples"]) >= {e["attach"] for e in positives + negatives}, "every attachment is a sample the file defines")
    check(TRIGGERS["skill"] == "ahrena-foundation:rewriting-ai-prose", "the triggers name the skill under test")
    check({"foundation"} <= set(TRIGGERS["plugins"]), "the skill's own plugin is loaded")
    check(all(set(e) >= {"id", "phrase", "lang", "form", "covers", "attach"} for e in positives), "every positive has its fields")
    check(all(set(e) >= {"id", "phrase", "lang", "category", "attach"} for e in negatives), "every negative has its fields")
    check(all(e["lang"] in ("pt", "en") for e in positives + negatives), "every phrase is pt or en")


def test_no_phrase_names_the_skill() -> None:
    """#365/AC-8: with no command and no skill named."""
    for entry in TRIGGERS["positives"] + TRIGGERS["negatives"]:
        phrase = entry["phrase"].lower()
        check(not phrase.startswith("/") and "rewriting-ai-prose" not in phrase and "skill" not in phrase,
              f"{entry['id']}: the phrase names no command and no skill")


def test_what_is_covered() -> None:
    """#365/AC-8: every phrasing under What is a positive, and the variants a person could write follow."""
    phrases = {fold(e["phrase"]) for e in TRIGGERS["positives"]}
    for phrase in WHAT:
        check(fold(phrase) in phrases, f"What: {phrase!r} is a positive")
    positives = TRIGGERS["positives"]
    for lang in ("pt", "en"):
        check(sum(e["lang"] == lang for e in positives) >= 10, f"at least ten {lang} positives")
        for form in (f for f in FORMS if not (lang == "en" and f == "no-accents")):
            check(sum(e["lang"] == lang and e["form"] == form for e in positives) >= 2, f"at least two {lang} positives are of form {form}")
    for form in PASTED_ONLY_FORMS:
        check(any(e["form"] == form for e in positives), f"a positive is aimed at a {form}")


def test_negatives_cover_what_is_left_alone() -> None:
    negatives = TRIGGERS["negatives"]
    for category in CATEGORIES:
        mine = [e for e in negatives if e["category"] == category]
        check(len(mine) >= 2, f"at least two negatives are {category}")
        check({e["lang"] for e in mine} == {"pt", "en"} or category == "code-comment", f"the {category} negatives are in both languages")
    check({e["category"] for e in negatives} <= set(CATEGORIES), "every negative is of a known category")
    check(any(e["attach"] == "code" for e in negatives), "a negative carries code")


def test_description_addresses_each_positive() -> None:
    """#365/AC-8: the description is what decides, so each positive is one it addresses."""
    description = fold(frontmatter(SKILL)["description"])
    for entry in TRIGGERS["positives"]:
        covers = fold(entry["covers"])
        check(covers in description, f"{entry['id']}: the description holds {entry['covers']!r}")
        if entry.get("via") == "translation":
            check(entry["lang"] == "en", f"{entry['id']}: only an English phrase relies on the description's Portuguese")
        else:
            check(bool(words(entry["covers"]) & words(entry["phrase"])), f"{entry['id']}: the phrase points at what it covers")
    quoted = {fold(q) for q in re.findall(r'"([^"]+)"', frontmatter(SKILL)["description"])}
    check(len(quoted) >= 12, "the description quotes at least twelve phrasings")
    for entry in TRIGGERS["negatives"]:
        check(fold(entry["phrase"]) not in description, f"{entry['id']}: the description does not hold a phrase it must stay out of")
    for needle in ("translat", "summar", "review", "comment"):
        check(needle in description.split("not for", 1)[-1], f"the description leaves out what {needle!r} names")


if __name__ == "__main__":
    test_skill_passes_the_gate()
    test_command_shape()
    test_command_cases()
    test_triggers_shape()
    test_no_phrase_names_the_skill()
    test_what_is_covered()
    test_negatives_cover_what_is_left_alone()
    test_description_addresses_each_positive()
    for label, ok in results:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
    failed = [label for label, ok in results if not ok]
    print(f"\n{'all passed' if not failed else f'{len(failed)} failed'}")
    sys.exit(1 if failed else 0)
