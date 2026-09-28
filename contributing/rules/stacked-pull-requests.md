---
id: stacked-pull-requests
type: rule
clade: contributing
title: A stack is a GitHub stack on trunk
statement: A pull request not based on trunk is a layer of a GitHub stack, that stack lands on trunk, and no pull request carries commits that already landed.
enforcement: hook
enforced-by: hooks/check-stack.py
enforced-in: forge
references:
  - docs/stacked-pull-requests.md
---

# A stack is a GitHub stack on trunk

Three conditions, all decided by `hooks/check-stack.py` and all read from the forge, so without a token each is reported unchecked rather than failed. [`docs/stacked-pull-requests.md`](../docs/stacked-pull-requests.md) says what GitHub's stacks do, what was measured on the first one here, and why stacking stays optional.

A stack is GitHub's own object, made with `gh stack` or on github.com. This repository's `ADR-008` records the choice, and why it replaced reading stacks from base branches. Putting pull requests in a stack is the declaration; there is no other flag. A pull request against trunk and in no stack is an ordinary pull request, and conditions 1 and 2 do not reach it.

## Conditions

Each of these is decided by `hooks/check-stack.py`.

1. **A pull request whose base is not trunk is a layer of a GitHub stack.** Its `stack` field is set. A pull request off trunk and in no stack is either opened against the wrong base, or a chain of branches built by hand, which `gh stack link <bottom> ... <top>` turns into a stack. The finding says both.

2. **The stack is based on trunk.** Merging a stack lands its layers on the stack's base. A stack based on any other branch lands nothing on trunk, and `protected-trunk.md` is then guarding a branch the work never reaches.

3. **No commit in the pull request already landed with another pull request.** Checked on every pull request, stacked or not. When a layer merges, GitHub rebases the layers above it, so inside a stack this should never fire. It catches a branch rebased by hand past the rebase GitHub did, and a pull request built on work that landed without being stacked. GitHub keeps a commit associated with the pull request it landed in, even after a squash. So a pull request still carrying such a commit fails, and the finding names where the commit came from.

## Where this stops

**The feature is in public preview.** GitHub's stacks, the `gh stack` commands and the `stack` field this reads are not called stable. A change to the field makes condition 1 and 2 report unchecked rather than fail, because a GraphQL error is the forge not answering. That is honest, and it also means a breaking change is only seen by someone reading the output.

**How to decompose a change into layers is not here.** When one change should become several, and in what order, is the plan's question, and `ADR-004` gives the plan its own sub-issue. The planning work of issue-driven development (#93) owns the decomposition checklist; this rule governs the stack once the layers exist.

**Nothing here orders the merges, because the stack does.** Merging from the stack lands a layer and every unmerged layer below it, in order, in one operation. What the stack does not stop is `gh pr merge` on one layer, or a layer merged into its parent's branch. The second one has a cost the author has to know. GitHub closes an issue from a pull request only when it merges into the default branch. A layer merged into its parent never closes its issue, and the parent's squash is written from the parent's body alone. Merge through the stack.

**A layer shows nothing to close until it lands.** Measured on stack #103: #101 and #102 had an empty `closingIssuesReferences` while stacked, even after #101's base became `main`. Each still closed its own issue when it merged, #98 and #99. `traceability.md` reads what a pull request closes from its body for that reason.

**The review of a layer is not here.** Reviewing a layer against its parent rather than trunk is step 1 of `engineering/skills/reviewing-diffs`.
