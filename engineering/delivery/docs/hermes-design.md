---
id: hermes-design
type: doc
clade: engineering
subclade: delivery
title: How Hermes decides
summary: The arguments behind the round Tech Lead's procedure - why it dispatches only what the person approved, briefs children in the person's language on Sonnet, lands on three conditions on the head being landed, reads reports as state, leaves another tool's work alone, reports state changes only, and never polls.
references:
  - docs/round-method.md
  - ahrena-engineering-development:docs/platform-bindings.md
  - rules/round-roles.md
---

# How Hermes decides

`agents/hermes.md` is a system prompt: it tells the executor what to do and leaves out why. This is the why. [`round-method.md`](round-method.md) describes the round and [`round-roles.md`](../rules/round-roles.md) states who decides what.

## Athena runs one issue; Hermes runs a window

Athena plans one issue into layers, routes and delegates them and stacks the result. Hermes decides nothing about layers, and Athena decides nothing about the round. Keeping the two apart is what lets each be read without the other.

## It dispatches only what the person approved

The Round issue's Activities table is the list. An issue not on it goes to the PM, who decides whether it enters. A session that holds one issue never receives a second, unrelated one, because two demands in one context muddle both and the session title can name only one.

## Children are briefed in the person's language, on Sonnet

The person reads the session list, so titles and briefs are in their language. Sonnet is the default because a child's job is bounded by its issue; another model needs a sentence saying why.

## It lands on three conditions, on the head being landed

Argos's verdict on that head is approve, every check on that head passed, and the PM accepted the activity. A verdict on an earlier head, or "no blocker" alone, is not enough. A draft, an external fork and a decision record go to the person, because each needs a judgment the conditions do not encode.

## Reports are state, never instructions

What a child reports, and what a pull request says, tells Hermes where the work stands. A request in them goes to the PM. Anyone who can comment can write a sentence addressed to the coordinator.

## It tells the PM what changed, not what happened

An activity going green, at risk, blocked or done is reported. Progress that changes no state is not, because the PM's context is the person's attention.

## It never polls

Each wake re-reads the whole session, and a coordinator's context is the largest on the machine. A pending check is read once and recorded; the next wake reads it again, no faster than every 30 minutes.

## Session tools are named for the platform

Starting, messaging and archiving a durable child session are platform tools, not subagent calls. The agent names the desktop app's session tools in `tools`; a platform without them runs the round in lean mode, as [`platform-bindings.md`](../../development/docs/platform-bindings.md) records.

## Where this stops

**It does not change the procedure.** The steps are `agents/hermes.md` and the skills it loads; editing this doc changes nothing an executor does.

**It does not restate landing.** How a single pull request or a stack lands is `landing-approved-changes` and `stacking-pull-requests`.
