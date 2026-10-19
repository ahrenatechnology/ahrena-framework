---
id: comment-pointers
type: rule
clade: engineering
subclade: quality
title: A comment points, or it goes
statement: A comment a change adds or edits carries a pointer — an ADR or an issue — or is a permitted exemption; prose with no pointer is a finding the fix removes.
enforcement: hook
enforced-by: hooks/check-comments.py
references:
  - docs/comment-pointers.md
---

# A comment points, or it goes

A comment is the one line nothing checks. The compiler skips it, the tests never run it, and the next change moves the code beside it and leaves it where it was. So a comment that explains what the code does is decaying from the moment it is written, and the reader who trusts it stops reading the code. A comment that points somewhere durable — a decision record, an issue — does not decay, because the thing it points at is versioned, owned, and open to argument. This rule keeps the second and removes the first.

One condition, decided by [`hooks/check-comments.py`](../hooks/check-comments.py). Like every condition that script decides, it is a shape in the source rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. [`docs/comment-pointers.md`](../docs/comment-pointers.md) carries the provenance, the argument for an ADR or an issue rather than a URL, the full exemption set, and the two parts of the condition a reviewer still owns.

The fix for a finding here adds no structure — it removes a comment, or the author adds the pointer that redeems it — so the abstraction trigger declared in condition 1 of [`yagni.md`](yagni.md) does not gate it.

## The change, not the tree, and what that costs

The condition is prospective. It reaches a comment this change added or edited and no other, which is what lets a repository with a thousand existing prose comments adopt it on a Tuesday. A detector that fires on every comment already in the tree is a detector somebody switches off in a week, and a rule enforced by a gate people have switched off is not enforced.

**The hook cannot work out on its own which lines are new.** It is handed paths, and nothing in a path says which of a file's lines this change wrote. So the change is a second, explicit input: `hooks/check-comments.py --changed <spec>` hands the spec to a pinned `git diff` and decides the condition over the lines that diff adds. This is the same `--changed` machinery [`debt-markers.md`](debt-markers.md) uses, taken unchanged so that the two conditions scope the same way and a local run agrees with CI. `--changed --cached` is the staged diff a pre-commit hook has; `--changed origin/main...HEAD` is a pull request's own change. The spec is a revision or a range, and an option in its place — `--name-only`, `-U5` — is refused, because it would empty or widen the scope while the run still exited 0, which is the silent pass that rule names as the one failure mode worse than a noisy one.

**With no `--changed`, every comment is in scope.** That is the honest default and not the safe-looking one: a gate that defaults to seeing less than it was handed is a gate that passes by seeing nothing. The cost is that a first run on a repository with a backlog reports the backlog, and `--changed` is the answer, written in the hook's usage line.

## Five languages, delegation in Python and none outside it

The condition is decided for five languages — Python, TypeScript, JavaScript, shell and SQL — dispatched by file suffix. Only Python shares its comments with two other conditions in this plugin, and the three are written so that no Python comment is judged by two of them.

- [`clean-code.md`](clean-code.md) **condition 3 governs commented-out Python code**: a comment whose text parses as Python. That is a corpse of a program, and version control already keeps the version that ran.
- [`debt-markers.md`](debt-markers.md) **condition 1 governs the Python debt marker**: a `TODO`, `TBD`, `FIXME` or `XXX` that names no issue. That is work deferred with nobody accountable for it.
- **This rule governs what is left in Python**: a comment that is neither of those, carries alphabetic prose, and points at nothing durable.

**In Python the three partition the comment.** A comment that parses as code is delegated to clean-code and this rule does not touch it. A comment carrying an unquoted marker is delegated to debt-markers and this rule does not touch it. What reaches this condition is the comment the other two leave behind, so the three partition the Python comment rather than overlapping on it. The three share the same `#` comment scan and the same backtick escape — a pointer or a marker quoted in backticks is prose about pointers or markers, not one — taken from the same place for the same reason.

**Outside Python there is nothing to delegate to, so nothing is delegated.** `clean-code.md` and `debt-markers.md` are Python-only, so in TypeScript, JavaScript, shell and SQL this rule is the only one reading a comment. The pointer rule subsumes the bare debt marker there: a `// TODO` that names no issue carries no durable pointer and is no exemption, so it is this condition's finding directly rather than a second condition's, while `// TODO (#12)` carries the issue and passes. The result a reader wants is the same — a bare marker is reported — reached by the one pointer test rather than by a delegation, so there is still one condition and no double-judging. A comment that happens to parse as code in another language is prose to this rule like any other, because no commented-out-code condition reaches outside Python to own it.

## Conditions

Decided by [`hooks/check-comments.py`](../hooks/check-comments.py).

