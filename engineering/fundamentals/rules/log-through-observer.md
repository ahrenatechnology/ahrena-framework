---
id: log-through-observer
type: rule
clade: engineering
subclade: architecture
title: The domain does not log; an observer does
statement: Domain and use-case code writes no log, console output or logger call; a fact leaves as an event and an observer at the edge records it.
enforcement: judgment
references:
  - docs/log-through-observer.md
---

# The domain does not log; an observer does

One catalog condition, OBS-1 of the PR quality rubric (#323), and two that state its boundary. `docs/log-through-observer.md` explains why the logging decision belongs at the edge and how it meets `rules/cross-cutting-concerns.md`.

A fact is something that happened that a person on call may want: an order was rejected, a payment was captured. The domain states the fact as an event or as the failure case of a `Result`; it does not decide that the fact is a log line, at what severity, or with which attributes. That decision is made once, by an observer at the edge, so it can be redacted, sampled and changed in one place.

Condition 1 removes a call rather than adding structure, so the abstraction trigger of `rules/yagni.md` does not gate it. Condition 2 names the observer, and it is gated: the observer is justified by the second consumer that every fact has, the log and the span.

## Conditions

1. **OBS-1. A module of the domain or use-case layer contains no `console.*`, `print`, `logging` or logger call.** The threshold is 0 occurrences, on new and changed lines. The layers are those the project's layer map names. Decided by a static search for the logging APIs of the project's language in those paths, and by a reviewer for what a search cannot place.

2. **A fact the domain wants recorded leaves as a domain event or as a `Result` failure, and the observer at the edge turns it into a log record.** The observer lives in an adapter module, receives the event, and is the only code that builds the record described by `rules/log-records.md` in the observability plugin. Decided by a reviewer reading where a record is constructed.

3. **A new kind of fact is a new event with a stable name, never a new log call in a body.** Decided by a reviewer.

## Where this stops

**OBS-1 does not reach the observer or the edge.** An adapter, a route handler, a job entry point and the composition root may write the record; they are the edge. Exclude them by path.

**OBS-1 does not reach a test.** A test may print to diagnose itself.

**OBS-1 does not forbid a span.** A span or a metric inside a body is a concern the boundary should declare, and `rules/cross-cutting-concerns.md` decides that; this condition is about the log call, which is the one that most often carries a datum nobody redacted.

**Condition 2 does not require an event bus.** The observer may be a function the use case's caller invokes with the returned event. The condition is who decides the log record, not the transport.

**These conditions are judgment, and the detector for OBS-1 is tracked in the detectors sub-issue of #323.**
