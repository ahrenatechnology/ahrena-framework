---
id: yagni
type: rule
clade: engineering
subclade: quality
title: The abstraction trigger
statement: An abstraction ships only with a second real consumer in the tree or a test that requires the seam; an anticipated consumer is not a consumer.
enforcement: judgment
references:
  - docs/simplicity.md
---

# The abstraction trigger

This rule owns the predicate that arbitrates between the conditions in `rules/solid.md` that add structure and the conditions here and in `rules/kiss.md` that take it away. It is declared once, in condition 1. Every other artifact in this plugin cites it and none restates it.

An abstraction, for the whole of this rule, is an interface, a protocol, an abstract base, a template method, an extension point, a plugin registry, a generic type parameter, or a configuration knob that selects behaviour.

## Conditions

Decided by a reviewer. Condition 1 is the trigger; the rest say how to count.

1. **An abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam. An anticipated consumer is not a consumer.** An abstraction that satisfies neither branch is deleted and its single implementation inlined at the one call site that used it.

2. A consumer is real when it exists in the tree at the moment of review and binds a different implementation than the first. Two call sites reaching the same concrete type are one consumer.

3. A test requires the seam when the test exists and fails without it. A test that could be written, or that is described in a comment, does not count. A fake, stub or in-memory double that runs today satisfies both branches at once, and that is the most common legitimate reason for a port to precede its second adapter.

4. A configuration knob with one value across the whole tree, and no written operational reason to vary it, is deleted together with the branch it feeds. The value it held becomes the behaviour.

5. Evidence lives in the tree, not around it. A backlog item, a roadmap entry, a design document, a comment reading "we will need this when", and a second implementation written in a test file for the purpose of satisfying this rule are each not a consumer.

## What the trigger does not gate

The trigger is asymmetric on purpose, and the asymmetry is the part that gets misread.

It gates the conditions that **add** structure: introducing polymorphism, splitting an interface, extracting a port. It does not gate the conditions that **remove** it. A type whose methods share no state, a subtype that narrows its parent's contract, and an interface member left unimplemented are defects whose fixes are smaller than the defect, so there is nothing for this rule to object to and nothing to wait for. `docs/simplicity.md` sets out the partition condition by condition.

Citing this rule to defer a removal is a misuse of it.

## Where this stops

**It does not forbid designing.** Choosing a shape before writing code is not speculative; shipping a seam for a consumer that does not exist is. The rule fires on what is in the diff, not on what was considered.

**It does not reach a requirement that has been accepted.** An extension point that a written, agreed requirement already demands has its second consumer on the schedule rather than in the tree, and the rule's second branch does not cover that case. Building it then is a scheduling decision, made once, by whoever owns the requirement. What the rule refuses is the same decision made silently by an author who thinks it is likely.

**It does not reach published API surface.** A library that other repositories consume has consumers the tree cannot see. The count runs over everything that imports the module, and when that set is not in the repository, the rule cannot decide it and a reviewer who knows the consumers must.

**It is not a hook, and the reason is not effort.** A script would count consumers by resolving imports, which misses every adapter bound through a dependency-injection container, a plugin entry point, a registry decorator or a settings string. Those look like zero consumers and are not. A detector that flags correct code often enough teaches people to skip the gate, which costs more than the rule it was enforcing. The condition needs a reader who can see the wiring, so the rule declares judgment and its statement is injected rather than replaced by a script that is wrong a third of the time.

**A candidate is not a verdict, and deletion is the default rather than the requirement.** Where the count is genuinely ambiguous, the rule's position is that the smaller code wins, because an abstraction that turns out to be needed is cheap to reintroduce from a working implementation, and one that turns out not to be is expensive to remove from a codebase that has grown around it.
