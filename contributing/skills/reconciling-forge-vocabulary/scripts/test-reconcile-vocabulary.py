#!/usr/bin/env python3
"""Tests for reconcile-vocabulary.py.

The script reaches the forge only through `gh`, so each run puts a fake `gh`
first on PATH. The fake answers from a table of routes, each a command prefix
and the answer it gives, and it logs every call. A run case executes the
script as a subprocess in a project directory of its own and asserts on the
exit code, the output, and the calls that were and were not made. No real
repository or organisation is read or written.

The parser is exercised directly, on texts that are in the subset and texts
that are not. The suite names #80's criteria beside the cases that cover them.

Usage:
    python3 contributing/skills/reconciling-forge-vocabulary/scripts/test-reconcile-vocabulary.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "reconcile-vocabulary.py"
REFERENCES = SCRIPT.parent.parent / "references"
REPO = "acme/widgets"
LABELS = f"api --paginate repos/{REPO}/labels"
TYPES = "api orgs/acme/issue-types"

FAKE_GH = """\
import json, os, sys
command = " ".join(sys.argv[1:])
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(command + "\\n")
with open(os.environ["FAKE_GH_ROUTES"], encoding="utf-8") as f:
    routes = json.load(f)
matches = [prefix for prefix in routes if command.startswith(prefix)]
if not matches:
    sys.stderr.write("fake gh: no route for " + command)
    sys.exit(1)
answer = routes[max(matches, key=len)]
sys.stdout.write(answer.get("out", ""))
sys.stderr.write(answer.get("err", ""))
sys.exit(answer.get("code", 0))
"""


def load_module():
    spec = importlib.util.spec_from_file_location("reconcile_vocabulary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def says(out: str = "", code: int = 0, err: str = "") -> dict:
    return {"out": out, "code": code, "err": err}


def labels(*items: tuple[str, str, str | None]) -> dict:
    """The forge's labels, one JSON object a line, as `--jq '.[] | ...'` prints them."""
    lines = [json.dumps({"name": n, "color": c, "description": d}) for n, c, d in items]
    return {LABELS: says("\n".join(lines) + "\n")}


def types(*items: dict) -> dict:
    return {TYPES: says(json.dumps(list(items)))}


def kind(number: int, name: str, color: str, description: str | None) -> dict:
    return {"id": number, "name": name, "color": color, "description": description, "is_enabled": True}


def disabled(held: dict) -> dict:
    return {**held, "is_enabled": False}


DENIED = {TYPES: says(code=1, err="gh: Must be an organization owner. (HTTP 403)")}
WRITES_OK = {"api -X POST": says("{}"), "api -X PATCH": says("{}")}
NO_TYPES_ROUTE = {TYPES: says("[]")}

PROJECT_LABELS = """\
# the project's own labels
- name: "status: todo"
  color: "ededed"
  description: "Not started"
- name: client-only
  color: 112233
"""

PROJECT_TYPES = """\
- name: Story
  color: green
  description: A behaviour a user can see
"""


def run_case(files: dict, routes: dict, args: list[str]) -> tuple[int, str, list[str]]:
    """Run the script in a project holding `files` with `routes` answering gh."""
    with tempfile.TemporaryDirectory() as tmp:
        root, bin_dir = Path(tmp) / "project", Path(tmp) / "bin"
        (root / ".github").mkdir(parents=True)
        bin_dir.mkdir()
        for name, text in files.items():
            (root / ".github" / name).write_text(text, encoding="utf-8")
        fake = bin_dir / "gh"
        fake.write_text(f"#!{sys.executable}\n{FAKE_GH}", encoding="utf-8")
        fake.chmod(0o755)
        (Path(tmp) / "routes.json").write_text(json.dumps(routes), encoding="utf-8")
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
               "FAKE_GH_ROUTES": str(Path(tmp) / "routes.json"), "FAKE_GH_LOG": str(Path(tmp) / "log")}
        result = subprocess.run([sys.executable, str(SCRIPT), REPO, "--root", str(root), *args],
                                capture_output=True, text=True, env=env)
        log = Path(tmp) / "log"
        calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result.returncode, result.stdout + result.stderr, calls


def case(name: str, given: tuple[dict, dict], args: list[str], expect: list[str], **checks) -> tuple:
    """`given` is the project's files and gh's routes. Among `checks`, `calls` must each start
    some gh call, `never` must be in none, `unsaid` must not be printed, and `code` is the exit."""
    files, routes = given
    return (name, files, routes, args, expect, list(checks.get("calls", ())), list(checks.get("never", ())),
            list(checks.get("unsaid", ())), checks.get("code", 0))


