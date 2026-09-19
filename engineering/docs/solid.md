---
id: solid
type: doc
clade: engineering
subclade: quality
title: The five principles and what they cost
summary: What each SOLID principle prevents, the detector behind each condition in the SOLID rule, and the situation in which applying that principle makes the code worse.
references:
  - rules/solid.md
  - docs/simplicity.md
---

# The five principles and what they cost

This is the companion to [`rules/solid.md`](../rules/solid.md). The rule states six conditions and names what decides each one; this explains what those conditions are protecting, where their numbers come from, and the case in which satisfying one is the wrong move. [`docs/simplicity.md`](./simplicity.md) covers the separate question of when a condition is allowed to add structure at all.

SOLID is usually taught as five sentences. Five sentences is what makes it useless in review: every one of them is agreeable, none of them is decidable, and two reviewers reach opposite conclusions about the same class without either being able to say why. What follows is the same five principles reduced to states a reader or a script can detect.

## Single responsibility

**What it prevents.** The class that everyone edits. When the billing team, the reporting team and the export team all have a reason to change `Order`, every one of their changes risks the others, and the merge queue serializes three teams behind one file.

"One reason to change" is not detectable, which is why Martin restated it in *Clean Architecture* as one **actor**: the module answers to one group of people. That is closer, and it is still not countable.

**The detector.** LCOM4, the number of connected components in the graph whose nodes are a class's methods and whose edges join methods that share an instance attribute or call one another. A value above 1 says the class already contains two independent objects; the split is not a proposal, it is a description of what is there. `docs/simplicity.md` carries the definition and its source.

The exclusions matter more than the number. The graph leaves out dunder methods and static methods, because `__init__` touches every attribute and therefore connects every component, and a static method touches none and therefore forms a component of its own. Both would make the metric say something about the language rather than the design. Protocols, abstract bases and enums are skipped whole, since an interface with no state has one component per method by construction.

**Where it stops paying.** A class deliberately built as a namespace for related-but-independent operations will score above 1 and should. `Path`, `datetime` and most value types with a broad convenience surface are in that category: the methods share the same one or two attributes only incidentally, and splitting them produces two types nobody wants to import separately. The rule's boundary section names this case; the honest position is that LCOM4 flags a candidate, and a candidate is not a verdict.

The other limit is that LCOM4 sees state, not meaning. Two responsibilities that happen to read the same field score as one component. The metric has no false-positive problem and a real false-negative one, and a reviewer is what closes it.

## Open/closed

**What it prevents.** The switch statement that grows a case per feature, in six places, one of which is always missed.

**The detector.** The third occurrence of the same discriminator chain. Two chains are the same when the discriminating expression is the same and the branch set matches. At the first occurrence there is a conditional; at the second there is a coincidence; at the third there is a type hierarchy that has not been written down yet.

Three is Fowler's rule of three from *Refactoring*, and it is the same shape this framework already uses for duplication. Reusing it rather than inventing a second number is deliberate: an arbitration mechanism that comes in two incompatible versions is not an arbitration mechanism.

**What the extension point costs, so the count is honest.** Polymorphism moves the decision from one visible place to the call site's dispatch table. That is a win when the branch set is stable and a loss when it is not: adding a case to a `match` is a one-line diff a reviewer can see, while adding a case to a hierarchy is a new file, a registration and a lookup nobody reads. Two occurrences genuinely are better as two conditionals.

**Where it stops paying.** When the discriminator is not yours. Parsing an external message format, mapping an error code from a third-party library, or branching on an enum that a protocol defines are all cases where the branch set changes only when someone else changes it, and a hierarchy just moves that change into more files. A visible conditional over a foreign vocabulary is the correct shape.

It also stops when the chain is a translation table rather than behaviour. Three branches that each return a different constant are a dictionary, not a polymorphism candidate, and turning them into three classes is the over-abstraction this document exists to prevent.

## Liskov substitution

**What it prevents.** The subtype that passes the type checker and fails at runtime, in the caller, with an error the caller cannot act on.

**Two detectors, because the violations come in two kinds.**

The first kind is visible in the type itself: a member declared and not implemented. In Python that is a body consisting of `raise NotImplementedError`; in C# a `throw new NotImplementedException()`; in TypeScript a method that throws rather than returning its declared type. The supertype promises the member, the subtype refuses it, and every caller holding the supertype is now wrong. This is decidable without running anything, and `hooks/check-structure.py` decides it for Python.

