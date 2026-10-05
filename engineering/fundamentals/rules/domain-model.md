---
id: domain-model
type: rule
clade: engineering
subclade: architecture
title: The domain owns its vocabulary
statement: A domain module imports no mechanism and names no vendor, an aggregate root declares identity and an audit stamp, and no client datum is a literal.
enforcement: judgment
references:
  - docs/bounded-contexts.md
  - docs/clean-code.md
---

# The domain owns its vocabulary

Five conditions. The first two are decided by `hooks/check-structure.py`; the last three need a marker the project supplies, a scanner it runs, or a reviewer, and the final section says why that makes this a judgment rule. `docs/bounded-contexts.md` explains what each condition protects, where the layout came from, and what the guardrails cost when they are wrong.

The subject is a single claim: a domain model is the one part of a system whose vocabulary is not negotiable with anything outside it. A model that mentions the database it is stored in, the format it is serialised to, the library it happens to use, or the customer it was first built for has stopped being a model of the business and become a model of this deployment of it. Everything below follows from that.

**This rule supplies the layer map.** Condition 6 of `rules/solid.md` needs a partition of modules into policy and mechanism and states that the plugin ships none; `docs/simplicity.md` records the same gap twice. Condition 1 here closes it by declaring the layout rather than asking for a map: a bounded context is a directory, `domain/` inside it is policy, and `adapters/`, `infrastructure/` and `persistence/` are mechanism. That is a convention, and the reason to state one is that a convention is checkable where a description is not.

No condition here adds an abstraction, so the abstraction trigger in condition 1 of `rules/yagni.md` does not gate any of them. The port that condition 1 usually implies is gated, and that gating already lives in condition 6 of `rules/solid.md` and in the port entry of `docs/patterns.md`, so it is not repeated here.

## Conditions

1. **A module under a context's `domain/` directory imports no mechanism.** Two states are forbidden: an import whose dotted path contains `adapters`, `adapter`, `infrastructure`, `infra` or `persistence`, whether absolute or relative; and an import whose top-level package is a transport, a driver, a web framework or a numeric runtime. The second list holds packages that are mechanism whatever they are imported for and deliberately excludes the standard library modules a domain legitimately uses — `datetime`, `decimal`, `uuid`, `enum`. Decided by `hooks/check-structure.py` for Python, and by a reviewer elsewhere.

2. **A name declared under `domain/` carries no vendor or technique token.** The state is a module filename, class, function or annotated field whose name, split on snake_case and camelCase boundaries, contains a token naming a product, a protocol, a serialisation format or a layering technique — `sql`, `redis`, `kafka`, `http`, `json`, `dto`, `dao`, `orm`, `impl` and the rest of a closed list the script carries. `docs/clean-code.md` refuses a list of generic nouns for naming, and this list is admissible for the reason that one is not: each token denotes something the domain does not contain, so a match is a domain name pointing outward rather than a word whose correctness depends on context. Decided by `hooks/check-structure.py` for Python, and by a reviewer elsewhere.

3. **An aggregate root declares its identity, and a persisted entity declares an audit stamp.** The identity is one field, declared on the root and not on the entities inside it, because the root is what the outside world addresses. The stamp is exactly four fields — created-at, created-by, updated-at, updated-by — which are the two questions an audit trail is asked, asked about the two events every record has. A deleted-at field is not in the set, because soft deletion is a storage decision and putting it in the contract makes every domain that does not soft-delete carry a field that is always empty. Decided by a reviewer, or by a script once the project names the base type its aggregates inherit.

4. **The attribute naming which domain concept a record represents is `domain_entity`.** `entity_type` is the superseded spelling and does not appear. The two are not interchangeable: `entity_type` pairs a domain noun with a schema noun and reads as metadata about a row, which is why it attracts every other classification anyone later needs; `domain_entity` names the thing the record is. Decided by a reviewer, and by a search over the tree that returns nothing.

5. **No client name, organisation identifier or personal datum appears as a literal in the tree.** The state is a customer's name, an account or tenant identifier, an email address, a national identity number or any other personal datum written into source, a test fixture, a migration, a seed file or a comment. A tenant is a runtime value; a client's name is configuration or test data generated for the purpose. Decided by the project's secret and personal-data scanner in the pipeline, and by a reviewer for the shapes no pattern catches.

