# Work inventory

The index of what is queued, the decisions already made, and what was refused. **The work itself lives in GitHub issues**; this file is what an issue cannot hold — a decision that spans several of them, and a refusal nobody should have to rediscover.

It lives at the repository root rather than inside `foundation/`, because it is project state, not framework content. An artifact inside a plugin ships to every consumer and must pass the gate; a backlog does neither.

## Landed

Four plugins, **48 artifacts**, 253 test cases, six hooks, no dependency beyond the standard library.

| Plugin | Rules | Docs | Skills | Agents | What it is |
|---|---|---|---|---|---|
| `ahrena-foundation` | 5 | 2 | 3 | 1 | What an artifact is, what it may cost, when it is finished, and the gate that decides it |
| `ahrena-engineering` | 12 | 13 | 4 | 1 | Language-agnostic fundamentals with one arbitration between them, and the reviewer that applies them |
| `ahrena-engineering-python` | 2 | 2 | — | — | What is specific to one language: the import graph, and the typing a checker decides |
| `ahrena-contributing` | 2 | 1 | — | — | What governs the repository rather than the code in it |

## Queued

Every row is a GitHub issue now. This table is the index and the dependency graph; the issue carries the work, and where the two disagree the issue wins.

| Issue | Work | Touches | Blocked by |
|---|---|---|---|
| [#39](https://github.com/ahrenatechnology/ahrena-framework/issues/39) | Issue, pull request and trunk rules | `contributing/` | label and status vocabulary (#22) |
| [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) | Code quality and code review — eight groups plus correctness and resource discipline | `engineering/`, `engineering-python/` | eleven owner decisions in the issue |
| [#45](https://github.com/ahrenatechnology/ahrena-framework/issues/45) | Issue-driven development, planning and QA-as-process — seven groups | undecided plugin | ten owner decisions in the issue |
| [#54](https://github.com/ahrenatechnology/ahrena-framework/issues/54) | Voice as a rule, and the configuration file that would gate it | new files, `README.md` | three decisions below |
| [#55](https://github.com/ahrenatechnology/ahrena-framework/issues/55) | Context injection per platform, and staleness detection | `ARCHITECTURE.md`, new files | #54, and a measurement against Claude Code |
| [#56](https://github.com/ahrenatechnology/ahrena-framework/issues/56) | MCP transport hierarchy | new files | which plugin owns it |
| [#57](https://github.com/ahrenatechnology/ahrena-framework/issues/57) | Publish Argos as a GitHub custom agent | `.github/`, `ARCHITECTURE.md`, `foundation/rules/naming.md` | seven content items, in the issue |
| [#58](https://github.com/ahrenatechnology/ahrena-framework/issues/58) | Stacked pull requests, and Argos reviewing a stack | `engineering/`, `contributing/` | **#39** |
| [#59](https://github.com/ahrenatechnology/ahrena-framework/issues/59) | Nothing listens for `@claude` | `.github/workflows/` | the app and a secret, both owner-side |
| [#12](https://github.com/ahrenatechnology/ahrena-framework/issues/12) | Contract-first: the authoring skills that never shipped | `engineering/` | open question 8 for the enforcement half |

**Landed and closed:** the foundation core and its gate, the eleven engineering rules, the Python plugin, Argos ([#33](https://github.com/ahrenatechnology/ahrena-framework/issues/33)), branch and commit rules ([#38](https://github.com/ahrenatechnology/ahrena-framework/issues/38)), specification, factory and domain service ([#42](https://github.com/ahrenatechnology/ahrena-framework/issues/42)), safe refactoring ([#43](https://github.com/ahrenatechnology/ahrena-framework/issues/43)) and Python typing and toolchain ([#44](https://github.com/ahrenatechnology/ahrena-framework/issues/44)). Epic #5 is closed.

### What serializes, and what does not

**Shared files are the bottleneck, not the gate.** Four files collide across almost everything queued: `engineering/agents/argos.md`, `engineering/hooks/check-structure.py`, `engineering/skills/reviewing-diffs/SKILL.md` and `README.md`. Give each to one issue per wave and reconcile the rest in a single commit afterwards.

**The index is not the only thing that collides.** Parallel agents must run in separate git worktrees. Four once shared one working tree and one git index: one agent's commit landed on another's branch, and each was validating a tree holding three others' half-written files, so every verification any of them did meant nothing. No two of them ever touched the same file.

## Decided

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

There is a **fifth platform**, found on 2026-09-19 and not yet reflected in `ARCHITECTURE.md`, which still says four. GitHub custom agents are `.agent.md` files under `.github/agents/` in a repository, or under `/agents/` in the organisation's `.github` repository, and they run in Copilot's cloud agent on github.com — assigned to an issue, opening a pull request — as well as in several IDEs. Their frontmatter is `description` (required) plus `name`, `tools`, `model`, `target` and others, which our open schema for agents already accepts unchanged.

Two things follow. The extension and directory conflict with `foundation/rules/naming.md`, which says an agent is `<plugin>/agents/<name>.md`; that is row M. And `AGENTS.md` gains a third consumer, since Copilot's coding agent reads it too, which strengthens the injection design in row D at no cost.

Sources could not be read first-hand: `docs.github.com` is blocked by this environment's egress proxy, so the field list came from secondary sources and one of them disagrees about whether the organisation-level file carries the `.agent` infix. Confirm before building M.

## Open, and only the owner settles these

1. **Does `.ahrena/config.json` ship before the gate that reads it?** Its only route-1 consumer is the banned-terms gate (#24), which does not exist. "Prefer deleting" says the file arrives with the gate. Blocks C and D.
2. **Whose voice is the default?** The predecessor's `tone_and_writing_style` is the maintainer's personal voice, in the first person. Company-agnostic (#15) says it cannot ship as-is.
3. **Does composition (#25) supersede the config file?** A layer that patches entries by id is a configuration mechanism. Deciding after both are built means building two.
4. **Does a branch name require an issue number?** The predecessor demanded `{type}/{issue}-{slug}`. This repository's own `feat/foundation-core` would fail it. Blocks A.
5. **Does `lex-mcp` survive?** Its third clause anchors on a `.directives` key that is being deleted. Without an anchor it becomes a maxim. Rewrite for third-party servers, or drop.
6. **Which plugin owns the MCP transport rule?** It is not the self-hosting core. Foundation is the wrong home and no tooling plugin exists. When it is written, it needs a sentence the predecessor's version lacks: the order optimises for local resource cost, and remote-first means the data leaves the machine. On a codebase handling a client's accounting records that is the first question anyone asks, and the rule has to say which axis it optimises and where that inverts.
7. ~~**Do cross-plugin references get an addressing form now?**~~ **Settled**, in the Decided table above. The slot is kept so that the numbers the other rows and [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) cite still point where they did.
8. **Does `enforcement` gain a third state?** It takes one value per rule today, so a rule whose conditions are partly mechanical cannot say so. `solid.md` hits it with two of six conditions scripted. `value-semantics.md` found a workaround — carry the judgment in the finding message, so it is delivered when the condition fires rather than in every request — which may be the answer, or may be a pattern that only works for gated conditions.
9. **How does an agent published to GitHub stay in sync with its plugin copy?** Row M creates a second file for the same agent, in a different directory with a different extension. Generating one from the other makes it a derived file, which #23 wants fewer of; maintaining both by hand makes them drift.

## Not coming across

From the predecessor's 139 foundation artifacts:

| Group | Count | Why |
|---|---|---|
| tooling | 33 | Make targets, the Ahrena MCP, git-spice, graphify, cost tracking. Maintainer infrastructure (#16) |
| process, planning and checkpoint | 26 | 980 lines in the two planning artifacts alone, bound to worktrees, labels, plan sub-issues and heartbeats |
| i18n | 2 | English-only (#2) |
| `lex-logging-decorator`, `lex-observability-required` | 2 | Engineering, not foundation (#13) |
