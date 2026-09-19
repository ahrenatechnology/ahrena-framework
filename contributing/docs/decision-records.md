---
id: decision-records
type: doc
clade: contributing
title: The decision log and the records it promotes
summary: Why a decision log has two fidelities, the three questions that decide which one a decision gets, this repository's own eleven decisions worked through that test, and which fields of the inherited ADR format were refused and why.
references:
  - docs/contribution-flow.md
---

# The decision log and the records it promotes

This is the reference for `rules/decision-records.md` and for the procedure in `skills/writing-decision-records/SKILL.md`. The rule states the shape a record must hold and the hook decides it. Neither of them answers the question that actually costs something, which is **when a decision earns a record at all**, and that is what most of this document is about.

The answer matters because both obvious answers are wrong. "Every decision gets a record" produces four sections of ceremony around a naming choice whose entire argument is its own title, and a process nobody sustains past the first busy week. "No decision gets a record" is where this repository is today: eleven decisions, and not one of them carries the context that made it necessary, the alternative that was rejected, or the cost that was accepted.

## The log this repository already keeps

`ROADMAP.md` has a **Decided** table. It is an undeclared decision log and it has been working, in the sense that a one-line record of a verdict is worth far more than nothing. What it cannot do is visible in its own contents.

**It has no supersession.** When open question 7 was settled, there was no way to say so, so the question was struck through in place and annotated in prose — *"the slot is kept so that the numbers the other rows and #34 cite still point where they did"*. That is a hand-rolled tombstone, invented on the spot because the log had no mechanism for one decision replacing another. It is the clearest evidence in the repository that the table has run out.

**It has no alternatives.** Every row states a verdict. Not one states what lost, which means the rejected option comes back — and the log cannot tell whether it is being reconsidered or reproposed by somebody who never knew it was considered.

**It cannot say that two rows are one decision.** *The Ahrena MCP server is dropped* and *Capability arrives as a skill, not an MCP server* are one decision written at two altitudes. The table has no way to join them, so they read as two independent verdicts that happen to agree.

**Its longest row is unreadable as a row.** Here is the distribution of the eleven consequence cells, in words:

```text
7   8   11   13   15   27   29        52   53   59   111
```

