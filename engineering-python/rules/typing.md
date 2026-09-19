---
id: typing
type: rule
clade: engineering
subclade: python
title: Types that hold, and the defects they do not catch
statement: Python annotates every parameter and return, passes `mypy --strict`, justifies every `Any`, defaults nothing to a mutable, and discards no exception it caught.
enforcement: judgment
references:
  - docs/toolchain.md
---

# Types that hold, and the defects they do not catch

Five conditions. The first is decided by a type checker the consuming project runs, and the other four by `hooks/check-typing.py`, which parses the source with the standard library and needs nothing installed. `docs/toolchain.md` explains why the tooling this rule came from shipped as a configuration file and why none of that configuration is here, which of the seventeen Ruff rule families that source selected survived a triage, and where every number in this rule came from.

The subject is a function's declared contract, and the two halves of the rule are the two ways that contract goes wrong. Conditions 1 to 3 are about the contract being written down and being true: an unannotated parameter is a contract the reader infers, an `Any` is a contract withdrawn, and a wrong annotation is a contract that lies. Conditions 4 and 5 are the two places where Python lets a complete, correct, `mypy --strict`-clean signature describe behaviour the function does not have. A default that is a list is shared by every caller that takes it, and the signature says nothing about that. A handler that catches everything and returns says the function succeeded, and the signature says nothing about that either.

None of the five adds an abstraction, so the abstraction trigger in condition 1 of `engineering/rules/yagni.md` does not gate any of them. Annotating a parameter writes down what was already true; deleting a blind handler removes code.

## Why this rule names a library, and what that costs

A rule may require the consuming project to adopt a library when the condition does not exist without one. That is the case here, and it is worth being precise about why, because a rule that names a library without this argument is a rule imposing a stack.

An AST can see that an annotation is missing. It cannot see that one is wrong. Deciding whether `def total(rows: list[Invoice]) -> str` tells the truth means resolving `Invoice` across files, following every call in the body, and running a type system over the result — and there is no second thing in the world that does it. Condition 2 without condition 1 buys annotations that are decoration: complete, uniform, and free to drift from the code the moment either changes. So the rule requires a checker, and the checker is mypy.

The framework's own no-dependency constraint is not in tension with this. That constraint is about the hooks, which run on a consumer's machine with nothing installed and must therefore stay inside the standard library. It was never about what a rule may ask of the project it governs. The split runs straight down this rule: condition 1 is the consuming project's job and its pipeline's, conditions 2 to 5 are the hook's, and the hook holds on a project that has configured nothing at all.

`--strict` is taken from mypy unchanged, and this rule does not enumerate what it expands to. Mypy defines the flag as the strictest set of options it currently supports, and that set grows with releases; a transcribed list of the flags behind it would be a second source of truth that is wrong at the next release and silently weaker than the word it replaced. The reason the flag is required rather than the default is that mypy's default does not check the body of an unannotated function, so "mypy passes" on an unannotated codebase is a statement about nothing.

## Conditions

1. **`mypy --strict` reports no error over the project's Python.** Decided by mypy, run by the consuming project's pipeline — not by anything in this plugin, and not by this rule's hook. This is the condition that does not exist without a library, for the reason the section above gives. The threshold is zero errors, which is the only figure available: a type error is not a quantity to stay under, and a tolerance would be a count of accepted lies. Where a third-party library ships no stubs, the escape is `# type: ignore[<code>]` with the code named and a comment saying which library and why, so that the ignore can be deleted when the stubs arrive.

2. **Every parameter and every return carries an annotation.** Decided by `hooks/check-typing.py`. A method's receiver is excluded, taken positionally rather than by name, so a method that calls it something other than `self` still has one and a `staticmethod` has none. An `__init__` with at least one annotated parameter owes no return type, which is mypy's own exemption rather than a softening invented here — a hook that disagreed with the checker condition 1 requires would be reporting a state that checker calls correct. This condition overlaps `disallow_untyped_defs`, which `--strict` turns on, and it is kept anyway: that flag is configuration, configuration has per-module overrides, and the tooling document this rule replaces used one to switch it off for the whole test tree. The hook has no override. A path that should not be held is left out of the invocation, in the command line where it is visible, rather than in a table nobody rereads.

3. **An `Any` in an annotation carries a comment saying why, on its line or the line above.** Decided by `hooks/check-typing.py`. `Any` is not a type; it is an instruction to stop checking, and it propagates to everything downstream of the value it annotates. A comment that is a tool directive — `# type: ignore`, `# noqa`, `# pyright: ...` — is not a reason, it is the second half of the same silence. The gate checks that somebody was made to write something, not that what they wrote is a reason; that is the same trade `foundation/rules/completeness.md` makes and the same place it stops.

4. **No parameter is defaulted to a mutable literal or to a call that builds one.** Decided by `hooks/check-typing.py`. The literals are list, dict and set displays and their comprehensions; the calls are Ruff's B006 list — `list`, `dict`, `set`, `bytearray`, `deque`, `defaultdict`, `OrderedDict`, `Counter`, `ChainMap` — taken closed and unchanged, because a closed list is what keeps `Decimal("0")` out of the report. A default is evaluated once, when the `def` runs, and every caller that takes it shares one object. The signature is complete, the annotation is correct, `mypy --strict` is clean, and the function still does not do what it says. The fix is to default to `None` and build the value in the body.

