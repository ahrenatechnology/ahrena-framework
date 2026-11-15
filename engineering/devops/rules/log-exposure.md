---
id: log-exposure
type: rule
clade: engineering
subclade: devops
title: Nothing sensitive is written to a pipeline log
statement: A step never prints a secret, a token, the environment, a whole context, an account identity or an unredacted plan to the job log.
enforcement: judgment
references:
  - docs/environments-and-secrets.md
  - ahrena-engineering-security:docs/layer-exposure.md
---

# Nothing sensitive is written to a pipeline log

This is the pipeline form of [`layer-exposure.md`](../../security/rules/layer-exposure.md): a pipeline log is an exit, more people read it than read the cloud console, and on a public repository it is public. GitHub redacts registered secrets from the log, and says itself that "automatic redaction is not guaranteed": a secret wrapped in JSON, transformed, or derived (a token a step mints) is not on the list, and values that are not GitHub secrets have to be masked with `::add-mask::` before they are printed ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use); [Workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)). Redaction is the backstop; not printing is the control. [`docs/environments-and-secrets.md`](../docs/environments-and-secrets.md) argues where each value goes instead.

## Conditions

1. **No step prints a secret.** `echo`, `printf`, `cat`, `Write-Host` or `Write-Output` of a `${{ secrets.* }}` expression, or of an environment variable whose value is one, on a line that neither redirects to a file nor pipes into a command; and any expansion of `toJSON(secrets)`. Decided by `hooks/check-workflows.py`; zizmor `overprovisioned-secrets` reports the whole context and `unredacted-secrets` a secret used as structured data.
2. **No step prints the environment or a whole context.** `env`, `printenv`, `export -p`, `set` or `Get-ChildItem env:` with no argument, and a printed `toJSON(github)`, `toJSON(env)`, `toJSON(vars)` and the like, directly or through a variable. The environment holds every secret a step was given; the `github` context holds the event and the token's scope. Decided by `hooks/check-workflows.py`.
3. **No job that holds a secret traces its shell.** `set -x`, `set -o xtrace`, a `-x` in a combined flag set or in `shell:`. Tracing prints each command after expansion. Decided by `hooks/check-workflows.py`.
4. **No step prints a credential it mints or the cloud identity it runs as.** `gcloud auth print-access-token` and `print-identity-token`, `az account get-access-token`, `aws sts get-session-token`, `assume-role`, `aws ecr get-login-password`, and the identity commands `aws sts get-caller-identity`, `az account show`, `gcloud config list`, when their output is neither captured, piped nor redirected. A minted token is not a registered secret and is printed in clear; an account, subscription or project identifier is in the third class of the exposure rule. Decided by `hooks/check-workflows.py`.
5. **Terraform's debug log stays off.** `TF_LOG` set to any level in a workflow or job `env`. [`toolchain.md`](../../terraform/docs/toolchain.md) of the Terraform plugin says why. Decided by `hooks/check-workflows.py`. The JSON plan and outputs printed to the log are condition 3 of the Terraform plugin's [`outputs.md`](../../terraform/rules/outputs.md), decided by its hook.
6. **Every other value a step writes to the log, a job summary, a pull-request comment or an artifact is a named field its reader needs.** A plan posted to a pull request on a public repository; a saved plan file or state uploaded as an artifact, which has the state's sensitivity; a deploy step that echoes the resource identifiers it created; a value derived from a secret and not masked; debug logging left on by the repository secret or variable `ACTIONS_STEP_DEBUG` or `ACTIONS_RUNNER_DEBUG`, which lives in the forge, not in the file. Decided by review, with `DAT-1` of `reviewing-sensitive-data`.

## Where this stops

**The hook decides five shapes and is written to miss rather than misfire.** A secret printed by a script the step calls, or by a tool's verbose flag, passes it. A pass from the hook is not a pass from the rule: condition 6 is the larger half, which is why the rule declares judgment.

**A secret handed over is not a secret printed.** `echo "$TOKEN" | docker login --password-stdin` and `echo "…$TOKEN" > .npmrc` pass: the value goes to a process or a file, not to the log.

**The human-readable Terraform plan may be printed.** The Terraform plugin allows it, because review reads it; its redaction is only as good as the marking of sensitive values, which is that plugin's rule.
