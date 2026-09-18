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

## References are plugin-relative

A path in `references` is relative to the plugin root and may not escape it. `docs/artifact-model.md` is valid; `../other-plugin/docs/x.md` and `/foundation/docs/x.md` are not.

Cross-plugin references are not expressible today because there is one plugin. When a second plugin needs to reference this one, the addressing form is decided then, and this rule grows a sixth condition. It does not grow one now.

## Where this stops

The matrix governs references, not mentions. A doc may discuss a skill in prose, name it and explain when it applies. What it may not do is put that skill in its `references` list, because that declares a dependency the hierarchy does not allow.

The rule also says nothing about whether the artifact is any good. A well-shaped artifact with wrong content passes every condition here.
