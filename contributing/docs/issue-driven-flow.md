---
id: issue-driven-flow
type: doc
clade: contributing
title: The issue-driven flow
summary: The path from an issue to trunk, which rule and skill governs each step, where the two gates sit, and what came across from the predecessor's seven phases.
references:
  - rules/gates.md
  - rules/issue-quality.md
  - rules/traceability.md
  - rules/pr-quality.md
  - rules/protected-trunk.md
  - rules/stacked-pull-requests.md
  - rules/planning.md
---

# The issue-driven flow

Every change in a repository that adopts this plugin runs the same path. This doc states it once and names what governs each step. The rules decide; this only puts them in order.

## The path

| Step | What happens | Governed by |
|---|---|---|
| 1. Issue | Find the issue that owns the work, or open one with evidence, criteria and what it leaves to others | `issue-quality.md`, `skills/opening-issues`, `skills/writing-acceptance-criteria` |
| **Gate 1** | **A person asks for the issue to be worked. Its criteria are what they approved** | `gates.md` condition 1 |
| 2. Plan | When the change is more than one pull request: its units as sub-issues, ordered by the forge's `blocked by`, and a stack when they land in that order | `planning.md`, `skills/planning-changes`, `stacked-pull-requests.md` |
| 3. Branch | Created from the issue, `type/N-slug`, and the author takes ownership | `branch-naming.md`, `skills/opening-issues` step 5 |
| 4. Build | Commits that pass `commit-format.md`; tests that name the criteria they cover | `commit-format.md`, `skills/writing-acceptance-criteria` step 5 |
| **Gate 2** | **Every check runs and passes, with its output shown** | `gates.md` condition 2, `skills/running-the-quality-gate` |
| 5. Pull request | Names its issue, closes it with its own keyword, and has a title trunk can take | `pr-quality.md`, `traceability.md` |
| 6. Review | Findings on the change, answered by the author, and a verdict | `engineering/fundamentals/skills/reviewing-diffs` |
| **Landing** | **The forge merges a pull request the review approved, once its checks pass. A person merges a decision record, a stack, a draft and a fork. The squash is written from the title and body, and closes the issue** | `gates.md` condition 3, `protected-trunk.md` |

CI runs every check again on step 5, and again on trunk after landing. The CI run is gate 2's trace, and the red run on trunk is how a landing that should not have happened is found.

## Why two gates and not seven phases

The predecessor ran seven phases: brief, requirements, architecture, implementation, security review, quality gate and pull request. Each wrote a file under `.ahrena/issues/{n}/`, and a checkpoint file tracked which phase the work was in.

What came across is the two gates and the properties inside the phases:

- **Scope before building.** The predecessor's Gate 1 approved the design and the criteria before implementation. Here the criteria live in the issue (`ADR-007`), and gate 1 is a person asking for it to be worked.
- **Checks before review, and no claim without a run.** The predecessor's Gate 2 was a go or no-go on seven checks, and its rule that a gate item may not be marked met without the verification being run is kept. Here the checks are the detectors, and CI is the trace.
- **Criteria traced to tests, both ways.** The predecessor's check 1 is `traceability.md`.

What did not come across is the phase files and the checkpoint. A brief, a requirements document and a quality report written by the agent into the repository are claims the agent makes about its own work. The issue already holds the criteria, the pull request holds the change, and CI holds the result, each where the party that did not write it can read it.

## Where this stops

**The flow is not enforced as a sequence.** Each step's rule enforces that step. Nothing checks that step 3 came after gate 1, and on a shared account nothing could. `gates.md` says what the agent owes instead.

**Security review and architecture are not steps here.** The predecessor had a phase for each. Here they are what a review reads for, through the engineering plugin's rules, and what a decision record captures when a decision is made. A step of their own would be a file to fill, and the property worth having is that the decision is written down, which `contributing/rules/decision-records.md` already governs.
