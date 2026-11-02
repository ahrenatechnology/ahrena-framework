---
id: round-method
type: doc
clade: engineering
subclade: delivery
title: The round method
summary: How a work window is run by a PM and a Tech Lead of the round — the Round issue, opening, durable day sessions, the checkpoint, the closing, carry-over, calibration and visibility — and how the round's TL differs from Athena.
references:
  - rules/round-roles.md
  - docs/platform-bindings.md
---

# The round method

A **round** is a work window with objectives the person approved, ending in a written closing. It exists because the alternative was measured and found expensive. Between 2026-10-05 and 2026-10-31 one person ran 73 coordinator sessions across three accounts. They read about 13 billion input tokens, a fifth to a third of the whole machine's, and 80% of that in calls above 300k of context. 53 of them stayed open more than a day, the longest 21 days, and titles were re-dated instead of sessions being renewed. No round had written day objectives or a closing. Account switches broke continuity, and who merges was recorded two different ways.

What worked in those sessions is kept: the title pattern `Papel · Projeto · dd/mm/aaaa`, a hand-over that says who is who and what is pending, pending items written in three parts, and merges delegated on a green CI and a review with no blocker. [`rules/round-roles.md`](../rules/round-roles.md) states the conditions a session is held to; this doc is the method around them.

## The Round issue holds the round

The round lives in a **Round issue** in the project's own repository, labelled `round`, written from the `round` issue form. It does not live in a session. A session dies on compaction, on an account switch and at the end of the day; an issue survives all three, and anyone on the team can read it.

The form has five sections. **Window** is the start and end of the round. **Sessions** names the PM and TL sessions by title. **Capacity** is the calibrated number of activities or points the round can hold. **Activities** is a table with one row per activity: the checkable result, its issue, its owner, its done criterion, its size (P, M or G), its origin (new or carried, with the round count) and its state. **Out of scope** names what was asked for and deliberately left out.

## Two coordinators, and how they differ from Athena

**The PM of the round**, `themis`, owns priority and acceptance. It opens the round, proposes the day's activities up to capacity, talks to the person, gives product acceptance and runs the closing. It never opens build sessions, reviews or merges.

**The Tech Lead of the round**, `hermes`, owns execution across the window. It starts one child session per issue, each running Athena, unblocks them, watches trunk and infrastructure, and merges on a green CI and an Argos verdict with no blocker, after the PM's acceptance. It tells the PM only when an activity changes state. It never builds or reviews.

**Athena is the tech-lead of one issue; hermes is the tech-lead of a work window.** Athena plans one issue into layers, routes them, delegates each to a build clade and stacks the result. Hermes does none of that. It decides which issues run now, starts one Athena session per issue, and carries each to a merge. The two never overlap: Athena never sees the round, and hermes never sees a layer.

**Lean mode** is the round without a TL. With one build issue at a time, the PM dispatches Athena directly and the TL's coordination has nothing to coordinate. A TL is opened when two or more build issues run in parallel, or when an infrastructure operation runs beside a build issue.

## Opening

`/round-pm` with the project, and optionally the window, opens the round. The PM reads the last closed Round issue, sessions that need attention, and the open issues and pull requests. Carried-over activities go on top of the proposal with their state and round count, and none is dropped silently.

An activity carried into its third round is not carried again. The PM raises it to the person, who splits it, reassigns it or drops it. An activity that keeps rolling over is a mis-sized or mis-owned activity, and a third round is where that becomes evidence rather than bad luck.

Every activity has an owner, a done criterion and an issue. One without an issue gets one through `opening-issues` first. The PM proposes up to the calibrated capacity and says so when the plan exceeds it. The person approves, and only then is the Round issue opened, the TL started with `/round-tl` when needed, and anything dispatched.

## Durable for the day

The PM and the TL are one session each for the whole day. The session title is `PM da rodada · Projeto · dd/mm/aaaa` or `Tech Lead da rodada · Projeto · dd/mm/aaaa`, in the person's language, and the date is the day it was opened, never edited later.

