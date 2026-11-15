---
id: test-discipline
type: rule
clade: engineering
subclade: fundamentals
title: Tests sit beside the code, come first and trace to the criteria
statement: A code file has its unit test beside it, the test is committed red before the code that passes it, and every acceptance criterion is named by a test.
enforcement: judgment
references:
  - docs/test-discipline.md
---

# Tests sit beside the code, come first and trace to the criteria

Three conditions that hold in every language. The language plugins already hold the first one for their own files (`typescript/colocated-tests`, `go/test-placement`, `python/test-placement`, `terraform/test-placement`); where a language plugin has a rule, that rule decides TST-1 for its files, its exemptions included (a Python module of types only still owes its test); this rule decides it for every other language. [`docs/test-discipline.md`](../docs/test-discipline.md) gives the reasons and says where each figure comes from.

Each condition carries its catalog id from the PR quality rubric (epic 323), so a detector and a finding can name it.

## Conditions

1. **TST-1: every code file that declares behaviour has its unit test in the same folder with the same name.** `model.ts` is answered by `model.test.ts`, `model.go` by `model_test.go`, `model.py` by `model_test.py`. A test in a separate `test/` tree does not count. The threshold is 100% of the files the pull request adds or changes, and the legacy tree is not held to it. A file that declares only types, constants or re-exports owes no test. Decided by the language plugin's hook where one exists, and elsewhere by a script the consuming project runs that lists the code files of the diff and the test files beside them.

2. **TST-2: the test is committed before the code that makes it pass.** The state is a branch whose history holds a commit where the new test fails and a later commit where it passes. Decided by a pipeline job that checks out the commit that adds the test, runs it, and expects a failure, then runs it again at the head and expects a pass. The threshold is presence: one red commit and one green commit for the new test. A pull request that adds no behaviour is exempt.

3. **TST-3: every live acceptance criterion of the issue is named by a test.** The threshold is 100%. A criterion ending in `(checked by review)` or marked removed is not live. Decided by `contributing/rules/traceability.md`, which owns the detector; this condition adds no second one.

## Where this stops

**TST-1 reads that a test file exists, not what it asserts.** An empty `model.test.ts` answers it. What the test must prove is TST-3 for behaviour and `engineering/quality/rules/coverage-by-layer.md` for lines and mutants.

**TST-1 does not reach a test that crosses units.** An integration test of an adapter, an end-to-end test and a contract test live where `rules/contract-tests.md` and the language plugin's testing doc put them. None of them answers TST-1 for a file it was not named for.

**TST-2 cannot be decided on a squashed branch.** The pipeline reads the branch's own commits, so a pull request opened from a single squashed commit shows no red step and is decided by a reviewer reading the test and the diff. A change to configuration, documentation or a rename adds no behaviour and is exempt.

**TST-3 is traceability, not sufficiency.** A criterion named in a test is exercised somewhere; whether the test would fail if the behaviour broke is the mutation score of the domain.

**The detectors that do not exist yet belong to #332.** TST-3 is already decided by the traceability hook and TST-1 by each language plugin's hook where one exists; the rest, TST-1 for other languages and TST-2, is #332's, and until it lands a reviewer reads them.
