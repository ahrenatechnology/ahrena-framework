---
name: reviewing-python
description: Use when a change under review edits Python (.py or .pyi) and the question is what a Python reader would catch that a language-agnostic pass does not - a mutable default argument, a swallowed exception, a late-binding closure, an unannotated surface, a type hole mypy would reject. Reads the routed files against this plugin's Python rules and the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: quality
references:
  - rules/typing.md
  - rules/module-boundaries.md
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md
---

# Reviewing Python

The language-agnostic pass in `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md` has already read the change against the rules that hold in any language, and `hooks/check-structure.py` has decided the mechanical conditions over the changed Python. This skill reads what is left: the defects that need a Python reader.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier. Severity and route follow `ahrena-engineering-quality:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `python` route on the changed `.py` and `.pyi` files. Those are the files this skill reads.

Before the checklists, read how this repository writes Python: its `pyproject.toml` for the Python version and the type-checker and linter configuration, its `AGENTS.md` and `CLAUDE.md`, and the layering its own `rules/module-boundaries.md` describes. A condition the project's own configuration already decides — a linter that bans bare `except`, a formatter that fixes a style — is not reported again. What a green check decided is settled.

## 2. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| any Python file | `references/correctness.md`, the conditions that hold for every change |
| a function signature, an annotation, a dataclass, a public callable | `references/types-and-contracts.md`, with `rules/typing.md` |
| an import, a package boundary, a module's public surface, an `__init__.py` | `references/idioms-and-structure.md`, with `rules/module-boundaries.md` |

A change that only edits a string or a comment inside one function opens `correctness.md` alone.

## 3. Read beyond the hunk

For each symbol the change touches, open the whole file and the callers the diff does not show. A mutable default is decided at the `def`, but whether it bites is decided where the function is called twice. An annotation is judged against what the function returns on every path, not only the edited one.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 4. Apply the routed conditions

Work condition by condition. For each candidate, give the scenario in Python terms: the input or the state, the value or the exception that results, and what it should have been. A condition whose answer depends on the project's intent, and which the repository does not settle, is a `question`.

Read each condition's `Exempt` line and drop what it excludes. Python has an idiom for nearly every one of these conditions that is correct on purpose.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-quality:docs/review-findings.md`, with the condition identifier where the rule and condition number go, and a correction that is an instruction: the line, what to replace, and with what.

Hand the set back to step 7 of `ahrena-engineering-quality:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Nesting depth, a function too long, a duplicated block, an abstraction with one consumer: those are `reviewing-diffs` and the fundamentals rules, and `hooks/check-structure.py` already decided the ones it can.

**The import graph of a distribution.** Whether a package's layers depend only downward and the graph is acyclic is `rules/module-boundaries.md` and its own hook, not a reading.

**Security of a Python change.** Untrusted input reaching a query or a command, a secret, a call to a model: that is the security disciplines (`reviewing-untrusted-input`, `reviewing-secrets`, `reviewing-sensitive-data`, `reviewing-model-use`), whose conditions carry those sinks.

**Another language.** A `.ts`, `.go` or `.rs` file in the same change is read by that language's skill.
