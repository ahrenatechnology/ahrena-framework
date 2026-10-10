# TypeScript correctness and async

Opened by step 2 of `SKILL.md` when the change touches a promise, async code, an event handler, equality or a number. These are the runtime defects the type system does not catch on its own.

### TS-8 A floating promise

- **State:** a call that returns a promise whose result and rejection are neither awaited nor `.then`/`.catch`ed nor assigned — a bare `doAsync()` on its own line, an async function called in a `forEach`, an async handler whose rejection no one catches.
- **Detect:** find promise-returning calls with no `await`, no `return`, no `.catch`, no `void` marker. The work runs unordered and a rejection becomes an unhandled rejection that can crash Node.
- **Exempt:** a deliberate fire-and-forget marked `void promise` with a `.catch`, or handed to a tracker.
- **Correct:** `await` it; or `void` it with an attached `.catch` that logs.

### TS-9 `await` missing on a returned or guarded promise

- **State:** `if (isReady())` where `isReady` is async (a promise is always truthy); `return doAsync()` inside a `try` that expects to catch its rejection (the rejection escapes the try); `.map(async ...)` passed where sequential awaited results were meant.
- **Detect:** read each async call in a condition, a `try`, or a place a value is used. A promise in a boolean test is always true.
- **Exempt:** returning a promise to a caller that will await it, outside a try that was not meant to catch it.
- **Correct:** `await` before the test or inside the try; `Promise.all` for parallel, a `for await` loop for sequential.

### TS-10 `Promise.all` where one rejection should not abort the rest, or vice versa

- **State:** `Promise.all` over independent best-effort tasks, so one failure rejects all and loses the successes; or sequential `await` in a loop over independent tasks, serialising what could run in parallel.
- **Detect:** read what the tasks are. All-or-nothing versus best-effort is the question.
- **Exempt:** tasks that genuinely must all succeed, or must run in order.
- **Correct:** `Promise.allSettled` for best-effort; `Promise.all` of a mapped array for independent parallel work.

### TS-11 `==` / `!=` instead of `===` / `!==`

- **State:** loose equality that triggers coercion — `== null` aside, comparisons like `x == 0`, `x == ""`, `x == false` that treat `0`, `""`, `false`, `null` and `undefined` as interchangeable.
- **Detect:** each `==`/`!=` the change adds.
- **Exempt:** `== null` used on purpose to catch both `null` and `undefined`, a known idiom.
- **Correct:** `===`/`!==`; test the condition explicitly.

### TS-12 A number trap

- **State:** money or exact quantities in `number` (IEEE-754 float, so `0.1 + 0.2 !== 0.3`); an id from an API that exceeds `Number.MAX_SAFE_INTEGER` parsed as a number; `parseInt` with no radix; `NaN` compared with `===`.
- **Detect:** follow the value. A 64-bit integer id loses precision silently above 2^53.
- **Exempt:** an integer known to stay in safe range, a ratio that is inherently approximate.
- **Correct:** integer minor units or a decimal library for money; `string` or `bigint` for large ids; `Number.isNaN`; a radix on `parseInt`.

### TS-13 A mutation of shared or frozen-by-intent data

- **State:** a function that mutates an argument the caller still owns (an options object, an array passed in), or reassigns a React prop/state object in place; `const` taken to mean deeply immutable.
- **Detect:** read what the function writes to. `const` freezes the binding, not the object.
- **Exempt:** a documented in-place transform the caller expects, or a local copy.
- **Correct:** copy before mutating (`{...x}`, `[...a]`, `structuredClone`); return a new value; type inputs `readonly`.

### TS-14 An error of type `unknown` or `any` used without narrowing

- **State:** `catch (e)` where `e` (typed `unknown` under `useUnknownInCatchVariables`, else `any`) is read as `e.message` or re-thrown as a typed error with no check.
- **Detect:** each `catch` the change adds. The thrown value can be anything, not only an `Error`.
- **Exempt:** a narrow after an `instanceof Error` check.
- **Correct:** `if (e instanceof Error)`; otherwise coerce to a message safely.
