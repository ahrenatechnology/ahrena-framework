---
name: reviewing-diffs
description: Use when a pull request or a working diff needs reviewing against this plugin's rules. Routes the changed paths to the conditions that reach them; every finding names file, line and rule.
type: skill
clade: engineering
subclade: quality
references:
  - rules/yagni.md
  - rules/solid.md
  - rules/kiss.md
  - rules/clean-code.md
  - rules/duplication.md
  - rules/value-semantics.md
  - rules/pattern-selection.md
  - rules/domain-model.md
  - rules/aggregates.md
  - rules/cross-cutting-concerns.md
  - docs/patterns.md
  - docs/review-findings.md
  - skills/detecting-contract-breaks/SKILL.md
  - skills/publishing-review-verdicts/SKILL.md
---

# Reviewing diffs

A review is a set of findings, each naming a file, a line and the condition it violates. [`docs/review-findings.md`](../../docs/review-findings.md) defines the four severity levels and the test that assigns each; this procedure produces the findings those levels are applied to.

## 1. Fix the base, the head and whether anything may be executed

Three facts, recorded before any file is read, because every later step depends on one of them.

**The base.** The commit the change merges into, not the tip of the default branch. A diff taken against the wrong base reports every commit somebody else landed in between, and a review that does that is discarded whole.

**The head.** The exact commit under review. It names the review, it bounds what counts as "in the diff" for the severity test in step 7, and `skills/publishing-review-verdicts/SKILL.md` builds the comment marker from it.

**Whether execution is permitted.** It is permitted when the head is a branch in the same repository as the base. It is not permitted when the head is an external fork, because building the project runs the change author's code — the dependency manifest, the build script, an install hook and every transitive dependency they name — on this machine. When it is not permitted, record one `unchecked` finding naming each condition step 5 will not decide and this reason, and carry on. Every other step in this procedure only reads.

## 2. Sort the changed paths into routes

The eleven rules do not all reach every change, and reading all of them against every diff spends attention on conditions that cannot fire. Each changed path selects a set; a path can be in several.

| What the path is | Read against it |
|---|---|
| any source file, in any language | `rules/yagni.md`, `rules/solid.md`, `rules/kiss.md`, `rules/clean-code.md`, `rules/duplication.md`, `rules/value-semantics.md`, `rules/pattern-selection.md` |
| a `.py` file | the same set, with the mechanical conditions decided by the detector in step 3 instead of by reading |
| a module under a bounded context's `domain/` directory | add `rules/domain-model.md` and `rules/aggregates.md` |
| a module under `adapters/`, `infrastructure/` or `persistence/`, or any handler, client or job entry point | add `rules/cross-cutting-concerns.md` |
| a contract document, an event definition, a schema migration, or a module's exported surface | hand to `skills/detecting-contract-breaks/SKILL.md`, which needs the base version of the surface and not the diff |
| a new interface, abstract base, port, registry, generic parameter or configuration switch, anywhere | condition 1 of `rules/yagni.md`, and `docs/patterns.md` through `rules/pattern-selection.md` |

A path that matches nothing below the first row falls through to the language-agnostic set. That is the weaker route and the review says so rather than implying the file was covered.

## 3. Run the shipped detector over the changed Python files

```sh
python3 engineering/hooks/check-structure.py path/to/changed.py
```

It decides nineteen conditions across seven rules in one pass and prints each finding with its file, line and rule already attached, which is three of the four fields a finding owes. Pass it the changed files rather than the tree: a whole-tree run buries the change under pre-existing violations that belong to nobody in this review.

Two recurring failures at this step. The detector parses Python only, so a change in any other language gets nothing from it and the conditions it would have decided move to step 4 by reading. And a file the rules' boundary sections exclude by path — a generated parser table, a template directory, a fixture that commits and rolls back — will produce findings the rule itself says are not findings; step 6 is where they are removed, and removing them at step 3 by not running the detector loses the rest of the file.

## 4. Read the routed judgment conditions against the changed lines

What is left after step 3 is the conditions no parser decides: the counts across a tree, the boundaries a reader draws, and the arbitration.

