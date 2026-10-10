# The decision log

Every decision this repository has made gets a row here. A row that earns more gets a record in this directory, and the row stays and points at it. [`contributing/docs/decision-records.md`](../../contributing/docs/decision-records.md) gives the three questions that decide which, and [`contributing/rules/decision-records.md`](../../contributing/rules/decision-records.md) gives the shape a record must hold.

This file is the index `check-decision-records.py` allows by name. It moved here from `ROADMAP.md` when that file was retired ([ADR-005](ADR-005-github-holds-the-work-inventory.md)). The rows are unchanged; where the work they mention is tracked is now the issue each one cites.

## Records

| Record | Decision |
|---|---|
| [ADR-001](ADR-001-pull-requests-land-as-a-squash.md) | Pull requests land on trunk as a squash |
| [ADR-002](ADR-002-enforcement-admits-a-forge-tier.md) | Enforcement admits a forge tier |
| [ADR-003](ADR-003-idd-builds-the-specification-system.md) | Issue-driven development builds the specification system |
| [ADR-004](ADR-004-a-plan-is-an-artifact.md) | A plan is an artifact, held in a sub-issue. Superseded by ADR-011 |
| [ADR-005](ADR-005-github-holds-the-work-inventory.md) | GitHub holds the work inventory, and `ROADMAP.md` is retired |
| [ADR-006](ADR-006-a-stack-is-read-from-its-bases.md) | A stack is read from its bases, and no tool or flag is adopted. Superseded by ADR-008 |
| [ADR-007](ADR-007-acceptance-criteria-live-in-the-issue.md) | Acceptance criteria live in the issue, and a test names the one it covers |
| [ADR-008](ADR-008-native-stacks-first-the-framework-runs-the-rest.md) | Native stacks where the forge has them, and the framework runs the stack where it does not |
| [ADR-009](ADR-009-two-gates-and-a-person-lands-the-change.md) | Two gates, scope and quality, and a person lands the change |
| [ADR-010](ADR-010-a-fork-syncs-through-a-merge-commit.md) | A fork syncs its parent through a merge commit, and the gates judge only what the fork brings |
| [ADR-011](ADR-011-a-plan-is-its-units-as-sub-issues.md) | A plan is its units, as sub-issues ordered by the forge's native dependencies |
| [ADR-012](ADR-012-the-repositorys-issue-templates-first.md) | The repository's issue templates first, and Ahrena's forms, adapted from the predecessor's, by default |
| [ADR-013](ADR-013-a-clean-review-approves-and-the-forge-lands-it.md) | A clean review approves on the first pass, and the forge lands it; supersedes ADR-009 |
| [ADR-014](ADR-014-a-separate-agent-applies-the-fixes.md) | A separate agent (Hephaestus) applies the review's fixes, and the review runs again before landing |

## Decided, as rows

The eleven decisions that predate the log. `contributing/docs/decision-records.md` works the three questions against each of them: six records would cover seven of them, and none has been written yet, because a record is written when a decision is made and not backfilled.

| Decision | Consequence |
|---|---|
| The Ahrena MCP server is dropped | 1,268 lines of Python, three artifacts, and the second `.directives` parser all go |
| Capability arrives as a skill, not an MCP server | An MCP server's tool definitions sit in the always-loaded tier; a skill costs its `description` |
| The framework does not own MCP configuration | Four platforms already declare MCP servers in their own manifests. A framework key listing them is a fifth source of truth that can disagree with the four real ones |
| Persona names are allowed on agents, and nowhere else | `name` is the handle, `role` is the subject |
| References carry no verb | The pair of types already determines it |
| MCP transport is ordered: remote HTTP, then a vendor binary, then npx, with Docker undecided | The predecessor already wrote this as `lex-mcp` section 5, with the same reasoning. The vendor-binary tier is the one worth recovering, because a binary needs no Node |
| A hook whose tests are not in CI is not trusted | All three suites run in `validate.yml`, tests before the corpus check |
| A rule may require the consuming project to adopt a library, when the condition does not exist without one | The no-dependency constraint is about the hooks, which run on a consumer's machine with nothing installed. It was never about what a rule may ask of the project it governs. This reopens the verified-property condition and gives explicit contracts a real mechanism; `lex-python-result-type` stays dropped on its merits rather than for naming `returns` |
| Correctness is four families, and it gates "deployable" | Explicit contract, totality, verified property, trace to a requirement. Totality is fully AST-decidable and ships first; explicit contract is the half no mainstream platform hands us, so the condition names a mechanism rather than a keyword; trace waits on the requirement vocabulary that row B would define. Registered as Q9 in [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) |
| A reference crosses plugins as `<marketplace-name>:<plugin-relative-path>`, and a body link crosses as an ordinary relative path | Two forms, because they are two different things. A declared reference is a load edge, so it is addressed by the identity that survives installation rather than by a path that resolves only in this repository; the matrix applies unchanged across the boundary, and the plugin graph those edges form must be acyclic. A body link is documentation, resolves from the file, opens on GitHub, and is how a rule cites a rule — the case the matrix refuses and always will, because a rule that drags another rule into context has doubled the cost of both. `pilars.md` conditions 7 and 8; `module-boundaries.md` stopped restating SOLID's sixth condition and links it |
| The concept is resource discipline, not memory safety | Python is memory-safe by construction, so a rule under that name fires on nothing here and means something else in C. What the platform withholds is deterministic release and bounded consumption: a resource acquired without the language's own release mechanism, an accumulator or pool with no ceiling, a collection materialised where iteration would do. Registered as Q10 in [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) |

## Refused

From the predecessor's 139 foundation artifacts, these did not come across. They are decisions too, and the same test keeps all four as rows. The process row is narrower than it reads: #45 found that it refused the plan-cache machinery, not issue-driven development, and ADR-003 and ADR-004 build what it left out.

| Group | Count | Why |
|---|---|---|
| tooling | 33 | Make targets, the Ahrena MCP, git-spice, graphify, cost tracking. Maintainer infrastructure (#16) |
| process, planning and checkpoint | 26 | 980 lines in the two planning artifacts alone, bound to worktrees, labels, plan sub-issues and heartbeats |
| i18n | 2 | English-only (#2) |
| `lex-logging-decorator`, `lex-observability-required` | 2 | Engineering, not foundation (#13) |
