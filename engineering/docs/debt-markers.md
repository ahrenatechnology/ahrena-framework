---
id: debt-markers
type: doc
clade: engineering
subclade: quality
title: Why a deferral has to name a number
summary: Why the reference must be an issue number rather than something trackable, what the detector is handed and why the change is an input rather than an inference, why the diff it reads is pinned and parsed as a hostile input, the tangential-finding protocol that replaces the marker, and the two trees the framework's two marker rules govern.
references:
  - rules/debt-markers.md
  - docs/review-findings.md
  - docs/simplicity.md
---

# Why a deferral has to name a number

This is the companion to [`rules/debt-markers.md`](../rules/debt-markers.md). The rule states one condition and names what decides it; this carries the question the rule had to settle, the protocol the rule refuses to number, and what the detector is actually handed at the moment it runs.

The subject is small enough to state in a line and has exactly one interesting decision in it, which is the one the predecessor left implicit.

## The open question: a number, or something trackable

A marker is redeemed by a reference. The question is what counts as one.

**The weak answer is "a reference to something trackable".** It costs nothing, it offends nobody, and it is what a framework writes when it does not want to presume a tracker. It is also not a shape. A detector cannot decide it, so either the condition stops being decidable — which removes the one property that made this rule worth a gate, since almost nothing else in this subject is fully decidable — or the detector guesses, matching anything that looks like a link or a ticket key, and a detector that guesses is the detector `rules/kiss.md` already lost a condition to and the one `rules/duplication.md` refuses on the duplicate no script can see.

Worse, the weak answer degrades in use rather than in the gate. `# FIXME: see the migration doc` is a reference to something trackable by any reading, and it names nothing that can be closed, assigned or argued with. The failure the rule exists to prevent — debt with no owner — passes.

**The strong answer is an issue number, and it is what shipped.** `(#N)` immediately after the marker, `N` decimal with no leading zero. One spelling, decidable by a regular expression over a comment, and it names a thing that has a state and an assignee.

The objection to it is real and worth stating: it presumes an issue tracker, and this framework does not otherwise require one. Except that it nearly does. Condition 1 of [`../../contributing/rules/branch-naming.md`](../../contributing/rules/branch-naming.md) requires every branch name to carry an issue number, in the same spelling, and [`../../contributing/rules/commit-format.md`](../../contributing/rules/commit-format.md) governs the commits that land on it. A project that follows this framework's contribution flow already has numbered issues, and has already been asked for a number in a place far more visible than a comment. The marginal presumption is close to zero, and what it buys is the difference between a condition a script decides and a condition a script approximates.

**The cost lands on the project that has no numbered tracker**, and the rule says where it lands: that project excludes the path and writes down why, in the invocation, the way `rules/clean-code.md` and `rules/duplication.md` already ask for their own carve-outs. That is an honest refusal. A softer default that accepted any reference would let the same project pass while telling everyone else the gate means less than it says.

**The reference has to be immediately after the marker**, not anywhere on the line. `# FIXME the retry path is broken, see #3 for context` names a number and is still silent debt: issue 3 is context for the reader, not the owner of the deferral. Requiring adjacency costs an author nothing they were not already going to type and removes the one ambiguity the form has.

## What the detector is handed

The condition is prospective; the hook that decides it is not, on its own, and the gap is worth being explicit about because it is the thing most likely to be papered over.

`hooks/check-structure.py` is invoked with paths. It resolves them, walks directories for `*.py`, parses each file, and hands each check a parsed file. Nineteen of its twenty conditions want exactly that, because their subject is a file. This one's subject is a change, and nothing in a path, a file or a parse tree says which lines a change wrote. The hook cannot infer it, and a hook that tried — by file modification time, by walking history and guessing, by comparing against a cached previous run — would be wrong in a way nobody could predict from reading it.

So the change is an input. `--changed <spec>` hands the spec to `git diff --unified=0`, the hook reads the `+` side of every hunk header, and the marker condition is decided over those line numbers and no others. Four things follow that are worth naming.

