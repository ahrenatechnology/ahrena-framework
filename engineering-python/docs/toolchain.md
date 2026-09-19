---
id: toolchain
type: doc
clade: engineering
subclade: python
title: The Python toolchain, triaged
summary: Why the tooling this plugin inherited was a configuration file rather than a rule, which of Ruff's seventeen selected families survive a triage and on what criterion, why mypy is the one library a rule here names, and what the two detectors measured across 313,000 lines.
references:
  - rules/typing.md
  - ahrena-engineering:docs/clean-code.md
---

# The Python toolchain, triaged

This is the companion to [`rules/typing.md`](../rules/typing.md). The rule states five conditions; this explains where they came from, which parts of the toolchain they deliberately leave out, and what the numbers behind them are.

It is also a refusal. The document this plugin inherited was a `pyproject.toml` with prose around it, and almost none of that file is here. The argument for the omission is the substance of this page.

## What the source was, and why it could not ship

The predecessor's tooling manual listed eight tools, a Ruff configuration selecting seventeen rule families, a mypy block, a pytest block, a pre-commit file with three pinned revisions, a dependency table with fourteen version floors, and a six-line CI script. It is a competent configuration. It is not an artifact this framework can ship, for three reasons.

**It never says what holds when the configuration is absent.** Every statement in it is conditional on somebody having copied the file in. A project that copies nothing gets nothing, and the manual has no answer for that project — which is most projects, at the moment they most need one. The rule beside this document is built the other way round: four of its five conditions are decided by a script that ships inside the plugin and reads source, so they hold on a repository that has configured nothing and installed nothing.

**Its content is version pins, and version pins are wrong on a schedule.** `ruff>=0.8.0`, `mypy>=1.13.0`, `pre-commit>=4.0.0`, `fastapi[standard]>=0.122.0`, and three pinned pre-commit revisions beside them. Each was true when it was typed. A document whose body is a set of floors has to be re-read at every release of fourteen packages to know whether it is still correct, and nobody does that, so it decays into a thing people copy without reading. Choosing a floor is a project's job, done against that project's lock file.

**It restates itself, and the restatement is already redundant.** The mypy block sets `strict = true` and then sets `warn_return_any`, `warn_unused_configs`, `disallow_untyped_defs`, `disallow_any_generics` and `check_untyped_defs` beneath it. All five are implied by `strict`. A reader cannot tell which lines are doing work and which are decoration, and the next mypy release moves that boundary again — the source pins `mypy>=1.13.0`, and mypy 1.19 lists fifteen flags behind `--strict`, one of which, `--strict-bytes`, did not exist when that floor was written. This is the failure mode of a transcribed configuration in miniature, and it is why `rules/typing.md` requires the flag and refuses to enumerate what it expands to.

So this document argues, and the project writes the file.

## The triage

Seventeen Ruff families were selected by the source. Three of them carried a sentence of reason; the rest carried none. A family earns a condition in this plugin when all three of the following hold.

1. **It decides a defect, not a style.** A style is settled by running a formatter and never discussing it again. A defect is a thing that is wrong whether or not anybody has an opinion.
2. **A standard-library parser can decide it with no configuration.** The hooks take no dependencies, because a consumer has to be able to run exactly what CI runs.
3. **Nothing in the framework already decides it.** A second detector for a decided condition is a second source of truth.

Two rules, drawn from two families, pass all three, and one of them only after being narrowed. The rest are placed below, with the reason each one did not, because a triage that only names its winners is a list of preferences.

### Settled by the formatter: `E`, `W`, `I`, `UP`, `N`, and the format block

Run a formatter, accept its output, and stop. These families produce no finding this framework wants a reader to read, and they produce no condition here.

**The one number in the source is here, and it is refused.** `line-length = 120` is not measured, and it is not Ruff's default either — Ruff's default is 88, inherited from Black. The source moves it and says nothing about why. Keeping it would put an unexplained number into a framework whose other thresholds each carry a measurement or a named ancestor, and it would also contradict a decision already taken: condition 1 of `ahrena-engineering`'s clean-code rule counts statements rather than lines precisely because a line count is the formatter's output and moves whenever the formatter's settings do. [`clean-code.md`](../../engineering/docs/clean-code.md) makes that argument at length. A project picks a line length; this framework has no business having one.

`target-version = "py311"` goes the same way. It is a true and useful fact about a particular project and it is not a rule about any other.

