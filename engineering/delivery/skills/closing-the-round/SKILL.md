---
name: closing-the-round
description: Close a round of work — close each done activity's issue with its evidence, write state, reason and next step on each left-over one, post the closing comment with the day's numbers and next capacity, close the Round issue, and draft the Slack summary and the week's series. Use when /round-close runs, fifteen minutes before a round's window ends, or when a Round issue is still open after its window. Posts to Slack only on the person's ok or a recorded standing ok.
type: skill
clade: engineering
subclade: delivery
references:
  - rules/round-roles.md
  - docs/round-method.md
  - skills/opening-the-round/SKILL.md
---

# Closing the round

A round ends in a written closing, fifteen minutes before its window does. This is how the PM of the round writes it. [`docs/round-method.md`](../../docs/round-method.md) says what the closing is for and [`rules/round-roles.md`](../../rules/round-roles.md) who may accept and merge. The decidable parts are the same `round.py` that [`opening-the-round`](../opening-the-round/SKILL.md) runs, so the numbers a closing writes are the numbers the next opening reads.

## 1. Recover the round from its issue

The plan lives in the Round issue's body, not in a session:

```sh
gh issue view <round> --json body -q .body > body.md
python3 skills/opening-the-round/scripts/round.py extract body.md > round.json
```

## 2. Write each activity's outcome

In `round.json`, give every activity an `outcome`. A `done` one carries its `evidence`: the merged pull request, a link, or a test's output, never a claim. A `left-over` one carries its `state`, the `reason` it was not done and its `next_step`. An activity is done only when the PM accepted its result against its done criterion.

Then add the round's `decisions`, the `pending` items for the person — each with `what`, `recommend` and `link` — the `context` for tomorrow, and `round_issue`, the Round issue's URL. `scripts/fixtures/round-to-close.json`, beside the opening skill's script, is a complete example.

## 3. Run the closing

Fetch the closed rounds as the opening does, then close. Add `--week-last` on the week's last round:

```sh
python3 skills/opening-the-round/scripts/round.py close round.json \
  --history rounds.json --out closing \
  --channel "#project-channel" --instructions AGENTS.md
```

`refused` names a done activity with no evidence, a left-over missing its state, reason or next step, or a pending item missing one of its three parts. Fill them and run it again. The report prints done over planned, the next capacity and whether the Slack summary may be posted.

## 4. Comment on each activity's issue

`closing/issue-comments.json` holds one comment per activity. Close each done one with its evidence comment, `gh issue close <n> --comment "<body>"`, and comment on each left-over one, `gh issue comment <n> --body "<body>"`, leaving it open. A left-over that would enter its third round is marked as raised; put it in the person's pending items rather than carrying it again.

## 5. Post the closing and close the Round issue

```sh
gh issue comment <round> --body-file closing/closing.md
gh issue close <round>
```

The comment's six parts are Delivered, Left over, Decisions, Pending, Context for tomorrow and the day's numbers, with a hidden block of numbers that the next opening reads. Do not edit that block by hand.

## 6. Post the Slack summary only with an ok

`closing/slack.txt` is the five-to-eight-line summary; on the week's last round, `closing/week.txt` is the week's series. Post them to the project's channel only on the person's ok given now, or on a standing ok they recorded for that project and channel. A standing ok is a line `ahrena:round-slack-ok` followed by the channel in the project's instruction file, written by the person or with their ok, and the report says whether one was found. Without either, show the draft and ask.

## 7. Leave nothing running into tomorrow

Offer to archive the child sessions whose pull requests merged; archive only on the person's yes. The PM and the TL of the round end with the day. Tomorrow's round starts fresh from this closing, through `/round-pm`.

## When this skill does not apply

**Mid-round status.** The checkpoint is one message at mid-window, in `opening-the-round`; it closes nothing.

**Accepting or merging.** The closing records what was accepted and merged. Accepting is the PM's act and merging the TL's, both before the closing, by the round's rule.

**A round with no Round issue.** A window that was never opened through `opening-the-round` has no plan to recover and no numbers to add. Open the next round properly instead of writing a closing for one that did not exist.