DEFAULT_LABEL_COUNT = len(MODULE.source(MODULE.LABELS, Path("/nonexistent")).items)

RUN_CASES = [
    # --- the defaults ship and are read when the project has none (#80/AC-1)
    case(
        "with no file in the project, both defaults are read and the status family is planned",
        ({},
         {**labels(), **types()}),
        [],
        ["labels: from labels.yml (Ahrena's default)", "issue types: from issue-types.yml (Ahrena's default)",
         "create  'status: todo'", "create  'status: development'", "create  'status: to review'",
         "create  'status: to release'", "create  'status: done'", "create  'blocked'",
         "create  'Epic'", f"{DEFAULT_LABEL_COUNT} declared"],
    ),
    # --- the project's file replaces the default, file by file (#80/AC-2)
    case(
        "a project labels.yml replaces the default labels, and the default issue types still apply",
        ({"labels.yml": PROJECT_LABELS},
         {**labels(), **types()}),
        [],
        ["labels: from .github/labels.yml", "create  'client-only'", "2 declared, 2 to create",
         "issue types: from issue-types.yml (Ahrena's default)", "create  'Task'"],
        unsaid=["'status: development'", "'size/XS'"],
    ),
    case(
        "a project issue-types.yml replaces the default issue types, and the default labels still apply",
        ({"issue-types.yml": PROJECT_TYPES},
         {**labels(), **types()}),
        [],
        ["labels: from labels.yml (Ahrena's default)", "issue types: from .github/issue-types.yml",
         "create  'Story'", "1 declared, 1 to create"],
        unsaid=["'Epic'", "'Task'"],
    ),
    # --- the dry run lists missing and differing, and writes nothing (#80/AC-3)
    case(
        "without --apply, missing and differing labels and types are listed and no write is made",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES + "- name: Bug\n  color: red\n  description: Broken\n"},
         {**labels(("Status: Todo", "EDEDED", "Not started"), ("client:acme", "000000", None)),
         **types(kind(1, "Story", "blue", "A behaviour a user can see"), kind(2, "Bug", "red", "Broken"))}),
        [],
        ["update  'status: todo'  name 'Status: Todo' -> 'status: todo'", "create  'client-only'  color 112233, ''",
         "update  'Story'  color blue -> green", "2 declared, 0 to create, 1 to update",
         "dry run: 3 change(s) listed, nothing written"],
        never=["-X POST", "-X PATCH", "-X DELETE", "-X PUT"],
        unsaid=["'Bug'", "client:acme"],
    ),
    case(
        "a description the forge lacks and a disabled issue type are both differences",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES},
         {**labels(("status: todo", "ededed", None), ("client-only", "112233", "")),
         **types(disabled(kind(1, "Story", "green", "A behaviour a user can see")))}),
        [],
        ["update  'status: todo'  description '' -> 'Not started'", "update  'Story'  disabled -> enabled",
         "dry run: 2 change(s) listed"],
        never=["-X "],
        unsaid=["'client-only'"],
    ),
    # --- --apply creates and updates, and deletes nothing (#80/AC-4)
    case(
        "with --apply the missing are created, the differing updated, and nothing is deleted",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES},
         {**labels(("Status: Todo", "cccccc", "Old"), ("client:acme", "000000", None)),
         **types(kind(7, "Story", "blue", "Old")), **WRITES_OK}),
        ["--apply"],
        ["created  'client-only'", "updated  'status: todo'", "updated  'Story'",
         "applied: 3 written, 0 failed, nothing deleted"],
        calls=[
            f"api -X PATCH repos/{REPO}/labels/Status%3A%20Todo -f new_name=status: todo -f color=ededed -f description=Not started",
            f"api -X POST repos/{REPO}/labels -f name=client-only -f color=112233 -f description=",
            "api -X PATCH orgs/acme/issue-types/7 -f name=Story -f description=A behaviour a user can see -F is_enabled=true -f color=green",
        ],
        never=["-X DELETE", "client:acme"],
    ),
    case(
        "with --apply and nothing to change, no write is made",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES},
         {**labels(("status: todo", "EDEDED", "Not started"), ("client-only", "112233", "")),
         **types(kind(1, "Story", "green", "A behaviour a user can see")), **WRITES_OK}),
        ["--apply"],
        ["0 to create, 0 to update", "applied: 0 written, 0 failed"],
        never=["-X "],
    ),
    case(
        "a label write the forge refuses fails the run, and the rest still go through",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES},
         {**labels(), **NO_TYPES_ROUTE, **WRITES_OK,
         f"api -X POST repos/{REPO}/labels -f name=client-only": says(code=1, err="gh: Validation Failed (HTTP 422)")}),
        ["--apply"],
        ["created  'status: todo'", "failed  'client-only'", "created  'Story'", "1 failed"],
        code=1,
    ),
    # --- issue types the token cannot read or write are reported, and labels go on (#80/AC-5)
    case(
        "issue types that cannot be read are reported, and the labels are still reconciled",
        ({"labels.yml": PROJECT_LABELS},
         {**labels(), **DENIED, **WRITES_OK}),
        ["--apply"],
        ["issue types: not reconciled, the token cannot read the issue types of acme", "HTTP 403",
         "created  'status: todo'", "created  'client-only'", "applied: 2 written, 0 failed"],
        calls=[f"api -X POST repos/{REPO}/labels -f name=status: todo"],
        never=["orgs/acme/issue-types -f", "-X POST orgs/"],
    ),
    case(
        "an owner with no organisation is reported the same way",
        ({"labels.yml": PROJECT_LABELS},
         {**labels(), TYPES: says(code=1, err="gh: Not Found (HTTP 404)")}),
        [],
        ["issue types: not reconciled", "HTTP 404", "labels: from .github/labels.yml", "dry run: 2 change(s)"],
    ),
    case(
        "issue types the token can read but not create are reported, and the run does not fail",
        ({"labels.yml": PROJECT_LABELS, "issue-types.yml": PROJECT_TYPES},
         {**labels(), **types(), **WRITES_OK,
         "api -X POST orgs/acme/issue-types": says(code=1, err="gh: Must be an organization owner. (HTTP 403)")}),
        ["--apply"],
        ["created  'status: todo'", "failed  'Story'", "1 issue type(s) need an admin of acme",
         "applied: 2 written, 0 failed"],
    ),
    # --- a file outside the subset is refused before the forge is asked (#80/AC-6)
    case(
        "a project file outside the subset is refused with its line, and gh is never called",
        ({"labels.yml": "- name: a\n  color: [1, 2]\n"},
         {**labels(), **types()}),
        ["--apply"],
        ["refused: .github/labels.yml:2: a flow sequence"],
        never=["api"],
        code=1,
    ),
]

