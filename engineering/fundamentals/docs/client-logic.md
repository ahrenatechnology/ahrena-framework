---
id: client-logic
type: doc
clade: engineering
subclade: architecture
title: Why a client's decision lives outside platform code
summary: What client logic in platform code costs, why a declaration and a port are the only two routes in, how the test for condition 1 is built, and why placement is not gated where dependency inversion is.
references:
  - rules/client-logic.md
  - rules/solid.md
  - rules/yagni.md
  - docs/solid.md
  - docs/simplicity.md
  - docs/contract-first.md
---

# Why a client's decision lives outside platform code

This is the companion to [`rules/client-logic.md`](../rules/client-logic.md). The rule states four conditions; this explains what they protect, how the detector for the first one is built, and where the rule meets the ones beside it.

## What it costs when a decision lives in code

A client decides things the platform cannot: which of its accounts belongs to which business unit, what a provider's status means for its revenue, what a product is called on its screens. Each of those decisions has an owner on the client's side, and each changes on the client's schedule.

Written into platform code, the decision costs three things.

**It is reviewed by the wrong people.** A change to a mapping table is a code change. It goes through code review, where the reviewers know the language and not the client's chart of accounts. The person who owns the decision cannot read the diff, and the people who can read it cannot judge it.

**It is hidden from its owner.** The client's finance team cannot open a Python module to check which business unit an account rolls up to. The decision is still theirs, and now they have to ask an engineer what they decided.

**It is inherited.** The next installation starts from the same code. A table written for the first client becomes the default for the second, and the second either carries values that mean nothing to it or forks the code to remove them.

One installation showed all three at once: a derivation script held the client's status mappings and business units as tables, and a business-unit name written by hand in four screens had to change in four places when the client corrected its spelling. On the platform side, a component inventoried the same pattern: vocabulary translation, account identity, labels, and the default currency and time zone.

## The two routes in

**A declaration** is the route for every rule that can be stated as data, which is most of them. A mapping, a list of accounts, a label, a default. It is a file in the installation's repository, so the client's decisions sit with the client's other decisions. It is validated against a schema the platform owns, so the platform states once what it can accept and every installation is held to the same shape. It changes by pull request, so a change to a decision has an author, a reviewer and a date.

The schema is a contract between the platform and every installation, and `rules/contract-first.md` governs it as one: it is authored, not generated from the loader, and a change that narrows it ships as a version. `docs/contract-first.md` carries the argument.

**A port** is the route for a rule that cannot be stated as data: a calculation the client owns, a call to a system only the client has. The platform defines the interface. The installation implements it and binds it. The platform calls what it was given and never learns what it is.

A port need not be in process. For a library the binding is the installation's composition root. For a component deployed as a service, whose `main` is the platform's, the port is a contract the platform owns across a process boundary, and the installation names the implementation's endpoint or entry point in a declaration. That is condition 3, not a third route: the platform owns the contract, and `rules/contract-first.md` holds it to the same discipline as any other published surface.

The direction matters more than the mechanism. If the installation declared the interface and the platform conformed to it, the platform would depend on the client. If the platform imported the implementation, the platform would carry the client's code. Either way the next installation inherits it.

**There is no third route.** Every other route that comes up puts a client difference into platform behaviour without a schema or a port: a fork per client, a branch per installation, a patch at deploy, a flag named for one client, a vendored copy edited in place. Each one works for the first installation, and each one makes the platform a different program in each place it runs. Condition 4 exists so that the question "is this a third way?" has a short answer.

## Placement is not gated, and layering is

Condition 6 of `rules/solid.md` and this rule both talk about which way a dependency points, and they are easy to read as one rule. They are not.

| | Dependency inversion | Client logic |
|---|---|---|
| Question | which module of one codebase may import which | whose repository a decision lives in |
| Boundary | policy and mechanism, inside one tree | platform and installation, across repositories |
| Gated by the abstraction trigger | yes | no |
| With one implementation | move the code, add no port | the port is required |

