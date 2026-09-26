# ADR-001: Pull requests land on trunk as a squash

- **Status:** accepted
- **Date:** 2026-09-25
- **Issue:** #72

## Context

`contributing/rules/commit-format.md` condition 6 requires a signature header on
the commit object. The rule records that it cannot be enforced against trunk and
is gated on a pull request's own commits instead, and it names what is missing
rather than solving it: "the fix is a merge strategy this rule does not own."

Nothing owned it. Sixteen pull requests had landed by rebase merge, and the
merge method was never chosen — it was whichever button was in front of the
person merging.

The method turns out to decide the signature. A rebase merge replays each commit
onto the base, and a replayed commit is a new object: the signature is over the
old one and does not survive the rewrite. A squash commit is built on GitHub's
side and signed there. Measured on trunk at `8ffc175`: 7 of 37 commits carry a
signature header, and they are the four earliest commits plus the three squash
merges of this date. All thirty unsigned commits are rebase-merged pull
requests.

A second, narrower problem surfaced the same day. Pull request #68's branch
carried a merge of trunk that resolved a conflict in
`.github/workflows/validate.yml`, where a step had been added on either side of
the fork. A rebase
drops the merge commit and replays what is under it, which reproduces the
conflict the merge had already settled. Verified before merging: the replay
fails on `79b88d6`.

## Decision

A pull request lands on trunk as a squash. One commit per pull request, whose
message is written for trunk rather than assembled from the branch's.

## Consequences

Trunk's commits carry signatures. The paragraph in `commit-format.md` that reads
as a permanent loss now describes a backlog that stops growing, because every
commit that lands from here is signed. The condition becomes enforceable against
trunk once enough of the history is squash-made, and this record is what a
reader needs to understand why the number moves.

A branch that resolved a conflict against trunk lands without reproducing it,
because the squash applies the resulting tree rather than the commits beneath
it.

Trunk stays linear, which it already was, so nothing about reading it changes.

The cost is granularity, and it is paid on every merge. A pull request's
intermediate commits stop existing on trunk. `git bisect` lands on a pull
request rather than on a step inside one, and the individual messages survive
only in the closed pull request, which is a weaker place to keep them. For a
branch whose commits were each worth reading, that is a real loss, and it makes
the squash message responsible for carrying what they said.

The squash commit is authored by whoever merged, not by whoever wrote the
branch. Authorship survives only through a `Co-Authored-By` trailer that the
squash message has to carry deliberately.

GitHub appends ` (#NN)` to the subject. Condition 3 caps a subject at 72
characters, so the budget a pull request title actually has is 66, and the
author writing that title cannot see the suffix that will consume the rest. The
first three subjects came in at 67, 67 and 68, under the cap only because they
were kept short on purpose.

## Alternatives considered

- **Rebase merge**, which sixteen pull requests used. Rejected on the
  measurement: it is why 30 of trunk's 37 commits carry no signature, and it
  reproduces a conflict a branch has already resolved.
- **Merge commit.** Keeps every commit and every signature on the branch side,
  and ends trunk's linearity. Rejected because the branch commits it preserves
  are the ones a squash message is meant to replace, and the merge commit it
  adds to trunk carries no signature of its own.
- **Fast-forward only.** Requires rebasing the branch before it can merge, so it
  inherits both of the rebase's failures and adds a manual step.
- **Leaving the method to whoever merges.** Rejected because that is the state
  this record replaces, and it produced thirty unsigned commits without anybody
  deciding to.
