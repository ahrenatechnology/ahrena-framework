---
name: opening-the-round
description: Open a round of work on a project — read the last closing, carry its left-over activities on top, propose the day's activities up to the calibrated capacity, wait for the person's ok, and open the Round issue from the round form. Use when the PM of the round starts a work window, when /round-pm runs, or when a round must be planned from carried-over work and open issues. Refuses an activity without owner, done criterion or issue, and dispatches nothing before the ok.
type: skill
clade: engineering
subclade: delivery
references:
  - rules/round-roles.md
  - docs/round-method.md
  - ahrena-contributing:skills/opening-issues/SKILL.md
---

# Opening the round

A round is a work window with objectives the person approved, held in a Round issue in the project's own repository. This is how the PM of the round opens one. [`docs/round-method.md`](../../docs/round-method.md) describes the whole round, and [`rules/round-roles.md`](../../rules/round-roles.md) states who decides what. The decidable parts — refusing an incomplete activity, carrying left-overs, computing capacity, rendering the body — are `scripts/round.py`, so the same plan always opens the same round.

Everything here is `gh` and the script. Run commands from the project's repository; the script path is the installed plugin's.

## 1. Read what the round starts from

Fetch the project's closed Round issues, which carry the last closing and the calibration history:

```sh
gh issue list --label round --state closed --limit 20 \
  --json number,title,url,comments > rounds.json
```

Then read what else is waiting: the sessions that need the person's attention, the open issues and the open pull requests. A pull request another tool owns, such as one Codex opened, is noted with its state and left alone.

## 2. Draft the plan

Write `plan.json` with the project, the date (ISO), the window, the person's language (`en` or `pt-BR`), the unit (`count` or `points`), the session titles, the out-of-scope items, and one entry per proposed activity: `result`, `issue`, `owner`, `done` (the done criterion) and `size` (P, M or G). `scripts/fixtures/plan.json` is a complete example.

An activity with no issue gets one first, through [`opening-issues`](../../../../contributing/skills/opening-issues/SKILL.md). The left-over activities of the last round are not written here; the script puts them on top.

## 3. Run the opening

```sh
python3 skills/opening-the-round/scripts/round.py open plan.json \
  --history rounds.json --body body.md
```

Read the report. `refused` names each activity missing its owner, done criterion or issue, or with a size outside P, M, G; fix the plan and run it again. `raise` names each left-over that would enter its third round: it is not carried, and the person decides to split it, reassign it or drop it. To keep one, add it to the plan; it stays with its age. `warning` says the plan is above the calibrated capacity.

## 4. Propose, and wait for the ok

Show the person the activities in order, the capacity, any warning and every raised item, in their language. Nothing is opened or dispatched before their ok. A change to the plan goes back to step 3, so the body always matches what was approved.

## 5. Open the Round issue

With the ok, open the issue from `body.md`, under the title the report printed, with the `round` label:

```sh
gh label create round --description "A round of the round method" 2>/dev/null
gh issue create --title "<title from the report>" --label round --body-file body.md
```

The body follows the `round` issue form and carries the plan in a hidden block, which is what the closing and a renewed session read back. Where the project keeps a GitHub Projects board, add the issue to it.

## 6. Hand the round to its runner

With two or more build issues in parallel, or an infrastructure operation beside one, start the Tech Lead of the round with `/round-tl` and point it at the Round issue. Otherwise the round is in lean mode, and the PM dispatches one Athena session per issue itself.

## 7. Send the checkpoint at mid-window

At the middle of the window, send the person one message: each activity green, at risk or dropped. A request that arrived since then goes through the PM, who opens its issue and decides whether it enters now, and what leaves, or waits for the next round.

## When this skill does not apply

**Closing the round.** Writing the evidence, the left-overs and the closing comment is `closing-the-round`.

**Running a single issue.** One issue that has to become merged work is Athena's, through `orchestrating-delivery`; a round is for a window that holds several.

**Choosing what matters.** The skill proposes up to capacity and the person approves. It never decides priority over the person's head.

<!--
Directory layout:

skills/opening-the-round/
├── SKILL.md
└── scripts/
    ├── round.py                        open, extract, close, calibrate
    ├── test-round.py                   the suite CI runs
    └── fixtures/
        ├── closed-rounds.json          six closed Round issues
        ├── plan.json                   a plan for the next round
        └── round-to-close.json         a round with its outcomes filled

Flat. One level under skills/. A nested skill is invisible to DeepSeek.
-->
