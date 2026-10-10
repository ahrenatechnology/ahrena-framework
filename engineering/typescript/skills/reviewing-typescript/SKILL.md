---
name: reviewing-typescript
description: Use when a change under review edits TypeScript or JavaScript (.ts, .tsx, .js, .jsx and their module variants) and the question is what a TypeScript reader would catch - an any or a cast that reopens a hole the compiler would have closed, a floating or unhandled promise, == where === was meant, a widened public type. Reads the routed files against the conditions below; every finding names the condition.
type: skill
clade: engineering
subclade: quality
references:
  - ahrena-engineering-fundamentals:docs/review-findings.md
  - ahrena-engineering-fundamentals:docs/review-routes.md
---

# Reviewing TypeScript

The language-agnostic pass in `ahrena-engineering-fundamentals:skills/reviewing-diffs/SKILL.md` has read the change against the rules that hold in any language. This skill reads what needs a TypeScript reader: the places the type system was told to stop checking, the async mistakes, and the surface others compile against.

The conditions are checklists in `references/`, identified by a prefix and a number. A finding cites the identifier. Severity and route follow `ahrena-engineering-fundamentals:docs/review-findings.md`.

## 1. Take the route, and read the repository first

The router fired the `typescript` route on the changed `.ts`, `.tsx`, `.js` and `.jsx` files (and the `.mts`/`.cts`/`.mjs`/`.cjs` variants). Those are the files this skill reads.

Read the project's `tsconfig.json` first: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitAny` decide which of these conditions the compiler already catches. In a strict project, a hole only exists where the code reopens it (`any`, `as`, `!`, `@ts-ignore`); in a loose one, the reader carries more. Read the ESLint config too — a rule it enforces (`no-floating-promises`, `eqeqeq`) is settled, and not reported again. A green `tsc` and a green lint decide what they cover.

## 2. Open the checklists the change calls for

| What the change touches | Reference |
|---|---|
| a type, an interface, a cast, a generic, a signature | `references/types.md` |
| a promise, `async`/`await`, an event handler, equality, a number | `references/correctness-and-async.md` |
| an export, a barrel, a public declaration, a `.d.ts` | `references/modules-and-surface.md` |

A change to a component's internals that adds no type and no async opens `correctness-and-async.md` alone.

## 3. Read beyond the hunk

Follow each changed symbol to its callers and to the types it flows into. A cast is judged by what the value actually is at runtime, which the surrounding code shows, not by the hunk. An exported type is judged by who imports it.

Read what the change replaced, from the base revision, before calling a changed line wrong.

## 4. Apply the routed conditions

Work condition by condition. Give the scenario in TypeScript terms: the value at runtime, the type the compiler believed, and where they part. A condition whose answer is a project convention the repository does not state is a `question`.

Read each condition's `Exempt` line. A cast at a true boundary and an `any` on genuinely dynamic data are correct, and reporting them teaches the author to skim.

## 5. Write the findings

Each finding carries the four fields in `ahrena-engineering-fundamentals:docs/review-findings.md`, with the condition identifier and a correction that is an instruction.

Hand the set back to step 7 of `ahrena-engineering-fundamentals:skills/reviewing-diffs/SKILL.md`. Do not publish from here, and do not edit the change.

## When this skill does not apply

**A language-agnostic defect.** Length, nesting, duplication, a premature abstraction: those are `reviewing-diffs` and the fundamentals rules.

**The experience of a React or browser UI.** Accessibility, component and state architecture, rendering performance and design-system use are a front-end discipline, not this skill, which reads the language. When the framework ships that discipline it owns them; until then this skill stays inside the type system, async and the module surface.

**Security of the change.** XSS through `dangerouslySetInnerHTML`, a URL built from input, a secret in a bundle: that is `ahrena-engineering-fundamentals:skills/reviewing-security/SKILL.md`, whose checklists carry the TypeScript sinks.

**Another language.** A `.py`, `.go` or `.rs` file in the same change is read by that language's skill.