The second kind needs execution: a subtype that rejects an input its parent accepts, or returns less than its parent promises. No signature shows it. The detector is the parent's own test suite run against an instance of the subtype, and the failure is a test the parent passes and the child does not. That is why the rule names a test suite rather than a script.

**Why the unimplemented member is also a segregation failure.** It is one defect that two principles describe. Liskov says the subtype broke the contract; interface segregation says the interface asked for something an implementation cannot supply. They disagree only about the fix: implement the member, or move it out of the interface that forced it. Both fixes remove code, which is why neither is gated by the abstraction trigger.

**Where it stops paying.** At the boundary of a language's type system. A Python `Protocol` member that a particular adapter genuinely cannot support is sometimes best expressed as a narrower protocol the adapter satisfies and a wider one it does not, and sometimes that split costs more than a documented capability flag the caller checks. The rule does not forbid the flag. It forbids the silent version, where the member exists, appears callable and raises.

The condition also does not reach a subtype that *widens* the contract, accepting more or promising more than its parent. That is legal substitution and usually a good sign.

## Interface segregation

**What it prevents.** The implementation that exists to satisfy an interface rather than a caller. Every `raise NotImplementedError` in a concrete adapter is an interface that asked for too much.

**The detector.** Partition the interface's members by consumer: for each member, the set of call sites that use it. If the members fall into two or more groups and no consumer calls across groups, there are two interfaces here and one name.

**The threshold, stated plainly.** Two groups. Not "the interface is large", not "it feels like a god interface". A ten-member interface whose consumers all call all ten members is correctly sized, and a three-member interface with two disjoint consumer groups is not.

**Where it stops paying.** When the groups are disjoint today by accident. One consumer per group and no test substituting at either seam means the partition is an observation about the current call sites, not about the domain, and the split will be undone the next time a caller needs both halves. This is a gated condition for exactly that reason, and `docs/simplicity.md` works through how the trigger applies to it.

It also stops when the interface is a published boundary. Splitting an interface that other repositories implement is a breaking change to every one of them, and a cohesion gain inside one codebase does not pay for a coordinated release across five.

## Dependency inversion

**What it prevents.** The domain that cannot be tested, deployed or reasoned about without a database, because it imports one.

**The detector.** A module on the policy side of the layer map importing a module on the mechanism side. The map is the input the condition needs and this plugin does not ship one, so a reviewer supplies it; the rule says so rather than pretending the condition is self-contained.

**The part that is usually skipped.** Inverting a dependency has two implementations, and only one of them adds code. The first is to extract a port: define the interface in the policy layer, implement it in the adapter layer, wire them at the composition root. The second is to move the code, so that the thing the policy needed is no longer in the adapter at all. The second is almost always smaller and it is almost never the one that gets proposed.

This is the single place in the rule where the abstraction trigger does real work rather than being satisfied by construction. With one adapter and no test that substitutes at the seam, a port is an interface with one implementation, which is the exact shape `rules/yagni.md` deletes. Move the code instead, and extract the port when the second adapter or the test arrives.

**Where it stops paying.** At the composition root, which must know every concrete type and is allowed to. A ports-and-adapters layout with no place where the wiring happens has not inverted its dependencies, it has hidden them in a container configuration that no type checker reads.

It also stops at stable mechanisms. The standard library's `datetime`, a language's own collections and a serialization format that has not changed in a decade are not dependencies worth a port. The value of inversion is proportional to how likely the mechanism is to change or to need substituting in a test, and for most of the standard library both are near zero.

## Where this stops

**This document does not teach the principles from scratch.** It assumes the reader knows roughly what each one claims and needs to know what this framework will hold them to. Martin's *Clean Architecture* and *Agile Software Development, Principles, Patterns, and Practices* are the primary sources and neither is reproduced here.

**It carries no worked examples in TypeScript or C#.** The conditions are stated in language-neutral terms and the one shipped detector parses Python, because the Python standard library contains a Python parser and nothing else. Worked examples in the other two languages, and detectors for them, belong with the plugins that may take a parser dependency.

**It does not cover the patterns that satisfy these conditions.** Strategy, adapter, template method and the rest are the vocabulary for the fixes, not for the conditions, and a pattern catalog is a separate artifact that does not exist yet.

**It says nothing about performance.** Every condition here trades indirection for changeability, and there are systems where an extra virtual call in a hot loop is the thing that matters. That trade is real, it is measured rather than argued, and a measurement beats every condition in the rule.
