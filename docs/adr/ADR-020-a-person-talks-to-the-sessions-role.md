# ADR-020: A person talks to the session's role, never to a relay

- **Status:** accepted
- **Date:** 2026-11-14
- **Issue:** #310, #314

## Context

Every agent in the framework is written to be called. The entry directive that
`installing-the-agency` writes tells the session to delegate build work to
`athena`; `/round-pm` says "Invoke `themis`" and `/round-tl` "Invoke `hermes`".
In each case the session the person talks to stays generic. It calls the role as
a subagent, receives a protocol block (`DONE`, `BLOCKED`, `NEEDS_APPROVAL` with
`key: value` fields) and turns it into prose with no definition of who it is or
how it speaks.

Three costs follow. The text the person reads is a relay, written by an agent
that holds none of the role's instructions; requests to explain what the agent
itself proposed were about 36% of the owner's interventions up to 12/11/2026 and
about 44% after (`foundation/docs/person-facing-text.md`). The role's definition
is spent on being relaunched: a subagent ends when it returns, so the tech lead
carries `plan`, `approval` and `child` inputs and four steps a relaunch resumes
at. And a level of nesting is used up, which `ADR-017` showed one platform caps
at 1 by default.

`ADR-017` decided that the agency's shape is portable and each platform binds it.
It said how each platform spawns the workers. It did not say how the agent a
person talks to becomes the session itself, and the platforms differ more here
than in delegation.

## Decision

**An agent a person talks to is the session's role, declared at entry.** A
session takes one role when it starts and holds it until it ends. The role is
named by a command (`/issue-tl`, `/review-pr`, `/round-pm`, `/round-tl`) or by
the brief of a child session. The command makes the session take the role; it
does not invoke the agent. Which roles are session roles, and what such an agent
owes, is `foundation/rules/session-roles.md`.

**One definition, two readers.** As the session's role, the agent writes for the
person under `foundation/rules/person-facing-text.md`, asks its question, and
reads the answer as the person's next message in the same session; nothing is
relaunched. Called by another agent, the same definition returns the protocol it
returns today.

**Each platform binds the role its own way:**

| Platform | How a session takes a role | What the binding enforces |
|---|---|---|
| Claude Code, from a command | The command's body tells the session to read the agent's definition with Read and hold it as its own instructions until the session ends, then to run the definition's first step with the command's arguments. The command's `model` field sets the model for that turn | The definition's text only. `tools` is not applied: the session keeps its own tools, and the definition's `What it does not do` is what holds the boundary |
| Claude Code, at launch | `claude --agent <plugin>:<agent>`, or the `agent` field of a settings file, starts the session with the definition as its system prompt | The definition, its `tools` and its `model` |
| Claude Code, a child session | The brief names the role and says to read its definition first, as the command does; the model is the brief's | As for a command |
| Codex | The session reads the definition at entry: the person names the role, or the entry directive in `AGENTS.md` names it for the kind of request. A Codex custom agent remains the subagent binding of `ADR-017` | The definition's text only |
| Cursor, DeepSeek | As Codex, from their always-loaded instruction file | The definition's text only |

**A platform that cannot take a role keeps the relay, and the relay follows the
rule.** Where the session cannot read a definition at entry, it calls the agent
as a subagent, as before, and applies `person-facing-text` itself when it turns
the protocol into prose. It never pastes the protocol block. The entry directive
says so in the same line that names the agent.

**A reviewer never reviews its own session's work.** Inside a tech lead's session
the review is still delegated to a separate agent with its own context. Only a
session a person opens for a review takes the reviewer's role.

**The tech lead's session runs on `opus`.** The owner decided this on 14/11/2026,
as `foundation/rules/frontmatter.md` already asks of a lead: a wrong plan or route
costs a round of rework, which outweighs the model's price. A round's child
session that takes the tech lead's role runs on `opus` for the same reason.

## Consequences

The person reads text written by the agent that holds the role's instructions and
its rule for writing, not by a generic session translating a block. The tech
lead's definition sheds its relaunch inputs and resume steps, because the
conversation is the state. Delegation starts one level higher, so the depth that
`ADR-017` flattened for gains a level back.

On Claude Code, the command route does not apply the agent's `tools` list; only
`--agent` does. A session that took a role from a command keeps every tool the
session had, and the role's boundary rests on its text. A project that wants the
tool list enforced starts the session with `--agent`.

The protocol stays. Every session role is still callable by another agent, and
the gate keeps checking its `## Output`. What changes is that a session role also
owes a section for the person, and the gate checks that too.

A child session started by the round's Tech Lead reports to an agent, so its
report keeps the protocol's first line; a person who opens that session reads
prose. The reader decides the mode, not the agent.

## Alternatives considered

- **Keep the relay, and give the generic session the writing rule.** Rejected as
  the default. The session would write well about a plan it did not make, and the
  role would still be relaunched for every answer. It stays as the fallback for a
  platform that cannot take a role.
- **A separate person-facing agent per role.** Rejected. Two definitions of one
  role drift, and the person-facing one would hold none of the procedure it
  explains.
- **`--agent` as the only Claude Code binding.** Rejected. It applies only when a
  session starts from the command line, and the desktop app and a child session
  start sessions otherwise. It is the stricter binding where it applies, so it is
  recorded beside the command.
- **Bind each role natively per platform, with no read-in fallback.** Rejected.
  On 14/11/2026 this framework knew of no documented way to start a Codex,
  Cursor or DeepSeek session as a named agent, so there would be no binding on
  three of four platforms. A platform that gains one gets a row in the table.