**It works in both places it has to work.** `--changed --cached` is the staged diff, which is what a pre-commit hook holds; `--changed origin/main...HEAD` is a pull request's change, which is what CI holds. The same hook, the same flag, the same answer. The failure this avoids is a condition implemented as a CI-only step, where a local run silently passes and the author discovers the gate after pushing — the arrangement that teaches people the gate is somebody else's problem.

**The default is every line, not no lines.** With no `--changed`, the hook has no change and scopes the condition to everything it was handed. Defaulting the other way would be tidier for an adopting repository and would mean that any invocation that forgot the flag reported a clean tree, which is a gate that passes by seeing nothing. The repository's own workflow already carries that lesson in the comment explaining why it fetches full history rather than a shallow clone: an empty range is not a green gate, it is an unasked question.

**A diff is a hostile input, and the invocation is pinned because of it.** The output of `git diff` is not a fixed format: `color.diff` wraps every row in escape sequences, `diff.external` and `GIT_EXTERNAL_DIFF` replace the patch with whatever another program prints, a textconv filter rewrites the content, and `diff.noprefix` drops the `a/` and `b/` a naive reader chops off the front of the path. Each of those is an ordinary setting on somebody's machine, and every one of them ends with the condition scoped to nothing or scoped to the wrong file while the run exits 0. So the run pins colour off, external and textconv drivers off, both prefixes and the context width, and it pins them after the caller's spec because git lets a later flag win. The patch is then decoded leniently rather than strictly, because a diff carries whatever bytes the changed files carry and a strict decode ends the run in a traceback that CI reads as a finding.

**The parser does not trust the patch body either.** Under `--unified=0` an added line is rendered with a single `+`, so a source line whose own text begins `++ ` arrives as `+++ ` — indistinguishable, to a reader scanning for the next file header, from the real thing. A file carrying diff fixtures has such a line, and this hook's own test suite is one. Read as a header it re-points the scope at a path lifted out of somebody's source, which hides every later marker in the file that really changed and reports one in a file the change never opened. The answer is structural rather than a heuristic: a `+++ ` row counts only straight after the matching `--- ` row, and each hunk's body is consumed by the counts the header declares rather than scanned past. The path is then unquoted, because git C-quotes a name holding a double quote or a backslash whatever `core.quotePath` says, and a marker that hid behind a filename would be a marker the gate can never see.

The one remaining limit of the git route is stated rather than worked around. A file git does not report as changed is out of scope, so a file that has never been added is invisible under `--changed <rev>` — it is in scope under `--changed --cached` the moment it is staged, which is where a pre-commit hook meets it. That is a property of the input, not a judgment the detector is making.

## The tangential-finding protocol

The ban is the smaller half of this subject. A rule that only forbids a marker is a rule whose honest response is to write nothing, and a finding that is never written down is worse than a finding that is written down without a number: the first is lost, the second is merely untracked.

So the marker is not the thing being removed. The thing being removed is the moment where an author, mid-change, decides alone that something can wait. The protocol replaces that moment with a decision somebody made on purpose.

When work turns up something real and outside the change's declared scope:

1. **Stop.** Not at the end of the change — at the finding. The cost of the three options is different once the surrounding work has been written around the gap.
2. **State the finding**, with what it affects and what handling it now costs against what handling it later costs. This is a finding in the sense `docs/review-findings.md` defines: a file, a line, a condition and the state observed. An impression is not a finding and does not earn a pause.
3. **Offer three options, and only three.** Widen the current change, if the fix is small and sits inside the same scope. Open a separate issue under the same parent, if it is material but separable. Open a new parent issue, if it is a capability rather than a piece of one.
4. **Record which was chosen**, in the issue, before resuming.

Every branch leaves a number, and that is what closes the loop back to the rule: after the protocol has run, the marker either has an issue to name or is not needed, because the work was done.

