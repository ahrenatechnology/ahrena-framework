---
name: reviewing-untrusted-input
description: Use when a change under review adds a line where a value from outside - a request, a queue message, an upload, a webhook, a third party's response, a field another user wrote - reaches a query, a command, a filesystem path, a URL, a template, a deserialiser, a response or a log, and the question is what the party who controls that value can make happen.
type: skill
clade: quality
references:
  - docs/review-findings.md
  - docs/review-routes.md
---

# Reviewing untrusted input

One question: with this change, what can the party who controls a value from outside make the code do with it? Outside is wider than the request — a queue message, an upload, a webhook, a third party's response and a stored field another user wrote are all outside, and a value from the system's own database is outside when somebody else put it there.

The conditions are in `references/conditions.md`, identified `INP-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route

The `untrusted-input` route fired on lines that reach a query, a command, a path, a URL, a template or a deserialiser. Those lines are where this skill starts, but a condition is decided on a pair, not a line.

## 2. Map each entry to its sink

For every candidate, follow the value both ways, in the whole file and not only the hunk: where it enters (the request, the queue, the file, the webhook, the provider's response, the stored field) and where it lands (the query, the command, the path, the URL, the template, the response, the log). Write the pairs down. A sink with no outside value reaching it is not a finding, and a line the route matched is usually one of those.

## 3. Apply the conditions

Open `references/conditions.md` and read each pair against INP-1 to INP-10: a query or a command built from text, a path or a URL the caller chooses, text rendered as markup, a template or bytes the caller controls, a structure accepted whole, no bound on what is accepted, outside text in a log or header.

Read each condition's `Exempt` line: a parameterised query, an argument list with no shell, a name the server generated, a sanitiser the repository already uses, a bound the framework enforces.

## 4. Write the findings

Each finding names the party who controls the input and what they gain, carries the four fields in `docs/review-findings.md` with the `INP-n` identifier, and a correction that is an instruction.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**Who is allowed to call the entry at all.** Authentication, authorisation and ownership are `reviewing-access` (ACC).

**A model's output used as input.** A completion treated as a query or a command is `reviewing-model-use` (LLM-4), which applies these same conditions to that value.

**A defect with no party who controls the input.** A wrong result from a value the system itself produced is correctness, in `skills/reviewing-diffs/SKILL.md` and the language skills.
