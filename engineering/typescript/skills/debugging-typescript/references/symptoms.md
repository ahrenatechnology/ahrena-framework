# Symptoms, causes and the first check

Opened by step 2 of `SKILL.md`. Every compiler code and runtime message below was reproduced on TypeScript 6.0.3 and 7.0.2 and on Node 26 while this table was written; the wording a reader sees may differ by version, the code does not.

## Compile errors

| Symptom | Likely cause | First check |
|---|---|---|
| `TS2307: Cannot find module './x.js' or its corresponding type declarations` | the specifier does not match a file under the project's `moduleResolution`, or a package ships no types | `tsc --noEmit --traceResolution` for that specifier; under `nodenext` a relative import carries the emitted extension |
| `TS2322: Type 'string \| undefined' is not assignable to type 'string'` on an index read | `noUncheckedIndexedAccess` doing its job | handle the missing element; do not add `!` |
| `TS18048: 'x' is possibly 'undefined'` | an optional value used before it is checked | narrow it, or make it required if it never is optional |
| `TS2352: Conversion of type … may be a mistake` | a single `as` between types that do not overlap | the types disagree; parse or narrow instead of adding `as unknown as` |
| `TS2366: Function lacks ending return statement` | a `switch` over a union that misses a member | add the case, and a `default` that assigns the value to `never` (TS-6 of `reviewing-typescript`), so the next member added fails the build too |
| `TS2801: This condition will always return true since this 'Promise<…>' is always defined` | a promise tested as a boolean | `await` it |
| `TS7006: Parameter 'x' implicitly has an 'any' type` | an unannotated parameter under `noImplicitAny` | annotate it; `unknown` if its shape is not known yet |
| `TS5107` or `TS5108` on an option | an option deprecated in 6.0 or removed in 7.0 | `tsc --showConfig`, then the 6.0 release notes' list ([`docs/toolchain.md`](../../../docs/toolchain.md)) |
| an error only under 7, or only under 6 | a deprecation that became an error, or a tool still on the 6 API | compare `tsc --showConfig` under both |

## Runtime errors

| Symptom | Likely cause | First check |
|---|---|---|
| `TypeError: Cannot read properties of undefined` on a value typed as defined | a hole on the value's path: an assertion on untyped input, an `any`, a `!` | step 4 of `SKILL.md`: the hooks over the files on the path |
| `TypeError: x is not iterable`, `x.map is not a function` on parsed data | the data's shape changed and an assertion hid it: an envelope, a renamed field, a single value where a list was | `hooks/check-untyped-input.py` on the parse; replace the assertion with a schema |
| `ReferenceError: Cannot access 'x' before initialization` at startup | an import cycle evaluated mid-way | `hooks/check-boundaries.py`; delete one of the reported edges |
| `ERR_PACKAGE_PATH_NOT_EXPORTED` | a deep import past a package's `exports` | import an exported entry, or export the subpath on purpose |
| `SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]` under `node file.ts` | an `enum`, a namespace or a parameter property, which type stripping cannot erase | rewrite it as erasable syntax and turn `erasableSyntaxOnly` on |
| the process exits on an `Error` nobody threw at that line | an unhandled rejection, which Node raises as an uncaught exception by default | the type-aware `no-floating-promises`; `hooks/check-promises.py` |

## Behaviours

| Symptom | Likely cause | First check |
|---|---|---|
| a loop finishes before its work does | an async callback passed to `forEach` | `hooks/check-promises.py`; `for…of` with `await` |
| a `catch` around a `return` never sees the rejection | `return promise` inside `try` without `await` | typescript-eslint's `return-await` |
| a request hangs during an incident | an outside call with no deadline | look for `fetch` without `signal: AbortSignal.timeout(…)` |
| a 404 or 500 treated as success | `fetch` does not reject on an HTTP error status | check `response.ok` before reading the body |
| a stack trace points into compiled JavaScript | source maps not applied | run Node with `--enable-source-maps` |
| a test passes with a type error in it | the runner strips types and does not check them | run `tsc --noEmit` over the tests too |
