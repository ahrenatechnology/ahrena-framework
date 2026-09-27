---
id: stacked-pull-requests
type: rule
clade: contributing
title: A stack is a chain of open pull requests
statement: A pull request not based on trunk sits on an open pull request's branch, its bases reach trunk, and no pull request carries commits that already landed.
enforcement: hook
enforced-by: hooks/check-stack.py
enforced-in: forge
references:
  - docs/stacked-pull-requests.md
---

# A stack is a chain of open pull requests

Three conditions, all decided by `hooks/check-stack.py` and all read from the forge, so without a token each is reported unchecked rather than failed. [`docs/stacked-pull-requests.md`](../docs/stacked-pull-requests.md) says why stacking is a mode rather than a mandate, and how a stack lands under a squash-only trunk.

A stack is not declared anywhere. It is read from what GitHub already records: a pull request whose base is another pull request's branch. That is the chain every stacking tool produces, and the one a person produces by hand with `gh pr create --base`. No tool is assumed and none is required. A pull request against trunk is not a stack of one, and conditions 1 and 2 do not reach it.

## Conditions

Each of these is decided by `hooks/check-stack.py`.

1. **A pull request whose base is not trunk is based on the branch of an open pull request in this repository.** That is what tells a layer of a stack from a pull request opened against the wrong base, which is otherwise the same shape. The condition fails three ways and names each. The base is the branch of a pull request that has already landed, so this one must be retargeted to trunk and restacked. The base is the branch of a pull request closed without merging, so this one sits on abandoned work. Or the base is the branch of no pull request at all, and this is a wrong base, not a stack.

2. **The chain of bases reaches trunk.** Following each layer's base to the open pull request whose branch it is ends at trunk. A chain that returns to a branch it has already passed is a cycle. Every layer in it waits for a parent that waits for it, and none of them can land. A chain that breaks before trunk is condition 1's failure at the layer where it breaks.

3. **No commit in the pull request already landed with another pull request.** Checked on every pull request, stacked or not, because this is the failure a squash-only trunk produces. When the bottom of a stack lands, trunk receives one new squash commit. The next layer's branch still holds the bottom's original commits, and GitHub keeps each of them associated with the pull request that landed. A pull request carrying any such commit fails and names the pull request they came from. The fix is to rebase past them onto trunk.

## Where this stops

**No flag turns this on.** A stack is detected from its bases, as the owner decided on #58. The cost is that a wrong base and a stack are told apart only by condition 1, and a branch that happens to be the head of an unrelated open pull request would read as a parent. That branch would still have to be named for its own issue under `branch-naming.md`, which makes the accident unlikely and not impossible.

**How to decompose a change into layers is not here.** When one change should become several, and in what order, is the plan's question, and `ADR-004` gives the plan its own sub-issue. The planning rule that issue-driven development builds (#45) owns the decomposition checklist; this rule governs the stack once the layers exist.

**Nothing here orders the merges.** A layer can be merged into its parent's branch, collapsing the two, and that is allowed. Under a squash-only forge the collapse is one squash commit on the parent's branch, so condition 3 does not see the child's commits in the parent afterwards. A middle layer cannot land on trunk before the bottom, and no rule is needed to say so: merging it lands it on its parent's branch, because that is its base.

**A merged pull request's commits are read from the forge's association, not from the tree.** A commit rewritten locally, by a rebase that changes its content, is a new commit with no association, and condition 3 does not flag it even if it repeats what landed. The rebase that condition 3 asks for produces exactly such commits, which is why it stops failing afterwards.

**The review of a stack is not here.** Reviewing a layer against its parent rather than trunk is step 1 of `engineering/skills/reviewing-diffs`, and the reviewer reads that there.