Work condition by condition, not file by file. Take one condition, read its statement, and look for its state in the changed lines — the reverse order produces a reviewer who reads the diff once and reports whatever it happened to notice.

The conditions that carry the most in practice, and the state each is looking for:

- **`rules/yagni.md` condition 1.** An abstraction added by this change with no second consumer in the tree and no test that fails without the seam. Count consumers in the tree, not in the description of the change.
- **`rules/solid.md` conditions 4 to 6.** A third occurrence of one discriminator chain, an interface whose consumers use disjoint halves, an import crossing the layer map in the wrong direction.
- **`rules/domain-model.md` conditions 3 to 5.** An aggregate root with no identity or no audit stamp, the superseded spelling of the record's domain attribute, a client name or personal datum written in as a literal.
- **`rules/aggregates.md` conditions 1 to 6.** An invariant whose terms reach two roots, a use case writing two roots in one transaction, a field typed as another aggregate's root, a cross-boundary gap with no stated window, an event missing its root identity or its time.
- **`rules/cross-cutting-concerns.md` conditions 4 and 5.** A mutating published operation with no idempotency key, and the third inline copy of one concern.
- **`rules/pattern-selection.md` conditions 1 to 4.** A pattern whose situation clause in `docs/patterns.md` is absent from the tree, a cheaper alternative neither tried nor ruled out, a gated pattern with no second consumer, a pattern word used for a shape that is not that pattern.

## 5. Run the conditions that need a test, or record that you did not

Two conditions on these routes are decided by running something: condition 3 of `rules/solid.md` runs the supertype's own suite against the subtype, and condition 4 of `rules/cross-cutting-concerns.md` replays one request twice with one key and asserts a single effect. The contract surfaces add three more, and those belong to `skills/detecting-contract-breaks/SKILL.md`.

Run them only when step 1 permitted execution, and only with the command the project itself declares. When execution was not permitted, when no test command is discoverable, or when the suite does not build, the outcome is one `unchecked` finding naming each condition and the reason — never a blocking finding, because nothing was observed, and never silence, because silence reads as a pass.

## 6. Check each candidate against the rule's own boundary section

Every rule in this plugin ends with `Where this stops`, and those sections are not commentary. They name the states that match a condition and are correct anyway: a parser table that nests deeply on purpose, a saga that commits and rolls back at a boundary it owns, three tests that repeat a shape so each reads alone, a domain whose subject genuinely is HTTP, a value type whose eight fields belong together.

Read the boundary section of every rule you are about to cite, and drop the candidates it excludes. A reviewer who skips this reports the cases the rule's author already considered and refused, and the cost is not one wasted finding — it is the author learning that this reviewer's findings need checking, after which all of them do.

## 7. Assign a severity and write the finding

Apply the four tests in `docs/review-findings.md` in order: is the violated line inside this diff (**blocking**), outside it or is the fix outside it (**deferrable**), does deciding it need an input only the author holds (**question**), or was it never decided at all (**unchecked**).

Then write the finding with all four fields — file and line, rule and condition number, the state observed, and the change that resolves it. Drop anything you cannot give all four to. An impression with the reasoning missing is not a finding at a lower severity; it is a question, and it is written as one or not at all.

Hand the set to `skills/publishing-review-verdicts/SKILL.md`. Do not publish from here, and do not commit, push or edit the change at any point in this procedure.

## When this skill does not apply

**An artifact of this framework** — a rule, doc, skill, agent or command — is not source code and none of these eleven rules is about it. The foundation plugin carries the procedure for reviewing those, and it asks different questions.

**A Python distribution's import graph, namespace layout or module boundaries.** Those conditions live in the Python plugin and its own detector decides them.

**Whether the change is wanted.** This procedure decides whether the code satisfies the conditions, not whether the feature should exist, whether the approach is the right one, or whether the effort was worth it. Those are the reviewer's to raise as questions and the owner's to settle.

**A change with no diff to read.** A rename-only change, a merge commit, a vendored dependency bump and a generated file refresh have no authored lines, and running eleven rules over them produces noise. Say what the change is and stop.
