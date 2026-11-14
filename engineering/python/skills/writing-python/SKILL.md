---
name: writing-python
description: Use before writing or changing Python (.py) - a behaviour, an endpoint, a use case, a repository, a job handler or a CLI - so it is written test-first against this plugin's rules and docs rather than checked against them afterwards. Places the behaviour in a layer, picks the library for the problem, writes the test red, writes the code under the rules, runs the plugin's hooks and the type checker, and reads the diff as a Python reviewer would before handing it back.
type: skill
clade: engineering
subclade: python
references:
  - rules/typing.md
  - rules/module-boundaries.md
  - rules/error-handling.md
  - rules/immutability.md
  - rules/testing.md
  - rules/security.md
  - rules/test-placement.md
  - docs/architecture.md
  - docs/libraries.md
  - docs/testing.md
  - docs/web-services.md
  - docs/persistence.md
  - docs/logging-and-observability.md
  - docs/toolchain.md
  - skills/reviewing-python/SKILL.md
  - ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md
  - ahrena-engineering-fundamentals:rules/solid.md
  - ahrena-engineering-fundamentals:rules/yagni.md
  - ahrena-engineering-fundamentals:rules/clean-code.md
  - ahrena-engineering-fundamentals:rules/kiss.md
  - ahrena-engineering-fundamentals:rules/value-semantics.md
  - ahrena-engineering-quality:skills/refactoring-safely/SKILL.md
---

# Writing Python

This plugin's rules are decided by hooks after the code exists, and its review skill reads the diff after it is written. This skill is the other end: what a writer reads and does before and while writing, so the hooks and the review find nothing. It does not restate a rule or a doc; each step names the one it applies, and opens it at the moment it is needed.

## 1. Read how this repository writes Python

Run `ahrena-engineering-fundamentals:skills/reading-the-component-map/SKILL.md` for the component the change lands in. Then read the repository's `pyproject.toml` — the Python version, the type checker and its mode, the linter, the test runner and its options — and its `AGENTS.md` or `CLAUDE.md`. The project's words, folders and tools win over every default below; a default applies only where the project is silent.

Output: the layer names, the folders the change may write to, the test command, the type-check command.

## 2. Place the behaviour in a layer

Open `docs/architecture.md` and decide which layer each part of the change belongs to: a rule in `domain/`, an operation in `application/`, an adapter — route, repository, client, handler — in `infra/`. A part that does I/O is not in the domain; a part with a business rule is not in a route. Where the change touches an edge, open the doc for it as well: `docs/web-services.md` for HTTP, `docs/persistence.md` for the database, `docs/logging-and-observability.md` for anything that logs, counts or traces.

Decide the composition the same way, from `docs/architecture.md`'s premises — maintainability, lower cyclomatic complexity, no circular reference:

- **A dependency is a `Protocol` the consumer owns, handed in through the constructor or a parameter** — SOLID and inversion of control as `ahrena-engineering-fundamentals:rules/solid.md` states them, in the form that page's SOLID section gives Python. No adapter is imported by the code that uses it.
- **Behaviour added to an existing package for one product or integration is a new distribution** that depends on the base and extends it through a protocol the base accepts or an entry point it reads — never an edit to the base, never a reach into its private names. `docs/architecture.md`, *Extending a package without modifying it*.
- **Every import points down the layers and closes no cycle**, between modules and between distributions — `rules/module-boundaries.md`.

The step fails when a new abstraction appears here without a second consumer or a test that needs the seam, which is the arbitration `ahrena-engineering-fundamentals:rules/yagni.md` gives SOLID. `docs/architecture.md`'s last section says when not to add a port, a use case or a layer.

Output: the files the change writes, by layer.

## 3. Choose a library only if the problem needs one

If the change needs a dependency the project does not have, open `docs/libraries.md` at the problem's entry, read its **Not when**, and check the project against it before adding anything. If the project already has a library for the problem, use that one. A new dependency is named in the hand-back with the entry that justified it.

## 4. Write the test red

Invoke the backend plugin's `ahrena-engineering-backend:driving-with-tdd` with the Skill tool and follow it at its step for the layer from step 2 — it is named here rather than declared, because that plugin already depends on this one — with `docs/testing.md` open for the Python shapes: which doubles that layer may use, factory fixtures, the async and database set-up. The unit's test is `<stem>_test.py` beside the module it tests, which `rules/test-placement.md` requires; a test of more than one unit goes under `tests/`. Double a port with a fake; never patch a name under `domain/` or `application/`, which `rules/testing.md` reports. Name the acceptance criterion the test covers with its token, `#N/AC-n`, in the test's name or docstring, which is where the contributing plugin's traceability rule reads it.

Run it and confirm it fails for the missing behaviour, not for an import error or a fixture typo.

Output: the red run — the command and the failing test names.

