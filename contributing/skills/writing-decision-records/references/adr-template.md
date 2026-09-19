# Decision record

The skeleton step 3 copies, the prompt for each field, and a filled example.
Everything between the rules is the record; the rules are not part of it.

Save it as `docs/adr/ADR-nnn-slug.md`. The number in the heading is the number
in the filename, and the gate checks that they agree.

---

# ADR-nnn: Short declarative title

- **Status:** accepted
- **Date:** YYYY-MM-DD
- **Issue:** #nnn
- **Supersedes:** ADR-nnn

## Context

## Decision

## Consequences

## Alternatives considered

-

---

## The header lines

**Status** is `accepted`, `superseded` or `withdrawn`. There is no `proposed`:
the pull request is the proposal and merging is the acceptance. `withdrawn` is
for a decision that stopped applying and was not replaced.

**Date** is the day the decision was made, not the day the file was written,
in `YYYY-MM-DD`. It is the only field that places the record against anything
outside the log.

**Issue** is optional and carries the thread the decision came out of. Write it
when there is one; a record that cannot name an issue is not thereby worse.

**Supersedes** appears only when this record replaces an earlier one, and it is
half of a pair — the older record gains `- **Superseded by:** ADR-nnn` and its
status becomes `superseded`, in the same commit. The gate fails a chain that
resolves in one direction only.

## The four sections

**Context** is the problem, not the solution. Write for a reader in two years
who has none of today's conversation: what forced a decision, what was in
tension, what constraint was not negotiable. If a sentence argues for the
choice, it belongs in Decision.

**Decision** is what was decided, in the active voice and the present tense.
"We address records as `plugin:path`", not "it was decided that records could
be addressed". One or two paragraphs. Where the decision has an edge that is
still open, say so here — a decision about the part that closed is still a
decision, and the open edge is the next record's Context.

**Consequences** is what improved, what it costs and what it forecloses, in
prose. There are no Positive / Negative / Neutral subsections, because three
mandatory headings produce three filled headings and the Neutral one fills with
changelog. The cost is the part a reader came for: a record whose consequences
are all benefits is describing a sales pitch, and nothing in the gate can tell
the difference.

**Alternatives considered** is one bullet per option, each naming the option and
why it lost. At least one, and the gate checks only that a bullet exists. An
alternative worth the line is one a reader might still prefer; "do nothing"
counts when doing nothing was available.

## A filled example

Written from an entry in this repository's own decision log, to show the format
holding the hardest of them. It is an example, not an adopted record.

---

# ADR-004: A reference crosses plugins by marketplace name

- **Status:** accepted
- **Date:** 2026-09-12
- **Issue:** #34

## Context

The framework ships four plugins and the artifacts in them had begun to need
each other. Nothing said how. Inside a plugin a reference is a path from the
plugin root, which resolves because the plugin is one directory; across plugins
there is no such directory, because a consumer installs each one wherever the
platform puts it and the layout in this repository survives nowhere.

Two different needs were being served by one unanswered question. A declared
`references` entry is a load edge: the artifact it names is pulled into context
when this one fires, and the type matrix in `pilars.md` governs which pairs are
allowed. A link in the body is documentation: a reader follows it, and it also
has to open on GitHub. Treating them as one thing meant choosing between an
address that survives installation and an address that a reader can click.

Pressing on this was `duplication.md`, which wanted to cite `yagni.md`, and
`module-boundaries.md`, which was restating SOLID's sixth condition in full
rather than pointing at it.

## Decision

A declared reference crosses a plugin boundary as `marketplace-name:path`,
naming the plugin as the marketplace names it, then the same plugin-relative
path. The matrix applies unchanged across the boundary, a qualified reference
into the artifact's own plugin fails, and the graph those edges form must be
acyclic.

A body link crosses as an ordinary relative path, resolved from the file.

## Consequences

The plugin graph is now a real dependency graph, checked for cycles by
`pilars.md` conditions 7 and 8, and a reference naming a plugin the marketplace
does not list fails rather than dangling.

Two spellings have to be remembered, and the cost is real: the same target is
written one way in frontmatter and another way three lines later in the body.
It is accepted because the two are not the same thing, and one spelling would
have meant either load edges that break on installation or documentation links
that do not open.

The route a rule takes to cite another rule is now a body link, and this closes
the door on rule-to-rule references permanently — a rule that drags another
rule into context has doubled the cost of both, and there is now a cheap way to
say what was wanted instead.

The gate validates a marketplace, not an installation. A consumer who installs
one plugin and not the plugin it depends on has a dangling edge that nothing
here detects.

## Alternatives considered

- **One spelling for both, using relative paths.** Rejected because a relative
  path between plugins resolves only in this repository's layout, which is the
  one layout no consumer has.
- **One spelling for both, using qualified names.** Rejected because a
  qualified name is not a link: it does not open on GitHub and a reader cannot
  follow it.
- **Allowing rule-to-rule references across plugins only.** Rejected because
  the cost the matrix is protecting against is context, and context does not
  care which plugin the second rule came from.
- **Leaving it undecided until a third plugin needed it.** Rejected because two
  artifacts were already working around the absence, one by duplicating a rule's
  text and one by not citing what it meant.

---

## What is deliberately absent

**No decision drivers or option-scoring table.** Full MADR has both. They turn
a judgment into arithmetic and the weights are chosen to produce the answer
already reached.

**No "related decisions" list.** Supersession is the only relationship the gate
can check, and an unchecked list of loose relations goes stale the way every
manually maintained index does. A record that wants to name another names it in
prose.

**No review date.** A record is not revisited on a schedule; it is superseded
when something changes. A date that arrives with nothing having changed
produces a decision reaffirmed for no reason.
