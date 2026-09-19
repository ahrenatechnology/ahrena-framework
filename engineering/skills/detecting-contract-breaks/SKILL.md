---
name: detecting-contract-breaks
description: Use when a change touches a published contract, event envelope or exported symbol set and the question is whether a consumer breaks and whether the change ships as a version.
type: skill
clade: engineering
subclade: architecture
references:
  - rules/contract-first.md
  - rules/aggregates.md
  - docs/contract-first.md
  - docs/review-findings.md
---

# Detecting contract breaks

Every other review axis reads the diff. This one cannot: a break is a relation between two versions of a published surface, and the previous version is not in the diff. It is a separate procedure because its input is separate — the base version of each surface has to be fetched before anything can be classified.

Condition 5 of `rules/contract-first.md` supplies the classification set. This procedure applies it and decides nothing new about what counts as a break.

## 1. List the published surfaces this change touches

A surface is published when someone outside the team that owns it can depend on it without asking. Four kinds, and the change touches a surface if it touches any file that defines one.

| Surface | Where the change shows up |
|---|---|
| a machine-readable contract | an OpenAPI, AsyncAPI, JSON Schema, protobuf or Avro document in the tree |
| an event | an event type, its envelope attributes, or the payload fields declared for it |
| an exported symbol set | a module's declared public surface, or an index that re-exports one |
| a shared schema | a migration against a database another team reads, or a table it queries |

A surface with no reader outside this repository is not published, and the boundary case is argued in `docs/contract-first.md`: the test is whether anyone outside the team can subscribe, call or import it without coordinating first. Internal boundaries are read by `skills/reviewing-diffs/SKILL.md` under the ordinary quality conditions, not here.

If the list is empty, stop and say so. An empty list is a result.

## 2. Fetch the base version of each surface

The base version is the surface as it stands on the commit this change merges into, which is the version live consumers are compiled or coded against. Take it from there, not from the last release tag, unless the surface itself is versioned by tag and consumers pin to it — in which case the pinned version is the base and the tag is the thing to read.

Three cases that are not breaks and are mistaken for them:

- **The surface is new in this change.** There is no base and nothing can break. Note it and move on.
- **The surface moved.** A contract document renamed or relocated with identical contents is a base that has to be matched by contents rather than by path.
- **The base cannot be fetched.** A surface published from somewhere this procedure cannot read is an `unchecked` finding naming the surface and why, not a silent pass.

Fetching a document and reading it executes nothing, so this step runs whether or not step 1 of `skills/reviewing-diffs/SKILL.md` permitted execution.

## 3. Classify each difference against the breaking set

Compare base to head, one surface at a time. The set is condition 5 of `rules/contract-first.md`, taken from the schema-diff tools rather than invented, plus what the other two kinds of surface add.

**On a contract:** an operation deleted; a field removed from a response; a field added as required to a request; an enum value removed; a type narrowed. Narrowing includes a tightened range, a shortened maximum length, a widened required set and an optional field made mandatory.

**On an event:** everything above against the payload, plus a CloudEvents required attribute removed from the envelope, plus an event type renamed. Condition 5 of `rules/aggregates.md` requires the root identity and the time on every domain event, so removing either is both a break and a violation of that condition, and it is reported once against the more specific of the two.

**On an exported symbol set:** a symbol removed, renamed, or moved to a different module. A signature narrowed — a parameter added without a default, a return type narrowed, an exception newly raised where the previous version handled it.

**On a shared schema:** a column or table dropped or renamed, a type narrowed, a constraint added that existing rows can violate, a default removed.

Everything else is an addition, and additions are not breaks. Resist the pull to report them: a review that flags every added optional field trains its reader to skim.

## 4. Decide whether the change ships as a version event

Condition 5 requires that a break be a version event — announced, dated and visible to consumers — and deliberately does not decide the mechanism. A path version, a header negotiation, a registry compatibility mode and a date-stamped revision all satisfy it.

So ask only two things. Does the change carry a version event of any of those shapes, and does the event reach the consumers of this particular surface. A version bumped on the package while the contract document is edited in place has versioned the wrong thing.

A break with a version event is correct and is not a finding. A break without one is the finding, and the finding is the missing version rather than the break.

## 5. Separate the breaks that are correct

Two cases, both from the boundary section of `rules/contract-first.md`, and both look identical to step 3.

**The contract documented behaviour the service never had.** Narrowing it to match reality is a fix, and versioning it would preserve a fiction nobody implements. It still ships as a version event, because consumers may have coded against the fiction.

**The symbol was never really public.** A module exports a name that nothing outside the repository imports, and the export was an accident of layout. Removing it breaks nobody. This is the case nothing in the tree can decide — `rules/yagni.md` says in its own boundary section that a published surface has consumers the tree cannot see, and the count therefore returns the wrong answer.

## 6. Assign a severity

Apply the tests in `docs/review-findings.md`.

**Blocking** is a break in the classification set with no version event carrying it. That is condition 5 of `rules/contract-first.md` violated by a line in this diff, and it names the contract, the operation or field, and the base version it differs from.

**Question** is the case step 5 ends on: a removal or rename whose consumers are outside this repository, where the reviewer can see the change but not who it breaks. Name the symbol, name the base version, and say what would settle it — the consumer list, or a statement that the surface was never published.

**Unchecked** is a surface whose base version step 2 could not fetch, and conditions 2, 3 and 4 of `rules/contract-first.md` whenever execution was not permitted — the served-description diff, the test per declared operation and the envelope validation inside it all need the service running.

**Deferrable** is rare here and worth stating: a break that is already live, introduced by an earlier commit and merely carried along by this diff, is not this change's to fix.

## When this skill does not apply

**An internal interface with one caller in the same deployment unit.** It is not published, nothing outside can be broken by it, and `docs/contract-first.md` names this as the case where the whole contract-first argument gives way to the abstraction trigger.

**Choosing the versioning scheme.** Condition 5 requires a version event and declines to pick the mechanism. A review that argues for header negotiation over path versions has left the rule behind and is stating a preference.

**Designing the migration path.** Running two versions at once, a deprecation window, a consumer-driven contract suite and registry compatibility modes are how a break is carried safely, and `docs/contract-first.md` records that it does not cover them. This procedure detects the break and checks for the version event; how the surface gets from one version to the next is the owner's design.

**A change with no published surface in it.** Step 1 returning an empty list is the answer, not a reason to loosen the definition until something qualifies.
