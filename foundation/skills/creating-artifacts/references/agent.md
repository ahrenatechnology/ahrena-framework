---
name: <filename-without-md, kebab-case. A persona name is allowed here and only here.>
description: { the specialism, then when to hand work to it. Written for the caller deciding whether this is the right specialist. }
type: agent
clade: <plugin-clade>
subclade: <optional>
role: <the subject as a noun phrase, kebab-case, e.g. artifact-author>
references:
  - skills/<skill-it-orchestrates>/SKILL.md
  - rules/<rule-it-enforces>.md
  - docs/<doc-it-consults>.md
skills:
  - <plugin>:<skill-it-orchestrates>
---

# <Specialist name>

<!--
The body is the executor's system prompt, and every section below is
addressed to the executor. Why this agent exists, its history and the
arguments behind its design go to the plugin's docs/. A sentence addressed to
the maintainer does not belong here. Keep the sections in this order;
rules/completeness.md checks presence, order and the Output status line.
Delete every HTML comment in this template before committing.
-->

## What this agent is for

You are <the specialist, as a noun phrase>. <What you take and what you leave.>

<!--
Two or three sentences, addressed to the executor. A caller reads them too, to
decide whether to route here, so lead with the boundary rather than the
capability.
-->

## Before you start

Before doing anything else, invoke each of these with the Skill tool, so its procedure is in your context: `<plugin>:<skill-it-orchestrates>`.

Loading a skill is not running it: run each one only at the step of `## Procedure` that names it.

<!--
Every skill `references` points at is listed in `skills` and named here,
plugin-qualified, or the gate fails the agent (`rules/frontmatter.md`,
conditions 8 to 10). Drop this section only when the agent orchestrates no
skill.
-->

## Inputs

- `<input>`: <what it is>. Missing: return `BLOCKED` naming it.
- `<input>`: <what it is>. Missing: derive it from <source>, and say so in the output.
- `approval`: the person's answer to a `NEEDS_APPROVAL` this agent returned. Present: resume at step <N>.

<!--
Name `approval` only when a step can return `NEEDS_APPROVAL`, and give the
step a relaunch resumes at, so it does not redo the work that led to the
question.
-->

## Procedure

1. <Action>, with `<plugin>:<skill>` or <tool>. Output: <what exists after this step>.
2. <Action>. If <condition>, return `NEEDS_APPROVAL` with <what is to be approved> and stop. Output: <...>.
3. <Action>. If <condition>, go to step <N>. Output: <...>.

<!--
Each step invokes a skill, delegates, or decides (a branch, a stop, a
return). When a step would carry out a procedure itself, the procedure
belongs in a skill and the step names it; an agent's Procedure sequences
skills, it does not restate them.
-->

A step that needs a person never waits for one: a subagent's question is its
last message. It returns `NEEDS_APPROVAL` and stops; the caller asks the
person and relaunches with the answer as `approval`, and the step named in
`Inputs` is where the run resumes.

## Delegation

| Situation | `subagent_type` | Brief contains | Comes back |
|---|---|---|---|
| <when> | `<plugin>:<agent>` | <the inputs it is given> | <its first line and the fields read> |

Call each child in the foreground and read its result in the same run.

<!--
Name only an agent that exists in the marketplace. Write "None." when the
agent delegates nothing.
-->

## Done when

Do not return before <the observable completion criterion>.

<!--
Observable means a caller could check it: the pull requests exist, the gate
passes, the verdict is published.
-->

## When blocked

Blocked is <the cases that stop this run>. Return `BLOCKED` with what stopped
the run and what the caller must supply.

<!--
Name the cases: a missing input, a check still failing after the last
attempt, a decision that is not this agent's. Blocked is not a question for
the person; that is `NEEDS_APPROVAL`.
-->

## Output

Return exactly one of these, first line first.

```text
DONE
exists: <branches, pull requests, verdicts, by name or URL>
left: <what remains for the caller, or none>
```

```text
BLOCKED
blocker: <what stopped the run, naming the input or the check>
exists: <what the run left behind, or none>
needs: <what the caller must supply to relaunch>
```

```text
NEEDS_APPROVAL
approve: <what the person is asked to approve, in full>
recommendation: <the option this agent recommends, in one line>
resume: relaunch with `approval`; the run resumes at step <N>
exists: <what the run left behind so far>
```

## What it does not do

<!--
The adjacent work it will be asked for, and the agent that owns it, by
plugin-qualified name.
-->

## Example

<example>
Input: <what the caller passes, concretely>.

```text
DONE
exists: <the concrete result>
left: none
```
</example>
