---
id: kiss
type: rule
clade: engineering
subclade: quality
title: Complexity a script can see
statement: A function nests control flow at most 3 deep and branches on no boolean parameter.
enforcement: hook
enforced-by: hooks/check-structure.py
references:
  - docs/simplicity.md
---

# Complexity a script can see

Two conditions, both decided by `hooks/check-structure.py`. Each is a shape in the source rather than an opinion about it, which is what lets this rule cost nothing to load and still fire. `docs/simplicity.md` gives the provenance of both, and the cases where the fix is worse than the finding.

"Keep it simple" is not in this rule, because it cannot be checked and a maxim sitting among conditions teaches readers that the conditions are optional too. Simplicity that needs a reader is guidance, and guidance is in the doc.

## Conditions

Each of these is decided by `hooks/check-structure.py`.

1. **Control flow nests at most 3 deep inside a function body.** Depth counts `if`, `for`, `while`, `with`, `try` and `match` statements enclosing one another, and the body of an `except` handler counts as one level. A function or class defined inside another is measured on its own and does not inherit its enclosure's depth. An `elif` sits at the depth of the `if` it continues rather than one below it. The threshold is the Linux kernel coding style's, unadjusted.

2. **A function does not branch on a boolean parameter.** The state is a parameter annotated `bool` or defaulted to a boolean literal, whose bare value is the test of an `if` in that function's own body. Such a function is already two functions, and the call site reads `render(doc, True)`, which tells a reader nothing. Split it into two named functions, or take the behaviour rather than the flag that selects it.

## Where this stops

**Neither condition reaches indirection, and that is a deliberate retreat.** The first draft of this rule carried a third condition against a function that forwards every parameter, unchanged, to a callable of the same name. Run against real trees it flagged every collection wrapper and every one-hop facade, which are not defects. The defect is a *chain* of same-named hops, and telling a chain from a facade needs the type of the attribute being delegated to, which a single-file parser does not have. A detector that is wrong about a common idiom teaches people to switch the gate off, so the condition was dropped rather than tuned. Indirection depth is a reviewer's call until something can resolve types across files.

**Condition 1 does not reach a flat sequence of branches.** A function with twenty `elif` arms at depth 1 passes and often should not. Depth is what a parser decides exactly; breadth needs a reader, and condition 4 of `rules/solid.md` covers the case where the breadth is a discriminator chain.

**Condition 1 does not reach generated or transcribed code.** A parser table, a state machine emitted by a generator and a numerical kernel transcribed from a published algorithm all nest to mirror a structure that exists outside the codebase, and flattening them breaks the correspondence a reader needs in order to check them against the source. Exclude those files by path when invoking the hook.

**Condition 2 does not reach a boolean the function stores rather than branches on.** A constructor parameter recorded as state and tested later is a configuration value, and condition 4 of `rules/yagni.md` covers the case where it only ever holds one. Nor does it reach a boolean the function passes through to something else, which is a signature problem one level down.

**Neither condition says the code is good.** A function at depth 3 with no flag arguments can still be the wrong function in the wrong module. The hook decides shape; everything about fit is judgment, and this rule does not pretend otherwise.

**The detector parses Python and nothing else.** The standard library ships one parser and this plugin takes no dependencies. In any other language these two conditions are read by a reviewer, which is the weaker route and is stated here rather than left to be discovered.
