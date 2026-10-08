---
id: cross-cutting-concerns
type: doc
clade: engineering
subclade: architecture
title: Four concerns and the boundary they belong to
summary: What each of transactions, resilience, idempotency and metrics costs when it is written inline, why the four are one rule, what the shipped detectors can and cannot claim, and when a boundary is the wrong shape.
references:
  - rules/cross-cutting-concerns.md
  - docs/solid.md
  - docs/simplicity.md
---

# Four concerns and the boundary they belong to

This is the companion to [`rules/cross-cutting-concerns.md`](../rules/cross-cutting-concerns.md). The rule states five conditions and names what decides each one; this explains what each concern costs when it is inlined, why four apparently unrelated subjects are one rule, and what the shipped detectors are and are not evidence of.

## Why these four are one rule

They look like four subjects. Transactions are a persistence question, resilience a networking question, idempotency a protocol question, metrics an operations question, and they are owned in most organisations by four different people.

They are one rule because they share a defect, and the defect is structural rather than topical. Each of them is needed by every operation at a boundary and is about none of them. That combination has one consequence: if the concern is not applied at the boundary, it is applied by each author, and each author applies a slightly different version.

The result is not "some operations lack retries". It is worse and less visible: every operation has a retry, no two are the same, and nobody can state the system's retry policy because there is not one. The same for transactions — three functions with three different ideas about where the unit of work begins — and for metrics, where the histogram buckets differ per endpoint so the dashboard cannot aggregate them.

**The property that makes a boundary work is that the concern becomes stateable.** One place to read, one place to change, one place to turn off. That property does not survive being distributed, however good each individual copy is.

This is the dependency-inversion argument from `docs/solid.md` applied to four specific things. The operation is policy; retry, transactions, idempotency and instrumentation are mechanism; an operation that implements them has taken a dependency on mechanism it should have been handed.

## Transactions

**What inlining costs.** The transaction boundary decides what is atomic, and a function that commits has decided that on behalf of every caller — including the caller that wanted to do two of these things together. The second caller then has three options, all bad: call both and lose atomicity, duplicate the body without the commit, or add a flag argument that suppresses it, which condition 2 of `rules/kiss.md` rejects for separate reasons.

**The detector, and why it needs both calls.** A commit and a rollback in one body. Either alone is fine and common. A lone `commit()` is usually a caller sitting at a boundary that already owns the unit of work — a request handler, a job runner — and that is exactly the arrangement the rule wants. A lone `rollback()` is usually a compensation in an error path. The pair is what says this function is managing the lifecycle rather than participating in one, and pairing them is what keeps the detector off the correct shape.

**Where it stops paying.** On a saga. Work that cannot hold a database transaction open across its steps commits each step and compensates the failed one, and the commits and rollbacks are then the subject of the code rather than its plumbing. And in tests, where committing and rolling back to isolate a case is the fixture doing its job.

## Resilience

**What inlining costs.** Retry is the concern where the copies differ most and the differences matter most. Backoff curve, jitter, maximum attempts, which exceptions are retryable, whether the operation is safe to repeat at all — five decisions, made independently at every call site, most of them by an author who was thinking about something else. The absence of jitter is the classic one: every client retries on the same schedule and the recovering service is knocked over by the retry storm.

A circuit breaker cannot be written inline at all, which is the sharper version of the argument. It needs state across calls to know whether the downstream is failing, and a function-local loop has none. Teams that inline retries usually have no breaker, and the missing breaker is why the retries turn a slow dependency into an outage.

**The detector, and what the conjunction buys.** A loop, an exception handler and a sleep, all three inside one function. Any two of the three are a different thing. A loop and a handler with no sleep is a scan that tolerates failures — iterating files and skipping the unreadable ones — and it is correct. A loop and a sleep with no handler is a poll, also correct. A handler and a sleep with no loop is a delay before giving up. Requiring all three is what makes the detector specific enough to be worth running.

**Where it stops paying.** On a domain retry. Re-reading an aggregate after an optimistic-concurrency conflict and reapplying the operation looks identical to a transport retry and is not one: the decision to try again depends on what the operation means, so it cannot be lifted to a boundary that does not know. And on the policy's own implementation, which contains exactly this shape because that is what a retry is.

## Idempotency

**What inlining costs.** This is the concern that is usually not implemented at all rather than implemented inconsistently, and it is the one whose absence is most expensive: the duplicate charge, the duplicate order, the duplicate email.

The reason it goes missing is a reasoning error that is worth naming. Idempotency is not needed because clients are badly behaved. It is needed because at-least-once delivery is the only delivery anyone can actually offer over a network: a client that times out cannot tell a request that was lost from one that succeeded with a lost response, so a correct client retries, and a correct server must be able to absorb it.

**The detector, and why it is a test rather than a shape.** Nothing in the source says whether an operation is replay-safe. The property is behavioural, so the detector is behavioural: issue the same request twice with the same key and assert exactly one effect and two identical responses. That test is also the documentation, because it states what "the same request" means for that operation, which is the part teams disagree about.

