---
id: review-verdicts
type: doc
clade: engineering
subclade: quality
title: The paper trail and the verdict it permits
summary: Why a reviewer may approve only after having itself requested changes, the four rows that follow from that, why one comment per commit and the earlier one is left standing, why the marker is readable rather than hashed, and why the reviewer never edits the change.
references:
  - docs/review-findings.md
---

# The paper trail and the verdict it permits

This is the companion to the publication procedure in `skills/publishing-review-verdicts/SKILL.md`. That skill says what to do; this says why the approval rule is shaped the way it is, what the four rows of the decision table are each protecting, and what the comment marker buys.

The severity levels the table reads are defined in [`docs/review-findings.md`](review-findings.md). Nothing here re-decides them.

## An automated reviewer that can approve on sight is worth nothing

The failure this rule exists for is specific. An automated reviewer runs on a pull request, finds nothing, approves, and the approval is indistinguishable from the approval it would have produced if it had been misconfigured, pointed at the wrong base, given an empty diff, or unable to read the changed files at all. Every one of those failures is silent and every one of them produces the same green mark.

A human reviewer has the same failure mode and a different defence against it: their approval carries their name, and a reviewer who approves everything is noticed. An automated one is not noticed, because nobody reads a stream of approvals looking for the one that should not be there.

So the reviewer is required to have disagreed at least once, on this pull request, before it is allowed to agree. The rule reads:

> The reviewer may approve a pull request only when it has itself previously requested changes on that same pull request. Cold-start approval is forbidden.

**What this buys is a signal with content.** An approval now means something specific and checkable: this reviewer found problems on this change, said so, and those problems are gone. A first-pass clean result is still published — it is just published as a comment, which records that the review happened and claims nothing more than that.

**What it costs is an approval on a change that was correct from the first commit.** That case exists and this rule declines it. The cost is one missing green mark on a change that needs no fixing; the alternative is approvals whose meaning depends on whether the reviewer happened to be working, which is not a signal at all. The clean first pass is recorded in a comment, so the reader still sees that the reviewer ran and found nothing.

## The four rows

Two axes: the highest severity present now, and whether this reviewer has itself previously requested changes on this pull request.

| Findings now | Prior request for changes by this reviewer | Verdict |
|---|:---:|---|
| at least one **blocking** | either | request changes |
| no blocking, but at least one deferrable, question or unchecked | either | comment |
| nothing at all | no | comment, recording the first clean pass |
| nothing at all | yes | approve, resolving the earlier refusal |

**Row one does not consult the history.** A blocking finding is a blocking finding whether or not the reviewer has been here before. Letting prior approval soften a present blocker would make the verdict depend on the order the commits arrived in.

**Row two is where most reviews land, and it is deliberately not an approval.** A review carrying a question has not finished — the question is addressed to the author and the answer may turn it into a blocking finding. A review carrying an `unchecked` axis has a hole in it, and approving over a hole is the silent failure this whole rule is about. Deferrable findings alone do not block the change, and they also do not earn agreement.

**Row three is the one people try to delete.** It looks like ceremony: nothing is wrong, so why not approve. The answer is that the second axis has no other way to become true. Without row three, a reviewer that never finds anything never establishes the history that row four reads, and row four is the only place an approval comes from. Row three is what makes the paper trail a trail rather than a condition that can never be met.

**Row four is the only approval.** It resolves the earlier refusal, and the thing it asserts is narrow: what this reviewer objected to is no longer there. It does not assert that the change is correct, that it is wanted, or that it may be merged. Where the repository requires a named owner's approval to merge, this one is an additional signal beside theirs and not a substitute for it.

## One comment per commit, and the earlier ones stay

The reviewer publishes a marker on the first line of the comment body, derived from the pull request number and the head commit the review looked at.

The marker does two things. It makes a re-run on the same commit idempotent: the reviewer finds its own earlier comment carrying the same marker and edits that comment instead of adding a second one, so a review triggered three times produces one comment rather than three copies of the same list. And it makes a re-run on a new commit a new comment, because the marker no longer matches anything.

**The earlier comment is left exactly where it is.** It is not deleted, edited or collapsed, and there are two reasons.

The first is that it is not stale. It is an accurate review of a commit that existed, and the fact that a later commit fixed three of its findings is information a reader wants, not noise to clean up.

The second is the one that actually forces it: the second axis of the table is read out of this reviewer's own published history. The request for changes that row four consults is a comment sitting on the pull request. A reviewer that tidied up after itself by replacing its earlier verdicts would delete the evidence that permits it to approve, and would then be unable to approve anything — or, worse, would keep a record that no longer matches what it published.

**Re-running on the same commit is the one case where content is replaced**, and the marker is what makes it safe: the verdict being overwritten is a verdict about the same commit, so nothing about a different state of the change is lost.

## Why the marker is readable rather than hashed

The obvious construction is a hash of the pull request number and the commit, truncated, in a comment. It is what the predecessor of this procedure used.

A plain, readable marker is better on three counts, and is no less idempotent. It needs no tool to produce, which matters because the reviewer may be running somewhere with no shell. It needs no tool to verify: a person reading the comment source can see which commit was reviewed, which is a question people actually ask when a review looks out of date. And a mismatch is legible — two markers that differ show which commits they belong to, where two truncated hashes show only that they differ.

The hash buys one property, which is a fixed length, and the marker is not stored anywhere that needs one.

## Why the reviewer never changes the pull request

The reviewer publishes exactly one thing: its review. It does not commit, push, rebase, re-target, label, assign, request other reviewers, resolve threads, close or merge.

A reviewer that fixes what it finds has stopped being a reviewer of that change, because the next thing it reviews includes its own work, and nobody reviews that. The separation is the whole value of a second party looking, and it survives only while the second party's output is words.

There is a second reason, smaller and more practical. A fix-up commit from the reviewer moves the head, which invalidates the marker of the review that proposed it, which turns one comment into two about the same state. The mechanism and the principle point the same way.

## Where this stops

**Nothing here decides who may merge.** The verdict is one input to that decision and this document has no opinion on branch protection, required approvals or who owns the surface.

**Nothing here covers other reviewers.** A pull request usually carries comments from people and from other automated reviewers. Reading, aggregating or answering those is outside this procedure: this reviewer publishes its own verdict and leaves everyone else's threads alone.

**The rule does not survive a reviewer with no history.** A repository where this reviewer's earlier comments were deleted, or one where it publishes under an identity that changes between runs, has no second axis, and the table collapses to rows one to three — no approval, ever. That is the correct degradation and it is also a warning: the identity the reviewer publishes under is the thing the whole rule is built on, and an unstable one silently removes the approval path.
