# TypeScript types

Opened by step 2 of `SKILL.md` when the change touches a type, a cast, a generic or a signature. Each condition gives the state, how it is detected, what exempts it, and the correction. Every one is about a place the compiler was told to stop checking, or a type that promises more than the value delivers.

### TS-1 `any`, explicit or implicit

- **State:** an explicit `: any`, a function parameter or return with no type in a project without `noImplicitAny`, or a value typed `any` because it came from an untyped import or a JSON parse.
- **Detect:** `any` turns off checking for every operation on the value and everything it flows into. Follow it downstream — the damage is not at the annotation.
- **Exempt:** a true dynamic boundary with a comment, soon narrowed by a type guard or a schema parse.
- **Correct:** the concrete type, a generic, `unknown` with narrowing, or a validated schema at the boundary.

### TS-2 `as` that asserts what the value is not

- **State:** a type assertion (`x as Foo`, `as unknown as Foo`, `as const` misused) that tells the compiler a shape it cannot verify, where the value may not have it — a cast on a `fetch` result, on `JSON.parse`, on an event target, on a double-cast through `unknown`.
- **Detect:** every `as` is the author overriding the checker. Ask what the value is at runtime on the path that reaches it.
- **Exempt:** a narrowing the compiler cannot express but the code guarantees, with a comment; `as const` used correctly for a literal.
- **Correct:** a type guard (`in`, `typeof`, `instanceof`, a predicate), a discriminated union, or a schema parse that returns the type.

### TS-3 The non-null assertion `!`

- **State:** `x!` or `x!.y` asserting a value is not null/undefined where the code does not guarantee it — after a `.find()`, a map lookup, an optional prop, a DOM query.
- **Detect:** each `!` the change adds. It silences the one check that would have caught a missing value, and the crash moves to runtime.
- **Exempt:** a value a prior line provably sets, or a test fixture.
- **Correct:** guard and handle the absence, `?.` with a fallback, or restructure so the type is non-null.

### TS-4 A suppression comment

- **State:** `@ts-ignore`, `@ts-expect-error` with no description, or `eslint-disable` left on a changed line.
- **Detect:** read the error it hides. `@ts-ignore` hides the next line's error and every future one that appears there.
- **Exempt:** `@ts-expect-error` with a comment naming the upstream bug it works around, ideally with a link.
- **Correct:** fix the type; if a dependency's types are wrong, narrow at that one call and comment why.

### TS-5 An optional and a `| undefined` confused, or an index assumed present

- **State:** `foo?: T` treated as always present; an array or record index (`arr[i]`, `map[key]`) used as `T` where `noUncheckedIndexedAccess` would type it `T | undefined`.
- **Detect:** follow an optional field or an index access to its use with no guard. In a project without `noUncheckedIndexedAccess`, the compiler types every index as present and the reader must not.
- **Exempt:** an index guarded by a bound check on the same path.
- **Correct:** guard the access; enable the flag at the project level; prefer `.at()` or `Map.get` whose types admit the miss.

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