**Why the rule names no retention window.** The window is set by the client's retry budget: it must outlive the longest sequence of retries a client will make, and it must not outlive it by so much that the store becomes permanent. Nobody outside the deployment knows that number. The rule requires it to be written down rather than choosing it, which is the same move condition 6 of `rules/solid.md` makes when it asks a reviewer for the layer map instead of shipping one.

**Where it stops paying.** On operations that are already replay-safe. A write that sets a value rather than adjusting one, a delete and any read absorb a duplicate with no key and no store, and adding one buys a lookup per request and nothing else.

## Metrics

**What inlining costs.** An inline timer cannot be turned off, sampled, relabelled, or given different histogram buckets without editing the function it measures. That is a small cost per function and a large one per system: changing how latency is aggregated becomes a change across every measured operation, so it does not happen, so the aggregation stays wrong.

There is a subtler cost. Metrics written by the author of the operation measure what that author found interesting, which is usually the part they were worried about. Metrics applied at a boundary measure the same three things for every operation — count, duration, outcome — which is what makes them comparable, and comparability is the entire value of a dashboard.

**The detector.** Two clock reads and a subtraction. One read is a timestamp, which is data that belongs to the domain: an order has a placed-at, an event has an occurred-at. Two reads and a difference is a measurement of elapsed time, and a measurement of elapsed time taken inside the work is the shape the condition names.

**Where it stops paying.** When the duration is the result rather than a report about it. A benchmark, a rate limiter measuring an interval, a cache computing an age, a scheduler checking a deadline: all read a clock twice and subtract, and in every one the number is the function's output. The detector cannot tell those apart and the carve-out is stated in the rule rather than guessed at by the script.

## What the detectors are evidence of, and what they are not

`docs/clean-code.md` and `docs/value-semantics.md` each report a false-positive count measured over the framework's own 2,291 lines of Python. This document cannot, and the difference is worth being explicit about rather than quietly omitting.

That corpus is two gate scripts and their test suites. It has no database, no network call, no sleep and no instrumentation. Running the three detectors over it returns zero findings, and zero findings there means only that the corpus contains nothing of the kind — it is not evidence that the detectors are quiet on code that does.

What backs them instead is two things. The first is the conjunctions: each condition requires two or three co-occurring shapes rather than one, and the carve-out fixtures in `hooks/test-check-structure.py` pin each of the near-misses — the poll loop, the catch-without-backoff, the lone commit, the single clock read, the two reads with no difference between them. The second is that each condition's known false positive is named in the rule rather than discovered later: the domain retry, the saga, the test fixture, the duration that is the result.

**What would change the picture** is running them over a service. Until that has happened, these three conditions are held to a lower standard of evidence than the other eight in the same script, and a reader deciding whether to wire the hook into a pipeline should know which is which. `docs/simplicity.md` records the case where a detector that looked definitional turned out to fire on a common idiom and was deleted rather than tuned; that outcome remains available for these.

## Where a boundary is the wrong shape

**When the platform already has one.** A service mesh that retries, a driver that manages the unit of work, a runtime that emits request latency and a broker that deduplicates are all boundaries that exist. Writing a second one a level up is the inlining this rule objects to, moved up a floor, and it produces the worst outcome available: two retry policies composing into a multiplication nobody intended.

**When three call sites have three genuinely different policies.** Three services with three failure profiles need three retry budgets, and collapsing them produces a decorator with a configuration argument per call site — the shape condition 4 of `rules/yagni.md` deletes. The rule of three is a trigger for the question, not the answer, and the question is whether the occurrences are one policy.

**When the decorator would hide something the caller must see.** A wrapper that swallows an exception to retry it also swallows the information that the first attempt failed, and a caller that needed to know — to fall back, to degrade, to tell a user — now cannot. Applying a concern at a boundary is only free when the boundary is where the decision belongs; when the caller has to participate, the wrapper has taken a decision away from it.

**When there is one operation.** The abstraction trigger applies, as condition 5 of the rule says: one inline occurrence and no test substituting at the seam is one implementation behind one interface. Write it inline and extract it at the third occurrence, which is when it becomes a policy.

## Where this stops

**This document does not name libraries.** Which retry library, which metrics client, which decorator syntax and which middleware stack are all decisions belonging to a language and a deployment, and they change faster than a rule should. The conditions are about where the concern is declared, not about what declares it.

**It does not cover the other cross-cutting concerns.** Authentication, authorisation, input validation, caching, logging, tracing and rate limiting are all boundary concerns by the same argument, and none of them is in the rule. The four here are the four the rule can either detect or test; the rest are covered by the argument in this document's opening and by nothing mechanical.

**It does not settle what a boundary is.** The rule requires that a concern be declared at one, and which layer that is in a given system depends on a layer map the plugin does not ship. `docs/simplicity.md` records the same gap for condition 6 of `rules/solid.md`, and both close when a bounded-context layout artifact exists.

**It says nothing about ordering.** Four decorators at one boundary compose in an order that matters — a timer outside a retry measures the whole sequence, inside it measures one attempt, and an idempotency check on the wrong side of a retry defeats both. That is a real design question with real wrong answers, and it belongs with the pattern material rather than here.
