---
id: issue-quality
type: rule
clade: contributing
title: What an issue carries
statement: An issue states what is wrong or missing with the evidence for it, what done looks like, and what it leaves to other issues.
enforcement: judgment
references:
  - docs/pull-requests-and-trunk.md
---

# What an issue carries

Three conditions, all read by a person. [`docs/pull-requests-and-trunk.md`](../docs/pull-requests-and-trunk.md) says why none of them is a hook.

An issue is where work starts. `branch-naming.md` makes a branch carry the number of one, and `pr-quality.md` makes the pull request name it and close it correctly. Both check that the link exists. Neither can check that what it links to is worth linking to, and that is this rule.

## Conditions

1. **It states what is wrong or missing, with the evidence for it.** A measurement, a reproduction, a link to the failing run, the line that is wrong. #39 opens with "this session opened 5 pull requests and 3 of them had no issue behind them", and that sentence is what made the work arguable. Where no evidence exists, the issue says so rather than implying some.

2. **It states what done looks like, in terms a reviewer can hold the pull request against.** The files it produces, the behaviour that changes, the condition that starts passing. How acceptance criteria are written, and where they live, is issue-driven development's to settle (#45). This condition asks only that done is written down before the work starts.

3. **It states what it leaves to other issues, when it touches something another issue owns.** The decisions already made, the work that is blocked on something else, and the part that belongs somewhere else, each named by number. #39's "Label and status vocabulary is unsettled (#22). Do not invent one" is the shape.

## Where this stops

**None of these is a hook, and the one candidate is not worth one.** Whether a body states its evidence, and whether that evidence is real, needs a reader. The one mechanical property, a body that is not empty, holds for every issue this repository has ever had, and a detector for it would need a workflow listening to issue events for nothing to report.

**Issue-first is not stated here.** That work starts from an issue is enforced by `branch-naming.md`, whose name needs the number, and by `pr-quality.md`, which checks the issue exists and is open. Restating it would be a third place to change it.

**Templates are not required.** An issue form turns these conditions into fields, and a project may add one. The rule is about what the issue says, and a template filled in with nothing passes a form while failing all three.
