---
id: debt-markers
type: rule
clade: engineering
subclade: quality
title: Debt that names its issue
statement: A debt marker a change adds or edits names the issue that owns it; a finding with no issue is surfaced and decided, not left in a comment.
enforcement: hook
enforced-by: hooks/check-structure.py
references:
  - docs/debt-markers.md
---

# Debt that names its issue

A marker left in source records that something was deferred. A marker that names an issue also records who deferred it, what for, and where the decision can be argued with. That difference is the whole rule: the first is debt nobody agreed to, and the person who pays for it is whoever finds it, months later, with no way to tell whether it still matters.

One condition, decided by `hooks/check-structure.py`. Like every other condition that script decides, it is a shape in the source rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. [`docs/debt-markers.md`](../docs/debt-markers.md) carries the argument for an issue number rather than something weaker, the protocol that replaces the marker, and the measurements behind both.

The fix for a finding here adds no structure — it opens an issue and names it, does the work now, or deletes the marker — so the abstraction trigger declared in condition 1 of `rules/yagni.md` does not gate it.

## The change, not the tree, and what that costs

The condition is prospective. It reaches a marker this change added or modified and no other, which is what lets a repository with two hundred existing markers adopt it on a Tuesday. A detector that fires on every marker already in the tree is a detector somebody switches off in a week, and a rule enforced by a gate people have switched off is not enforced.

**The hook cannot work out on its own which lines are new.** It is handed paths. A path names a file, a file has lines, and nothing in either says which of them this change wrote. So the change is a second, explicit input rather than something inferred: `hooks/check-structure.py --changed <spec>` passes the spec through to `git diff --unified=0` and decides the condition over the lines that diff adds. `--changed --cached` is the staged diff, which is what a pre-commit hook has; `--changed origin/main...HEAD` is a pull request's own change. It is one argument in the same command line either way, so the local run and the CI run are the same run rather than two gates that can disagree.

Consulting git for this is the same move [`../../contributing/rules/branch-naming.md`](../../contributing/rules/branch-naming.md) and [`../../contributing/rules/commit-format.md`](../../contributing/rules/commit-format.md) already make, and for the same reason: git is the subject here, not a dependency. A branch name does not exist without git and neither does a change.

**With no `--changed`, every line is in scope.** That is the honest default and not the safe-looking one. A gate that defaults to seeing less than it was handed is a gate that passes by seeing nothing, which is the failure the repository's own workflow already records in the comment explaining why it fetches full history. The cost is that a first run on a repository with a backlog reports the backlog; `--changed` is the answer to that, and it is written in the hook's usage line rather than left to be discovered.

## Two rules, four tokens, and the tree each one governs

[`../../foundation/rules/completeness.md`](../../foundation/rules/completeness.md) bans the same four tokens, and it is right to: an artifact carrying an unfilled marker is an artifact that is not finished, and no reference redeems it. This rule permits `# TODO(#172): switch to the bank-specific fee table once the spec arrives`, because source is where work in progress lives and a deferral that names its issue is a decision somebody made rather than one nobody did.

**The two govern different trees, and this is the sentence that says so on this side.** This rule reaches a consumer's source. That rule reaches the five artifact types' own text. No file is judged by both: `foundation/hooks/validate-artifacts.py` reads artifact markdown and `hooks/check-structure.py` parses Python, and neither reads what the other reads. The other sentence belongs in that rule and is not this rule's to write.

What the two do share is the token set and the escape. The four markers here are the four there, taken unchanged so that the framework cannot say two things about which tokens are markers, and a marker quoted in backticks is prose about markers in both — the same backtick, bought for the same reason, in a comment instead of a line of prose.

## The half no script decides

A rule that only forbids a marker gets the response it deserves, which is that the author writes nothing at all and the finding is lost rather than merely untracked. That is worse, and it is why the predecessor paired the ban with a protocol: when work turns up something real and out of scope, the author pauses, presents the finding with its cost now against its cost later, offers the three options — widen this change, open a separate issue under the same parent, open a new parent — and records which one was chosen before resuming.

**That half is routed to [`docs/debt-markers.md`](../docs/debt-markers.md) and no condition here decides it.** Nothing mechanical can tell a finding that was surfaced and declined from one that was never mentioned; the evidence is a conversation, and the artifact that reads a conversation is a reviewer or an agent. Numbering it as a condition of a hook rule would put an undecidable state next to a decided one under the same heading, which is the defect this plugin's rules are written to avoid.

