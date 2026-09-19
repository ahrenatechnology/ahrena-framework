---
id: module-boundaries
type: doc
clade: engineering
subclade: python
title: Layers, distributions and the import graph
summary: Why a layer is a distribution rather than a folder, why the import graph's node is the module, what each of the four hard cases costs, and why this one is a hook instead of a document.
references:
  - rules/module-boundaries.md
---

# Layers, distributions and the import graph

This is the companion to [`rules/module-boundaries.md`](../rules/module-boundaries.md). The rule states six conditions and names the script that decides each one; this explains where the layout came from, why the graph is drawn the way it is, and what the four hard cases would cost if they were handled any other way.

## Why this one is a hook

The framework this replaces already had the layer structure. It was written down, in a document, in sentences as direct as "`domain/` MUST NOT import from `infrastructure/`". The direction was correct and nothing enforced it, so it drifted, and the drift was discovered by reading rather than by a build going red.

That is the whole distinction the `enforcement` field exists for. A dependency direction stated in a document is an instruction: it reaches an agent only if the agent loads the document, and it reaches a person only if the person happens to be reading. An acyclicity check that runs is a guardrail: it costs no context, it cannot be skipped by someone who did not read it, and it fails at the moment the edge is added rather than at the review that notices six months later.

A cycle is also the kind of defect that gets worse quietly. Nothing breaks the day it is introduced, because Python only fails when the loop is entered in the unlucky order. What it does immediately is make both modules untestable in isolation and unmovable separately, and by the time somebody wants to split the package, the loop has three more edges.

## The layout, as it runs

The convention is not proposed here. It runs in production, and the rule codifies what already works.

```
components/{context}/
├── domain/        no framework imports
├── application/   ports.py defines the contracts
└── infra/         adapters
```

**Each layer is a distributable package with its own `pyproject.toml`, not just a directory.** This is the part that is usually dropped, and it is the part that does the work. A directory boundary is a convention a reviewer enforces; a distribution boundary is one the installer enforces. When the agent kernel ships separately from its infrastructure, the kernel's `strands`, `boto3` and `tiktoken` never reach a consumer that only needed the infrastructure adapters. The layer split stops being about tidiness and starts being about what gets installed.

**`components/` is a PEP 420 namespace root**, with no `__init__.py` at the namespace level and none at the context level either. That is what lets three separately built distributions contribute `components.billing.domain`, `components.billing.application` and `components.billing.infra` to one importable tree. An initializer at either level makes the namespace a regular package owned by whichever distribution ships it, and the second one to install shadows the first.

**The acyclicity is declared in the package metadata, beside the dependency it explains.** The kernel distribution's own description carries it: *"Importable by every context's application and agents subtree and by the agent deployables; depends on no context"*, and *"the dependency is acyclic: commons-infra to commons-domain, never back to this kernel."* Written there, it is in front of the person editing the dependency list, which is the moment the direction is at risk. Written only in a design document, it is in front of nobody.

The rule's condition 6 checks that the `pyproject.toml` exists. It does not read that sentence, and it could not check that the sentence is true — the truth of it is what conditions 1 and 2 decide, from the source, which is the better place to decide it from.

**One concept per module**, private modules prefixed with `_`, tests colocated as `foo_test.py`. That part of the convention carries no condition in the rule, because a script cannot count concepts.

## Why the node is the module

The graph could be drawn over packages, over distributions, or over modules, and only one of the three matches the failure.

A cycle is a runtime event. Importing `a` executes `a` top to bottom; reaching `import b` suspends that and executes `b`; if `b` reaches back to `a`, Python hands it the module object that is still half-built and the name it wants is not bound yet. The unit that is half-built is the module.

Draw the graph over packages and the detector reports cycles that cannot happen: `billing/invoice.py` imports `shipping/label.py`, `shipping/rate.py` imports `billing/tax.py`, no module is ever half-built, and the report says the two packages are cyclic. A detector that is wrong in the direction of over-reporting is the worse kind, because the first three false findings teach everybody to skip the gate.

Drawing it over modules costs one subtlety, which is that `__init__.py` is a module too and Python runs it before anything underneath it. The rule handles that by making the initializer a node and adding the edge that Python's own execution adds — and then, deliberately, not adding it for a module importing within its own package, where the initializer has already finished.