1. **A comment a change adds or edits points at an ADR or an issue, or is a permitted exemption.** The condition is decided for Python (`.py`, `.pyi`), TypeScript and JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`), shell (`.sh`, `.bash`) and SQL (`.sql`), each through a reader matched to its syntax. The pointer is `ADR-N`, with `N` a decimal ADR number that may carry leading zeros because this repository pads them (`ADR-001`, `ADR-014`, `ADR-0001`), or `#N`, an issue reference with `N` a decimal issue number and no leading zero — the same spelling condition 1 of [`branch-naming.md`](../../../contributing/rules/branch-naming.md) requires of every branch here. The comment need only contain a pointer, so a pointer followed by a brief single-line description is clean. A pointer quoted in backticks is prose about pointers and does not count. The exemptions are a shebang, a PEP 263 coding declaration, a license header (`SPDX-License-Identifier`, `Copyright`, `Licensed under`, `all rights reserved`, `(c)`), a separator with no alphabetic word, the documentation block directly above a TypeScript or JavaScript `export`, and a tool directive by prefix — the directive set is per language: the Python directives (`type:`, `noqa`, `pragma`, `pylint`, `mypy`, `ruff`, `fmt:`, `isort`, `nosec`, `pyright`, `flake8`, `yapf`, `black`, `coding`), the TypeScript and JavaScript directives (`eslint-`, `@ts-`, `prettier-ignore`, the webpack magic comments, `@__PURE__`, `@type`, `@license`, `@preserve`, and the rest), `shellcheck` for shell, and the migration-tool directives for SQL (`+goose`, `+migrate`, `migrate:`, `liquibase`, `changeset`, `sqlfluff:`, `noqa`). In Python only, a comment that parses as code is delegated to [`clean-code.md`](clean-code.md) condition 3, and a comment carrying an unquoted debt marker to [`debt-markers.md`](debt-markers.md) condition 1; neither is this condition's finding. Outside Python there is no such delegation, because those two rules are Python-only, so a bare debt marker there is simply pointerless prose this condition reports. Everything else is a finding, and `--fix` removes the comment. The condition is decided over the lines the run is scoped to: with `--changed <spec>` those are the lines that diff adds, and with no `--changed` they are every line of every file the run was handed.

## Where this stops

**Five languages, and comments only.** The detector reads Python, TypeScript, JavaScript, shell and SQL, each through a reader matched to its syntax: Python through the standard library's tokenizer, so a `#` inside a string is never a comment; TypeScript and JavaScript through a lexer that tracks strings, template literals and regular expressions; shell and SQL for their whole-line comments. Each reader is conservative in the same direction — where it cannot tell a comment from the data around it, it reports nothing for that file, because `--fix` deletes what is reported and a deleted piece of a string is a defect the hook would have written itself. A docstring is a string literal, not a comment, and it is out of scope by nature — it is the documented interface of the thing it opens, reached by tooling, and it does not rot the way an inline aside does. This is why the hook that enforces this rule carries all of its own rationale in docstrings. Prose in a language outside these five is read by a reviewer, the same boundary every condition `check-structure.py` and this hook decide already has.

**The pointer set is closed, and so is the exemption set.** Two pointers, `ADR-N` and `#N`, because they are the two references this framework version-controls or the forge owns; a URL points outside the repository at something nobody here controls, so it rots as silently as the prose it would replace and is refused. [`docs/comment-pointers.md`](../docs/comment-pointers.md) argues that refusal in full. The exemptions are the comments that are not explanatory prose at all — machinery, legal notices, directives to other tools, and visual separators — and each is asserted rather than measured, the way `debt-markers.md` asserts its marker list.

**A pointer redeems a comment whether or not it resolves.** `# ADR-9999` passes though no such record exists, and `# see #1` passes whether issue 1 is open, closed, or about something else. Resolving the reference means reaching a tracker the gate has no business calling, and a gate that made a network request is a gate people run without the network. What the condition buys is that somebody pointed at something durable; whether they pointed at the right thing is a reviewer's question, the same place `debt-markers.md` stops.

**The fix removes, it does not rewrite.** A full-line comment is deleted, line and all; an inline comment is stripped with the code kept; a block comment goes whole; and the fix is idempotent. It does not invent a pointer, because it cannot know which ADR or which issue the author meant — it removes the prose that was decaying and leaves the author to add the pointer if there was one to add. The review route runs the detector report-only; `--fix` belongs to the fixer agent Erodos and to a pre-commit hook, the separation `ADR-014` records, so that a reviewer never reads its own edit.

**Ambiguous is not a finding.** Where a comment could be read two ways, the delegations and the exemptions win: a comment that parses as code, carries a marker, contains a pointer, or is an exemption is never this condition's finding, so the rule never flags a comment another rule already owns or a comment that is not prose at all.

**It does not reach the stale comment or the restating comment.** A comment that describes behaviour the code no longer has, and a comment that repeats the line below it, are both defects and neither is caught here unless it also lacks a pointer. Staleness in particular is the expensive one, and nothing mechanical detects it; `docs/clean-code.md` carries what a reviewer asks about comment hygiene, and this rule adds one mechanical case to that judgment rather than replacing it.

**This rule declares a hook rather than judgment, and the cost is named here.** The condition is decided by a parser, so the script stands in for the rule and the rule contributes no text to any request — the cheapest route, and the reason to take it. What it drops is the material above: the URL argument, the staleness a reader catches, and the question of whether a pointer points at the right thing. Those live in `docs/comment-pointers.md`, which a reviewer reads and an agent loads when a finding needs arbitration.
