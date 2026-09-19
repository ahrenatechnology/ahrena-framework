---
name: writing-decision-records
description: Write a decision record, or decide that a log entry is enough. Use when a decision has been made that someone will question later, when an entry in a decision log has outgrown one line, when a rejected alternative is proposed a second time, or when one decision replaces another and both states have to stay readable.
type: skill
clade: contributing
references:
  - rules/decision-records.md
  - docs/decision-records.md
---

# Writing decision records

Most decisions do not earn a record, and step 1 is the step that matters. The rest is mechanical.

## 1. Decide whether this earns a record

A record is earned when at least one of these is yes.

- **Would someone who disagrees need the alternatives to be convinced?** Can you name an option a competent colleague would still propose next quarter, not knowing it was weighed.
- **Is there a cost the repository keeps paying?** A recurring tax, something that got harder, a door that closed.
- **Will it be superseded rather than edited?** A staging post whose replacement has to leave both states readable.

All three no means a line in the decision log, and you are finished. So does the disqualifier: **a decision whose reasoning already ships inside a rule or a doc gets a log entry citing that artifact, not a second copy of the argument.**

[`docs/decision-records.md`](../../docs/decision-records.md) works this through against eleven real decisions, six of which earn a record. Read it the first time; the three questions are the whole of it afterwards.

## 2. Take the next number

```sh
ls docs/adr/ADR-*.md | tail -1
```

Add one and pad to three digits. Numbers are never reused and never skipped, so if two of you are writing at once, agree who takes which before either writes a file — condition 2 fails a duplicate and a gap alike, and it fails them for whoever pulls next rather than for whoever caused it.

## 3. Copy the template and fill it

`references/adr-template.md` is the record, with the prompt for each section beside it. Save it as `docs/adr/ADR-nnn-slug.md`, with the slug kebab-case and the same number in the heading as in the filename.

Two sections carry the weight and both are usually written too thin.

**Context is the problem, not the solution.** Write it for somebody reading in two years who has none of today's conversation. If it can be read as an argument for the decision, it is Decision text in the wrong section.

**Alternatives is where the value is.** One real option is the minimum and the gate checks only that a list item exists. An alternative worth writing is one a reader might still prefer; "do nothing" counts when doing nothing was genuinely available.

## 4. Write both halves of a supersession

When this record replaces an earlier one, two files change in the same commit.

The new record gains `- **Supersedes:** ADR-003` and says in its Context what changed since. The old record gains `- **Superseded by:** ADR-009` and its status becomes `superseded`. Nothing else in the old record is edited — it stays an accurate account of what was decided then.

Forgetting the second edit is the failure this is a step for. Condition 6 checks the pair, not each half, so a chain that resolves one way and not the other fails.

## 5. Run the gate

```sh
python3 contributing/hooks/check-decision-records.py docs/adr
```

It decides the seven conditions in `rules/decision-records.md` over the whole directory, not just the new file, which is how it catches the half-written supersession and the gap a deletion left.

## 6. Put the entry in the log and point it at the record

The record does not replace the log entry. Every decision keeps its one line in the project's decision log, and a line whose decision earned a record cites it by number.

The log stays the complete index, readable in one screen. The records are its overflow, and a reader who wants the reasoning follows the number.

## When this skill does not apply

**A decision that has not been made.** A record states what was decided and what it costs. An option still being weighed belongs in the issue, where people can argue with it; a record written to host an argument is a proposal wearing a decision's format, which is why there is no `proposed` status to put it in.

**A decision somebody else owns.** Recording a choice made by a team, a vendor or an upstream project as though this repository made it puts a decision in the log that nobody here can supersede. Write down the consequence for this repository instead, and that is usually a doc.

**Changing a decision that already has a record.** The record is not edited in place except to add its `Superseded by` line. The new decision is a new record at step 2, and step 4 is how the two are joined.

**Explaining how something works.** A record says why the alternative lost, once, at a date. A reference that has to stay true as the code changes is a doc, and `foundation/skills/creating-artifacts/SKILL.md` step 1 is where that choice is made.
