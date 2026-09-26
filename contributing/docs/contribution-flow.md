---
id: contribution-flow
type: doc
clade: contributing
title: The contribution flow
summary: Where a change comes from, why the issue number rides in the branch name, where the commit thresholds came from, and which properties of a commit this framework refuses to check.
references:
  - rules/branch-naming.md
  - rules/commit-format.md
---

# The contribution flow

This is the reference for the two rules in this plugin. They state what is checked; this states why, carries the measurements behind every number in them, and records what was refused.

## The chain, and the one link that is new

```
issue  →  branch  →  commits  →  pull request
```

Three of those four steps already happened in this repository the way they should. Issues exist and are detailed. Branches are typed. Commits are conventional — all 38 of them, which is a better rate than most projects reach on purpose.

The link that is missing is the first arrow. A branch called `feat/foundation-core` records what kind of change it is and what it is about, and nothing about what it answers. Five of five branches predating this plugin are that shape, so the work is traceable from the branch only to whoever remembers it.

The pull request is a weaker case and is worth stating at its real strength rather than borrowing the branch's. Of the seven pull requests opened here, six name an issue in the body; only #35 names none. The link is therefore usually written — it is just written by hand, in prose, once per pull request, and five of the seven carry no `Closes`, `Fixes` or `Resolves`, so nothing closes on merge. That is a pull-request problem with a pull-request fix, and this plugin does not carry one.

Putting the issue number in the branch name fixes that at the cheapest possible point. The number is available at the one moment somebody is guaranteed to be thinking about the work as a whole, it costs nothing to carry, and it propagates for free: the branch name appears on the pull request, in the merge commit, and in every `git branch` listing for as long as the branch exists. It also enforces issue-first without a second rule to do it, because a name that needs the number cannot be written before the number exists.

## Why the type set has eleven entries and not five

