---
id: simplicity
type: doc
clade: engineering
subclade: quality
title: Simplicity and the abstraction trigger
summary: Why one predicate arbitrates between SOLID and YAGNI, why that arbitration is deliberately asymmetric, and where the thresholds in the KISS rule came from.
references:
  - rules/yagni.md
  - rules/kiss.md
  - rules/solid.md
---

# Simplicity and the abstraction trigger

This is the companion to [`rules/yagni.md`](../rules/yagni.md) and [`rules/kiss.md`](../rules/kiss.md), and it is where [`rules/solid.md`](../rules/solid.md) sends a reader who wants to know why half of its conditions are gated and half are not.

## Two rules pointing in opposite directions

SOLID asks for more structure. A responsibility gets its own type, a variation point gets polymorphism, a dependency gets a port. KISS and YAGNI ask for less. Fewer branches, fewer hops, nothing built for a requirement nobody has written down.

Both are correct, and both are correct about different code. The failure mode is not that one of them is wrong. It is that an agent loads whichever fires first, applies it to the end, and produces either a three-line function wrapped in four interfaces or a two-thousand-line class with a `mode` parameter. Reviewers then get contradictory feedback on consecutive pull requests from the same corpus.

An arbitration is what stops that, and it only works if there is exactly one of them.

## The trigger, and who owns it

> An abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam. An anticipated consumer is not a consumer.

That predicate is declared once, as condition 1 of `rules/yagni.md`. Every other artifact in this plugin cites it by name and none of them restates it.

**YAGNI owns it because YAGNI is the only one of the three whose entire subject is whether a thing should exist.** KISS bounds how complicated a thing may be once it exists. SOLID decides what shape it takes. Neither of them is about existence, so neither can host the predicate without acquiring a second subject.

There is a second reason, and it is structural. The trigger gates conditions that live in another rule, and in this framework authority runs one way: nothing may contradict a rule, and a doc has no standing to gate one. Putting the trigger in this document would mean a reference manual deciding when a rule's condition fires. It has to be a rule, and among the three it has to be YAGNI.

The cost of that choice is visible: `rules/solid.md` cannot put `rules/yagni.md` in its `references` list, because a rule may reference only a doc. It names it in prose instead. That is a real loss of machine-checkable linkage and it is the price of the authority hierarchy, not an oversight.

## Why the arbitration is asymmetric

The trigger does not apply evenly to SOLID, and saying so is the whole point of the design.

Sort SOLID's conditions by what satisfying them does to the code.

| Condition | What satisfying it does | Gated by the trigger |
|---|---|---|
| A type whose methods share no state serves two actors | splits one type into two that already existed inside it | no |
| A concrete member is declared and not implemented | deletes a member, or moves it to the base that owns it | no |
| A subtype narrows its parent's contract | removes the lie, by fixing the subtype or breaking the hierarchy | no |
| The third occurrence of the same discriminator chain | introduces polymorphism | yes |
| An interface's members partition by consumer | introduces a second interface | yes |
| A policy module imports a mechanism module | introduces a port | yes |

The first three cost nothing. A class that already partitions into two disjoint groups of methods becomes two classes with the same total surface. A member that raises rather than working is deleted or implemented, and either outcome is smaller than the lie. There is nothing for YAGNI to object to, because nothing speculative is being added. Gating them would mean tolerating a known defect until a second consumer shows up, which is an argument nobody would make out loud.

The last three add a type, a file or a level of indirection that was not there. Those are exactly the things YAGNI exists to stop, so those are the ones the trigger gates.

Two of the three gated conditions satisfy the trigger by construction, which is worth noticing before it looks like a loophole. The third occurrence of a discriminator chain **is** the second consumer, and then some; a member partition with two consumer groups **is** two consumers. Only dependency inversion can fire with a single consumer, and that is the one place the trigger does real work: with one adapter and no test that substitutes at the seam, the dependency is inverted by moving the code, not by adding an interface in front of it.

## What counts, and what people try to count

A **real consumer** is a call site that exists in the tree at the moment of review and binds a different implementation than the first one. Two call sites that reach the same concrete class are one consumer wearing two hats.

A **test that requires the seam** is a test that exists and fails without it. An in-memory repository standing in for a database in a test that runs today is a second consumer under route one and a required seam under route two; it qualifies on either reading, and that is deliberate, because test substitution is the most common legitimate reason for a port to exist before a second adapter does.

The following are not consumers, and each one has been argued for at least once:

- a backlog item, however well specified
- a comment reading "we will need this when we add the other provider"
- a roadmap entry, a design document, or a slide
- a second implementation that exists only as a subclass in the test file, constructed to satisfy this trigger
- the observation that the abstraction is cheap

