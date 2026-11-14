---
id: promises
type: rule
clade: engineering
subclade: typescript
title: No promise floats, and no rejection is discarded
statement: Every promise is awaited, returned or handled; no async callback goes to forEach; no catch is empty without a reason; nothing quiets an unhandled rejection.
enforcement: judgment
references:
  - docs/async.md
  - docs/error-handling.md
---

# No promise floats, and no rejection is discarded

Five conditions. Condition 1 needs the type of every expression and is decided by typescript-eslint's type-aware rules, run by the consuming project. Conditions 2 to 5 are decided by `hooks/check-promises.py`, which reads the source and the files that launch Node with the standard library alone. [`docs/async.md`](../docs/async.md) argues how async code is written so that these hold without effort, and [`docs/error-handling.md`](../docs/error-handling.md) what a handler does with what it caught.

The subject is a failure that nobody is told about. A promise that nothing awaits runs on unordered, and its rejection reaches no `catch`: in Node, since v15, an unhandled rejection is raised as an uncaught exception and ends the process, and in a browser it is a console line nobody reads. Either way the code that started the work has already returned success. Each condition below is one of the ways a rejection gets lost between the line that caused it and the code that should have known.

## Conditions

1. **typescript-eslint's `no-floating-promises`, `no-misused-promises` and `await-thenable` report nothing.** Decided by typescript-eslint with typed linting on, run by the consuming project's pipeline. All three are in its `recommendedTypeChecked` configuration. `no-floating-promises` reports a promise-valued statement that is neither awaited, returned, `.catch`ed nor marked with `void`; `no-misused-promises` reports a promise where a boolean or a `void` callback is expected — `if (isReady())` on an async `isReady`, an async handler given to an API that ignores its result; `await-thenable` reports an `await` on something that is not a promise, which is usually a missing call. Whether an expression is a promise is a fact about its type, and no scan of the source can know it. Under TypeScript 7, typescript-eslint runs against the 6 API installed beside it, as [`docs/toolchain.md`](../docs/toolchain.md) arranges.

2. **No async function is passed to `forEach`.** Decided by `hooks/check-promises.py`. `forEach` discards what its callback returns, so each call's promise floats, the loop finishes before any of the work does, and every rejection is unhandled. This is the one shape of condition 1 that the source spells without a type, and the hook holds it on a project that has not set up typed linting. The fix is `for…of` with `await` when the order matters, and `await Promise.all(rows.map(async …))` when it does not.

3. **No `.catch` handler and no `catch` block is empty, unless a comment inside it says why.** Decided by `hooks/check-promises.py`, on `.catch(() => {})`, `.catch(function () {})`, `catch {}` and `catch (error) {}`. An empty handler is the rejection handled in the one way that tells nobody: the work failed, the caller continues, and nothing anywhere records it. A comment inside is accepted because ESLint's `no-empty` accepts it, for the same reason: the author has decided, and said so. A sync `try` is held like an async one, because `await` turns a rejection into a throw and the same `catch` handles both.

4. **A process-level `unhandledRejection` or `uncaughtException` listener ends the process: it throws, or calls `process.exit`, `process.abort` or `process.kill`.** Decided by `hooks/check-promises.py`, for a listener written inline. Node's default for an unhandled rejection is to raise it as an uncaught exception and stop; a listener that only logs turns that default off for the whole process, and every later rejection becomes a log line in a process whose state nobody knows. Node's own documentation says of `uncaughtException` that it is not safe to resume normal operation after it. A listener exists to record the failure before the process ends, not instead of ending it.

5. **Nothing runs Node with `--unhandled-rejections` set to `warn`, `warn-with-error-code` or `none`.** Decided by `hooks/check-promises.py`, in `package.json`, `.npmrc`, a Dockerfile, a compose file, a `Procfile`, an `.env` file or a shell script. Node documents five modes; `throw` is the default and `strict` raises even when a listener exists, and both are allowed. The other three let the process run past a rejection nobody handled, which is condition 4's defect configured instead of written.

## Where this stops

**Condition 1 is not decided by anything in this plugin.** A project without typed linting gets conditions 2 to 5 and nothing else, and the floating promise in `save(row);` on its own line goes unreported. That is the reason the rule is `judgment`: the hook alone would teach that a project without the linter is covered.

**Conditions 2 to 5 read shapes, not types.** `items.forEach(handle)` where `handle` is an async function declared elsewhere is condition 1's; so is a `.then(ok, () => {})` whose second argument is empty. A `.catch(noop)` that names a function is not read, and is a finding at review.

**Condition 4 reads only an inline listener.** `process.on("unhandledRejection", onRejection)` has no body here to read, and is left to review; a listener that calls the project's own shutdown routine, which exits after closing the server, is a finding until the exit is visible in the listener. Writing `process.exit` after the shutdown call is the fix the condition asks for, and it is the one a reader needs anyway.

**Condition 5 reads the files where a flag is set in practice.** `NODE_OPTIONS` exported in a CI variable, a Kubernetes manifest, or a process manager's own configuration is outside its walk. A browser has no such flag, and conditions 4 and 5 do not apply there; the browser's equivalent, an `unhandledrejection` event listener that calls `preventDefault()`, is a finding at review.

**Nothing here says how a failure is handled once it is caught.** Whether to retry, to return a result type, to log at which level, or to rethrow with context is [`docs/error-handling.md`](../docs/error-handling.md)'s subject. This rule only refuses the handler that does none of them.

**Measured on four public codebases** — zod, hono, typescript-eslint and vscode-extension-samples, about 580,000 lines of TypeScript at the commits [`docs/toolchain.md`](../docs/toolchain.md) records — the hook reported 61 findings: 59 under condition 3, two under condition 2, none under 4 and 5 after the listener-by-reference case was taken out. Of twenty condition 3 findings read one by one, eleven were benchmarks and tests that call something expected to throw, four were capability probes — `performance.now()`, `AsyncLocalStorage`, a `stat` on a path that may not exist — and two were parser fixtures that are empty on purpose. Each is a decision the author made, and none says so: that is the case the comment exception is for, and a one-line comment is the whole cost of passing. Two more were a `catch` around a conversion that does not throw — `Number(value)` and `new Date(value)` — and the last a fuzzing script discarding a compiler failure on purpose.