## Conditions

Decided by `hooks/check-structure.py`.

1. **A debt marker names the issue that owns it.** The markers are `TODO`, `TBD`, `FIXME` and `XXX`, uppercase, matched as whole words in a Python comment. A marker is redeemed by an issue reference written immediately after it, as `(#N)` with `N` a decimal issue number with no leading zero — the same spelling of an issue number that condition 1 of [`../../contributing/rules/branch-naming.md`](../../contributing/rules/branch-naming.md) already requires of every branch in this framework. A marker quoted in backticks is prose about markers and is not a marker. The condition is decided over the lines the run is scoped to: with `--changed <spec>` those are the lines that diff adds, and with no `--changed` they are every line of every file the run was handed.

## Where this stops

**The scoping is the caller's, and the hook says so rather than guessing.** Run without `--changed`, the condition reads the tree and reports every unreferenced marker in it, which is the retrospective answer to a prospective question. Nothing in the hook can close that gap, because nothing it is handed carries the change. What it can do, and does, is refuse to guess: `--changed` with no revision, or in a directory git cannot answer for, exits non-zero with the reason instead of reporting a clean tree. A gate that silently degrades to seeing nothing is the one failure mode worse than a noisy one.

**The marker list is closed, and it is asserted rather than measured.** Four tokens, uppercase, because they are conventional and unambiguous in that spelling. The predecessor added `follow-up`, `later` and `revisit`; those three are ordinary English words, a comment saying a value is computed later is not a deferral, and a detector that rejects prose is the detector that gets switched off. That is the same argument [`../../foundation/rules/completeness.md`](../../foundation/rules/completeness.md) makes about a lowercase spelling of the first token, and taking its list whole is what makes the two rules agree. Nobody has measured which tokens actually carry deferred work; the claim here is convention, and it is stated as one.

**Comments only, and Python only.** A marker in a docstring, in a string literal, in a Markdown file that is not an artifact, or in any other language is invisible to this condition. The string carve-out is not squeamishness: the detector's own list of marker words is a string, so a detector that read strings would be a finding against itself, and so would every test that pins it. The predecessor's documentation half — an `## Out of scope (to revisit)` heading in a Markdown file — is dropped here for the flat reason that this hook parses Python, which is the same boundary every other condition it decides already has.

**Presence, not substance.** `TODO(#1)` passes whether issue 1 is open, closed, about something else, or never existed. Resolving the reference means reaching a tracker the gate has no business calling, and a gate that made a network request would be a gate people run without the network. What the condition buys is that somebody was made to open an issue before writing the marker; whether the issue is the right one is a reviewer's question, and it is the same place `../../foundation/rules/completeness.md` stops with its own fields.

**A marker adjacent to punctuation is a false positive.** `XXX-1234` in a comment describing a masked identifier matches, because the boundary test is a character class and a hyphen is outside it. The escape is a backtick or a rewording, which costs an author a keystroke and buys a detector with no judgment in it — the same trade, stated in the same terms, that the angle-bracket condition in the foundation's completeness rule makes.

**A repository with no issue tracker cannot satisfy this condition.** Requiring `(#N)` presumes numbered issues. That presumption is smaller than it looks in this framework, where every branch name already carries an issue number, but it is real, and a project that tracks work somewhere unnumbered has no spelling available to it. The route is the one `rules/clean-code.md` and `rules/duplication.md` already name for their own carve-outs: exclude by path, in the invocation where it is visible, and write down why. `docs/debt-markers.md` argues why the weaker alternative — a reference to "something trackable" — was refused rather than shipped as a softer default.

**Nothing here decides the protocol.** The three options, the pause and the recorded decision are in `docs/debt-markers.md`, and no script checks that any of them happened. An author who deletes the marker and says nothing passes this gate and has lost the finding, which is the failure the protocol exists to prevent and which only a reader catches.

**This rule declares a hook rather than judgment, and the cost is the protocol.** The condition is decided by a parser, so the script stands in for the rule and the rule contributes no text to any request — the cheapest route, and the reason to take it. What that drops is exactly the half above: a hook rule's statement is not injected, so the protocol never reaches an agent through this rule and has to reach it through the artifact that reads the doc. `rules/solid.md` takes the other branch, declares judgment and explains that trade in its own final section; here the undecidable material was routed out of the rule rather than numbered inside it, which is the move `rules/duplication.md` makes with the duplicate no script can see.
