---
name: round-close
description: Close the day's round fifteen minutes before its window ends — evidence on done issues, state and next step on left-overs, the closing comment with the day's numbers, and a Slack draft.
type: command
clade: engineering
subclade: delivery
argument-hint: "[round-issue]"
references:
  - skills/closing-the-round/SKILL.md
---

# /round-close

Invoke `closing-the-round` with the argument below, in the PM of the round's session.

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `round-issue` | no | The open Round issue, by number or link. Without it, the project's one open issue labelled `round` |

## What runs

`skills/closing-the-round`, from step 1. The Slack summary is posted only on the person's ok or a standing ok recorded for that project and channel.
