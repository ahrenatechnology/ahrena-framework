---
name: planning-changes
description: Decide whether a change needs a plan, split it into typed units, order them and make them on the forge, one epic or a whole backlog of them at a time. Use when an issue is too large for one pull request, when a backlog of epics has to become user stories, tech tasks, spikes and bugs, or when the order between pieces of work has to be recorded.
type: skill
clade: contributing
references:
  - rules/planning.md
  - skills/opening-issues/SKILL.md
  - skills/writing-acceptance-criteria/SKILL.md
  - skills/stacking-pull-requests/SKILL.md
---

# Planning changes

A plan is the issue it plans, its units as sub-issues, and their order as the forge's `blocked by`. This repository's `ADR-011` records the model. Every unit is typed, as an epic, a user story, a tech task, a spike or a bug, and written to its type's template in `opening-issues` (`ADR-012`). This skill owns the decomposition checklist; `stacked-pull-requests.md` and the flow cite it.

Steps 1 to 8 plan one change. When what arrives is a backlog of epics, start at step 9, which runs steps 2 to 8 for every epic at once.

## 1. Decide whether a plan is needed

Most changes are one pull request, and they need none. Plan when at least one of these holds:

- **The change will not be reviewed in one sitting.** Several subsystems, or a diff a reviewer would read in more than one pass.
- **Parts of it can be judged apart.** A decision, then the code that follows it. A detector, then the rule that uses it.
- **Parts of it must land in a set order.** One piece changes what the next one builds on.
- **Parts of it can go in parallel.** Different people or agents could take them at the same time.

None of these holds: write one issue with `opening-issues`, and stop here.

## 2. Pick the strategy the change splits by

| Strategy | Split when | Units look like |
|---|---|---|
| By layer | The change crosses the stack: storage, service, interface | one unit per layer, lowest first |
| By endpoint or flag | Independent entry points, each shippable alone | one unit per endpoint or flag |
| By workflow phase | A decision, then its implementation, then its enforcement | the record, then the code, then the check |
| By bounded context | The change crosses domain boundaries | one unit per context |
| By dependency | Some parts only make sense once others exist | the parts nothing depends on first |

Say which strategy you chose and why. That sentence goes into the plan, and nothing else records it.

Then give each unit its type:

- **User story** when a user can see the unit's behaviour. Slice it vertically, so each story works end to end on its own; a story that only makes sense with the next one is half a story.
- **Tech task** when nothing a user sees changes: the schema, the job runner, the migration, the pipeline. It usually blocks the stories that need it.
- **Spike** when something is not known well enough to plan or build: whether an approach works, what a system can take, which option to pick. It comes first and blocks every unit that waits on its answer, and it is timeboxed.
- **Bug** when the unit fixes something that does not do what was specified.

## 3. Confirm the whole decomposition first

Write every unit down, with its type, its title, what it produces and what it waits on, and put the whole set in front of the person who asked for the work. Create nothing until they confirm it. That is gate 1 of `gates.md`, applied to the plan. A plan confirmed one unit at a time drifts halfway through, and the units already created no longer fit the ones that follow.

## 4. Make the units

Each unit is an issue in its own right, written with `opening-issues` to its type's template, with its native type set and acceptance criteria from `writing-acceptance-criteria`. Make each one a sub-issue of the parent (`opening-issues` step 5 has the command).

## 5. Record the order on the forge

For each unit that waits on another, set the dependency on the forge. The field is the blocking issue's `id`, not its number:

```sh
gh api -X POST repos/<owner>/<repo>/issues/<unit>/dependencies/blocked_by \
  -F issue_id="$(gh api repos/<owner>/<repo>/issues/<blocker> -q .id)"
```

`planning.md` condition 2 then fails a pull request that closes the unit before its blocker has landed.

## 6. Write the plan section in the parent

Under `## Plan` in the parent's body: the strategy and why, and whether the units stack. The sub-issues and their dependencies hold the rest, so do not copy them here.

If the forge has no native sub-issues or dependencies, `## Plan` also lists the units and their order. Keep it current as units close, because nothing else holds that order.

## 7. Decide whether the units stack

Stack them when each builds on the code of the one before and they should land in that order. Then build them with `stacking-pull-requests`. Do not stack units that are independent. They are parallel pull requests, and a stack would make each wait for the others for no reason.

## 8. Close the parent when the last unit closes

No pull request closes the parent, because `planning.md` condition 1 fails one that tries while a unit is open. Each unit's pull request says `Part of #<parent>` beside its own `Closes`. When the last unit lands, close the parent by hand, with a comment naming what landed.

## 9. From a backlog of epics

A backlog arrives as a list of epics, some written well and some a single line. Plan all of it before creating any of it: an item under one epic often waits on an item under another, and that only shows when the whole set is on the table.

1. **Bring every epic to its template.** Each has an outcome, the evidence it is worth doing, and what is in and out of scope (`opening-issues`, `references/epic.md`). Where an epic has none of that, draft it and flag what you had to assume. An epic whose outcome cannot be stated is a spike first.
2. **Run steps 2 and the typing above for every epic.** Pick each one's strategy, and list its items with their type.
3. **Look across epics.** Mark each item that waits on an item under another epic, and each spike whose answer changes more than one epic. Two epics that need the same tech task share one, under the epic that needs it first, and the other waits on it.
4. **Present the whole backlog at once**, one table per epic, before creating anything:

   | # | Type | Title | Produces | Blocked by |
   |---|---|---|---|---|
   | 1 | Spike | Can the ledger take 5,000 writes a second? | a decision | — |
   | 2 | Tech task | Partition the ledger table by month | the new schema | 1 |
   | 3 | User story | Pay an invoice by bank transfer | the payment flow | 2 |

   List the assumptions you made, and the questions only the person can answer. This is gate 1 for the whole backlog. Create nothing until it is confirmed.
5. **Create what was confirmed:** each epic's text updated to its template, then its items with `opening-issues`, as sub-issues of their epic, then every dependency, including the ones that cross epics, with step 5. Then write each epic's `## Plan` (step 6).

## When this skill does not apply

A change that is one pull request needs one issue and no plan. Splitting code inside a pull request into commits is not planning, and `commit-format.md` governs it.
