---
id: cross-cutting-concerns
type: rule
clade: engineering
subclade: architecture
title: Concerns belong at a boundary
statement: Retry, transaction control, idempotency and metrics are declared once at a boundary; a hand-rolled one inside a body is the defect.
enforcement: judgment
references:
  - docs/cross-cutting-concerns.md
---

# Concerns belong at a boundary

Five conditions covering four concerns. Conditions 1 to 3 are decided by `hooks/check-structure.py`; conditions 4 and 5 need a test run or a count across the tree, and the final section says why that makes this a judgment rule rather than a hook. `docs/cross-cutting-concerns.md` explains what each concern costs when it is inlined, where the one count came from, and the cases where a decorator is the wrong shape.

A cross-cutting concern is one that every operation at a boundary needs and no operation is about. Written inline it is implemented once per author: three retry loops with three different backoff curves, two of which have no jitter and one of which retries a non-idempotent write. Written at the boundary it is one policy, changed in one place, testable without the work it wraps and vice versa.

The concern the four have in common is which side of the boundary they are declared on, and that is the same dependency-direction argument condition 6 of `rules/solid.md` makes. This rule is the concrete version of it for four specific concerns.

Condition 5 adds structure, so it is gated by the abstraction trigger declared in condition 1 of `rules/yagni.md`. A rule may reference only a doc, so the trigger is named here in prose rather than linked. It reads: an abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam. Conditions 1 to 4 describe a state rather than prescribe a wrapper, and the trigger does not gate them.

## Conditions

1. **A loop that catches an exception and backs off is a retry written inline.** The state is a `for` or `while` inside a function body containing both an exception handler and a call to a sleep. Each of the three alone is something else: a loop with a handler and no sleep is a scan that tolerates failures, a loop with a sleep and no handler is a poll, and a handler with no loop is error handling. The conjunction is what makes the shape specific, and it is what the detector requires. Decided by `hooks/check-structure.py` for Python, and by a reviewer elsewhere.

2. **A function that both commits and rolls back owns a transaction boundary as well as the work inside it.** The state is a call to `commit` and a call to `rollback` in one function body. Either alone is legitimate — a lone commit is a caller at a boundary that already owns the unit of work, and a lone rollback is a compensation — and the pair is the boundary written inside the operation. The fix is to let the body raise and let the boundary decide. Decided by `hooks/check-structure.py` for Python, and by a reviewer elsewhere.

3. **A function that reads a clock twice and subtracts is measuring itself.** The state is two or more calls to a clock in one function body with a subtraction among its expressions. One read is a timestamp, which is data; two and a difference is a measurement, and a measurement taken inside the work it measures cannot be turned off, sampled, relabelled or given a histogram without editing the work. Decided by `hooks/check-structure.py` for Python, and by a reviewer elsewhere.

4. **A mutating operation on a published surface accepts an idempotency key and consults a store keyed by it before doing the work.** The detector is a test that issues the same request twice with the same key and asserts exactly one effect and two identical responses; the violation is that test failing or not existing. The retention window for the store is an input the consuming project states, because it is set by the client's retry budget rather than by anything this plugin knows; what the condition requires is that the window be written down. Decided by that test, and by a reviewer for the surfaces that have none.

5. **The third inline occurrence of the same concern becomes the boundary.** Two occurrences are a coincidence; the third is a policy nobody has written down. Three is the rule of three that condition 4 of `rules/solid.md` already uses for the discriminator chain and that condition 2 of `rules/value-semantics.md` uses for the data clump — one arbitration mechanism, reused. Decided by a reviewer counting occurrences across the tree. Gated, and satisfied by construction: the third occurrence is the second consumer and then some.

## Where this stops

**Condition 1 does not reach a retry that belongs in the body.** A loop reconciling a domain invariant — re-reading a version and reapplying an operation after an optimistic-concurrency conflict — is domain logic that happens to look like a retry, because the decision to try again depends on what the operation means. What the condition catches is the transport-level retry, where the decision depends only on the kind of failure.

