---
id: logging-and-observability
type: doc
clade: engineering
subclade: go
title: Logging and observability in Go
summary: How a Go service logs with log/slog — one logger passed in, structured attributes, levels that mean something, the request's context on every line — and how traces and metrics reach a collector through OpenTelemetry, without logging what must not be logged.
references:
  - docs/libraries.md
  - docs/error-handling.md
  - rules/errors.md
---

# Logging and observability in Go

A log line is written for one reader: the person on call, at night, who has the line and the code and nothing else. This document is how a Go service writes for that reader with the standard library's `log/slog`, and how it adds traces and metrics with OpenTelemetry. It is Go's half of the subject; what an on-call reader needs from a change, in any language, is the observability plugin's review discipline.

## slog, and why not the log package

The `log` package prints a line of text. The Go blog's *Structured Logging with slog* introduced `log/slog` in Go 1.21 because logs are increasingly read by machines first: a structured record — a message, a level, and key-value attributes — can be filtered, aggregated and joined to a trace without a regular expression. `slog` ships a `JSONHandler` for production and a `TextHandler` for a terminal, and any backend plugs in by implementing `slog.Handler`. Since Go 1.24 `slog.DiscardHandler` silences a logger in a test, and since Go 1.26 `slog.NewMultiHandler` sends one record to several handlers.

The rest of this page assumes `slog`; [`docs/libraries.md`](libraries.md) says when a faster handler is worth swapping in behind it.

## One logger, passed in

A component receives its `*slog.Logger` through its constructor, already carrying the attributes that identify it — `logger.With("component", "orders")`. It does not call `slog.Default()` from deep inside. A logger passed in is a logger a test can replace and a reader can trace to where it was configured; the default logger is global mutable state, which the Uber guide's *Avoid Mutable Globals* argues against in general. `main` builds the root logger once, from configuration, and calls `slog.SetDefault` only so that libraries which log through the default end up in the same stream.

## Attributes, not interpolation

`logger.Info("order cancelled", "order_id", id, "reason", reason)` keeps the values queryable; `logger.Info(fmt.Sprintf("order %s cancelled: %s", id, reason))` turns them into prose. The message is a constant that says what happened; everything that varies is an attribute. Attribute keys are chosen once per service and reused — `order_id` everywhere, not `orderID` in one place and `order` in another — because a query for one misses the others. `slog.Attr` constructors (`slog.String`, `slog.Int`) avoid the alternating key-value list's one failure mode, an odd number of arguments, which `go vet`'s `slog` analyzer reports.

## Levels that mean something

A level is a promise about who must read the line. `ERROR` means someone must act — and is logged once, at the frame that handles the error, as [`rules/errors.md`](../rules/errors.md) condition 4 requires; [`docs/error-handling.md`](error-handling.md) shows where that frame is. `WARN` is a degraded but handled condition worth a trend: a retry that succeeded, a fallback taken. `INFO` is the service's own narrative at the grain of a request or a job. `DEBUG` is off in production. A service whose `ERROR` stream carries handled, expected failures trains its on-call reader to ignore `ERROR`.

## The request's context on every line

Every line written while serving a request carries what identifies the request: its trace and span identifiers, and whatever the service uses to correlate — a request id, a tenant. The `slog` methods that take a context, `InfoContext` and its siblings, pass the context to the handler, and a handler that reads the active OpenTelemetry span from it adds `trace_id` and `span_id` to the record. That is the join between a log line and the trace that explains it, and it is why the context must reach the logging call — which is condition 3 of [`rules/context.md`](../rules/context.md) seen from the other side.

## Never log what must not be logged

A credential, a token, a session cookie, a card number, a password or a field of personal data is never an attribute. `slog.LogValuer` lets a type decide how it is logged, so a `User` type logs its id and never its email, and a `Secret` type logs `REDACTED`: the decision is made once, on the type, rather than at every call site. What counts as sensitive is the security plugin's `reviewing-sensitive-data` discipline; this page says only that `LogValuer` is the Go mechanism for keeping to it.

## Traces and metrics through OpenTelemetry

OpenTelemetry's Go SDK lists traces and metrics as stable. A service creates its tracer and meter providers in `main`, exports over OTLP to a collector, and shuts them down on exit so the last spans are flushed. Incoming HTTP is instrumented by wrapping the handler with the OpenTelemetry `net/http` instrumentation, which starts a span per request and puts it in the request's context; outgoing HTTP is instrumented by wrapping the client's transport, which propagates the trace to the next service. Everything between receives the span through the context it is already passed.

A span is started for an operation a reader would want to see on a timeline — a database query, a call to another service, a unit of business work — not for every function. A metric is a number someone will put on a dashboard or alert on: a request count and duration by route and status, a queue depth, a pool's in-use connections. Metric attributes are low-cardinality — a route template, never a raw path with an id in it — because each distinct value is a separate time series.

OpenTelemetry's logs signal is a release candidate in its Go documentation. Logs stay on `slog`, joined to traces by the identifiers above, until it is stable.

## Where this stops

**What an on-call reader needs from a change is not decided here.** Whether a failure path logs enough, whether a critical operation emits a metric, whether a request can be followed across services, is the observability plugin's review discipline, in any language. This page is how Go code meets it.

**No log format, retention or backend is chosen.** JSON to standard output is the twelve-factor default and what `slog.JSONHandler` produces; where it goes from there is the platform's.

**Profiling is mentioned only once.** `net/http/pprof` exposes CPU, heap and goroutine profiles, and from Go 1.27 the `goroutineleak` profile; it is how a running service is diagnosed, which the `debugging-go` skill uses. It is not an observability signal a dashboard reads.

**Sensitive data is the security plugin's to define.** This page names the Go mechanism, `LogValuer`, and nothing more.
