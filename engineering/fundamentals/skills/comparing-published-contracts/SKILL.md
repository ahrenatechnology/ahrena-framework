---
name: comparing-published-contracts
description: Use when a service can be started and the question is whether the description it serves is still the committed contract. Fetch it, canonicalise both sides, compare them, and wire the comparison into the pipeline.
type: skill
clade: engineering
subclade: architecture
references:
  - rules/contract-first.md
  - docs/contract-first.md
  - docs/review-findings.md
  - skills/authoring-contracts/SKILL.md
  - skills/detecting-contract-breaks/SKILL.md
  - skills/reviewing-diffs/SKILL.md
---

# Comparing published contracts

Condition 2 of `rules/contract-first.md` requires the published contract and the committed contract to be byte-equal after canonical serialisation. The rule names what decides it, a pipeline job that starts the service and compares, and ships no such job, because the two things the job needs are a start command and an address. This is the procedure around those two inputs.

It is also the rule's fallback. Where a framework can only describe a surface from its handlers, the rule's boundary section keeps the property that matters by comparing the generated description with a document a person edits. That comparison is this one, unchanged.

## 1. Name the two documents, and stop if there is only one

**The committed contract** is a file in the tree: the document `skills/authoring-contracts/SKILL.md` produced, or whichever one the team reviews.

**The published description** is what the running service hands a consumer who asks: an OpenAPI document at a path, an AsyncAPI document, a schema a registry returns for a subject. Write down the address and the command that starts the service. Both come from the project, and a guessed address is a comparison against the wrong thing.

A surface that serves no description has no second document. A library's exported symbols, a command line's arguments and a database schema another team reads are contracts, and the rule's boundary section says the condition does not reach them. Stop there and report that the condition was not reached and why. That is a result, and it is a different one from a pass.

## 2. Start the service the way the pipeline starts it, and fetch

Use the command the project itself declares, with the configuration the contract tests run under. A description served by a differently configured build is a third document.

```sh
curl --fail --silent --show-error "$DESCRIPTION_URL" --output published.json
```

`--fail` is what turns an error page into a failed step. Without it the comparison in step 4 runs against the body of a 404 and reports that body as not JSON, which is true and sends the reader to the wrong problem.

During a review, starting the service is execution of the change author's code. Step 1 of `skills/reviewing-diffs/SKILL.md` decides whether that is permitted. Where it is not, this procedure ends here with one `unchecked` finding that names condition 2.

## 3. Bring both sides to JSON, and change nothing else

The comparison reads JSON. A committed contract kept as YAML is converted with the project's own toolchain, and the conversion is the only transformation either side goes through.

Do not strip anything first. Removing descriptions, examples or a server list before comparing is a tolerance, and [`docs/contract-first.md`](../../docs/contract-first.md) argues why a tolerance is where drift accumulates. A field the framework injects at run time is a real difference between what was reviewed and what is served. It is settled by writing it into the committed contract or by stopping the injection.

## 4. Compare

```sh
python3 scripts/diff-contract.py committed.json published.json
```

Canonical serialisation is object keys sorted and whitespace normalised, so formatting is not a difference. Everything else is: an array in another order, `100` against `100.0`, one added optional field.

| Exit | Meaning |
|---|---|
| 0 | the two are equal |
| 1 | they differ, and each difference is printed with its JSON Pointer and the side it is on |
| 2 | one of them could not be read, so nothing was compared |

`scripts/test-diff-contract.py` is the suite, and it pins each of the cases above.

## 5. Decide which side is wrong, and fix that side

A difference has two causes and the output does not say which.

**The implementation drifted.** The contract still says what was agreed and the service stopped doing it. The code is wrong and the code changes.

**The surface was changed in the code first.** The service does what somebody now wants and the contract was never told. The contract is edited by hand, through step 8 of `skills/authoring-contracts/SKILL.md`, and reviewed as the change it is.

Never settle a difference by writing the published description over the committed file. That is the generation direction condition 1 forbids, and it turns the comparison into one that passes by construction.

## 6. Wire it into the pipeline, where exit 2 fails as well

The comparison belongs in the job that already starts the service for the contract tests, on every change, after the fetch. It adds no dependency and one step.

Treat exit 2 as a failure of the job. A description that could not be fetched or read was not compared, and a pipeline that reads "not compared" as green has a gate that passes by seeing nothing.

In a review, report the outcome by the tests in `docs/review-findings.md`. A difference introduced by the change under review is **blocking** and cites condition 2 with the pointer. One that was already on the base is **deferrable**. A comparison that could not run is **unchecked**, with the reason.

## When this skill does not apply

**A surface with no machine-readable description.** Step 1 ends there. The property survives and the detector does not, which means a reviewer.

**Comparing two versions of the committed contract.** Whether an edit removes or narrows something, and whether it ships as a version, is `skills/detecting-contract-breaks/SKILL.md`. Its two documents are the base and the head. This procedure's two are the head and the running service.

**A comparison that forgives some differences.** A semantic diff that ignores additions or descriptions answers a different question, and the rule chose equality on purpose. A project that wants one runs it beside this, not in place of it.

**Checking that the service behaves as the contract says.** Two equal documents show that the service describes itself as agreed. Whether each operation does what its description claims is conditions 3 and 4, and the contract tests decide those.
