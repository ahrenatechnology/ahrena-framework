---
id: module-boundaries
type: rule
clade: engineering
subclade: terraform
title: Module calls run one way, from the root configuration down
statement: Terraform module calls form no cycle and never reach a root configuration; a reusable module declares no provider block and no backend.
enforcement: hook
enforced-by: hooks/check-terraform.py
references:
  - docs/modules.md
---

# Module calls run one way, from the root configuration down

Terraform's unit of packaging is the module: a directory of `.tf` files, called by a `module` block with a `source`. A root configuration is the module Terraform runs in; it owns a backend, configures providers and composes the modules below it. A reusable module receives what it needs through its input variables and returns what it made through its outputs.

HashiCorp's [Module composition](https://developer.hashicorp.com/terraform/language/modules/develop/composition) page argues for exactly this shape: keep the module tree flat, "with only one level of child modules", and let the module receive its dependencies from the root module rather than create or look them up itself. That is dependency inversion in Terraform's own form, the condition of [`solid.md`](../../fundamentals/rules/solid.md) condition 6: the policy (the module) depends on an abstraction it owns (its variables), and the root decides which concrete object fills it. `docs/modules.md` argues the rest, including how a module is extended without being edited.

What can be decided from source is the direction. A call that runs up (into a root configuration) or round (back to a module that called it) is a cycle, and a module that configures its own provider or backend has taken the root's job.

## Conditions

Each of these is decided by `hooks/check-terraform.py`, over the graph of local module calls (`source = "./..."` or `"../..."`), resolved from the calling directory.

1. **The graph of local module calls has no cycle.** Each edge is one `module` block; a call that reaches a module already on the path is reported, with the path. HashiCorp's documentation does not name module cycles; the condition follows from the composition page's direction (the root passes dependencies down) and from what a cycle is for an `init`: a module tree with no bottom.

2. **No module calls a root configuration.** A directory that declares a `backend` or a `cloud` block owns state and is run, not called. A call into one gives two configurations one state, or none.

3. **A reusable module declares no `provider` block and no backend.** HashiCorp: "A module intended to be called by one or more other modules must not contain any `provider` blocks", and such a module cannot be used with `count`, `for_each` or `depends_on`, nor removed without first removing its resources ([Providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)). The caller configures providers and passes them in with `providers = { ... }` where the module needs an aliased one. A backend in a module is state ownership in the wrong place, for the reason condition 2 gives.

A reusable module is a directory under `modules/`, or one that another configuration calls by a local path and that declares no backend.

## Where this stops

**Only local calls are in the graph.** A registry or git module is a dependency of a fixed version (`rules/pinning.md`), and its internals are its publisher's. A cycle through two published modules is not visible from here.

**Depth is not decided.** The composition page recommends one level of child modules "in most cases", which is a default, not a limit. A module calling a module is a reviewer's question, and `docs/modules.md` says when nesting earns its place.

**Whether a module receives its dependencies or creates them is not decided.** A module that builds its own network when it should take a subnet id as input is the composition page's central example, and telling the two apart needs to know what the caller already has. That is review, with `docs/modules.md`.

**Terraform refuses some of this on its own.** A provider block in a module called with `count` fails at plan. The hook moves that failure to the commit and extends it to every reusable module, called with `count` or not, because the next caller may be the one that adds it.
