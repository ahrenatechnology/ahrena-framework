---
id: result-errors
type: doc
clade: engineering
subclade: architecture
title: Why an expected failure is a value and the stack stays on the span
summary: What a Result buys over an exception, where the expected/unexpected line falls, why the stack trace has exactly one home, and where each threshold in the rule came from.
references:
  - rules/result-errors.md
  - docs/solid.md
---

# Why an expected failure is a value and the stack stays on the span

This is the companion to [`rules/result-errors.md`](../rules/result-errors.md). The rule states the conditions; this explains what they protect and where the numbers came from.

## Why a value

An exception is invisible in a signature. A caller of `reserveStock` cannot tell from the type that "out of stock" is a case it has to handle, so the case is handled by whoever remembered, and the one who forgot ships a 500 for a situation the domain has a name for. A `Result` puts the case in the return type: the compiler or the type checker refuses a caller that ignores it. That is the whole argument, and it is the dependency argument of [`docs/solid.md`](solid.md): the domain declares what can happen, and the layer above is told, rather than discovering at run time.

The maintainer's decision, 14 November 2026, is `Result` over exception for expected failure. It is declared maintainer policy (#34), not a measurement, and the threshold in ERR-1 is the policy written as a count: 0 `throw` in the domain and use-case layers, for new and changed lines. The catalog applies limits to new lines and a ratchet to the total, so the existing code does not block a merge; an indicator that gets worse does.

## The line between expected and unexpected

| | Expected | Unexpected |
|---|---|---|
| Example | stock is zero, the email is taken, the token expired | a null where the type said none, a dependency that is down, a broken invariant |
| Who can act | the caller, with a different request | a person on call, with the trace |
| Carried by | a `Result`, in the return type | an exception, caught once at the boundary |
| Reaches the caller as | a domain error code, mapped to the project's shape | the project's generic error shape, with a stable code |

The one `throw` the rule permits is the broken invariant, raised through a helper the project declares. A helper gives the exceptions one name to search for, so "0 `throw` outside the helper" is a count a script can make.

## One home for the stack

A stack trace is the most useful object in a diagnosis and the most dangerous in a response: it names files, versions, queries and sometimes values. The decision is that it has one home, the span.

- OpenTelemetry's trace specification says an exception SHOULD be recorded as an event on the span, named `exception`, with `exception.type`, `exception.message` and `exception.stacktrace`, and that the span status is set to error when it remains unhandled. Source: OpenTelemetry Specification, Trace, Exceptions (<https://opentelemetry.io/docs/specs/otel/trace/exceptions/>), read on 14 November 2026.
- The semantic conventions mark `exception.message` as possibly carrying sensitive information, which is why the observer's redaction (condition 1 of `rules/log-records.md` in the observability plugin) applies to it before export.
- The response is the other half: ERR-2 and ERR-3 say what the caller gets. gRPC's own error guide lists stack traces among the details a richer error model *can* carry; it is a capability, not guidance, so the ban here is maintainer policy and not borrowed authority.

Saying both in one place is the point. A rule that only says "no stack in the response" leaves a developer with nowhere to put it and a `console.error` in the handler; a rule that only says "record the exception" leaves the response alone. Together they say where it goes and where it does not.

## Where the numbers came from

| Condition | Threshold | Source |
|---|---|---|
| ERR-1 | 0 `throw` outside the invariant helper, new lines | declared maintainer policy, #34 and #323 |
| ERR-2 | 0 stacks or raw messages in a response | declared maintainer policy; the exposure class is held by the security plugin |
| ERR-3 | 1 forcing test per route | declared maintainer policy; one is the least that proves the shape |

None of the three is measured against the framework's own code, because it contains no routes. That is stated rather than hidden, as in [`docs/contract-first.md`](contract-first.md).

## Where this stops

This document does not choose the shape of the `Result`, the error schema of a response or the helper's name; those belong to the consuming project's component map. It does not cover a language whose idiom already is the error value, where the language plugin's rule decides.
