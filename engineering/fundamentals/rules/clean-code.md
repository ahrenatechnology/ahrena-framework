---
id: clean-code
type: rule
clade: engineering
subclade: quality
title: The readable surface
statement: A function body holds at most 30 statements, no statement follows an unconditional exit, and no comment is commented-out code.
enforcement: hook
enforced-by: hooks/check-structure.py
references:
  - docs/clean-code.md
---

# The readable surface

Three conditions, all decided by `hooks/check-structure.py`. Each is a shape in the source rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. `docs/clean-code.md` gives the provenance of the threshold, the two conditions that were considered and left out, and the cases where the fix is worse than the finding.

This rule owns the surface a reader meets first: how much a function asks them to hold at once, whether everything they are reading runs, and whether a comment is prose or a corpse. It does not own duplication, abstraction structure or simplicity; `rules/kiss.md`, `rules/solid.md` and `rules/yagni.md` own those, and this rule cross-references rather than restates.

**Naming is not in this rule.** The naming defects that matter — a name that lies, a name that abbreviates past recognition, a name whose scope does not match its length — all need a reader with a dictionary and the domain in their head. A detector for them would have to guess, and a detector that is wrong about a common idiom teaches people to switch the gate off. `docs/clean-code.md` carries what a reviewer should ask instead.

None of the three conditions adds structure, so the abstraction trigger in `rules/yagni.md` does not gate any of them. Splitting a 30-statement function extracts something that was already inside it, and deleting a dead statement or a dead comment removes code outright.

## Conditions

Each of these is decided by `hooks/check-structure.py`.

1. **A function body holds at most 30 statements.** The count is every statement in the function's own body and in the bodies of the control-flow statements it contains. The docstring is not counted. A nested function or class counts as one statement and is measured on its own, exactly as in condition 1 of `rules/kiss.md`. The threshold sits in the empty span in the framework's own Python, where 61 functions reach 26 statements and then jump straight to 41; `docs/clean-code.md` carries the distribution and says why 30 rather than another number in the gap.

2. **No statement follows an unconditional exit in the same block.** The state is a statement that comes after a bare `return`, `raise`, `continue` or `break` at the same nesting level, with no branch between them. Such a statement cannot run, so it is either a leftover or a bug in the control flow, and both are resolved by deleting it or by moving the exit. This is a definition, not a threshold: there is nothing to tune.

3. **No comment is commented-out code.** The state is a comment whose text parses as a Python assignment, augmented assignment, `return`, `raise`, `import`, `del`, `assert`, `global`, `nonlocal`, or a bare call expression. Tool directives are excluded by prefix: `type:`, `noqa`, `pragma`, `pylint`, `mypy`, `ruff`, `fmt:`, `isort` and `#!`. Commented-out code is a branch that no longer exists in any history a reader can search, and version control already keeps the version that was deleted.

## Where this stops

**Condition 1 measures statements, not lines.** That is the point of it: lines are the formatter's output, so a line-counting threshold moves when somebody changes the line length or expands a call across four lines. It also means a single statement of arbitrary horizontal complexity passes, and a chained expression spanning a screen is exactly that case. Breadth in one statement is a reviewer's call, as it is for condition 1 of `rules/kiss.md`.

**Condition 1 does not reach a flat sequence.** A 30-statement function that assigns 30 unrelated fields in a row is at the limit and is fine; a 20-statement function with four interleaved concerns is under it and is not. The threshold catches the functions nobody can hold in their head, and it will never catch the ones that are merely badly arranged.

**Condition 1 does not reach data.** A dictionary or a table written out as consecutive assignments, a fixture builder, and a generated constant block all count statements without asking a reader to follow anything. Move them to module level where they read as data, or exclude the file by path when invoking the hook; what the condition is protecting against is control flow a reader has to simulate, and a table has none.

**Condition 2 does not reach code that is unreachable for a reason the parser cannot see.** A branch guarded by a constant that is always false, a call after a function that never returns, and a case a type makes impossible are all dead and none of them is a statement following a bare exit. Whole-program analysis finds those and a single-file parser does not.

**Condition 3 accepts a comment that explains code by quoting a line of it.** `# the caller does self.cache.clear() first` does not parse and passes; `# self.cache.clear()` does parse and fails, whatever the author meant. The cost is a backtick or a rewording, and the benefit is a detector with no judgment in it. It found nothing across 2,291 lines of the framework's own heavily commented Python, and six of six in a fixture built to trip it, which is what a condition should look like before it is worth a gate.

**Condition 3 does not reach a comment that should not exist for a different reason.** A comment restating what the next line does, a commented-out block that has become prose, and a stale comment describing behaviour that changed are all defects and none of them parses as code. Staleness in particular is the expensive one, and nothing mechanical detects it.

**This rule declares a hook rather than judgment, and the cost of that choice is named here.** All three conditions are decided by a parser, so the script stands in for the rule and the rule contributes no text to any request — which is the cheapest route and the reason to take it. What it drops is the material the rule cannot deliver at gate time: the naming question above, and the boundary cases in this section. Those live in `docs/clean-code.md`, which a reviewer reads and an agent loads when a finding needs arbitration. Where a rule in this plugin has conditions a script cannot decide, it declares `judgment` instead and says so; `rules/solid.md` is that case and explains the trade in its own final section.

**The detector parses Python and nothing else.** The standard library ships one parser and this plugin takes no dependencies. In any other language these three conditions are read by a reviewer, which is the weaker route and is stated here rather than left to be discovered.
