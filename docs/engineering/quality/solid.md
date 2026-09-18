---
type: doc
title: SOLID
scope: engineering/quality
consulted_by:
  - rules/engineering/quality/solid
---

# Doc: SOLID

> **Type:** Reference manual · **Scope:** Engineering — what each SOLID condition prevents, and where it stops paying

## Overview

The rule states five conditions as detectable states with thresholds. This manual explains what each one prevents, what it costs, and the situations where applying it makes the code worse. Read it when a condition fires and the remedy is not obvious, or when deciding whether a condition should fire at all.

The order below is the order of the acronym, which is not the order of usefulness. In practice the first and the fifth conditions catch most real defects; the second is the one most often applied too early.

## Context

- **Domain:** application code design
- **Audience:** engineers and agents writing or reviewing code
- **Update:** when a condition's threshold changes, or when a language the framework covers gains a detector that shifts a condition from review to CI

## Content

### Single responsibility — one module, one actor

**What it prevents.** Two teams editing the same file for unrelated reasons, and each breaking the other. The defect is not size; it is shared ownership of a change surface.

**Why "actor" and not "thing".** "A class should do one thing" is unusable, because "one thing" expands or contracts to justify any decision already made. "One reason to change" is closer but still abstract. The actor formulation is operational: name the role that requests the change. If two different roles request changes to the same module, the module has two owners and will be edited by both.

A domain entity that serializes itself to the database is the canonical violation, and the actor test explains why cleanly: the business changes the invoice rules, the schema owner changes the columns. Two roles, one file, guaranteed collision.

**Where it stops paying.** Splitting a 30-line module because a metric flagged it. `LCOM4 > 1` marks a candidate; the actor test decides. A module with two method clusters that answer to the same role is cohesive, whatever the metric says.

### Open/closed — a case enumeration appears once

**What it prevents.** Adding the fourth payment method and discovering the type is switched on in six places, one of which you missed.

**Why the threshold is three.** Two conditionals over the same discriminator are cheaper to read than a polymorphic hierarchy — the reader sees both branches in one place. At three, the cost inverts: you can no longer hold the set of sites in your head, and a missed site becomes a silent defect rather than a compile error.

This is the same threshold the duplication rule uses, for the same underlying reason. Two points do not establish a direction. Three do.

**Where it stops paying.** A discriminator that is genuinely closed. Days of the week will not gain an eighth member. A `match` over a sealed set of three states, in three places, is fine — the extension the principle protects against cannot happen.

**The common failure.** Applying this condition before the second case exists, which produces a strategy interface with one strategy. That is a [`yagni`](../../../rules/engineering/quality/yagni.md) violation, and the abstraction trigger exists precisely to catch it.

### Liskov substitution — a subtype never narrows its base

**What it prevents.** Code that works against the base type and breaks against a subtype, at a call site that never mentions the subtype.

**The mechanical version.** Contract reasoning makes this principle sound academic. It is not. Four concrete moves violate it, and all four are visible in a diff:

| Move | What the caller experiences |
|---|---|
| Strengthen a precondition | An argument the base accepts is now rejected |
| Weaken a postcondition | A guarantee the caller relied on is gone |
| Raise a new exception | A failure path the caller does not handle |
| Leave a member unimplemented | A method that exists and does not work |

**Where it stops paying.** Nowhere — this condition costs nothing to satisfy, because satisfying it means removing structure rather than adding it. A subtype that cannot honor the base contract is not a subtype, and the fix is a separate type, not an abstraction.

**The signal worth knowing.** `raise NotImplementedError` in a concrete class is the single highest-yield grep in this manual. It is almost always this condition, condition 4, or both.

### Interface segregation — no implementation leaves a member empty

**What it prevents.** An interface that forces implementers to carry members they have no meaning for, and callers to wonder which members are real.

**Read it from the implementation side.** The principle is usually stated as "clients should not depend on methods they do not use", which asks you to reason about hypothetical clients. The implementation side is observable: an empty override is the interface telling you it declares a member that does not belong to every implementer. Split at that member.

**Where it stops paying.** Splitting an interface into single-method fragments because the principle says smaller is better. An interface whose members are always implemented together and always called together is one interface. The trigger is an empty implementation, not a member count.

### Dependency inversion — dependencies point inward

**What it prevents.** A domain you cannot test without a database, and a business rule you cannot read without knowing the ORM.

**What "inward" means.** The domain declares what it needs as a port. The outer layer implements it. The direction of the import is the direction of the dependency, and it runs opposite to the direction of control flow — which is the part that takes getting used to. Control flows from the HTTP handler into the domain; imports flow from infrastructure toward the domain.

**Where it stops paying.** A port with one adapter and no test that needs the seam is indirection, and the abstraction trigger rejects it. The condition fires on the import direction, which is free to satisfy — not on introducing ports, which is not.

For Python, the enforceable form of this condition is [`module-boundaries`](../backend/python/module-boundaries.md).

## The conflict with simplicity, stated plainly

Three of the five conditions describe a state a module is already in: mixed actors, a subtype that narrows its base, an interface member nobody implements. Satisfying them removes structure. They are free and they always apply.

Two of them introduce structure: polymorphism in place of a conditional, and a port in place of a direct call. These are the conditions that produce over-engineered code when applied on principle rather than on evidence. Both are gated by the abstraction trigger in [`yagni`](../../../rules/engineering/quality/yagni.md).

An engineer who knows only this distinction has most of the value of SOLID and almost none of its failure mode.

## Glossary

| Term | Meaning |
|---|---|
| Actor | The role that requests a change — a team or a function, not a subsystem |
| Port | An interface declared by an inner layer, stating what it needs from outside |
| Adapter | An outer-layer implementation of a port |
| LCOM | Lack of cohesion of methods; a metric marking split candidates, not a verdict |
| Discriminator | The value a conditional switches on to select behavior |

## References

- [`solid`](../../../rules/engineering/quality/solid.md) — the enforceable conditions
- [`yagni`](../../../rules/engineering/quality/yagni.md) — the abstraction trigger that gates conditions 2 and 5
- [`kiss`](../../../rules/engineering/quality/kiss.md) — the thresholds that catch the over-applied version
