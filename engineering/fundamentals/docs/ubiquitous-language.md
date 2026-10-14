---
id: ubiquitous-language
type: doc
clade: engineering
subclade: architecture
title: Why the agent speaks the client's language
summary: Why an agent conforms to the project's existing vocabulary rather than imposing its own taxonomy, why an invented folder or term is a defect, how project value overrides framework default, and where that conformance stops.
references:
  - rules/ubiquitous-language.md
  - docs/component-map.md
---

# Why the agent speaks the client's language

This is the companion to [`rules/ubiquitous-language.md`](../rules/ubiquitous-language.md). The rule states three conditions an agent must satisfy before it names or creates anything in a project; this explains what those conditions protect, why imposing a taxonomy is a defect and not a style choice, and the point past which conforming stops.

## Ubiquitous language is the client's, not ours

Ubiquitous language is Eric Evans' term from Domain-Driven Design: the single vocabulary shared by the people who own a domain and the code that models it, so that the word a stakeholder says in a meeting is the word on the class, the folder and the endpoint. Its value is that there is no translation layer between the conversation and the system, and therefore no place for a mistranslation to hide.

An agency of agents is the party most tempted to break it. An agent arrives with a framework that has its own words — `use_case`, `aggregate`, `handler` — and those words are good defaults precisely because they are DDD-literate. But they are defaults, not the domain. Barte's domain says `workflow` where the framework default says `use_case`. A payments domain may say `settlement` where a generic model says `transaction`. The domain's word is the correct one in that domain, by definition, because ubiquitous language is defined as the word the domain already uses.

So the direction of conformance is fixed. The agent reads the project's language and speaks it back. It does not read its own language and write it in. An agent that renames the client's concepts to match its framework has not tidied the codebase; it has inserted the exact translation layer that ubiquitous language exists to remove, and every future conversation now needs a glossary the agent carries in its head and nobody else has.

## Imposing a taxonomy is a defect

The sharpest form of the failure is the invented folder. An agent asked to add a feature decides, on its own authority, that the project needs a `use_cases/` directory, and creates one. No stakeholder asked for that word. No existing file used it. The project's own layout called the same concept something else, or placed it somewhere else, and now there are two vocabularies in one tree.

This is a defect in the same sense `docs/contract-first.md` uses the word: the result is not merely different, it is wrong, because it makes a false claim. A `use_cases/` folder asserts that this project organises itself around use cases. If the project organises itself around workflows, the folder is a lie about the project's own structure, and the next reader — human or agent — believes it.

The test for whether a name is the agent's to choose is simple: has the project sanctioned it? A term is sanctioned when it already appears in the project's code, its documented conventions, or its component map. A term the agent reached for because its framework likes it is not sanctioned, no matter how well-established that term is in the wider discipline. The discipline's authority ends at the project boundary; inside it, the domain's vocabulary is sovereign.

## Precedence: project value over framework default

The framework is not silent. It ships defaults — a canonical vocabulary, a default layout, default testing lanes — and those defaults are what an agent uses when it genuinely has nothing else to go on. A greenfield project with no stated conventions gets the framework's, because a considered default beats an arbitrary invention.

The precedence is one rule and it runs one way: **where the project has stated a value, the project's value wins; the framework default applies only where the project is silent.** This is not negotiable per term. The agent does not keep the framework word because it prefers it, does not merge the two vocabularies, and does not use the framework word "for consistency with other projects." Consistency across projects is not a goal; fidelity to each project's own language is. [`docs/component-map.md`](component-map.md) is where a project states those values, term by term, so that "what has the project said" is a file an agent reads rather than a judgment it improvises.

Silence is a real state and it is different from disagreement. When the component map has no entry for a concept, the framework default applies and the agent proceeds. When the component map has an entry that differs from the default, the project's entry wins and the default is discarded for that project. The agent never has to choose between them on taste, because the precedence has already chosen.

## Where this stops

**Conforming to vocabulary is not conforming to defects.** A project that has misspelled a domain term, or that uses one word for two distinct concepts, has a problem the agent may name — but it names it as a finding for the owner to decide, not by silently substituting its own word. The rule makes the agent speak the project's language; it does not make the agent pretend the language is beyond question.

**It governs names and structure, not engineering judgment.** Whether a concept should be an aggregate, whether a boundary is in the right place, whether two things should be one service — those are decided by the architecture rules in this plugin, in the project's own words. This doc only fixes whose words they are.

**It does not reach code the project did not author.** Generated files, vendored dependencies and framework scaffolding carry the vocabulary of whoever produced them, and an agent does not rename them to match the domain. The ubiquitous language governs the domain model the team owns, not every string in the tree.

**It is not a licence to skip reading.** The precedence only works if the agent actually read the project's language first. An agent that applies the framework default because it did not bother to look has not found the project silent; it has failed condition 1 of the rule. [`docs/component-map.md`](component-map.md) and the reading procedure exist so that "the project is silent" is a conclusion drawn from the map, not an excuse for not opening it.