The abstraction trigger in `rules/yagni.md` asks for a second real consumer before an abstraction ships. For dependency inversion that is sound: with one adapter, `docs/solid.md` shows that moving the code is smaller than a port, and `docs/simplicity.md` explains why the trigger sits there.

For client logic the same move is the defect. Moving the installation's code to where the platform can call it directly puts it in the platform, which is condition 1's state. The seam is not there to let a second implementation in. It is there to keep the first one out, and one client is enough to need it.

So the trigger has nothing to arbitrate. It weighs an abstraction against the smaller code without it, and here the smaller code is the defect. The same holds for a schema field that selects behaviour: condition 4 of `rules/yagni.md` deletes a knob with one value and makes the value the behaviour, and the behaviour would then be client logic in platform code. Neither condition reaches this rule.

## The test for condition 1

The test is a job each component owns and publishes with each release, as a command an installation can run against the version it pins. Only the component knows its source layout, and only the installation knows its values. Its shape is the same everywhere.

1. **It takes two inputs.** A path to a set of declaration files, in the shape the platform's schema defines, and the root of the source to scan.
2. **It extracts what the installation introduces.** Account and business-unit identifiers, product names, labels: the names and identifiers that exist because this client exists. It extracts neither the platform's canonical values nor a vendor's vocabulary, because both are shared and belong in platform code.
3. **It normalises before it compares.** Values and source are case-folded and stripped of accents. A multi-word value is matched as written and in identifier form, so a two-word business unit is also found as its `snake_case`, `kebab-case` and `camelCase` spellings. A match is a whole token, so a value does not match inside a longer word.
4. **It skips what would only collide.** A value shorter than four characters, or a common word, is matched only when the component lists it explicitly. A value that is legitimately both, such as a word the platform's vocabulary and one installation's happen to share, is listed as an exception, with its reason.
5. **It scans everything but the declarations.** String literals, identifiers and comments, in every file under the source root except the declaration files it was given.
6. **It fails on any match.** The threshold is zero.

The component runs the test in its own pipeline against synthetic declarations, which proves the test works and can find nothing else. That is why a reviewer is the gate on the component's own pull request. Each installation runs it in its pipeline against its own declarations and the component version it pins, which is where it finds something. The same test, pointed at the installation's own platform-side tooling, covers the derivation scripts and loaders that live in the installation repository.

The test cannot see a translation table whose keys are a vendor's statuses and whose values are the platform's: both sides are shared, and the client's decision is the pairing. That table is the reviewer's, and the question below is the one to ask of it.

A hook in this plugin that scans any repository against its own declared values is the obvious next step. It waits until one component has the test and the shape is known, because a detector written before its first real input tends to be wrong about the second.

## What a reviewer checks

The test sees literals. The rest is a reviewer's, and these are the questions, one per condition.

- **Condition 1.** Would a second installation write this table, this branch, this default the same way? If not, it is client logic whatever its values are today.
- **Condition 2.** Where does the platform read this rule from, and does it validate it before using it? Is the schema in the platform?
- **Condition 3.** Who declares the interface? Does any platform module import from the installation, or look at the concrete type it was given?
- **Condition 4.** Does this client difference reach platform behaviour through a declaration or a port? If through neither, it fails.

## Where this stops

**This doc does not choose a schema language.** JSON Schema, a typed configuration model and a protocol buffer definition all satisfy condition 2. What the condition requires is that the platform owns the schema and validates against it.

**It does not settle how a port is bound.** A constructor argument, an entry point and a container registration are all dependency injection. The composition root that binds them sits on the installation's side, and `docs/solid.md` says why a composition root is allowed to know every concrete type.

**It does not decide where an existing table moves.** Moving logic that is already in code is migration work with its own issues. The rule and this doc describe the state a change must not add.

**The cost is real and it is paid up front.** A client difference that would have been one line of code becomes a schema field, a validation and a declaration. That is more work for the first installation. It is paid once, and every later installation gets a platform that already knows how to accept the difference.
