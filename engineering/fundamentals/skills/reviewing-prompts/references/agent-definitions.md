# Agent, skill and command definitions

Opened by step 1 of `SKILL.md` when the `agent-definitions` route fires. The body of such a file is read against `instructions.md`; these conditions cover what is specific to a definition a platform loads by name or by description.

A definition has two readers. The first is whatever decides whether to load it, and that reader sees the name and the description and nothing else. The second is the model that runs it, and for a subagent that model starts with the body and the caller's message and no other context.

## The part that decides whether it loads

### DEF-1 A description that states capability and not occasion

- **State:** the description says what the artifact is or can do, and names no situation in which to reach for it: "reviews code", "helps with deployments".
- **Detect:** read the description alone. List the situations it names. An empty list is the state.
- **Exempt:** a command invoked only by a person typing its name.
- **Correct:** open with what it does in one clause, then the situations: the request, the file type, the event that should select it.

### DEF-2 A description that fires on its neighbour's work

- **State:** two definitions the same reader can load whose descriptions name the same situation, or one whose description is wide enough to cover any request.
- **Detect:** list the other agents, skills and commands the reader holds, from the tree and the plugin manifests. Compare the situations each description names.
- **Exempt:** two definitions that state, each in its own description, which case goes to the other.
- **Correct:** narrow the description to its own case and name the neighbour for the adjacent one.

### DEF-3 A description that does not match the body

- **State:** the description promises something the body does not do, or the body does something the description would never lead a caller to expect, such as publishing, committing or deleting.
- **Detect:** read the description, then the body, then the description again.
- **Exempt:** none.
- **Correct:** rewrite the description from the body as it now is. When the change edited one of the two, the other is the stale one.

## The part the model runs

### DEF-4 A subagent that assumes the caller's context

- **State:** the body of an agent that runs in its own context refers to what "the user asked", to files "already read", or to a plan, as though it had seen the conversation.
- **Detect:** read the body as a model holding nothing but it and one message from a caller.
- **Exempt:** an agent the platform runs in the caller's own context.
- **Correct:** say what the caller must supply, and what the agent does when it is missing.

### DEF-5 No statement of what comes back

- **State:** the body does not say what the result looks like or what is deliberately left to the caller. A caller cannot tell a finished run from an abandoned one, or a verified claim from a guess.
- **Detect:** look for the shape of the result and for how the agent marks what it did not check.
- **Exempt:** a command whose effect is the result.
- **Correct:** state the result's shape, and that anything not verified is marked as such.

### DEF-6 No boundary

- **State:** the body says what the agent does and never what it does not, so adjacent work lands on it by default.
- **Detect:** look for the adjacent requests the agent will receive and where each goes.
- **Exempt:** a skill whose description already confines it to one narrow procedure.
- **Correct:** name the nearest two or three cases it should refuse and who owns each.

### DEF-7 Steps where a choice was needed, or a choice where steps were needed

- **State:** an agent whose body is a fixed sequence of steps it carries out itself, or a skill whose body only picks between other skills.
- **Detect:** ask whether the body selects a procedure or is one.
- **Exempt:** a platform that has only one of the two kinds.
- **Correct:** move the steps into a skill the agent invokes, or turn the selecting skill into an agent.

### DEF-8 A body that restates what it could point at

- **State:** the body copies a rule, a checklist or a procedure that lives in another file the reader can open. The copies drift, and the body pays for the text on every run.
- **Detect:** search the tree for the paragraphs the change added.
- **Exempt:** a one-line summary beside the pointer.
- **Correct:** name the file and the step that opens it.

## Tools and settings

### DEF-9 A tool list that does not match the task

- **State:** the definition declares tools the body never uses, or the body tells the model to do something no declared tool can do.
- **Detect:** list the actions the body asks for and the tools the frontmatter grants, and compare.
- **Exempt:** a platform where an omitted tool list means the caller's tools, when the body relies on that and says so.
- **Correct:** make the two lists agree. Whether a granted tool is too powerful is LLM-8 in `skills/reviewing-model-use/SKILL.md`.

### DEF-10 A model or effort setting with no reason

- **State:** the definition pins a model or an effort level, and neither the file nor the pull request says why. The pin outlives the reason and nobody knows whether it may be changed.
- **Detect:** the frontmatter's model and effort fields, read against the description of the change.
- **Exempt:** a pin the repository's documents require for every definition.
- **Correct:** state the reason beside the pin, or remove it.
