---
id: pattern-selection
type: rule
clade: engineering
subclade: quality
title: Which pattern, and when
statement: A pattern ships only when the situation its catalog entry names is present in the tree and the cheaper alternative in that entry has been ruled out.
enforcement: judgment
references:
  - docs/patterns.md
  - docs/clean-code.md
---

# Which pattern, and when

Four conditions, each decided by a reviewer reading the diff against the entry in `docs/patterns.md`. The catalog is the input this rule needs and does not restate: every entry carries a situation, a shape, a cost, and a cheaper alternative, and all four conditions are phrased in terms of those four fields.

The rule exists because the usual failure with patterns is not ignorance of them. It is direction. A developer who knows the catalog reaches for a pattern and then looks for a place it fits, and the place is always findable, because every pattern is a plausible answer to a question somebody could ask. The correct direction is the other one: the situation is identified in the code that exists, and the catalog either names a pattern for it or names nothing.

Reversing the direction is also what makes the vocabulary worth having. A pattern name is a compression: saying "this is a decorator" saves a paragraph, and it only saves it if the reader can rely on the word meaning what it means. A codebase where the names are applied by resemblance costs more than one with no pattern names at all, because the reader has to check each one.

Condition 3 gates every entry that adds structure, using the abstraction trigger declared in condition 1 of `rules/yagni.md`. A rule may reference only a doc, so the trigger is named here in prose rather than linked. It reads: an abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam.

## Conditions

1. **A pattern is introduced only when the situation clause of its catalog entry holds in the tree.** Each entry in `docs/patterns.md` states its situation as a condition on code that exists, not on code that is planned. The state this condition forbids is a pattern whose situation is absent, anticipated, or true of a different part of the system. There is no threshold: the clause is either true of what is in the diff or it is not. Decided by a reviewer reading the entry against the change.

2. **Where the entry names a cheaper alternative, the alternative is the default.** Every entry carries one, because a pattern with no cheaper alternative is a pattern that never needed arbitrating. The pattern ships when the alternative was tried and did not hold, or was ruled out for a reason recorded in the change; a change that names neither has skipped the decision rather than made it. Decided by a reviewer, and the evidence is in the change rather than in anyone's memory.

3. **A pattern that introduces a type, a level of indirection or an extension point is gated by the abstraction trigger.** The catalog marks each entry as adding or removing structure, so the reader does not have to judge which. The entries that remove it — collapsing a discriminator chain that already occurs three times, replacing a repeated absence check — are not gated, for the reason `docs/simplicity.md` gives about the conditions in `rules/solid.md`. Decided by a reviewer applying the trigger.

4. **A type named for a pattern exhibits that pattern's shape, and a type exhibiting a pattern's shape is named for it.** The shape is the entry's shape line. Both directions are failures. A class called `OrderFactory` that validates and never constructs has spent a word the reader trusted; a class that assembles an object step by step and calls itself `OrderHelper` has withheld a name the reader already knew. Decided by a reviewer comparing the type against the entry.

## Where this stops

**Condition 1 does not forbid designing with patterns in mind.** Choosing a shape before writing the code is not speculative, and `rules/yagni.md` says the same thing about abstractions in its own boundary section. What the condition fires on is what is in the diff: a pattern present in the code with its situation absent from the code. A pattern that was considered, sketched and not built is invisible to it.

**Condition 1 does not reach a pattern the catalog does not carry.** `docs/patterns.md` holds twelve entries, chosen because each is the named fix for a condition in this plugin's other rules. Flyweight, visitor, memento, interpreter and most of the rest of the classical catalog are absent, and a developer applying one of them is outside this rule rather than in violation of it. The honest position is that the catalog covers the fixes this plugin prescribes and makes no claim to completeness; extending it is how a missing entry is fixed, not reading this condition as a ban.

**Condition 2 does not require the alternative to be built first.** Ruling it out on a stated reason is enough, and the reason can be short. What it refuses is the change that never mentions one, because that is the change where the alternative was not considered rather than rejected. The condition is about making the decision visible, at a cost of one sentence.

**Condition 2 stops paying when the cheaper alternative is already in the tree and failing.** A team that has lived with the lookup table for two years does not owe a paragraph explaining why they are replacing it; the history is the reason. The condition is aimed at the greenfield case, where nothing has been tried and the pattern arrives first.

**Condition 4 does not reach a name that is accurate and unfashionable.** `OrderStore` implementing the repository shape is a good name, and renaming it to `OrderRepository` to satisfy a vocabulary is churn. What the condition requires is that a pattern word, once used, be true — not that every pattern be announced in a suffix. The second direction is about a *missing* name only where the shape is unmistakable and the chosen name actively misleads.

**Condition 4 does not reach a framework's vocabulary.** A base class the framework calls a `Manager`, a `Service` or a `Provider` brings its own meaning, and renaming around it makes the code harder to place. The catalog's words apply to types this codebase names.

**The whole rule is downstream of a document, and that is its main weakness.** Every condition is decided against `docs/patterns.md`, so a gap in the catalog is a gap in the rule, and an entry whose situation clause is vague produces a condition nobody can apply. That is a real coupling and it is the cost of organising patterns by situation rather than by name: a catalog indexed by name would be inert and could not be wrong.

**This rule declares judgment rather than a hook, and the alternative was considered and refused.** The one condition that looks mechanical is condition 4, which could be read as a list of pattern suffixes matched against class names. `docs/clean-code.md` refuses exactly that detector for naming, on the grounds that a list like it is wrong in both directions — `TemplateManager` is accurate, and the worst names are plausible, specific and false, which no list catches. Adopting it here would contradict that position for no better reason than that patterns have a smaller vocabulary than domains do. The other three conditions need the catalog read against a diff, which needs a reader. So the rule takes the judgment route, and its statement is injected; `rules/solid.md` reaches the same conclusion by a different path and its final section sets out the trade.
