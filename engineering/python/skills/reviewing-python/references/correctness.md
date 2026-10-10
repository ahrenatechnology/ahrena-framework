# Python correctness

Opened by step 2 of `SKILL.md` on every Python change. Each condition gives the state, how it is detected, what exempts it, and the correction. `hooks/check-typing.py` already decides the mutable-default and swallowed-exception conditions on the changed lines; what is here is the reading those leave, and the conditions no parser decides.

### PY-1 A mutable default argument

- **State:** a parameter defaults to a `list`, `dict`, `set` or other mutable literal, or to a call that returns a fresh mutable (`[]`, `{}`, `list()`, `dict()`).
- **Detect:** read the `def`. The default is evaluated once, at definition, and shared across every call that does not pass the argument, so one call's mutation is seen by the next.
- **Exempt:** a default used only as a read-only sentinel and never mutated — but `None` plus a body assignment is the idiom, and the reviewer should ask why the mutable was chosen.
- **Correct:** default to `None` and build the mutable inside the body: `x = x if x is not None else []`.

### PY-2 A closure that binds the loop variable late

- **State:** a lambda or inner function created in a loop that refers to the loop variable, kept in a list or registered as a callback.
- **Detect:** find functions defined in a `for`/comprehension that close over the iteration name. They all capture the variable, not its value, so every one sees the last iteration's value.
- **Exempt:** the closure is called inside the same iteration and not kept.
- **Correct:** bind the value as a default argument (`lambda x=item:`) or pass it to a factory.

### PY-3 An exception caught and dropped

- **State:** an `except` whose body swallows the error — `pass`, a bare `return`/`continue`, or a log with no re-raise — where the caller then proceeds as if the operation succeeded.
- **Detect:** read each `except` the change adds or widens. A bare `except:` or `except Exception:` around more than the one line that can raise is the common shape.
- **Exempt:** a genuine best-effort step whose failure is meant to be ignored, with a comment saying so, logging the exception.
- **Correct:** catch the narrowest exception, around the smallest block; re-raise, translate to a domain error, or handle it — do not continue blind. Never catch `BaseException` (it takes `KeyboardInterrupt` and `SystemExit`).

### PY-4 Identity where equality was meant

- **State:** `is` / `is not` comparing against a string, an int, a tuple or any value that is not a singleton.
- **Detect:** read each `is` comparison. `is` is reserved for `None`, `True`, `False` and sentinels; against other values it compares object identity, which CPython makes true for small ints and interned strings and false otherwise, so it passes in tests and fails in production.
- **Exempt:** comparison with `None`, a boolean, or a module-level sentinel object.
- **Correct:** use `==`.

### PY-5 Float arithmetic on money or exact quantities

- **State:** a price, a currency amount or a count that must be exact, held or computed as `float`.
- **Detect:** follow the value. `0.1 + 0.2 != 0.3` in binary float, and the error accumulates and is stored.
- **Exempt:** a measurement that is inherently approximate (a ratio, a physical quantity) and never summed for money.
- **Correct:** `decimal.Decimal` from a string, or integer minor units.

### PY-6 A boundary iterator or generator consumed twice

- **State:** a generator, `map`, `filter`, `zip` or a file object iterated once and then read again, or passed to two consumers, as if it were a list.
- **Detect:** find the second consumer. The first exhausts it; the second sees nothing and reports an empty result with no error.
- **Exempt:** a value that is materialised (`list(...)`) before the first use.
- **Correct:** materialise once into a list or tuple when it must be read more than once.

### PY-7 A time, a path or an environment read with no zone or no default

- **State:** `datetime.now()` / `utcnow()` with no timezone used for a stored or compared timestamp; `os.environ["X"]` that raises where a default was meant; a path built with string concatenation.
- **Detect:** read the call. A naive datetime compared with an aware one raises; `utcnow()` returns naive and is deprecated.
- **Exempt:** a naive datetime that never leaves a context that is documented as local.
- **Correct:** `datetime.now(timezone.utc)`; `os.environ.get("X")` with an explicit default or an explicit raise; `pathlib.Path` with `/`.

### PY-8 `async` that blocks or is never awaited

- **State:** a blocking call (`requests`, `time.sleep`, a sync file read, a CPU loop) inside an `async def`; or a coroutine called without `await` and its result discarded.
- **Detect:** read each `async def` for a call that is not awaited and does not yield. A coroutine not awaited runs nothing and warns at garbage-collection, not at the call.
- **Exempt:** a blocking call wrapped in `run_in_executor` or `asyncio.to_thread`.
- **Correct:** await the async equivalent; wrap unavoidable blocking work in a thread; await every coroutine or pass it to a task group.
