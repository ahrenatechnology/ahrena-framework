---
id: review-findings
type: doc
clade: engineering
subclade: quality
title: What a review finding owes its reader
summary: The four severity levels and the test that assigns each, why a finding names a file, a line and a condition rather than a virtue, why the review routes by changed path, and why an external fork's checkout is never executed.
references:
  - docs/simplicity.md
---

# What a review finding owes its reader

This is the companion to the review procedure in `skills/reviewing-diffs/SKILL.md` and `skills/detecting-contract-breaks/SKILL.md`. Those skills say what to do; this says what a finding has to contain before it is worth writing down, what each severity level means in terms a second reviewer would apply the same way, and the two boundaries the procedure will not cross.

A review is worth its cost when the author can act on it without a conversation. Everything below is in service of that one property.

## A finding names a file, a line and a condition

Three fields, and a finding missing any of them is not a finding.

**The file and the line** are where the state was observed. Not the module, not the class, not "the approval flow" — the line, because the author has to find it, and a finding that costs a search is a finding that gets deferred.

**The rule and the condition number** are what the state violates. Every rule in this plugin numbers its conditions, and each numbered condition names a detectable state and what decides it. Citing the rule without the number hands the author eleven pages; citing the number hands them one sentence they can agree or disagree with.

**The state observed** is what is actually there, phrased so a reader can check it against the line. "This function nests control flow 5 deep" is checkable. "This function is hard to follow" is not, and it is the same defect the reviewing procedure in this framework's foundation plugin calls a maxim: a virtue where a condition belongs.

A fourth field is optional and usually worth its space: the change that resolves it. Most conditions in this plugin name their own fix — splitting the function, deleting the statement, moving the boundary — so the sentence is short, and its absence is what makes a reviewer sound like an obstacle rather than a colleague.

**What this rules out is vague feedback.** "Looks good", "consider refactoring this", "not sure about this approach" and "could be cleaner" are each a reviewer's impression with the reasoning removed. They cost the author a round trip to discover what was meant, and they cannot be argued with, because there is nothing stated to disagree with. If the impression is real, it is a question (see below) and it is written as one.

## The four severity levels

The predecessor of this procedure carried two levels and distinguished them by colour, which tells a reader the weight of a finding and nothing about how that weight was decided. These four are each defined by a test, so two reviewers reading the same finding assign the same level.

| Level | The state | The test that assigns it |
|---|---|---|
| **blocking** | a numbered condition is violated by a line this change introduces or edits | the finding names the rule, the condition, the file and the line, and the line is inside the diff |
| **deferrable** | the same violation, on a line the change did not touch, or where the fix reaches code the change does not | the finding names the same four things, and the line is outside the diff or the fix is |
| **question** | a condition the reviewer cannot decide without an input only the author or the wider organisation holds | the finding names the condition, the missing input, and which answer would settle it either way |
| **unchecked** | a condition nothing decided, because a detector, a base version or permission to execute was unavailable | the finding names the condition and why it was not decided |

**Only blocking stops the change.** The other three are not weaker forms of it. Each names a different reason the reviewer is not entitled to demand a fix in this pull request, and collapsing them is how a review turns into a list of things the author is expected to feel bad about.

**Deferrable is about the diff, not about importance.** A pre-existing violation is real and the author did not introduce it. Asking them to fix it because they happened to edit the file next door is how an unrelated change grows a refactor, and the refactor is then reviewed by nobody. The finding is recorded so the next person has it; it does not gate this change.

**Question is the level the gated conditions produce.** Eight conditions across five rules are gated by the abstraction trigger in `rules/yagni.md` — three in `rules/solid.md`, two in `rules/value-semantics.md`, and one each in `rules/duplication.md`, `rules/cross-cutting-concerns.md` and `rules/pattern-selection.md` — and that rule's own boundary section says the count cannot be decided from a tree that does not contain every consumer. A reviewer who marks such a finding blocking has asserted something they cannot see. A reviewer who drops it has thrown away the one question worth asking. It is a question, and the author answers it.

**Unchecked is a statement about the review, not about the code.** It says an axis was not covered, which is exactly what the reader of a green review needs to know and exactly what a review that reports only violations conceals.

## Why the review routes by changed path

The eleven rules in this plugin do not all reach every change. The conditions in `rules/domain-model.md` are about modules under a context's `domain/` directory; the conditions in `rules/contract-first.md` are about a published contract document; the shipped detector parses Python and nothing else.

Reading every rule against every diff produces two failures at once. The reviewer spends its attention on conditions that cannot fire, and the conditions that can fire get a fraction of what they deserve. Routing is what buys the depth: the changed paths select a small set of rules, and each one is then read properly against the lines that could violate it.

The cost of routing is a miss when a path is classified wrongly, and it is a real cost. A file with no extension the route map knows falls through to the language-agnostic conditions, which is the weaker route, and the route map says so rather than pretending the default is complete.

## Why an external fork's checkout is not executed

Five conditions in this plugin are decided by running something. Condition 3 of `rules/solid.md` runs the supertype's own tests against a subtype. Condition 4 of `rules/cross-cutting-concerns.md` replays one request twice with one key. Conditions 2, 3 and 4 of `rules/contract-first.md` start the service to fetch what it serves, run a test per declared operation, and validate a captured event against the CloudEvents schema inside that test. A reviewer that wants any of those five answers has to build the project and run its suite.

Building a project executes code the change's author controls. Not only the test files in the diff — the dependency manifest, the build script, the package post-install hook, the test configuration and every transitive dependency they name. On a pull request whose head is a branch in the same repository, the author already had write access and this buys nothing. On a pull request from an external fork, the author is a stranger, and bootstrapping their checkout runs their code on the reviewer's machine with the reviewer's credentials in the environment.

So the procedure does not do it. It records an `unchecked` finding that names each condition it could not decide and the reason, and it continues with everything that only reads: the shipped detector, the judgment conditions, and the contract comparison, which is a diff of two documents and executes nothing.

**This is a refusal, not a gap to close later.** The suggestions that come up are a sandbox, a container or a disposable runner, and each of them is a real answer to a different question — how to run untrusted code safely — which is a piece of infrastructure the consuming project either has or does not. This plugin has no way to know which, and a procedure that assumes the sandbox exists is a procedure that silently executes a stranger's code on the machines where it does not. `docs/simplicity.md` records the general form of this position: a detector that is confidently wrong is worse than an absent one, and the same holds for a safety precondition that is confidently assumed.

## Where this stops

**The levels say nothing about how many findings a review should have.** A review with forty blocking findings on a small change is either reviewing generated code or applying a rule where its boundary section says not to, and both are the reviewer's defect rather than the author's. Nothing here detects that; a second reader does.

**Nothing here decides what happens to the findings.** Which verdict a set of findings produces, when the reviewer may approve, and how the result is published are in `docs/review-verdicts.md`, because they are about the reviewer's history on the pull request rather than about the change.

**The route map is not a taxonomy of software.** It maps the paths this plugin's conditions can reach. A change touching something none of the eleven rules is about produces a review that says so, and that is the honest output rather than a failure of the map.
