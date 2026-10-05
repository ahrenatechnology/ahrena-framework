---
id: solid
type: rule
clade: engineering
subclade: quality
title: SOLID as detectable conditions
statement: SOLID conditions that remove structure always apply; the ones that add it apply only when the abstraction trigger in rules/yagni.md is met.
enforcement: judgment
references:
  - docs/solid.md
  - docs/simplicity.md
---

# SOLID as detectable conditions

Six conditions, each a state with a threshold and a named detector. Conditions 1 to 3 remove structure and apply unconditionally. Conditions 4 to 6 add structure and fire only when the abstraction trigger in `rules/yagni.md` is satisfied; `docs/simplicity.md` explains why the split falls there.

A rule may reference only a doc, so the trigger is named here in prose rather than linked. It reads: an abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam.

## Conditions

1. **Single responsibility.** A class whose LCOM4 exceeds 1 is a split candidate. LCOM4 is the number of connected components in the graph whose nodes are the class's methods and whose edges join two methods that touch a common instance attribute or call one another. Dunder methods and static methods are excluded from the graph; protocols, abstract bases and enums are skipped. Decided by `hooks/check-structure.py` for Python, and by a reviewer computing the same partition in any other language. Not gated.

2. **Liskov substitution, and interface segregation, at once.** A concrete member that is declared and not implemented is a failure of both. In Python the state is a member whose body, after any docstring, is a single `raise NotImplementedError` and that carries no `abstractmethod` decorator; in C# a `throw new NotImplementedException()` in a non-abstract member; in TypeScript a method that throws in place of returning its declared type. The fix is to implement the member or to remove it from the interface that forced it, and both are smaller than the defect. Decided by `hooks/check-structure.py` for Python, by a reviewer elsewhere. Not gated.

3. **Liskov substitution, the part no signature shows.** A subtype that rejects an input its supertype accepts, or returns less than its supertype promises, narrows the contract. The detector is the supertype's own test suite executed against an instance of the subtype: a test the parent passes and the child fails is the violation. Decided by that test run. Not gated.

4. **Open/closed.** The third occurrence of the same discriminator chain introduces polymorphism. Two chains are the same when the discriminating expression is the same and the branch set matches. Decided by a reviewer counting occurrences across the tree. Gated, and satisfied by construction: the third occurrence is itself the second consumer.

5. **Interface segregation.** An interface is split when its members partition into two or more groups such that no consumer calls members from more than one group. Decided by a reviewer partitioning the call sites. Gated, and satisfied by construction when each group has a consumer that exists today.

6. **Dependency inversion.** A module on the policy side of the layer map may not import a module on the mechanism side. The map is an input a reviewer supplies; this plugin ships none. Gated, and this is the one condition the trigger genuinely constrains: with a single adapter and no test substituting at the seam, invert the dependency by moving the code rather than by adding a port in front of it.

## Where this stops

**Condition 1 flags a candidate, not a defect.** A value type or a namespace class with a broad convenience surface scores above 1 legitimately, because its methods share an attribute only incidentally and splitting it produces two types nobody imports separately. The reviewer decides; the script reports.

**Condition 1 has a false-negative problem it cannot fix.** LCOM4 sees shared state, not shared meaning, so two unrelated responsibilities that happen to read the same field score as one component. Closing that gap requires understanding what the field means, which no metric does.

**Condition 2 does not reach a documented capability check.** A member that is genuinely optional at a boundary may be modelled as a capability flag the caller tests before calling. What the condition forbids is the silent form, where the member exists, appears callable and raises.

**Condition 2 does not reach a skeleton that is meant to be filled in.** A template whose members are deliberately unimplemented matches the state exactly, and the state is correct there. Exclude template and scaffold directories by path when invoking the script; `foundation/skills/writing-hooks/references/` is the case that forced this sentence.

**Conditions 1 and 2 fire together, by construction.** A member that only raises touches no state, so it is always its own LCOM4 component as well. Both findings are reported because the fixes differ: implementing the member usually collapses the partition, and deleting it always does.

**Condition 4 does not reach a discriminator you do not own.** Branching on an external message format, a third-party error code or a protocol's enum puts the branch set under someone else's control, and a hierarchy only spreads their next change across more files. A visible conditional over a foreign vocabulary is correct. Nor does it reach a chain whose branches each return a constant: that is a lookup table, and three classes is the wrong answer to it.

**Condition 5 does not reach a published boundary.** Splitting an interface that other repositories implement is a breaking change to all of them, and cohesion inside one codebase does not pay for a coordinated release across five.

**Condition 6 does not reach the composition root**, which must know every concrete type, nor stable mechanisms such as the standard library's own date, collection and serialization types, where the probability of substitution is near zero and a port buys nothing.

**Four of the six conditions have no script, and that is why this rule declares judgment rather than a hook.** Conditions 3, 4, 5 and 6 need a test run, a count across the tree, or a layer map, and `enforcement` decides how a rule reaches an agent: a hook rule is replaced by its script and contributes no text, a judgment rule contributes its statement. Declaring a hook here would deliver the two conditions a script can decide and silently drop the four that carry the arbitration. The script still exists and conditions 1 and 2 name it, so a reviewer and a pipeline can both run it; what it does not do is stand in for the rule.

**The script parses Python and nothing else.** The Python standard library ships one parser, this plugin takes no dependencies, and a regular expression over source is a detector that stops matching when somebody reformats. Detectors for TypeScript and C# belong with plugins that may take a parser dependency.
