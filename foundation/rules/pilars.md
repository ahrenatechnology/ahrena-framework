---
id: pilars
type: rule
clade: foundation
title: Artifact types and authority
statement: An artifact is exactly one of five types and references only what its type permits.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/artifact-model.md
---

# Artifact types and authority

## The closed set

An artifact is a **rule**, a **doc**, a **skill**, an **agent** or a **command**. There is no sixth type, and no artifact is two types at once.

The type is declared in frontmatter and is determined by location. `rules/` holds rules, `docs/` holds docs, `skills/` holds skills, `agents/` holds agents, `commands/` holds commands. A declared type that disagrees with the directory is a failure, not a preference.

## The reference matrix

An artifact may reference only the types its own type permits.

| From | May reference |
|---|---|
| **rule** | doc |
| **doc** | doc, rule |
| **skill** | rule, doc, skill |
| **agent** | rule, doc, skill, agent |
| **command** | skill, agent |

Every other pair is a failure. The three that are asked for most often, and are still failures:

- **command → rule** or **command → doc.** The command has absorbed a procedure. Move it into a skill and invoke that.
- **rule → skill.** The guardrail now depends on what it constrains.
- **doc → skill.** A reference manual that drives a procedure is a procedure.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. The `type` field is one of the five. Any other value fails.
2. The `type` field matches the directory the artifact lives in.
3. Every path in `references` resolves to a file that exists.
4. Every path in `references` points at a type the matrix permits.
5. Every relative markdown link in the body resolves to a file that exists.
6. A rule declares `enforcement`, and when it declares `hook` the file named in `enforced-by` exists.
7. A reference that crosses plugins names its target's plugin, and that plugin is one the marketplace lists.
8. The plugin dependency graph those references form is acyclic.

## How a reference addresses its target

**Inside one plugin, a reference is a path from the plugin root.** `docs/artifact-model.md` is valid; `/foundation/docs/x.md` and anything containing `..` are not. This is the ordinary case and it does not change.

**Across plugins, a reference is `<plugin>:<path>`.** `ahrena-engineering:docs/simplicity.md` names the plugin, then the same plugin-relative path. The plugin is named as the **marketplace** names it, not as its directory is spelled, because the marketplace name is the identity that survives installation — a consumer who installs two plugins gets whatever on-disk layout the platform chooses, and a relative path between them resolves only in this repository.

Three things follow, and the gate decides all three. A qualified reference naming a plugin the marketplace does not list fails, because the edge points nowhere. A qualified reference into the artifact's own plugin fails, because one thing gets one spelling. And **the matrix above applies unchanged** — a rule may reference a doc in another plugin for exactly the reasons it may reference one in its own, and may not reference a rule in either.

**Crossing plugins is a dependency, so the graph of them is acyclic.** Two plugins that reference each other cannot be installed one at a time and neither can be read first. Today `ahrena-engineering-python` depends on `ahrena-engineering`, which depends on `ahrena-foundation`, and nothing points back.

## A body link is not a reference

Condition 5 checks markdown links in the body, and it resolves them from the file rather than from the plugin root. A link into another plugin is therefore an ordinary relative path — `../../engineering/rules/solid.md` — and it works the way every other link works: it resolves on disk, it opens on GitHub, and the gate fails it when the target is renamed.

This is the route for the case the matrix refuses. A rule may not *reference* another rule, in its own plugin or anywhere else, because a declared reference is a load edge and a rule that drags another rule into context has doubled the cost of both. Naming one in prose costs nothing and is already how `duplication.md` cites `yagni.md`. Crossing a plugin boundary changes the path and changes nothing else.

## Where this stops

The matrix governs references, not mentions. A doc may discuss a skill in prose, name it and explain when it applies. What it may not do is put that skill in its `references` list, because that declares a dependency the hierarchy does not allow.

**The gate validates a marketplace, not an installation.** It sees every plugin the catalogue lists and can therefore resolve every qualified reference. A consumer who installs `ahrena-engineering-python` and not `ahrena-engineering` has a dangling edge, and nothing here detects it — the installed set is the platform's business and this repository never sees it. Conditions 7 and 8 keep the catalogue coherent, which is the most a gate that runs before distribution can promise.

**Nothing here orders the plugins.** Acyclic is the only shape required; no artifact declares a layer, and a plugin may reference any other it does not already sit downstream of. Three plugins do not justify a layering vocabulary, and the first time two of them disagree about which is lower is the moment to invent one.

The rule also says nothing about whether the artifact is any good. A well-shaped artifact with wrong content passes every condition here.
