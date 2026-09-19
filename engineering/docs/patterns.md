---
id: patterns
type: doc
clade: engineering
subclade: quality
title: Patterns indexed by the situation that calls for them
summary: Ten patterns, each entered under the condition in the code that names it, with the shape it must exhibit, what it costs, and the cheaper alternative that is the default until it fails.
references:
  - rules/pattern-selection.md
  - docs/solid.md
  - docs/simplicity.md
  - docs/cross-cutting-concerns.md
---

# Patterns indexed by the situation that calls for them

This is the companion to [`rules/pattern-selection.md`](../rules/pattern-selection.md) and the input its four conditions are decided against. [`docs/solid.md`](./solid.md) closes by saying that the patterns satisfying its conditions are the vocabulary for the fixes and that no catalog exists yet; this is that catalog.

## How to read it, and why it is organised this way

A pattern catalog indexed by name teaches vocabulary. Vocabulary is useful and it is not the problem: the failure in practice is not that somebody has never heard of the decorator pattern, it is that they reach for it where a function would do, or fail to reach for it where the concern is already written out five times.

So every entry is entered under its **situation** — a condition on code that exists — and each carries four fields.

| Field | What it is for |
|---|---|
| **Situation** | The state in the tree that names this pattern. Condition 1 of the rule is decided against it. |
| **Shape** | The minimum a type must do to deserve the name. Condition 4 is decided against it. |
| **Cost** | What the pattern takes, paid continuously rather than in the diff. |
| **Cheaper** | The default. Condition 2 says the pattern ships only when this has been ruled out. |

Each entry is also marked **adds** or **removes**, because condition 3 gates the ones that add structure with the abstraction trigger in `rules/yagni.md`, and a reader should not have to work out which is which.

**The ten entries are not the classical catalog.** They are the named fixes for conditions this plugin's other rules state, plus the two or three that come up most in arguing against those fixes. That is a deliberate scope: a pattern with no situation in this corpus has no entry, and `rules/pattern-selection.md` says in its boundary section that applying one is outside the rule rather than against it.

## Entries under the code-structure axis

### Parameter Object, and the value it becomes — adds

**Situation.** A callable exceeds the parameter cap, or three or more parameter names travel together across three callables. Conditions 1 and 2 of `rules/value-semantics.md` detect both.

**Shape.** A type whose fields are the parameters, immutable, with no behaviour beyond validation and derivation. If it grows methods that operate on something other than its own fields, it has become a service and the name is wrong.

**Cost.** A type and a name, and one level of indirection at every call site: the reader now opens two files to learn what the function takes. The cost is small and it is not zero, and it is paid on every read rather than once.

**Cheaper.** Splitting the function. A five-parameter function is often two three-parameter functions that were merged, and with one call site the split is strictly smaller than the object. `docs/value-semantics.md` works this through.

### Builder — adds

**Situation.** A value has many optional parts, or an order in which its parts must be supplied, such that a partially constructed instance would be invalid if anyone could observe it.

**Shape.** A mutable accumulator, separate from the value, with a terminal call that validates and produces the immutable value. A builder with no terminal call is a mutable object with a fluent interface, which is a different and lesser thing.

**Cost.** A second type that mirrors the first field for field, and therefore drifts from it. Every field added to the value must be added to the builder, and the compiler will not remind anyone.

**Cheaper.** A factory function with keyword arguments and defaults, or an immutable value with a `replace` operation. In a language with keyword arguments, most builders are a workaround for a language feature that is present.

### Strategy, and the polymorphism behind it — adds

**Situation.** The third occurrence of the same discriminator chain, where two chains are the same when the discriminating expression is the same and the branch set matches. Condition 4 of `rules/solid.md` states it and `docs/solid.md` traces the three to Fowler.

**Shape.** One type per branch, selected by the discriminator at one place, each implementing the same operation. The selection happens once; if the discriminator is still tested after the dispatch, the chain was not replaced, it was moved.

**Cost.** The decision leaves the page. Adding a case to a `match` is a one-line diff a reviewer sees whole; adding a case to a hierarchy is a new file, a registration and a lookup nobody reads. `docs/solid.md` states this trade and concludes that two occurrences are genuinely better as two conditionals.

**Cheaper.** A lookup table, when every branch returns a value rather than doing work. Three branches each returning a constant are a dictionary, and three classes is the wrong answer to a dictionary.

### Decorator and middleware — adds

**Situation.** A cross-cutting concern — retry, transaction control, idempotency, instrumentation — appearing inline for the third time. `rules/cross-cutting-concerns.md` states the conditions and `docs/cross-cutting-concerns.md` argues each one.

**Shape.** A type or function with the same interface as the thing it wraps, adding behaviour before or after and delegating the middle. If the signature changes, it is an adapter; if it chooses between implementations, it is a strategy.

**Cost.** Order becomes significant and invisible. A timer outside a retry measures the whole sequence and inside it measures one attempt; an idempotency check on the wrong side of a retry defeats both. Stack traces also deepen by one frame per layer, which matters more than it sounds like at four layers.

**Cheaper.** Doing it in the one place, when there is one place. And checking whether the platform already provides it: a mesh that retries, a driver that owns the unit of work and a runtime that emits latency are boundaries that exist, and a second one composes badly with the first.

### Port and adapter — adds

**Situation.** A module on the policy side of the layer map imports one on the mechanism side. Condition 6 of `rules/solid.md`, and the one condition there where the abstraction trigger does real work rather than being satisfied by construction.

**Shape.** The interface is declared by the policy, in the policy's vocabulary; the implementation lives with the mechanism; the two are bound at the composition root. An interface declared next to its single implementation and named after it has inverted nothing.