### Already decided elsewhere in the framework: `SIM`, `TCH`, `ARG`, `C4`

**`SIM`** is flake8-simplify, and simplicity in this framework is `ahrena-engineering`'s KISS rule: nesting depth and boolean parameters, both measured, both scripted. A second opinion about `if x: return True else: return False` is not worth a rule.

**`TCH`** is the interesting one, because it points the opposite way from a condition this plugin already has. TCH moves imports used only in annotations under `if TYPE_CHECKING:`. Condition 4 of `rules/module-boundaries.md` decides when such a guard is honest — an import under the guard is an edge in the import graph as soon as a name it binds is loaded outside an annotation. The two are compatible and the order matters: a codebase that enables TCH and has no condition 4 acquires guarded imports it genuinely needs at runtime, which fail as a `NameError` on the first call path that reaches them. The family is fine. The condition that makes it safe is already here.

**`ARG`** reports unused arguments, which sits next to the dead-code condition in `ahrena-engineering`'s clean-code rule and is mostly noise on interface implementations and callbacks. **`C4`** is comprehension style.

### Decides a defect, and is still not promoted: `F`, `S`, `DTZ`, `A`, `RUF`, `T20`

**`F`** is pyflakes: undefined name, unused import, f-string with no placeholder. These are real defects and a stdlib reimplementation of them would be a worse pyflakes, shipped to compete with the one every project already has. Criterion 3 excludes it, in the sense that the world already decides it.

**`S`** is bandit, and it is refused on subject rather than on difficulty. A security posture — what counts as a hardcoded secret, whether `assert` is acceptable outside tests, which subprocess call is a finding — is a rule of its own with its own boundary section, and putting it inside a typing document is the same drift that produced the source.

**`DTZ`** — a naive `datetime` where an aware one was meant — is the strongest candidate for the next promotion. It is a defect, a parser decides it, and nothing here covers it. It is not in `rules/typing.md` because it is not about typing, and inventing a home for it inside this rule would be how a rule becomes a bag.

**`A`** is shadowed builtins and **`RUF`** is Ruff's own miscellany; both are style-adjacent. **`T20`** bans `print`, which is right for a service and wrong for the four command-line hooks in this repository, all of which print by design. That is a project decision and it belongs to a logging rule this framework has not written.

### Promoted: `B006` and a narrowed `BLE`

**`B006`** — a parameter defaulted to a mutable literal or to a call that builds one — is condition 4 of `rules/typing.md`. It clears all three criteria: the default is evaluated once when the `def` runs, so every caller that takes it shares one object, which is a defect and not a preference; `ast` decides it; and nothing else in the framework reads parameter defaults. The list of builder calls is Ruff's, taken closed and unchanged, because a closed list is what keeps `Decimal("0")` out of the report.

**`BLE001`** is where the transcription would have been wrong, and the measurement below is what says so. The Ruff rule reports `except Exception:` wholesale. Across the CPython standard library as installed here, 373 handlers catch everything; 101 of them discard what they caught. Shipping BLE001 as written would report 272 handlers that re-raise, log, or use the exception — a detector that is wrong about a common idiom, which `ahrena-engineering`'s simplicity document records as the failure that gets gates switched off and which already cost the KISS rule a condition. So condition 5 asks the narrower question the family was reaching for: not *did you catch everything*, but *did you catch everything and drop it*.

## Why mypy is named, when nothing else is

`rules/typing.md` requires the consuming project to run `mypy --strict`. It is the only place in this framework where a rule requires a library, and the argument is short: an AST sees that an annotation is missing, and only a type checker sees that one is wrong. Deciding whether `def total(rows: list[Invoice]) -> str` tells the truth means resolving a name across files and running a type system; there is no second thing that does it, and a missing-annotation check without it delivers decoration.

The no-dependency constraint this framework repeats is about the hooks. They run on a consumer's machine with nothing installed, so they stay inside the standard library. It was never a constraint on what a rule may ask of the project it governs, and reading it that way is how the source ended up with a law that says "CI adopts the stack baseline" and names no baseline.

The rule names one checker rather than a set, and its boundary section carries the cost of that to a project standardised on pyright.

## What the two detectors measured

Both figures below come from `hooks/check-typing.py` run as it ships, on 2026-09-19.

