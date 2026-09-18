# Work inventory

Every artifact in flight or queued, one row each, so two pieces of work never collide on the same file.

This lives at the repository root rather than inside `foundation/`, because it is project state, not framework content. An artifact inside the plugin ships to every consumer and must pass the gate; a backlog does neither.

## Landed

On `feat/foundation-core`, in PR #33. Eleven artifacts, gate green.

| Artifact | Type | What it settles |
|---|---|---|
| `rules/pilars.md` | rule | Five types, and the matrix of which references which |
| `rules/naming.md` | rule | Kebab-case, no prefixes, flat layout, the agent's two names |
| `rules/frontmatter.md` | rule | Required fields per type, closed schema for rule and doc |
| `rules/progressive-disclosure.md` | rule | 10-line cap on body code, reachability of deferred material |
| `rules/completeness.md` | rule | No unfilled marker or placeholder, required sections per type |
| `docs/artifact-model.md` | doc | Rationale for four of the five rules |
| `docs/context-budget.md` | doc | Three load tiers, and the measurement behind the cap |
| `skills/creating-artifacts/` | skill | Type decision, five templates |
| `skills/reviewing-artifacts/` | skill | The review the gate cannot give |
| `skills/writing-hooks/` | skill | Conditions into a script, test-first |
| `agents/claudionor.md` | agent | The specialist that orchestrates the three |

## Queued

`Touches` is the column that decides parallelism. Two rows that share a file cannot run at the same time.

| # | Work | New artifacts | Touches | Blocked by |
|---|---|---|---|---|
| **A** | Branch and commit rules | `rules/branch-naming.md`, `rules/commit-format.md`, `docs/contribution-flow.md`, `hooks/check-branch-name.py`, `hooks/check-commit-message.py` | new files, `README.md` | the issue-number question below |
| **B** | Issue and PR rules | `rules/issue-quality.md`, `rules/pr-quality.md`, `rules/protected-trunk.md` + doc | new files, `README.md` | label and status vocabulary (#22) |
| **C** | Voice, and the config file | `rules/voice.md`, `docs/voice.md`, `hooks/verify-banned-terms.py`, `.ahrena/config.json` | new files, `README.md` | three decisions below (#24, #25) |
| **D** | Context injection per platform | `hooks/session-context.py`, generated-block markers, `hooks/verify-instruction-freshness.py` | `ARCHITECTURE.md`, new files | C, and a measurement against Claude Code |
| **E** | MCP transport hierarchy | `rules/mcp-transport.md` + doc | new files | which plugin owns it |
| **F** | Two judgment scans in review | none | `skills/reviewing-artifacts/SKILL.md` | nothing |
| **G** | Engineering fundamentals (#5) | a second plugin: SOLID, KISS, YAGNI, clean code, DTO, patterns, DDD, contract-first, decorators, Python modules | new plugin dir, `.claude-plugin/marketplace.json` | nothing |

### What serializes, and what does not

**The artifact gate is the only real bottleneck.** Everything that adds a *condition* edits `foundation/hooks/validate-artifacts.py` and its test file. Nothing in the queue above does, which is the useful finding: A, B, C, E and F create their own hooks or touch only their own files.

**F and G are fully parallel with everything.** F edits one skill body. G is a different plugin and shares no file with foundation.

**The cheap collisions are `README.md` and `docs/artifact-model.md`.** A, B and C each want a line in the README's rule count, and several want a section in the model doc. Trivial to resolve, worth knowing before two of them run at once.

## Decided

| Decision | Consequence |
|---|---|
| The Ahrena MCP server is dropped | 1,268 lines of Python, three artifacts, and the second `.directives` parser all go |
| Capability arrives as a skill, not an MCP server | An MCP server's tool definitions sit in the always-loaded tier; a skill costs its `description` |
| The framework does not own MCP configuration | Four platforms already declare MCP servers in their own manifests. A framework key listing them is a fifth source of truth that can disagree with the four real ones |
| Persona names are allowed on agents, and nowhere else | `name` is the handle, `role` is the subject |
| References carry no verb | The pair of types already determines it |

## Open, and only the owner settles these

1. **Does `.ahrena/config.json` ship before the gate that reads it?** Its only route-1 consumer is the banned-terms gate (#24), which does not exist. "Prefer deleting" says the file arrives with the gate. Blocks C and D.
2. **Whose voice is the default?** The predecessor's `tone_and_writing_style` is the maintainer's personal voice, in the first person. Company-agnostic (#15) says it cannot ship as-is.
3. **Does composition (#25) supersede the config file?** A layer that patches entries by id is a configuration mechanism. Deciding after both are built means building two.
4. **Does a branch name require an issue number?** The predecessor demanded `{type}/{issue}-{slug}`. This repository's own `feat/foundation-core` would fail it. Blocks A.
5. **Does `lex-mcp` survive?** Its third clause anchors on a `.directives` key that is being deleted. Without an anchor it becomes a maxim. Rewrite for third-party servers, or drop.
6. **Which plugin owns the MCP transport rule?** It is not the self-hosting core. Foundation is the wrong home and no tooling plugin exists.

## Not coming across

From the predecessor's 139 foundation artifacts:

| Group | Count | Why |
|---|---|---|
| tooling | 33 | Make targets, the Ahrena MCP, git-spice, graphify, cost tracking. Maintainer infrastructure (#16) |
| process, planning and checkpoint | 26 | 980 lines in the two planning artifacts alone, bound to worktrees, labels, plan sub-issues and heartbeats |
| i18n | 2 | English-only (#2) |
| `lex-logging-decorator`, `lex-observability-required` | 2 | Engineering, not foundation (#13) |
