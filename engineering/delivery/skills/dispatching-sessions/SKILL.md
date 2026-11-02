---
name: dispatching-sessions
description: Hand one issue of a round to one child session that runs Athena — titled and briefed in the person's language, on Sonnet unless the brief says why not. Use when the Tech Lead of a round, or the PM in lean mode, starts work on an approved activity, sends more work to a child session, or finds a pull request that may belong to another tool. Refuses a child without an issue and a second, unrelated demand to a session that holds one.
type: skill
clade: engineering
subclade: delivery
references:
  - rules/round-roles.md
  - docs/round-method.md
  - docs/platform-bindings.md
  - skills/orchestrating-delivery/SKILL.md
---

# Dispatching sessions

A round's work runs in child sessions, one issue each, each running Athena. This is how a coordinator starts one, or sends one more work, without breaking the round's rule: [`rules/round-roles.md`](../../rules/round-roles.md) conditions 4 and 5. The decidable parts are `scripts/check-dispatch.py`, which refuses a dispatch the rule forbids before any session exists.

## 1. Start from an approved activity

The issue comes from the Round issue's Activities table, approved by the person at the opening. An activity with no issue goes back to the PM, who opens one. A request that arrived mid-round and is not in the table also goes to the PM, who decides whether it enters now and what leaves; it is not dispatched on the way past.

## 2. Find the session it goes to

Look for a child session that already holds this issue. More work on the same issue goes to that session. Otherwise it gets a new session. A session that holds another issue never receives this one, however idle it looks: a second, unrelated demand muddles two pieces of work into one context and one title.

A pull request another tool owns, such as one Codex opened, is not dispatched at all. Record its state in the Round issue and leave it to that tool.

## 3. Write the title and the brief

Both are in the person's language, because the person reads them in the session list. The title names the round's project and the issue; the date is the round's. The brief names the issue and says, in this order:

- who is who: the PM and the TL of the round, and that this session holds this one issue;
- what is theirs: run Athena on the issue, through [`orchestrating-delivery`](../orchestrating-delivery/SKILL.md), up to an open, reviewed pull request;
- the state: what is already done, the branch and any pull request;
- what is pending on the person, and the limits: no merge, no other issue, report back when the activity changes state.

The model is Sonnet. Another model is used only when the brief says why, in a sentence, such as a decision record whose design is the work.

## 4. Check the dispatch

Write the dispatch as JSON — `issue`, `title`, `brief`, `language`, `person_language`, `model`, `model_reason`, `agent` (`athena`), `tool`, and `session` or `pull_request` when they apply. `scripts/fixtures/dispatches.json` holds one of each kind. Then:

```sh
python3 skills/dispatching-sessions/scripts/check-dispatch.py dispatch.json
```

`dispatch` means it may go. `refuse` names what to fix: no issue, a child not running Athena, a model other than Sonnet with no reason in the brief, a title or brief not in the person's language or not naming its issue, or a session that already holds another demand. `skip` names a pull request another tool owns. The script reads what was declared; whether the brief is really in that language is the coordinator's read.

## 5. Start the session, or send to it

On Claude Code, `start_session` with the title, the model and the brief starts a new child; `SendMessage` reaches one already holding the issue. Record the child in the Round issue's next work context. Where neither exists, as on Codex, the round runs in lean mode, one issue at a time, as [`docs/platform-bindings.md`](../../docs/platform-bindings.md) records.

## 6. Close the loop on the child

When the child's pull request merges, offer the person to archive the session, and archive it only on their yes. An idle session still wakes on every notification. The child reports state changes; the TL passes to the PM only what changes an activity's state.

## When this skill does not apply

**Orchestrating the issue itself.** Planning, routing, building and stacking happen inside the child, in Athena's `orchestrating-delivery`. This skill hands the issue over; it does not run it.

**Deciding what is dispatched.** Which activities run, and in what order, was decided at the opening, by `opening-the-round` and the person's ok. This skill carries out that plan.

**Work outside a round.** A single issue started by a person directly goes to Athena without a round, a coordinator or this check.

<!--
Directory layout:

skills/dispatching-sessions/
├── SKILL.md
└── scripts/
    ├── check-dispatch.py          refuse, skip or allow one dispatch
    ├── test-check-dispatch.py     the suite CI runs
    └── fixtures/
        └── dispatches.json        one dispatch of each kind, with its verdict

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
