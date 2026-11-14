---
id: error-handling
type: rule
clade: engineering
subclade: python
title: Exceptions that reach whoever has to act on them
statement: What catches BaseException or a cancellation re-raises it, nothing raises Exception itself, and no return, break or continue leaves a finally block.
enforcement: hook
enforced-by: hooks/check-python.py
references:
  - docs/web-services.md
  - docs/logging-and-observability.md
---

# Exceptions that reach whoever has to act on them

Three conditions, all decided by `hooks/check-python.py`. Each is a place where Python's exception model lets a failure stop travelling before it reaches the code that was meant to act on it: a handler that keeps an interrupt meant for the process, a raise that only a blind handler can catch, and a `finally` that throws away the exception in flight.

The predecessor's error-handling law had five parts, and this rule carries the three a parser decides. The other two are placed in the boundary section with where each one went. The predecessor also had a result type and an error object that its law was written around; both were dropped by #34, which ruled them an error model rather than a quality condition, and this rule does not reopen that verdict. Reversing it needs a decision record, not a port.

The rule sits beside condition 5 of [`typing.md`](typing.md), which decides the most common shape of this subject: a handler that catches everything and leaves no trace at all. The two never report the same handler. A blind handler with no trace is that condition's finding; a blind handler that logs, uses or translates what it caught and still keeps an interrupt is condition 1's.

## What the specification says

- **`BaseException` is the root of the hierarchy and `Exception` is the root of everything that is not an exit signal**: `SystemExit`, `KeyboardInterrupt` and `GeneratorExit` derive from `BaseException` directly (Library Reference, *Built-in Exceptions*, *Exception hierarchy*). Since Python 3.8 so does `asyncio.CancelledError` (Library Reference, *asyncio — Exceptions*), and the asyncio documentation on *Task Cancellation* says a coroutine that catches it should, in almost every case, re-raise it.
- **PEP 8**, *Programming Recommendations*: derive exceptions from `Exception` rather than `BaseException`, and name specific exceptions when catching instead of a bare `except:`, which also catches `SystemExit` and `KeyboardInterrupt`. Conditions 1 and 2 follow it.
- **A bare `raise` re-raises the exception being handled, and `raise ... from` sets its cause**: Language Reference §7.8, *The raise statement*, and PEP 3134.
- **A `return`, `break` or `continue` in a `finally` clause discards the saved exception**: Language Reference §8.4.4, *finally clause*. PEP 765 makes the construct a `SyntaxWarning` from Python 3.14.

## Conditions

Each of these is decided by `hooks/check-python.py`.

1. **A handler that catches `BaseException` or a task's cancellation hands it back.** The state is a bare `except:`, an `except` naming `BaseException`, or one naming `CancelledError`, whose body neither re-raises the same object — a bare `raise`, or `raise` of the name it bound — nor ends the process with `sys.exit`, `os._exit` or `os.abort`. `BaseException` is `KeyboardInterrupt`, `SystemExit` and `GeneratorExit` as well as every error; since Python 3.8 it is also `asyncio.CancelledError`, which is how a `TaskGroup`, a `timeout()` and a shutdown stop a task. A handler that logs one of those and carries on has turned the person pressing Ctrl-C, or the supervisor stopping the worker, into a line in a log. Translating into an ordinary exception is the same defect: `raise ServiceError() from exc` makes an interrupt catchable by every `except Exception` above it. The asyncio documentation says the same about cancellation in its own words: in almost every situation it must be re-raised. A handler that catches everything on purpose — the outermost frame of a command-line entry point deciding an exit code, a logging handler that must never raise — says why in a comment on its line or the one above, which is the same escape condition 3 of `typing.md` gives an `Any`.

    Measured with the hook as it ships, on 2026-11-14. The CPython 3.14 standard library without its test suite — 721 files, 334,790 lines — has 266 handlers that catch `BaseException` and 15 that name `CancelledError`; the condition reports 75 and 8 of them. They sit almost entirely in the code whose job is to own an interrupt: `pdb`, `bdb`, `code`, `pydoc`, `idlelib`, `multiprocessing`, and asyncio's own implementation of cancellation. pip 26.2.1 with its vendored libraries — 398 files, 133,846 lines — has 7 and the condition reports 2: `base_command.py`, the entry point that turns any failure into an exit status, and `rich`'s logging handler, which by the `logging` module's own contract must not raise. Both are the case the escape exists for. This repository has one, `costs/runtime/record.py`, a recorder that must never fail the session that runs it, and its directive comment is not yet a reason.

