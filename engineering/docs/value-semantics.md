---
id: value-semantics
type: doc
clade: engineering
subclade: quality
title: When a parameter list becomes a value
summary: Why the parameter cap and the immutability conditions are one rule, where the 4 and the rule of three came from, and the cases where making a value costs more than passing the arguments.
references:
  - rules/value-semantics.md
  - docs/simplicity.md
---

# When a parameter list becomes a value

This is the companion to [`rules/value-semantics.md`](../rules/value-semantics.md). The rule states five conditions and names what decides each one; this explains what they are protecting, where the two numbers came from, and why a rule about parameter counts and a rule about immutability are the same rule.

## Why these are one rule and not two

The obvious reading is that there are two subjects here: how many arguments a function may take, and how a value type must behave. They were written as two rules and merged, and the merge is the useful part of the design.

A parameter list that crosses the threshold is told to become an object. The question nobody asks next is *what kind of object*. Left alone, the answer is almost always a mutable bag: a class with five public attributes, assigned by the caller in four places, read by the callee, and handed onward. That object is worse than the parameter list it replaced. The parameter list at least made the dependency visible at every call site; the bag hides it, and adds the possibility that somebody mutates the thing mid-flight and the callee sees a different value than the caller sent.

So the conditions that create objects and the conditions that constrain them have to arrive together. Split across two rules, the first is the one that gets adopted and the second is the one that gets read later, which produces precisely the bag. One rule, and the fix the first condition asks for is defined by the conditions below it.

## The parameter cap

**What it prevents.** The call site nobody can read and the signature nobody can extend. Past a handful of positional arguments a reader has to count commas against the definition, and the compiler stops helping the moment two adjacent parameters share a type: swapping `host` and `region` type-checks and fails in production.

There is a second cost that is easier to miss. A long parameter list is a coupling report. It says the callee needs this many separate things from its caller, and every one of them is a decision the caller has to be in a position to make. A function taking seven arguments cannot be called from anywhere that does not already know all seven, which is usually one place, which is why it has seven arguments.

**Where the 4 came from.** It was measured against the same corpus that produced the size threshold in `docs/clean-code.md` — 61 callables across 2,291 lines of the framework's own Python.

| | Parameters |
|---|---|
| median | 1 |
| 90th percentile | 3 |
| 95th percentile | 4 |
| maximum | 4 |

The maximum in the corpus is 4, reached by five callables, and every one of them is a tuple-shaped constructor: `case(name, files, expect, ok)` in the two test suites, `problems_for(expect, ok, code, output)`, `_check_name_shape(a, value, findings, label)`. The distribution has no tail at all.

That is an unusual and convenient shape. A cap at 4 fails nothing in the corpus and the next value up has never been reached, so the threshold cannot be hit by a function drifting — only by one that takes a genuine step. `rules/progressive-disclosure.md` placed its 10-line cap the same way, and `docs/clean-code.md` places the statement threshold the same way.

The cross-check is Martin's *Clean Code*, which puts the ceiling at three and calls more than three a case requiring "very special justification". The rule takes 4 rather than 3 for a reason worth stating: 3 is the corpus's own 90th percentile, and a threshold at the 90th percentile of good practice fires on ordinary code. The measured ceiling is the honest number here, and it is one above the book rather than one below it.

**Why the variadics do not count.** `*args` and `**kwargs` are one name each at the call site. There is no clump in them to gather and no reader counting commas against a definition, because the definition does not enumerate anything. A function with four named parameters and a `**kwargs` passes, and whether the `**kwargs` is itself a defect is a different question about typed interfaces.

**Where it stops paying.** On a value type's own field count, which the condition deliberately never sees, because a frozen dataclass generates its `__init__` rather than declaring one. That is the exemption that makes the rule coherent: the fix for a long parameter list is a value, so the value cannot then be penalised for holding the fields the parameters held. What the eight-field value still owes is a reason those eight things belong together, and that question is cohesion, answered by condition 1 of `rules/solid.md`.

It also stops at the boundary of the codebase. A function implementing a signature someone else defined — a callback, a framework hook, a C API binding — takes the parameters it is handed, and gathering them into an object on the way in adds a hop without removing a coupling.

## The data clump

**What it prevents.** The change that has to be made in six signatures. Once `(host, port, timeout)` travels together through four functions, adding a fifth field to the connection means touching all four and every one of their callers, and the compiler only finds the ones it can see.

**The detector.** The third callable in a module passing the same contiguous run of three or more parameter names. Only the longest run shared by a given set of callables is reported, so a shared four-name run produces one finding rather than the three sub-runs inside it.

**Where the numbers came from, and why there are two of them.** Three names is Fowler's Data Clumps: the smell is defined as three or more values that appear together in several places, and below three there is nothing to gather that a pair of arguments does not express as well.

