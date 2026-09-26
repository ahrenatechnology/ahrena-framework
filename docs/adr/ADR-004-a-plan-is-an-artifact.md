# ADR-004: A plan is an artifact, held in a sub-issue

- **Status:** accepted
- **Date:** 2026-09-26
- **Issue:** #45

## Context

IDD needs a home for the plan — the written decomposition of an issue into the
units that will each become a pull request — and #45 open question 6 asks whether
that plan is an artifact at all, or whether this repository's own working model
already covers it.

Two models were on the table. The predecessor's is issue → plan sub-issue → pull
request: the plan lives in its own issue, decomposing the parent. This
repository's own model is `ROADMAP.md`: an epic, a row per unit of work, a
`Touches` column and a `Blocked by` column, with the work itself in GitHub issues.
The survey observed they are close to the same thing under different names, and
that the answer decides whether Group 5 of #45 is 350 lines or 60.

The predecessor's implementation of the plan was refused once already, and for a
reason this framework holds elsewhere. Its plan text lived in an issue body,
mirrored to a gitignored local cache with `not-flushed` regions filtered on the
way up — three sources of truth for one plan, the same shape the "Decided" table
refuses for MCP configuration. That refusal was of the caching machinery, not of
the plan. The survey separated them: the five-strategy decomposition table (by
layer, by endpoint, by workflow phase, by bounded context, by dependency) and the
discipline of confirming the whole decomposition before creating the first unit
are the only decomposition guidance in either repository and are worth carrying.

The owner chose the sub-issue model over the ROADMAP model.

## Decision

A plan is an artifact, and it lives in a GitHub sub-issue of the issue it plans.
The flow is issue → plan sub-issue → pull request. The plan sub-issue carries the
decomposition — the units, their order, what each touches, what blocks what — and
each unit becomes a pull request that closes against the plan.

The plan lives in the sub-issue body and nowhere else. There is no local cache,
no mirror, and no gitignored copy. GitHub's own sub-issue link is the single
source of truth for which plan belongs to which parent, the way `gh issue develop`
is the single source of truth for which branch belongs to which issue.

## Consequences

Group 5 of #45 is the larger of the two sizes the survey named — roughly 350 lines
rather than 60 — because a plan-as-artifact needs its own rule, its own shape, and
the decomposition guidance stated in full, where the ROADMAP model would have
needed only the five-strategy table appended to an existing doc.

The plan gets the same treatment as every other work item under IDD. It is
issue-first by construction, since it is itself an issue. It can carry the state
vocabulary of #22 on the configured axis, so a plan has a readable state and a
named owner per transition the way any issue does. It sits under the parent in
GitHub's model, so the decomposition is navigable without a document that has to
be kept in sync.

`ROADMAP.md` is not replaced. It remains what its own header says it is —
project state, the index of what is queued and the record of what was refused,
the thing an issue cannot hold because it spans several of them. What changes is
that per-issue decomposition moves out of any single document and into a sub-issue
per parent, so the ROADMAP stops being asked to be both the cross-issue index and
the per-issue plan.

The refused machinery stays refused. The decision adopts the plan as an artifact,
not the cache that mirrored it. A plan whose text is duplicated to a local file
would reintroduce the three-sources-of-truth shape this framework rejects, and the
rule Group 5 writes says so in its boundary section.

The cost is one more issue per planned unit of work and the discipline of keeping
the sub-issue link correct. For a change small enough to be one pull request with
no decomposition, a plan sub-issue is overhead, and the rule Group 5 writes has to
say where a plan is required and where a single well-formed issue is enough — the
same shape the branch and commit rules already draw around what they do not check.

## Alternatives considered

- **The ROADMAP is the plan.** Treat `ROADMAP.md`'s epic-and-rows as the
  decomposition and add only the five-strategy table to an existing doc — the
  60-line path. Rejected by the owner. It keeps per-issue decomposition inside a
  single shared document, which is one file every planned issue must edit and a
  merge point the survey already flags as the serialization bottleneck; and it
  gives a plan no state, no owner and no place in GitHub's model.
- **Plan in the parent issue body.** Keep the decomposition in the parent rather
  than a sub-issue. Rejected because the parent then carries both the problem and
  its decomposition, and a plan that changes edits the issue that framed the work,
  losing the history of how the decomposition itself evolved.
- **The predecessor's cached plan.** Issue body mirrored to a gitignored local
  cache with filtered regions. Rejected on the ground the "Decided" table already
  refuses for MCP: three sources of truth for one plan. This is the machinery the
  survey separated from the plan itself, and only the plan is adopted.
