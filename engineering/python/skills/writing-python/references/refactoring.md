# Refactoring Python without changing what it does

Read at step 5 of `SKILL.md`, when existing code has to be reshaped before a behaviour fits. The procedure is `ahrena-engineering-quality:refactoring-safely`, and its own Python instance already carries the baseline, the mutation check, the per-commit gates and a worked example. This file adds what that instance does not: the Python reshapes that look behaviour-free and are not, and the plugin's hooks as part of each commit's gate.

## The gate for each commit

Every commit of a refactor runs the tests, `mypy --strict`, and the plugin's hooks over the files it touched: `check-typing.py`, `check-python.py`, `check-boundaries.py`, `check-test-placement.py`, with the fundamentals `check-structure.py`. A move that leaves a module without its `_test.py` beside it has moved half a unit. A refactor that moves code across layers is exactly what `check-boundaries.py` exists to catch, and a cycle it reports after a move is the move's, not the code's.

## Reshapes that change behaviour in Python

Each of these passes a careless reading as a pure refactor, and each changes what a caller observes. Treat them as behaviour changes: their own commit, their own test.

- **Renaming a parameter.** In Python a parameter's name is part of its signature, because any caller may pass it by keyword. Rename it only with every caller in the tree, and keep the old name working for a release where callers live outside it — or make the parameter positional-only with `/` first, which is the change that removes the name from the contract.
- **Reordering positional parameters or dataclass fields.** A dataclass's field order is its constructor's positional order. Moving a field changes every positional construction silently when the types agree.
- **Changing a default.** The default is evaluated once, at the `def`, and is read by every caller that omits the argument; a new default is new behaviour for all of them.
- **Moving or renaming a module or a class.** A pickled object, a dotted path in a settings file, a `mock.patch` target, a logging configuration naming a logger, an entry point in `pyproject.toml` and an import in another repository all address the old path, and none of them is an import the type checker follows. Search for the dotted path as a string before moving, and leave an alias where the old path is published.
- **Turning a list into a generator.** A caller that iterates twice, or takes `len()`, now sees an empty second pass or a `TypeError`. PY-6 of `reviewing-python` is this defect.
- **Making a function `async`.** Every caller must now await it; a caller that does not gets a coroutine object, which is truthy, and runs nothing. Change the callers in the same commit, and let `mypy --strict` find the ones that were missed.
- **Moving work to import time, or out of it.** A module-level call runs once, at first import, in whatever order imports happen. Moving a computation into or out of the module body changes when it runs and whether a test's patch is in place by then.
- **Narrowing an exception.** Replacing `except Exception` with the specific class is usually the right change and is a behaviour change: the failures it no longer catches now propagate. `rules/error-handling.md` and condition 5 of `rules/typing.md` say why it is still the right one.

## What does not need its own commit

A rename of a private name with every reference in one module, the extraction of a private helper, the inlining of a variable, a reorder of keyword-only parameters, and the conversion of a comprehension to a loop are shape-only and go together, under the gate above.
