---
id: decision-records
type: rule
clade: contributing
title: What a decision record carries
statement: A decision record is numbered without gaps, carries a status from the enum and the four sections, and its supersession names a record that names it back.
enforcement: hook
enforced-by: hooks/check-decision-records.py
references:
  - docs/decision-records.md
---

# What a decision record carries

Seven conditions, all decided by `hooks/check-decision-records.py`. Each is a state of a file or of the set of files, rather than an opinion about either. [`docs/decision-records.md`](../docs/decision-records.md) carries the part that is not decidable: when a decision earns a record at all, which of this repository's own eleven decisions would have earned one, and what was refused from the format this one inherits.

The rule governs a record that exists. It does not say that a decision must have one, because nothing can.

## Where they live

```
docs/adr/ADR-001-workflow-status-is-one-enum.md
docs/adr/ADR-002-plans-live-in-the-issue-body.md
```

At the repository root, outside every plugin, because a record is project state and not framework content. `foundation/rules/naming.md` governs artifacts inside a plugin and does not reach here — which is why the `ADR-` prefix and the capital letters are allowed, and the doc says what that prefix buys that an artifact's type prefix never does.

## The shape

```markdown
# ADR-007: Short declarative title

- **Status:** accepted
- **Date:** 2026-09-19
- **Issue:** #65
- **Supersedes:** ADR-003

## Context

## Decision

## Consequences

## Alternatives considered
```

`Issue` is optional and `Supersedes` appears only on a record that supersedes one. `Superseded by` is added to the older record at the same moment, and condition 6 is the reason both halves get written.

## Conditions

Each of these is decided by `hooks/check-decision-records.py`.

1. **Every file in the decision directory is named `ADR-` plus three digits, a hyphen, and a kebab-case slug**, matching `ADR-\d{3}-[a-z0-9]+(-[a-z0-9]+)*\.md`. Three digits rather than a variable width so the directory sorts in numeric order in every tool that lists it. A file that is not a record does not belong in a directory whose whole contents are addressable by number.

2. **The numbers are unique and run from 001 with no gaps.** Two conditions in one state, because both failures are the same read. A duplicate is what two authors produce concurrently, and it silently breaks every reference by number. A gap is what a deleted record leaves, and a decision that was made and then erased is the one case a log exists to prevent. The predecessor stated this as "sequential numbering is inviolable" and enforced it with nothing.

3. **The first line is `# ADR-nnn: ` followed by a non-empty title, and `nnn` matches the filename.** A record is almost always written by copying the last one, and the heading is what gets forgotten. This is the same condition `foundation/rules/naming.md` states as identity — the name inside matches the name on disk — applied to the one place a record carries its own number twice.

4. **A `- **Status:**` line is present and its value is `accepted`, `superseded` or `withdrawn`.** The enum is closed at three. `proposed` and `rejected` were dropped and `deprecated` was renamed; `docs/decision-records.md` gives the reason for each.

5. **A `- **Date:**` line is present and parses as an ISO-8601 calendar date.** The number orders the records against each other; the date is the only thing that places one against anything else — a release, an issue, a person's memory of the week. It is a format check and nothing more: a record dated 1970 passes.

6. **Supersession resolves in both directions.** A record whose status is `superseded` carries a `- **Superseded by:**` line naming a record that exists, and that record carries a `- **Supersedes:**` line naming this one. The converse holds too: a `Supersedes` line names a record that exists, whose status is `superseded`, and whose `Superseded by` points back. Every other arrangement fails.

7. **The four sections are present as `##` headings — `Context`, `Decision`, `Consequences`, `Alternatives considered` — and the alternatives section carries at least one list item.** Heading matching ignores case and is done outside fenced code, so a record quoting a heading is not one.

## The condition worth having, and the one that is theatre

**Condition 6 is why this hook exists.** Supersession is two edits in two files, made at one moment by one person who is thinking about the new record and not the old one. Forgetting the second edit produces a log that reads as current and is not: the superseded record still says `accepted`, or says `superseded` and points nowhere. Neither half is visible from the file being written, which is exactly the failure a gate is for. The predecessor's format had supersession and left both halves to discipline.

**Condition 7's alternatives clause is presence, not substance, and it is worth saying so plainly.** A list item reading "doing nothing" satisfies it. The predecessor's framing — an ADR with no alternatives means the decision was made without considering options — is the thing actually worth checking, and it is a reviewer's question. What the condition buys is that the heading is never left empty, which is the one failure mode that is unambiguous.

## Where this stops

**Nothing here says a decision needs a record.** That is the judgment `docs/decision-records.md` is written to inform and it is the whole value of the practice. A repository with no `docs/adr/` directory passes every condition above, and so does one whose every real decision is undocumented.

**Nothing here reads the record.** A Context section describing a different problem, a Decision that contradicts the code, alternatives that were never considered and consequences nobody will pay all pass. Conditions 3 to 7 check that a reader was given the fields; only a reader checks that they were filled with the truth.

**Condition 2 makes a deleted record unfixable except by another record.** That is deliberate and it is the append-only property stated as a state rather than as an exhortation. A record that turned out to be wrong is superseded or withdrawn, both of which keep the file; deleting it fails the gate for everybody who pulls afterwards, which is a worse day than the one where somebody wanted the file gone.

**Nothing here is enforced against a consuming project's history.** The hook runs over a directory and judges what it finds, so a project adopting this rule mid-life has whatever it has. There is no migration condition, because a log that has to be rewritten to be adopted does not get adopted.

**The directory is a convention this rule does not argue for.** `docs/adr/` is where the ADR ecosystem's tooling looks and where the predecessor put them. The hook takes the directory as an argument and defaults to that path; a project that keeps records elsewhere passes the path and loses nothing.
