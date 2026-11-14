---
id: web-services
type: doc
clade: engineering
subclade: python
title: A FastAPI service at the edge of the layers
summary: How a FastAPI route stays an adapter — validate with a Pydantic model, call one use case, map the result — where the composition root lives, how a domain failure becomes a stable error body, what to make of frozen response models and idempotency keys, and how the whole service is tested without a patch.
references:
  - docs/architecture.md
  - docs/libraries.md
  - docs/testing.md
  - rules/error-handling.md
  - rules/security.md
  - rules/testing.md
---

# A FastAPI service at the edge of the layers

[`architecture.md`](architecture.md) puts the HTTP routes in `infra/`, as adapters: they turn a request into a call to a use case and the result into a response, and they own nothing else. This page is how that reads in FastAPI, which [`libraries.md`](libraries.md) recommends and argues. It is the predecessor's FastAPI manual with its rules kept where they hold, its error handling tied to the rule that now decides part of it, and one of its mandates — frozen response models — argued down to a preference.

## What the specification says

- **Status codes have the meaning RFC 9110 gives them**: `422` for content that is well formed and cannot be processed (§15.5.21), `202` for work accepted and not yet done (§15.3.3), `500` for a failure the server did not expect (§15.6.1).
- **A machine-readable error body** has a standard form in RFC 9457, *Problem Details for HTTP APIs*; a service that has not chosen a shape should take that one.
- **The `Idempotency-Key` header** is specified in the IETF HTTP APIs working group's draft, *The Idempotency-Key HTTP Header Field*; it is a draft, and the header is used as it describes.
- FastAPI runs on ASGI, whose specification is maintained by the Django project's `asgiref`, not by a PEP; WSGI, the synchronous predecessor, is PEP 3333.

## A route validates, delegates and maps

A route does three things, and a fourth is a defect:

1. **It validates.** The request body is a Pydantic model and the path and query parameters are annotated; FastAPI refuses what does not fit with a 422 before the route body runs. That is the boundary validation the predecessor's security law required, done by declaration. It also answers INP-8 of the security plugin: a model names the fields a caller may set, and anything else is not bound.
2. **It calls one use case**, received through `Depends`, with a command built from the validated input and from what the server decides — the caller's identity from the authenticated principal, never from the body.
3. **It maps the result** to a response model with a classmethod such as `from_domain`, so the response's shape is declared beside the route and a domain field added tomorrow does not leak out by default — DAT-2 in the security plugin.

The fourth thing is business logic: a branch on a domain rule, a computation, a second write. When a route grows one, the use case is missing it. The predecessor's two corollaries stand: a route never builds a repository or a session itself, and never raises `HTTPException` from below the edge.

One router per resource or per bounded context, under the context's `infra/`. The request and response models live beside the router, not in the domain, because they are the HTTP contract and change at its pace.

## The composition root is `Depends`

The session, the repositories, the clients and the use case are built by `Depends` factories that chain into each other, so one request gets one graph with the lifetimes HTTP needs: the session is opened by a generator factory and closed when the response is sent, whatever happened. The factories live in `infra/`, beside the routes. [`architecture.md`](architecture.md) argues why this is the whole wiring and no container is added.

The application is built by a factory function — `create_app()` — that registers the routers, the exception handlers, the middleware and the instrumentation in one place. A module-level `app = FastAPI()` that registers itself on import cannot be built twice with different adapters, and a test needs to do exactly that.

## A domain failure becomes a stable error body

The domain raises an exception named for what it refused; [`rules/error-handling.md`](../rules/error-handling.md) makes sure it is named. The edge translates, in exception handlers registered by the application factory:

- **One handler per domain exception family**, mapping it to a status and a body with a stable code the client can branch on, and a message a person can read. The body is the same shape for every error the service returns, and the shape is part of the contract the fundamentals contract-first rule asks to be authored.
- **One handler for `RequestValidationError`**, mapping FastAPI's 422 into that same shape, so a client parses one error format and not two. The predecessor's debugging procedure found this missing as its worked example, and it is the commonest gap.
- **One handler for everything else**, which logs the exception with the request's context and returns a generic 500 body with no detail. That handler catches `Exception`, not `BaseException`: an interrupt or a cancellation is the server's to act on, and condition 1 of the error-handling rule reports a handler that keeps one.

No response body carries a stack trace, a query, a driver message or a credential, and **no response body carries an upstream error as it came**. The incident behind #294 was exactly this: a handler caught a cloud SDK's access-denied exception and returned `str(exc)` in a 500 body, and the message named the account, the role, the denied action and the resource path. The adapter that calls the SDK catches its error, logs it internally with the request's identifiers, and raises a domain exception with a message the service wrote; the catch-all handler returns the generic body and the correlation id. A handler that builds a response from `str(exc)`, `exc.args` or `exc.response` is the finding, whatever the exception happens to say today. [`logging-and-observability.md`](logging-and-observability.md) has the Python means — a redacting representation, named log fields — and PY-9 of the review skill is the condition. A message that interpolates the value that failed — `f"token {token} rejected"` — is DAT-1 in the security plugin, and the fix is to name what failed, not to echo it.

## Response models: frozen is a preference

The predecessor required every response model to be frozen. A response model is built once, from a domain value, and serialised immediately; nothing holds it long enough for a mutation to surprise anyone, and freezing it changes nothing a reader or a client can observe. So it is not a rule here and [`rules/immutability.md`](../rules/immutability.md) does not read outside the domain. Freeze it if the project likes the uniformity; do not count it as a finding when it is not.

What does matter about a response model is that it is declared — `response_model` or the route's return annotation — so the fields that leave the service are a list somebody wrote, rather than whatever the domain object happens to carry today.

## Mutations carry an idempotency key

A route that creates or changes something on a published surface accepts an `Idempotency-Key` header and, before doing the work, consults a store keyed by it. That is condition 4 of the fundamentals cross-cutting-concerns rule, and its detector is a test: the same request twice with the same key gives one effect and two identical responses. The check belongs at the edge, in a dependency or a middleware, not in each use case — a key is an HTTP concern, and the use case should not know it is being retried.

## Long work does not run in the request

A route that starts work longer than a client will wait for publishes an event or enqueues a job and returns `202` with a way to check on it. `BackgroundTasks` runs work after the response in the same process and dies with it; it is for best-effort side effects such as warming a cache, not for anything that must happen.

## Testing the service without a patch

The application factory and `app.dependency_overrides` are what make the service testable the way [`rules/testing.md`](../rules/testing.md) asks: a test builds the app, overrides the repository and client factories with fakes of the ports, and drives it through `httpx.AsyncClient` over an ASGI transport. The domain and the use case run for real. No name under `domain/` or `application/` is patched, and none needs to be. [`testing.md`](testing.md) carries the fixture shapes.

The acceptance tests at the API layer — the backend plugin's outermost layer — do the same with the persistence adapter real and the database from testcontainers, so a route test and a migration are exercised together at least once.

## Where this stops

**It does not design the API.** Resource names, status codes, pagination and versioning are the contract's, authored first under the fundamentals contract-first rule; this page is how the authored contract is served.

**It does not cover authentication.** Which identity a request carries and what it may do are the security plugin's `reviewing-access` conditions; this page only insists that the identity comes from the authenticated principal and not from the body.

**It does not cover a server-rendered or admin application.** [`libraries.md`](libraries.md) says when that is Django instead.

**It does not pin FastAPI's configuration.** Middleware order, CORS origins, the server's worker count: each is the project's, and none is an argument this page can settle for every service.