5. **No `except:` or `except Exception:` handler discards what it caught.** Decided by `hooks/check-typing.py`. A handler discards when its body does none of three things: re-raise, call something from the logging vocabulary — `logger.exception`, `logging.error`, `warnings.warn` and their siblings, or `sys.exc_info` and `traceback.format_exc` for a bare handler that has no name to bind — or load the name it bound. A handler naming the failure it absorbs is not read at all: `except KeyError: return default` is a decision about a known failure, and this condition has no opinion about decisions. What it refuses is the handler that catches every failure there is, including the ones nobody anticipated, and leaves no trace of any of them.

## Where this stops

**Condition 1 is not decided by anything in this plugin, and the hook does not pretend otherwise.** It does not look for a `[tool.mypy]` table, because a table proves that somebody wrote a table. A configuration is not a run, and the property the condition is about is that the checker ran and said nothing. That check belongs in the pipeline, beside the tests, which is where `docs/toolchain.md` puts it.

**One checker, not a choice of checkers.** Pyright in strict mode decides substantially the same condition, and this rule still names one. A rule that accepts any of three configurations is a setting, and a setting every repository fills in differently is not a guardrail — the same position condition 2 of `rules/module-boundaries.md` takes about its layer map. The cost is real and lands on a project standardised on pyright: it substitutes its checker, writes down that it did, and keeps the other four conditions unchanged. What the rule refuses to do is ship the choice.

**Condition 2 does not read whether the annotation is true.** That is condition 1's entire job, and it is why the rule cannot be satisfied by the hook alone. A codebase that annotates everything incorrectly passes conditions 2 to 5 and fails the rule.

**Condition 2 does not reach a lambda**, which has nowhere to put an annotation, and it does not reach a parameter whose type is genuinely unnameable without a protocol nobody has written. The second case is a design problem, and writing the protocol is the fix rather than the exemption.

**Condition 2 holds the test tree like everything else, and that is the part people will want to turn off.** An untyped test helper is where the untyped fixture lives and where the wrong argument reaches production code unchallenged. If a tree genuinely should not be held — a migrations directory, a generated client — leave it out of the paths the hook is given and write down why, the way `engineering/rules/clean-code.md` and `engineering/rules/kiss.md` already ask for their own carve-outs.

**Condition 3 does not see an `Any` that never appears in an annotation.** `cast(Any, value)`, an alias such as `from typing import Any as Opaque`, and an untyped third-party function whose return is `Any` by inference are all the same erasure and none of them is in an annotation this hook reads. The third is the common one, it is invisible to any parser, and it is what `warn_return_any` inside `--strict` exists to catch — which is condition 1 again, doing the part a parser cannot.

**Condition 4 will report a deliberate sentinel, and two of them are in the corpus it was measured against.** CPython's `copy.deepcopy(x, memo=None, _nil=[])` and `functools._make_key(..., fasttypes={int, str})` both default to a mutable that is never mutated, in one case as a private identity sentinel and in the other to bind two names at definition time. Both are findings and both have "no" for an answer. Exclude by path and write down why, which is the same answer `engineering/rules/duplication.md` gives to the same shape of question.

**Condition 5 does not recognise every way of leaving a trace.** A handler that writes to `sys.stderr` by hand, or that routes the failure through a project's own reporter without passing the exception to it, is silent as far as this detector is concerned. The first is rare enough to exclude by path; the second is a finding whose fix is to pass the exception, which is what the reporter wanted anyway. Widening the recognised set to any call at all would make the condition report only `except Exception: pass`, which is the one case nobody needs a gate for.

**Condition 5 has no opinion on the level, the message, or whether the failure should have been caught at all.** A handler that logs at `debug` and returns a default satisfies it, and may still be the wrong handler in the wrong place. Deciding that needs to know what the caller does next, which is a reviewer.

**Nothing here reaches a defect the types describe correctly.** A function whose annotations are complete, checked and honest can still compute the wrong number. This rule is about the contract, not about whether the contract was worth signing.

**This rule declares judgment rather than a hook, and the reason is condition 1.** Four of the five conditions have a script, and declaring `hook` would deliver those four and contribute no text to any request — which is the cheapest route and the one `engineering/rules/clean-code.md` and `engineering/rules/duplication.md` take. What it would drop is the requirement to run a type checker at all, because a hook rule is replaced by its script and this script cannot decide condition 1. The requirement is not a detail of the rule; it is the reason conditions 2 and 3 are worth anything, and a plugin that shipped annotation-presence checks while silently dropping the checker would be teaching decoration. So the rule takes the route `engineering/rules/solid.md` and `engineering/rules/contract-first.md` take: the statement is injected, the script still exists and conditions 2 to 5 name it, and a reviewer and a pipeline can both run it. The cost is counted rather than waved at — the always-loaded footprint across the framework's judgment rules was 1,001 characters over seven rules, this is the eighth, and its statement adds 159; `foundation/docs/context-budget.md` keeps the account.

**This rule is Python's and does not generalise.** Conditions 4 and 5 are two pieces of Python syntax: a default evaluated at definition time and an except clause that can name a base class. A language that evaluates defaults per call has no condition 4, and a language with checked exceptions decides condition 5 at compile time. Condition 1 is Python's because Python's type system is optional and bolted on; a language whose compiler refuses to build an ill-typed program does not need a rule requiring that somebody run the checker.
