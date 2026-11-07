---
id: artifact-model
type: doc
clade: foundation
title: The artifact model
summary: Why the framework has five artifact types, how to choose between them, and why authority runs in one direction.
references:
  - rules/pilars.md
  - rules/naming.md
  - rules/frontmatter.md
  - rules/completeness.md
---

# The artifact model

This is the reference for four of the five foundation rules: `rules/pilars.md`, `rules/naming.md`, `rules/frontmatter.md` and `rules/completeness.md`. They state what is checked; this states why. The fifth, `rules/progressive-disclosure.md`, has its own companion in `docs/context-budget.md`.

## Five types, one job each

Every piece of content the framework ships is exactly one of five things.

| Type | Job | The question it answers |
|---|---|---|
| **rule** | An unbreakable guardrail. | What may I never do? |
| **doc** | A reference manual. | What do I need to know to decide? |
| **skill** | A repeatable procedure. | How do I carry this out? |
| **agent** | A specialist that orchestrates skills. | Who does this kind of work? |
| **command** | An entry point. | How does a person start it? |

The list is closed. A sixth type is not a gap to fill, it is a sign that something is being written at the wrong altitude.

## Choosing a type

Take the candidate and ask, in order:

1. **Can it be violated?** If the answer is "yes, and the result is defective," it is a rule. If the answer is "yes, and the result is merely different," it is not.
2. **Does it have steps?** A procedure with an order and an end state is a skill. A body of knowledge with no order is a doc.
3. **Does it choose between skills?** Something that decides which procedure applies, and in what sequence, is an agent.
4. **Is a person typing it?** An invocation surface is a command. It holds no logic of its own.

Most mistakes are a rule that should be a doc. The test is the first question. "Prefer composition over inheritance" fails it: both produce working code, so it is guidance, and guidance belongs in a doc. "A concrete type never raises `NotImplementedError`" passes it: the result is a type that lies about its interface.

## Authority runs one way

The five types form a hierarchy, and references may only run along it.

```
command  ──▶  skill, agent
agent    ──▶  skill, doc, rule, agent
skill    ──▶  rule, doc, skill
doc      ──▶  doc, rule
rule     ──▶  doc
```

Three consequences are worth naming.

**A command references no rule and no doc.** A command that reads a rule has become a procedure, and the procedure should have been a skill it invokes. Keeping commands thin is what makes them cheap to add.

**A rule references only a doc, and only for rationale.** Nothing may contradict a rule, so a rule that leans on a skill would invert the hierarchy: the guardrail would depend on the thing it constrains.

**A rule carries no rationale of its own.** Rationale is what makes a rule long, and a long rule is one nobody loads. The rule states the condition and links here. This document is that link for the three foundation rules.

## Why references are untyped

A reference is a path in the `references` list, with no verb attached. There is no `applies`, `consults` or `extends`.

The verb is already determined by the pair of types. A skill pointing at a rule applies it; there is nothing else a skill can do with a rule. A skill pointing at a doc consults it. Writing the verb down adds a second source of truth that can disagree with the first, and the gate would then have to decide which one is right.

If a pair of types ever admits two genuinely different relationships, the verb earns its place. Until then it is a field to maintain and a field to get wrong.

## Why an agent names its skills three times

`references` is this framework's field. The gate reads it to check the matrix above, and a person reads it to see what an agent depends on. No platform reads it: Claude Code ignores a frontmatter field it does not recognise without reporting it, and none of the other three documents a field by that name. An agent that names a skill only in `references` runs without that skill unless the model happens to invoke it, which is how every agent in this corpus ran until #252.

Two routes do load a skill, and an agent takes both.

**The preload field.** Claude Code's `skills` frontmatter injects the full content of each listed skill into the subagent at startup. A plugin's components are namespaced by the plugin, so the entry is `<plugin>:<skill>`, the name the Skill tool lists, not the path `references` uses. A skill that sets `disable-model-invocation: true` cannot be preloaded. Source: [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents).

**The body instruction.** It is the only route the other three platforms have, and it is the fallback on Claude Code when a preload does not take. No other platform documents a field that loads a skill into an agent:

