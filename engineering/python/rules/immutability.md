---
id: immutability
type: rule
clade: engineering
subclade: python
title: Domain values that do not change under their holders
statement: A dataclass under domain/ is frozen or says why not, and a function under domain/ changes no list, dict or set it was passed.
enforcement: hook
enforced-by: hooks/check-python.py
references:
  - docs/architecture.md
---

# Domain values that do not change under their holders

Two conditions, both decided by `hooks/check-python.py`, both read only under a `domain/` directory. The subject is the domain layer's values: a record two parts of the program hold at once, and a container a caller hands to a domain function. In both cases Python makes the mutation free and silent, and the holder who did not make it is the one who pays.

The predecessor's immutability law had four parts. Two are already decided elsewhere in this framework and are not restated: a parameter defaulted to a mutable is condition 4 of [`typing.md`](typing.md), and a frozen type that exposes a mutable field, or writes through its own guard, is conditions 3 and 4 of the fundamentals plugin's value-semantics rule, [`value-semantics.md`](../../fundamentals/rules/value-semantics.md). This rule carries the two that were left: the record that is not frozen at all, and the argument that is changed in place.

**Why only `domain/`.** The predecessor applied both to all code and exempted ORM models and builders by name. A rule over all code would report every SQLAlchemy model, every Pydantic settings object and every accumulator a recursive helper threads through itself, and the exemption list would grow until it was the rule. The domain layer is where the subject lives: [`docs/architecture.md`](../docs/architecture.md) puts values and entities there, and the fundamentals domain-model rule already locates the layer by that directory name, so this rule reuses the convention rather than inventing a second one. A project that lays its domain out under another name gets nothing from this rule, which is the cost the domain-model rule already accepted for the same reason.

## What the specification says

- **Mutability is a property of the object, and an immutable container can still hold mutable objects**: Language Reference §3.1, *Objects, values and types*.
- **Arguments are passed by assignment**: the callee receives a reference to the caller's object, so changing a list it was passed changes the caller's list (Python Programming FAQ, *How do I write a function with output parameters?*). Condition 2 is that consequence held back in the domain.
- **A frozen dataclass raises on assignment to a field**, and is hashable when it also defines equality: PEP 557 and the Library Reference, *dataclasses — Frozen instances*. That is what condition 1 asks a domain record to be.

## Conditions

Each of these is decided by `hooks/check-python.py`, in modules under a `domain/` directory.

1. **A dataclass or attrs class is frozen, or says why it is not.** The state is a class decorated with `dataclasses.dataclass` without `frozen=True`, or with `attrs.define`, `attrs.mutable`, `attr.s` or their aliases, carrying no comment on the decorator's line or the line above. `attrs.frozen` is frozen by construction. A frozen value can be shared, hashed, put in a set and handed to a coroutine without anyone checking who else holds it; a mutable one cannot, and the decorator gives no hint which kind a reader is looking at. An entity whose identity is a field and whose state moves on purpose is the legitimate mutable case, and the comment is where the author says so: "the ledger is identified by its id and its balance moves", once, where the next reader looks.

2. **A function does not change a list, dict, set or deque it was passed.** The state is a call to an in-place method — `append`, `extend`, `insert`, `remove`, `pop`, `clear`, `update`, `setdefault`, `add`, `discard`, `sort` and the rest of the closed set the hook carries — on a parameter, or an assignment, augmented assignment or `del` through a subscript of one, or `+=`, `|=` and the other augmented assignments on a parameter annotated as a list, dict, set, deque or one of their typing aliases, which change that object in place (Language Reference §7.2.1, *Augmented assignment statements*). The receiver of a method is excluded, taken positionally as `typing.md` takes it: an entity changing its own state is what a method is for. A caller that passes a list to `enrich(tags)` and gets one back has two names for one object and no way to tell from the signature that its own list changed. The fix is to build a new value and return it.

    Measured with the hook as it ships, on 2026-11-14, by copying two corpora that have no domain layer under a directory named `domain/`, to see how often the shape occurs in code that was never held to it. The CPython 3.14 standard library without its test suite — 719 files, 334,080 lines, 17,205 function definitions — gives 206 findings; pip 26.2.1 with its vendored libraries — 398 files, 133,846 lines, 5,110 definitions — gives 57. About one definition in a hundred in both. Read by hand, most are the accumulator idiom of a recursive helper that threads one list through its own calls, which is why the condition is scoped to the domain rather than shipped everywhere: in the domain that idiom has no reason to exist, and outside it the condition would be wrong about a common pattern, which is the failure that gets a gate switched off.

    The same copies give condition 1 a measurement too: 12 of the standard library's 21 dataclasses and 24 of pip's 50 are not frozen. Neither corpus has a domain, so this says only that a mutable dataclass is the default people write, which is the reason a domain needs the condition.

## Where this stops

**Neither condition reaches a value outside `domain/`.** An adapter's request schema, an ORM model, a settings object: each is mutable for a reason its library gives, and each is outside the layer this rule protects. Whether a FastAPI response model should be frozen is argued in `docs/web-services.md`, not required here, because a response is built once and serialised, and freezing it buys nothing a reader can observe.

**Condition 1 does not read a Pydantic model or a `NamedTuple`.** A `NamedTuple` is immutable by construction. A Pydantic model in the domain is a finding of the domain-model rule before it is one of this rule, because the domain imports no framework.

**Condition 1 does not decide whether the comment is a reason.** It checks that somebody was made to write something, the trade condition 3 of `typing.md` makes for `Any` and the same place it stops.

**Condition 2 does not reach an attribute assignment on a parameter.** `order.status = "paid"` changes the caller's object as surely as `tags.append` does, and it is also how an entity passed to a domain service is legitimately changed. Telling the two apart needs to know whether the parameter's type is a value or an entity, which a single-file parser does not. The container case is the one with no legitimate domain reading, and it is the one decided.

**Condition 2 does not see `+=` on an unannotated parameter.** On a list it changes the caller's object; on an int it rebinds a local name. Only the annotation tells the two apart, and `rules/typing.md` already requires it, so the gap closes wherever that rule holds.

**Condition 2 does not follow an alias.** `rows = tags; rows.append(x)` changes the caller's list through a second name and is not seen. Following aliases means data-flow analysis, which this hook does not do.

**Deep immutability is not reached.** A frozen record holding a tuple of mutable records is as leaky as one holding a list, and the value-semantics rule names the same limit for the same reason.

**This rule declares a hook, and both conditions have a script.** The statement reaches no request; the boundary material above is what a reviewer reads when a finding is disputed.
