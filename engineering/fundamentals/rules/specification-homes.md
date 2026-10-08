---
id: specification-homes
type: rule
clade: engineering
subclade: architecture
title: Where a specification lives
statement: A specification sits in docs/ under its context and then its kind, and an entity specification carries the header and seven sections of its template.
enforcement: hook
enforced-by: hooks/check-specifications.py
references:
  - docs/specification-homes.md
---

# Where a specification lives

Seven conditions, all decided by `hooks/check-specifications.py` over the consuming project's tree. [`docs/specification-homes.md`](../docs/specification-homes.md) argues the layout, the closed set of kinds and the seven sections; this states them, once.

A specification is a document that says what a part of the system is before, and while, code says how. It is written to be found by somebody who did not write it, so its address is not a preference.

## The homes

```
docs/
└── <context>/
    ├── entities/        one file per entity: <entity>.md
    ├── contracts/       the machine-readable contracts the context publishes
    ├── capabilities/    one file per capability
    └── metrics/         what the context is measured by
```

| Kind | Home | What it specifies | Its content is owned by |
|---|---|---|---|
| **entity** | `docs/<context>/entities/<entity>.md` | one aggregate root, entity or value object of the model | conditions 3 to 7 here, and the template in `skills/writing-entity-specifications` |
| **contract** | `docs/<context>/contracts/` | an API description, an event schema, an IDL | [`contract-first.md`](./contract-first.md) |
| **capability** | `docs/<context>/capabilities/` | what the context lets somebody do, and how it is known to be done | nothing in this plugin yet |
| **metrics** | `docs/<context>/metrics/` | the measures a capability is judged by | nothing in this plugin yet |

`<context>` is the bounded context, under the name its source directory carries by condition 1 of [`domain-model.md`](./domain-model.md). The set of kinds is closed at four. The last two are homes without a shape: the address is fixed here so that whatever defines the content later does not also have to choose where it goes.

## Conditions

Each of these is decided by `hooks/check-specifications.py`.

1. **A kind sits inside a context, never above one.** The state is a directory directly under `docs/` named `entities`, `contracts`, `capabilities` or `metrics`. The order is `docs/<context>/<kind>/`, and `docs/<kind>/<context>/` is the same content with the context cut into four places.

2. **A context directory is named in kebab-case.** The state is a directory under `docs/` that holds a kind directory and whose name does not match `[a-z0-9]+(-[a-z0-9]+)*`. A directory under `docs/` that holds no kind directory is not a context and is not read.

3. **An entity specification is one markdown file per entity, directly in `entities/`, named in kebab-case.** The state is a subdirectory there, a file that is not `.md`, or a stem that does not match the pattern in condition 2. `README.md` and `.gitkeep` are not specifications and do not fail.

4. **Its heading is the entity's name, and the filename is that name in kebab-case.** The heading is `# ` plus one PascalCase word, the name the domain uses. The two agree when the stem with its hyphens removed equals the heading in lowercase: `# ScheduledTransfer` in `scheduled-transfer.md`.

5. **Its header declares a classification from the closed set.** The line is `- **Classification:**` followed by `aggregate root`, `entity` or `value object`, above the first section.

6. **Its header names the context it sits in.** The line is `- **Context:**` followed by the name of the context directory, exactly.

7. **It carries the seven sections, filled.** `Why it exists`, `Fields`, `Invariants`, `Business rules`, `Relationships`, `Events` and `Errors`, each as an `##` heading outside code. No text in braces is left outside code, because a brace pair is how the template marks what the author replaces.

## Where this stops

**Presence, not substance.** A `Fields` table listing storage columns, an invariant that is a wish and an `Events` section naming a command all pass. The hook decides that the reader was given the seven answers; whether they are the model's is what the conditions of [`domain-model.md`](./domain-model.md) and [`aggregates.md`](./aggregates.md) ask of a reviewer, and the template restates none of them.

**A section with nothing in it says so.** A value object emits no event and many entities raise no error of their own. The section stays and reads `None`, with the reason when it is not obvious. Dropping the heading fails condition 7, deliberately: an absent section cannot be told from a question nobody asked.

**The rule does not say that an entity must have a specification.** It governs one that exists and the place one goes. Which entities earn a document is a judgment about the model, and a hook requiring one per type would need the root marker `aggregates.md` already records this plugin cannot guess.

**Only the entity kind has conditions on its content.** The other three are located by conditions 1 and 2 and read no further. A contract's shape is `contract-first.md`'s subject and its format is the consuming project's choice, so no filename is fixed inside `contracts/`.

**The layout is fixed and not configurable.** A project that keeps its specifications elsewhere gets nothing from the hook and fails nothing either, which is the trade `domain-model.md` makes for the source layout and for the same reason. What it cannot do is declare another path in a file, because that file is what drifts.

**Condition 1 misreads a context that is really called `metrics`.** A bounded context named for one of the four kinds would be reported as an inverted hierarchy. No such context is known, and the exception is written when one is.

**Condition 4 compares letters, not word boundaries.** `# HttpProbe` agrees with `http-probe.md` and with `httpprobe.md`. Deciding where the hyphens belong needs a rule for acronyms that would be wrong about some project's correct name, so the hook checks that the two are the same name and leaves the hyphenation to condition 3 and a reader.

**Braces outside code always fail condition 7**, even where an author meant one literally. A literal brace belongs in a code span, which is where a path template or a payload fragment already goes.
