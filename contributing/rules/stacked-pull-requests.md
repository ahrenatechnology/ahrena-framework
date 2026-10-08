---
id: stacked-pull-requests
type: rule
clade: contributing
title: A stack is native where it can be, and lands on trunk
statement: A pull request not based on trunk is a layer of a stack, native where the forge has them, the stack lands on trunk, and nothing already landed rides along.
enforcement: hook
enforced-by: hooks/check-stack.py
enforced-in: forge
references:
  - docs/stacked-pull-requests.md
---

# A stack is native where it can be, and lands on trunk

Three conditions, all decided by `hooks/check-stack.py` and all read from the forge, so without a token each is reported unchecked rather than failed. [`docs/stacked-pull-requests.md`](../docs/stacked-pull-requests.md) says what native stacks do, what the first stack here showed, and how the framework runs a stack where the forge cannot.

There are two kinds of stack, and this repository's `ADR-008` records why. Where the forge has native stacks, as GitHub has since 2026-07-30, a stack is the forge's own object, and putting pull requests in one is the declaration. Where the forge has none, the framework runs the stack itself: a stack is the chain of base branches, and `skills/stacking-pull-requests` does the restacking the forge would have done. Which kind applies is read from the forge's schema, never configured. A pull request against trunk and in no stack is an ordinary pull request, and conditions 1 and 2 do not reach it.

## Conditions

Each of these is decided by `hooks/check-stack.py`.

1. **A pull request whose base is not trunk is a layer of a stack.** On a forge with native stacks, its `stack` field is set; a pull request off trunk and in no stack either has a wrong base or is a hand-made chain, which `gh stack link <bottom> ... <top>` turns into a stack. On a forge without them, its base is the branch of an open pull request. It fails with a name for each way it can be wrong. The parent landed, and this layer must be restacked onto trunk and retargeted. The parent was closed without merging. Or the base belongs to no pull request, so the base is wrong.

2. **The stack lands on trunk.** A native stack's base is trunk. A framework-run stack's chain of bases reaches trunk without returning to a branch it already passed, since a cycle is a set of layers each waiting on another. A stack that lands anywhere else lands nothing on trunk, and `protected-trunk.md` guards a branch the work never reaches.

3. **No commit in the pull request already landed with another pull request.** Checked on every pull request, stacked or not. GitHub keeps a commit associated with the pull request it landed in, even after a squash, so a pull request still carrying one fails, and the finding names where it came from. In a native stack this should never fire, because the forge rebases the layers above a merge. In a framework-run stack it is the signal that the restack is due.

## Where this stops

**Native stacks are in preview.** GitHub's stacks, the `gh stack` commands and the `stack` field are not called stable. A change to the field makes conditions 1 and 2 report unchecked rather than fail, because a GraphQL error is the forge not answering. The framework-run path does not depend on the field.

**The detector reads GitHub's API on both paths.** On a forge that does not speak it, all three conditions are unchecked, and the skill is what still runs: the agent follows the framework-run path with that forge's own CLI.

**How to decompose a change into layers is not here.** When one change should become several, and in what order, is the plan's question. `ADR-011` makes each unit its own sub-issue, and `skills/planning-changes` owns the decomposition checklist.

**Nothing here orders the merges, but one way of merging costs an issue.** Each layer lands on trunk through its own merge, native stacks from the stack, framework-run stacks bottom first. A layer merged into its parent's branch instead never closes its issue. GitHub closes an issue from a pull request only on a merge into the default branch, and the parent's squash is written from the parent's body alone.

**A layer shows nothing to close until it lands.** Measured on stack #103: #101 and #102 had an empty `closingIssuesReferences` while stacked, even after #101's base became `main`. Each still closed its own issue when it merged. `traceability.md` reads what a pull request closes from its body for that reason.

**The review of a layer is not here.** Reviewing a layer against its parent rather than trunk is step 1 of `engineering/fundamentals/skills/reviewing-diffs`.
