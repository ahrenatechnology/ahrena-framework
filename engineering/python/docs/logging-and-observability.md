---
id: logging-and-observability
type: doc
clade: engineering
subclade: python
title: Logs where the failure is handled, measurements at the boundary
summary: How a Python service meets the observability plugin's four conditions — structured logs through the standard logger tree with structlog, context bound once per request, failures logged where they are handled, spans and metrics from OpenTelemetry at the boundary rather than in the body — and which of the predecessor's logging and telemetry mandates were set aside and why.
references:
  - docs/libraries.md
  - rules/security.md
  - docs/web-services.md
  - rules/error-handling.md
  - rules/typing.md
---

# Logs where the failure is handled, measurements at the boundary

The observability plugin owns this concern. Its review skill asks four questions of a change: is a failure logged with something a reader could act on (OBS-1), is a critical operation counted or timed (OBS-2), does a log line say what and to whom (OBS-3), and can a request be followed across services (OBS-4). It names no library. This page is how a Python service answers the four, with the libraries [`libraries.md`](libraries.md) recommends: the standard library's `logging` with structlog for logs, OpenTelemetry for traces and metrics.

It replaces two documents and a procedure from the predecessor — 787 lines on Loguru, a logging decorator, a telemetry decorator and their set-up — and it is shorter because two of their mandates are set aside. The section after next says which and why.

## What the specification says

- **Loggers form a hierarchy named by dotted paths, and a record propagates to its ancestors' handlers**: PEP 282 and the Library Reference, `logging`, *Logger Objects*. That is why one configuration at the root decides output for every library.
- **Context that follows a request across `await` points** is a context variable: PEP 567 and the Library Reference, `contextvars`. structlog's bound context is built on it.
- **Trace propagation across services** is the W3C *Trace Context* recommendation; the instrument types for metrics are those of the OpenTelemetry specification's *Metrics API*.

## One logger tree, structured

Every library a service uses — SQLAlchemy, httpx, uvicorn, botocore — logs through the standard library's `logging`, so the service's own records go there too, and one configuration at start-up decides level and output for all of them. A module takes its logger once, at the top: `logger = structlog.get_logger(__name__)`, or `logging.getLogger(__name__)` where structlog is not in use.

Records are structured: an event name and fields, not a sentence with values formatted into it. `logger.info("order.paid", order_id=order.id, amount=order.total)` produces a record a query can filter on `order_id`; `logger.info(f"Order {order.id} paid")` produces a string someone has to parse back. In production the renderer writes one JSON object per record; on a developer's terminal it writes the same fields for a person. Which renderer runs is a setting, not a code path.

## Context is bound once, at the edge

The request id, the tenant, the authenticated principal and the operation name belong on every record a request writes, and they are known at the edge. A middleware binds them with `structlog.contextvars.bind_contextvars` when the request arrives and clears them when it leaves; a job handler does the same with the identifiers in its event. Every record written during the request carries them without the code that writes it knowing they exist. That is what OBS-3's exemption describes — context attached once by the logger — and it is what makes a log line in a repository three layers down searchable by request.

Bound context is the place where sensitive data leaks most quietly, because it is attached to everything. Bind identifiers, never values: a user's id, never their email or document number; a payment's id, never its card. DAT-1 in the security plugin reads exactly that, and a field-name denylist in the renderer is a backstop, not the control.

## A failure is logged where it is handled

OBS-1 asks for a failure to be logged where it is handled, with the identifiers of what the code was acting on. In Python that means a handler that decides something — returns a default, retries, translates into a domain error — logs with `logger.exception` or `logger.warning(..., exc_info=True)`, and the fields name the entity. A handler that re-raises does not log; whoever finally handles it logs once, and the exception carries its cause through `raise ... from`. A failure logged at every layer it passes through is five records for one event, each with less context than the last.

The outermost handler — the service's catch-all for `Exception`, described in [`web-services.md`](web-services.md) — logs what nothing below handled, with the request's bound context, and returns a generic body. Condition 5 of [`rules/typing.md`](../rules/typing.md) recognises `logger.exception` and its siblings as a trace, so a handler written this way passes the hook; condition 1 of [`rules/error-handling.md`](../rules/error-handling.md) is why the catch-all catches `Exception` and not `BaseException`.

## Spans and metrics at the boundary, not in the body

OpenTelemetry's instrumentation packages for FastAPI, SQLAlchemy or asyncpg, httpx and `logging` produce a span for every request, query and outbound call, propagate the W3C trace context on every outbound request, and put the trace and span ids on every log record. That answers OBS-4 without a line in the application, and it answers most of OBS-2's latency question too: the request and the query are already timed.

