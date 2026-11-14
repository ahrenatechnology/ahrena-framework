---
id: state
type: doc
clade: engineering
subclade: terraform
title: State, secrets and environments
summary: What Terraform state holds and why it is the most sensitive file in the system, how a backend is chosen, how environments are separated, how a secret reaches a resource without passing through the source and, where the version allows, without reaching state, and where OpenTofu differs.
references:
  - rules/state.md
  - rules/secrets.md
  - rules/outputs.md
  - rules/drift.md
---

# State, secrets and environments

The companion to [`rules/state.md`](../rules/state.md), [`rules/secrets.md`](../rules/secrets.md) and [`rules/drift.md`](../rules/drift.md).

## What state is, and what it holds

State maps each resource address in the configuration to the real object it manages, with every attribute Terraform read or wrote. Every attribute means every attribute: a generated password's value, a database's connection details, a private key a `tls_private_key` produced. HashiCorp says it twice over: secrets written into a configuration are stored in state and plan files, and values marked `sensitive` are still recorded there, in plain text when the state is local ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)).

So the access question is simple. Whoever can read a configuration's state can read every secret that configuration ever handled. A plan file is the same, plus the full configuration ([`terraform plan`](https://developer.hashicorp.com/terraform/cli/commands/plan)). Neither is an artifact to attach, share or print.

## Choosing a backend

A backend is where state lives. The rule asks four things of it, all from HashiCorp's state-security list: remote, locked, encrypted at rest, and readable only by what plans and applies.

- **Remote** so a team shares one state rather than racing copies ([Remote state](https://developer.hashicorp.com/terraform/language/state/remote)).
- **Locked** so two runs cannot write it at once. Terraform takes the lock on every operation that could write state, if the backend supports locking; not every backend does, and some make it opt-in ([State locking](https://developer.hashicorp.com/terraform/language/state/locking)).
- **Encrypted at rest**, which each backend does its own way and some only when asked ([Manage sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)).
- **Narrowly readable.** The identity that plans holds read on state; the identity that applies holds write; nobody else holds either.

The backend's credentials never sit in the `backend` block. HashiCorp recommends environment variables, and warns that values given with `-backend-config` or written into the block are copied into `.terraform/` and into every plan file in plain text ([Backend block](https://developer.hashicorp.com/terraform/language/backend)). A partial configuration (`backend "<type>" {}` with the non-secret settings supplied at init) is the usual shape.

Which backend is the cloud's question. Object storage in the account the configuration manages is the common choice; HCP Terraform is the vendor-neutral one, with state encrypted at rest. The settings that turn on locking and encryption for each cloud's backend are in that cloud's plugin.

## Separating environments

Each environment is its own root configuration, with its own backend and its own credentials, calling the same modules with different values. HashiCorp is direct that CLI workspaces are not the tool for this: they share one backend and so cannot give production different credentials and access controls from staging ([CLI workspaces](https://developer.hashicorp.com/terraform/cli/workspaces)). CLI workspaces are for short-lived copies of one environment, a feature branch's stack for instance, where shared access is acceptable. HCP Terraform workspaces are a different concept, a separate state with its own permissions, and the [style guide](https://developer.hashicorp.com/terraform/language/style) recommends separate workspaces for each environment there.

## Reading another configuration's values

A configuration that needs another's outputs is tempted by `terraform_remote_state`. HashiCorp warns against it where sensitive data is involved, because the reader "must have access to the entire state snapshot", and recommends publishing the values a consumer needs to a separate location instead, so the two can carry different access controls ([`terraform_remote_state`](https://developer.hashicorp.com/terraform/language/state/remote-state-data)). That is the exposure rule, [`layer-exposure.md`](../../security/rules/layer-exposure.md), in its plainest form: the consumer gets the named value, not the layer. Publish the value as a resource in the producing configuration (a parameter, a DNS record, a key in a store) and read it with a data source in the consumer.

## Getting a secret to a resource

From strongest to weakest, and the first one the Terraform version and the provider support is the one to use:

1. **The resource never takes the secret.** The provider generates it and stores it in a secret manager, and the application reads it there at run time. Terraform manages the secret's container, never its value.
2. **An ephemeral resource reads it, and a write-only argument passes it.** An ephemeral resource (Terraform 1.10 and later) fetches the value during the run; a write-only argument (Terraform 1.11 and later, conventionally suffixed `_wo` with a `_wo_version` beside it) hands it to the provider; neither reaches state or plan ([Ephemeral values in resources](https://developer.hashicorp.com/terraform/language/manage-sensitive-data/ephemeral)). This needs a provider that implements both for the resource in hand.
3. **An ephemeral variable carries it.** `ephemeral = true` (1.10 and later) keeps the variable out of state and plan; it can only flow into ephemeral contexts, which is what limits where it can go.
4. **A sensitive variable carries it.** `sensitive = true` redacts it from the CLI's output and still writes it to state. This is the floor, not the goal.

In every case the value arrives at run time: `TF_VAR_<name>` set by the pipeline from its own secret store, or an ephemeral resource. Never a default, never a literal, never a committed `.tfvars` (`rules/secrets.md`).

## When state and reality disagree

Drift is a real object that no longer matches state and code. `terraform plan -refresh-only` shows it without proposing to change anything; `terraform apply -refresh-only` records it in state without touching infrastructure; an ordinary apply reverts it ([Manage resource drift](https://developer.hashicorp.com/terraform/tutorials/state/resource-drift)). Which of the last two is right depends on whether the change was wanted, and either way the code is edited to agree (`rules/drift.md`). `import`, `moved` and `removed` blocks change state through reviewed code; `terraform state` subcommands are for recovery.

## Where OpenTofu differs

- **Client-side encryption of state and plan.** OpenTofu 1.7 and later can encrypt state and plan files before they reach any backend, with keys from a passphrase, a cloud KMS, OpenBao or an external program ([State and plan encryption](https://opentofu.org/docs/language/state/encryption/)). It protects state from whoever can read the backend's storage, and not from whoever runs `tofu`. Terraform has no equivalent.
- **Variables in the backend block.** OpenTofu 1.8 evaluates variables and locals early enough to use them in backend configuration and module sources ([What's new in OpenTofu 1.8](https://opentofu.org/docs/v1.8/intro/whats-new/)). In Terraform the same values arrive through partial configuration at `init`.
- **State compatibility.** OpenTofu reads state written by Terraform up to 1.5.x ([OpenTofu FAQ](https://opentofu.org/faq/)); moving back and forth after that is a migration, not a switch.

## Where this stops

**No backend is recommended here.** The choice follows the cloud, and the cloud's plugin makes it.

**Secret managers are the cloud's.** Which store, which ephemeral resource reads it, and which resources of that cloud support write-only arguments are in the cloud's plugin; this page orders the mechanisms, it does not pick a product.

**Encrypting state does not make it shareable.** Every option above narrows who can read state; none makes state safe to hand to someone who only needs one value. Publishing that value is the answer to that, as above.
