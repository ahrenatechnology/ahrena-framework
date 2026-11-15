---
id: coverage-by-layer
type: rule
clade: engineering
subclade: quality
title: Coverage is held by layer, and the domain is also mutated
statement: New lines are 90% covered, the project 80% and not falling, the domain 100% with 80% of mutants killed, the edge 75%, read through the layer map.
enforcement: judgment
references:
  - docs/coverage-by-layer.md
---

# Coverage is held by layer, and the domain is also mutated

Five conditions, each a figure a coverage report or a mutation run produces and a pipeline compares. The layers are those of the project's layer map (STR-4 of the PR quality rubric, epic 323): domain, use case, edge and composition root. A project with no layer map cannot answer COV-3, COV-4 or COV-5 and fails them as unchecked with that finding, never as passed. [`docs/coverage-by-layer.md`](../docs/coverage-by-layer.md) gives the origin of each figure and why coverage alone does not hold the domain.

COV-1 applies to the lines a pull request adds. COV-3, COV-4 and COV-5 apply to a layer, and are decided on the files of that layer the pull request adds or changes, so a legacy layer below the figure does not block an unrelated change. COV-2 is the only whole-project figure and it may not fall.

## Conditions

1. **COV-1: at least 90% of the lines the pull request adds are covered.** Decided by crossing the coverage report's covered lines with the lines of the diff. A pull request that adds no executable line is exempt.

2. **COV-2: total line coverage of the project is at least 80% and does not fall.** Decided by comparing the report of the head with the report of the base. This is an indicator: it appears in the pull request's scoreboard and a fall is flagged, and a project already under 80% is held only to not falling.

3. **COV-3: the domain layer has 100% line coverage and 100% branch coverage.** Decided by the coverage report restricted to the changed files in the folders the layer map names as domain.

4. **COV-4: at least 80% of the mutants generated in the domain layer are killed.** Decided by a mutation-testing run over the domain folders, with Stryker for TypeScript, `go-mutesting` or Gremlins for Go, and `mutmut` or `cosmic-ray` for Python. A survivor is reported with its file and line. A pull request is held to the mutants of the files it changes.

5. **COV-5: the edge layer has at least 75% line coverage**, the edge being the folders the layer map names as API, database or integration. Decided by the coverage report restricted to the changed files in those folders. The contract and integration tests that `engineering/fundamentals/rules/contract-tests.md` requires are what bring it there.

## Where this stops

**Coverage says a line ran, not that anything checked it.** A test with no assertion covers its lines and kills no mutant. That is why COV-3 is paired with COV-4 and no other layer is mutated: the domain is where a wrong answer costs most and where 100% is reachable.

**Use cases and the composition root carry only COV-1 and COV-2.** No layer figure is declared for them because none has been measured or decided; a figure invented here would be the unattributed threshold the standard of issue 34 forbids.

**A mutant that cannot be killed is declared, not ignored.** An equivalent mutant is listed in the project's mutation configuration with a pointer to the issue or decision that records why, and the score is computed without it. An unpointed exclusion counts as a survivor.

**Generated code, vendored code and test code are outside every figure.** The project's report configuration excludes them by path.

**No detector ships with this rule.** The scripts for COV-1 to COV-5 are #332's, and until they land a reviewer reads the coverage and mutation reports.
