---
id: client-logic
type: rule
clade: engineering
subclade: architecture
title: Platform code holds no client logic
statement: No client logic in platform code: a client's rule is a declaration in its installation, checked by a platform schema; its code enters only by a platform port.
enforcement: judgment
references:
  - docs/client-logic.md
---

# Platform code holds no client logic

Four conditions. Each names a state and what decides it: conditions 1 and 2 have a test the component owns and a reviewer for what the test cannot see, and conditions 3 and 4 have a reviewer. The final section says why that makes this a judgment rule. `docs/client-logic.md` explains what each condition prevents, how the tests are built, and the cases that look like client logic and are not.

The subject is placement. A client's decision lives in the installation's repository, where the client can read it, change it and review the change, and never inside the code of a platform every installation shares. Code is reviewed as code, by people who do not own the decision, and the next installation inherits it.

Three terms, used in the same sense throughout.

- **Platform code** is every component the platform ships to more than one installation — a service, a worker, a gateway, a shell, a shared package — and the platform-side tooling of an installation repository. Tooling is platform-side when it came from the platform's template, or when it produces or loads an input that a component's schema or port defines. A derivation script that writes a component's input is platform-side; a screen of the installation's own app is not.
- **An installation** is one client's deployment of the platform, with its own repository.
- **Client logic** is a decision that belongs to one client: how its vocabulary maps onto the platform's, which account, business unit, product or label is which, and any default that holds for that client and not for the platform.

## Conditions

1. **No platform code holds client logic.** Three states are forbidden in it: a translation table whose pairing is one installation's decision; a branch on installation identity, in any form (`if installation == …`, a match on a tenant name, a lookup keyed by one); and a literal account, business-unit, product or label value that only one installation uses. The detector is a test the component owns and publishes with each release. It takes a set of declarations and a source root, extracts the names and identifiers the installation introduces, and fails when one of them appears in the source outside the declaration files. The threshold is zero. Each installation runs it in its pipeline against its own declarations, over the component version it pins and over its own platform-side tooling. In the component's own pull request the test has only synthetic declarations and cannot match, so there a reviewer is the gate and the installation's pipeline is the backstop. A reviewer also decides what the test cannot see: a mapping whose keys and values are both vendor or platform vocabulary, a value the installation has not declared yet, and a branch that tests identity without naming it.

2. **A client's rule arrives as a declaration.** A declaration is a file in the installation's repository, validated against a schema the platform owns, and changed only by pull request. Three states fail: a rule the platform reads from anywhere else (an environment variable no schema covers, a database row edited by hand, a file in the component's own repository); a schema that lives in the installation rather than in the platform; and a loader that reads a declaration without validating it. Decided by a test in the component that hands the loader an invalid declaration and expects a rejection naming the field, and by a reviewer reading the loader.

3. **Client code arrives by dependency injection, and only that way.** When a rule cannot be stated as data, the platform defines a port, the installation provides the implementation, and the platform calls what it was given without knowing what it is. A port is an interface in process, or a contract the platform owns across a process boundary, which `rules/contract-first.md` governs. The binding is the installation's: its composition root, or, for a component deployed as a service, an entry point or endpoint the installation names in a declaration. Three states fail: platform code importing a module from an installation; a port declared on the installation side that the platform conforms to; and platform code that inspects the injected implementation's concrete type to choose behaviour. Decided by a reviewer, and by a search of the component for the installation's package names. No detector ships for it here.

4. **Nothing else.** A client difference that reaches platform behaviour by any route other than conditions 2 and 3 fails. The routes that get proposed are a fork of a component per client, a branch of a component's repository per installation, a patch applied at deploy time, a feature flag named for or set by one client outside a declaration, and a vendored copy of platform code edited in the installation. Decided by a reviewer.

## How this relates to dependency inversion

Condition 6 of `rules/solid.md` is about layering: which modules of one codebase may import which, gated by the abstraction trigger in `rules/yagni.md`. This rule is about placement: whose repository a decision lives in. It is not gated, and one client is enough. That condition's single-adapter remedy is not open here, because it would put a client's code in the platform, which is the state condition 1 forbids. Conditions 1 and 4 of `rules/yagni.md` do not reach the port in condition 3 or the schema field in condition 2: the alternative to either is not less structure, it is client logic in platform code. `docs/client-logic.md` works the difference through.

## Where this stops

**A vendor's own vocabulary is not client logic.** An adapter for a payment provider or an ERP knows that provider's statuses and fields, and every installation that uses the provider gets the same adapter. The mapping from that vocabulary onto the platform's is client logic when two installations would map it differently. The test cannot see that pairing, because both sides are shared vocabulary; the reviewer's question is whether a second installation would write the same table.

**The platform's own vocabulary is not client logic.** The canonical statuses, the schema's field names, and a default that holds for every installation belong to the platform. The test in condition 1 extracts only what the installation introduces, never a canonical value or a vendor's.

**The installation's own application is out of scope.** An installation can hold any code that is about its client, in its own apps and workers. This rule governs platform code as defined above.

**Test fixtures in a component are synthetic.** A component tests its loader and its ports with declarations and implementations written for the test. A real installation's values in a component's fixtures are condition 1's state.

**A literal that identifies a client is two findings.** Condition 5 of `rules/domain-model.md` forbids a client name or identifier as a literal anywhere in a tree, and condition 1 here forbids client logic in platform code. Both fire on a client's account number in a component, and the project's personal-data scanner decides the identifying subset.

**Condition 1's test sees literals.** It does not see a rule encoded in structure — an ordering, a threshold, a computed key. A short or common value collides with ordinary code, so `docs/client-logic.md` sets a minimum length and an exception list.

**Moving existing logic out of code is not this rule's work.** The rule describes the state a change must not add. Code that already holds client logic is a finding outside the diff, and the move is tracked as its own issue.

**This rule declares judgment rather than a hook, and the reason is not effort.** The tests in conditions 1 and 2 are real, and they need inputs this plugin cannot have: a component's source layout, its loader, and an installation's declarations. All of them live in other repositories. Conditions 3 and 4 need a reader who can see the wiring and the deploy. So the rule takes the judgment route, its statement is injected, and the tests are jobs each component owns. `rules/contract-first.md` takes the same route for the same reason.
