---
id: aggregates
type: doc
clade: engineering
subclade: architecture
title: The consistency boundary and the fact that crosses it
summary: Why the aggregate boundary is drawn by invariants rather than by the object graph, what one root per transaction actually buys, why an event carries two fields and not three, and the cases where the boundary should be larger than the advice says.
references:
  - rules/aggregates.md
  - docs/bounded-contexts.md
  - docs/contract-first.md
  - docs/patterns.md
---

# The consistency boundary and the fact that crosses it

This is the companion to [`rules/aggregates.md`](../rules/aggregates.md). The rule states six conditions and names what decides each one; this explains what they protect, where the two figures came from, and the situations in which satisfying one makes the model worse.

[`docs/bounded-contexts.md`](./bounded-contexts.md) closed by saying that the tactical vocabulary beyond aggregate and entity was assumed rather than taught, and that domain events had no home: their shape on the wire belongs to [`docs/contract-first.md`](./contract-first.md) and their place in the model was covered nowhere. [`docs/patterns.md`](./patterns.md) recorded the same gap from the structural side. This closes the two halves that the rest of this plugin actually depends on — the boundary and the event — and leaves the rest of the set open on purpose.

## What the aggregate is for, stated so it can be wrong

An aggregate is usually introduced as a cluster of objects with a root. That description is true and useless, because every object graph is a cluster of objects and any of them can be called the root. It gives no way to decide whether a proposed boundary is right, which is the only question anybody actually has.

The useful statement is the one Evans gives and that condition 1 of the rule takes: **an aggregate is the set of things that must be consistent at the instant a transaction commits.** The boundary is a consequence of the invariants, not a taste about object graphs. List the rules the business says are always true, write down which types each one names, and the partition falls out. If no rule connects two types, they are two aggregates however tightly the code currently couples them; if a rule connects them, they are one however inconvenient that is.

**This is what makes the other conditions decidable.** Reference by identity, one root per transaction and eventual consistency across boundaries are all arbitrary unless the boundary means something specific, and "the set over which an invariant holds at commit" is the only definition that makes them follow rather than accumulate. A team that draws boundaries by intuition and then applies the other three rules has three constraints with nothing underneath them, and will relax whichever one hurts first.

**The common failure is the boundary drawn too small.** Small aggregates are the standard advice and they are good advice, and the way teams reach them is by cutting an invariant in half. The rule then moves into the application service, where it is enforced by a read, a check and a write that another request can interleave with — and it now fails under concurrency in a way nobody sees in a test. Nothing about the boundary announces this. The aggregate looks smaller, the code looks cleaner, and an invariant the business believes is guaranteed is now guaranteed by luck.

So the rule states the boundary condition first and refuses to state a size. Size is an outcome. `rules/domain-model.md` takes the same position about a layer map: declare the thing that is checkable and let the consequences follow, rather than describing the outcome and hoping.

## What one root per transaction buys

Vernon's four rules of thumb in *Effective Aggregate Design* are the source for conditions 2, 3 and 4, and the second of them — modify one aggregate instance per transaction — is the one that sounds like an arbitrary restriction. It is not, and the reason is worth stating in terms of what it costs to break rather than as an appeal to the source.

**Contention.** A transaction's conflict surface is the union of what it writes. Two roots written together means a request conflicts with everything that touches either one, so the conflict rate stops being the sum of two aggregates' write rates and becomes closer to their product. An aggregate written by one user's own actions has essentially no contention; joined in a transaction with one written by a nightly job, it inherits the job's.

**The boundary stops being real.** If two roots are always written together, the database is enforcing a consistency rule the model did not declare. Every reader of the model now has to know that the declared boundary and the enforced boundary differ, and the divergence is invisible: there is no type, no name and no test that records it. The first person to write one of the two roots on its own discovers the rule by breaking it.

**It is the condition that forces condition 1 to be answered.** When two roots must be written together, one of two things is true: there is an invariant spanning them, in which case the boundary is wrong and should be one aggregate; or there is not, in which case the second write can happen afterwards. Condition 2 is what turns that into a question somebody has to answer rather than a shape that persists because it was convenient on the day.