`rules/branch-naming.md` and `rules/commit-format.md` both close their type set at the same eleven: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`.

Five of those appear in this repository's history:

| Type | Commits on trunk |
|---|---|
| `feat` | 12 |
| `docs` | 8 |
| `ci` | 2 |
| `refactor` | 1 |
| `chore` | 1 |

Closing the set at the measured five would be the corpus-driven move, and it would be wrong. The five are not a preference discovered by practice; they are the types a repository happens to need in its first three weeks, before it has shipped anything that can break. A set closed at five rejects `fix` the first time somebody fixes a bug and `revert` the first time somebody reverts one, and a gate that fails correct work is a gate that gets switched off.

So the set is inherited rather than measured, from `@commitlint/config-conventional`'s `type-enum`, which is the list the Conventional Commits specification itself points at for everything beyond `feat` and `fix`. It is stated once in each hook and read from the specification rather than from the other hook.

Scope stays optional on the same evidence, in the other direction: 21 of 38 commits carry one, so requiring it would fail practice that is not wrong and forbidding it would fail more than half the corpus.

## Where 72 came from

`git log` indents every line of a commit message by four spaces. A subject of 72 characters therefore occupies 76 columns of a default 80-column terminal, and a subject of 77 wraps. That is the whole derivation, and it is the only reason the number is 72 rather than 70 or 80. It reaches this framework by way of the predecessor's `codex-commit-standards`, which stated 72 without saying where it came from.

The threshold is inherited rather than measured. When it was set, the measurement offered nothing to inherit instead; re-measured, it offers 77, and 77 is worse. Here is the distribution over the 38 subjects on trunk:

| | Characters |
|---|---|
| Shortest | 21 |
| Median | 65 |
| 90th percentile | 75 |
| Longest | 88 |
| Over 72 | 6 of 38 |

Over the first 24 subjects there was no empty span anywhere a ceiling could sit, and that absence was the whole argument for inheriting the number. Over 38 there is one. The body of the distribution still ends at 76 — the run from 64 up is 64, 65, 66, 67, 68, 69, 70, 71, 73, 75, 76, missing only 72 and 74, a one-character hole each — and then it stops. The next two subjects are 83 and 88. That leaves 77 to 82 empty, six characters wide, which is the widest span in the distribution apart from the 16-character hole between 21 and 38, and a gap at the bottom is no use for a ceiling.

So the move `rules/clean-code.md` in the engineering plugin makes — place the threshold in an empty span, where it fails nothing in the body and cannot be reached without a change of kind — now returns an answer. The answer is 77, and it is refused three times over.

**The span was opened by two commits.** Both are `engineering-python` subjects written on the same day, at 83 and 88. Two observations establish that somebody wrote two long subjects, not that a change of kind begins above 76. One more subject at 79 closes the span and the measured threshold evaporates, which is the test of whether a span is structure or sample.

**77 is laxer than 72, not stricter.** It fails the two outliers and passes 73, 75 and 76; the inherited threshold fails all six. The measurement therefore argues for loosening the rule until more of what exists passes it, and that is the direction in which calibrating to a corpus is least defensible — a ceiling that rises to admit whatever was written last detects nothing by construction.

**77 has no derivation.** 72 occupies 76 columns of an 80-column terminal under `git log`'s four-space indent, and 77 wraps. That arithmetic is the only argument for having a number rather than a preference, and trading it for a span two commits opened is a bad trade.

**And the span sits where only violations live.** It runs 77 to 82, and the cap is 72, so every subject that could fill it already fails condition 3. The gap cannot be closed by compliant practice — only by writing more of exactly what the rule forbids. This was demonstrated by the commit that wrote this paragraph: its first subject was 79 characters, landing inside the span, and the hook rejected it before it could reach trunk. A gap that opens above a ceiling, in the region the ceiling exists to empty, is produced by the ceiling and carries no information about where the ceiling belongs.

So the rule keeps 72 and the reason has changed. It is no longer that the measurement offered nothing; it is that the measurement offered 77 and 77 is worse. Six of 38 commits on trunk fail the threshold the rule ships, and saying so is what keeps this a rule that asks for a small change on thin evidence rather than one that claims the evidence is better than it is.

## What "signed" means, and which one is checked

Three properties can all be called "signed" and they are not equally available.

| Property | Detector | What it needs | Fires correctly here |
|---|---|---|---|
| A signature is on the object | a `gpgsig` header in the stored commit | nothing beyond the repository | yes |
| The signature verifies | `git verify-commit` | `gpg.ssh.allowedSignersFile` or a keyring holding every contributor's key | no |
| The forge marks it Verified | the forge's API | the key registered on an account, plus a credential | no |

Condition 6 of `rules/commit-format.md` takes the first.

The second and the third both need key distribution the framework cannot ship. A consumer installing this plugin gets no keys with it, so a condition built on verification fires on everybody who has not yet configured a signer list — a detector that is wrong about the ordinary case, which is the failure `docs/simplicity.md` in the engineering plugin argues against and which already cost `rules/kiss.md` a condition. The third adds a network call and a credential to a hook whose whole claim is that it runs offline.

Both of the obvious shortcuts were run against a commit known to carry an SSH `gpgsig` header, on git 2.43.0, in this repository as it is configured.

`git verify-commit` exits 1 without deciding: it prints `gpg.ssh.allowedSignersFile needs to be configured and exist for ssh signature verification`. That is the second property in the table failing to be available, observed rather than assumed — the tool declines, and a gate that reads a decline as a failure fails everyone who has not distributed keys.

`git log --format=%G?` looks like a presence check and is not one. It reports `N` for an unsigned commit, and `N` again for the SSH-signed one — the same letter for "no signature" and "a signature I have no key for". Reading the header directly is the only local detector that separates the two.

**What the choice costs is trust, and the cost is real.** A self-signed key nobody has vouched for satisfies condition 6, and so does a signature over a payload that has since been rewritten. The condition proves that signing was configured and used. Proving who signed is a different job and it belongs where the keys are, which is the forge.

The other thing it cannot do is survive the forge's merge, and which merge is the whole of it. Every commit written in this project's agent container carries an SSH signature. A rebase merge re-authors each one onto the base and does not re-sign; a squash merge is built on the forge's side and is signed there. The evidence is clean: 31 of 38 commits on trunk carry no signature header at all, and the seven that do are the four earliest commits and three squash merges. That is why the condition is checked over a pull request's own commits rather than over trunk's history.

It also means the fix is a repository setting rather than anything this rule can ship. This repository records the decision as `ADR-001` and has configured the forge to offer no merge method but the squash. A consumer has to make that choice themselves, and until they do, their trunk will keep collecting unsigned copies of commits that were signed when they were written.

## The three things a reviewer still has to do

Each of these was stated as law by the predecessor, and each is refused here rather than restated, because none of them is a state a script can decide. They are the questions a reviewer asks in the place where a condition would have been.

**Is this commit one change?** The predecessor's `lex-small-commits` required it and named human review as the enforcement, which is an accurate description of an unenforceable rule. The runnable approximation is a threshold on diff size, and it fails a large rename while passing a small commit that slipped a fix into a refactor. Ask instead: if this commit were reverted on its own, what else would break?

**Is the subject in English, in the imperative?** `lex-commit-language` required both and named a commitlint rule that did not exist. Detecting English needs a dictionary or a model; detecting the imperative needs a parser for English; both would be wrong about `docs: i18n groundwork`. Ask instead: does the subject complete the sentence "this commit will..."?

**Does the message describe the change that is in the diff?** No condition anywhere in this plugin reads a description. `feat: stuff` passes every one of them, and so does a subject that accurately describes a different commit.

## Where this stops

**This plugin covers the branch and the commit, and stops there.** What an issue must contain, what a pull request must contain, and whether trunk may be written to directly are three separate questions with three separate answers, and none of them is settled in this plugin today. The branch rule therefore says only that a number must be present, not that the issue behind it is any good; and nothing here says what happens between pushing a branch and the change arriving on trunk.

**Both rules ship a hook, and neither of them runs on a contributor's machine unless they run it.** There is no installed git hook, no `pre-push`, and no `commit-msg`. The enforcement point is CI, for the reason `rules/commit-format.md` gives: at `commit-msg` time there is no commit object, so the signature condition has nothing to read, and two enforcement points that disagree are worse than one that fires late.

**And in CI both hooks judge a pull request only.** The workflow runs each hook's test suite on every event, because a detector whose own tests are not in CI stops being trustworthy the first time somebody edits it in a hurry. The two checks over the repository's own state are gated on the pull-request event: on a push to trunk there is no working branch to name, and trunk's commits are the rebase's re-authored copies, so the signature condition would fail the default branch permanently over objects nobody can now re-sign. The checkout fetches full history, because a hook that walks a revision range in a one-commit clone finds nothing and passes by seeing nothing.

**The measurements here are small and they will age.** Twenty-four commits, five branch names and five pull requests is a corpus thin enough that one busy week could change every figure in this document. Two of the numbers are load-bearing — the 72 that four commits already fail, and the eleven types that five of eleven are actually in use — and both are stated as inherited rather than measured for exactly that reason. When the corpus is large enough to argue with them, the argument is worth having.
