---
id: test-placement
type: rule
clade: engineering
subclade: python
title: A unit's test beside the unit
statement: A Python module that defines a function or a class has its test beside it, as stem_test.py in the same folder.
enforcement: hook
enforced-by: hooks/check-test-placement.py
references:
  - docs/testing.md
---

# A unit's test beside the unit

One condition, decided by `hooks/check-test-placement.py`. A reader who opens a module finds what checks it in the same folder, under the same name with `_test` added, and a module that grew a function nobody tested is visible in the directory listing rather than in a coverage report somebody has to run.

This is the layout `module-boundaries.md`'s reference layout already uses — tests colocated as `foo_test.py` — written down as a condition with a detector, which is item 9 of the owner's directive in #285.

## What the specification says, and what it leaves open

**Nothing in the Python specification places a test.** The Language Reference defines modules and packages and how `import` finds them (chapter 5, *The import system*); no PEP prescribes where tests live. The placement is therefore a choice between options the specification leaves open, and it is made on the directive's premises:

- **Maintainability.** The test changes when the unit does; beside the unit, the two are in the same diff, the same review hunk and the same `git log` of one folder.
- **No circular reference.** A colocated test imports its unit and nothing imports the test, so the edge points one way. A shared `tests/` tree that grows helpers imported back by the code is how a test tree becomes a dependency.

**Common practice is the second source, and it supports the form.** pytest's default discovery collects both `test_*.py` and `*_test.py` (pytest documentation, *Conventions for Python test discovery*), so the form needs no configuration. The suffix is chosen over the prefix because it sorts the test next to its unit in a listing, which is the whole point of putting it in the same folder.

**Where this departs from common practice, it says so.** The most common Python layout keeps every test under a top-level `tests/` directory, and pytest's own documentation describes it. This plugin keeps that directory for tests that exercise more than one unit — integration and acceptance — and puts each unit's test beside the unit. [`docs/testing.md`](../docs/testing.md) gives the layout, how a distribution leaves the colocated tests out of its wheel, and why the split is by what a test exercises.

## Conditions

1. **A module that defines a unit has `<stem>_test.py` beside it.** Decided by `hooks/check-test-placement.py`. A unit is a function, a coroutine or a class defined at the module's top level; a class that subclasses `Protocol` is not one, because it declares a contract and has no behaviour of its own (PEP 544). The test is a file named for the module's stem with `_test` appended, in the same directory. A test elsewhere does not satisfy it, nor does `test_<stem>.py` beside it: one form is what lets a reader and the detector find it without searching.

    These are not read, each because it is not a module that owes a unit test: a package initialiser (`__init__.py`) and an entry module (`__main__.py`), whose behaviour is the package's or the command's and is tested there; a `conftest.py`; a test itself; anything under a directory named `test` or `tests`, which is where the multi-unit tests live; and a file whose stem is not an identifier, such as `check-fees.py`, which an `import` statement cannot name (Language Reference §7.11, *The import statement*) and which is a script rather than a module. That last exemption is also why this repository's own hooks, which are scripts with `test-` suites beside them, are not findings.

    Not measured, and the reason is stated: neither corpus this plugin measures against — the CPython standard library and pip — places tests this way, so both would report nearly every module and the figure would describe their convention, not a defect. The condition has no threshold for a measurement to justify.

## Where this stops

**The condition checks that the test file exists, not what it tests.** An empty `fees_test.py` satisfies it. Whether the unit's behaviour is asserted is the review's, and the contributing plugin's traceability rule is what requires a criterion to be named by a test.

**It reads the top level only.** A function nested in another, or a method, is part of the unit that defines it and is tested through it.

**A module of data classes with no methods is a unit.** It defines a class, and the class has behaviour the language gives it — construction, equality, freezing — that the domain relies on. A value whose invariants live in `__post_init__` needs that test most.

**Generated code and migrations are excluded by path.** An Alembic revision, a generated client, a vendored module: leave them out of the paths the hook is given and write down why, the same answer `typing.md` gives for its own carve-outs.

**Tests of more than one unit are not placed by this rule.** Integration, acceptance and end-to-end tests live under `tests/`, where the language's community conventionally puts them; `docs/testing.md` says how they are split.

**This rule declares a hook, and its one condition has a script.** The statement reaches no request.
