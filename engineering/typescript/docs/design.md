---
id: design
type: doc
clade: engineering
subclade: typescript
title: Designing TypeScript - premises, SOLID in the language's own form, and extension by package
summary: The three premises every choice of implementation path in this plugin is argued from, how SOLID and inversion of control are expressed in TypeScript, how a package is extended without being modified, what a unit is and which tool reports one that has outgrown the fundamentals' limits, and the TypeScript handbook guidance this plugin follows and where it departs.
references:
  - rules/module-boundaries.md
  - rules/colocated-tests.md
  - ahrena-engineering-fundamentals:docs/clean-code.md
---

# Designing TypeScript

This page holds the design choices the other artifacts of the plugin lean on. It restates no condition of the language-agnostic engineering plugin; it says how TypeScript meets them, and where the language's own limits stop it.

## The premises a choice is argued from

When two paths both work, this plugin chooses by three premises, in this order, and names the one that decides:

1. **No circular reference.** A path that introduces a cycle between modules or packages is refused outright, because nothing in the language refuses it ([`rules/module-boundaries.md`](../rules/module-boundaries.md)) and a cycle makes evaluation order — and with it correctness — depend on which module is imported first (ECMA-262 §16.2.1.6).
2. **Lower cyclomatic complexity.** Between two paths, the one with fewer branches in any one function wins: a discriminated union and an exhaustive `switch` over a chain of `typeof` tests, a lookup table over a ladder of `if`, an early return over a nested `else`.
3. **Maintainability.** Between two paths equal on the first two, the one a reader changes with less to hold in mind: the explicit dependency over the ambient one, the narrow type over the wide one, the standard construct over the clever one.

The language-agnostic thresholds stay in `ahrena-engineering-fundamentals`; these premises decide between paths that are both inside them.

## SOLID and inversion of control in TypeScript

The conditions are the fundamentals' [`solid.md`](../../fundamentals/rules/solid.md), arbitrated by [`yagni.md`](../../fundamentals/rules/yagni.md) exactly as that rule states: the conditions that remove structure always apply, and the ones that add an abstraction apply only when the abstraction trigger is met. This page does not restate them. It says how TypeScript expresses them.

**An abstraction is a structural interface, declared by its consumer.** TypeScript's "type compatibility … is based on structural subtyping" (Handbook, *Type Compatibility*): a value satisfies an interface by having its shape, with no `implements` clause and no import of the interface. So the port a use case needs is declared beside the use case, in the application layer, and the adapter in the infrastructure layer satisfies it without the application importing anything from infrastructure. That is dependency inversion with no framework and no runtime cost, and it is what keeps condition 6 of `solid.md` and the one-way graph of `module-boundaries.md` true at once.

**A dependency arrives as a parameter.** A function takes its collaborators as parameters; a class takes them in its constructor, as `private readonly` fields. The composition root — `main.ts`, [`project-layout.md`](project-layout.md) — is the one place that constructs adapters and passes them in. A module that imports a concrete collaborator and calls it directly has hidden a dependency that a test then has to patch the module system to replace, which [`testing.md`](testing.md) refuses.

**No dependency-injection container by default.** Containers that resolve constructor parameters by reflection (InversifyJS, tsyringe) depend on `experimentalDecorators` and `emitDecoratorMetadata`. The standard decorators TypeScript 5.0 implements are "not compatible with `--emitDecoratorMetadata`" (TypeScript 5.0 release notes), and the proposal itself is at Stage 2.7 in TC39, not in the language yet. A composition root of plain constructor calls is shorter, typed end to end, and needs neither. A framework that is built on a container — NestJS, Angular — brings its own, and inside it the framework's way wins.

**Interface segregation is a small interface per consumer.** Because the consumer declares the port, it declares only the members it calls; `Pick<Repository, "save">` or a two-method interface beside the use case, not the repository's whole surface. Liskov substitution is checked by the compiler for signatures and by the adapter's own test for behaviour.

**What the language does not give.** TypeScript erases its types: an interface cannot be asked for at runtime, so a plugin registry or a factory that chooses an implementation by type needs a value — a string key, a class, a symbol — that the code passes explicitly. And a structural type accepts any value of the right shape, so two ports with the same shape are interchangeable; a branded type (`string & { readonly brand: "OrderId" }`) is how two such values are kept apart where it matters.

**A pattern imported against the grain is a finding.** A class of only static methods where a module of functions was meant; an `I`-prefixed interface for every class; a getter and setter pair around a public field; an abstract base class used only to share code where a function would; a service locator. Each is a habit from another language that TypeScript expresses more simply, and review reports it under TS-21 of `reviewing-typescript`.

## A package is open to extension and closed to modification

Extending a behaviour, a module or a frontend component is done by a **new workspace package** that depends on the base package and extends it through the base's public extension points, not by editing the base. The base package declares those extension points in its `exports` ([`project-layout.md`](project-layout.md)):

