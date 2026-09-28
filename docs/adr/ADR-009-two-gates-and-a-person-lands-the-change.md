# ADR-009: Two gates, and a person lands the change

- **Status:** accepted
- **Date:** 2026-09-28
- **Issue:** #100

## Context

The predecessor's issue-driven flow had seven phases and two gates. Gate 1
was scope: a person approved the design and the acceptance criteria before
implementation began. Gate 2 was quality: a set of checks decided go or no-go
before the pull request was opened. Its rules included one worth keeping
whole: no gate item may be claimed as met without the verification actually
being run.

#45 open question 7 asks how a human gate leaves a trace an agent cannot fake.
The question is sharper here than it reads. In this repository the agents act
through the owner's own GitHub account. Every issue, branch, pull request,
comment, label and review this session produced carries the owner's login.
So nothing on the forge distinguishes an act of the owner from an act of an
agent working for the owner. Any trace the forge holds, an agent with the same
token could have written.

Two measurements from the same session bear on it. The owner's Claude Code
refused `gh pr merge` from the agent as "Merge Without Review", and it refused
a change to the repository's merge settings, both in auto mode. The owner then
did each by hand, or explicitly asked for it to run in the terminal. So the
one boundary that held was the agent's own permission layer, not the forge.
And every check in CI ran as the workflow, on GitHub's runners, from the tree
under review. The agent could make CI fail by changing the tree. It could not
make a check report success on a tree that fails it.

## Decision

The flow has two gates, and landing on trunk is a third point that belongs to
a person.

**Gate 1, scope, is a person's.** Work on an issue starts only when a person
has asked for it: the issue's criteria, and its plan when it has one, are what
they approved. Where agents share the person's account, no forge trace proves
the approval, and the framework says so rather than inventing one. The
agent's obligation is that it does not start an issue nobody asked it to
start. The trace that remains is the assignment made when work starts, which
records that someone started, not that anyone approved.

**Gate 2, quality, is the checks, and its trace is CI.** The agent runs every
check before it opens a pull request for review, and does not claim a check
passed without the output of the run. CI runs them again, and the CI run is
the trace: it runs outside the agent, from the tree, and a green run means
the checks passed on that tree.

**Landing is a person's act.** An agent does not merge to trunk, and does not
merge a stack, even when its token can. Where agents have an identity of their
own, the merge's author on the forge shows who landed it. Where they share the
person's account, the agent's own permissions are what hold. On Claude Code
that is auto mode, or a deny rule for the merge commands. Every platform the
framework ships to has an equivalent.

## Consequences

`contributing/rules/gates.md` states the three obligations as a judgment rule,
because none of them is decidable from the forge while identities are
shared. Its one line reaches every agent in the always-loaded tier, which is
the only enforcement the first and third obligations have on a shared account.

`skills/running-the-quality-gate` is the procedure for gate 2. It runs the
checks CI will run, then the forge-tier checks against the pull request, and
reports each with its output. A gate that only blocks leaves the author to
guess the fix. #27 asks for gates that instruct, and every finding this
framework's detectors print already names the fix. The skill passes those
messages on rather than summarising them away.

Gate 2 is only as strong as CI is required. A ruleset that does not require
the checks to pass lets a person land a red pull request. The repository's
ruleset requires a pull request and not yet the checks. Making them required
is an owner's setting.

The trace for gate 1 stays weak until agents stop sharing the person's
account. A GitHub App or a machine account for the agents would make both
gate 1 and landing visible on the forge. #57, publishing Argos as a GitHub
custom agent, is the first step in that direction. This record does not
require it, because requiring it would stop every repository without one from
using the flow at all.

## Alternatives considered

- **Labels as gate approvals.** A person adds `approved` and the work starts.
  Rejected on two grounds: labels are each project's configuration (#80), and
  on a shared account an agent can add the label as easily as the person.
- **Required reviews as gate 2.** A ruleset requiring one approving review.
  Rejected for this flow. A solo owner cannot approve their own pull request,
  and an agent acting on the owner's account can approve anybody else's. The
  review stays what it is, a reader's judgment, and gate 2 stays the checks.
- **Require agents to have their own identity.** It is the only way to make
  gate 1 and landing checkable on the forge. Rejected as a requirement, and
  recorded as the direction, because it would make the flow unusable without
  an App or a machine account. It is worth doing, and not worth blocking on.
- **The predecessor's quality report file.** A `06-quality-report.md` per
  issue, written by the agent. Rejected: a report the agent writes is a claim
  the agent makes, and the CI run is the same evidence from a party that
  cannot shade it.