Above 200k of context a coordinator compacts, and does not hand over. Before compacting it writes its work context as a comment on the Round issue: the goal, the decisions taken, the pull requests and branches, the child sessions, the next step and the blockers. After compacting it re-reads that comment. The figure is the session-economy setting that compacts at 200k on a 1M window, and the target behind it is no coordinator call above 300k.

A new session starts only at the day's turn or on an account switch. A prompt cache belongs to its account, so a session resumed on another account re-reads its whole context at full price; on 2026-10-21 one TL transcript was copied across accounts twice and resumed at 845k. The new session starts through `/round-pm` or `/round-tl` from the Round issue, which carries everything a transcript would, at a fraction of its size. The old session is archived only on the person's yes.

A coordinator does not poll faster than every 30 minutes, because each wake re-reads the session in full.

## No undefined work

A request that arrives mid-round goes to the PM. The PM opens its issue and decides: it enters now and something named leaves, or it waits for the next round. The TL never starts a child session for work that has no issue, and never hands a second, unrelated demand to a child session that already holds one. A pull request another tool owns, such as one Codex opened, is recorded and left alone.

## Checkpoint

At the middle of the window the PM sends the person one message: each activity green, at risk or dropped. It is one message, not a report, because its job is to let the person change course while there is still time to.

## Closing

`/round-close`, fifteen minutes before the window ends, closes the round. Of the round's activities, each done one has its issue closed with an evidence comment: a merged pull request, a link, a test output. Each left-over one gets its state, the reason it was not done and its next step written on its own issue, and moves to the next round.

The Round issue then gets the closing comment and is closed. The comment has six parts. **Delivered** lists each done activity with its evidence. **Left over** lists each one that was not, with state, reason and next step. **Decisions** records what was decided during the round. **Pending** lists what waits on the person, each in three parts: what it is, a recommendation written as `Recomendo: …` in the person's language, and a link. **Context for tomorrow** is what the next opening needs. **The day's numbers** are done over planned, the number carried over, and points when the project counts them.

## Calibration

Three figures come from the project's closed Round issues and nowhere else.

- **Completion rate** is done divided by planned, per round. Between 70% and 90% is healthy: below, the rounds are over-planned; above, they are probably under-planned.
- **Next capacity** is the mean done over the last five closed rounds of the project, as a count of activities or in points, P=1, M=2, G=3. The opening proposes up to it.
- **Item age** is the number of rounds an activity has been planned in. At three the PM raises it instead of carrying it.

Cost per delivery is optional, through `/issue-cost` from the `ahrena-costs` plugin, when that plugin is installed.

## Visibility

The round is open to the team, not only to the person who ran it. With the person's ok, or a standing ok they recorded for that project and channel, the closing posts a five-to-eight-line summary to the project's Slack channel. On the week's last round it adds the week's series: completion rate and capacity per round, and the oldest items. Round issues sit on the project's GitHub Projects board. The TL offers to archive child sessions whose pull requests merged, since an idle session still wakes on every notification.

## On a platform without child sessions

Hermes needs a way to start a child session and talk to it. On Claude Code that is `start_session` and `SendMessage`. Where they are missing, as on Codex, the round runs in lean mode: the PM alone, one issue at a time through Athena. [`docs/platform-bindings.md`](platform-bindings.md) records the fallback beside the other per-platform bindings.

## Where this stops

**It does not choose what is worth building.** The method structures a window around objectives the person approved. What those objectives are is the person's call.

**It does not orchestrate an issue.** Planning one issue into layers, routing them and stacking them is Athena's, in `orchestrating-delivery`. A round contains Athena runs; it does not reach into them.

**It does not observe sessions.** Detecting which session plays which role, measuring a coordinator's context and proposing its renewal on screen belong to a session observer, ahrenatechnology/ahrena-console#292 and ahrenatechnology/ahrena-console#293. The method states the limits; the observer measures them.

**Its thresholds come from one person's audit.** The 200k compaction, the 300k target, the five-round mean, the 70–90% band and the third-round raise were set on one person's sessions in 2026-10. They are the starting values, and a pilot round on a real project is what tests them.
