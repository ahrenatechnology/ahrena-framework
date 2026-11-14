---
id: janus-design
type: doc
clade: engineering
subclade: security
title: How Janus decides
summary: The arguments behind the security guardian's procedure - why it runs inside the build loop, why it is a lens and not the whole review, why it reads the project's conventions first, bounds the damage rather than the door, gives every finding four fields, says what it did not check, and references the six disciplines rather than their conditions.
references:
  - ahrena-engineering-quality:docs/review-findings.md
---

# How Janus decides

`agents/janus.md` is a system prompt: it tells the executor what to do and leaves out why. This is the why. Read it when the procedure looks wrong, before changing it.

## A guardian at the threshold

Janus is named for the two-faced guardian of thresholds: it looks both ways across the boundary a change crosses and applies the security lens before the change passes, not after. It is the dedicated security reviewer of the agency flow. Athena routes a security-sensitive concern to it, and it gates the threshold before a layer opens as a stacked pull request: the build agent develops, Janus reads the working diff for security alone, and a security concern surfaces inside the loop where it is cheap to fix rather than at the end where it is expensive.

It is addressed as `janus` and its subject is `security-guardian`. The naming rule in the foundation plugin explains why an agent carries both a handle and a subject.

## It is a lens, not the whole review

It applies the six security disciplines and nothing else. The engineering rules over source, the language specifics, the contract break and the prompt-as-instruction review belong to Argos, in the one verdict Argos publishes on the pull request. Janus moves the security disciplines earlier in the flow; it does not take over the parts of the review that are not about security. A guardian that published its own verdict would be a second Argos, and the flow has one. A clear threshold is therefore not an approval of the change.

## It applies the exposure rule at every threshold

The routed disciplines are selected by what a change's lines look like, and the incident behind `rules/layer-exposure.md` is the case where that selection failed: the line that returned a provider's error to a client was not the line any route pointed at. So at a threshold Janus does not wait to be routed to exposure. It always runs the access and sensitive-data disciplines, runs the exposure hook, and reads every exit the layer adds against the rule, because a layer is the unit that owns its data and the threshold is the last point where the layer's own author can still change what it emits. A dependency's error passed through is `ACC-8`; any other sensitive datum or whole object at an exit is `DAT-1`; both block, because the line is in the layer's diff.

## It does not fix what it finds

A reviewer that applied its own findings would read its own edit on the next pass, and the second reading is the value of the review. The build agent writes the change, and Erodos applies the mechanically applicable findings once the layer is a pull request.

## It reads the project's conventions first

What a repository treats as sensitive, how it reads its own secrets, where the owner or tenant identity comes from, and which recipients its documents already name decide `DAT-5` and `ACC-5`. A verdict on those invented from scratch would be the framework's opinion of someone else's system. So the component map is read before any discipline runs, and a condition that needs the project's answer and cannot find it is a question, not a verdict.

## It bounds the damage, not only the door

On model use it assumes the model follows the attacker's text at some point and that no delimiter prevents that reliably. A change that only hardens the prompt has not resolved a finding about what the model can then cause. The same instinct runs through the set: the sink matters more than the source.

## Every finding has four fields

File and line, the discipline's condition identifier, the party who gains and what, and a correction that is a concrete instruction. An impression missing one of those cannot be acted on by the build agent or applied by Erodos, so it is a question or it is dropped. A real credential already committed is also flagged for rotation, because removing the line leaves it in history.

## It says what it did not check

A dependency advisory the repository runs no audit for is recorded `unchecked` rather than recalled from memory, and a discipline no line selected is named as not selected. The guardian that reads as clean when it skipped a check is worse than no guardian, because the build loop stops looking.

## It references the disciplines, not their conditions

The agent references the six skills and none of their `references/conditions.md` files, because the agent selects the discipline and the discipline reads its own conditions. Duplicating every condition in the agent would put the real dependency in two places that drift. Where a request disagrees with a condition, the condition wins.

## What it leaves to others

Whether a deferrable finding becomes work is the caller's. Whether a recipient may receive a category of data at all is the organisation's to settle, and not a verdict this agent passes.

## Where this stops

This doc argues the agent's procedure; it does not define it. The steps, inputs and outputs are in `agents/janus.md`, and the conditions are in each discipline's `references/conditions.md`. Where this doc and the agent disagree, the agent body is what runs, so fix the disagreement rather than reading this as an override.
