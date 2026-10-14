# Observability

The conditions `reviewing-observability` applies. Each gives the state, how it is detected, what exempts it, and the correction. The party who pays is whoever is on call: every condition here is about what they would have to work with when the operation fails or misbehaves in production.

**Every correction adds context, never a value.** The fix for a thin record is more of what identifies the operation — an id, a count, the name of the step — never the data itself. A correction that would log a secret, a credential, a token or personal data is a `reviewing-sensitive-data` finding (DAT-1), not an observability one.

### OBS-1 A failure with no actionable log

- **State:** an error caught, returned or raised on a path where nothing is logged, or logged with nothing a reader could act on — so an outage leaves no record of what failed.
- **Detect:** each error handler and each error-returning call the route pointed at. Read whether a log is written, and whether it names the operation and the entity it concerns.
- **Exempt:** a failure logged with context by a middleware, decorator or framework handler that already wraps this path, when the finding can name where; an expected, handled condition that is not a failure.
- **Correct:** log the failure where it is handled, with the operation, the identifiers of what it was acting on, and the error — the identifiers, never the sensitive values behind them.

### OBS-2 A critical operation with no metric or event

- **State:** an operation whose success, failure or duration the business or on-call needs to see — a payment, a state transition, a job run, a login, an external call — completing with no metric, counter or domain event emitted, so it is invisible until someone complains.
- **Detect:** each operation the change adds or changes that is on a path that matters. Read whether its outcome is counted, timed, or published as an event.
- **Exempt:** an operation already measured by a metric the platform, gateway or framework emits for free, when the finding can name it; an operation that is genuinely not material.
- **Correct:** emit a counter or an event for the outcome, and a duration where latency matters, through the metrics client the repository already uses. Which operations are material enough to measure is a **question** for the owner when the change does not settle it.

### OBS-3 A log line with no context

- **State:** a log that names a condition and not its subject — `log.error("error")`, `"failed"`, `"something went wrong"` — so the line proves a thing happened and not what, where, or to whom.
- **Detect:** each log call the route pointed at. Read whether the message and its fields identify the operation and the entity, or only assert that an event occurred.
- **Exempt:** a message whose context is carried in structured fields attached elsewhere on the path — a request id, a tenant, an operation name set by the logger — when the finding can name where.
- **Correct:** add the operation and the identifiers as structured fields so the line is searchable and self-explaining — the id of the record, never its sensitive contents.

### OBS-4 A service edge with no correlation id

- **State:** a boundary where a request enters, leaves or is picked off a queue — an inbound handler, an outbound call, a consumer — that neither reads nor propagates a correlation or trace id, so one request cannot be followed across services.
- **Detect:** each entry point, outbound call and message publish or consume the route pointed at. Read whether a correlation or trace id is taken from the incoming context and passed on.
- **Exempt:** an edge where the framework, service mesh or messaging library propagates the trace context automatically, when the finding can name it.
- **Correct:** read the correlation or trace id from the incoming request or message and attach it to the logs and to every call and publish the operation makes, so one identifier threads the whole request.