## Where this stops

**Condition 1 does not reach a tree with no `domain/` directory.** The detector finds the layer by the directory name, so a project that lays its contexts out differently gets nothing from it. That is the cost of a convention over a configuration, and it is the right cost here: a configurable layer map is a file that drifts from the layout, and the drift is invisible until the check has been passing on the wrong partition for a year. A project with another layout supplies the map to a reviewer, which is where condition 6 of `rules/solid.md` already left it.

**Condition 1 does not reach an import the domain needs and the list happens to name.** A domain about web traffic imports `http` legitimately, and one about statistical models may genuinely be built on `numpy`. Those are the cases the next paragraph covers, and the answer is the same: exclude by path, once, in writing.

**Condition 2 stops where the technology is the domain.** A monitoring product's domain contains an `HttpProbe`; a data-integration product's domain contains a `CsvSchema`; a database vendor's domain contains `Sql`. In those systems the token is the business's own word and the condition is simply wrong. This is the carve-out the whole condition depends on, so it is stated first rather than last: the list is not a claim that these words are bad, it is a claim that in most domains they name something outside. Exclude the context by path and write down why.

**Condition 2 does not reach the name that matters most.** A domain type called `Order` that models a database row, with a field per column and no behaviour, passes every token check and is the defect the rule is actually about. A vendor token is the visible end of a leak; the invisible end is a model shaped by the storage without ever mentioning it, and no list finds that. A reviewer asking whether the domain expert would recognise the type does.

**Condition 3 does not reach a value object.** A value has no identity by definition, so requiring one of it is a category error, and condition 5 of `rules/value-semantics.md` covers the separate question of whether a value behaves like one. Nor does it reach an entity that is never persisted: an audit stamp records who changed a stored record, and a domain object that lives only inside one computation has nothing to stamp.

**Condition 3 does not require the stamp to be mandatory on every read path.** A projection, a read model and an event payload carry what their consumer needs, and copying four audit fields into each of them is how a stamp becomes noise. The contract binds the persisted aggregate, not everything derived from it.

**Condition 4 settles a spelling and nothing else.** It does not say that a record should carry such an attribute at all; a model that needs no discriminator should have none, and a single-table design that needs one has usually made a storage decision that leaked into the model — which is condition 2's subject. The condition exists because the two spellings were both in use and a corpus with two names for one concept costs more than either name does.

**Condition 5 does not reach data the system is about.** A domain whose subject is people holds personal data at runtime, and that is the system working. The condition is about literals: a name, an account number or an address written into the source, where it cannot be rotated, cannot be scoped, outlives the relationship it came from, and travels to everyone who clones the repository. The distinction is between data that flows through the system and data that is part of it.

**Condition 5 does not reach a public identifier the system must hard-code.** A regulator's registration number, a well-known public endpoint and a statutory code are facts about the world rather than about a client, and treating them as secrets makes the code worse. The test is whether the value identifies a particular customer of this system.

**This rule declares judgment rather than a hook, although two of its five conditions have a script.** Conditions 3, 4 and 5 need a marker the project names, a search someone reads, or a scanner the project runs, and `enforcement` decides how a rule reaches an agent: a hook rule is replaced by its script and contributes no text, a judgment rule contributes its statement. Declaring a hook here would deliver the two shapes a parser can see and silently drop the entity contract, the naming decision and the personal-data guardrail — of which the last is the one with the largest consequence when it is missed. The script still exists and conditions 1 and 2 name it, so a reviewer and a pipeline can both run it; what it does not do is stand in for the rule. `rules/solid.md` takes the same route for the same reason and its final section sets out the trade.

**The two shipped detectors are unproven against real code.** The framework's own Python has no `domain/` directory, so running them over it returns zero findings and that number means nothing. What backs them is the fixture suite in `hooks/test-check-structure.py`, which pins both directions of each condition, and the carve-outs above. `rules/cross-cutting-concerns.md` carries the same caveat for the same reason, and `docs/bounded-contexts.md` says what would change it.

**The detector parses Python and nothing else.** The standard library ships one parser and this plugin takes no dependencies. The layout condition is the most portable of the two — a directory is a directory in any language — and a detector for another language belongs with the plugin for it.
