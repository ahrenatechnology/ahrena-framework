---
id: themis-design
type: doc
clade: engineering
subclade: delivery
title: How Themis decides
summary: The arguments behind the round PM's procedure - why it proposes and the person approves, refuses undefined work, raises what keeps rolling over, accepts against the done criterion, writes pending items in three parts, keeps one session for the day, and hands the Slack summary back instead of posting it.
references:
  - docs/round-method.md
  - rules/round-roles.md
---

# How Themis decides

`agents/themis.md` is a system prompt: it tells the executor what to do and leaves out why. This is the why. [`round-method.md`](round-method.md) describes the whole round and [`round-roles.md`](../rules/round-roles.md) states who decides what; this doc covers only the PM's choices.

## It proposes, and the person approves

Themis drafts the activities, carried-over ones on top, up to the calibrated capacity, and says so when the plan goes above it. Nothing is opened or dispatched before the person's ok, because a round whose objectives nobody approved is just a busy day. The ok is a `NEEDS_APPROVAL` return rather than a wait, so the same procedure runs whether Themis is the person's session or a subagent.

## It refuses undefined work

Every activity has an issue, an owner and a done criterion. A request arriving mid-round gets its issue first, and then the person decides whether it enters now, and what leaves, or waits. Work without an issue is work nobody can accept.

## It raises what keeps rolling over

An activity that would enter its third round is not carried again. A third round is evidence that the activity is mis-sized or mis-owned, so the person splits, reassigns or drops it.

## It accepts against the done criterion

Product acceptance is the PM's act: the result read against the criterion written at the opening, not against how the diff looks. The Tech Lead lands only after it, which is what keeps "reviewed" from standing in for "wanted".

## Pending items come in three parts

What it is, a recommendation written as `Recomendo: …` in the person's language, and a link. A pending item without a recommendation hands the person a problem instead of a decision.

## One session for the day

Above 200k of context Themis writes its work context to the Round issue and compacts; it renews only at the day's turn or on an account switch, from the Round issue. The figures and the measurements behind them are in `round-method.md`.

## The Slack summary is handed back

The closing skill posts to Slack only on the person's ok. The agent declares its tools, and no Slack tool is common to every install, so Themis prepares the summary, asks for the ok, and hands the approved text back for the person to post. Posting outside the repository stays a person's act.

## Where this stops

**It does not change the procedure.** The steps are `agents/themis.md` and the skills it loads; editing this doc changes nothing an executor does.

**It does not restate the round.** Windows, capacity, calibration and the closing's parts are `round-method.md` and the round skills.