- Codex defines a custom agent in TOML with `name`, `description` and `developer_instructions`. Its skills inherit from the parent, and `skills.config` only disables one. Source: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- Cursor's subagent frontmatter is `name`, `description`, `model`, `readonly` and `is_background`; nothing attaches a skill. Source: [Cursor subagents](https://cursor.com/docs/context/subagents).
- DeepSeek discovers skills by directory and spawns sub-agents with a tool call; it has no agent definition file to carry a field. Source: [DeepSeek TUI README](https://docs.rs/crate/deepseek-tui/0.3.16/source/README.md) and the install mapping in this repository's `ARCHITECTURE.md`.

The preload is the stronger route and the instruction the portable one. Either alone leaves a platform or a failure mode uncovered, so `rules/frontmatter.md` requires both and the gate checks that they agree with `references`.

## Why some rules ship a hook and others do not

A rule is only as strong as what checks it. Two routes exist, and the rule declares which one it takes in its `enforcement` field.

**`enforcement: hook`** means the condition is mechanically decidable, and a script in `hooks/` decides it. The rule costs no context, and it cannot be skipped by an agent that did not read it.

**`enforcement: judgment`** means the condition needs a reader. The rule's one-line `statement` goes into the platform's instruction file with a link to its full text, and nothing else does.

Declaring `judgment` is allowed. Declaring `judgment` for something that is decidable is how a framework fills up with rules that nobody enforces, so the review question for every new rule is whether a script could have decided it.

## What makes an artifact complete

An artifact is authored by filling a template, and that decides which defects survive to review. They are not subtle ones: they are the parts of the template nobody filled.

**A leftover marker or bracket is the most common.** `TODO`, `TBD`, and an unreplaced `<noun phrase, title case>` in a title all pass a schema check, because the field is present and non-empty. Only reading catches them, and reading is the expensive thing. So `rules/completeness.md` makes the gate read for them instead.

The scan skips code, and that is not a compromise. `<plugin>` and `<name>` on a command line are what the reader is meant to substitute, and a backticked `TODO` is prose about markers rather than a marker. Every angle bracket in this corpus is one of those two, which is why scanning code would fail nothing real and reject everything honest.

**A missing section is the other.** Each type owes its reader a fixed set: a rule owes its conditions and its boundary, a skill owes the cases it does not handle, an agent owes what it refuses and the skeleton below. These are not formatting preferences. The boundary section is what separates a rule from dogma, and the "does not apply" section is what stops a skill being reached for in the wrong situation. An artifact that drops them is not shorter, it is incomplete.

Fixed headings also let a reader skim a corpus they have never seen, and let the gate check presence without understanding content.

## The agent body skeleton

An agent body is a system prompt, and its reader is the model that runs it, often as a subagent with nobody to ask. So the body instructs the executor, in this order, under these `##` headings:

1. **What this agent is for.** The role, in two or three sentences, addressed to the executor: "You are…". A caller deciding whether to route here reads it too, so it leads with the boundary.
2. **Before you start.** The instruction to invoke each orchestrated skill with the Skill tool before doing anything else, exactly as conditions 8 to 10 of `rules/frontmatter.md` require, and the reminder that loading a skill is not running it: each one runs at the `Procedure` step that names it. An agent that orchestrates no skill has no such section.
3. **Inputs.** What the caller passes, and for each one what to do when it is missing: return `BLOCKED` naming it, or derive it and say how.
4. **Procedure.** Numbered steps. Each states the action, the skill or tool it uses, and what the step outputs. A branch is explicit: "if the plan is not approved, go to step 2". A step that applies a rule names it.
5. **Delegation.** A table: the situation, the exact `subagent_type`, plugin-qualified (`ahrena-engineering-quality:argos`), what the brief contains, and what comes back. "None" when the agent delegates nothing. A child is called in the foreground and its result read in the same run.
6. **Done when.** The completion criterion, phrased "Do not return before …".
7. **When blocked.** What counts as blocked, and what to return when it is.
8. **Output.** A literal template in a fenced block, one per status the agent can return. The first line is `DONE`, `BLOCKED` or `NEEDS_APPROVAL`; the fields after it are what the caller reads: what exists (branches, pull requests, verdicts), what is left, and for `NEEDS_APPROVAL` what is to be approved, the recommendation, and how the run resumes.
9. **What it does not do.** The adjacent work it will be asked for, and who owns it.
10. **Example.** At least one worked example, the input and the output the agent returns, inside `<example>` tags.

**No agent waits for a person mid-run.** A subagent cannot hold a conversation: a question it asks is its final message, and the run is over. So a step that needs a person's approval returns `NEEDS_APPROVAL`, with what is to be approved and the agent's recommendation, and stops. The caller asks the person and relaunches the agent with the answer as an input. `Inputs` names that input (`approval`, say), and `Procedure` says at which step a run resumes when it is present, so a relaunch does not redo the work that led to the question.

**The body addresses the executor only.** Why an agent exists, its history and the arguments behind its design go to the plugin's `docs/`. A sentence addressed to the maintainer, such as one explaining why an agent carries both a handle and a role, costs every run its tokens and tells the executor nothing it can act on.

The fixed status line and fixed headings are what let a caller read the result without parsing prose, and let `rules/completeness.md` check presence, order and the status line. Whether the steps are executable is read by `skills/reviewing-artifacts/SKILL.md`.

## Where this stops

The model governs artifacts, not code. A bounded context, a module layout or a class design is the subject of an artifact, never an artifact itself.

It also says nothing about quality. A rule that passes every check in `hooks/validate-artifacts.py` can still be a bad rule. The gate protects the shape of the corpus; the review protects its content.
