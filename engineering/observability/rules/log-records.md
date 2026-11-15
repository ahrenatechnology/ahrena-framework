---
id: log-records
type: rule
clade: observability
title: A log record follows the OpenTelemetry data model
statement: A log record has no secret or personal datum, carries resource and trace ids, an OTel severity, exception attributes on errors, a stable name; no hot loop.
enforcement: judgment
references:
  - docs/opentelemetry.md
---

# A log record follows the OpenTelemetry data model

Seven conditions, LOG-1 to LOG-7 of the PR quality rubric (#323). The record is built by the observer at the edge, per `rules/log-through-observer.md` in the fundamentals plugin, and the fields below are those of the OpenTelemetry log data model. `docs/opentelemetry.md` cites it.

None of these conditions adds an abstraction, so the abstraction trigger of `rules/yagni.md` does not gate them. `rules/yagni.md` is in the fundamentals plugin. The detectors are tests with an in-memory exporter and static checks, tracked in the detectors sub-issue of #323.

## Conditions

1. **LOG-1. A record carries no secret and no personal datum; the observer masks before export.** The threshold is 0 occurrences of an attribute on the project's sensitive-attribute list, in a record or in `exception.message`. Decided by a test with an in-memory exporter and that list, and by the security plugin's review of sensitive data.

2. **LOG-2. Every record carries the resource attributes `service.name`, `service.version` and `deployment.environment.name`.** The threshold is 100%. The catalog wrote `deployment.environment`; the specification's stable attribute is `deployment.environment.name`, so that name is the condition. `service.version` is the application's version, and it never carries a secret. Decided by a test that exports a record and reads the resource.

3. **LOG-3. Every record emitted inside a span carries its `trace_id` and `span_id`.** The threshold is 100%. The specification makes them optional and says they can be set for records that are part of request processing; here they are required inside a span as policy. Decided by a test that logs inside a span.

4. **LOG-4. Severity is an OpenTelemetry `SeverityNumber`, and the record is structured: attributes named by the semantic conventions where the registry has one and a project-namespaced name otherwise, and a body that is only a display message, never an interpolated string carrying data.** The threshold is 100% of records. A datum goes into an attribute, not into the string. Decided by a static search for string interpolation or concatenation in the body argument of a record, and by a test reading the severity.

5. **LOG-5. An error record carries `exception.type`, `exception.message` and `exception.stacktrace`.** The threshold is 100% of error records. The stack is the one allowed here, in the record the observer exports, never in a response; `exception.message` goes through LOG-1. Decided by a test that forces an error.

6. **LOG-6. Each kind of record has a stable event name.** The threshold is 100% of records, and a name contains no dynamic value. The `EventName` field of the data model holds it. Decided by a static search for records built without a name, and by a check that no name is built from a variable.

7. **LOG-7. No record in a hot loop, and no attribute of unbounded cardinality.** The threshold is 0 occurrences. A hot loop is a loop whose body runs per item of an unbounded input; an unbounded attribute is a free-text field, an identifier of a person or a raw URL. Decided by a static search for a record call inside a loop and for those attribute sources.

## Where this stops

**LOG-1 does not remove a legitimate identifier.** An order id and a trace id are not personal data by themselves; the project's sensitive list says which fields are, and the condition masks that list, not every id.

**LOG-2 does not apply to the SDK's own diagnostics.** The condition is about records the project's code emits.

**LOG-3 does not apply to a record outside a span.** A start-up record has no trace to carry; LOG-2 still applies.

**LOG-4 does not reach a message with no datum.** A fixed display string such as `order rejected` is a body; the condition forbids the string that carries a value the reader needs to filter on.

**LOG-5 does not make the stack a response field.** See condition 2 of `rules/result-errors.md` in the fundamentals plugin.

**LOG-6 does not ask a name per call site.** Two call sites that record the same kind of fact share a name, and the specification says a shared name is used only when the same definition applies.

**LOG-7 does not forbid a sampled record in a loop.** A record emitted once per batch or at a bounded rate is not per item.

**These conditions are judgment, and the detectors are named rather than shipped.** The framework contains no logger to run them against.
