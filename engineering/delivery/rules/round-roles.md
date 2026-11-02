---
id: round-roles
type: rule
clade: engineering
subclade: delivery
title: Who decides, accepts and merges in a round
statement: The round's PM sets priority and accepts, its TL lands what Argos approved after the PM's acceptance, and all work has an issue, an owner and a done criterion.
enforcement: judgment
references:
  - docs/round-method.md
---

# Who decides, accepts and merges in a round

A round is a work window with objectives the person approved, ending in a written closing. Two coordinators run it: the PM of the round, `themis`, and the Tech Lead of the round, `hermes`. [`docs/round-method.md`](../docs/round-method.md) describes the whole round and why it is shaped this way; this rule is the part a reader holds a session to.

Before this rule, the same person's rounds recorded who merges in two contradictory places, a PM did technical work, five PMs opened in one minute, and coordinator sessions lived up to 21 days and read 80% of their tokens above 300k of context. Each condition below closes one of those.

## Conditions

1. **The PM decides priority, and nothing is dispatched before the person's ok.** The PM proposes the round's activities, carried-over ones first, up to the calibrated capacity, and the person approves them. Neither coordinator starts a child session for an activity the person has not approved.

2. **The PM gives product acceptance; the TL does not.** An activity is accepted when the PM has checked its result against the activity's done criterion. The TL reports a result; it does not declare it accepted.

3. **The TL lands only what Argos approved, on green checks, after the PM's acceptance.** Argos's verdict on the head is approve. A comment verdict carries an open question or an unchecked condition, and that is answered first; "no blocker" alone is not enough. Every check on that head has passed, and the PM has accepted the activity. All three hold on the head being landed. A single pull request lands through `ahrena-engineering-quality`'s `landing-approved-changes`. A stack lands layer by layer through `ahrena-contributing`'s `stacking-pull-requests`, each layer on its own approval and its own green checks. [`ahrena-contributing`'s gates rule](../../../contributing/rules/gates.md) governs every landing, and its condition 3 names the round's TL as the agent that lands in a round. The PM never merges. In lean mode (condition 8), with no TL, Argos lands a single pull request after the PM's acceptance, and the person lands a stack.

4. **No work without an issue, an owner and a done criterion.** Every activity of the round carries all three. A request arriving mid-round goes to the PM, who opens its issue and decides whether it enters now, and what leaves to make room, or waits for the next round. No child session is started without an issue.

5. **One demand per child session, and what another tool owns stays out.** A child session holds one issue. A second, unrelated demand goes to a new child session, never to one that holds a demand. A pull request owned by another tool, such as one Codex opened, is left to that tool: the coordinators neither push to it, review it nor merge it, and they record its state only.

6. **Each coordinator is one session for the day.** Per project, one PM session and one TL session run from the opening to the closing. Above 200k of context a coordinator writes its work context to the Round issue, compacts, and re-reads that comment; it does not hand over to a new session. A new session starts only at the day's turn or on an account switch, through `/round-pm` or `/round-tl` from the Round issue, never by copying or resuming a transcript. No coordinator crosses into the next day.

7. **A coordinator polls no faster than every 30 minutes.** A `/loop` or any other repeated wake on a coordinator session has an interval of 30 minutes or more. Each wake re-reads the whole session, and a coordinator's context is the largest on the machine.

8. **The TL exists only for parallel work.** With one build issue at a time the round runs in lean mode: the PM alone, dispatching Athena directly. A TL is opened when two or more build issues run in parallel, or when an infrastructure operation runs beside a build issue.

## Where this stops

**It does not decide what is worth building.** Which issues matter is the person's call, made when they approve the round's objectives. This rule says who proposes and who approves, not what.

**It does not replace Athena or Argos.** Inside a child session, Athena orchestrates one issue and Argos reviews it. The round's coordinators sit above both: the TL dispatches Athena runs and acts on Argos's verdict, and neither coordinator builds or reviews.

**Nothing here is decided by a script.** Who accepted, who merged and how old a session is are visible on the forge and in the platform, but a shared account records the person and the agents under one login, as the gates rule's own limits say. The decidable parts of a round, such as an activity missing its owner or a dispatch without an issue, are checked by the scripts of the round's skills, not by a hook on this rule.

**The 200k and 30-minute figures come from one person's measured sessions.** They were set on the 2026-10 audit of 73 coordinator sessions and the session-economy setting that compacts at 200k on a 1M window. A project on a different window or limit restates them in its own instruction file, and the doc names where they came from.
