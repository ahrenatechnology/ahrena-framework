---
id: gates
type: rule
clade: contributing
title: Two gates, and a review lands the change
statement: An agent starts an issue only when asked, asks for review only after the quality gate passes, and lands a change only after a review approved it.
enforcement: judgment
references:
  - docs/issue-driven-flow.md
---

# Two gates, and a review lands the change

Three conditions, all read by a person. [`docs/issue-driven-flow.md`](../docs/issue-driven-flow.md) places them in the flow from issue to trunk, and this repository's `ADR-013` records why none of them is a hook.

The flow has two gates. Gate 1 is scope, a person's approval of what will be built. Gate 2 is quality, the checks. Landing on trunk is a third point: the forge lands a change a review approved, and a person lands the rest.

## Conditions

1. **An agent starts work on an issue only when a person asked for it.** The request names the issue, or the plan the issue belongs to. Its criteria are what the person approved, and a change that needs criteria the issue does not have goes back to the person before it is built. Starting is recorded by the assignment `opening-issues` makes when the branch is created. That assignment records that someone started, not that anyone approved.

2. **A pull request asks for review only after the quality gate has passed, and it shows the output.** `skills/running-the-quality-gate` runs the checks CI will run and the forge-tier checks against the pull request. A check is claimed as passing only with the output of the run that shows it. "Tests pass" is not a result; the line the runner printed is. When a check fails, its finding already names the fix, as #27 asks every gate to do, and the author applies it and runs the gate again. CI then runs every check again, and the CI run is the trace.

3. **An agent lands a change only through the forge, and only after a review approved it.** Argos, having approved a pull request, asks the forge to merge by squash the commit it reviewed, once every check on that commit has passed. `engineering/fundamentals/skills/landing-approved-changes` is the procedure. No agent merges any other way: the author of a change does not land it, nothing is merged over a pending or red check, and no ruleset is bypassed. A person lands a pull request that touches a decision record, a layer of a stack, a draft, and a pull request from an external fork.

## Where this stops

**None of this is visible on the forge while identities are shared.** On a shared account the forge records the same login for the person and the agent, so an approval, a merge and a claim of having run the checks all look alike. The one exception is condition 2's second half: the CI run is produced by the workflow, not by the agent, and it is the only gate trace an agent cannot write. Giving agents their own identity, a GitHub App or a machine account, would make conditions 1 and 3 checkable. `ADR-013` records it as the direction and does not require it.

**Gate 2 is only as strong as the ruleset.** If the ruleset on trunk does not require the checks, a person can land a pull request with a red run. Whether it does is an owner's setting. The landing procedure reads the checks itself for that reason, and does not rely on the ruleset to hold a red run.

**A review that approves is not a second person.** Argos through `engineering/fundamentals/skills/reviewing-diffs` reads the change against conditions, and what no condition is about it does not see. Whether the feature was wanted is gate 1's question and was answered there. A repository that needs a named person on every merge says so in its ruleset, and the forge then refuses the merge until that person approves.

**Asking is not approving everything that follows.** A person who asks for issue #N has approved #N's criteria. Work the issue does not describe, found along the way, is a new issue, opened with `opening-issues` and started only when asked for.
