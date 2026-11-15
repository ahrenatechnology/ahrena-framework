---
id: linting
type: rule
clade: engineering
subclade: quality
title: A change passes the linters and does not silence them
statement: A change passes every linter, the formatter and the type checker, silences no rule without a pointer, and loosens no configuration it needs.
enforcement: judgment
references:
  - docs/linting.md
---

# A change passes the linters and does not silence them

Three conditions about static checks. They are the same in every language; what differs is the tool, and [`docs/linting.md`](../docs/linting.md) lists the usual one per language and says where the zero thresholds come from. Each condition carries its catalog id from the PR quality rubric (epic 323).

## Conditions

1. **LNT-1: the pull request passes every linter, the formatter and the type checker of its language, with the configuration versioned in the repository.** The threshold is 0 errors and 0 new warnings. Decided by running the project's own commands in the pipeline and failing on a non-zero exit, and by counting warnings with the linter's machine-readable output on the base and on the head and failing when the head count is higher. A project with no linter configured fails the condition with that finding, because a check that does not run passes nothing. The configuration must be a file in the repository; a setting that lives only in a developer's editor does not count.

2. **LNT-2: no line the pull request adds switches a lint or type rule off without a pointer.** The markers are `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `nolint`, `# noqa`, `# type: ignore` and the equivalents of the language. A pointer is `#N` or `ADR-N`, as `engineering/fundamentals/rules/comment-pointers.md` spells them, on the same line or the line above. The threshold is 0 without a pointer. Decided by a search over the added lines of the diff.

3. **LNT-3: a pull request that changes code does not also loosen the linter configuration it would otherwise fail.** Loosening is turning a rule off, lowering its severity, widening an ignore list, or raising a limit. The threshold is 0. Decided by a diff of the configuration files: a loosening in a pull request that also changes code under the rule it loosened is reported. A pull request that only changes the configuration is read by a reviewer.

## Where this stops

**Passing the linter is not the same as the code being clear.** The rules a linter holds are the project's choice, and a weak configuration passes weak code. LNT-3 only stops the configuration being weakened to fit a change; it does not judge the configuration.

**A pointer is checked for presence, not for truth.** The condition reads that the line names an issue or a decision, not that the issue justifies the switch. A reviewer reads the pointer.

**Warnings that existed before the change do not fail it.** Only a warning the change introduces counts, so a legacy tree is not blocked; the count of existing warnings may not rise.

**Generated files are outside the condition.** The project excludes them by path in the linter configuration, and that exclusion is itself held by LNT-3.

**No detector ships with this rule.** The scripts for LNT-1 to LNT-3 are #332's, and until they land a reviewer reads the linter output and the diff.
