---
id: modules
type: doc
clade: engineering
subclade: terraform
title: Composing Terraform by modules
summary: How a Terraform repository is cut into modules, why calls run one way from the root down, how a module receives its dependencies and is extended without being edited, when to write a module and when to take a registry one, and how SOLID, single responsibility and the exposure rule look in HCL.
references:
  - rules/module-boundaries.md
  - rules/outputs.md
  - rules/test-placement.md
  - rules/pinning.md
---

# Composing Terraform by modules

The companion to [`rules/module-boundaries.md`](../rules/module-boundaries.md). The rule decides direction; this argues the shape. Every recommendation here names the premise that decides it, from the three the framework holds: maintainability, low cyclomatic complexity, and no circular reference.

## The unit, and the two kinds of module

Terraform's unit of packaging is the module: one directory of `.tf` files. There are two kinds, and keeping them apart is most of the design.

- **A root configuration** is the directory Terraform runs in. It declares the backend, configures the providers, sets the values for one environment, and composes modules. It is run, never called.
- **A reusable module** declares variables, resources and outputs. It configures no provider and owns no state; it is called.

HashiCorp's [standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) puts nested modules under `modules/` and examples under `examples/`, and recommends `main.tf`, `variables.tf` and `outputs.tf` in each, even when empty, with a README. The style guide adds `terraform.tf` for the `terraform` block, `providers.tf` for provider blocks and `backend.tf` for the backend ([Style guide](https://developer.hashicorp.com/terraform/language/style)). A repository laid out that way is one a reader navigates without being told how.

```
live/<environment>/        root configurations: backend.tf, providers.tf, main.tf
modules/<name>/            reusable modules: variables.tf, main.tf, outputs.tf, tests/
```

## Dependencies run one way

Calls run from the root configuration down to the modules it composes. No module calls a root, and the graph of calls has no cycle; `hooks/check-terraform.py` decides both. The premise is the third one, no circular reference: a cycle in a module tree is a tree with no bottom, which nobody can read from one end.

HashiCorp's [Module composition](https://developer.hashicorp.com/terraform/language/modules/develop/composition) goes further and recommends keeping the tree flat, with one level of child modules "in most cases". The premise is maintainability: a root that calls `network`, `database` and `service` side by side, and wires the outputs of one into the inputs of the next, shows the whole architecture in one file. A `service` module that calls `database` internally hides it, and the next reader finds the database by grepping. Nest only when the inner module is an implementation detail no root will ever want to wire differently.

## Inversion of control: the module receives what it depends on

This is the Terraform form of dependency inversion, condition 6 of [`solid.md`](../../fundamentals/rules/solid.md): a component depends on an abstraction it owns, not on a concrete collaborator. In HCL the abstraction is the module's variable block, and the concrete collaborator is whatever the root passes into it.

The composition page is explicit about the anti-pattern. A module should not embed its dependencies, creating its own copy of the network it runs in, and should not try to detect whether something exists and create it if not; it takes the subnet ids, the key, the zone as variables, and the root decides where they come from. The same module then serves a root that creates the network and a root that looks up one somebody else owns, with no change. That is the whole of inversion of control in Terraform: variables in, outputs out, and the root as the only place where concrete objects are chosen.

Two consequences follow, and both are conditions of the rule. A reusable module configures no provider, because a provider configuration is a concrete collaborator; it declares `required_providers` and receives configured providers, aliased ones through `providers = { ... }` ([Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)). And it declares no backend, because state ownership is the root's.

Coupling is kept to what the behaviour needs. A module that takes a whole object (`var.network` with twenty attributes) when it reads two of them is coupled to all twenty; take the two. The variables are the module's interface, and an interface is narrow on purpose.

## Open to extension, closed to edits

A module is extended by a new module that calls it, never by editing it for one caller's case. The base module's extension points are its variables and its outputs: anything a caller may vary is a variable with a type and a validation, and anything a caller may build on is an output.

- **A caller needs a behaviour the module does not have.** Write a module that calls the base one and adds the resources around it, wiring the base's outputs into the new resources. The base is unchanged and every other caller is unaffected.
- **A caller needs to vary something the module hard-codes.** That is a new variable on the base, with a default that keeps today's behaviour, released as a minor version. That is extension through the public extension point, and it is the only edit the base takes.
- **A flag that switches the module between two shapes is two modules.** `var.create_public_endpoint = true` that adds or removes half the resources is the boolean-parameter smell of [`kiss.md`](../../fundamentals/rules/kiss.md) condition 2 in HCL. The composition page's conditional-creation guidance points the same way: let the caller decide what exists by passing it in, not by toggling it inside.

