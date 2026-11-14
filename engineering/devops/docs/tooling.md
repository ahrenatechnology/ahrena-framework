---
id: tooling
type: doc
clade: engineering
subclade: devops
title: The tools for GitHub Actions pipelines
summary: For each problem a pipeline author or reviewer meets - syntax and expressions, security patterns, pin maintenance, provenance, local runs - the tool the framework recommends, why, and when not to use it.
references:
  - rules/action-pinning.md
  - rules/script-injection.md
  - rules/token-permissions.md
  - docs/github-actions.md
---

# The tools for GitHub Actions pipelines

One tool per problem, the reason, and the case where it is the wrong one. The plugin's own hook, `hooks/check-workflows.py`, runs with nothing installed and decides the conditions of this plugin's rules that a file can decide; the tools below go further and are what a project installs.

| Problem | Tool | Why | When not |
|---|---|---|---|
| Syntax, expression types, action inputs, shell errors in `run:` | [actionlint](https://github.com/rhysd/actionlint) (with shellcheck installed, which it calls) | It knows the workflow schema and the inputs of popular actions, types `${{ }}` expressions, and runs shellcheck on every `run:` block. It also reports script injection by untrusted inputs, and checks the `permissions` block's syntax ([checks](https://github.com/rhysd/actionlint/blob/main/docs/checks.md)). | It does not check pinning, permissions breadth or dangerous triggers. Not a security scanner on its own. |
| Security patterns: permissions, pinning, injection, triggers, cache poisoning, secrets | [zizmor](https://docs.zizmor.sh/audits/) | The broadest named audit set: `excessive-permissions`, `unpinned-uses`, `template-injection`, `dangerous-triggers`, `artipacked`, `cache-poisoning`, `secrets-inherit`, `overprovisioned-secrets`, `unredacted-secrets`, `impostor-commit` and more. Its default pin policy hash-pins every action, `actions/*` included. Emits SARIF for code scanning. | Its pedantic audits (`undocumented-permissions`, `anonymous-definition`) are noise for most teams; run the default persona in CI. It has no timeout check, which the hook covers. |
| A score across the repository's supply chain | [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md) | `Token-Permissions`, `Pinned-Dependencies`, `Dangerous-Workflow` beside branch protection and the rest, as one report a reader outside the team trusts. | It scores, it does not gate a pull request line by line; use zizmor for that. |
| Keeping pins current | Dependabot, `package-ecosystem: github-actions` | Native, updates SHA pins and their version comments ([Dependabot for actions](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)). | A repository on the workflow lockfile regenerates it with `gh actions-lock` instead ([Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles)). |
| Provenance of what is deployed | `actions/attest` and `gh attestation verify` | Signed build provenance and SBOM attestations, SLSA Build Level 2 on their own ([Using artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)). | A private repository uses GitHub's instance, which has no transparency log ([Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)); a consumer outside GitHub may need another signer. |
| Reading a run from the terminal | `gh run view --log-failed`, `gh run rerun --failed` | The failed steps' logs without the noise, and a rerun of only what failed; the debugging skill starts here. | A log that has expired is gone; a rerun with debug logging needs the secret or variable set first. |
| Running a workflow locally | `act` | A fast loop on a workflow's shape. | Its runner images are not GitHub's, it has no OIDC token, and environments do not exist; a green local run says little about the real one. Never give it production credentials. |

## Order in a pipeline

On a change to `.github/`: actionlint, then zizmor, then this plugin's hook. actionlint first, because a file that does not parse makes the other two report noise. Each is a required check on a repository whose pipeline is worth protecting ([`repository-governance.md`](repository-governance.md)).

## Where this stops

**Language and infrastructure tools** (the test runner, tflint, Checkov) are their plugins'; this page covers what reads the workflow files.

**A tool's version** is pinned like any action ([`rules/action-pinning.md`](../rules/action-pinning.md)); the versions named in the citations were current when this page was written and are not repeated here.
