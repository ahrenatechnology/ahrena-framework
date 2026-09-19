---
id: value-semantics
type: rule
clade: engineering
subclade: quality
title: Parameter objects and value semantics
statement: A callable takes at most 4 parameters, a type declared immutable exposes no mutable field, and a type that defines equality defines hashing.
enforcement: hook
enforced-by: hooks/check-structure.py
references:
  - docs/value-semantics.md
---

# Parameter objects and value semantics

Five conditions, all decided by `hooks/check-structure.py`. The first two decide when a parameter list has become a value; the last three decide whether that value behaves like one. `docs/value-semantics.md` gives the provenance of both thresholds, the argument for why the two halves belong in one rule, and the cases where the fix is worse than the finding.

The two halves are one subject because they are one move. A parameter list crossing the threshold is told to become an object, and an object made out of a parameter list is a value: it has no identity, two of them carrying the same fields are interchangeable, and the only reason it exists is to be passed. Conditions 3 to 5 are what stops that object being a mutable bag with a class statement around it, which is the failure mode the first two conditions would otherwise create.

Conditions 1 and 2 add structure, so both are gated by the abstraction trigger declared in condition 1 of `rules/yagni.md`. A rule may reference only a doc, so the trigger is named here in prose rather than linked. It reads: an abstraction is justified when it has a second real consumer, or when a test that exists today requires the seam. Conditions 3, 4 and 5 remove structure or replace a lie with the truth, and the trigger does not gate them.

## Conditions

Each of these is decided by `hooks/check-structure.py`.

1. **A callable takes at most 4 named parameters.** The receiver is excluded, and so are `*args` and `**kwargs`, because a variadic is one name at the call site and there is nothing in it to gather. Four is the measured ceiling of the framework's own Python: 61 callables, maximum 4, and 4 at the 95th percentile. Martin's *Clean Code* puts the ceiling at three; this cap takes the measured number, which is one higher and fails nothing that exists. Gated. A parameter object is a new type, so with a single call site the cheaper fix is to split the function, and the finding says so.

2. **The third callable in a module passing the same ordered run of 3 or more parameter names is a parameter object.** A run is contiguous in the parameter list, and only the longest run shared by a given set of callables is reported. Three is Fowler's Data Clumps, and three occurrences is the rule of three that condition 4 of `rules/solid.md` already uses for the discriminator chain; reusing it rather than inventing a second number is deliberate, because an arbitration mechanism that comes in two incompatible versions is not one. Gated, and satisfied by construction: the third callable is the second consumer and then some.

3. **A type declared immutable exposes no mutable field.** The state is a class declared frozen — a `frozen=True` dataclass or `attrs` class, or a `NamedTuple` — carrying a field annotated `list`, `set`, `dict`, `bytearray`, `deque`, `defaultdict`, `Counter`, `OrderedDict` or one of their typing aliases, or defaulted through a `default_factory` that builds one. Freezing binds the reference and not the contents, so two values that compare equal today need not tomorrow and a hash computed once stops matching the object it came from. The fix is the immutable counterpart: a tuple, a `frozenset`, a `MappingProxyType`.

4. **A type declared immutable does not write through its own guard.** The state is a call to `__setattr__` on an object other than a bare name, inside a method of a frozen class, anywhere but `__post_init__`. Normalising a field during construction is what `__post_init__` is for and is excluded; everything else is a type that says it is immutable and is not. The fix is to return a replaced copy, or to stop declaring the type frozen.

5. **A type that defines equality defines hashing.** The state is a class that defines `__eq__` and neither defines `__hash__` nor assigns it. Python sets `__hash__` to `None` when `__eq__` is defined, so the instance cannot be a dict key or a set member, and the failure surfaces far from the class at the first place someone tries. Classes whose equality is generated — `dataclass`, `attrs` — are skipped, because the decorator decides hashing along with equality. The fix is one line either way: define `__hash__` over the same fields, or write `__hash__ = None` to say the type has identity rather than value.

## Where this stops

**Condition 1 does not reach a value type's own field count.** A frozen dataclass with eight fields generates its `__init__` rather than declaring one, so the condition never sees it, and that is the intended consequence rather than a hole. The fix for a long parameter list is a value, and penalising the value for having the fields the parameters had would leave nowhere to put them. What the eight-field value still owes a reader is a reason those eight things travel together; that is a cohesion question and condition 1 of `rules/solid.md` is where it is asked.

**Condition 1 does not reach a parameter list that is already a value in disguise.** A function taking four parameters that are always the same four is a clump under condition 2 whether or not it is under the cap, and a function taking five genuinely unrelated arguments at one call site is over the cap and probably fine. The count is a trigger for the question, not the answer to it.

**Condition 2 reads one module at a time.** The clump that matters most is the one spread across a package, where the same four values are threaded through six files and nobody has noticed. Deciding that needs every module at once, and this detector parses one file at a time, so the cross-module form is a reviewer's count. The single-module version was kept because it is free and because a clump usually starts inside one file before it spreads.

**Condition 2 does not reach a uniform interface.** Three functions registered in the same dispatch table share a signature because the table requires it, and the shared run is the contract rather than a clump. Collapsing it into an object is sometimes still right and often is not, and the distinction is whether the callables are called through the table or called directly.

**Condition 3 does not reach a mutable object reached through a field of an immutable one.** A frozen type holding a tuple of mutable records is as leaky as one holding a list, and the annotation says `tuple`. Deep immutability needs to follow types across modules, which a single-file parser cannot do; what this condition catches is the shallow case, which is the common one.

**Condition 3 does not reach a deliberate cache.** A memoisation dictionary on an otherwise immutable value is a real pattern and it does violate the condition. The honest fix is to hold the cache outside the value; where that is genuinely worse, the field belongs behind a name that says so and the file belongs in the hook's exclusions, which is a decision someone makes once and writes down.

**Condition 5 does not decide whether the type should have value semantics at all.** An entity has identity, two entities with equal fields are not the same entity, and `__hash__ = None` is the correct answer for one. The condition does not read which kind of type it is looking at; it requires only that the author say which, because the silent version is the one that fails in a set three months later.

**This rule declares a hook rather than judgment, and two of its conditions are nonetheless gated.** Every condition here is decided by a parser, so the script stands in for the rule and the rule contributes no text to any request, which is the cheapest route and the reason to take it. The gate on conditions 1 and 2 would normally be the argument for `judgment`, as it is in `rules/solid.md`: a hook rule contributes no text, so the arbitration would be dropped. It is not dropped here because it is carried in the finding itself — both messages name the trigger and say what satisfies it, which delivers the arbitration at the moment the condition fires instead of on every request that has nothing to do with it. That works because each gate has one answer that fits in a sentence. Where a gate needs a layer map or a count across the tree, it does not fit, and `rules/solid.md` takes the other route for exactly that reason.

**The detector parses Python and nothing else.** The standard library ships one parser and this plugin takes no dependencies. Conditions 3, 4 and 5 are also the most language-shaped in this plugin: a language with a real `const`, or with value types the compiler enforces, decides them at compile time and does not need the rule. In a language that does not, these are read by a reviewer.
