# The defects Python makes easy

Read at step 3 of `SKILL.md`, against the code on the failing path. Each entry gives the symptom a report usually describes, the cause, and how to confirm it. Where a hook decides the shape, it is named: run it on the path, because its finding may be the defect.

## Wrong value, no error

- **A default shared across calls.** Symptom: a second call sees data from the first. Cause: a parameter defaulted to a list, dict or set. Confirm: `check-typing.py` condition 4.
- **A closure that saw the last value.** Symptom: every callback acts on the final item of a loop. Cause: a lambda or inner function created in a loop that reads the loop variable when called, not when made. Confirm: PY-2 of `reviewing-python`; bind the value as a default or through a factory.
- **An argument changed under its caller.** Symptom: a caller's list or dict changes after a call it expected to be read-only. Confirm: `check-python.py`, immutability condition 2, under `domain/`; elsewhere, read the callee for an in-place method on its parameter.
- **A shared record changed by one holder.** Symptom: a value differs between two places that were handed the same object. Confirm: a dataclass without `frozen=True`, immutability condition 1.
- **Identity where equality was meant.** Symptom: passes in tests, fails in production, or the reverse. Cause: `is` against a string or an int, true for small or interned values and false otherwise. Confirm: PY-4.
- **Float arithmetic on money.** Symptom: a total off by a cent. Cause: `float`, or `Decimal` built from a float rather than a string. Confirm: PY-5.
- **A generator read twice.** Symptom: the second consumer sees nothing, with no error. Confirm: PY-6.
- **A naive datetime.** Symptom: an hour off around a daylight-saving change or between servers; a `TypeError` comparing two timestamps. Cause: `datetime.now()` or `utcnow()` with no zone. Confirm: PY-7.

## A failure that disappeared

- **A handler that kept it.** Symptom: an operation reports success and its effect is missing. Confirm: `check-typing.py` condition 5 for a blind handler with no trace; a narrower handler returning a default is read by hand.
- **A `finally` that left.** Symptom: an exception raised in the `try` never reaches anyone. Confirm: `check-python.py`, error-handling condition 3.
- **A repository that turned "unavailable" into "absent".** Symptom: a record reported missing while the database was down. Cause: a driver error caught and `None` returned. `docs/persistence.md` describes the translation that should have happened.

## A task that never finishes, or never stops

- **A coroutine never awaited.** Symptom: the work never happens; a `RuntimeWarning: coroutine ... was never awaited` at garbage collection. Confirm: `python -X dev`; PY-8.
- **A blocking call on the event loop.** Symptom: every request slows together; timeouts across unrelated endpoints. Cause: `requests`, `time.sleep`, a synchronous driver or a CPU loop inside `async def`. Confirm: `PYTHONASYNCIODEBUG=1` reports the slow callback.
- **A cancellation swallowed.** Symptom: shutdown hangs, a `TaskGroup` or a timeout never returns. Cause: `except CancelledError` or `except BaseException` without re-raising. Confirm: `check-python.py`, error-handling condition 1.
- **A call with no timeout.** Symptom: a worker stuck forever on one request. Confirm: REL-1 of the reliability plugin; `httpx` times out by default and `requests` does not.

## Fails only in some environments

- **An import cycle.** Symptom: `ImportError: cannot import name` or an attribute missing on a partially initialised module, depending on which module was imported first. Confirm: `check-boundaries.py` condition 1; a function-level import that "fixed" it is condition 3.
- **A `TYPE_CHECKING` import used at runtime.** Symptom: `NameError` on a path that only some requests take. Confirm: `check-boundaries.py` condition 4.
- **A patch that outlived its test.** Symptom: a test passes alone and fails in the suite, or the reverse. Cause: a module attribute replaced without `monkeypatch` or a `with` block, so it stays replaced; or a patch aimed at where a name is defined rather than where it is looked up. This is also why `rules/testing.md` keeps patches out of the domain.
- **An `assert` doing a check.** Symptom: a guard that works in development and not in an optimised build. Cause: `python -O` removes every `assert`.
