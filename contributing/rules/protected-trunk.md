---
id: protected-trunk
type: rule
clade: contributing
title: Only a pull request reaches trunk
statement: Trunk is written only by a pull request's squash, and the forge is configured so that nothing else can reach it.
enforcement: hook
enforced-by: hooks/check-trunk.py
enforced-in: forge
references:
  - docs/pull-requests-and-trunk.md
---

# Only a pull request reaches trunk

Three conditions, all decided by `hooks/check-trunk.py` and all read from the forge, so without a token each is reported unchecked rather than failed. [`docs/pull-requests-and-trunk.md`](../docs/pull-requests-and-trunk.md) carries the measurements.

`ADR-001` decided that a pull request lands on trunk as a squash. A decision the forge does not enforce is a preference. This repository proved it the day after the record was accepted: the setting still offered all three merge methods, and #74, #77 and #78 reached trunk by rebase, unsigned and without the ` (#N)` a squash writes. Two of the conditions below are therefore about the forge's configuration rather than about any commit. They fail until an owner changes a setting, and the failure is the point.

## Conditions

Each of these is decided by `hooks/check-trunk.py`.

1. **The forge merges by squash only, and writes the squash from the pull request's title and body.** `allow_squash_merge` is on, `allow_rebase_merge` and `allow_merge_commit` are off, `squash_merge_commit_title` is `PR_TITLE` and `squash_merge_commit_message` is `PR_BODY`. The title setting makes the title the subject trunk receives, so `pr-quality.md` condition 3 checks the subject that actually lands. Without it, a single-commit pull request lands under its commit's subject instead. The body setting matters more. GitHub closes an issue when a closing keyword lands on trunk in any commit message. A squash assembled from the branch's commit messages carries every keyword those commits contain. `pr-quality.md` reads the body, so the body must be the only text that lands. `75481ca`, the squash of #79, closed #45 from a commit message that read "when it closed #45". `ADR-001` already said the message is "written for trunk rather than assembled from the branch's", and this setting is how the forge holds to that. If the token cannot see these fields, the condition is unchecked.

2. **Something on the forge requires a pull request to reach trunk.** A ruleset active on the trunk branch carries a `pull_request` rule. Rulesets are readable with the default token. Classic branch protection is not: only an admin token can read what it requires. So a trunk under classic protection is reported unchecked rather than guessed at, and a trunk under neither fails.

3. **Every commit a push adds to trunk is the squash of a merged pull request.** Decided on a push to trunk, over the first-parent commits the push added. Each subject ends in ` (#N)`, and pull request N's merge commit is that commit. A direct push, a rebase merge and a merge commit all fail. On a pull-request event nothing has reached trunk yet, and the condition has nothing to decide.

## Where this stops

**A fork keeps the merge commit.** A fork syncs its parent through a merge commit, because a squash leaves the merge base where it was, and every later sync then conflicts on the same lines again. Where the repository declares its parent in `PARENT_REPOSITORY`, condition 1 leaves `allow_merge_commit` undecided and holds every other setting. Condition 3 also accepts the merge commit of a merged pull request, which GitHub writes as `Merge pull request #N from …`. The forge cannot tell a sync from any other pull request, so the choice of method is left to review. This repository's `ADR-010` records the decision.

**Condition 3 detects; conditions 1 and 2 prevent.** A push that fails condition 3 is already on trunk, and the red run on trunk is how anybody learns of it. That is why the configuration is checked on every event: with conditions 1 and 2 passing, the only way to fail condition 3 is to bypass a ruleset, and that leaves a trace on the forge too.

**Condition 3 judges what a push adds, never the history.** The rebase-merged commits already on trunk cannot be re-made as squashes without rewriting trunk, and a condition that fails forever on them fails correct work from then on. The history is measured in the doc and left alone.

**Condition 1 may be unchecked in CI, and that is recorded rather than hidden.** The merge settings are fields of the repository resource, and whether the default `GITHUB_TOKEN` is shown them was not verified before this rule shipped. If it is not, condition 1 prints unchecked in every run, and the setting is still an owner's to make.

**Nothing here requires a pull request's base to be trunk.** A stacked pull request's base is another pull request's branch, and it reaches trunk only when the bottom of the stack does, by the same squash. The stack is `stacked-pull-requests.md`'s.

**The bypass list is not read.** A ruleset can let an admin push past it. Whether that list is right is an owner's call, and condition 3 is what catches it being used.