GOOD = """\
---
# a comment line
- name: "status: todo"   # quoted, with a trailing comment
  color: 'ededed'
  description: It's plain text, with a#hash in it # and a trailing comment
- name: "quote \\" and backslash \\\\"
  color: 0E8A16

  description: 'it''s single-quoted'
"""

# Each text, the line it is refused on, and what the message must name. (#80/AC-6)
REFUSED = [
    ("- name: a\n  meta:\n    nested: x\n", 2, "has no value"),
    ("- name: a\n  meta: {x: 1}\n", 2, "a flow mapping"),
    ("- name: a\n  colors: [a, b]\n", 2, "a flow sequence"),
    ("- name: a\n  description: |\n    text\n", 2, "a block scalar"),
    ("- name: a\n  description: >\n", 2, "a block scalar"),
    ("- name: &anchor a\n", 1, "an anchor"),
    ("- name: *alias\n", 1, "an alias"),
    ("- name: !!str a\n", 1, "a tag"),
    ("name: a\ncolor: b\n", 1, "expected a list item"),
    ("- name: a\n  description: one\n    two\n", 3, "indented"),
    ("- name: a\n  description: one\ntwo\n", 3, "indented 0 spaces"),
    ("- name: a\n   color: b\n", 2, "indented 3 spaces"),
    ("- name: a\n  - b\n", 2, "a list inside an item"),
    ("- - name: a\n", 1, "a list inside an item"),
    ("-\n  name: a\n", 1, "an item with no field"),
    ("- name: a\n  name: b\n", 2, "given twice"),
    ('- name: "a\n', 1, "does not close"),
    ('- name: "a" b\n', 1, "text after a quoted value"),
    ('- name: "a\\q"\n', 1, "an escape"),
    ("- name: a: b\n", 1, "reads as a nested mapping"),
    ("- name: a\n\t color: b\n", 2, "a tab"),
    ("- ? name\n", 1, "not a `key: value` field"),
]