There is a clean empty span between 29 and 52, and four rows sit above it. That is the same shape of evidence [the engineering plugin's clean-code doc](../../engineering/docs/clean-code.md) uses when it places a threshold at the bottom of a gap rather than at the top of the data, and it gives a tripwire worth having: **a consequence cell running past about thirty words has outgrown the table.** Row 10 is 111 words of prose in a two-column cell and nobody reads it there.

The tripwire is an alarm, not the criterion. It tells you to ask the three questions below; it does not answer them. One of the eleven is short precisely because its consequences were never written down, and length would have let it through.

## The three questions

A decision earns a record when at least one of these is yes. Otherwise a row is enough.

**1. Would someone who disagrees need the alternatives to be convinced?** The test is concrete: can you name an option a competent colleague would still propose next quarter, not knowing it was already weighed. If you can, the row records only that they lost an argument they were never shown. A record is the only place the argument survives.

**2. Is there a cost the repository has to keep paying?** A row records what was chosen. A record records what was accepted — the recurring tax, the thing that got harder, the door that closed. A decision whose only consequence is that something is now spelled a particular way has no ongoing cost and needs no record of one.

**3. Will it be superseded rather than simply edited?** Some decisions are staging posts: they will be replaced, and when they are, both states have to remain legible. A table row replaced in place destroys its own history. A record is superseded, and the chain is the point.

### The disqualifier

**A decision whose reasoning already ships inside an artifact does not also get a record.** *Persona names are allowed on agents, and nowhere else* has an entire section of `foundation/rules/naming.md` explaining it — the two names, what each is for, and the cost of the second field. A record would be a second copy of that argument, in a second place, drifting from the first. The row stays and cites the artifact.

This disqualifier is what keeps the record count honest. A framework that writes rules and docs for a living will find that most of its reasoning has a home already.

### The trigger for promoting a row later

A row is not a permanent verdict about fidelity. **The first time somebody proposes a rejected alternative a second time, the row has failed question 1 in public, and it gets promoted to a record.** That is cheap, it is observable, and it means no one has to predict at decision time which arguments will come back.

Promotion is the whole mechanism. Records are not a parallel system beside the table; they are the table's overflow. Every decision still gets a row, because a row costs one line. A row that earns a record keeps its cell and points at the record, so the index stays complete and the reasoning has somewhere to live.

## The eleven, decided

Applying the test to this repository's own log. Six records would cover seven rows; four rows are enough as they are.

| Decision | Verdict | Why |
|---|---|---|
| The Ahrena MCP server is dropped | **record** | Q1 and Q2. "Why does Ahrena have no MCP server" is the most re-askable question in the project, the artifacts carrying the reasoning were the ones deleted, and the cost is ongoing. Merged with the next row |
| Capability arrives as a skill, not an MCP server | **record** | Same decision at a different altitude. One record, two consequences — this pair is the case the table provably cannot express |
| The framework does not own MCP configuration | row | The argument is complete in the cell: a framework key listing MCP servers is a fifth source of truth beside four real ones. The closest call of the four, and the first reproposal promotes it |
| Persona names are allowed on agents, and nowhere else | row | Disqualified. `foundation/rules/naming.md` carries the argument in full |
| References carry no verb | row | Q1 fails by exhaustion. The alternative is "references carry a verb" and the seven-word cell refutes it |
| MCP transport is ordered: remote HTTP, vendor binary, npx | **record** | Q1 and Q2, at 27 words — under the tripwire and over the bar. Docker is undecided, the owning plugin is undecided, and open question 6 says the rule still needs a sentence on which axis the order optimises and where that inverts. Those are the record's Context, sitting in the open-questions list for want of anywhere else |
| A hook whose tests are not in CI is not trusted | row | Disqualified twice over: `validate.yml` enacts it and `foundation/skills/writing-hooks/SKILL.md` step 6 states it |
| A rule may require the consuming project to adopt a library | **record** | All three. It reopens the verified-property condition and reverses the standing reading of the no-dependency constraint, which is supersession in everything but name |
| Correctness is four families, and it gates "deployable" | **record** | Q2 and Q3. Three of the four families wait on mechanisms that do not exist yet, so this will be amended as each ships, and each amendment needs the previous state to stay readable |
| A reference crosses plugins as a qualified path | **record** | All three, and the canonical case. 111 words, two rules changed, a third form permanently refused, and it already forced the strikethrough that proves the table has no supersession |
| The concept is resource discipline, not memory safety | **record** | Q1 and Q2. Anyone arriving from C or Rust reproposes the memory-safety framing, and the row carries three conditions nobody has built |

The tripwire and the three questions agree on ten of the eleven. They disagree on the MCP transport row, and the disagreement is the useful part: that row is short because its consequences were never written, not because it has none.

The four refusals in *Not coming across* are decisions too, and the same test sends all four to rows. Each one's "why" column is complete — 33 tooling artifacts are maintainer infrastructure, 2 i18n artifacts lose to an English-only project — and none of them has an alternative anybody will repropose.

**None of this migrates the eleven.** That is a second step and a separate decision, and this document does not make it. What it does is establish that the format can hold them, because a format that cannot hold the first eleven consumers is the wrong format.

## Where a record lives, and why it is not an artifact

A decision record is **project state, not framework content**. It records why this repository decided something, it ships to nobody, and it has no reason to pass the artifact gate. That is the same argument `ROADMAP.md` makes for sitting at the repository root rather than inside `foundation/`.

So records live in `docs/adr/` at the repository root, outside every plugin. Three consequences follow.

`foundation/rules/naming.md` does not reach them. A record is named `ADR-007-something.md`, which carries a type prefix that the naming rule forbids and a capital letter its character class does not allow — and neither applies, because a record is not one of the five types and does not sit in a plugin.

**The prefix is kept anyway, because it is load-bearing here in a way it never is on an artifact.** The number is a sort key, and it is an address: "ADR-007" is how one record names another in a supersession line and how a person names one in an issue. An artifact's type prefix buys nothing because the directory already says the type; a record's prefix buys a stable short name.

**The "A" is not load-bearing.** These are decision records, not architecture decision records: nine of the eleven above are about how this repository governs itself, not about a system's structure. The prefix is inherited so that the tooling and the habits built around `docs/adr/` keep working, and the scope is any decision worth keeping.

## What was refused from the inherited format

The format comes from the predecessor's `kata-adr-write`, which is simplified MADR. Most of it survives. These pieces did not.

**The Positive / Negative / Neutral subsections under Consequences.** The predecessor required all three and said an ADR with no Negative is suspicious, which is true and is not fixed by a heading. Three mandatory subsections produce three filled subsections: the two real records in the predecessor use Neutral for a folder rename and a label-colour note, which is a changelog. One `Consequences` section, holding what improved, what it costs and what it forecloses, in prose. The cost question stays with the reviewer, where the predecessor's own rule already left it — a `### Negative` reading "none" satisfies a gate exactly as well as a real one does, which is the boundary `foundation/rules/completeness.md` draws when it says presence is not substance.

**The `proposed` status.** The pull request is the proposal and merging is the acceptance. A record on a branch is already a proposal, and a status field restating what the forge holds is a second source of truth for the same fact — and one that must be remembered and edited on merge, which is exactly the kind of manual sync that goes stale. A record whose *subject* is still partly open is not a proposal: it is a decision about the part that closed, and the open edge belongs in its own text. The MCP transport record above is that case.

**The `rejected` status.** A rejected decision has no consequence to record and no supersession chain to join. What is worth keeping from a rejection is the rejected option and the reason, and that already has a section in every record that considered it.

**`deprecated` became `withdrawn`.** Deprecated means still in use and discouraged, which is a property of code. A decision that stopped applying and was not replaced was withdrawn.

**The 60-character slug cap.** Stated by the predecessor without a derivation and enforcing nothing anybody gets wrong. The slug is kebab-case and that is all.

**"Sequential numbering is inviolable."** Kept as two conditions, not as an exhortation. Duplicate numbers are what concurrent authors produce; gaps are what a deleted record leaves. Both are decidable and both are now decided by the hook.

**The bare "at least one alternative."** Kept, and kept honest. The hook decides that a list item exists under the heading. An alternative reading "do nothing" satisfies it, and the predecessor's framing — *an ADR with no alternatives is suspicious* — is a review question that no script inherits.

## What the hook decides, and what it cannot

`hooks/check-decision-records.py` decides the seven conditions in `rules/decision-records.md`. Six of them are the shape of a string or a file's presence. The seventh is the only one with any reach:

**Supersession is checked in both directions.** A record marked `superseded` names its successor, the successor exists, and the successor names it back. A half-written chain — the common failure, because the second edit happens in a different file at a different moment — fails the gate. That one condition is most of the hook's value, and it is the thing the inherited format left to discipline.

What the hook cannot decide is everything this document is about. It cannot tell whether a decision deserved a record, whether the alternatives are the real ones, whether the consequences are the ones that will actually be paid, or whether the context would mean anything to a reader in two years. The checklist narrows that judgment. Nothing decides it.

## Where this stops

**Nothing here migrates the Decided table.** The verdicts above are an analysis, not a plan, and the eleven rows stay exactly where they are until somebody decides otherwise.

**The three questions are a test, not a formula.** They will misfire in both directions — a decision that passes all three and still reads as ceremony, a row that fails all three and is missed for a year. The promotion trigger is the cheap correction for the second case and there is none for the first; a record that turned out not to be worth writing is a sunk half hour and it stays, because deleting it leaves the gap that condition 2 of the rule then fails on.

**Nothing here governs a consuming project's records.** A project that installs this plugin gets a shape and a procedure. Whether its decisions look anything like this repository's eleven is its own business, and the three questions are stated as reasoning rather than as conditions precisely so that a project can disagree with them without failing a gate.

**The record does not replace the issue.** An issue carries the work and the discussion that produced a decision; the record carries the decision. Where the two disagree the record is the one that was meant to outlive the thread, and it should name the issue so the thread is still reachable.
