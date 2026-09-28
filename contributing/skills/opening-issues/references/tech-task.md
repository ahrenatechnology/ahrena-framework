# Tech task

Work with no behaviour a user sees: an enabling change, a refactor, a dependency, CI, documentation, maintenance. Native type: `Task`.

Title: the change, in the imperative. "Move payment retries into the job runner".

```markdown
## Why

The problem it solves or the risk it removes, with evidence: the slow query,
the flaky run, the deprecation notice, the line that is wrong. Where there is
none, say so.

## What

What changes, and what explicitly does not.

## Acceptance criteria

- AC-1: <observable result: a check that starts passing, a number that moves, a file that exists>
- AC-2: <no regression: the suite that must still pass, or the behaviour that must not change>

## How

The approach, if it is not obvious or was argued over. Optional.

## Left to other issues

- <each by number>
```

A tech task that enables a user story is a blocker of that story: set it with `planning-changes` step 5.
