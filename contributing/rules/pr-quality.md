---
id: pr-quality
type: rule
clade: contributing
title: What a pull request carries
statement: A pull request names its branch's issue, closes each issue with its own keyword and nothing it does not name, and has a title trunk can take as a subject.
enforcement: hook
enforced-by: hooks/check-pull-request.py
enforced-in: forge
references:
  - docs/pull-requests-and-trunk.md
---

# What a pull request carries

Five conditions, all decided by `hooks/check-pull-request.py`. The first three read the pull request as the event describes it; the last two ask the forge, so without a token they are reported unchecked rather than failed. [`docs/pull-requests-and-trunk.md`](../docs/pull-requests-and-trunk.md) carries the measurements behind each one and the conditions that were left out.

A pull request is the one place where an issue, a branch and the commit that lands on trunk are all in view at once. Every condition here is a link between two of them that was written wrong in this repository and failed silently.

## Conditions

Each of these is decided by `hooks/check-pull-request.py`.

The body is read as GitHub reads it. Fenced code, inline code and HTML comments carry no references and close nothing, so a body quoting `Closes #4, #5` as an example is not held to it.

1. **The body names the issue the branch carries.** A branch named `feat/39-issue-pr-trunk-rules` answers #39, and the body writes `#39` somewhere, as `Closes #39` when the merge finishes it or `Part of #39` when it does not. `owner/name#39` counts when it names this repository. The branch name ties the branch to the issue for a machine; the body is where a reviewer reads the tie. A branch with no number is `branch-naming.md`'s failure, and this condition does not report it a second time.

2. **A closing keyword is followed by one issue, not a list.** GitHub reads `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves` and `resolved` in any case, with an optional colon, and binds the keyword to the single reference that follows it. `Closes #4, #5, #6` closes #4. A comma, an `and` or an `&` followed by another reference is the list, and it fails. Each issue gets its own keyword.

3. **The title fits trunk as the squash commit's subject.** Trunk receives a pull request as one squash commit, titled from the pull request (`ADR-001`, and condition 1 of `protected-trunk.md`), and GitHub appends ` (#N)`. So the title is held to `commit-format.md`'s subject conditions 1, 2 and 4, read from that rule's own hook rather than restated, and to its 72-character cap after the suffix is added. A title has 66 characters on a two-digit pull request and 65 on a three-digit one.

4. **Every issue the body closes exists, is an issue, and is open.** A closing keyword pointing at a number that does not exist, at a pull request, or at an issue already closed closes nothing, and says it does. Decided through the REST API.

5. **Every issue the merge will close is one the body closes.** GitHub closes more than the body says. An issue linked from the pull request's sidebar, or linked to the branch because it was created with `gh issue develop`, is closed on merge whatever the body reads. The forge lists what it will close as `closingIssuesReferences`; anything on that list the body does not close with a keyword fails. Decided through the GraphQL API.

## Where this stops

**Conditions 4 and 5 are unchecked on a checkout with no token, and that is the design.** The forge tier, recorded as `ADR-002`, reports a condition it could not ask about as unchecked rather than failed. Offline, conditions 1 to 3 are still decided, because the event carries the title, the body and the branch.

**Conditions 4 and 5 are judged when CI runs, not at the moment of merge.** An issue closed by somebody else after the last run passes condition 4 and is closed again by the merge, harmlessly. A link added in the sidebar after the last run escapes condition 5 until the pull request is next touched. The workflow reruns the check when the body is edited, which is when a body's claims change; a sidebar edit fires no event the workflow listens to.

**Nothing here checks labels.** A size label that matches the diff, and exactly one state label from a closed axis, are both detectable and both left out. The state vocabulary is configuration each consuming project owns (#22), so the framework cannot name the labels, and a condition over labels nobody has defined is a detector that does not exist.

**Nothing here reads the body for substance.** A body that names the right issue, closes it correctly and describes a different change passes every condition. Whether the description matches the diff, whether the verification section shows anything was verified, and whether the pull request is one change are the reviewer's questions, and `docs/pull-requests-and-trunk.md` states them where a condition would have been.

**A stacked pull request is not special here.** Its base is another pull request's branch rather than trunk, and no condition reads the base. The stack itself is #58's.

**Most of this repository's pull requests before this rule would fail it.** The measurements are in the doc, including three of the conditions failing on pull requests opened the same week the rule was written. The rule changes the practice rather than describing it.
