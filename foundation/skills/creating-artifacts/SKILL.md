---
name: creating-artifacts
description: Create a rule, doc, skill, agent or command for an Ahrena plugin. Use when adding any new artifact to this framework or to a plugin built on it, when unsure which of the five types a piece of content should be, or when an existing artifact fails the foundation gate and needs to be brought into shape. Also writes a skill in Anthropic's standard Agent Skills shape (claude.ai, the Skills API, a plain Claude Code plugin) when the caller asks for that shape.
type: skill
clade: foundation
references:
  - rules/pilars.md
  - rules/naming.md
  - rules/frontmatter.md
  - rules/progressive-disclosure.md
  - rules/completeness.md
  - docs/artifact-model.md
  - docs/anthropic-skill-format.md
  - skills/writing-system-prompts/SKILL.md
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

A skill the caller asks for in Anthropic's Agent Skills shape skips steps 3, 4, 6 and 7: go to step 9.

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

**An agent is written to the body skeleton**, which `docs/artifact-model.md` defines and `references/agent.md` lays out in order: role, `Before you start`, `Inputs`, `Procedure`, `Delegation`, `Done when`, `When blocked`, `Writing to a person` for a session role, `Output`, `What it does not do`, `Example`. An agent a person talks to is a session role ([`session-roles.md`](../../rules/session-roles.md)): its role takes the session, so it opens with who it is, whom it works for and the business result it protects, and it writes for the person as well as returning the protocol to a caller. The body is the executor's system prompt, so write each section as an instruction to the executor ("You are…", "Do not return before…"), not as an argument for the agent. Rationale, history and anything addressed to a maintainer go to the plugin's `docs/`.

Three parts of it fail most often:

- **A step that waits for a person.** A subagent cannot. The step returns `NEEDS_APPROVAL` and stops, `Inputs` names the answer the caller relaunches with (`approval`), and `Procedure` names the step the run resumes at.
- **Delegation to an agent that does not exist.** Name the `subagent_type` plugin-qualified, as the Agent tool lists it, and check it is in the marketplace.
- **An output described in prose.** `Output` holds one fenced template per status, each opening with `DONE`, `BLOCKED` or `NEEDS_APPROVAL`, and `Example` shows one real input and the output returned for it, inside `<example>` tags.

`rules/completeness.md` checks the sections, their order, the status lines and the tags on every agent (conditions 3 and 5 to 7); `rules/frontmatter.md` checks `tools` and `model` (conditions 11 and 12) and `rules/naming.md` that every delegated agent exists (conditions 9 and 10). Whether the steps are executable is for `reviewing-artifacts`.

**Write the body of an agent or a skill with `writing-system-prompts`.** Once the template is copied and the frontmatter filled, invoke `ahrena-foundation:writing-system-prompts` with the Skill tool and follow it through step 10 for the body: the success criterion, the steps, delegation, the stop paths, the output template, the three controls, the example and the adversarial cases. Then come back here at step 5. Run its step 11 after step 8 here, on the finished artifact. A rule, a doc or a command has no executor to write for and skips this.

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

`references` loads nothing on any platform. An agent also lists every skill it references in `skills`, as `<plugin>:<skill>`, and names each one in its `## Before you start` section with the instruction to invoke it with the Skill tool. `rules/frontmatter.md` states both and the gate checks them.

## 8. Run the gate

```sh
python3 <plugin>/hooks/validate-artifacts.py [repo-root]
```

In this repository that is `python3 foundation/hooks/validate-artifacts.py`. It walks every plugin listed in the marketplace, exits non-zero, and names the rule behind each failure. Run it before committing, not after CI does.

## 9. Write a skill in Anthropic's shape when the caller asks for it

The caller states the shape. A request that asks for a skill and does not say "Anthropic", "Agent Skills", claude.ai, the Skills API or a plain Claude Code plugin gets the framework shape, and steps 1 to 8 apply unchanged. A request that does ask for it gets this step in place of steps 3, 4, 6 and 7; the shapes never mix.

1. Read `docs/anthropic-skill-format.md` for the fields, the limits and the layout. The caller gives the destination folder; a skill in this shape never goes under a marketplace plugin's `skills/`, because `validate-artifacts.py` would read it as a framework skill and fail it for the missing framework fields.
2. Pick the profile: `portable` unless the caller says the skill is for Claude Code alone and needs a Claude Code field.
3. Name it as the format asks, not as `rules/naming.md` asks: lowercase letters, numbers and single hyphens, at most 64 characters, neither `anthropic` nor `claude` in it, equal to the folder name. A gerund first token is recommended, not required.
4. Copy `references/anthropic-skill.md` to `<destination>/<name>/SKILL.md`, drop the trailing comment, and fill in `name` and `description`. The frontmatter holds those two fields and, only when the skill needs them, the optional fields of the chosen profile. Write the `description` in the third person: what the skill does, then "Use when" and the situations that trigger it.
5. Write the body for its executor, through `ahrena-foundation:writing-system-prompts`, under 500 lines. Put material read on demand in `references/`, code that runs in `scripts/` and templates in `assets/`, and link each file straight from `SKILL.md`.
6. Run the checker and fix what it names before handing the folder back:

```sh
python3 <plugin>/hooks/validate-anthropic-skill.py [--profile claude-code] <destination>/<name>
```

In this repository that is `python3 foundation/hooks/validate-anthropic-skill.py`.

## When this skill does not apply

Editing the body of an artifact that already exists and already passes. Only the steps that touch frontmatter, naming or references are relevant then, and the gate covers those.
