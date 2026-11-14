# TypeScript correctness and async

Opened by step 4 of `SKILL.md` when the change touches a promise, async code, an event handler, equality, a number or a `catch`. These are the runtime defects the type system does not catch on its own.

Where `rules/promises.md` decides a condition, the entry points at it and says only what a reader adds: the finding is reported under the rule. `docs/async.md` and `docs/error-handling.md` argue the corrections.

### TS-8 A floating promise

- **Rule:** condition 1 of `rules/promises.md` (typescript-eslint's `no-floating-promises`), and its condition 2 for an async callback to `forEach`, decided by `hooks/check-promises.py`. Report under the rule.
- **Read here:** only where the project has no typed linting — a promise-returning call on its own line with no `await`, `return`, `.catch` or `void`.
- **Correct:** `await` it; or `void` it with an attached `.catch` that logs (`docs/async.md`).

### TS-9 `await` missing on a returned or guarded promise

- **Rule:** a promise in a condition is condition 1 of `rules/promises.md` (`no-misused-promises`; the compiler also reports it as TS2801). Report under the rule.
- **State, for what is left:** `return doAsync()` inside a `try` that expects to catch its rejection (the rejection escapes the try); `.map(async …)` passed where sequential awaited results were meant.
- **Detect:** read each async call in a `try` and each `.map(async …)`. typescript-eslint's `return-await`, in its strict configuration, decides the first where the project enables it.
- **Exempt:** returning a promise to a caller that will await it, outside a try that was not meant to catch it.
- **Correct:** `await` inside the try; `Promise.all` for parallel, a `for…of` loop with `await` for sequential.

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

- **Rule:** `useUnknownInCatchVariables`, which condition 2 of `rules/typing.md` keeps on, types the binding as `unknown` and makes the compiler refuse `e.message`; `catch (e: any)` reopens it and is that rule's condition 4. Report under the rule.
- **Read here:** a `.catch((e) => …)` callback, whose parameter the compiler still types as `any` unless typescript-eslint's `use-unknown-in-catch-callback-variable` is on; and an empty handler, which is condition 3 of `rules/promises.md`.
- **Correct:** `if (e instanceof Error)`; otherwise log the value as it is (`docs/error-handling.md`).
