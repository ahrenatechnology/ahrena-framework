# ADR-007: Acceptance criteria live in the issue

- **Status:** accepted
- **Date:** 2026-09-27
- **Issue:** #98

## Context

`issue-quality.md` condition 2 asks every issue to say what done looks like,
and leaves the form to issue-driven development. #45 open question 8 asks
where acceptance criteria live, and calls it the sharpest unresolved question
in the subject. It states the dilemma exactly. If the issue is canonical, the
trace to tests cannot run in a checkout. If a committed file is canonical, the
issue and the file can disagree.

The predecessor answered by keeping all three. Criteria were written to
`.ahrena/issues/{n}/02-requirements.md`, restated in the issue body, and named
again by test markers that differed by stack: `@pytest.mark.ac("AC-N")` for
Python, an `@ac` docblock tag for TypeScript, a comment for Go, and a regular
expression as the fallback. Three homes for one list is the shape this
repository has refused twice already: for MCP configuration, and for the
cached plan in `ADR-004`.

Two things have changed since the question was asked. `ADR-002` gave the
framework a forge tier, so a check that reads an issue in CI is no longer a
contradiction. And `ADR-004` put the plan in a sub-issue, so the issue is
already where the decomposition of the work lives. Criteria that live beside
it are one read away from the plan they belong to.

The predecessor's conventions for the criteria themselves were sound and are
kept: numbered `AC-1` upward with no gaps, a removed criterion left in place
so the numbers do not move, one behaviour per criterion, and something
observable in each.

## Decision

Acceptance criteria live in the body of the issue they belong to, under a
`## Acceptance criteria` heading, and nowhere else. There is no requirements
file and no local copy.

Each criterion is a list item whose text begins `AC-<n>:`, numbered from 1
with no gaps and no repeats. A criterion that is dropped stays, reading
`AC-<n>: (removed: <why>)`. A criterion that no test can decide ends with
`(checked by review)`, and says so rather than going untraced.

A test names the criterion it covers with the token `#<issue>/AC-<n>`,
anywhere in the test file: a comment, a docstring, a marker argument. It is
one token in every language. It carries the issue number because `AC-1`
exists in every issue.

## Consequences

The trace from criteria to tests is forge-tier by construction. Offline it is
unchecked, since the criteria are not in the checkout. In CI it reads the
issue as it is at that moment. #99 builds it.

Editing an issue's criteria changes the contract a pull request is held to,
and nothing in the tree records the change. GitHub keeps an issue's edit
history, and that is the record. A pull request is judged against the
criteria as they stand when its checks run, which is the version the reviewer
reads too.

The criteria and the plan sit together. A plan sub-issue lists the units, and
each unit's own issue carries the criteria that unit must meet. A unit's pull
request is traced against its own issue, not the parent's.

One marker for every language gives up what the predecessor's per-stack
markers had: a test runner's own selection, such as `pytest -m ac`. The token
still fits inside a runner's marker, as `@pytest.mark.ac("#98/AC-1")`, so a
project can keep that selection if it wants it. The detector reads the token
and nothing else.

## Alternatives considered

- **A committed requirements file per issue.** This is the predecessor's
  `02-requirements.md`, and it makes the trace runnable offline. Rejected
  because the issue and the file would then both state done, and #45 named
  their disagreement as the failure. A reviewer reads the issue. A file that
  can say something else is a second contract nobody is looking at.
- **Tests as the canonical list.** Whatever the markers name is the set of
  criteria. Rejected because it inverts the check: a criterion nobody wrote a
  test for would not exist, which is exactly the case the trace is meant to
  catch.
- **All three, kept in sync.** The predecessor's arrangement. Rejected on the
  same ground `ADR-004` rejected the cached plan: three sources of truth for
  one list.
- **Per-stack markers.** Rejected for the detector. A language-specific marker
  needs a parser per language. The one token works in any file, and it fits
  inside a runner's own marker for a project that wants both.
