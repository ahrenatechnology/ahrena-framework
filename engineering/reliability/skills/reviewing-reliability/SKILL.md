---
name: reviewing-reliability
description: Use when a change under review talks to something that can be slow, absent or repeated - an outbound call, a retry, a webhook or queue consumer, a resource it acquires, a dependency it leans on, a destructive migration - and the question is whether the change still behaves when that call hangs, fails, or arrives twice.
type: skill
clade: reliability
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md

---

# Reviewing reliability

One question, on every call the change makes to something it does not control: does the change still behave when that something is slow, absent, or delivered twice? The party who pays is whoever is waiting on the request, or whoever is charged, double-booked or corrupted when a failure is not handled.

The conditions are in `references/conditions.md`, identified `REL-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

## 1. Take the route, and read the repository first

The `reliability` route fired on a line that issues an outbound call, retries, acquires a resource, leans on a dependency, or alters a schema destructively. Read how the repository already handles these before judging the change: the client wrapper that sets a default timeout, the retry helper, the migration tool's own down path. A control the repository applies elsewhere is where the correction points, and a condition it already enforces is not reported again.

## 2. Follow the operation to what it waits on and what it changes

For each call the route pointed at, ask two things: what does the caller do while it waits, and what has changed when it comes back — or when it is delivered a second time. A request with no deadline waits forever; a non-idempotent write replayed by a retry or a redelivery happens twice. The reliability question is decided on that pair, not on the call alone.

## 3. Apply the conditions

Open `references/conditions.md` and read against REL-1 to REL-7: a call with no timeout, a retry with no backoff or bound, a non-idempotent effect on a retried path, an error swallowed, a resource acquired and not released, a dependency with no degradation, a destructive change with no reversal.

Read each condition's `Exempt` line: a timeout set once on the client, a retry a library already bounds, a resource a language construct releases, a dependency whose absence is not survivable by design and says so.

## 4. Write the findings

Each finding carries the four fields in `docs/review-findings.md` with the `REL-n` identifier and a correction that is an instruction. Whether a dependency is allowed to be a hard requirement — whether its absence *should* degrade or *should* stop the system — is a `question` for the owner when the change does not settle it, not a verdict this skill gives.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**Whether a failure is logged or measured.** That a failure is handled is this skill; that the handling leaves a trace a human can act on is `reviewing-observability` (OBS). The two meet on a swallowed error: REL-4 is that the error changes no control flow, OBS-1 is that it leaves no record.

**A missing idempotency key on a published mutation.** The engineering rule `cross-cutting-concerns` condition 4 already decides that over the `edges` route; REL-3 is the broader question of an effect that is not safe to repeat, and it points at that rule when a key is the fix.

**An unbounded size, count or recursion driven by an outside value.** That is resource exhaustion from untrusted input, `reviewing-untrusted-input` (INP-9). REL-1 and REL-5 are about the change's own calls and resources, whatever the caller sends.
