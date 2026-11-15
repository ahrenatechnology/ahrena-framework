---
id: session-roles
type: rule
clade: foundation
title: An agent a person talks to is the session's role
statement: An agent whose role is a session role has a Writing to a person section that links person-facing-text, beside the protocol it returns to a caller.
enforcement: hook
enforced-by: hooks/validate-artifacts.py
references:
  - docs/person-facing-text.md
---

# An agent a person talks to is the session's role

Some agents are talked to by a person. The session takes their role when it starts and holds it until it ends, so the text the person reads is written by the agent that holds the role's instructions, not relayed by a generic session. This repository's `ADR-020` records the decision and how each platform binds it.

Such an agent has two readers in one definition. As the session's role it writes for a person, under [`person-facing-text`](person-facing-text.md), and reads the answer to its question as the person's next message. Called by another agent, it returns the protocol of its `## Output`, as every agent does.

## The session roles

An agent is a session role when its `role` is one of these:

| `role` | Agent a person talks to |
|---|---|
| `tech-lead` | the tech lead of an issue |
| `review-orchestrator` | the reviewer, in a session a person opens for a review |
| `product-manager` | the PM of a round |
| `round-lead` | the Tech Lead of a round |

The list is closed so the gate can decide it. A new session role is an amendment to this rule, made together with the agent's person section and the command that makes a session take it.

## Conditions

Each of these is decided by `hooks/validate-artifacts.py`.

1. An agent whose `role` is a session role has a `## Writing to a person` section, outside code, placed after `## When blocked` and before `## Output`.
2. That section links `person-facing-text.md` as a Markdown link, outside inline code.
3. A `NEEDS_APPROVAL` template in a session role's `## Output` may omit `resume:`. The other agents keep it, as condition 6 of [`completeness.md`](completeness.md) says.

## Where this stops

**Presence, not substance.** The gate checks that the section exists and points at the writing rule. Whether the agent opens with who it is, whom it works for and the business result it protects, and whether the section says what the person reads at each moment, is read by [`reviewing-artifacts`](../skills/reviewing-artifacts/SKILL.md).

**It does not say how to write.** The wording of what a person reads is [`person-facing-text`](person-facing-text.md)'s. This rule makes a session role reach it.

**It does not make a session.** A command or a child session's brief makes a session take a role; the binding per platform is `ADR-020`'s. An agent outside the list can still be talked to directly; it is held to nothing here until its role joins the list.

**A reviewer never reviews its own session's work.** That is a judgment the gate cannot see: inside a tech lead's session, review is still delegated to a separate agent with its own context.
