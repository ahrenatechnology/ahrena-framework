---
id: module-boundaries
type: rule
clade: engineering
subclade: python
title: Module boundaries and import acyclicity
statement: Layers import only downward and the first-party import graph is acyclic; moving an import inside a function is the same edge and breaks no cycle.
enforcement: hook
enforced-by: hooks/check-boundaries.py
references:
  - docs/module-boundaries.md
---

# Module boundaries and import acyclicity

A Python codebase lays its contexts out under `components/`, a PEP 420 namespace root. Each context holds three layers — `domain`, `application`, `infra` — and each layer ships as its own distribution. An import runs down that order and never up, and the graph of first-party imports carries no cycle.

Every condition below is decided by `hooks/check-boundaries.py`, which builds the graph with the standard library's `ast` module and searches it. The script is the point. A dependency direction written in a document is an instruction, and the framework this one replaces had exactly that: a layer structure described in prose, nothing that blocked a violation, and a codebase that drifted anyway. `docs/module-boundaries.md` carries the rest of the argument.

## This is the Python instance of dependency inversion

The language-agnostic engineering plugin carries a SOLID rule whose sixth condition is dependency inversion, and that condition closes by saying the layer map is an input a reviewer supplies, because that plugin ships none. This rule is that condition with the map filled in and a script reading it.

A rule may reference only a doc, so that condition is linked from the body rather than declared: [`solid.md`](../../engineering/rules/solid.md), condition 6. The link is an ordinary relative path, which is how `foundation/rules/pilars.md` says a body link crosses a plugin, and it means a rename over there fails the gate here instead of quietly leaving this paragraph pointing at nothing.

One line of that condition is what a reader needs, and it is restated rather than fetched: **a module on the policy side of the layer map may not import a module on the mechanism side.** Everything else — when to invert by extracting a port and when to invert by moving the code — stays where it is, and is not duplicated here.

## What counts as a node

A node is a module: one `.py` file, `__init__.py` included.

Not a package. A cycle is a runtime failure, and the failure is between modules: executing `a` runs as far as its `import b`, which runs `b`, which reaches back to `a` and finds a half-built module object with the name it wants still unbound. Two modules in different packages that import each other's neighbours produce no such failure, and a graph drawn over packages would report one anyway. A package initializer is a node like any other because Python executes it like any other.

## How the graph is built

An edge is one import statement, resolved against the import roots the hook is pointed at. A dotted name that resolves to no file in those roots is standard library or third party and contributes nothing.

- **A relative import is resolved against the importing module's own package**, computed from its path, with each leading dot walking one level up. `from . import sibling` reaches the sibling module when one exists and the package initializer when it does not.
- **`from package import name` reaches the submodule `package/name.py` when that file exists, and `package/__init__.py` otherwise**, because that is what Python binds.
- **Naming a submodule of another package adds an edge to that package's initializer too**, since Python runs the initializer before the submodule. It is skipped when the importer already lives inside that package: by then the initializer has finished, or is the thing that pulled the importer in.

## Conditions

Each of these is decided by `hooks/check-boundaries.py`.

1. **The first-party import graph is acyclic.** A cycle is reported as the cycle — every module in it, in import order, closing back on the first, with the line of each edge — and never as a set of offending files, because the set does not say which import to delete.

2. **A layer imports only downward.** Under `components/`, `domain` ranks below `application`, which ranks below `infra`. A module in one layer may not import a module in a layer of higher rank, in its own context or in any other.

3. **A deferred import is the same edge as a module-level one.** An import written inside a function body counts in conditions 1 and 2 exactly as it would at module level, and the report marks it as deferred. Moving an import into a function changes when the coupling is paid and nothing else; it silences a detector that reads only the top of the file, and it leaves the codebase worse off than the cycle did, because the cycle at least announced itself.

4. **A `TYPE_CHECKING` import is an edge only when a name it binds is loaded outside an annotation.** Under `if TYPE_CHECKING:`, an import whose names appear solely in annotations is a legitimate cycle-breaker and is not an edge: it does not execute. A name it binds that is loaded anywhere else — a call, an `isinstance`, a default value, an alias assignment — makes the statement an ordinary edge, because the code needs the module at runtime and the guard is hiding that, not removing it.

5. **The namespace root and each context directory carry no `__init__.py`.** `components/` and each context directory directly beneath it are PEP 420 namespace levels. An initializer at either turns the namespace into a regular package and stops a second distribution contributing to it.

6. **Each layer directory carries its own `pyproject.toml`.** A layer is a distribution, not a folder. That is what keeps a layer's dependency set off the consumers of the layers beneath it.

## Where this stops

**One cycle is reported per strongly connected component.** A knot of four mutually importing modules contains many loops and one defect; reporting them all buries the finding. Breaking the reported cycle and re-running is the loop, and it terminates.

**A module gets no implicit edge to its own package initializer.** Adding it would report every package whose `__init__.py` re-exports its own submodules, which is most of them and almost always works. The cost is a narrow blind spot: a loop that closes only through an initializer that the importing module's own package triggers. The loops that actually break are written as explicit imports, and those are caught.

**Dynamic imports are invisible.** `importlib.import_module`, `__import__`, a plugin registry, a setuptools entry point and a dotted path read from configuration are all edges the graph does not contain, and a cycle that runs through one of them will not be reported. Resolving them needs the program running, which a gate does not have. This is the same blind spot the abstraction trigger in the engineering plugin declines to script, for the same reason.

**A string annotation that something evaluates at runtime is not covered by condition 4.** `typing.get_type_hints` on a class whose annotations name a `TYPE_CHECKING` import will fail, and the hook sees only annotations. A codebase that resolves hints at runtime has to treat those imports as runtime imports and write them unguarded.

**Condition 6 checks that the file is there.** Whether the distribution it declares actually packages that layer, and whether its metadata restates the dependency direction beside the dependency it explains, is a reader's job — the hook parses Python, not packaging. `docs/module-boundaries.md` gives the sentence that convention uses.

**The layer map is these three names.** A codebase that layers under different names, or that has more than three, gets conditions 1, 3 and 4 and nothing from condition 2. Making the map configurable would turn a rule into a setting, and a setting that every repository fills in differently is not a guardrail. A codebase with no `components/` directory at all is held only to acyclicity, which is the correct answer: the cycle is a defect anywhere, the layering is a convention this framework teaches.

**Nothing here bans a deferred import.** Condition 3 says a deferred import does not break a cycle; it does not say a function-level import is a defect. Deferring a genuinely optional or expensive dependency is fine and is not reported unless it closes a loop or crosses a layer upward.
