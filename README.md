# Ahrena Framework

Operating rules, reference docs, skills, agents and commands for AI coding agents.

This repository is a rebuild of the framework on four premises:

- **Company-agnostic.** The content serves any organization. Brand, design system and platform namespaces are parameterized or live in a company overlay, never hardcoded.
- **One language.** English, everywhere. No parallel language trees to keep in sync.
- **Official nomenclature.** `rules/`, `docs/`, `skills/`, `agents/`, `commands/` — the names the platforms already use.
- **A validated graph.** Artifacts reference each other through typed edges that CI checks. A reference to something that does not exist fails the build.

## Status

Under construction. The work is tracked in the issues of this repository, ordered by dependency.

The predecessor repository carries 337 artifacts across three language trees. Measured before the rebuild: 2,865 cross-references between artifacts, of which 112 point at artifacts that do not exist and 111 invert the authority hierarchy the framework declares for itself. Those numbers are the reason this is a rebuild and not a rename.

## The five artifact types

| Type | Directory | What it is |
|---|---|---|
| Rule | `rules/` | An unbreakable guardrail. No exceptions. |
| Doc | `docs/` | A reference manual. Informs decisions. |
| Skill | `skills/` | A repeatable procedure. Applies rules, consults docs. |
| Agent | `agents/` | A specialist that orchestrates skills. |
| Command | `commands/` | An entry point. Invokes a skill or an agent — never a rule or a doc. |

## License

See [LICENSE](LICENSE).
