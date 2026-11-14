# TypeScript types

Opened by step 4 of `SKILL.md` when the change touches a type, a cast, a generic or a signature. Each condition gives the state, how it is detected, what exempts it, and the correction. Every one is about a place the compiler was told to stop checking, or a type that promises more than the value delivers.

Where `rules/typing.md` or `rules/runtime-validation.md` decides a condition, the entry points at it and says only what a reader adds: the finding is reported under the rule.

### TS-1 `any`, explicit or implicit

- **Rule:** an explicit `any` is condition 4 of `rules/typing.md`, decided by `hooks/check-typing.py`; an `any` that arrives by inference is its condition 3, decided by typescript-eslint's `no-unsafe-*` rules. Report under the rule.
- **Read here:** whether the reason written beside an explicit `any` is a reason. "Library has no types" is one when it names the library; "any" or "TODO type this" is not, and is a finding under condition 4.
- **Correct:** the concrete type, a generic, `unknown` with narrowing, or a schema parse at the boundary.

### TS-2 `as` that asserts what the value is not

- **Rule:** a double assertion (`as unknown as T`) is condition 6 of `rules/typing.md`, and an assertion on `JSON.parse`, a `.json()` body or `process.env` is condition 2 of `rules/runtime-validation.md`; both are decided by a hook. Report under the rule.
- **State, for what is left:** a single `as` that narrows to a shape the value may not have — on an event target, on the result of `.find()`, on a value from a generic helper that types its result by a type argument (`ky`'s `.json<T>()`).
- **Detect:** every `as` is the author overriding the checker. Ask what the value is at runtime on the path that reaches it.
- **Exempt:** a narrowing the compiler cannot express but the code guarantees, with a comment; `as const` on a literal.
- **Correct:** a type guard (`in`, `typeof`, `instanceof`, a predicate), a discriminated union, or a schema parse that returns the type.

### TS-3 The non-null assertion `!`

- **State:** `x!` or `x!.y` asserting a value is not null/undefined where the code does not guarantee it — after a `.find()`, a map lookup, an optional prop, a DOM query.
- **Detect:** each `!` the change adds. It silences the one check that would have caught a missing value, and the crash moves to runtime.
- **Exempt:** a value a prior line provably sets, or a test fixture.
- **Correct:** guard and handle the absence, `?.` with a fallback, or restructure so the type is non-null.

### TS-4 A suppression comment

- **Rule:** `@ts-ignore`, `@ts-nocheck`, and a `@ts-expect-error` with no description are condition 5 of `rules/typing.md`, decided by `hooks/check-typing.py`. Report under the rule.
- **Read here:** an `eslint-disable` on a changed line, which no rule of this plugin decides: it is a finding unless its ` -- ` description names why, and a disable of a rule a condition of this plugin cites (`no-floating-promises`, `no-unsafe-assignment`) is reported under that condition.
- **Correct:** fix the type; if a dependency's types are wrong, narrow at that one call and say why.

### TS-5 An optional and a `| undefined` confused, or an index assumed present

- **Rule:** in a project that sets `noUncheckedIndexedAccess`, as condition 2 of `rules/typing.md` requires, the compiler types an index read as possibly `undefined` and this condition is decided. Read it by hand only where the project does not set it, and report the missing flag under the rule.
- **State:** `foo?: T` treated as always present; an array or record index (`arr[i]`, `map[key]`) used as `T` without a guard.
- **Exempt:** an index guarded by a bound check on the same path.
- **Correct:** guard the access; prefer `.at()` or `Map.get`, whose types admit the miss.

### TS-6 An enum, a union or a switch that is not exhaustive

- **State:** a `switch` or an `if`/`else` chain over a union or enum with no default that asserts never, so a new variant compiles and falls through silently.
- **Detect:** read the switch against the union. Adding a member later is the moment this bites, and nothing flags it.
- **Exempt:** a switch with a `default` that handles the rest deliberately.
- **Correct:** an exhaustiveness guard — `default: const _: never = x`.

### TS-7 A widened or structurally loose type on a surface

- **State:** a public type widened past what callers need — `string` where a union of literals was meant, `object` or `{}` or `Function` as a type, an interface with an index signature that swallows typos.
- **Detect:** read the exported type the change adds or edits. `{}` means "any non-nullish value", not "empty object"; `Function` accepts any callable unchecked.
- **Exempt:** a type that is genuinely open at that boundary.
- **Correct:** a literal union, `Record<K, V>`, a precise interface, a specific function signature.
