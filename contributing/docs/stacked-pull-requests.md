---
id: stacked-pull-requests
type: doc
clade: contributing
title: Stacked pull requests
summary: What GitHub's native stacks do, what the first stack in this repository showed, why stacking stays a mode rather than a mandate, and what was dropped when the framework stopped reading stacks from base branches.
references:
  - rules/stacked-pull-requests.md
  - rules/pr-quality.md
  - rules/protected-trunk.md
---

# Stacked pull requests

The reference for `rules/stacked-pull-requests.md`. The rule states what is checked; this states what GitHub's stacks do, and what was measured here.

## A mode, not a mandate

A stack splits one change into layers that are reviewed apart and land in order. Each layer is a pull request based on the layer below it, and the bottom is based on trunk. Some changes want this and most do not. A repository that never stacks loses nothing under these rules.

When a change does want it, the stack is GitHub's own. GitHub shipped stacked pull requests in public preview on 2026-07-30, with the `gh-stack` CLI extension and an agent skill. This repository's `ADR-008` adopts them, superseding `ADR-006`, which read stacks from base branches because the native module was believed not to exist.

## What a GitHub stack is

A stack is an object on the forge. A pull request carries a `stack` field, of GraphQL type `PullRequestStack`, with the stack's number, its base branch, and its entries in order. `gh stack submit` creates it with the pull requests. `gh stack link` creates it around pull requests that already exist, and so does github.com.

Being in a stack is the declaration. There is no flag and nothing to infer: `check-stack` reads the field.

## What the first stack showed

Stack #103, on 2026-09-28, was #97 at the bottom, then #101, then #102. It was made by linking three pull requests that had been opened by hand on top of each other.

**GitHub restacked it.** When #97 merged, GitHub moved #101's base to `main` and rebased it. #101's timeline shows `automatic_base_change_succeeded` and then `head_ref_force_pushed`, and the branch was left holding its own single commit, signed. The manual rebase this framework used to prescribe was never needed. The same happened to #102 when #101 merged.

**Each layer closed its own issue.** #101 closed #98 and #102 closed #99. That had been in doubt. While stacked, both showed an empty `closingIssuesReferences`, even after #101's base had become `main`, and saving the body again did not change it. GitHub lists nothing to close for a layer, and then closes what the body says when the layer merges.

**The layers passed every other check.** `pr-quality`, `traceability` and the rest ran on each layer as on any pull request. #102 was the first pull request judged by `traceability`, and it passed.

## How a stack is merged

From the stack, on github.com or with `gh stack merge <pr> --yes --squash`. Merging a layer from the stack lands it and every unmerged layer below it, in order, all or nothing. The layers above stay open, and GitHub retargets and rebases them.

Not with `gh pr merge` on a layer, and never into a parent's branch. A layer merged into its parent's branch never closes its issue: GitHub closes issues only on merges into the default branch, and the parent's squash is written from the parent's body alone.

## Reviewing a layer

A layer is reviewed against its parent, which is its base. `engineering/skills/reviewing-diffs` step 1 fixes the base as the commit the change merges into. A finding on a line the layer did not touch belongs to the layer that did. After the layer below lands and GitHub rebases this one onto trunk, the diff has changed, and a verdict given before is given again.

## Dropped

**Reading a stack from base branches.** `ADR-006` did it, and it needed an inference, a layer's base must be an open pull request's branch, with an ambiguity the rule had to admit. The `stack` field removes both.

**The manual restack.** `git rebase --onto` past a landed layer, then `gh pr edit --base`. GitHub does both.

**The cycle condition.** A GitHub stack is an ordered list of entries and cannot close into a ring.

**The predecessor's six artifacts and git-spice.** The predecessor carried 1,523 lines of stacking, 321 of them for git-spice, which is refused as maintainer infrastructure (#16). The native module needs nothing the forge does not already provide.

## Where this stops

**The feature is in public preview**, and so is the field this reads. Its behaviour was measured once, on one stack of three, in one repository. Anything above that GitHub changes can change under these rules without warning.

**The forge is GitHub.** Other forges have their own stacking, or none. There, all three conditions report unchecked.
