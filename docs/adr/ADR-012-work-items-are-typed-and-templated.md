# ADR-012: Work items are typed, and each type has a template

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #110

## Context

The survey in #45 counted the predecessor's `.github/ISSUE_TEMPLATE/`, 1,015
lines of issue forms, and called them "the real schema of a well-formed
issue". The forms were: epic, feature request, API user story, frontend user
story, tech task, bug, plan and config. #39 then set templates aside, and
`issue-quality.md` said a template "is not required", because a form filled
with nothing passes a form and fails the rule. Labels, issue types and the
predecessor's status labels went out with them, as configuration (#80).

That cut went one step too far. The owner's direction on 2026-09-28: backlogs
arrive as epics, and the framework should propose the user stories, tech
tasks, spikes and bugs under them, each structured the way the predecessor's
templates were. The configuration was the vocabulary of labels and states,
which differs by project. The shape of a work item is content, and it is the
same everywhere.

Two further facts shape the answer. The organisation has three native issue
types, `Task`, `Bug` and `Feature`, and `gh issue create --type` sets one by
name. And the predecessor had no spike: no item for a question that must be
answered before the work depending on it can be planned.

## Decision

A work item has one of five types: epic, user story, tech task, spike or bug.
Each has a template, shipped as a reference of `skills/opening-issues`, and
every issue the framework writes is written to its type's template.

Every template carries what this framework's rules read. It holds the
evidence `issue-quality.md` asks for, and its done as `## Acceptance criteria`
in the shape `ADR-007` fixed, which `traceability.md` reads. It also holds
what it leaves to other issues. An epic carries the `## Plan` section of
`ADR-011`.

The type is recorded natively where the forge can hold it. The organisation's
issue type of the same name is used when there is one. Otherwise the nearest
is used: `Feature` for an epic or a user story, `Task` for a tech task or a
spike, `Bug` for a bug. Where the forge has no issue types, the body's first
line records the type.

A backlog of epics is planned as one set. `skills/planning-changes` brings
each epic to its template, types every item under it, finds the dependencies
that cross epics, and presents the whole backlog for confirmation before
creating anything.

## Consequences

The predecessor's two user-story forms, one for an API and one for a
frontend, become one user story with an optional interface section. Its
request-header table and the error envelope that named the maintainer's
client are dropped, because the framework is company-agnostic (#15). Its
feature request folds into the user story. Its plan form is replaced by
`ADR-011`'s units as sub-issues. Its config form was the form chooser's own
settings, not a work item.

A spike is new, and it changes how plans are ordered. A spike blocks every
item that waits on its answer. So the unknowns in a backlog are answered
first, and the items that depend on them are planned, not guessed. A spike's
criteria are all judged by a reader, because what it produces is a decision,
not code.

The mapping to native types loses detail where the organisation has fewer
types than the framework: an epic and a story both show as `Feature`. The
template's structure still tells them apart, and an organisation that adds
`Epic`, `Story` or `Spike` as types gets the exact name with nothing to change.
Adding those types is an owner's organisation setting.

The templates are written for agents and people who follow the skill. Forms
for people filing by hand on github.com, built from the same templates, are
not part of this change. Building them would give the same shape two copies,
and they would need a way to stay in sync.

`issue-quality.md` keeps its three conditions. Its paragraph saying templates
are not required changes to say that the framework's templates are how an
issue meets them, and that a template filled with nothing still fails.

## Alternatives considered

- **No types, as `#39` left it.** Rejected by the owner. A backlog decomposed
  into untyped issues gives every item the same shape, which suits none of
  them. A spike and a user story need different sections, and an epic needs
  a plan.
- **The predecessor's eight forms as they were.** Rejected. Two of them were
  the same story split by interface, one named the maintainer's client, one
  was a plan the forge now holds natively, and one was not a work item. None
  of them carried numbered acceptance criteria in the shape the trace reads.
- **Types as labels.** Rejected. Labels are each project's configuration
  (#80), and the forge has a native field for exactly this.
- **Require the organisation to create all five native types.** Rejected as a
  requirement. It is a setting the framework cannot make, and the nearest
  default type plus the template's structure is enough to work with.