2. **Nothing raises `Exception` or `BaseException` itself.** The state is `raise Exception(...)` or `raise BaseException`, by the bare name. The only handler that can catch it is the blind one, so every caller that wants to handle this failure has to catch every other failure with it — which is condition 5 of `typing.md` being forced on someone who did not want it. The fix is a class named for the failure, deriving from the nearest built-in that already describes it (`ValueError`, `LookupError`, `PermissionError`), or that built-in itself. Measured as above: 8 of the 3,963 raises in the standard library and 6 of the 1,090 in pip.

3. **No `return`, `break` or `continue` leaves a `finally` block.** The state is one of those statements inside a `finally`, not owned by a loop or a function nested there. Leaving a `finally` discards the exception in flight: `try: return parse() finally: return 0` returns 0 when `parse` raises, and nothing anywhere says it raised. Python 3.14 makes the construct a `SyntaxWarning` under PEP 765, which is the language deciding this condition after the fact; the hook decides it for every interpreter a project runs on. Measured as above: none in the standard library's 368 `finally` blocks, none in pip's 54. A condition that fires on nothing in two large corpora is still worth a gate when the one occurrence it catches is a failure that cannot be seen any other way.

## Where this stops

**Translating at the boundary is not decided here.** The predecessor required every top-level handler — an HTTP exception handler, a CLI entry point, a message consumer — to log the original exception and translate it into a stable error payload. That is right, and it needs to know which function is a boundary, which no parser knows. It lives in [`docs/web-services.md`](../docs/web-services.md) as the pattern a FastAPI service follows, and in PY-3 of the review skill as what a reader checks.

**A sensitive value in an exception message is not decided here.** `raise AuthError(f"bad token {token}")` puts a credential wherever the exception is logged or rendered. Which names hold a secret is a vocabulary question, and the security plugin owns it: DAT-1 in `reviewing-sensitive-data` reads exactly this state, and duplicating a heuristic for it here would give the framework two answers to one question.

**Specific exceptions deriving from a project base are not required.** The predecessor mandated a project-wide base exception. A base is useful when a caller wants to catch everything the project raises and nothing else, and needless when no caller does; whether one exists is condition 1 of `rules/yagni.md` in the fundamentals plugin, not a rule about Python. Condition 2 asks for the narrower thing that is always true: a raise a caller can name.

**Condition 1 does not follow a handler into the functions it calls.** A handler that calls `self._shutdown(exc)`, which re-raises, is reported, because the hook reads one handler's body and not the call graph. The fix is to move the `raise` into the handler, which is also where a reader looks for it, or to say why on the `except` line.

**Condition 1 does not read `KeyboardInterrupt`, `SystemExit` or `GeneratorExit` named on their own.** `except KeyboardInterrupt: return 130` is a decision about a known failure, the same line condition 5 of `typing.md` draws between a blind handler and a named one. Cancellation is the exception to that line, and the reason is asyncio's contract: a task that swallows its own cancellation breaks the code that cancelled it, whatever the handler meant.

**Condition 2 reads the bare names.** `raise builtins.Exception()` and a raise of a variable holding the class are not seen. Neither is common, and both are the same finding to a reader.

**Condition 3 does not reach a `match` arm.** A `return` inside a `case` inside a `finally` is not walked; the construct is rare enough that the cost of a second traversal was not paid for it.

**This rule declares a hook, and every condition has a script.** The statement reaches no request; the hook stands in for the rule, which is the cheapest route `ARCHITECTURE.md` describes, and the boundary material above is what a reviewer reads when a finding is disputed.
