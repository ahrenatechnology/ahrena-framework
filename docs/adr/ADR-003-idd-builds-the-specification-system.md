# ADR-003: Issue-driven development is built, not ported

- **Status:** accepted
- **Date:** 2026-09-26
- **Issue:** #45

## Context

The IDD survey in #45 found that the specification half of the subject does not
exist to port. The `docs/product-*.md` documents in the predecessor — 3,419
Portuguese lines marked "proposta v3" — describe a Definition of Ready with nine
criteria, a Definition of Done with seven, capability specifications, success
metrics, a three-iteration adversarial design-validation loop, six human gates
and twelve new agents. None of it shipped. Grepping the predecessor's canonical
tree for `lex-dor-criteria`, `kata-dor-validate`, `lex-capability-spec-required`
or any of the twelve agents returns one forward reference and nothing else.

That leaves the owner with two different undertakings behind one word. One is a
port: carry the workflow artifacts that do exist — the seven phases, both gates,
the AC↔test convention — and rewrite them to this framework's shape. The other is
a build: create the specification system the proposal only described. The survey
named this the single question that changes the size of the work more than any
other, because the two criterion lists are the only carry-over at sixteen lines
and everything else is new text.

The owner chose to build it.

## Decision

IDD is built, not ported. The specification system the predecessor proposed and
never shipped — Definition of Ready, Definition of Done, capability
specifications, the design-validation loop, and the agents that run them — is in
scope as new work, on top of the workflow artifacts that are ported and rewritten.

The two criterion lists in the proposal are the sixteen-line carry-over. The rest
is authored against this framework's conventions rather than translated from a
document that never became artifacts.

## Consequences

The undertaking is a program, not a pull request. It sequences behind the
foundation and process rules it depends on: the enforcement tier of ADR-002, the
issue, pull-request and trunk rules of #39, and the state vocabulary of #22. The
specification system is the last and largest stage and carries its own epic and
sub-issues rather than riding in with the rules.

Everything authored here inherits obligations the proposal's documents did not
carry. Each rule states where it stops, in the `## Where this stops` section this
framework requires and no predecessor artifact has; the survey names writing those
boundaries the largest source of genuinely new text across the whole subject. Each
rule that references another is rewritten so the reference graph stays acyclic,
rather than copied with the predecessor's mutually-referencing lists intact. Each
of the twelve agents is measured against `foundation/rules/` before it is built,
not assumed in because the proposal listed it.

The Portuguese proposal is a source, not a specification. It is read for the
properties it identifies — the DoR and DoD criteria, the shape of a capability
spec — and discarded as prose. The framework is English-only per #2, so nothing
crosses as text.

The cost is committed: this is the largest single undertaking on the roadmap, and
choosing to build rather than port is what makes it so. The alternative would have
delivered the ported workflow rules alone at a fraction of the size. The record
exists so that a reader who finds the program long understands that its length was
chosen, on this question, on this date.

## Alternatives considered

- **Port only, build nothing.** Carry the thirteen workflow artifacts and the
  eight product artifacts that exist as artifacts, rewrite them, and leave the
  proposal's specification system unbuilt. Rejected by the owner. It is the
  smaller undertaking by far and it is what the survey sized as the default, but
  it ships IDD without the specification discipline the proposal was written to
  add, which is the half the owner wanted.
- **Adopt the proposal's documents as-is.** Rejected on two grounds the survey
  established: they are 3,419 lines of Portuguese against an English-only
  framework, and they are a proposal that never became artifacts, so there is no
  running behaviour to preserve and every criterion has to be authored to this
  framework's shape regardless. Adopting the text would import a fourth voice and
  a reference structure that fails the gate.
- **Defer the decision until the rules land.** Rejected because the size of Group
  2 and Group 5 in #45 depends on it, and deciding after they are built means
  building them twice. The scope question is upstream of the work it sizes.
