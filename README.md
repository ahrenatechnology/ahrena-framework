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

Early. The `ahrena-foundation` plugin carries the self-hosting core: the five rules that define what an artifact is, what it may cost and when it is finished, the docs that explain them, the skills that create, review and enforce artifacts, the specialist that orchestrates those skills, and the gate that decides every condition the rules state.

```sh
python3 foundation/hooks/validate-artifacts.py
```

The gate takes no dependencies, so the check CI runs is the check a consumer runs.

`ahrena-engineering-fundamentals` is the second plugin and the first consumer of that core: SOLID, KISS and YAGNI alongside nine more, written as detectable conditions with a single arbitration between them, plus the reviewer that applies them to a pull request.

The language plugins — `ahrena-engineering-python`, `-typescript`, `-go` and `-rust` — each hold what is specific to one language: rules with a named detector each, references that ground them in the language's specification, skills to write, review and debug it, and a specialist agent. `ahrena-engineering-terraform` does the same for infrastructure as code, and `-aws`, `-gcp` and `-azure` for one cloud each. The layer builders reach a language through its writing skill and the security plugin's exposure rule, loaded before they write the first test, and through its review skill afterwards. `ahrena-contributing` governs the repository rather than the code in it, as one flow from issue to trunk with two gates and a person landing the change: how an issue is opened, a change planned and its acceptance criteria traced to tests, what a branch is called, what a commit message carries, how a pull request closes its issues, how a stack of them lands, natively or run by the framework, and what may reach trunk, with a detector for each that can have one.

A plugin may reference another by the name the marketplace gives it, as `ahrena-engineering-fundamentals:docs/simplicity.md`, and that graph is acyclic. Everything else is tracked in the issues of this repository.

## Install the agency

The agency is ten plugins from the `ahrena` marketplace, plus one per language, infrastructure tool or cloud the repository uses.

| Plugin | What it is |
|---|---|
| `ahrena-engineering-development` | Athena, who turns an issue into a stack of reviewed pull requests, and `/install-agency` |
| `ahrena-engineering-delivery` | Themis and Hermes, the PM and the Tech Lead of a round, who run a work window of Athena sessions |
| `ahrena-engineering-frontend` | Iris, who builds a feature outside-in, wireframe first; Daedalus, who draws the wireframe for approval; Aglaia, who writes each code layer |
| `ahrena-engineering-backend` | Apollo, who builds a capability inside-out, domain first; Hephaestus, who writes each layer test-first |
| `ahrena-engineering-code-review` | Argos, who conducts the review: routes the lenses, publishes one verdict, loops through Erodos, lands |
| `ahrena-engineering-quality` | Erodos and the review skills: route, review, publish the verdict, apply fixes, land |
| `ahrena-engineering-fundamentals` | The language-agnostic engineering rules and the code graph |
| `ahrena-engineering-security` | Janus, the six security review disciplines, and the rule that nothing sensitive leaves the layer that owns it |
| `ahrena-contributing` | Issue, plan, branch, commit and pull request rules |
| `ahrena-foundation` | What an artifact is, and the skills that create and review them |

The language, infrastructure and cloud plugins each bring a specialist, the entry point for work in that stack that is not one layer of a build, and the skills the builders load:

| Plugin | Specialist | Skills |
|---|---|---|
| `ahrena-engineering-python` | Pythia (`python-engineer`) | `writing-python`, `reviewing-python`, `debugging-python` |
| `ahrena-engineering-typescript` | Proteus (`typescript-specialist`) | `writing-typescript`, `reviewing-typescript`, `debugging-typescript` |
| `ahrena-engineering-go` | Ariadne (`go-specialist`) | `writing-go`, `reviewing-go`, `debugging-go` |
| `ahrena-engineering-rust` | Talos (`rust-specialist`) | `writing-rust`, `reviewing-rust`, `debugging-rust` |
| `ahrena-engineering-terraform` | Gaia (`terraform-engineer`) | `writing-terraform`, `reviewing-terraform`, `debugging-terraform` |
| `ahrena-engineering-aws` | Atlas (`aws-specialist`) | `designing-on-aws`, `reviewing-aws`, `diagnosing-aws-deployments` |
| `ahrena-engineering-gcp` | Hyperion (`gcp-architect`) | `designing-on-gcp`, `reviewing-gcp`, `diagnosing-gcp-deployments` |
| `ahrena-engineering-azure` | Ouranos (`azure-specialist`) | `designing-on-azure`, `reviewing-azure`, `diagnosing-azure-deployments` |

The installer enables the ones whose marker file sits at the repository root (`pyproject.toml`, `requirements.txt` or `setup.py`; `tsconfig.json` or `package.json`; `go.mod`; `Cargo.toml`; `main.tf`, `versions.tf`, `terraform.tf` or `.terraform.lock.hcl`; `cdk.json` or `samconfig.toml`; `cloudbuild.yaml` or `.gcloudignore`; `azure.yaml` or `host.json`), or the ones `--language` names.

From the root of your repository, with no checkout and no plugin installed:

```sh
curl -fsSL https://raw.githubusercontent.com/ahrenatechnology/ahrena-framework/main/engineering/development/skills/installing-the-agency/scripts/install.py | python3 -
```

Pass options after the dash, as `python3 - --language python`. The command fetches `install.py` from the `main` branch. `--platform claude|codex` limits the run to one instruction file. If only `AGENTS.md` exists the run is Codex-only and skips `.claude/settings.json`, so pass `--platform claude` to write it. Once `ahrena-engineering-development` is present, `/install-agency` runs the same script, and `/install-agency --check` verifies the result without writing.

`--platform claude|codex` limits the run to one instruction file. A repository that has only `AGENTS.md` is treated as Codex-only and skips `.claude/settings.json`; pass `--platform claude` to write it.

It is idempotent: a second run changes nothing and says so. It writes:

- `.claude/settings.json`: `extraKnownMarketplaces.ahrena` and `enabledPlugins["<plugin>@ahrena"]: true`, keeping every other key and never flipping a plugin you disabled.
- A block between `<!-- ahrena:agency:start -->` and `<!-- ahrena:agency:end -->` in `CLAUDE.md` and `AGENTS.md`, for every file present, or both when neither exists.

It does not use `claude plugin marketplace add`, which rewrote an existing `ahrena` entry's ref. The manual path is still available:

```sh
claude plugin marketplace add ahrenatechnology/ahrena-framework --scope project
claude plugin install ahrena-engineering-development@ahrena --scope project
# the same for each plugin in the table
```

The directive names `clio`, the data builder, which lives in `ahrena-engineering-data` with `mnemosyne`, its implementer, and is not one of the ten. To add it, run `claude plugin install ahrena-engineering-data@ahrena --scope project`, or add `"ahrena-engineering-data@ahrena": true` to `enabledPlugins`.

## License

See [LICENSE](LICENSE).
