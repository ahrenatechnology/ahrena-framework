---
name: publishing-review-verdicts
description: Use when review findings are ready to publish on a pull request. Picks request-changes, comment or approve from the highest severity present, one comment per commit, and hands an approval to the landing skill.
type: skill
clade: quality
references:
  - docs/review-findings.md
  - docs/review-verdicts.md
  - skills/landing-approved-changes/SKILL.md
---

# Publishing review verdicts

One review, one comment, one verdict. The reasoning behind the three rows is in [`docs/review-verdicts.md`](../../docs/review-verdicts.md); this is the procedure that applies it.

Nothing in this procedure changes the content of the pull request. It makes two writes: the review itself, as a comment, and a commit status on the head that was read, which is what a ruleset can require. Landing an approved change is a separate procedure.

## 1. Build the marker

The marker is a plain, readable string on the first line of the comment body, inside an HTML comment so it does not render:

```text
<!-- ahrena-review:142:a1b2c3d -->
```

The pull request number, then the first seven characters of the head commit the review looked at. No hash: a readable marker needs no tool to produce and none to verify, and `docs/review-verdicts.md` sets out why that is worth more than a fixed length.

Take the head from step 1 of the review, not from the branch tip now. Keep the full commit sha as well: the marker abbreviates it, and step 5 needs the whole of it. If a commit landed while the review was running, the marker must name the commit that was actually read, or the comment claims to be about a state nobody looked at.

## 2. Find this reviewer's own earlier comment for this commit

List the comments this reviewer has published on the pull request and look for a marker matching the one from step 1.

**A match** means this is a re-run on the same commit. Edit that comment in place, replacing its body. Nothing about a different state of the change is lost, because the verdict being overwritten is about the same commit.

**No match** means the head has moved, or this is the first review. Publish a new comment.

**Leave every earlier comment exactly as it is.** Do not delete, collapse or rewrite a review of a different commit. Each one was accurate about the state it read, and together they are the record of what this reviewer said at each commit.

## 3. Pick the verdict

One axis: the highest severity present now.

| Findings now | Verdict |
|---|---|
| at least one **blocking** | request changes |
| no blocking, but at least one question or unchecked | comment |
| deferrable only, or nothing at all | approve |

An approval may arrive on the first pass. What makes it worth something is the coverage the body states, so do not approve with a `Not decided` section that names a condition: that is row two.

The row that gets softened is the second. A question looks minor beside a clean diff, and its answer may be a blocking finding.

## 4. Assemble the body

Copy the skeleton in `references/review-body.md` and fill it. The order is fixed — marker, verdict line, counts, findings grouped by severity, then the axes that were not decided — because a reader scanning three reviews should find the same thing in the same place each time.

Two sections carry the weight. Every finding line has its four fields from `docs/review-findings.md`, and a line missing one is dropped rather than published short. And the `unchecked` section is written even when it is empty, with the word that says so, because an absent section reads as full coverage and that is the claim this procedure is built to avoid making.

## 5. Publish once, then set the status

Publish the verdict from step 3 with the body from step 4, as an edit or as a new comment per step 2.

When the verdict is approve and the forge refuses the approving review because the reviewer's account is the author's, publish the same body as a comment. Keep the verdict line as approve and add one sentence saying the forge refused the review and why.

Then set the commit status on the head from step 1, with the comment's `html_url` as the target. The comment goes first because the status needs its URL:

```bash
gh api repos/{owner}/{repo}/statuses/{sha} \
  -f context='argos/verdict' \
  -f state='success' \
  -f target_url='{comment-html-url}' \
  -f description='approve at {short-sha}'
```

`{sha}` is the full head commit the review read (the one the marker abbreviates), never the branch tip now. The context is always `argos/verdict`. Take `html_url` from the create or edit response of the comment (`--jq .html_url`). `{sha}`, `{short-sha}` and `{comment-html-url}` are yours to fill; `gh` fills only `{owner}` and `{repo}`.

| Verdict | `state` |
|---|---|
| approve | `success` |
| request changes | `failure` |
| comment | `failure` |

Comment is `failure` because row two is a review that has not finished, and a check that passed over an unfinished review would let the change through. Keep the description short, for example `request changes at a1b2c3d`.

A re-run on the same commit edits the comment per step 2 and sets the status again on the same sha with the same context. The forge keeps the latest status per context, so the result is one status, not two.

**A new head has no status.** A push after the verdict moves the head, and the forge does not carry statuses to it. Do not copy a status to a new head: the new head has not been reviewed until a review of it publishes its own. That absence is what makes a required `argos/verdict` check block an unreviewed push.

If the status call is refused, for example because the token cannot write statuses, report the refusal in what was published and do not change or withdraw the verdict. A missing status is what makes a required check block, which is the safe direction.

Do not push a fix-up commit, retarget the branch, change a label, assign anyone, request another reviewer, resolve a thread or close the pull request. A reviewer that fixes what it found is reviewing its own work on the next run, and the separation between the two parties is the only thing a second opinion is made of.

Report back what was published: the verdict, the marker, whether an existing comment was edited or a new one created, and the status set on the head or the refusal.

### The ruleset that requires the status

This is shown, not enabled. This procedure never creates or changes a ruleset; turning one on is the repository owner's decision. The body is in [`references/argos-verdict-ruleset.json`](references/argos-verdict-ruleset.json): a `required_status_checks` rule on the default branch whose only required context is `argos/verdict`, with `enforcement` set to `evaluate`. An owner can submit it with `gh api repos/{owner}/{repo}/rulesets --method POST --input ruleset.json`. `evaluate` needs GitHub Enterprise; elsewhere submit with `disabled` and turn it to `active` once checked. Where `evaluate` is available, start there: it records what the ruleset would have blocked without blocking. The status stops an unreviewed push, not a writer who sets the context themselves; closing that is a GitHub App with `integration_id` on the required check, or a ruleset that also requires a named reviewer. Landing does not need the status: where a ruleset requires it the forge holds the merge, and where none does landing proceeds as before.

## 6. Hand an approval to landing

When the verdict is approve, continue with `skills/landing-approved-changes/SKILL.md`, passing the pull request and the head commit from step 1. On any other verdict, stop here.

## When this skill does not apply

**There are no findings and no review was run.** This publishes a verdict; it does not stand in for having reached one. A comment saying nothing was checked is worse than no comment, because it occupies the place a real review would have gone.

**Answering the pull request's other reviewers.** People and other automated reviewers leave threads, and reading, aggregating or replying to them is somebody else's job. This procedure publishes one verdict and leaves every other thread alone.

**A repository that does not require the status.** The status is still set, and harmless; it blocks nothing until a ruleset names `argos/verdict`.

**Merging.** This publishes the verdict. `skills/landing-approved-changes/SKILL.md` lands an approved change, and names the changes it leaves to a person.

**A review published anywhere but a pull request.** A findings list handed back in a terminal, written into a file or sent to a person needs none of this: the marker, the idempotency and the paper trail all exist because the destination keeps a history that outlives the run.
