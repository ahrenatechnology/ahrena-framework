---
id: stacked-pull-requests
type: doc
clade: contributing
title: Stacked pull requests
summary: What native stacks do, what the first stack in this repository showed, how the framework runs a stack where the forge has none, and why stacking stays a mode rather than a mandate.
references:
  - rules/stacked-pull-requests.md
  - rules/pr-quality.md
  - rules/protected-trunk.md
---

# Stacked pull requests

The reference for `rules/stacked-pull-requests.md`. The rule states what is checked; this states what GitHub's stacks do, and what was measured here.

## A mode, not a mandate

A stack splits one change into layers that are reviewed apart and land in order. Each layer is a pull request based on the layer below it, and the bottom is based on trunk. Some changes want this and most do not. A repository that never stacks loses nothing under these rules.

When a change does want it, the stack is the forge's own wherever the forge has one. GitHub shipped stacked pull requests in public preview on 2026-07-30, with the `gh-stack` CLI extension and an agent skill. Where the forge has none, the framework runs the stack itself. This repository's `ADR-008` records both, superseding `ADR-006`, which knew only the second because the native module was believed not to exist.

## What a native stack is

A stack is an object on the forge. A pull request carries a `stack` field, of GraphQL type `PullRequestStack`, with the stack's number, its base branch, and its entries in order. `gh stack submit` creates it with the pull requests. `gh stack link` creates it around pull requests that already exist, and so does github.com.

Being in a stack is the declaration. There is no flag and nothing to infer: `check-stack` reads the field. Whether the field exists at all is read from the forge's schema, so a GitHub Enterprise host without the feature is on the other path with nothing to set.

## What the first stack showed

Stack #103, on 2026-09-28, was #97 at the bottom, then #101, then #102. It was made by linking three pull requests that had been opened by hand on top of each other.

**GitHub restacked it.** When #97 merged, GitHub moved #101's base to `main` and rebased it. #101's timeline shows `automatic_base_change_succeeded` and then `head_ref_force_pushed`, and the branch was left holding its own single commit, signed. The manual rebase this framework used to prescribe was never needed. The same happened to #102 when #101 merged.

**Each layer closed its own issue.** #101 closed #98 and #102 closed #99. That had been in doubt. While stacked, both showed an empty `closingIssuesReferences`, even after #101's base had become `main`, and saving the body again did not change it. GitHub lists nothing to close for a layer, and then closes what the body says when the layer merges.

**The layers passed every other check.** `pr-quality`, `traceability` and the rest ran on each layer as on any pull request. #102 was the first pull request judged by `traceability`, and it passed.

## How a stack is merged

From the stack, on github.com or with `gh stack merge <pr> --yes --squash`. Merging a layer from the stack lands it and every unmerged layer below it, in order, all or nothing. The layers above stay open, and GitHub retargets and rebases them.

Or one layer at a time, each only once its own checks are green, which is how stack 110 of `barte-ai-services/barte-ai-platform-monkey` landed on 2026-09-29, thirteen layers with merge commits. `gh pr merge` refuses a stacked layer, saying it must be merged using the asynchronous merge REST API. That API answers the `PUT` with `pending` and an id in `details.uuid`, and the merge's real outcome is read from the status under that id: a merge the branch rules refuse comes back `failed` there, with the forge's reason. Its admin override is `bypass_rules=true`. `skills/stacking-pull-requests` ships the script that does this.

Not with `gh pr merge` on a layer, and never into a parent's branch. A layer merged into its parent's branch never closes its issue: GitHub closes issues only on merges into the default branch, and the parent's squash is written from the parent's body alone.

## Where the forge has no native stacks

The framework runs the stack itself, and an agent following `skills/stacking-pull-requests` does what the forge would have done. A stack is then the chain of base branches: each layer is opened against the branch of the layer below, and the bottom against trunk. `check-stack` holds each layer's base to the branch of an open pull request, and the chain to trunk.

The restack is the step a native stack spares. Before anything lands:

```
main ── A1 ── A2          #80  feat/1-bottom  base main
               └── B1     #81  feat/2-top     base feat/1-bottom
```

#80 lands as one squash commit `S`. `feat/2-top` still holds A1 and A2 as they were, so #81's diff shows them again. `check-stack` condition 3 fails #81 and names #80 as their source. The agent rebases past them and moves the base:

```sh
git rebase --onto origin/main <tip-of-feat/1-bottom> feat/2-top
git push --force-with-lease
gh pr edit 81 --base main
```

Then #81 is the bottom, and the same steps repeat up the stack. With `delete_branch_on_merge` on, GitHub moves the base itself when the landed branch is deleted, and only the rebase is left.

## Reviewing a layer

A layer is reviewed against its parent, which is its base. `engineering/skills/reviewing-diffs` step 1 fixes the base as the commit the change merges into. A finding on a line the layer did not touch belongs to the layer that did. After the layer below lands and GitHub rebases this one onto trunk, the diff has changed, and a verdict given before is given again.

## Dropped

**Reading base branches where the forge has native stacks.** `ADR-006` did it everywhere, with an inference and an ambiguity the rule had to admit. Where the `stack` field exists, it replaces both, and the inference is kept only for forges without one.

**The predecessor's six artifacts and git-spice.** The predecessor carried 1,523 lines of stacking, 321 of them for git-spice, which is refused as maintainer infrastructure (#16). The native module needs nothing the forge does not already provide.

## Where this stops

**The feature is in public preview**, and so is the field this reads. Its behaviour was measured once, on one stack of three, in one repository. Anything above that GitHub changes can change under these rules without warning.

**The detector is GitHub's.** It reads GitHub's API on both paths. On a forge that does not speak it, all three conditions report unchecked, and the skill's framework-run path is what still works, with that forge's own CLI.
