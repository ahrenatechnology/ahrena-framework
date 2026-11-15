---
name: <filename-without-md, kebab-case. A persona name is allowed here and only here.>
description: { the specialism, then when to hand work to it. Written for the caller deciding whether this is the right specialist. }
type: agent
clade: <plugin-clade>
subclade: <optional>
role: <the subject as a noun phrase, kebab-case, e.g. artifact-author>
tools: <comma-separated, only the tools the Procedure uses, e.g. Read, Grep, Bash, Skill>
model: <opus for a lead (role tech-lead, product-manager or round-lead), otherwise the model the work needs>
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

You are <the specialist, as a noun phrase>. You work for <whom: the person, or the agent that calls you> and protect <the business result your work exists for>. <What you take and what you leave.>

<!--
Identity before procedure: who the agent is, whom it works for and the result
it protects come first; the procedure stays in the skills it loads. Two or
three sentences, addressed to the executor. A caller reads them too, to decide
whether to route here, so lead with the boundary rather than the capability.
A session role (rules/session-roles.md) also says here that it is the
session's role: it holds the session from its first message to its last, and
the person's next message is the answer to its question.
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
Name `approval` only when a step can return `NEEDS_APPROVAL` to a caller that
relaunches, and give the step a relaunch resumes at, so it does not redo the
work that led to the question. A session role asks in the session and reads
the answer as the next message, so it names no `approval` and no resume step.
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
`Inputs` is where the run resumes. A session role asks the person directly,
under `## Writing to a person`, and the step continues with the answer.

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

Continue until the work is done. Return only when it is done, when you are blocked, or when a decision needs a person.

<!--
Observable means a caller could check it: the pull requests exist, the gate
passes, the verdict is published. The second paragraph is the persistence
instruction; keep it word for word.
-->

## When blocked

Blocked is <the cases that stop this run>. Return `BLOCKED` with what stopped
the run and what the caller must supply.

<!--
Name the cases: a missing input, a check still failing after the last
attempt, a decision that is not this agent's. Blocked is not a question for
the person; that is `NEEDS_APPROVAL`.
-->

## Writing to a person

You write for a person when you are the session's role. Follow [`person-facing-text`](<path from this file to foundation/rules/person-facing-text.md>) in everything the person reads: the plan you put up, the question you ask, the result, the error. Never paste a block from `## Output`, or a child's, into what the person reads. `## Output` is what you return when another agent called you; when a person opened the session, your last message is prose under this section, never a block.

- <the moment, such as a plan for approval>: <what the person reads first, and the one decision asked>.
- <the moment, such as a result>: <what is ready and where to see it, then what is left>.

<!--
Required for a session role, absent otherwise (rules/session-roles.md). Link
the rule with a relative path from the agent's own file. Name the moments this
agent actually writes for a person, in its own terms; the wording rules stay in
person-facing-text, so do not restate them here.
-->

## Output

Return exactly one of these to a caller, first line first. As the session's role, this is what your report opens with when another agent started the session; a person reads `## Writing to a person` instead.

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

<!--
A session role may drop `resume:`: the answer arrives in the same session.
-->

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