## 5. Write the smallest code that turns it green

Write against the rules as you go rather than fixing their findings afterwards. Single responsibility first, down to the function and the file, at the fundamentals plugin's limits — this plugin adds no number of its own:

- a function or method does one thing, holds at most 30 statements (`ahrena-engineering-fundamentals:rules/clean-code.md`), nests at most 3 deep and branches on no boolean parameter (`ahrena-engineering-fundamentals:rules/kiss.md`), and takes at most 4 parameters (`ahrena-engineering-fundamentals:rules/value-semantics.md`); a class is cohesive (`ahrena-engineering-fundamentals:rules/solid.md`, condition 1); a module solves one problem, and a second problem is a second module with its own `_test.py`. `ahrena-engineering-fundamentals`'s `hooks/check-structure.py` reports a unit past a limit, and step 6 runs it. Split before the limit is reached, not after the hook fires.

Then the Python rules:

- every parameter and return annotated, `Any` only with a reason, no mutable default, no blind handler left silent — `rules/typing.md`;
- an interrupt or a cancellation handed back, a raise a caller can name, nothing leaving a `finally` — `rules/error-handling.md`;
- a domain record frozen, a domain function returning a new value rather than changing its argument — `rules/immutability.md`;
- `eval`, `pickle`, a shell, a tar extract or `verify=False` only with a reason beside it — `rules/security.md`;
- imports only downward, and no cycle broken by moving an import into a function — `rules/module-boundaries.md`;
- nothing sensitive leaves the layer: a log call is given named fields and never a whole object, a type that carries a secret, personal data, a policy or a resource identifier redacts its own `__repr__`, and an upstream error is translated into the domain's own before the boundary — the rule of #294 in the security plugin, in the form `docs/logging-and-observability.md` gives Python, and PY-9 of `reviewing-python`.

Then refactor under green. If the change needs the existing code reshaped before the behaviour fits, do that first, as its own commits, by `ahrena-engineering-quality:skills/refactoring-safely/SKILL.md`; `references/refactoring.md` holds what is specific to Python about keeping a reshape behaviour-free.

Output: the green run — the command and the counts.

## 6. Run the plugin's hooks and the type checker

```sh
python3 <python-plugin>/hooks/check-typing.py <paths>
python3 <python-plugin>/hooks/check-python.py <paths>
python3 <python-plugin>/hooks/check-test-placement.py <paths>
python3 <fundamentals-plugin>/hooks/check-structure.py <paths>
python3 <python-plugin>/hooks/check-boundaries.py <import-roots>
mypy --strict --explicit-package-bases <paths>
```

Read the placeholders this way:

- **The plugin directories** are where `ahrena-engineering-python` and `ahrena-engineering-fundamentals` are installed; in the framework's own repository they are `engineering/python` and `engineering/fundamentals`.
- **The paths** are the files the change wrote, the tests included, each a separate argument. A hook given a path that does not exist exits with an error rather than reporting nothing; a count of `0 file(s)` means the paths did not reach it.
- **The import roots** are the directories the project's dotted imports resolve against — the one that holds `components/`, usually the project root.
- **The type check** is the project's own command when `pyproject.toml` declares one. Otherwise `--explicit-package-bases` is what lets mypy map a file under a PEP 420 namespace without `__init__.py` to its dotted name; without it, a module and the test beside it are found twice under two names (mypy documentation, *Mapping file paths to modules*). A finding is fixed, or answered with the reason the rule's own escape asks for, never silenced with a tool directive. `docs/toolchain.md` says why the checker is required and what each hook measured.

Output: each command with its last line.

## 7. Read the diff as a reviewer

Invoke `skills/reviewing-python/SKILL.md` on the diff, read it against the conditions it routes to, correct what it finds, and run steps 4 to 6 again. The review is not delegated to yourself to approve; it is the check that what the hooks cannot decide — an annotation that lies, a late-binding closure, a coroutine never awaited — is not left for the reviewer to find.

## 8. Hand back

Return the red run, the green run, the output of step 6, any dependency added with the `docs/libraries.md` entry behind it, and any rule escape used with its reason. Do not open or merge a pull request from here.

## When this skill does not apply

**A defect to find before it can be fixed.** Reproducing, isolating and fixing a bug is `debugging-python`, which starts from the failure rather than from a criterion.

**Reviewing someone else's Python.** That is `reviewing-python`, reached through the language-agnostic review route.

**Orchestrating a backend build across layers.** The order of the layers, their branches and their pull requests are the backend plugin's `building-backend-inside-out`; this skill writes the Python inside one of them.

**A refactor with no behaviour change.** That is `ahrena-engineering-quality:refactoring-safely` on its own, with `references/refactoring.md` for the Python cautions.

**Another language.** A `.ts`, `.go` or `.rs` file is that language plugin's.
