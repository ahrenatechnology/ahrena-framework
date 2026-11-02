<!-- Generated from issue-forms/round.yml by scripts/render_issue_forms.py. Edit the form, then rerun it. -->

# Round

A work window with objectives the person approved, run by the PM of the round and closed with a written closing

Native issue type: `none`. Title: `{{ Round · project · date, in the person's language }}`.

Use this form to open a round: a work window with objectives the person approved, ending in a written closing.
The PM of the round writes it, after the person approved the activities, with the `opening-the-round` skill. The closing is a comment on this issue, and closes it.
Every activity has an owner, a done criterion and an issue. One without an issue gets one before it enters the table.

## Sections, in order

Write each as a `### <label>` heading, as GitHub does when the form is filled in.

### Window

When the round starts and ends, with the date. The closing runs 15 minutes before the end.

For example:

> e.g. 2026-11-02, 09:00 to 18:00

Required.

### Sessions

The coordinator sessions of the round, by title. One PM session; a TL session only when two or more build issues run in parallel or an infrastructure operation runs beside one. Otherwise write that the round runs in lean mode.

For example:

> e.g.
> - PM: PM da rodada · ahrena-console · 02/11/2026
> - TL: Tech Lead da rodada · ahrena-console · 02/11/2026

Required.

### Capacity

The calibrated capacity: the mean done over the project's last five closed rounds, as activities or points (P=1, M=2, G=3). Say so when there is no history yet, and when the plan exceeds it.

For example:

> e.g. 6 points (mean of the last 5 rounds); planned 7

Required.

### Activities

One row per activity, carried-over ones first. Size is P, M or G. Origin is new, or carried with the round count. State starts as planned.

Starts as:

```markdown
| Result | Issue | Owner | Done criterion | Size | Origin | State |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  | planned |
```

Required.

### Out of scope

What was asked for and deliberately left out of this round, each with its issue when it has one.

Required.
