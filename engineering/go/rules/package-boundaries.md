---
id: package-boundaries
type: rule
clade: engineering
subclade: go
title: Packages that depend in one direction
statement: Go packages import in one direction: no cycle, domain below application below infra, no require cycle between modules, and what is not promised under internal/.
enforcement: judgment
references:
  - docs/project-layout.md
  - docs/toolchain.md
---

# Packages that depend in one direction

Go's unit of composition is the package, and its unit of release is the module. The specification makes the first rule of composition a compile error: "It is illegal for a package to import itself, directly or indirectly" (the Go Specification, *Import declarations*). That settles cycles between packages and nothing else. To the compiler a layer is only a directory, so a domain package may import the database adapter and the build is green; and the `go` command resolves requirements with minimal version selection, whose design says outright that its algorithms "must not assume the module requirement graph is acyclic" (Russ Cox, *Minimal Version Selection*, the design behind `go.dev/ref/mod`). The conditions below are the two directions the toolchain does not hold, the one it does, and the boundary `internal/` draws.

The layer vocabulary — `domain`, `application`, `infra`, in that order — is the one the Python plugin's `module-boundaries` rule already uses, taken unchanged so that the two plugins describe the same architecture with the same words. [`docs/project-layout.md`](../docs/project-layout.md) argues the direction, how Go's consumer-declared interfaces invert the dependency that would otherwise point up, and how a package is extended without being edited.

## Conditions

1. **No package imports itself, directly or indirectly.** Decided by the compiler: `go build` and `go vet` stop with `import cycle not allowed`. The threshold is zero, because the build fails at one. Source: the Go Specification, *Import declarations*.

2. **A package in a layer imports no first-party package in a layer above it.** A package whose path, inside its module, holds a directory named `domain` ranks below one holding `application`, which ranks below one holding `infra`; an import from a lower rank to a higher one is the violation, in its own bounded context or another's, in its own module or another module of the same repository. A package outside any layer — `cmd/`, a shared utility — is not ranked. Decided by [`hooks/check-packages.py`](../hooks/check-packages.py). Source for the direction: condition 6 of [`solid.md`](../../fundamentals/rules/solid.md) in the fundamentals plugin, dependency inversion, of which this condition is the Go-specific detector.

3. **The modules of one repository do not require one another in a cycle.** Read from every `go.mod` in the tree, through `require` lines whose module path is another module of the same tree. Decided by [`hooks/check-packages.py`](../hooks/check-packages.py), which reports each cycle once, as the module paths in order. Source: *Minimal Version Selection*, which tolerates such a cycle by design, so nothing in the toolchain reports it.

4. **A package that importers outside the module are not promised lives under `internal/`.** In a service that is every package but `cmd/`; in a library it is everything but the packages its documentation names as its API. Decided by a reviewer, who reads each new package's path against what the module publishes. Source: the `go` command documentation, *Internal packages* — "Code in or below a directory named "internal" is importable only by code that shares the same import path above the internal directory"; *Organizing a Go module*, `go.dev/doc/modules/layout`.

5. **A behaviour is extended by a new package that depends on the base package through what the base exports, not by editing the base to know about the extension.** The base accepts an interface, a function type or an option, and the extension satisfies it from its own package; the base imports none of its extensions. Decided by a reviewer, who reads whether a change that adds a variant edited the base to add a branch for it. Source: condition 4 of [`solid.md`](../../fundamentals/rules/solid.md), open/closed, which fixes when the extension point becomes due — the third occurrence of the same discriminator chain — and its YAGNI arbitration, which this condition does not override.

## Where this stops

**Condition 1 is stated so the rule is whole, not because anything here decides it.** The compiler does, on every build, and a project that compiles meets it.

**Condition 2 knows three layer names and no others.** A project that names its layers `core`, `usecase` and `adapter` is not held until its directories carry the framework's names, or until a project-specific map is added to the hook, which this plugin does not ship. The cost is the same one the Python rule carries, and the reason is the same: a rule that accepts any vocabulary is a setting, and a setting every repository fills in differently is not a guardrail. A project with no layered directories at all passes condition 2 vacuously; it is still held to conditions 1, 3, 4 and 5.

**Condition 2 does not read test files.** An integration test in a `domain` directory that wires the real `infra` adapter is a test of the composition, not a dependency of the domain, and `go build` never links it into the domain package.

**Condition 3 sees only the modules in the tree it is given.** A cycle through a module published from another repository needs both `go.mod` files, and the hook reads only files on disk. On the Go 1.27.4 source of `net/http`, `database`, `context` and `cmd/go` — the `std` and `cmd` modules, 440 files of Go after generated files are skipped — conditions 2 and 3 report nothing: neither module has layer directories, and they do not require each other. That is a measurement of absence on code the conditions do not target, not of precision; no layered Go service was at hand to measure against.

**Condition 4 cannot be decided by a script.** Whether a package is promised to outside importers is the author's intent, written in the module's documentation, and a package outside `internal/` is not a defect until somebody depends on it who should not.

**Condition 5 is a reviewer's, and its trigger is the fundamentals'.** Whether a change should have added an extension point instead of a branch depends on how many variants exist today, which [`solid.md`](../../fundamentals/rules/solid.md) counts and [`yagni.md`](../../fundamentals/rules/yagni.md) arbitrates. An extension point built for a variant nobody has written is the YAGNI defect, not compliance with this condition.

**Which interface goes where is [`api-surface.md`](api-surface.md).** That a constructor returns a concrete type and an interface is declared by its consumer is condition 3 there; this rule holds only the direction of imports.