**Cost.** An interface with one implementation, until the second adapter or the substituting test arrives. That is the exact shape `rules/yagni.md` deletes, which is why this entry is the catalog's clearest gated case.

**Cheaper.** Moving the code, so that what the policy needed is no longer in the adapter at all. `docs/solid.md` observes that this is almost always smaller and almost never the one proposed.

### Adapter and the anti-corruption layer — adds

**Situation.** An external interface whose vocabulary is not yours, used in more than one place, where the vendor's model and the domain's model disagree about what things are called or how they are shaped.

**Shape.** A translation at the edge: the vendor type goes in, the domain type comes out, and the vendor type appears nowhere beyond it. A layer that passes the vendor's type through under a new name has renamed the coupling.

**Cost.** A translation to maintain, and a second model to keep in agreement with the first. When the vendor changes, two things change.

**Cheaper.** Using the vendor's type directly, confined to the edge. With one call site and a stable vendor, the translation buys nothing that a narrow import boundary does not, and `docs/solid.md` makes the same point about stable mechanisms.

### Null Object — removes

**Situation.** The same absence check repeated at many call sites, where the behaviour on absence is identical everywhere and is "do nothing".

**Shape.** An instance of the same type that implements every operation as a no-op or an identity, substitutable for a real one with no caller change.

**Cost.** Absence stops being visible. A bug that leaves the field empty now produces silence instead of an error, and silence is the hardest failure to find. This is the entry whose cost most often exceeds its benefit.

**Cheaper.** An explicit optional and one guard at the boundary where the value enters. This is the default and it should usually stay the default; the entry exists mainly so that the cost is written down somewhere.

### Template Method — adds

**Situation.** Several operations share a fixed sequence of steps in which one or two steps vary, and the sequence itself is the thing worth enforcing.

**Shape.** A base declaring the sequence, with the varying steps as members the subtype supplies. Every concrete member is implemented; a subtype that raises rather than implementing one is condition 2 of `rules/solid.md`.

**Cost.** Inheritance, which is the tightest coupling a language offers: the subtype depends on the base's sequence, its state and its protected surface, and the base cannot change any of them. It also consumes the single inheritance slot in languages that have one.

**Cheaper.** Passing the varying step in as a function. This is the same design with the coupling removed, it composes, and it needs no hierarchy; the template method earns its place only when the sequence must be impossible to bypass.

## Entries under the domain axis

### Repository — adds

**Situation.** Persistence of an aggregate, where the domain needs to express what it wants in its own vocabulary and must not import the storage mechanism. A specialisation of the port entry above, with a well-known name.

**Shape.** A collection-shaped interface over one aggregate, declared in the domain, returning domain types. One repository per aggregate root, not per table.

**Cost.** A second query language. Every query the domain needs becomes a method, and the set grows until the interface has thirty methods and the team starts passing specifications or raw filters through it — at which point the storage mechanism has leaked back in wearing a domain name.

**Cheaper.** A query function per use case, in the application layer, returning exactly what that use case needs. This scales better than it sounds: there are fewer use cases than there are query shapes a general repository ends up supporting.

### State — adds

**Situation.** An object whose behaviour changes with an internal mode, where three or more of its methods branch on that mode. Below three, this is the discriminator chain entry and the rule of three has not been reached.

**Shape.** A type per state, holding the behaviour for that state, with transitions returning the next state. The mode field disappears; if it survives alongside the state types, there are now two representations of the same thing.

**Cost.** A class per state, and the transitions become the hard part: a state machine with six states has up to thirty transitions, and the pattern gives no help in deciding which are legal.

**Cheaper.** An enum field and one dispatch, until the third method branches on it. This is the same rule of three, counted over methods rather than over call sites.

## Two that are almost always the wrong answer here

**Singleton.** A globally reachable mutable instance constructed at import time is global state with a design-pattern name on it. It defeats the composition root that condition 6 of `rules/solid.md` requires, it makes tests order-dependent, and the property people actually want — one instance — is what a composition root already provides by constructing one. The entry is here so that the answer is written down rather than rediscovered.

**The non-patterns.** `Manager`, `Helper`, `Util`, `Processor` and `Handler` are not patterns; they are names for types whose responsibility nobody could state. `docs/clean-code.md` explains why they are not on a banned list — the list would be wrong in both directions — and the constructive version is condition 1 of `rules/solid.md`: a type nobody can name is usually a type whose methods share no state, and the metric says so.

## Where this stops

**The catalog is not complete and does not try to be.** Ten entries, chosen because each is the named fix for a condition this plugin states or the named alternative to one. Visitor, flyweight, memento, interpreter, observer, command and the rest of the classical catalog are absent. Their absence means this plugin has nothing useful to say about when to reach for them, not that they are wrong.

**It does not teach the patterns.** Each entry assumes the reader can recognise the pattern and needs to know when it applies and what it costs. Gamma, Helm, Johnson and Vlissides for the classical set and Fowler's *Patterns of Enterprise Application Architecture* for the repository and the anti-corruption layer are the sources, and neither is reproduced.

**The costs are argued, not measured.** Unlike the thresholds in `docs/clean-code.md` and `docs/value-semantics.md`, nothing here was run against a corpus. A pattern's cost is paid in reading and changing rather than in anything a script counts, so the entries state the cost and the reasoning, and a reader who disagrees with one has a specific claim to disagree with rather than a verdict.

**It says nothing about the domain patterns proper.** Aggregate, entity, value object, domain event, specification and the rest of the tactical DDD set are a vocabulary for modelling rather than for structure, and they need the bounded-context material that this plugin does not carry yet. `docs/simplicity.md` records the same gap for the layer map, and both close together.

**It cannot arbitrate a pattern against a measurement.** Every entry trades indirection for changeability, and a profile beats the catalog. `docs/solid.md` takes the same position and for the same reason.