**Condition 1 does not reach the boundary's own implementation.** The decorator this rule asks for contains a loop, a handler and a sleep, because that is what a retry is. Exclude the module that implements the policy by path; the condition is about the concern appearing in operations, not about it existing.

**Condition 2 does not reach a saga or a compensating transaction.** A long-running process that commits each step and compensates a failed one is committing and rolling back deliberately, at a boundary it owns, and that is the correct shape for work that cannot hold a database transaction open. The distinction is whether the commit and the rollback are the operation's subject or its plumbing.

**Condition 2 does not reach a test.** A test that commits and then rolls back to isolate itself is doing exactly the right thing, and the fixture that does it is a boundary. Exclude the test tree by path.

**Condition 3 does not reach a duration that is the result.** A benchmark, a rate limiter measuring an interval, a cache computing an age and a scheduler deciding whether a deadline passed all read a clock twice and subtract, and in every one of them the number is what the function is for rather than a report about it. The condition is about measurement emitted as a side effect of doing something else.

**Condition 4 does not reach a naturally idempotent operation.** A write that sets a value rather than adjusting one, a delete, and a read are all replay-safe without a key, and requiring one buys a store lookup and nothing else. It also does not reach an internal call inside one deployment unit where the caller is the only retrier and it retries in memory.

**Condition 4 states no retention window on purpose.** A window that is too short reopens the duplicate it was preventing and one that is too long is a store that only grows, and the right value is the client's maximum retry span plus a margin. Naming a figure here would be this framework guessing at somebody else's timeout, which is the same reason condition 6 of `rules/solid.md` asks a reviewer for the layer map instead of shipping one.

**Condition 5 does not make the decorator the only shape.** A decorator is one way to apply a concern at a boundary, and middleware, an interceptor, a context manager, a pipeline stage and the framework's own extension point are others; which one fits is decided by the stack. What the condition requires is one place, not one mechanism. Nor does it apply to a concern the platform already provides: a service mesh that retries, a database driver that manages the unit of work and a runtime that emits request latency are all boundaries that exist, and reimplementing them one level up is the inlining this rule objects to, moved.

**Condition 5 does not survive three genuinely different policies.** Three call sites that retry with three different budgets because they talk to three services with three different failure profiles are not one policy occurring three times. Collapsing them produces a decorator with a configuration argument per call site, which is the shape condition 4 of `rules/yagni.md` deletes. The count is a trigger for the question, and the question is whether the three are the same policy.

**This rule declares judgment rather than a hook, although three of its five conditions have a script.** Conditions 4 and 5 need a replay test and a count across the tree, and `enforcement` decides how a rule reaches an agent: a hook rule is replaced by its script and contributes no text, a judgment rule contributes its statement. Declaring a hook here would deliver the three shapes a parser can see and silently drop the two that carry the arbitration — including condition 5, which is the one that says when a boundary is warranted at all. The script still exists and conditions 1 to 3 name it, so a reviewer and a pipeline can both run it; what it does not do is stand in for the rule. `rules/solid.md` takes the same route for the same reason and its final section sets out the trade.

**The three shipped detectors are unproven against real code, and that is stated rather than hidden.** The framework's own Python contains no persistence, no network calls and no instrumentation, so the corpus that produced the measured false-positive counts in `docs/clean-code.md` and `docs/value-semantics.md` cannot exercise these three at all: it returns zero findings because there is nothing of the kind in it, not because the detectors are quiet. What backs them is the fixture suite, which pins each condition against the three carve-outs above it, and the conjunctions in the conditions themselves. `docs/cross-cutting-concerns.md` says what would change the picture.

**The detector parses Python and nothing else.** The standard library ships one parser and this plugin takes no dependencies. In any other language these three conditions are read by a reviewer, which is the weaker route and is stated here rather than left to be discovered.
