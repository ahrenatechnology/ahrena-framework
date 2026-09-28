# Epic

An outcome too large for one pull request, delivered by the items under it. Native type: `Epic` if the organisation has it, otherwise `Feature`.

Title: the outcome, as a noun phrase. "Customers pay by bank transfer", not "Implement bank transfers".

```markdown
## Outcome

What is true for users or the business when this is done, in two or three sentences.

## Why

The evidence this is worth doing: the request, the metric, the incident, the
cost of not doing it. Link each one. Where there is none, say so.

## Scope

In: what this epic covers.
Out: what a reader might expect here and will not find, and where it lives if anywhere.

## Plan

The strategy the epic splits by, and why (planning-changes step 2).
Whether its items stack.
The items themselves are this issue's sub-issues, and their order is their
`blocked by`; do not list them here unless the forge has neither.

## Acceptance criteria

- AC-1: <the outcome, observable, as the epic's owner would check it> (checked by review)
- AC-2: Every sub-issue is closed. (checked by review)

## Left to other issues

- <decisions already made, work owned elsewhere, each by number>
```

An epic is closed by hand when its last item lands (`planning.md` condition 1). Its criteria are the outcome, judged by a person, so they are marked `(checked by review)`.
