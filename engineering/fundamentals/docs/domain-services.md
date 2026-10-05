---
id: domain-services
type: doc
clade: engineering
subclade: architecture
title: The residue a boundary leaves, and the two patterns that got no rule
summary: What behaviour belongs to no aggregate and where it goes, why statelessness is the condition that bites, and the measurements over 288,485 lines that refused a detector for each of specification, factory and domain service.
references:
  - rules/domain-services.md
  - docs/aggregates.md
  - docs/bounded-contexts.md
  - docs/duplication.md
  - docs/patterns.md
---

# The residue a boundary leaves, and the two patterns that got no rule

This is the companion to [`rules/domain-services.md`](../rules/domain-services.md). The rule states four conditions and says a reviewer decides all four; this explains what each one protects, and carries the measurements that made the rule a judgment rule instead of a hook.

It also carries the work on two patterns that arrived with it and did not become rules. [`docs/aggregates.md`](./aggregates.md) closes by saying that specification, factory and domain service have no artifact, and that the absence means this plugin has nothing useful to say about them yet. One of the three now has a rule, two have catalog entries in [`docs/patterns.md`](./patterns.md), and the difference between those outcomes was decided by running candidate detectors over a corpus rather than by argument.

## What the residue is

An aggregate boundary is drawn by the invariants, which is condition 1 of [`rules/aggregates.md`](../rules/aggregates.md) and Evans' definition. Draw it that way and some behaviour is left over: a rule the business states in one sentence whose terms name two roots. Transferring funds between two accounts, deciding whether a shipment may be released against an order and a credit limit, pricing an order against a customer's contract — each is one rule, and neither of the two roots owns it.

The rule exists because both defaults for that residue are bad, and they are bad in opposite directions.

**Pushed into one root**, the behaviour makes that root know about the other. If it holds a field, condition 3 of `rules/aggregates.md` fails it. If it takes the other as a parameter, nothing fails it and the coupling is the same — worse, in one respect, because the type declaration no longer shows it and a reader learns the dependency only by reading the method. That is the state condition 1 of the rule names.

**Pushed into the application layer**, the behaviour survives but stops being a model of anything. It is now a step inside a use case. A reader who opens `domain/` to learn what the business believes will not find it. The next use case that needs the same rule will not find it either, and will write it again — which is the duplication [`docs/duplication.md`](./duplication.md) describes as the expensive kind, the one with no shape in common and no detector.

So the residue gets a name and a home, and the rule's conditions 1 and 3 are the two halves of saying so.

## Why statelessness is the condition that bites

Conditions 1, 3 and 4 are about placement. Condition 2 is about the object itself, and it is the one that catches a service after it has been placed correctly and then rotted.

A service accumulates state in a predictable way. Someone needs a value computed in step one during step three, and a field is the shortest route. The object still passes every other condition — it is under `domain/`, it names two aggregates, it decides something real — and it is now an aggregate with no identity and no boundary, shared by every caller. Under concurrency it is a defect that reproduces once a week and never in a test.

Evans states the requirement plainly: a service is defined by what it can do rather than by what it is, and the state it operates on is handed to it and handed back. This rule takes that unchanged. The carve-out in the rule's boundary section — a memo, a lazily built table — is the case where the field cannot change what the next call answers, which is the whole content of the condition.

The collaborators supplied at construction are deliberately not state here. A service holding a port it was wired with is the ordinary shape, the value is fixed for the object's life, and forbidding it would leave only free functions, which is a different rule about a different thing.

## The line between a domain service and a use case

Condition 4 is the one that draws it, and the line is thin enough to state honestly.

A use case sequences: it loads through ports, calls a model, saves, and reports. A domain service decides: given what it was handed, it produces an answer the business would recognise, and it would produce the same answer if the ports were different. The test in the rule — whether the operation would still have to exist if every delivery mechanism were replaced — is the one that separates them in practice.

What makes the line thin is that almost every real use case contains one small decision, and almost every real domain service is called from exactly one use case. So the condition is written to fire on the type whose *every* operation is a sequence, rather than on any type that sequences at all. A type under `domain/` that loads, calls one aggregate and saves has taken a domain name for application work, and it will collect the next three orchestrations too, because the name does not refuse them.

This is the one condition in the rule inherited from the predecessor framework rather than from Evans or from a measurement. Its DDD reference carries a table of tactical patterns with an "avoid when" column, and the Domain Service row reads "it is only IO orchestration". That table is otherwise the whole of what the predecessor had to say about these three patterns — no conditions, no detector, no thresholds — and that line is the part worth carrying.

## What the detectors measured

Every candidate below was run over the **CPython 3.11 standard library, 564 files and 288,485 lines, excluding its own test trees and `lib2to3`**. That is the same corpus and the same file set [`docs/duplication.md`](./duplication.md) placed its two floors against, chosen for the same reason: it is large, old, written by many hands and well reviewed, so it is a good place to find out whether a detector fires on correct code.

