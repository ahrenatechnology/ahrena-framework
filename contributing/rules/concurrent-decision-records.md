---
id: concurrent-decision-records
type: rule
clade: contributing
title: A decision-record number is free across open pull requests
statement: An open pull request introduces no decision-record number that trunk already carries or that another open pull request also introduces.
enforcement: hook
enforced-by: hooks/check-decision-records-numbers.py
enforced-in: forge
references:
  - docs/decision-records.md
---

# A decision-record number is free across open pull requests

Two conditions, both decided by `hooks/check-decision-records-numbers.py` and both read from the forge, so without a token each is reported unchecked rather than failed. [`docs/decision-records.md`](../docs/decision-records.md) carries when a decision earns a record at all; this rule guards only the number the record is given.

This is the collision `decision-records.md` condition 2 cannot see. `check-decision-records.py` reads one tree: each branch holds only its own new record, so each passes alone, and the duplicate — or the gap a later renumber leaves — surfaces only once both reach one tree, at rebase or at land, the latest and most expensive moment. This rule reads the forge instead, where trunk and every other open pull request are in view at once, and catches the clash on the pull request that introduces it.

A number this pull request introduces is one its diff adds: a file added, or renamed to, under `docs/adr/` whose name matches `ADR-nnn-slug.md`. A pull request's files are its diff against its base, not against trunk, so a layer stacked on another shows only the record it adds itself, never the one its base introduced. Two layers of one stack, each adding a different number, never meet here; only independent branches that each add the same number do.

## Conditions

Each of these is decided by `hooks/check-decision-records-numbers.py`.

1. **A number this pull request introduces is not already on trunk.** The number is read from each record the diff adds or renames to under `docs/adr/`, and checked against the numbers trunk's `docs/adr/` already carries. A number trunk holds was taken by a record that has landed, so a second record claiming it is the duplicate `decision-records.md` condition 2 would fail once this branch rebased — reported here first, on the pull request, before the rebase. The finding names the fix: `contributing/skills/writing-decision-records/scripts/renumber-decision-record.py`, which moves the losing record to the next free number.

2. **A number this pull request introduces is not also introduced by another open pull request.** The other open pull requests are read from the forge, and a number two of them each add is a clash neither tree can see, because neither branch carries the other's record. Whichever lands first takes the number; the other becomes the duplicate at its own next rebase. The finding names both pull requests and the same renumber script, run on the record that has not landed.

## Where this stops

**This is not the tree-tier numbering check, and does not replace it.** `decision-records.md` condition 2 still decides a record's number over one tree, where it catches the gap a deletion leaves and a duplicate within a single branch, and it stays unchanged. This rule adds the one view a single tree does not have: the other branches. Because each finding names the renumber script and the correction is a concrete instruction — this record, to the next free number — Erodos applies it under the applying-fixes model.

**Both conditions are unchecked on a checkout with no token, and that is the design.** The forge tier, recorded as `ADR-002`, reports a condition it could not ask about as unchecked rather than failed. The state these conditions read — trunk's landed records and the set of open pull requests — is the forge's, not the tree's, so offline there is nothing to read and nothing to fail.

**It reads what the forge lists when the check runs.** A pull request opened after the last run is not in view until the next run, which is when a branch that would clash with it is next checked. The clash is caught on whichever of the two is touched after both are open, not at the instant the second opens.

**It checks the number, not the record.** Whether the record's context, decision and alternatives are right, and whether the decision earned a record at all, are `decision-records.md`'s conditions and a reviewer's judgment. This rule decides only that the number is free.
