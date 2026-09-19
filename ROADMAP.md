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
| **K** | Specification, factory and domain service | `engineering/` | `engineering/` | nothing |
| **M** | Publish Argos as a GitHub custom agent | `.github/agents/argos.agent.md` | `.github/`, `ARCHITECTURE.md`, `foundation/rules/naming.md` | the extension conflict below, and seven content items L found |
| **N** | Stacked pull requests | port of 6 predecessor artifacts, 1,523 lines | `engineering/` or a contributing plugin | **A and B** |
| **Q** | Code quality and code review — eight groups, [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) | 16 artifacts ported or rewritten, 2,212 predecessor lines | `engineering/`, `engineering-python/` | #33, and eleven owner decisions in the issue |

Everything else in this table has landed: **F**, **G1** (SOLID, KISS, YAGNI), **G2** (clean code, value semantics, contract-first, cross-cutting concerns, pattern selection, domain model), **G3** (the `ahrena-engineering-python` plugin), **H** (duplication), **I** (aggregates and domain events), **J** (the two clean-code findings in the foundation's own gate) and **L** (Argos). Epic #5 is closed.

**L landed as five artifacts, and no rule.** `engineering/agents/argos.md`, the skills `reviewing-diffs`, `detecting-contract-breaks` and `publishing-review-verdicts`, and the docs `review-findings.md` and `review-verdicts.md`. The three skills split by input rather than by subject: the first consumes the diff, the second cannot (a break is a relation between two versions and the earlier one is not in the diff) and the third consumes neither the diff nor the code, only the finding set and the reviewer's own published history. No rule, because a review procedure is not a state a codebase can be in.

**M is blocked on seven content items, not just on the file extension.** A single `.agent.md` in a cloud runner loses more than layout. `hooks/check-structure.py` is named twice as a local-checkout assumption, and without it nineteen conditions across seven rules fall back to reader-decided with only the "not Python" degradation written down. The fork-safety refusal is phrased for a workstation and has to be restated for an ephemeral runner holding an org-scoped token, not copied. The test command and the contract fetch both assume a working tree; only the fetch ports, and only if rewritten against the contents API. The publishing identity is the item most likely to break silently, because GitHub's cloud agents publish under the runner's identity and an unstable one makes the approval row unreachable forever. The relative links and `references/review-body.md` resolve only inside the plugin tree, and the body skeleton inlined is over the 10-line cap this framework enforces and GitHub does not — so the two files are two documents that share content, not one file in two places. The frontmatter does not map: `role`, `type`, `clade`, `subclade` and `references` have nowhere to go, and `role: pull-request-reviewer` is the real loss. And "Skills it orchestrates" presumes a skill loader, so the cloud version inlines the procedures and stops being an orchestrator, which `foundation/rules/pilars.md` calls a defect here and which is unavoidable there.

**Q is eight groups and it is not free.** The survey behind [#34](https://github.com/ahrenatechnology/ahrena-framework/issues/34) read 38 candidate artifacts totalling 5,417 lines in the predecessor and found that **not one threshold in them is justified by a measurement** — 70/20/10 links Fowler, 80% coverage is "default", the 90/80/70/60 tier table is asserted, `min-similarity-lines=30` is a pylint default, six suite-time budgets are asserted, and the word "complexity" appears 14 times without ever standing beside a figure. Every ported threshold therefore needs a measurement or a sentence naming who it was inherited from, and for the test pyramid there may be no corpus here to measure against. Three groups collide on `skills/reviewing-diffs/SKILL.md` and `agents/argos.md`, two collide on `hooks/check-structure.py`; the issue says which and in what order. Nine of its findings contradict a decision this repository already made in writing, the sharpest being the colour-coded severity scheme that `docs/review-findings.md` refused by name.

**Nothing in this repository listens for `@claude`.** `.github/workflows/` holds one file, `validate.yml`, which fires on `push` and `pull_request`. A review request posted as a comment is therefore text, and the Claude app has never commented in this repository. Wiring it needs a workflow on `issue_comment`, the app installed on the organisation, and a secret in the repository. The workflow is not committed yet, because without the secret it fails on every pull request and turns the gate's neighbour red.

K is what `docs/patterns.md` still names as absent after I. The plugin now states aggregate, entity, value object and domain event as conditions; specification, factory and domain service have no artifact.

**N is the second round, and it cannot come first.** The six stacked-pull-request artifacts in the predecessor (`codex-stacked-prs` 271 lines, `kata-stacked-pr-create` 330, `kata-stacked-pr-merge` 320, `kata-stacked-pr-rebase` 237, `cry-new-stacked-pr` 44, `codex-git-spice` 321) consult nine rules from the contributing set: branch naming, conventional commits, commit language, small commits, signed commits, issue-first, issue quality, PR quality and protected trunk. None of those exist here yet. Building N before A and B means inventing the rules it rests on, which is how the predecessor ended up with a rule corpus nobody could trace.

Argos extends into stacked pull requests in that round: a stack is a review subject with an order, and reviewing the third pull request in a stack without its two parents is a different procedure.

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
| MCP transport is ordered: remote HTTP, then a vendor binary, then npx, with Docker undecided | The predecessor already wrote this as `lex-mcp` section 5, with the same reasoning. The vendor-binary tier is the one worth recovering, because a binary needs no Node |
| A hook whose tests are not in CI is not trusted | All three suites run in `validate.yml`, tests before the corpus check |

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
7. **Do cross-plugin references get an addressing form now?** `pilars.md` said the question waits until a second plugin needs to reference the first. Two artifacts have now paid for its absence independently: `engineering-python/rules/module-boundaries.md` restates one line of SOLID's sixth condition in prose because it cannot link it, and `engineering/rules/duplication.md` names the same constraint from the other side, observing that a third plugin would turn `SKIP_DIRS` into a finding whose only fix is the shared module the no-dependency constraint forbids.
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
