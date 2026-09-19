---
name: publishing-review-verdicts
description: Use when review findings are ready to publish on a pull request. Picks request-changes, comment or approve from severity and this reviewer's own prior verdicts, one comment per commit.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-findings.md
  - docs/review-verdicts.md
---

# Publishing review verdicts

One review, one comment, one verdict. The reasoning behind the approval rule and the four rows it produces is in [`docs/review-verdicts.md`](../../docs/review-verdicts.md); this is the procedure that applies it.

Nothing in this procedure changes the pull request. The single write is the review itself.

## 1. Build the marker

The marker is a plain, readable string on the first line of the comment body, inside an HTML comment so it does not render:

```text
<!-- ahrena-review:142:a1b2c3d -->
```

The pull request number, then the first seven characters of the head commit the review looked at. No hash: a readable marker needs no tool to produce and none to verify, and `docs/review-verdicts.md` sets out why that is worth more than a fixed length.

Take the head from step 1 of the review, not from the branch tip now. If a commit landed while the review was running, the marker must name the commit that was actually read, or the comment claims to be about a state nobody looked at.

## 2. Find this reviewer's own earlier comment for this commit

List the comments this reviewer has published on the pull request and look for a marker matching the one from step 1.

**A match** means this is a re-run on the same commit. Edit that comment in place, replacing its body. Nothing about a different state of the change is lost, because the verdict being overwritten is about the same commit.

**No match** means the head has moved, or this is the first review. Publish a new comment.

**Leave every earlier comment exactly as it is.** Do not delete, collapse or rewrite a review of a different commit. Each one was accurate about the state it read, and step 3 reads this reviewer's own published history to decide whether it may approve — a reviewer that tidies up after itself deletes the evidence that permits its own approval.

## 3. Determine whether this reviewer has already requested changes here

Read this reviewer's own verdicts on this pull request and answer one question: has at least one of them been a request for changes.

This is the second axis of the table in step 4, and it is read from what was published rather than from anything remembered. Two things make the answer wrong in ways that are easy to miss. Somebody else's request for changes does not count — the rule is about this reviewer having disagreed. And a request for changes that was later dismissed still happened; the trail is the history, not the current state.

If this reviewer publishes under an identity that is not stable across runs, the answer is always no and the approval row can never be reached. Say so in the comment rather than approving anyway.

## 4. Pick the verdict

Two axes: the highest severity present now, and the answer from step 3.

| Findings now | Prior request for changes by this reviewer | Verdict |
|---|:---:|---|
| at least one **blocking** | either | request changes |
| no blocking, but at least one deferrable, question or unchecked | either | comment |
| nothing at all | no | comment, recording the first clean pass |
| nothing at all | yes | approve |

Cold-start approval is forbidden. A clean first pass is published as a comment, which records that the review ran and found nothing and claims nothing more; the approval row exists only to resolve a refusal this reviewer made earlier.

The row that gets skipped is the third. It looks like ceremony and it is what makes the second axis reachable at all — without it a reviewer that never finds anything can never approve anything.

## 5. Assemble the body

Copy the skeleton in `references/review-body.md` and fill it. The order is fixed — marker, verdict line, counts, findings grouped by severity, then the axes that were not decided — because a reader scanning three reviews should find the same thing in the same place each time.

Two sections carry the weight. Every finding line has its four fields from `docs/review-findings.md`, and a line missing one is dropped rather than published short. And the `unchecked` section is written even when it is empty, with the word that says so, because an absent section reads as full coverage and that is the claim this procedure is built to avoid making.

## 6. Publish once, then stop

Publish the verdict from step 4 with the body from step 5, as an edit or as a new comment per step 2.

Then stop. Do not push a fix-up commit, retarget the branch, change a label, assign anyone, request another reviewer, resolve a thread, close the pull request or merge it. A reviewer that fixes what it found is reviewing its own work on the next run, and the separation between the two parties is the only thing a second opinion is made of.

Report back what was published: the verdict, the marker, and whether an existing comment was edited or a new one created.

## When this skill does not apply

**There are no findings and no review was run.** This publishes a verdict; it does not stand in for having reached one. A comment saying nothing was checked is worse than no comment, because it occupies the place a real review would have gone.

**Answering the pull request's other reviewers.** People and other automated reviewers leave threads, and reading, aggregating or replying to them is somebody else's job. This procedure publishes one verdict and leaves every other thread alone.

**Deciding whether the change may merge.** The verdict is one input. Who owns the surface, what the branch protection requires and whether the change is wanted are all outside it, and an approval here asserts only that what this reviewer objected to is gone.

**A review published anywhere but a pull request.** A findings list handed back in a terminal, written into a file or sent to a person needs none of this: the marker, the idempotency and the paper trail all exist because the destination keeps a history that outlives the run.
