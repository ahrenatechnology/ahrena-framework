---
id: ubiquitous-language
type: rule
clade: engineering
subclade: architecture
title: The project's language wins
statement: Before naming or creating anything, read the project's ubiquitous language and conventions; the framework default applies only where the project is silent.
enforcement: judgment
references:
  - docs/ubiquitous-language.md
  - docs/component-map.md
---

# The project's language wins

Three conditions, each naming a state a reader can observe in the change and the project's own map. None is a parse a script in this plugin could run, because deciding them needs the project's component map and its sanctioned vocabulary, which this plugin does not have and must not guess — the final section says why that makes this a judgment rule. [`docs/ubiquitous-language.md`](../docs/ubiquitous-language.md) explains what the conditions protect; [`docs/component-map.md`](../docs/component-map.md) defines the file they read.

The subject is direction. An agent carries a framework vocabulary, and a project carries its own. The two meet whenever the agent names a file, a type, a folder or a concept, and only one of them can be right in the project's domain. The project's is, by the definition of ubiquitous language: the correct word for a concept in a domain is the word that domain already uses. So the agent reads the project's language and conforms to it, and reaches for the framework default only where the project has said nothing.

## Conditions

1. **The agent read the project's ubiquitous language before it named or created anything.** The state is that the project's component map and its existing conventions were consulted ahead of the first name chosen or folder created — not after, and not skipped. Decided by a reviewer checking that the vocabulary and layout the change uses trace to the project's map or existing code, rather than to the framework's defaults applied without a look. An agent that defaulted without reading has not found the project silent; it has failed this condition.

2. **Where the project's term and the framework default differ, the change uses the project's term.** The state is a concept the project's glossary maps to a word of its own, named in the change by that word and not by the canonical default. Decided by a reviewer comparing each domain name the change introduces against the project's glossary: a `use_case` written where the glossary says `workflow` is a failure, regardless of how standard `use_case` is elsewhere. The project's value wins per concept, and is never merged with the default.

3. **The change invents no folder or term the project has not sanctioned.** The state is a directory or a domain term created on the agent's own authority, absent from the project's code, its documented conventions and its component map. Decided by a reviewer checking every new folder and coined term against the project's sanctioned set: a fresh `use_cases/` directory in a project whose layout names no such folder is a failure, because it asserts a structure the project does not have. Silence licenses the framework default, not an invention.

## Where this stops

**This rule governs vocabulary and structure, not engineering judgment.** Whether a concept should be an aggregate, where a boundary belongs, whether two things are one service — those are decided by the other architecture rules in this plugin, in the project's words. This rule fixes only whose words are used, never what the words should describe.

**Conforming to the project's language is not conforming to its mistakes.** A misspelled domain term, or one word used for two distinct concepts, is a problem the agent may raise as a finding for the owner to settle. It does not license the agent to substitute its own word silently; naming the defect is conformance, overwriting it is not.

**Silence is a real state, and the framework default is the right answer to it.** A project that has stated no term, no folder and no convention for a concept gets the framework's, because a considered default beats an arbitrary invention. The failure in condition 1 is not using a default; it is using one without having read the map to confirm the project was silent.

**This rule declares judgment rather than a hook, and the reason is structural.** Every condition above is decidable, but each needs the same two inputs — the project's component map and its sanctioned vocabulary — and both live in the consuming project, not in this plugin. A hook shipped here would have to hard-code where a project keeps its map and what counts as a sanctioned term, and the first project that arranged itself differently would get a gate that is confidently wrong about the very thing this rule protects: the project's own language. `docs/simplicity.md` records that a confidently wrong gate is the one that gets switched off. So the rule takes the judgment route, its statement is injected, and its detector is a reviewer reading the change against the project's map. The reading procedure a conforming agent runs is the skill `reading-the-component-map`.