**This repository's own Python** — 10 files, 6,290 lines, 208 function definitions, 10 exception handlers, 6 parameter defaults, and no occurrence of `Any` anywhere.

| Condition | Findings |
|---|---|
| 2, annotation present | 6 |
| 3, `Any` justified | 0 |
| 4, mutable default | 0 |
| 5, discarded exception | 0 |

All six are in one file, `engineering/hooks/check-structure.py`: four generator functions and one helper with no return annotation, and one unannotated parameter. None of the ten handlers in the repository catches everything.

Condition 1 was run too, on the four files this plugin owns, and they are clean under `mypy --strict` — which is the rule being satisfied rather than described. It is not run in CI, and the reason is stated in the boundary section below.

**The CPython 3.11 standard library as installed here** — 670 files, 306,907 lines, 14,720 function definitions, 2,793 exception handlers, 5,781 parameter defaults, 33 occurrences of the name `Any`.

| Condition | Findings | Of what |
|---|---|---|
| 2, annotation present | 24,505 | 14,720 definitions |
| 3, `Any` justified | 27 | 33 occurrences |
| 4, mutable default | 50 | 5,781 defaults |
| 5, discarded exception | 101 | 373 handlers that catch everything |

Each row says something the rule needed to know.

**Condition 2's 24,505 is not an indictment of the standard library**; it is the shape of the condition. Most Python in the world is unannotated, so complete annotation is a commitment a project makes rather than a defect that exists everywhere. That is exactly why the rule pairs it with a checker: the commitment is worth making only if something verifies the annotations are true.

**Condition 4 fires on 0.9% of the defaults it reads.** A condition that reports one site in a hundred is a condition. Two of the fifty are deliberate — `copy.deepcopy`'s private `_nil=[]` sentinel and `functools._make_key`'s `fasttypes={int, str}`, both read-only — and the rule's boundary section names them as findings with "no" for an answer rather than pretending the detector has none.

**Condition 5 fires on 27% of the handlers that catch everything, and on 3.6% of all handlers.** The 73% it stays quiet on is the measurement that shaped it, and it is the difference between this condition and the Ruff family it came from.

**Condition 3 fires 27 times in 306,907 lines**, which is what a rule about an escape hatch should look like: rare, and each occurrence worth a sentence.

## How a project runs this

Two commands, and neither of them is a configuration file.

```
python3 engineering-python/hooks/check-typing.py src tests
mypy --strict src
```

The first takes no dependencies and decides conditions 2 to 5 on every path it is given. The second decides condition 1 and is the project's to install and configure. Paths that genuinely should not be held are left out of the first command, where the exclusion is visible in the pipeline, rather than hidden in a per-module override.

## Where this stops

**This document configures nothing.** There is no `pyproject.toml` here, no `.pre-commit-config.yaml`, and no version floor. A project reading it should end up writing its own file and being able to say why each line is in it.

**It has no opinion on the test runner.** The source's pytest block — markers for unit, integration and property tests, `asyncio_mode = "auto"`, `--strict-markers` — is sensible and homeless. Test organisation is a subject with its own conditions and its own boundary, and this framework has not written that rule. Transcribing the block here would put a testing opinion inside a typing document, which is the drift being refused.

**It has no opinion on dependencies or on supply chain.** `pip-audit` in the source's CI list is correct and belongs to a security rule that does not exist yet, beside the bandit family refused above. Until that rule is written, a project that runs `pip-audit` is doing something this framework neither requires nor discourages.

**pre-commit is not required, and the reason is not that it is bad.** It is a convenience; the gate is CI, as the source itself says. What a mandate would add is a second file in which every tool version lives, kept in agreement with the first by hand. A project that wants the local loop should have it.

**The triage above is this framework's, and another framework would run it differently.** What is not negotiable is that a triage happened. Seventeen families were enabled in the source with three sentences of reason between them, and a list that long with a rationale that short is a list nobody will ever remove anything from.

**Condition 1 is not in this repository's own pipeline, and that is a real gap rather than an oversight.** The framework's CI installs nothing, by design, so that it runs exactly what a consumer runs; mypy is an install. The four files in this plugin are clean under `mypy --strict` and were checked by hand, which is weaker than a job and is stated as such. A consuming project has no such constraint and should wire the second command above beside the first.

**Four conditions is a floor, not a ceiling.** A project that runs no linter at all still gets them, which is the point. A project that runs Ruff with the families above gets considerably more, and should.