What remains is the business operation the platform cannot see: a payment captured, a refund refused, a batch reconciled. Count it where it is declared, once, at a boundary. The fundamentals cross-cutting-concerns rule makes a function that reads the clock twice and subtracts a defect — measurement inside the work cannot be turned off, sampled or relabelled without editing the work — and asks for the measurement at the boundary. In Python the boundary is a decorator on the use case, a middleware, or a domain event a subscriber counts. Which of the three depends on what the count needs to know: a decorator sees arguments and the outcome, a subscriber sees the event's fields.

Metrics follow OpenTelemetry's instrument types. A counter for what only grows — operations completed, by outcome. A histogram for a distribution — a duration, a size — which aggregates across instances where a client-side summary does not. An up-down counter for what rises and falls — items in flight. An observable gauge for what is sampled — a queue's depth. Attributes on a metric are kept to small closed sets — an outcome, a currency, a route template — because every distinct value is a separate time series, and an id as an attribute is a series per request.

## What a unit emits is a list of fields

Nothing sensitive leaves the layer that owns it. The rule is language-agnostic and belongs to the security plugin (#294, which places it under `engineering/security/rules/`): a credential, personal data, an access policy, a resource identifier, infrastructure layout, or a whole configuration, error or upstream response never reaches an output, a log, a trace, an error message or a response, and what a unit emits is an allowlist of named fields. It was written after an access-denied message from a cloud SDK — account id, role, denied action, resource path — reached a client verbatim in a 500 body. This section is how Python holds it.

- **A type that carries something sensitive redacts its own representation.** `repr()` and `str()` are what a log, a traceback and an f-string call (Language Reference §3.3.1, `__repr__` and `__str__`), so the type decides what they show: `field(repr=False)` on a dataclass field (Library Reference, `dataclasses.field`), `SecretStr` or `Field(repr=False)` on a Pydantic model, or a written `__repr__` that names the type and its identifier and nothing else. A settings object holding a connection string is such a type, and so is a domain value holding a document number.
- **The logger is given named fields, never an object.** `logger.info("policy.applied", policy_id=policy.id)`, not `logger.info("applied %s", policy)`, not `vars(policy)`, `asdict(policy)`, `policy.model_dump()` or `json.dumps(response)`. Each of the latter writes whatever the object holds today and whatever it is given tomorrow; the allowlist is the list of keyword arguments.
- **An error is translated before it crosses the boundary.** A driver's, an SDK's or a third party's exception carries their detail in its message; `str(exc)` is that message. The adapter that catches it logs it internally — with the request's identifiers and without a secret — and raises the domain's own exception, whose message the service wrote. The edge then returns the generic body and the correlation id, never the original message: [`web-services.md`](web-services.md) shows it. A traceback is the same detail in another form and stays in the internal log.
- **Exception notes and `__cause__` travel with the exception.** `raise DomainError(...) from exc` keeps the provider's exception on `__cause__` for the internal log (PEP 3134), and that is right; what must not happen is rendering the chain into anything the caller sees.

`reviewing-python` carries the condition (PY-9) a reader checks; the hook that decides the language-agnostic shape is #294's.

## What was set aside, and why

**Loguru.** [`libraries.md`](libraries.md) argues it in full: it replaces the standard logger tree that every dependency writes to, rather than joining it.

**"No function body calls the logger."** The predecessor allowed logger calls in three modules — the set-up, the decorator, the top-level handler — and required everything else to be instrumented by a decorator that records entry, exit and error. Its purpose was right: instrumentation should not crowd the business logic. But a decorator wrapped around a function cannot see what the function found halfway through, which is exactly the identifier OBS-1 asks for, and a rule against logging in a body forces a failure handled in the middle of a function to be either silent or moved into a helper invented to carry a decorator. The owning plugin asks for the failure to be logged where it is handled, and the owning plugin wins. What survives of the purpose is the boundary rule for measurements in the section above, which the fundamentals plugin already states.

**The outcome classifier on a result type.** The predecessor's telemetry decorator inspected a `Result` to count failures that were not exceptions. The result type was dropped by #34; with exceptions as the error model, an outcome is what the boundary saw — a normal return or which exception — and a domain event names a refusal that is not an error.

**A `/metrics` endpoint as a rule.** Whether metrics are pulled from an endpoint or pushed over OTLP is the platform's choice. When it is an endpoint, it is mounted once by the application factory and is not reachable from outside the network.

## Where this stops

**It does not choose a backend.** Where logs, traces and metrics go is the platform's; OpenTelemetry is chosen so that the code does not need to know.

**It does not decide what is critical.** OBS-2's own correction leaves that to the owner as a question when a change does not settle it, and so does this page.

**It does not configure the logging.** The processor chain, the renderer, the levels per logger: the project's, set once at start-up. This page argues what those settings have to produce.

**It does not cover alerting or dashboards.** What a person is woken for is an operational decision about the signals produced here, not part of producing them.
