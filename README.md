# Ahrena Framework

Operating artifacts for AI coding agents — rules, reference docs, skills, agents and commands — distributed as a plugin.

This is the successor to a framework that has been in production use. Most of what that framework established carries over: the clade taxonomy, the five artifact types with a declared authority hierarchy, the addressing convention, the artifact templates, and the issue-driven development flow.

What changes is scoped and deliberate:

- **One language.** English, everywhere. No parallel language trees to keep in sync.
- **Platform nomenclature.** `rules`, `docs`, `skills`, `agents`, `commands` — the names the tooling already uses.
- **A validated graph.** Artifacts reference each other through edges that CI resolves. A reference to something that does not exist fails the build.
- **Skills with bodies.** `references/` and `scripts/` alongside `SKILL.md`, so a procedure is executed rather than paraphrased.
- **Company-agnostic content.** Brand, design system and platform namespaces are parameterized or live in an overlay.
- **Development scope.** Discovery and delivery artifacts are out for now.
- **Engineering fundamentals first.** SOLID, KISS, YAGNI, clean code, DDD, module boundaries — stated as checkable conditions with thresholds, not as maxims.

## Status

Architecture in definition. The work is tracked in the issues of this repository.

## License

See [LICENSE](LICENSE).