The mechanism that composes modules across a repository, the equivalent of a workspace in a language plugin, is the module source. Within one repository a local path (`./modules/network`) composes modules at the same commit; across repositories a pinned registry version or git tag does (`rules/pinning.md`). A module that more than one repository consumes moves to its own repository or a private registry, and is consumed pinned; a module only one repository uses stays local, because a version boundary costs a release for every change and buys nothing with one consumer.

## Single responsibility, at the module and the file

A module solves one problem and is named for it. HashiCorp's test for a module that does not earn its place is that its name would be the name of the one resource it wraps: "We do not recommend writing modules that are just thin wrappers around single other resource types" ([Creating modules](https://developer.hashicorp.com/terraform/language/modules/develop)). The premise is maintainability: a wrapper adds a layer a reader crosses and a version a maintainer bumps, and decides nothing. The same page asks for moderation, which is [`yagni.md`](../../fundamentals/rules/yagni.md) in HCL: the second root that needs the same group of resources is when the module is extracted, not the first.

Inside a module a file holds one concern. The style guide's file names are the starting cut; a module large enough to need more splits `main.tf` by concern (`network.tf`, `iam.tf`, `storage.tf`), never by resource type alone. The limits are the ones [`clean-code.md`](../../fundamentals/rules/clean-code.md) holds; Terraform adds no number of its own. What grows past them in HCL is not a function but an expression: a `for` expression nested in a conditional nested in a `merge()`. That expression moves into a `locals` block with a name, which is the HCL form of extracting a function, and is testable on its own through an output in a test.

Cyclomatic complexity in HCL is `count`, `for_each`, `dynamic` blocks and conditional expressions. The [style guide](https://developer.hashicorp.com/terraform/language/style) says meta-arguments "add complexity, so use them in moderation": `count` for resources that are almost identical, `for_each` when some arguments need distinct values an integer cannot derive. A `dynamic` block whose content has its own conditionals is a branch a reader simulates; a module with two of them is two modules.

## When to write a module, and when to take one from a registry

| The problem | Choice | Premise |
|---|---|---|
| a group of resources two roots need, specific to this organisation | a local module under `modules/` | maintainability: one definition, wired per root |
| a group of resources many repositories need | its own repository or a private registry, consumed pinned | maintainability: one release per change, not one edit per copy |
| a well-known shape of one cloud's resources (a network, a cluster) | a registry module, pinned exactly, read before adopting | maintainability: a maintained module beats a fork nobody updates |
| one resource with a few arguments | the resource, inline | the thin-wrapper rule above |

A registry module is third-party code that runs with the configuration's credentials. It is read before it is adopted, pinned exactly (`rules/pinning.md`), and treated as a dependency, not as a snippet. `docs/libraries.md` names the registry modules this framework does not choose, because the cloud's plugin does.

## Nothing sensitive leaves the module

The exposure rule of issue #294 holds at every module boundary, not only at the root. In Terraform's form:

- **An output is an allowlist.** A module returns the named attributes its callers read. A root never exports a whole resource or module object (`rules/outputs.md` condition 2).
- **Sensitive values are marked where they enter.** A variable that carries a secret is `sensitive` or `ephemeral`; an output that carries one is `sensitive`, or `ephemeral` in a child module (`rules/secrets.md`, `rules/outputs.md`).
- **Access and topology are not exported without a consumer.** A role, a policy, an account id, a subnet layout: an output of one is a decision with a reader named.
- **Errors carry no configuration.** A `validation`, `precondition` or `postcondition` `error_message` says which rule failed and never interpolates the value that failed it when the value is sensitive; Terraform evaluates these during plan, and the message goes to the log ([Validate your infrastructure](https://developer.hashicorp.com/terraform/language/validate)).

## Where this stops

**The cloud is not here.** Which network, cluster or identity module to take for AWS, Google Cloud or Azure, and how that cloud's resources are best cut, belongs to the cloud's plugin. This page argues the shape any of them takes.

**Terragrunt and similar wrappers are not argued.** They solve the repetition of backend and provider blocks across many roots, which is real; whether a project takes on a second tool for it is the project's decision. Everything here holds with or without one.

**Nothing above the root configuration is covered.** How several root configurations are ordered and fed into one another is a pipeline's and a platform's concern; this page stops at the root, where state is owned.
