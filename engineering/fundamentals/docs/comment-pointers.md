---
id: comment-pointers
type: doc
clade: engineering
subclade: quality
title: The comment that points, and the prose that rots
summary: Where the comment-pointer condition came from, why a pointer is an ADR or an issue and not a URL, the exemption set and its rationale, why the fix removes the comment and the review runs it report-only, and why it reads Python comments only.
references:
  - rules/comment-pointers.md
---

# The comment that points, and the prose that rots

This is the companion to [`rules/comment-pointers.md`](../rules/comment-pointers.md). The rule states one condition and names what decides it; this says what the condition is protecting, where it came from, which comments it deliberately lets through, and the two parts of it a script does not reach.

A comment is the one line in a source file that nothing checks. The compiler ignores it, the tests never exercise it, and the next change moves the code it sits beside without moving the comment. So a comment that explains what the code does starts decaying the moment it is written, and the reader who trusts it is reading a description of a program that no longer exists. A comment that points somewhere durable does not decay, because the thing it points at — a decision record, an issue — is versioned and owned and can be argued with. This rule is the line between the two.

## Provenance

The condition is part 3 of Barte's `check-comments.py`, generalised into this framework. That detector decided three things about a comment a change touched: whether it was commented-out code, whether it was a debt marker with no issue, and whether it was explanatory prose with no durable pointer. The first two already live here — [`rules/clean-code.md`](../rules/clean-code.md) condition 3 owns commented-out code and [`rules/debt-markers.md`](../rules/debt-markers.md) owns a `TODO`, `TBD`, `FIXME` or `XXX` that names no issue — so only the third was missing. This rule is that third part, and once it ships Barte consumes the rule rather than carrying its own copy, which is the whole point of porting it: one decision, enforced in one place, read by every repository that installs the plugin.

## Why a pointer is an ADR or an issue, and not a URL

A pointer is worth more than prose only when it is durable, and durability is the whole test. An ADR number names a decision record that lives in the repository, moves with it, and records the alternatives that were refused. An issue number names a unit of work on the forge, with its own discussion and its own close. Both outlive every refactor that passes the comment, and both are things a reader can reach and argue with.

A URL is not. It points outside the repository at something nobody here controls: a wiki page that gets reorganised, a ticket in a tracker the team has since left, a gist that is deleted. It rots exactly the way the prose it was meant to replace rots, and it rots silently, because nothing in the checkout can tell that the far end is gone. So the rule takes the two pointers that are version-controlled or forge-owned and refuses the one that is neither. This is the same reasoning [`rules/debt-markers.md`](../rules/debt-markers.md) uses when it requires `(#N)` rather than "something trackable": the value is not that a reference exists, it is that the reference resolves to something that will still be there.

The two pointers are spelled the way this repository already spells them. An ADR number is zero-padded — `ADR-001`, `ADR-014`, `ADR-0001` — so the pattern allows a leading zero. An issue number is not padded anywhere in this framework; condition 1 of [`rules/debt-markers.md`](../rules/debt-markers.md) and `branch-naming.md` both require `#N` with no leading zero, and this rule matches that spelling so the framework says one thing about what an issue number looks like.

**A pointer may carry a brief description, because the exemption is that the comment contains a pointer, not that it is only one.** `# ADR-0001 switch to the bank-specific fee table` is clean: the ADR reference is present, and the short line describing the decision is prose that will not rot, because the pointer beside it is where the reader goes when the prose and the code disagree. A reader who wants the full argument follows the pointer; a reader skimming gets a sentence. What the rule refuses is the sentence with nothing behind it.

## The exemption set, and why each is in it

A comment is exempt when it is one of a closed set of comments that are not explanatory prose at all. Each is here because flagging it would be wrong, not because it is tedious to flag.

- **A shebang** (`#!/usr/bin/env python3`) is an instruction to the loader, not a comment to a reader. It parses as a comment only because `#` is the comment character.
- **A PEP 263 coding declaration** (`# -*- coding: utf-8 -*-`, `# coding: utf-8`) is read by the interpreter to decode the file. It is machinery wearing a comment's syntax.
- **A license header** — a line carrying `SPDX-License-Identifier`, `Copyright`, `Licensed under`, `all rights reserved` or `(c)` — is a legal notice the file is required to carry. It does not describe the code and it does not rot.
- **A tool directive** — `type:`, `noqa`, `pragma`, `pylint`, `mypy`, `ruff`, `fmt:`, `isort`, `nosec`, `pyright`, `flake8`, `yapf`, `black`, `coding` — is an instruction to another tool, matched by prefix. This is the same carve-out [`rules/clean-code.md`](../rules/clean-code.md) condition 3 makes, and for the same reason: `# type: ignore` is not prose.
- **A separator with no alphabetic word** (`# ----------`, `# ==========`) is visual structure, not a sentence. It has nothing to rot, because it says nothing. This is why the dividers in this rule's own hook are written without words: a divider carrying words would be a finding against the rule it enforces.