Three *occurrences* is the rule of three, and that number is not chosen here — it is inherited. Condition 4 of `rules/solid.md` uses the third occurrence of a discriminator chain, `docs/solid.md` traces that to Fowler's *Refactoring*, and `docs/simplicity.md` records the position that an arbitration mechanism coming in two incompatible versions is not an arbitration mechanism. Picking two occurrences here would have been defensible in isolation and incoherent in context.

The two numbers also do different jobs, which is why both are needed. Three names is what makes the group a thing worth naming. Three occurrences is what makes it worth the type.

**Measured.** Run against the framework's own Python as it stood before this rule landed, the condition produced exactly one finding across 2,291 lines: `(tree, rel, findings)`, passed by `check_cohesion`, `check_unimplemented`, `check_nesting` and `check_flag_argument` in `hooks/check-structure.py`.

It was a true positive, and it is now fixed. The four checks take a `Source` — the display path, the file text and the parsed tree — and the fix paid for itself immediately: the comment scan that conditions 3 of `rules/clean-code.md` needed requires the file text, which the three-name run did not carry. Under the old signature adding it would have made a four-name run across seven callables. The object absorbed it without changing a single call site.

That is the argument for the condition in one example, and it is recorded here rather than claimed in the abstract.

**Where it stops paying.** On a uniform interface. Three handlers registered in the same dispatch table share a signature because the table demands it; the run is the contract. The test is whether the callables are invoked through the table or called directly — `CHECKS` in this plugin's own hook is the borderline case, and it fell on the clump side because every check is also called directly from the tests.

It also stops when the run is shared by accident. Three functions each taking `(name, path, index)` for three unrelated reasons have a coincidence, not a concept, and forcing a type on them names something that does not exist. The reviewer's question is whether the three values have a name; if they do not, there is no parameter object, only a tuple with a class around it.

## Value semantics

**What the three conditions prevent, together.** The object that claims to be a value and is not, which fails in three specific places.

A frozen dataclass holding a list fails in a set. It is hashable, because the dataclass generated `__hash__` from the fields, and the hash is computed from a list whose contents can change afterwards — so the object is placed in one bucket and later looks for itself in another. This is the condition worth having even if the other two were dropped, because the failure is silent, delayed, and presents as data loss rather than as an error.

A frozen type that writes through `object.__setattr__` fails the reader. Every caller has been told the type cannot change and one method changes it, so every piece of reasoning downstream that depended on the declaration is wrong. Python offers no way to stop this — `frozen=True` raises on normal assignment and the escape hatch is one function call away — which is exactly why it needs a detector rather than a type system.

A class that defines `__eq__` and no `__hash__` fails at the first set or dict. Python sets `__hash__` to `None` when it sees a hand-written `__eq__`, because a type that redefines equality and keeps identity hashing is broken in a subtler way, and the language chooses the loud failure. The loud failure still arrives far from the class, in someone else's code, with a message about the type rather than about the omission.

**Why `__post_init__` is excluded and nothing else is.** Normalising a field during construction — stripping a string, sorting a tuple, deriving one field from another — has to happen after the generated `__init__` has assigned the fields, and `object.__setattr__` in `__post_init__` is the documented way to do it. The object has not been handed to anyone yet, so nothing observes a change. Every other method has.

**Why `__hash__ = None` satisfies condition 5.** The condition is not that every type is hashable. It is that the author says which kind of type this is. An entity has identity; two customers with the same name are two customers; `__hash__ = None` is the right answer and it is one line. What the condition refuses is the version where nobody decided, which is indistinguishable from the entity case in the source and distinguishable from it at runtime.

**Where they stop paying.** Depth. A frozen type holding a tuple of mutable records is as leaky as one holding a list, and the annotation says `tuple`, so condition 3 passes it. Following mutability through types across modules is a whole-program question; the shallow case is the one a single file can decide and the one that occurs most.

And caching. A memoised property on a value object is a real pattern and it genuinely violates conditions 3 and 4. The condition is right that the type is no longer immutable and the author may still be right that the cache belongs there. What the rule asks is that the decision be visible, which in practice means holding the cache outside the value or excluding the file by path and writing down why.

## Where this stops

**This document does not settle what a value object is in DDD terms.** The entity-versus-value distinction, aggregate boundaries and identity are a domain-modelling subject with its own vocabulary, and no artifact in this plugin covers it yet. What is here is the mechanical half: given that a type is meant to behave as a value, these are the ways it fails to.

**It does not cover serialisation.** A value that must round-trip through JSON, a database row or a message payload acquires constraints these conditions say nothing about, and the usual collision is that the immutable in-memory form and the wire form want different field types. That is a contract question rather than a value question.

**It carries no worked examples outside Python.** The conditions are stated in language-neutral terms, and the three immutability conditions are the most language-shaped material in this plugin: a language with enforced value types decides them at compile time and does not need the rule at all. The one shipped detector parses Python because the Python standard library contains a Python parser and nothing else.

**It says nothing about cost.** Replacing a list field with a tuple copies on every change, and a value object allocated per call in a hot loop is a real expense. Every condition here trades allocation for safety, and a measurement beats the condition; `docs/solid.md` takes the same position for the same reason.
