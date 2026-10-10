---
id: review-verdicts
type: doc
clade: quality
title: The verdict a review publishes
summary: Why the verdict follows the findings alone, what an approval on the first pass asserts and what makes it worth something, the three rows, why one comment per commit and the earlier one is left standing, why the marker is readable, and why the reviewer never edits the change.
references:
  - docs/review-findings.md
---

# The verdict a review publishes

This is the companion to the publication procedure in `skills/publishing-review-verdicts/SKILL.md`. That skill says what to do; this says why the verdict is assigned the way it is, what each of the three rows protects, and what the comment marker buys.

The severity levels the table reads are defined in [`docs/review-findings.md`](review-findings.md). Nothing here re-decides them. This repository's `ADR-013` records the decision this document argues, and the rule it replaced.

## The verdict follows the findings

One axis: the highest severity present now.

| Findings now | Verdict |
|---|---|
| at least one **blocking** | request changes |
| no blocking, but at least one question or unchecked | comment |
| deferrable only, or nothing at all | approve |

**Row one stops the change.** A blocking finding is a numbered condition violated on a line this change introduces or edits, and the author owes a fix or an argument.

**Row two is a review that has not finished.** A question is addressed to the author and the answer may turn it into a blocking finding. An unchecked condition is a part of the change nobody read. Approving over either is approving over a hole, so neither approves, however clean the rest is.

**Row three is the approval, and it can arrive on the first pass.** Deferrable findings do not hold it back: each is a real violation on a line the change did not touch, recorded for the next person, and by its own definition not this pull request's to fix.

## What an approval on the first pass is worth

The failure an approving reviewer has to answer for is specific. An automated reviewer runs on a pull request, finds nothing, approves, and that approval is indistinguishable from the one it would have produced if it had been pointed at the wrong base, given an empty diff, or unable to read the change. A person who approves everything is noticed. An automated reviewer is not, because nobody reads a stream of approvals looking for the one that should not be there.

The predecessor of this rule answered by forbidding the first approval: the reviewer could approve only after having itself requested changes on the same pull request. That made an approval mean "what I objected to is gone", and it declined every change that was right from the first commit.

The answer here is that the approval carries its own evidence. A review states the base and the head it read, the routes that fired, the skills no route selected, the paths nothing but the baseline reached, and every condition it did not decide. A reviewer pointed at an empty diff reports no routes. One that could not run a check reports it unchecked, and by row two does not approve.

**So an approval asserts this, and no more:** over the commit named in the marker, every routed condition was decided and none is violated by a line the change touched. It does not assert that the change is wanted, or that nothing outside the routes is wrong.

**What that costs is the second chance.** Under the old rule a person merged every change, and could notice what the review missed. An approval now lands the change, through `skills/landing-approved-changes`, and what a miss meets is CI on trunk and the revert. A repository that cannot afford that requires a named person's approval in its ruleset, and the forge holds the merge.

## When the forge refuses the approval

GitHub does not let an account approve its own pull request. Where the reviewer publishes through the author's account, the approving review is refused.

The verdict does not change. It is published as a comment whose verdict line reads approve, and the comment says the forge refused the review and why. Landing reads the verdict, not the review's state on the forge. Where the ruleset requires an approving review, the merge is then refused too, and the pull request waits for a person, which is the ruleset doing what it was set to do.

## One comment per commit, and the earlier ones stay

The reviewer publishes a marker on the first line of the comment body, derived from the pull request number and the head commit the review looked at.

The marker does two things. It makes a re-run on the same commit idempotent: the reviewer finds its own earlier comment carrying the same marker and edits that comment instead of adding a second one, so a review triggered three times produces one comment rather than three copies of the same list. And it makes a re-run on a new commit a new comment, because the marker no longer matches anything.

**The earlier comment is left exactly where it is.** It is not deleted, edited or collapsed, and there are two reasons.

The first is that it is not stale. It is an accurate review of a commit that existed, and the fact that a later commit fixed three of its findings is information a reader wants, not noise to clean up.

The second is that the trail is the record of what the reviewer said at each commit. An approval that follows two requests for changes reads differently from one that arrived alone, and a reader can see that only while the earlier comments stand.

**Re-running on the same commit is the one case where content is replaced**, and the marker is what makes it safe: the verdict being overwritten is a verdict about the same commit, so nothing about a different state of the change is lost.

## Why the marker is readable rather than hashed

The obvious construction is a hash of the pull request number and the commit, truncated, in a comment. It is what the predecessor of this procedure used.

A plain, readable marker is better on three counts, and is no less idempotent. It needs no tool to produce, which matters because the reviewer may be running somewhere with no shell. It needs no tool to verify: a person reading the comment source can see which commit was reviewed, which is a question people actually ask when a review looks out of date. And a mismatch is legible — two markers that differ show which commits they belong to, where two truncated hashes show only that they differ.

The hash buys one property, which is a fixed length, and the marker is not stored anywhere that needs one.

## Why the reviewer never changes the pull request

The reviewer publishes its review, and after an approval asks the forge to land the commit it reviewed. It does not commit, push, rebase, re-target, label, assign, request other reviewers, resolve threads or close.

A reviewer that fixes what it finds has stopped being a reviewer of that change, because the next thing it reviews includes its own work, and nobody reviews that. The separation is the whole value of a second party looking, and it survives only while the second party leaves the content of the change alone. Landing does not touch the content: it merges the commit that was read, named by its hash, and a head that moved since the review is not landed.

There is a second reason, smaller and more practical. A fix-up commit from the reviewer moves the head, which invalidates the marker of the review that proposed it, which turns one comment into two about the same state. The mechanism and the principle point the same way.

## Where this stops

**Nothing here decides what a ruleset requires.** Required approvals, required checks and who owns a surface are the repository's settings, and an approval here does not stand in for any of them.

**Nothing here covers other reviewers.** A pull request usually carries comments from people and from other automated reviewers. Reading, aggregating or answering those is outside this procedure: this reviewer publishes its own verdict and leaves everyone else's threads alone.

**The approval is only as good as the coverage statement beside it.** A review whose routes missed the part of the change that mattered approves a change it did not read, and says which routes fired. Reading that list is what a person checking an approval does.
