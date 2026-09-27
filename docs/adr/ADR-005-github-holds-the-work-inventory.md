# ADR-005: GitHub holds the work inventory, and ROADMAP.md is retired

- **Status:** accepted
- **Date:** 2026-09-27
- **Issue:** #85

## Context

`ROADMAP.md` held four things at once: an index of the queued issues, the
dependency graph between them (a `Touches` column and a `Blocked by` column), a
table of eleven decisions, and the owner's open questions. Its own header said the
work lived in GitHub issues and that the file held only what an issue cannot, a
decision that spans several of them.

By 2026-09-27 the index had drifted from the issues it indexed. #75 was open and
absent from it. Eighteen open issues, from #1 to #30, were in no row. #39 was
listed as blocked by #22 under a name #22 never carried, so the blocker #39 was
actually waiting on had no issue at all. Nine of the open issues turned out to be
done or superseded. The file said that where it and an issue disagreed the issue
won, which is a concession that the file was a second source of truth for the
same facts.

GitHub now expresses what the file was invented to express. Sub-issues give an
epic its children and their order, and ADR-004 already chose them to hold a plan.
Issue types classify the work. A closed issue and the pull request that closed it
record what landed. The one thing GitHub does not hold is a decision that
belongs to no single issue, and `contributing/rules/decision-records.md` already
gave that a home, `docs/adr/`, with `README.md` allowed by name as the log's index.

ADR-004 said in writing that `ROADMAP.md` is not replaced. This record changes
that one paragraph and nothing else in ADR-004: a plan is still an artifact held
in a sub-issue.

## Decision

`ROADMAP.md` is deleted. Each of its parts moves to the place that already holds
that kind of fact.

- **Queued work and its dependencies** become five epics whose sub-issues are the
  work: #45 (contributing and issue-driven development), #34 (engineering
  quality), #82 (voice and configuration), #83 (platforms and publishing) and #84
  (the gate and its evaluation). #18 stands alone as the design clade. The order
  and the blockers are written in each epic's body.
- **Landed work** is the closed issues and the pull requests that closed them.
  The artifact and test counts in the "Landed" table are not carried over. They
  went stale twice after other merges (#70, #73), and the tree itself is where
  they are counted.
- **The Decided table and the refusals** move unchanged to `docs/adr/README.md`,
  which becomes the log's index: one row per decision, and a link wherever a row
  has a record.
- **The open questions** move to the epic each one blocks. Questions 1 to 3 go to
  #82, questions 5, 6 and 9 to #83. Question 4 is answered by the branch-naming
  rule that landed, question 7 by the Decided table, and question 8 by ADR-002.

Nothing is created to replace the file. There is no generated index, no label
convention standing in for an epic, and no second list of the epics.

## Consequences

The work inventory has one source of truth, and it is the one that people and
agents already read and write. An issue that is opened, closed or re-parented
changes the inventory at the same moment, so there is no file to forget.

What is lost is the single page. `ROADMAP.md` could be read in one screen, and
the epics take five. The file's "What serializes" section, the list of shared
files that collide across the queue, has no natural home in an issue. The four
files it named are `engineering/agents/argos.md`,
`engineering/hooks/check-structure.py`,
`engineering/skills/reviewing-diffs/SKILL.md` and `README.md`, and the lesson
that parallel agents need separate git worktrees came from a real failure. That
lesson is kept here, in this record, which is where a reader looking for why the
file went away will find it.

Milestones are not used. They were asked for and could not be created from the
tooling available on the day, and the epics carry the same grouping. If they are
adopted later, each milestone mirrors one epic, and that is a change to this
record rather than a second grouping beside it.

The Decided rows are still rows. Moving them does not promote any of them to a
record. `contributing/docs/decision-records.md` names six that would earn one,
and each is written when somebody next needs the argument, as that document
prescribes.

## Alternatives considered

- **Keep `ROADMAP.md` and re-sync it.** Fix the three drifts found on the day and
  carry on. Rejected because the drift is the file's nature rather than an
  accident: every issue that opens or closes has to be mirrored by hand, and the
  file itself conceded that the issue wins a disagreement.
- **Keep the Decided table in a slimmer `ROADMAP.md`.** Delete the queue and keep
  the rest. Rejected because `docs/adr/` is already where decisions live, and a
  second decision table at the root is the two-place shape the decision-records
  doc refuses.
- **Promote all eleven rows to records now.** Rejected on the decision-records
  doc's own ground: a record is written when a decision is made, and backfilling
  eleven of them at once would be ceremony over reasoning that the rows already
  hold.
