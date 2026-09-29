---
name: writing-acceptance-criteria
description: Write an issue's acceptance criteria as a numbered list a script can trace to tests. Use when an issue states what done looks like, when criteria change after work has started, or when a test needs to name the criterion it covers.
type: skill
clade: contributing
references:
  - rules/issue-quality.md
---

# Writing acceptance criteria

Acceptance criteria are the form "what done looks like" takes, which `issue-quality.md` condition 2 asks every issue to state. They live in the issue body and nowhere else, and each is numbered so a test can name it. This repository's `ADR-007` records why the issue is the only home.

## 1. Put them under one heading

In the issue body, under exactly this heading:

```markdown
## Acceptance criteria

- AC-1: A decision record settles where criteria live.
- AC-2: Given an issue with no criteria, when its pull request is checked, then the check says so.
- AC-3: Every artifact passes the foundation gate. (checked by review)
```

Each item begins `AC-` and a number, then a colon. A checkbox before it, `- [ ] AC-1:`, is allowed and changes nothing.

## 2. One behaviour each, and something to observe

A criterion describes one thing a reviewer can see happen or not happen. "The page is fast" is not a criterion. "The page renders in under 200 ms on the benchmark fixture" is. Given, when and then is a good shape when there is a precondition, and not required when there is none.

Two behaviours joined by "and" are two criteria. If the "and" cannot be split, the criterion is one behaviour described twice, so write it once.

## 3. Number from 1, and never renumber

Numbers start at `AC-1` and run without gaps or repeats. Tests and reviews refer to them by number, so a number never moves.

A criterion that is dropped stays in the list, reading `AC-4: (removed: <why>)`. A new criterion takes the next number, even when it belongs between two others.

## 4. Say which ones no test can decide

Some criteria are judged by a person: a decision is recorded, a document is clear, a gate passes. End each of those with `(checked by review)`. It is then reviewed rather than traced, and nobody mistakes it for a gap in the tests.

Use it for what really needs a reader. A criterion marked this way to avoid writing a test has only moved the gap.

## 5. Name the criterion in the test that covers it

Put the token `#<issue>/AC-<n>` anywhere in the test file, next to the test that proves it:

```python
def test_rejects_an_issue_without_criteria():  # covers #98/AC-2
    ...
```

It is plain text, so it works in any language and inside a runner's own marker, as `@pytest.mark.ac("#98/AC-2")`. It carries the issue number because every issue has an `AC-1`. One test may cover several criteria, and one criterion may need several tests.

## 6. When criteria change after work has started

Edit the issue. Its edit history is the record of the change, and a pull request is judged against the criteria as they stand when its checks run. If the change moves the scope, say so in a comment on the issue, so the reviewer sees why the target moved.

## When this skill does not apply

A plan's parent states the strategy, not the criteria. Each unit's own issue carries the criteria that unit must meet (`planning-changes`). Writing the rest of an issue, including its evidence and what it leaves to others, is `opening-issues`.