**Where it stops paying** is in work whose subject is many roots. A migration, a backfill and a bulk operation touch many aggregates by definition, and the honest answer there is one transaction per root rather than one transaction for the batch — which satisfies the condition — or an acknowledgement that the job is not a use case and the condition is not about it. The rule's boundary section says so, and it says so before the case is met rather than after.

## Reference by identity, and the thing it prevents

Condition 3 is the cheapest of the four to satisfy and the easiest to argue against, because holding an object is more convenient than holding an identifier at every single call site.

The argument for it is not the persistence cost, although loading a graph nobody asked for is real. It is that **a direct reference removes the only signal that a boundary was crossed.** `order.customer.apply_credit(...)` reads like one operation on one thing. It is two aggregates modified in one transaction, which is condition 2 broken, and nothing in that line says so. Written as `customer_id`, the second aggregate cannot be reached without loading it, loading it cannot happen without a repository, and the repository call is visible in the use case where the decision belongs.

The identifier is the other root's own identifier type rather than a string, which costs a type and buys back what the reference gave away: the field still says what it points at, so the model has not lost expressiveness, only reach. This is the same trade `docs/patterns.md` describes under the adapter entry, where a translation at the edge keeps the vocabulary and drops the coupling.

**Where it stops paying** is inside one boundary, where entities reach each other directly and should: the root is what holds them together and there is no second consistency boundary to cross. It also stops on a read model, where several roots are assembled for a screen and re-resolving identifiers buys nothing, because no invariant is being enforced there.

## Eventual consistency, and why the rule asks for a number it will not supply

Condition 4 requires three answers about the gap between two boundaries — which root is authoritative, how long the other may disagree, and what closes the gap — and supplies none of them.

That is deliberate and it follows a position this plugin already holds twice. Condition 4 of `rules/cross-cutting-concerns.md` declines to name an idempotency retention window because the window is the client's retry budget. Condition 6 of `rules/solid.md` declines to ship a layer map because the map is the project's. The consistency window is the same kind of figure: it is set by what the business can tolerate between the two facts being true, and a framework guessing it would be guessing at somebody else's tolerance.

**What the condition does contribute is that the number has to exist.** An unstated window is not a fast one; it is one nobody is monitoring, and the failure mode is specific — the repair mechanism stops working, nothing alarms because nothing knows what "late" means, and the divergence is discovered by a customer. Writing the figure down is what makes the gap an operational thing with an owner rather than an assumption.

**The mechanism is not the condition.** A published event with a handler is the usual answer and it is not the only one: a periodic reconciliation, a read that resolves the second root on demand, and a saga with compensations are all answers, and which fits is decided by the deployment. `docs/cross-cutting-concerns.md` makes the same distinction for its own concerns — one place, not one mechanism.

## The event, and why it is in the same rule

An event is in the aggregate rule rather than a rule of its own because it is what conditions 1 to 4 create the need for. Draw a boundary, forbid a second write inside the transaction, and the second aggregate has no way to learn. The event is the answer, and separating the two produces the failure the rule names in its opening: the boundary conditions get adopted, the second aggregate is updated by a second repository call, and the team believes it is doing DDD.

**Two required fields, and why not three.** An event's type name says what happened. A consumer holding one still cannot act without two more things: which instance it happened to, and when. Those two are asked of every event, whatever it is, which is what makes them a contract rather than a convention.

The third field usually proposed is the actor — who did it. It is not in the set for the reason `docs/bounded-contexts.md` gives for keeping `deleted_at` out of the audit stamp: the question is already answered somewhere better. The aggregate's stamp carries created-by and updated-by under condition 3 of `rules/domain-model.md`, and putting the actor on the event as well produces two records of the same fact that can disagree — which is duplication in the sense `docs/duplication.md` says no detector will catch, one decision expressed twice with no shape in common.

The symmetry with the audit stamp is worth noticing rather than hiding. The stamp is four fields because it answers two questions about two events; the event contract is two fields because it answers two questions about one. Both numbers come from counting what is asked, and neither was chosen for looking reasonable.

**Immutability and the no-entity state.** An event is a fact about the past, so a mutable event is a fact that can be edited after the fact. That half is mechanically decided already: `hooks/check-structure.py` runs conditions 3 and 4 of `rules/value-semantics.md` over any type declared frozen, so a frozen event holding a list or writing through its own guard is caught without this rule shipping anything. What is not caught is an event that was never declared frozen, and a reviewer decides that.

