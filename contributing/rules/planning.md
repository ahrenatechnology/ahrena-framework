---
id: planning
type: rule
clade: contributing
title: A plan closes when its units have, and in order
statement: A pull request does not close an issue with open sub-issues, nor one blocked by an open issue unless it is a layer of a stack.
enforcement: hook
enforced-by: hooks/check-plan.py
enforced-in: forge
references:
  - docs/issue-driven-flow.md
---

# A plan closes when its units have, and in order

Two conditions, decided by `hooks/check-plan.py` from the forge. Without a token, or on a forge whose schema has no sub-issues or dependencies, both are reported unchecked rather than failed.

A plan is the issue it plans, with its units as sub-issues, each answered by one pull request. The order between the units is the forge's native `blocked by`. This repository's `ADR-011` records the model. `skills/planning-changes` makes a plan: when one is needed, how to split the change, and how to order the units. This rule holds the two properties of a plan a script can decide.

## Conditions

Each of these is decided by `hooks/check-plan.py`, over every issue the pull request closes, read the way `traceability.md` reads them.

1. **No issue the pull request closes has an open sub-issue.** A plan is done when its units are. A pull request that closes the parent while a unit is open ends the plan early, and the open unit becomes work nobody is tracking toward anything. The parent is closed by hand when its last unit closes. A pull request that belongs to a plan without finishing it says `Part of #<parent>`, which closes nothing.

2. **No issue the pull request closes is blocked by an open issue, unless the pull request is a layer of a stack.** A unit's `blocked by` says what must land first. Closing the unit before its blocker lands inverts the order the plan agreed. A layer of a stack is exempt, because the stack already holds its order: its base is the layer below, and it cannot land before it.

## Where this stops

**Only closing is checked.** Opening a unit early, starting work on it, or pushing its branch before its blocker lands are all allowed. Work in parallel is fine. What the rule protects is the order things are declared done.

**The plan's shape is not checked.** Whether a change that needed a plan got one, whether the units are the right units, and whether the order is the right order are the reader's to judge, with `skills/planning-changes` as the checklist. A single issue with no sub-issues passes both conditions, and it should: most changes are one pull request.

**A dependency the forge does not hold is invisible here.** Order written only in prose, in a body or a comment, is not read. On a forge without native dependencies, the parent's `## Plan` section holds the order, and keeping to it is the agent's, not this check's.

**The exemption for a layer trusts the stack.** A layer based on its parent's branch, or in a native stack, is not held to condition 2. A stack whose layers are in the wrong order passes, and `stacked-pull-requests.md` does not read issue dependencies either. The order of layers is decided when the plan is made, and a reviewer reads it then.