## The four cases that make the graph hard

**Relative imports** are the easy one, and the one a regular expression gets wrong first. `from . import sibling` and `from ..other.thing import Thing` carry no absolute name, so they have to be resolved against the importing module's own position. A detector that skips them has a hole exactly where intra-package cycles live, which is where most of them live.

**`__init__.py` re-exports** are the case that tempts a detector into over-reporting. A package initializer that re-exports its submodules has an edge to every one of them; a submodule that imports a name from its own package root has an edge back. Treated naively, every convenience `__init__.py` in the repository is a cycle. Treated as the rule does — the initializer is a node, an explicit edge to it counts, an implicit one from inside the package does not — the loops that actually break are reported and the ones that never break are not. The blind spot that remains is written down rather than papered over.

**`TYPE_CHECKING` is the one that genuinely lands on both sides**, which is why the rule has to choose and the hook has to match. Under `if TYPE_CHECKING:` the import does not execute, so a name used only in an annotation costs nothing at runtime and the edge is not real. It is the sanctioned way to annotate across a boundary that would otherwise be circular, and a detector that flags it is telling people to delete their type hints.

The same syntax with the name used at runtime is the opposite: a call, an `isinstance`, a default argument or a module-level alias that reads a `TYPE_CHECKING` name is a `NameError` the moment the line runs. The coupling is real, the guard is hiding it, and the guard has also removed the import that would have documented it. So the hook looks at where each bound name is loaded — inside a type annotation or anywhere else — and decides per name rather than per statement.

**The deferred import** is the one the rule exists to refuse. A cycle is reported; the import moves inside the function that needed it; the detector goes quiet; nothing else changes. The modules still cannot be tested apart, still cannot be moved apart, and still cannot be packaged apart. What the move has bought is the loss of the signal. The failure mode has also become worse: instead of an `ImportError` on the first import, there is an `ImportError` on whichever call path reaches that function first, in production, under whatever ordering the request happened to take.

So a function-level import is an edge, and the report marks it as deferred, and the message says what the marking means. That last part matters more than it looks. A gate that reports the cycle without naming the workaround gets the workaround applied a second time, by somebody who assumed the first attempt was nearly right.

## The relationship to dependency inversion

The language-agnostic engineering plugin's SOLID rule ends its dependency-inversion condition by admitting that the layer map is an input a reviewer has to supply. This rule supplies it for Python: three named layers, one ranking, one script.

That is the only thing added. The part of the condition about *how* to invert — that extracting a port and moving the code are both inversions, that the second is smaller and almost never the one proposed, and that a port with one adapter and no test at the seam is the shape the abstraction trigger deletes — is not restated here and should not be. A reader who needs it reads that rule.

A reference could now address it. `foundation/rules/pilars.md` has since settled the cross-plugin form — `ahrena-engineering:rules/solid.md`, the marketplace name and then the plugin-relative path — and doc-to-rule is a pair the matrix permits. It is still not declared here, and the reason has changed from "cannot" to "will not": a declared reference is a load edge, and a reader who needs the inversion argument should pay for that rule when they open it rather than every time they open this page. Naming it in prose costs nothing. `docs/toolchain.md`, the other doc in this directory, does declare a qualified reference, because it argues against a decision that lives in the other plugin and a reader cannot check the argument without it.

## Where this stops

**This document does not teach layered architecture.** It assumes the reader knows what a domain layer is for and needs to know what this framework will hold them to, and what the script can see.

**It says nothing about the boundary between contexts.** `components/{context}/` is one namespace level per bounded context, and which context a module belongs in is a modelling decision no import graph can check. The rule reaches the direction between layers and the absence of cycles; it has no opinion on whether `billing` should have been two contexts.

**It carries no opinion on the shared kernel's contents.** A distribution that every context imports and that imports no context is a legitimate shape, and it is also the easiest place in a codebase for unrelated things to accumulate. What stops that is the cohesion condition in the engineering plugin's SOLID rule and a reviewer, not this one.

**It does not cover async import ordering, lazy module objects, or `sys.modules` manipulation.** Each defeats the static graph, each is rare, and each is a deliberate act by someone who should be writing down why.