It is a poor place to find out whether a detector fires on the defect, and that limit is the important one here. CPython contains no aggregates, no repositories and no `domain/` directory, so none of these detectors can be scored for recall against it. What the corpus answers is precision: of what the detector reports, how much is code a maintainer would change. [`docs/bounded-contexts.md`](./bounded-contexts.md) records the same limit for the two detectors `rules/domain-model.md` does ship.

### The factory detector, and why nine findings killed it

The defect is an aggregate assembled field by field at a call site, so that between the first assignment and the last it exists in a state its own invariant forbids. The shape is a local bound to a constructor call followed by attribute writes to that same local.

| Attribute writes following the call | Sites | Of those, outside the type's own module |
|---|---|---|
| 2 or more | 33 | 9 |
| **3 or more** | **9** | **0** |
| 4 or more | 4 | 0 |

Nine sites in 288,485 lines is a quiet detector, and quiet is what a floor of three buys. All nine are wrong, and they are wrong in the same way:

| Site | What it is |
|---|---|
| `importlib/_bootstrap.py:486` | `_spec_from_module`, a factory function building a `ModuleSpec` |
| `importlib/metadata/__init__.py:651` | `make_file`, a nested factory building a `PackagePath` |
| `unittest/loader.py:483` | `_makeLoader`, a factory function building a `TestLoader` |
| `unittest/mock.py:2212` | a test double being assembled |
| `xml/dom/minidom.py:1337` and `:1943` | two clone operations — a copy constructor written out |
| `xml/dom/xmlbuilder.py:217` | `resolveEntity`, a factory method building a `DOMInputSource` |
| `zipfile.py:1435` | the central-directory parser, deserialising a `ZipInfo` |
| `zipfile.py:1881` | `ZipFile.mkdir`, building a directory entry |

Every one is a factory, a clone or a deserialiser — code whose entire job is field-by-field assembly, which is the code the pattern says should exist. **The detector cannot tell a call site from the factory itself**, and that is not a tuning problem, because the two are the same statements in the same order. Nine out of nine, at the floor that makes it quiet.

Narrowing was the obvious repair and it was tried: require that the constructed type be declared in a different module, so that the factory, which almost always lives beside its type, drops out. At three writes that leaves **zero findings in 288,485 lines**. The narrowed detector is silent on the whole corpus, which is the other failure the rule was written to avoid — a condition that fires on nothing looks like a condition being satisfied.

So the shape correlates with the defect only when the constructed type has an invariant, and whether a type has one is not in the source. Telling that apart needs the aggregate-root marker, which is where `rules/aggregates.md` ended and why it declares judgment. A factory rule would have inherited that, and then would have had nothing left that condition 1 of `rules/aggregates.md` does not already say: an invariant enforced outside the boundary that owns it is exactly what that condition's boundary section calls the more common defect and the one it is aimed at.

### The specification detector, and the two ways it fails

The defect is one selection rule written twice — once where the storage answers it, once where memory does. The two copies are written in two different languages of expression, and that is the whole difficulty.

Taking the narrowest reading the corpus can score — a predicate that already has a name, being the sole `return` of a function, whose expression is also written out inline somewhere else — gives:

| Floor, in AST nodes | Named predicates also written inline |
|---|---|
| 6 | 42 |
| **8** | **25** |
| 12 | 5 |

Reading all 25 at floor 8, **one** is the defect: `trace.is_ignored_filename` returns `filename.startswith('<') and filename.endswith('>')`, and `linecache` writes that same test out at two places in another module. Of the rest, five are the rich-comparison idiom `self._cmp(other) < 0` appearing in `minidom`, `_pydecimal` and `datetime`, which is three unrelated classes sharing a convention rather than one decision written three times; most of the remainder are a class testing its own field where it could have called its own accessor — `gzip` writing `self.mode == WRITE` inline beside a `writable()` that returns it. That last group is arguable and small; it is not a specification.

One in twenty-five is worse than the predicate condition `rules/duplication.md` already removed, which ran at roughly one in two and was removed for it.

The second failure is more fundamental and is the reason no tuning reaches it. An ORM filter and an in-memory filter are both Python expressions — `Order.status == OPEN` against `order.status == OPEN` — and they differ in the receiver's name, so an exact comparison never matches the pair the pattern is about. Renaming identifiers the way `rules/duplication.md` renames a body makes them match, and makes everything else match too:

| Floor, in AST nodes | Exact groups of 3+ | Renamed groups of 3+ |
|---|---|---|
| 8 | 248 | 526 |
| 12 | 60 | 187 |
| 16 | 16 | 52 |
| 20 | 4 | 20 |

At every floor, renaming roughly triples the group count, and the added groups are by construction the ones whose only commonality is structure. The 60 at floor 12 are the measurement `docs/duplication.md` reports for the condition it deleted; 187 is that detector three times noisier. There is no floor at which the version that can see the real pair is quieter than the version already judged too loud.

