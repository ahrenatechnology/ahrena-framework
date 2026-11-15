---
id: telemetry-sdk
type: rule
clade: observability
title: Telemetry leaves through OpenTelemetry
statement: Logs, traces and metrics go through the OpenTelemetry SDK; every entry point opens a span, and an unexpected failure is recorded on it.
enforcement: judgment
references:
  - docs/opentelemetry.md
---

# Telemetry leaves through OpenTelemetry

Four conditions, OTL-1 to OTL-4 of the PR quality rubric (#323). `docs/opentelemetry.md` cites the specification text behind each and says which thresholds are the specification's and which are declared maintainer policy (#34).

None of these conditions adds an abstraction, so the abstraction trigger of `rules/yagni.md` in the fundamentals plugin does not gate them. Each is decided by a test with an in-memory exporter, which the consuming project owns because it needs its own entry points; the detectors are tracked in the detectors sub-issue of #323.

## Conditions

1. **OTL-1. A log, a trace and a metric are emitted through the OpenTelemetry SDK, with its semantic-convention names.** The threshold is 0 emissions through another path: no custom log format, no hand-written trace header, no metric client of another vendor. Decided by a static search for the project's logging, tracing and metrics imports outside the OpenTelemetry packages, and by a reviewer for the rest.

2. **OTL-2. Every entry point opens a root span, and every adapter call opens a child span.** An entry point is a route, a job or an event consumer. The threshold is 100% of both, decided by a test that drives each entry point with an in-memory exporter and asserts one root span and one child span per adapter call it makes.

3. **OTL-3. An unexpected failure records the exception on the span and sets the span status to error; the stack lives there and never in a response.** The record carries `exception.type`, `exception.message` and `exception.stacktrace`. The threshold is 100% of unexpected-failure paths, decided by a test with an in-memory exporter that forces a failure and reads the span. The response side is condition 2 of `rules/result-errors.md` in the fundamentals plugin.

4. **OTL-4. The trace context propagates between processes in the `traceparent` header, and every log record inside a span carries its `trace_id` and `span_id`.** The threshold is 100% of outbound calls to services the project owns carry the header; the in-span record ids are LOG-3 and are stated there once. Decided by a test that makes an outbound call and reads the header, and by condition 3 of `rules/log-records.md`.

## Where this stops

**OTL-1 does not forbid a local debug sink.** A console exporter the SDK ships is still the SDK; the condition forbids a path that bypasses it.

**OTL-2 does not require a span for every function.** Only the entry point and the adapter call; a span per internal function is the volume `rules/log-records.md` condition 7 forbids for records.

**OTL-3 does not apply to an expected failure.** A `Result` failure is a value; the observer may record it as an event, but it is not an exception on the span and does not set error status unless the project's convention says it does.

**OTL-3 does not forbid the exception message from being redacted.** The conventions say `exception.message` may carry sensitive information, so the observer's redaction, condition 1 of `rules/log-records.md`, applies before export.

**OTL-4 does not require propagation to a system that does not read it.** A vendor call that drops the header is still an adapter span; the condition applies to calls between services the project owns.

**These conditions are judgment, and the detectors are named rather than shipped.** The in-memory-exporter tests need the project's entry points.
