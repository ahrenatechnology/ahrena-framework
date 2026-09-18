---
name: creating-artifacts
description: Create a rule, doc, skill, agent or command for an Ahrena plugin. Use when adding any new artifact to this framework or to a plugin built on it, when unsure which of the five types a piece of content should be, or when an existing artifact fails the foundation gate and needs to be brought into shape.
type: skill
clade: foundation
references:
  - rules/pilars.md
  - rules/naming.md
  - rules/frontmatter.md
  - rules/progressive-disclosure.md
  - rules/completeness.md
  - docs/artifact-model.md
---

# Creating artifacts

## 1. Decide the type before writing anything

Ask, in order, and stop at the first yes.

1. **Can it be violated, and is the result defective?** → **rule**
2. **Does it have ordered steps and an end state?** → **skill**
3. **Does it choose between skills?** → **agent**
4. **Is it an invocation surface a person types?** → **command**
5. Otherwise → **doc**

If the first question gets "yes, and the result is merely different," it is not a rule. That is the mistake this step exists to catch. `docs/artifact-model.md` works the distinction through.

Write the type down before opening a file. Reclassifying after the body is written produces an artifact shaped like the type it started as.

## 2. Split rationale out of a rule

A rule states conditions. If the draft explains *why*, that prose belongs in a doc, and the rule references it.

This means most rules arrive as a pair. Create the doc first so the rule has something to reference, then the rule.

## 3. Name it and place it

Read `rules/naming.md` before choosing a name. The three failures that recur:

- a type prefix (`rule-naming`)
- a clade prefix (`foundation-naming`)
- a skill named as a noun (`artifact-creation` instead of `creating-artifacts`)
- an agent given only one name. An agent declares a handle in `name` and its subject in `role`, and a persona name is allowed in the first and nowhere else.

Place it flat in its type directory. A skill is `skills/<name>/SKILL.md` and nothing deeper.

## 4. Copy the template

| Type | Template |
|---|---|
| rule | `references/rule.md` |
| doc | `references/doc.md` |
| skill | `references/skill.md` |
| agent | `references/agent.md` |
| command | `references/command.md` |

Fill every field, and keep the sections the template gives you. `rules/completeness.md` fails a leftover marker or an unreplaced `<placeholder>`, and fails a missing required section, so an unfinished copy does not reach review.

What the gate cannot check is whether a section that exists says anything. A `Where this stops` reading "use judgment" passes condition 3 and still tells the reader nothing.

## 5. Put the material where the step reads it, not in the body

A skill or agent body is paid in full every time the artifact fires, so only the line a person types belongs inline. `rules/progressive-disclosure.md` caps a code block there at 10 lines.

Anything copied and edited goes in `references/`. Anything executed goes in `scripts/`. Then name the file in the step that opens it, because the gate also fails material that no step can reach.

## 6. Declare enforcement, for a rule only

Ask whether a script could decide the condition.

**Yes** → `enforcement: hook`, and write the hook. A rule declared as a hook whose hook does not exist fails the gate.

**No** → `enforcement: judgment`, and write the `statement` so it stands alone in an instruction file, because that line and a link are all the agent will see.

Reaching for `judgment` because the hook is work is how the corpus fills with rules nothing enforces. If the condition is decidable, it is a hook.

## 7. Wire the references

List plugin-relative paths in `references`. Check the pair against the matrix in `rules/pilars.md` before adding one. Commands reference only skills and agents; rules reference only docs.

A mention in prose is not a reference. Only declare a dependency the artifact actually has.

## 8. Run the gate

```sh
python3 <plugin>/hooks/validate-artifacts.py [repo-root]
```

In this repository that is `python3 foundation/hooks/validate-artifacts.py`. It walks every plugin listed in the marketplace, exits non-zero, and names the rule behind each failure. Run it before committing, not after CI does.

## When this skill does not apply

Editing the body of an artifact that already exists and already passes. Only the steps that touch frontmatter, naming or references are relevant then, and the gate covers those.
