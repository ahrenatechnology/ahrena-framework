---
id: state
type: rule
clade: engineering
subclade: terraform
title: State lives in a remote backend, locked and encrypted, and never in the repository
statement: Terraform state lives in a remote backend that locks it and encrypts it at rest; no state, saved plan or .terraform directory is in the repository.
enforcement: judgment
references:
  - docs/state.md
---

# State lives in a remote backend, locked and encrypted, and never in the repository

State is the one file that maps the configuration to the real objects, and it is also the one file that holds every value the configuration ever touched. HashiCorp says both halves of that plainly: a secret written into a configuration is stored "in its state and plan files", and a value marked `sensitive` is still recorded in state ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)). Redaction is a property of the CLI's output, not of the file. So where state sits, who can read it and whether two runs can write it at once are not housekeeping; they decide whether the infrastructure's credentials are as protected as the infrastructure.

The same page lists what HashiCorp recommends for a state that holds sensitive values: store it remotely, encrypt it at rest, limit who can read it, and audit who did. The style guide's `.gitignore` section names what never enters version control: the state file and its backups, the `.terraform.tfstate.lock.info` file, the `.terraform` directory, saved plan files, and any `.tfvars` file that holds something sensitive ([Style guide](https://developer.hashicorp.com/terraform/language/style)). This rule is those two lists made into conditions.

`docs/state.md` carries the rest: how a backend is chosen, how environments are separated, what `terraform_remote_state` costs, and where OpenTofu differs.

## Conditions

1. **No state file, backup, saved plan or `.terraform` directory is in the repository.** Decided by `hooks/check-terraform.py`, over the files git tracks or would add: `*.tfstate`, `*.tfstate.*`, `.terraform.tfstate.lock.info`, `*.tfplan`, and anything under a `.terraform/` directory. A saved plan holds the full configuration and the values of the planned changes "in cleartext" ([`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)), and `.terraform` holds the merged backend configuration in plain text, credentials included when they were passed with `-backend-config` ([Backend block](https://developer.hashicorp.com/terraform/language/backend)). HashiCorp's own reason for keeping state out of git is a second one: version control cannot lock the file.

2. **Every root module declares a remote backend, or a `cloud` block.** Decided by `hooks/check-terraform.py`. A root module with no `backend` block uses the `local` backend, which is Terraform's default ([Backend block](https://developer.hashicorp.com/terraform/language/backend)), and a declared `backend "local"` is the same thing written down. Both keep state as a plaintext file on whichever machine ran the apply. A root module is a directory of `.tf` files that is neither under `modules/` nor called by another configuration; a directory under `examples/` or `tests/` is a demonstration and owes no backend.

3. **No script or pipeline turns locking off.** Decided by `hooks/check-terraform.py`, which reports `-lock=false` in a shell script, a Makefile or a pipeline definition. Terraform locks state for every operation that could write it when the backend supports locking, and stops when it cannot take the lock; HashiCorp documents `-lock=false` and says it does not recommend it ([State locking](https://developer.hashicorp.com/terraform/language/state/locking)). `terraform force-unlock` is for releasing your own lock after automatic unlocking failed, and never belongs in a pipeline.

4. **The backend locks and encrypts at rest, and its access is narrower than the configuration's.** Decided by review against the backend's own documentation, because each backend spells these differently and some make them opt-in. HashiCorp's locking page says not every backend supports locking and sends the reader to each backend's page; the S3 backend, for one, locks only when `use_lockfile` is set, and encrypts only when `encrypt` is set. The settings for a given cloud's backend belong to that cloud's plugin; this rule names the state that must hold, on any backend. Access means the identity that reads state for a plan is not given to anyone who only needs an output: the state is the whole configuration's secrets, and an output is one value.

5. **Each environment has its own state, in its own backend configuration.** Decided by review. HashiCorp says CLI workspaces share one backend and are therefore "not a suitable isolation mechanism" where deployments need separate credentials and access controls, which is what separating production from anything else means ([CLI workspaces](https://developer.hashicorp.com/terraform/cli/workspaces)). An environment is a root configuration of its own, calling the same modules, with its own backend.

## Where this stops

**Condition 1 sees the repository, not a laptop.** A state file that `.gitignore` excludes is on disk and outside the repository, which is the correct place for a developer's scratch state and is not reported. Outside a git work tree the hook cannot tell the two apart and reports every such file it finds.

**Condition 1 reports `*.tfplan` and no other plan name.** A plan file can be called anything; `*.tfplan` is the common convention and the one a `.gitignore` can name. A plan saved as `plan.out` is not recognised, and a reviewer reads the pipeline that writes it.

**Condition 2 decides that a backend is declared, not that it is the right one.** `backend "s3" {}` with every setting supplied by `-backend-config` at init is correct and passes; so does a backend whose bucket is world-readable. Condition 4 is where that is read.

**Encryption at rest is not encryption from the people who run Terraform.** Whoever can run a plan can read the state, because Terraform decrypts it to plan. OpenTofu's client-side state encryption (OpenTofu 1.7 and later) encrypts state and plan files with a key Terraform does not have, and its documentation says plainly that it cannot protect sensitive values from the person running `tofu` ([State and plan encryption](https://opentofu.org/docs/language/state/encryption/)). It satisfies condition 4 on any backend; Terraform has no equivalent and relies on the backend.

**This rule declares judgment, and the reason is conditions 4 and 5.** Three of the five conditions have a script, and a hook rule would contribute no text to any request. What it would drop is the requirement that the backend locks and encrypts, which no script can read from a `backend "s3" {}` whose settings arrive at init. A plugin that checked that a backend exists and stayed silent on whether it protects anything would be teaching the wrong half.