- **an interface the base accepts** — the extension implements it, and the composition root hands the implementation to the base;
- **a registration function** — `registerPaymentMethod(method)`, where the base keeps the registry and the extension calls it;
- **a component that takes its parts as props**, for a frontend component — the extension passes its own; the frontend clade's artifacts own how the component is designed.

The extension package declares the base in its `dependencies` with the workspace protocol, which condition 6 of `module-boundaries.md` requires, and the base never imports the extension, which condition 5 holds. A base that has to be edited to accept an extension is missing an extension point; adding the point is the base's own change, reviewed as such, and the extension follows it.

The workspace tool that composes the packages is pnpm, argued in [`libraries.md`](libraries.md) with the case where a sturdier tool is the better choice.

## Single responsibility, down to the function and the file

The measured limits are the fundamentals': a function body of at most 30 statements ([`clean-code.md`](../../fundamentals/rules/clean-code.md), condition 1), control flow nested at most 3 deep ([`kiss.md`](../../fundamentals/rules/kiss.md), condition 1), at most 4 parameters ([`value-semantics.md`](../../fundamentals/rules/value-semantics.md), condition 1), and a class whose methods share state ([`solid.md`](../../fundamentals/rules/solid.md), condition 1). This plugin adds no number.

**The units in TypeScript** are the function (declaration, expression or arrow), the method, the module — one file — and the package. A file solves one problem: it exports one function or one class and what that function or class needs callers to see, and its test sits beside it ([`rules/colocated-tests.md`](../rules/colocated-tests.md)). A unit is tested in isolation by calling it with fakes for the ports it receives, which the parameter and constructor injection above make possible without patching anything.

**The tool that reports a breach.** The fundamentals' `check-structure.py` parses Python only, and says so. In TypeScript the same limits are ESLint's core rules, configured to the fundamentals' numbers: `max-statements` at 30, `max-depth` at 3, and typescript-eslint's `max-params` at 4 (which, unlike the core rule, does not count a `this: void` declaration unless `countVoidThis` is set). `max-statements` counts as condition 1 of `clean-code.md` does — the statements of the body and of the blocks it contains, with a nested function counted once and measured on its own — which this plugin checked on ESLint 10.15. Unreachable code is core ESLint's `no-unreachable`, in its recommended set. The two conditions without an ESLint counterpart, branching on a boolean parameter and a class's cohesion, are read at review.

## The TypeScript handbook's guidance

This plugin follows the handbook's *Do's and Don'ts*, and cites them where they apply:

- Don't use the boxed types `Number`, `String`, `Boolean`, `Symbol` or `Object`; use `number`, `string`, `boolean`, `symbol`, and `object` or `unknown`.
- Don't have a generic type that doesn't use its type parameter.
- Use `void` as the return type of a callback whose value is ignored, not `any`.
- Don't make callback parameters optional unless the caller really may omit them.
- Prefer optional parameters and union types to overloads that differ only in trailing parameters or in one argument's type, and order overloads specific to general.

**Where this plugin departs.** The handbook says "Don't use `any` as a type unless you are in the process of migrating a JavaScript project to TypeScript". [`rules/typing.md`](../rules/typing.md) allows an explicit `any` with a written reason, because the measured codebases show type-level library code where `any` is the only constraint the compiler accepts. The departure is narrow: the reason is required, and `unknown` is the default.

## Where this stops

**Design of user-facing features** — components, state, wireframes — is the frontend clade's. The extension-by-package rule applies to a frontend component as to any module; how the component's extension points are designed is theirs.

**When a premise is wrong.** Lower cyclomatic complexity loses to a clearer algorithm that needs one more branch, and a lookup table loses when its entries need different code; the premise decides between two paths, it does not forbid the third.

**Extension by package is wrong for a one-line change to the base's own behaviour.** A bug fix or a change the base's owners want is a change to the base. The rule is for adding behaviour the base does not own.

## Sources

- ECMA-262, 17th edition (ES2026), §16.2.1.6 Cyclic Module Records: <https://262.ecma-international.org/17.0/>.
- TypeScript Handbook, *Type Compatibility*: <https://www.typescriptlang.org/docs/handbook/type-compatibility.html>.
- TypeScript Handbook, *Do's and Don'ts*: <https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html>.
- TypeScript 5.0 release notes, decorators and `emitDecoratorMetadata`: <https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html>.
- TC39 decorators proposal, Stage 2.7: <https://github.com/tc39/proposal-decorators>; stages listed in <https://github.com/tc39/proposals>.
- ESLint `max-statements`, `max-depth`, `no-unreachable`: <https://eslint.org/docs/latest/rules/max-statements>, <https://eslint.org/docs/latest/rules/max-depth>, <https://eslint.org/docs/latest/rules/no-unreachable>; typescript-eslint `max-params`: <https://typescript-eslint.io/rules/max-params/>.
- The owner's directive, items 3, 5, 6, 7 and 8: issue #285 of this repository.
