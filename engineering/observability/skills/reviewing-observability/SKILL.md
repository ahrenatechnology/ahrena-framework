---
name: reviewing-observability
description: Use when a change under review has a failure path, a critical operation, or a service edge, and the question is what a human on call would have to diagnose it at 3am - whether a failure is logged with enough context to act on, a critical operation emits a metric or event, a log line says what happened and where, and a request can be followed across services by a correlation id. Never asks for sensitive data to be logged.
type: skill
clade: observability
references:
  - ahrena-engineering-quality:docs/review-findings.md
  - ahrena-engineering-quality:docs/review-routes.md

---

# Reviewing observability

One question: when this operation fails in production, does it leave enough behind for a human who was not there to find out what happened and where? The party who pays is whoever is on call — a failure that is silent, or logged without the context to act on it, costs them the outage's whole duration in guesswork.

The conditions are in `references/conditions.md`, identified `OBS-n`. A finding cites the identifier. Severity and route follow `docs/review-findings.md`.

**One rule overrides every correction here: never ask for a sensitive value to be logged.** The fix for a thin log is always more *context* — identifiers, counts, the operation's name — never the data itself. A correction that would put a secret, a credential, a token or personal data into a log is a `reviewing-sensitive-data` finding (DAT-1), not an observability improvement. Log the identifier, never the value.

## 1. Take the route, and read what the repository already does

The `observability` route fired on a line that logs, emits a metric or a trace, or handles an error where one of those belongs. Read the repository's own convention first: the structured logger it uses, the fields it already attaches (a request id, a tenant), the metrics client, the trace propagation. A correction names that path, and context the repository already attaches at a middleware is not asked for again at the call.

## 2. Read the failure paths and the critical operations

For each error handler and each operation that matters — a payment, a state transition, a batch, an external call — ask what a reader would see if it failed or ran. An empty `except` leaves nothing; a `log.error("error")` leaves a line that says a thing went wrong and not which thing, for which entity, where.

## 3. Apply the conditions

Open `references/conditions.md` and read against OBS-1 to OBS-4: a failure with no actionable log, a critical operation with no metric or event, a log line with no context, a service edge with no correlation id.

Read each condition's `Exempt` line: context attached once at a middleware or a logging filter, a metric the platform emits for free, a trace id propagated by the framework.

## 4. Write the findings

Each finding carries the four fields in `docs/review-findings.md` with the `OBS-n` identifier and a correction that is an instruction — and that instruction adds context, never a sensitive value. What the right metric or log level is for a given operation can be a `question` for the owner when the change does not settle it.

Hand the set back to step 7 of `skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**Whether the failure is handled at all.** That a broken operation changes control flow instead of continuing as success is `reviewing-reliability` (REL-4). This skill assumes the failure is handled and asks whether it was recorded; the two meet on a swallowed error, which is both.

**A sensitive value reaching a log.** That a log call carries a password, a token or personal data is `reviewing-sensitive-data` (DAT-1). This skill never corrects *toward* that, and when a proposed log would carry such a value the finding is DAT-1.

**An outside value written to a log with its line breaks intact.** Log injection and forging is `reviewing-untrusted-input` (INP-10). This skill asks whether the log exists and carries context, not whether an attacker can corrupt it.