Carrying an entity is the subtler defect. An event holding a live object hands the consumer something whose state has moved on since the fact was true, so the consumer reacting to `OrderShipped` reads an order that has since been cancelled and is now reasoning about the present while believing it is reasoning about the past. Identifiers and values are the payload, and a consumer that needs more loads it and knows it is loading the present.

**On the wire is a different question.** `rules/contract-first.md` condition 4 requires the CloudEvents attributes on any event crossing a published surface, and none of that is restated here. The envelope is about interoperability between systems; these two fields are about the fact being usable at all. An event will usually carry both, and the two sets overlap only in spirit: CloudEvents' `id` identifies the message and this rule's identity field identifies the aggregate, which are different things that get conflated about once per project.

## Why no detector, and what a project can wire in

Every condition above describes a state a script could find, and none of them can be found by a script this plugin ships. The rule's final section says so and this is the longer version, because "we did not write the hook" and "the hook cannot be written here" deserve to be told apart.

A detector for condition 2 counts the roots a use case writes. To count them it has to know which calls are writes to a root, which means knowing the repository base type or the root base type — a name the project chooses. A detector for condition 3 reads a field's declared type and asks whether it is another root: same input. Conditions 5 and 6 need to know which types are events. Each is a one-line input and there is no defensible default: guessing `Repository` as a suffix, or `domain/events.py` as a location, produces a gate that is confidently wrong on the first project that spells it differently, and `docs/simplicity.md` records what a confidently wrong gate does to the rules around it.

**What a consuming project should do with that.** Name the two base types once, write the four detectors against them, and run them in the pipeline beside `hooks/check-structure.py`. They are small — a walk over `application/` counting repository writes per function, and a walk over the event types checking two field names and a frozen declaration. `rules/contract-first.md` takes the same position about its own five conditions and `docs/contract-first.md` argues it at length: a real detector the consuming project runs beats a guessed one shipped from here.

**What this costs in the budget.** The rule declares judgment, so its statement is injected into every request whether or not the request has a domain model in it. That takes the plugin from 847 characters across six judgment rules to 1,001 across seven, and `docs/context-budget.md` in the foundation plugin is the accounting. It is the largest single addition since the plugin's first two rules, and the thing to weigh it against is not a cheaper enforcement route — there is not one — but the alternative of leaving the vocabulary unstated, which is what `docs/patterns.md` and `docs/bounded-contexts.md` both recorded as the gap.

## Where this stops

**This document does not teach DDD.** Evans' *Domain-Driven Design* and Vernon's *Implementing Domain-Driven Design*, and in particular the three-part *Effective Aggregate Design*, are the sources for conditions 1 to 4, and neither book is reproduced. What is here is the part this framework holds a reviewer to and the argument for each figure.

**It carries no measurement.** Every other threshold in this plugin was either measured against a corpus — the statement count in `docs/clean-code.md`, the parameter cap in `docs/value-semantics.md`, the clone floor in `docs/duplication.md` — or is a definition with nothing to tune. The two figures here, one root per transaction and two fields on an event, are neither: they are a cited rule of thumb and a count of the questions an event is asked. The framework's own Python contains no aggregates and no events, so there is nothing to run, and `docs/bounded-contexts.md` already records that its own two detectors are held to a lower standard of evidence for the same reason. A reader should know which numbers in this plugin are measured and which are argued, and these two are argued.

**It does not cover the rest of the tactical set.** Specification, factory, domain service, and the modelling half of value object have no artifact. The mechanical half of value object is `rules/value-semantics.md` and the entity contract is `rules/domain-model.md`; the others are absent because this plugin has nothing useful to say about when to reach for them yet, which is the same scope `docs/patterns.md` claims for its ten entries.

**It does not decide how contexts integrate.** An event published by one context and consumed by another is an integration decision — published language, customer-supplier, conformist — and `docs/bounded-contexts.md` already declines to pick one. This document is about the event inside the model that produced it. What happens to it at the boundary between two contexts is that document's open question and remains open.

**It says nothing about event sourcing.** Using events as the system of record rather than as notifications changes what an aggregate is, what a repository does and what a projection costs, and it is a different architecture with its own literature. Every condition here holds in a system that stores state and publishes events, which is the common case; a system that stores the events has questions this rule does not ask.