So specification's condition is the "same decision" definition of a duplicate. `docs/duplication.md` refuses that definition from the rule rather than parking it there, and puts the reviewer's question in prose instead — *where is this decided, and how many places could answer?* A specification rule would re-admit the refused definition under a pattern name. What the pattern genuinely adds is a named fix once the reviewer's question has been answered with "two", and a named fix with a situation, a cost and a cheaper default is an entry in `docs/patterns.md`.

### The domain-service detectors

Three were written for the rule's own conditions and none shipped.

**A stateless class with exactly one method**, the shape a domain service is most often wrongly given, reports 14 classes over the corpus. Not one is a service. Six are sentinels or dummies — `_Sentinel` in `traceback`, `_auto_null` in `enum`, `_Unknown` in `dis`, `Dummy` in `typing`, `OptionDummy` in `distutils`, `_HAS_DEFAULT_FACTORY_CLASS` in `dataclasses`. One is a metaclass, one a mixin, one the terminating leaf of `pathlib`'s selector chain. Two are test scaffolds, both named `_C`. One is an SAX interface base carrying no `ABC`, and two are the documentation examples in `xmlrpc.server`. Restricted to classes whose one method is public it reports 4, and those are the interface base, the two examples and one scaffold. Nought of fourteen.

**A `*Service`, `*Policy`, `*Calculator`, `*Manager` or `*Handler` holding state outside construction** reports 29, and all 29 are correct code: the `logging` handler hierarchy, `socketserver`'s request handlers, `http.cookiejar.DefaultCookiePolicy`, `asyncio`'s event-loop policy. Narrowed to `*Service` and `*Policy` it reports 2, both still correct. The suffix is naming a framework's vocabulary, which condition 4 of `rules/pattern-selection.md` already carves out, and `docs/clean-code.md` refuses suffix lists for naming on independent grounds.

**A method on an aggregate root taking another root** — the detector for condition 1 — is runnable and was not run, because it cannot be. It needs to know which type is an aggregate root, which is the input `rules/aggregates.md` states this plugin cannot guess without hard-coding a base-type name or a directory that the first differently arranged project would get wrong.

That is three detectors, two measured against 288,485 lines and wrong on every finding, one unmeasurable for the reason the neighbouring rule already documented. The rule declares judgment on that evidence rather than on a preference.

## What a reviewer asks

The four conditions are what the rule holds a change to. These are the questions that reach the part no condition states.

**Say the rule out loud without naming a type.** "A shipment may be released when the order is confirmed and the customer is inside their credit limit." If the sentence names two things the system stores separately, it is a service, and the only question left is where to put it. If it names one, it is a method, and extracting it is ceremony.

**Ask who would notice if it moved.** Domain logic that moves into the application layer breaks no test and changes no behaviour, which is exactly why it happens. The cost lands later, on the second reader who looks for the rule where the rules are and does not find it.

**Count the services in the context.** One or two is a boundary leaving residue. Eight is usually a model that has been hollowed out: the aggregates hold fields and the services hold every rule, which is the anaemic model `docs/bounded-contexts.md` describes, reached one reasonable extraction at a time. The test is whether a domain expert reading only the aggregates would recognise their own business.

**Ask what the service is called, and refuse the answer "Manager".** `docs/patterns.md` explains why `Manager`, `Helper`, `Util`, `Processor` and `Handler` are not on a banned list and are still the names of types whose responsibility nobody could state. A service named for its activity — `FundsTransfer`, `ReleaseDecision` — has been thought about; one named for its layer has not.

## Where this stops

**It does not teach DDD.** Evans' *Domain-Driven Design* defines the service and states the stateless requirement, and neither is reproduced. What is here is the part this framework will hold a reviewer to, plus the measurements behind what it declined to automate.

**The measurements score precision and nothing else.** CPython has no aggregates, so none of these detectors can be told how much of the defect it would find. A run over a large domain application would be worth more than another argument and has not been done — the same closing caveat `docs/duplication.md` records for its own floors, and it is the honest limit on everything in the section above.

**One corpus is one corpus, and the factory result is the one that would most repay a second.** Nine findings, nine of them factories, is a clean result and it rests on nine cases. A corpus with real aggregates in it might well show the shape firing on the defect too, at which point the detector becomes a question of ratio rather than a refusal. The position here is that it is refused on the evidence available, not that the evidence is complete.

**Nothing here is language-specific, and nothing here ships a detector.** The three candidates parse Python because the standard library ships one parser, which is the constraint every hook in this plugin works under. Since none of them ships, the conditions cost a reader in every language equally — which is worse than the rules with hooks and is stated rather than discovered.

**It says nothing about the strategic half.** Context maps, published languages, upstream and downstream relationships and the rest of strategic DDD are absent from this plugin, and `docs/bounded-contexts.md` carries what little of it the layout condition implies. A domain service is a tactical answer to a tactical residue, and putting one in the wrong context is a mistake this document cannot see.
