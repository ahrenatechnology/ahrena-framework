---
id: opentelemetry
type: doc
clade: observability
title: The OpenTelemetry text behind the telemetry rules
summary: Which OpenTelemetry specification page each condition cites, what it says as read on 14 November 2026, where the project's thresholds go beyond it, and the one attribute name the catalog had wrong.
references:
  - rules/telemetry-sdk.md
  - rules/log-records.md
  - rules/result-metrics.md
---

# The OpenTelemetry text behind the telemetry rules

This is the companion to [`rules/telemetry-sdk.md`](../rules/telemetry-sdk.md), [`rules/log-records.md`](../rules/log-records.md) and [`rules/result-metrics.md`](../rules/result-metrics.md). Each source below was read on 14 November 2026; a threshold is the specification's, or it is declared maintainer policy (#34).

## Logs data model (LOG-2 to LOG-6)

Source: OpenTelemetry Specification, Logs Data Model, status Stable (<https://opentelemetry.io/docs/specs/otel/logs/data-model/>).

- The record has `Timestamp`, `ObservedTimestamp`, `TraceId`, `SpanId`, `TraceFlags`, `SeverityText`, `SeverityNumber`, `Body`, `Resource`, `InstrumentationScope`, `Attributes` and `EventName`.
- `SeverityNumber` is 1-4 TRACE, 5-8 DEBUG, 9-12 INFO, 13-16 WARN, 17-20 ERROR, 21-24 FATAL; 0 may mean unspecified.
- `Resource` should follow the semantic conventions for resources. `TraceId` and `SpanId` are optional and can be set for records that are part of request processing; if `SpanId` is present, `TraceId` should be too.

Policy beyond the text: LOG-3 requires the ids on every in-span record, which the specification allows and does not require.

## Log body and event name (LOG-4, LOG-6)

Source: Semantic Conventions, General, Events (<https://opentelemetry.io/docs/specs/semconv/general/events/>).

- An event must have a name that uniquely identifies the event structure, names must not include dynamic values and should be low-cardinality, and a shared name is used only when the same definition applies to every occurrence.
- Structured detail belongs in attributes; the conventions define no body value except a string display message of the event.

So LOG-4 reads "structured body" as structured attributes plus a display-only body, which is what the text allows.

## Exception attributes (LOG-5, OTL-3)

Sources: Semantic Conventions, Exceptions in Logs (<https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-logs/>) and Trace, Exceptions (<https://opentelemetry.io/docs/specs/otel/trace/exceptions/>).

- A log record carries `exception.type` and `exception.message`, one required if the other is absent, and `exception.stacktrace` recommended. `exception.message` may contain sensitive information, which is why LOG-1 reaches it.
- On a span, an exception that remains unhandled when the span ends and causes error status SHOULD be recorded as an event named `exception`, with those three attributes.

Policy beyond the text: OTL-3 requires the record for every unexpected failure, and LOG-5 requires all three attributes where the conventions recommend the stack.

## Resource attributes (LOG-2)

Source: Semantic Conventions, Registry, Service (<https://opentelemetry.io/docs/specs/semconv/registry/attributes/service/>) and Resource, Deployment Environment (<https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/>).

- `service.name` is the logical name of the service; `service.version` is the version string of the service component. Both are stable. If `service.name` is unset the SDK falls back to `unknown_service`, which a project must not accept.
- The stable deployment attribute is `deployment.environment.name`. The catalog and the issue wrote `deployment.environment`; the page does not mention that name, so the rule uses the current one.

## Trace context (OTL-4)

Source: W3C Trace Context, Recommendation of 23 November 2021 (<https://www.w3.org/TR/trace-context/>). The `traceparent` header is `version-trace-id-parent-id-trace-flags`; its example is `00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01`.

## Metrics (MET-1, MET-2)

Source: OpenTelemetry Specification, Metrics API (<https://opentelemetry.io/docs/specs/otel/metrics/api/>).

- The synchronous instruments are Counter, Histogram, Gauge and UpDownCounter. A name is case-insensitive ASCII, starts with a letter, may continue with letters, digits, `_`, `.`, `-` and `/`, and is at most 255 characters. A unit is a case-sensitive ASCII string of at most 63 characters; a description supports at least 1023 characters.
- The page gives no cardinality limit, so LOG-7's unbounded-attribute rule is policy, and the same reading applies to metric attributes.

## Thresholds

| Condition | Threshold | Source |
|---|---|---|
| OTL-1, OTL-2 | 0 other paths; 100% of entry points and adapter calls | maintainer policy; the SDK is the standard named |
| OTL-3, LOG-5 | 100% of failure paths | policy; the attribute names are the conventions' |
| OTL-4, LOG-3 | 100% | policy; the header format is W3C's |
| LOG-1, LOG-7 | 0 | maintainer policy |
| LOG-2, LOG-4, LOG-6 | 100% | the conventions' names; the percentage is policy |
| MET-1, MET-2 | a filled field; 100% of declared | maintainer policy; field syntax from the Metrics API |

## Where this stops

This document does not track later versions of the specification; a project re-reads the pages it pins. It does not cover vendor-specific exporters, sampling policy or dashboards.