**None of this is decided by a script, and no condition pretends otherwise.** The evidence that a finding was surfaced is a conversation; the evidence that a decision was recorded is an issue the gate would have to fetch. What a detector can see is a marker with no number, which is the shadow the missing protocol casts and not the protocol itself. The rule numbers the shadow and routes the rest here, to a reader.

The reader is the part this framework has not wired up yet. The review skills in this plugin and the agent that orchestrates them are where a protocol like this reaches an agent at the moment it is needed, and neither names this doc today. That is a gap, it is recorded here rather than in a marker, and it is the single most likely way this half of the rule quietly fails to exist.

## The marker set, and the fact that nobody measured it

`TODO`, `TBD`, `FIXME` and `XXX`. Four tokens, uppercase, closed.

They are the four [`../../foundation/rules/completeness.md`](../../foundation/rules/completeness.md) chose, taken unchanged. The predecessor's list was different — it added `follow-up`, `later` and `revisit` and did not include the second of the four — and the three it added are ordinary English. "Handled later" in a comment is a sentence, not a deferral, and a detector that rejects sentences is a detector people stop running. That is not a new argument; it is the argument the foundation's completeness rule already makes about a lowercase spelling, applied to the same problem one tree over.

**Neither list was measured.** The predecessor asserted its six and this framework asserts four. Nobody counted which tokens actually precede deferred work in a corpus, nobody knows the rate at which each of the four is a real deferral rather than a shout, and the honest version of the claim is that these four are conventional. The counter-evidence is easy to find and is in the rule's boundary section: `XXX` next to a hyphen is a masked identifier at least as often as it is a marker.

What the choice does buy is agreement. Before it, the framework was on course to ban four tokens in artifacts and seven in source, with three of them overlapping, which is two vocabularies for one idea and the sort of thing that turns into a support question.

## The two trees

The framework now has two rules about these four tokens and they do not say the same thing. That is correct, and it is only correct because they govern different trees.

| | `foundation/rules/completeness.md` | `rules/debt-markers.md` |
|---|---|---|
| **Governs** | the five artifact types' own text | a consumer's Python source |
| **Decided by** | `foundation/hooks/validate-artifacts.py` | `hooks/check-structure.py` |
| **A marker is** | always a failure | a failure unless it names an issue |
| **Scope** | the whole artifact corpus | the lines a change adds, when the run is scoped |

No file is judged by both, because the two detectors read disjoint sets: one reads artifact markdown, the other parses Python. The rules can therefore disagree about what a marker means without any file ever receiving two answers.

The reason they disagree is the difference between the two trees. An artifact is a finished statement — a rule, a doc, a skill — and a marker in one means it was shipped unfinished; no issue number repairs that, because the defect is the artifact, not the schedule. Source is where unfinished work legitimately lives, and the only question worth asking of a deferral there is whether anybody agreed to it.

**Both rules needed a sentence saying which tree they mean, and only one of them could be written here.** `rules/debt-markers.md` carries its own. The other belongs in `foundation/rules/completeness.md`, which this plugin does not own; until it is added, that rule bans four tokens without saying where, and a reader who meets it first will reasonably conclude the framework forbids `TODO(#172)` everywhere.

## Where this stops

**This doc does not say what to do with a backlog.** A repository adopting the condition with two hundred markers already in it has a migration, and the rule's answer — scope the run to the change — defers that migration indefinitely rather than planning it. Planning it is a piece of work with an owner, and turning the backlog into issues is the same protocol above run in bulk. Nothing here says when that should happen, because the answer depends on how much of the backlog is still true.

**It does not reach the marker that is not a marker.** A function that returns a constant with a comment explaining that the real table arrives later, a test skipped with a reason that names no issue, a configuration value set to a placeholder: each is deferred work, none carries a token, and neither the rule nor this doc detects any of them. The tokens are a convention, and a convention only catches the people following it.

**It does not argue the case for issue-driven development.** That the unit of deferred work is an issue is taken from the framework's contribution flow rather than defended here; [`../../contributing/docs/contribution-flow.md`](../../contributing/docs/contribution-flow.md) is where that argument lives, and this rule is downstream of it.
