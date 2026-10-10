---
name: landing-approved-changes
description: Use when a review has just published an approve verdict on a pull request and the change should reach trunk. Checks the four cases a person lands, reads the checks on the reviewed commit, and asks the forge to squash-merge that commit and no other.
type: skill
clade: engineering
subclade: quality
references:
  - docs/review-verdicts.md
  - skills/publishing-review-verdicts/SKILL.md
---

# Landing approved changes

An approved pull request is merged by the forge, by squash, at the commit the review read. This procedure asks for that merge and does nothing else to the pull request. `docs/review-verdicts.md` says what the approval asserts, and this repository's `ADR-013` records why a review lands a change.

## 1. Confirm the verdict is for this head

Read the pull request's head now and compare it with the commit in the marker of the review just published.

```sh
gh pr view 142 --json headRefOid,isDraft,baseRefName,isCrossRepository,files
```

When the head has moved, stop. The approval is for a commit that is no longer the tip, and the new one has not been read. Say so and name both commits.

When the published verdict is anything but approve, stop. This procedure does not run on a comment or a request for changes.

## 2. Leave four kinds of change to a person

Check each against the output of step 1, and stop on the first that holds, naming it.

| The pull request | Why a person lands it |
|---|---|
| is a draft | its author has not asked for it to land |
| has a base that is not trunk | it is a layer of a stack, and the stack's order is the plan's |
| has a head in another repository | an external fork's checkout was never executed, so its review carries unchecked conditions |
| touches a decision record | no condition decides whether a decision is right |

A decision record is a file under `docs/adr/`, or under the directory the repository's own documents name for its records.

The failure that recurs here is treating a stack's bottom layer as an ordinary pull request because its base is trunk. A pull request that another open pull request is based on is a layer, and it is left too.

## 3. Read the checks on the reviewed commit

```sh
gh pr checks 142
```

Land only when every check has completed and passed. A failing check stops the procedure. A pending check stops it too: say which, and that the procedure can be run again when it finishes.

Do not ask the forge to merge automatically when the checks pass. On a repository whose ruleset does not require the checks, that request merges at once, over the pending run.

A pull request with no checks at all has no gate 2 trace. Stop and say so.

## 4. Ask the forge to merge the reviewed commit

```sh
gh pr merge 142 --squash --match-head-commit a1b2c3d4e5f60718293a4b5c6d7e8f9012345678
```

The full hash is the head from step 1. With it the forge refuses the merge if a commit arrived in between, which is the case step 1 cannot close on its own.

Use this command and no stronger one. No administrator override, no merge commit, no rebase, no push to trunk. The squash's subject and body come from the pull request, as the repository's settings write them.

A refusal stands. The forge refuses when the ruleset requires an approving review the pull request lacks, when the branch conflicts, or when a required check is missing. The platform running this procedure may refuse the command itself. In each case report the refusal as it was printed and stop; the pull request waits for a person.

## 5. Report

Say what happened: the commit that landed on trunk and the issue it closed, or the step that stopped the procedure and why. Do not delete the branch, edit the issue or open a follow-up from here.

## When this skill does not apply

**A stack.** `contributing/skills/stacking-pull-requests` lands a stack layer by layer, and a person runs it.

**A pull request this review did not approve.** A person's approval, or another reviewer's, does not start this procedure.

**The author's own session.** An agent that wrote a change does not land it. This runs from the review.

**A merge that failed after landing.** A red run on trunk is answered with a revert through a pull request, not from here.
