---
id: result-errors
type: rule
clade: engineering
subclade: architecture
title: Expected failure is a value
statement: Domain and use cases return a Result for an expected failure; an unexpected one reaches the caller with no stack, which stays in telemetry.
enforcement: judgment
references:
  - docs/result-errors.md
---

# Expected failure is a value

Four conditions. The first three carry the catalog ids ERR-1 to ERR-3 of the PR quality rubric (#323); ERR-2 is the exposure condition that condition 1 of `rules/layer-exposure.md` in the security plugin already states and `hooks/check-exposure.py` there decides. `docs/result-errors.md` explains the split between expected and unexpected failure, where each threshold came from and why the stack is said to belong in telemetry and never in a response, in one place.

An expected failure is one the caller can act on and the domain names: a rejected command, a missing record, a rule that was not met. An unexpected failure is everything else: a bug, an outage, a broken invariant. The two are handled by different mechanisms, and the conditions below say which.

None of these conditions adds an abstraction. A `Result` is a return type, not a seam, so the abstraction trigger in condition 1 of `rules/yagni.md` does not gate them. Except ERR-2, which `hooks/check-exposure.py` in the security plugin decides, each is decided by a reviewer today; the detectors are tracked in the detectors sub-issue of #323, and each condition names the one it will get.

## Conditions

1. **ERR-1. A function in the domain or use-case layer returns a `Result` for an expected failure and does not `throw` or `raise` it.** The threshold is 0 `throw` or `raise` statements in a new or changed line of those layers, outside the one invariant helper the project declares. The permitted `throw` is a broken invariant, raised through that helper, because there is no caller that can act on it. The shape of the `Result` (a discriminated union, a library type) is the project's choice and is written in its component map, once; what the condition requires is that the failure is in the return type, where the compiler or the type checker sees it. Decided by a static search for `throw` (`raise` in Python) in those layers, and by a reviewer for the layers a search cannot place.

2. **ERR-2. No error response carries a stack trace, or the raw message of an unexpected error.** The threshold is 0 occurrences. The body of an unexpected-failure response is the project's error shape with a stable code and a generic message; the detail is in the trace, per condition 3 of `rules/telemetry-sdk.md` in the observability plugin, which records the exception with its stack on the span. The condition is decided by `hooks/check-exposure.py` in the security plugin, under condition 1 of its `rules/layer-exposure.md`, and is restated here so that the two halves, the stack on the span and the shape on the wire, are read together. A reviewer reads the handler paths the hook cannot place.

3. **ERR-3. Every route has a test that forces an unexpected failure and asserts the body is the project's error shape without a stack.** The threshold is one such test per route. The test injects a failure below the route (a throwing adapter double), calls the route, and asserts that the status is the error status, the body matches the error schema, and no field contains `stack`, a file path or the injected message. The detector is the set difference between the routes the project declares and the routes those tests name, a script the project owns because it needs to know how its routes are addressed. Decided by that script, and by a reviewer where none is wired.

4. **A `Result` is not turned back into an exception inside the domain.** The state is a `throw` or `raise` whose argument is the failure case of a `Result` the same layer produced. The failure is mapped to the project's error shape at the boundary, once, in the code that owns the response. Decided by a reviewer.

## Where this stops

**ERR-1 does not reach a language whose idiom is the error value.** Go returns `error` as a second value and Rust returns `Result`; both already satisfy the condition and a second wrapper type on top would be the structure `rules/yagni.md` deletes. In those languages the language plugin's error rule decides, and this condition adds only that an expected failure is a value the caller can match.

**ERR-1 does not reach a boundary the project does not own.** A framework hook that only accepts an exception, a constructor that cannot return a value and a test assertion all throw correctly. The condition is about the domain and use-case layers the project wrote.

**ERR-1 does not make every failure a `Result`.** A broken invariant is a defect, and wrapping it in a `Result` makes a caller handle a case it cannot handle. The helper exists so there is one place to read the exceptions and one name to search for.

**ERR-2 does not reach a developer-facing channel.** A local debug mode that a person turns on, a log that never leaves the process and a trace the project's tracing backend stores are where the stack goes. The condition is about what a caller outside the process receives.

**ERR-3 does not require a test per failure kind.** One forced unexpected failure per route proves the shape; the expected failures are covered by the `Result` tests of the use case. The condition also does not apply to a route the project has marked internal and unreachable from outside the deployment unit.

**ERR-1, ERR-3 and condition 4 are judgment, and their detectors are named rather than shipped; ERR-2's ships in the security plugin.** The framework contains no HTTP route to count and no `Result` type to search for, so the detectors need the consuming project's layer map and route list, which condition 6 of `rules/solid.md` also asks a reviewer for rather than shipping one.
