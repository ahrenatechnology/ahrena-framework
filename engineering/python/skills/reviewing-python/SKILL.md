---
name: reviewing-python
description: Use when a change under review edits Python (.py or .pyi) and the question is what a Python reader would catch that a language-agnostic pass does not - a mutable default argument, a swallowed exception, a late-binding closure, an unannotated surface, a type hole mypy would reject. Reads the routed files against this plugin's Python rules and the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: python
references:
  - rules/typing.md
  - rules/module-boundaries.md
  - rules/error-handling.md
  - rules/immutability.md
  - rules/testing.md
  - rules/security.md
  - rules/test-placement.md
  - docs/architecture.md
  - docs/logging-and-observability.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Python

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has already read the change against the rules that hold in any language, and `hooks/check-structure.py` has decided the mechanical conditions over the changed Python. This skill reads what is left: the defects that need a Python reader.

Seven rules in this plugin hold Python, and four hooks decide them:

| Rule | Decided by |
|---|---|
| `rules/typing.md` | `hooks/check-typing.py`, conditions 2 to 5; condition 1 is the project's `mypy --strict` |
| `rules/module-boundaries.md` | `hooks/check-boundaries.py` |
| `rules/error-handling.md` | `hooks/check-python.py` |
| `rules/immutability.md` | `hooks/check-python.py`, under `domain/` |
| `rules/testing.md` | `hooks/check-python.py` |
| `rules/security.md` | `hooks/check-python.py` |
| `rules/test-placement.md` | `hooks/check-test-placement.py` |

A hook's finding cites its rule and condition, as `[error-handling] condition 1`, and is reported as it is. What this skill adds is the reading the hooks cannot do.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `python` route on the changed `.py` and `.pyi` files. Those are the files this skill reads. When the skill runs on its own — called by the Python specialist, or by a writer on its own diff — there is no router and no language-agnostic pass before it: the files are the ones the diff changed, and the fundamentals structure hook runs below with the other four.

Before the checklists, read how this repository writes Python: its `pyproject.toml` for the Python version and the type-checker and linter configuration, its `AGENTS.md` and `CLAUDE.md`, and the layering its own `rules/module-boundaries.md` describes. A condition the project's own configuration already decides — a linter that bans bare `except`, a formatter that fixes a style — is not reported again. What a green check decided is settled.

Then run the four hooks over the changed files and keep their findings for step 5:

```sh
python3 <python-plugin>/hooks/check-typing.py <changed .py files>
python3 <python-plugin>/hooks/check-python.py <changed .py files>
python3 <python-plugin>/hooks/check-test-placement.py <changed .py files>
python3 <python-plugin>/hooks/check-boundaries.py <import roots>
```

The plugin directory is where `ahrena-engineering-python` is installed (`engineering/python` in the framework's repository); the import roots are the directories the project's dotted imports resolve against. Pass the changed files, not their directories: a directory brings in findings on lines the change did not touch. The boundaries hook reads the whole graph by nature, so a finding of it on a module the diff did not touch, or with no line, is deferrable, as `ahrena-engineering-quality:docs/review-findings.md` grades a finding outside the diff.

**One identifier per finding.** Where a hook's condition and a PY reading name the same line — a blind handler is condition 5 of `rules/typing.md` and PY-3; an unannotated parameter is condition 2 and PY-T6 — the finding cites the hook's condition, because a script decided it, and the PY reading adds only what the hook did not see.

A hook finding that a rule's own escape answers — a reason comment beside an `Any`, a mutable domain record or a `pickle.load` — is not reported. Whether the reason is true is read: a comment saying the bytes are trusted, on a function that loads an upload, is a finding of `reviewing-untrusted-input`, INP-7.

## 2. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| any Python file | `references/correctness.md`, the conditions that hold for every change |
| a function signature, an annotation, a dataclass, a public callable | `references/types-and-contracts.md`, with `rules/typing.md` |
| an import, a package boundary, a module's public surface, an `__init__.py` | `references/idioms-and-structure.md`, with `rules/module-boundaries.md` |
| an `except`, a `raise` or a `finally` | PY-3 in `references/correctness.md`, with `rules/error-handling.md` |
| a dataclass, or a function, under `domain/` | PY-T3 in `references/types-and-contracts.md`, with `rules/immutability.md` and `docs/architecture.md` |
| a test, a fixture or a `conftest.py` | `rules/testing.md`, and PY-10 in `references/correctness.md` for the doubles a reader sees and the hook does not |
| `eval`, `exec`, a deserialiser, a subprocess, an archive, a TLS setting | `rules/security.md`, then the security discipline its condition names |
| a log call, a `print`, a `raise`, an error handler, a response, a `__repr__` | PY-9 in `references/correctness.md`, with `docs/logging-and-observability.md` |
| a new module with a function or a class | `rules/test-placement.md`, decided by `hooks/check-test-placement.py` |

A change that only edits a string or a comment inside one function opens `correctness.md` alone.

## 3. Read beyond the hunk

For each symbol the change touches, open the whole file and the callers the diff does not show. A mutable default is decided at the `def`, but whether it bites is decided where the function is called twice. An annotation is judged against what the function returns on every path, not only the edited one.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 4. Apply the routed conditions

Work condition by condition. For each candidate, give the scenario in Python terms: the input or the state, the value or the exception that results, and what it should have been. A condition whose answer depends on the project's intent, and which the repository does not settle, is a `question`.

Read each condition's `Exempt` line and drop what it excludes. Python has an idiom for nearly every one of these conditions that is correct on purpose.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier where the rule and condition number go, and a correction that is an instruction: the line, what to replace, and with what.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` when that skill called this one; on its own, return it to the caller, with each condition not decided listed as `unchecked`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Nesting depth, a function too long, a duplicated block, an abstraction with one consumer: those are `reviewing-diffs` and the fundamentals rules, and `hooks/check-structure.py` already decided the ones it can.

**The import graph of a distribution.** Whether a package's layers depend only downward and the graph is acyclic is `rules/module-boundaries.md` and its own hook, not a reading.

**Security of a Python change.** Untrusted input reaching a query or a command, a secret, a call to a model: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`), whose conditions carry those sinks.

**Another language.** A `.ts`, `.go` or `.rs` file in the same change is read by that language's skill.