The set is closed and asserted rather than measured, the same way [`rules/debt-markers.md`](../rules/debt-markers.md) asserts its marker list. A comment that is none of these and carries alphabetic prose with no pointer is what is left, and that is the finding.

## Why the fix removes the comment, and why review runs it report-only

The fix for a finding is to remove the comment, and the removal is reproducible. A full-line comment — one with only whitespace before the `#` — is deleted outright, line and all. An inline comment — code, then a `#` — is stripped from the `#` to the end of the line, the trailing whitespace is dropped, and the code is kept. Running the fix twice changes nothing the second time, because the first run already removed everything the condition flags.

Removing a comment is the honest fix, not a lossy one. The prose was decaying; deleting it loses a description that was already drifting out of true, and if the information mattered it belonged in an ADR or an issue, which is exactly what the rule asked for. The fix does not invent a pointer, because it cannot know which ADR or which issue the author meant. It removes the rot and leaves the author to add the pointer if there was ever one to add.

The fix is not applied by the reviewer. Argos runs the detector without `--fix` and reports the finding; Erodos, the fixer agent, applies `--fix` in a separate run, and Argos then reviews that run as it reviews any commit. This is the separation [`ADR-014`](../../../docs/adr/ADR-014-a-separate-agent-applies-the-fixes.md) records — the party that fixes is never the party that reviews, so a reviewer never reads its own edit — and this rule inherits it unchanged. A pre-commit hook is the other place `--fix` belongs, where the author applies it to their own change before it is ever reviewed.

## Boundary cases

**It reads Python, and it reads comments.** The detector tokenises Python and looks at `#` comments. A docstring is a string literal, not a comment, and it is out of scope by nature: a docstring is the documented interface of the thing it opens, it is reached by `help()` and by tooling, and it does not rot the way an inline aside does. The rule's own hook puts all of its rationale in docstrings for exactly this reason. Prose in any other language's comments is read by a reviewer, because the standard library ships one parser and this plugin takes no dependency.

**It is change-scoped, and the default is honest.** The condition reaches a comment this change added or edited, so a repository with a thousand existing prose comments adopts it without a thousand findings. Run with no `--changed`, it reads every comment it is handed, which over-reports on a backlog and is the right default anyway: a gate that defaults to seeing less than it was given is a gate that passes by seeing nothing. [`rules/debt-markers.md`](../rules/debt-markers.md) makes this argument in full and this rule takes the same `--changed` machinery, so a local run and a CI run decide the same thing.

**Ambiguous is not a finding.** A comment that parses as code is delegated to [`rules/clean-code.md`](../rules/clean-code.md) condition 3; a comment carrying an unquoted marker is delegated to [`rules/debt-markers.md`](../rules/debt-markers.md); a comment that contains a pointer is clean; a comment that is an exemption is clean. What is left — alphabetic prose, no pointer, no delegation, no exemption — is the finding, and when a comment could be read two ways the delegations and the exemptions win, so the rule never flags a comment another rule already owns.

## Where this stops

**It does not judge whether the prose was true.** A comment with a pointer passes whether the pointer is the right one, whether the ADR was superseded, or whether the issue is closed. Resolving the reference means reaching a tracker the gate has no business calling, and the value the condition buys is that somebody pointed at something durable, not that they pointed at the correct thing. That last question is a reviewer's, the same place [`rules/debt-markers.md`](../rules/debt-markers.md) stops with its own references.

**It does not reach the stale comment or the restating comment.** A comment that describes behaviour the code no longer has, and a comment that repeats the line below it in English, are both defects and neither is caught here: the first is reached only when it also lacks a pointer, and the second is prose a reviewer removes. [`docs/clean-code.md`](clean-code.md) carries what a reviewer asks about comment hygiene beyond the one mechanical case, and this rule adds one mechanical case to it rather than replacing that judgment.

**It does not decide where a comment should have been a name.** A comment introducing a block inside a function is marking a section, and a section is a function; extracting it is the fix. That is a judgment about structure, not about pointers, and it stays with the reviewer.