The last one is the interesting one. The cost of an unjustified abstraction is not the cost of writing it. It is the cost of every future reader having to open two files to learn what one function does, and of every future change having to decide which side of the seam it belongs on. That cost is paid continuously and it does not appear in the diff.

## Where the KISS thresholds came from

Numbers in a rule are worth exactly what their provenance is worth. Both of the surviving ones are borrowed rather than chosen.

**Nesting depth above 3.** The Linux kernel coding style has held the same line since it was written: "if you need more than 3 levels of indentation, you're screwed anyway, and should fix your program." The rule measures control-flow nesting inside a function body rather than raw indentation, so a method's own `def` does not count against it and `elif` sits at the depth of the `if` it continues. Under that definition, 3 is the kernel's number applied without adjustment.

**A boolean parameter the function branches on.** Fowler's "Remove Flag Argument" in *Refactoring* is the source, and the argument is about the call site rather than the body: `render(doc, true)` tells the reader nothing and the only way to find out is to open the callee. The function is already two functions, and the flag is the seam between them written in the wrong place.

## The condition that measurement removed

`rules/kiss.md` was drafted with a third condition. A function that forwards every one of its parameters, in order and unchanged, to a callable of the same name adds no behaviour, no adaptation and not even a change of vocabulary, so it looked definitional: no threshold to tune and nothing for a detector to get wrong.

Run against real trees it flagged every collection wrapper and every single-hop facade. `def record(self, row): self.rows.append(row)` matches it exactly and is not a defect; it is encapsulation.

The mistake was in what the condition claimed to detect. Excess indirection is a *chain* of same-named hops, and distinguishing a chain from a facade needs the type of the attribute being delegated to. A single-file parser does not have that, so the detector was matching a shape that correlates with the defect instead of the defect. A gate that is wrong about a common idiom gets switched off, and then it is not enforcing the two conditions that were right either.

The condition was removed rather than tuned, which is the outcome worth recording: it is the same reasoning that keeps `rules/yagni.md` on the judgment route, and it is why the surviving conditions are worth believing.

## What the detectors cost, measured

The claim that these two conditions are low-noise is checkable, so it was checked. Run over the foundation plugin's two hook scripts, 1,231 lines of the framework's own Python, `hooks/check-structure.py` produces exactly one finding: `check_completeness` in `validate-artifacts.py` nests four deep, one level over the limit, and it does. Nothing fires for the flag-argument condition or for either SOLID condition.

Two further findings appear when the run is widened to include `foundation/skills/writing-hooks/references/`, both of them the deliberate `raise NotImplementedError` in a hook skeleton. That is the exclusion `rules/solid.md` names: a template is not an implementation, and it is skipped by path.

One true positive and zero false positives over 1,231 lines is what a detector should look like before its rule is worth loading.

## Where the LCOM4 threshold came from

It is not a threshold. LCOM4 is the number of connected components in a graph whose nodes are a class's methods and whose edges join two methods that touch a common instance attribute or call one another. Hitz and Montazeri defined it that way in *Measuring Coupling and Cohesion in Object-Oriented Systems* (1995), and the definition is what makes the number meaningful rather than any cutoff placed on it.

A value above 1 means the class literally partitions: there are two sets of methods with no shared state and no call between them, sitting in one type because somebody put them there. That is Robert Martin's later restatement of single responsibility, "a module should be responsible to one, and only one, actor" (*Clean Architecture*, 2017), made countable. Nothing was chosen. The only judgment in the detector is which members to exclude from the graph, and the rule states those exclusions rather than hiding them in the script.

## Where this stops

**This document does not rank the three rules.** The trigger arbitrates one specific collision, between a SOLID condition that wants to add structure and a YAGNI condition that wants it gone. It says nothing about a collision between KISS and SOLID, because there is no general one: a function that nests four deep is not made simpler by an interface, and splitting an incohesive class does not deepen anything.

**It does not cover DRY.** Duplication and abstraction are not the same question, the rule of three is a different predicate from this trigger, and collapsing them is how "extract the common part" becomes a justification for a base class nobody wanted. `rules/duplication.md` carries that predicate and `docs/duplication.md` argues it, including which of the three available definitions of a duplicate is worth a gate. The two predicates meet in one place and the meeting is settled there: the third copy is the second consumer, so a collapse that adds a parameter or a seam satisfies this trigger by construction.

**It does not reach language-specific structure.** Python module boundaries, import cycles, assembly layout in .NET and barrel files in TypeScript are all real versions of dependency inversion and all decided by facts about one toolchain. They belong in the language plugins, and `ahrena-engineering-python` is the first of them.

**Neither does it settle what a layer is.** Condition 6 of `rules/solid.md` needs a map of which modules are policy and which are mechanism, and this plugin does not supply one. Until a bounded-context layout artifact exists, a reviewer supplies the map and the condition is only as good as that map.