# Shapes the subset reads that the schema of a vocabulary refuses.
SCHEMA = [
    ("labels", "- name: a\n  color: 12345\n", "labels.yml:2: color '12345' is not six hex digits"),
    ("labels", "- name: a\n", "labels.yml:1: the label has no `color`"),
    ("labels", "- name: a\n  color: 111111\n  from_name: b\n", "labels.yml:3: `from_name` is not a field of a label"),
    ("labels", "- name: a\n  color: 111111\n- name: A\n  color: 222222\n", "labels.yml:3: label 'A' is declared twice, first on line 1"),
    ("types", "- name: Task\n  color: teal\n", "issue-types.yml:2: color 'teal' is not gray, blue"),
]


def check_parser() -> list[str]:
    failures: list[str] = []
    entries = MODULE.parse(GOOD, "good.yml")
    expected = [
        {"name": "status: todo", "color": "ededed", "description": "It's plain text, with a#hash in it"},
        {"name": 'quote " and backslash \\', "color": "0E8A16", "description": "it's single-quoted"},
    ]
    if [e.fields for e in entries] != expected:
        failures.append(f"the subset is read as {[e.fields for e in entries]}, expected {expected} (#80/AC-6)")
    for text, line, phrase in REFUSED:
        try:
            MODULE.parse(text, "bad.yml")
            failures.append(f"accepted {text!r}, expected a refusal on line {line} (#80/AC-6)")
        except MODULE.Refused as error:
            if not str(error).startswith(f"bad.yml:{line}: ") or phrase not in str(error):
                failures.append(f"{text!r} refused as {error!r}, expected line {line} and {phrase!r} (#80/AC-6)")
    return failures


def check_schema() -> list[str]:
    failures: list[str] = []
    for which, text, phrase in SCHEMA:
        kind_of = MODULE.LABELS if which == "labels" else MODULE.TYPES
        refusal = schema_refusal(kind_of, text)
        if phrase not in refusal:
            failures.append(f"{text!r} as {which} gave {refusal!r}, expected {phrase!r}")
    return failures


def schema_refusal(kind_of, text: str) -> str:
    """What reading `text` as the project's file of `kind_of` is refused with, or "accepted"."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".github").mkdir()
        (Path(tmp) / ".github" / kind_of.filename).write_text(text, encoding="utf-8")
        try:
            MODULE.source(kind_of, Path(tmp))
        except MODULE.Refused as error:
            return str(error)
    return "accepted"


def check_defaults() -> list[str]:
    """The shipped files are in the subset and carry the status family. (#80/AC-1)"""
    failures: list[str] = []
    for name in ("labels.yml", "issue-types.yml"):
        if not (REFERENCES / name).is_file():
            failures.append(f"references/{name} is not shipped (#80/AC-1)")
    names = {item.name for item in MODULE.source(MODULE.LABELS, Path("/nonexistent")).items}
    family = {"status: todo", "status: development", "status: to review", "status: to release", "status: done", "blocked"}
    if not family <= names:
        failures.append(f"the default labels lack {sorted(family - names)} (#80/AC-1)")
    if not MODULE.source(MODULE.TYPES, Path("/nonexistent")).items:
        failures.append("the default issue types are empty (#80/AC-1)")
    return failures


def check_run(spec: tuple) -> list[str]:
    name, files, routes, args, expect, calls, never, unsaid, code = spec
    status, output, made = run_case(files, routes, args)
    problems = [f"exit {status}, expected {code}"] if status != code else []
    problems += [f"output lacks {phrase!r}" for phrase in expect if phrase not in output]
    problems += [f"output has {phrase!r}" for phrase in unsaid if phrase in output]
    problems += [f"no call starting {c!r}" for c in calls if not any(m.startswith(c) for m in made)]
    problems += [f"a call holds {n!r}" for n in never if any(n in m for m in made)]
    if not problems:
        return []
    return [f"{name}\n    " + "\n    ".join(problems) + "\n    --- output\n" + output + "    --- calls\n    " + "\n    ".join(made)]


def main() -> int:
    failures = check_defaults() + check_parser() + check_schema()
    for spec in RUN_CASES:
        failures += check_run(spec)
    total = 3 + len(REFUSED) + len(SCHEMA) + len(RUN_CASES)
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{total} case(s), {len(failures)} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
