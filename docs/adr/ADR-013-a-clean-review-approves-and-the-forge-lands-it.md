# ADR-013: A clean review approves, and the forge lands it

- **Status:** accepted
- **Date:** 2026-10-09
- **Issue:** #130
- **Supersedes:** ADR-009

## Context

`ADR-009` set two gates and kept landing for a person. An agent did not merge
to trunk, and Argos approved a pull request only to resolve a request for
changes it had made earlier on the same pull request, so a change that was
right on the first pass was published as a comment and waited for the owner.

Two things `ADR-009` reasoned from have moved.

The first is what a clean review says. The approval rule was written against a
reviewer that could be silently broken: pointed at the wrong base, handed an
empty diff, unable to read the change, and approving all the same. Since #128
a review names the routes that fired, the skills no route selected, the paths
nothing but the secret sweep reached, and every condition it did not decide.
A clean result now states what it covered, and a review that covered nothing
reads as one.

The second is the cost. On a repository with one owner, keeping the owner on
every merge does not add a second reading. The owner who merges a pull request
the review found nothing in is confirming a result, not reviewing a change.

What has not moved is the forge. Agents still act through the owner's account
in this repository, so an approval, a merge and a comment all carry one login,
and GitHub refuses a review that approves the reviewer's own pull request.

## Decision

The flow keeps its two gates, and a review that approves lands the change.

**Gate 1, scope, is a person's.** Work on an issue starts only when a person
asked for it. Unchanged from `ADR-009`.

**Gate 2, quality, is the checks, and its trace is CI.** Unchanged from
`ADR-009`.

**The verdict follows the findings and nothing else.** At least one blocking
finding is a request for changes. A question or an unchecked condition, with
no blocking finding, is a comment. Deferrable findings alone, or no findings,
is an approval, on the first pass as on any other.

**An approved pull request is landed by the forge.** After Argos approves, it
asks the forge to merge by squash the commit it reviewed, and only when every
check on that commit has completed and passed. It uses the forge's own merge
and nothing that bypasses a ruleset. No other agent merges, and the author of
a change never lands it.

**A person still lands four kinds of change:** a pull request that touches a
decision record, a layer of a stack, a draft, and a pull request whose head is
an external fork.

## Consequences

A change the review finds nothing in reaches trunk without the owner. That is
the whole benefit, and it is paid for in three places.

An approval no longer proves the reviewer once disagreed. `ADR-009`'s rule
made an approval mean "what I objected to is gone". It now means "nothing I
read stops this", and its worth is the coverage statement beside it. A review
that reports an unchecked condition does not approve, so a review that could
not see part of the change does not land it.

A defect Argos misses lands. Before, the owner's merge was a second chance to
notice. What remains is CI on the pull request, CI again on trunk, and the
revert. A repository that cannot afford that keeps a ruleset requiring a named
person's approval, and the forge then holds the merge whatever Argos says.

On a shared account the forge refuses Argos's approval of the owner's own pull
request. Argos then publishes the same verdict as a comment and lands on the
verdict. Where the ruleset requires an approving review, the forge refuses the
merge and the pull request waits for a person, which is the ruleset working.
An identity of its own for Argos, #57, is what makes the approval a review the
forge records.

Decision records stay with a person because they are the one kind of change
whose correctness no condition decides. A stack stays with a person because
its order is the plan's, and `contributing/skills/stacking-pull-requests` lands
it layer by layer.

Where the platform's own permission layer refuses the merge command, as Claude
Code's auto mode did in the session `ADR-009` records, that refusal stands and
the pull request waits for a person.

`contributing/rules/gates.md` condition 3, `docs/review-verdicts.md`,
`skills/publishing-review-verdicts` and `agents/argos.md` change to say this,
and `skills/landing-approved-changes` is the procedure.

## Alternatives considered

- **Keep `ADR-009`.** A person lands everything. Rejected by the owner: the
  cost is paid on every clean pull request and buys a confirmation, not a
  review.
- **Approve on the first pass, and leave the merge to a person.** Rejected
  because the approval was never what held a change back. The merge was.
- **Enable the forge's auto-merge and let it wait for the checks.** Rejected
  for now. On a repository whose ruleset does not require the checks, enabling
  it merges at once, over a run that is still pending. Landing reads the
  checks itself until the ruleset requires them.
- **Land a pull request that carries questions or unchecked conditions.**
  Rejected. A question is addressed to the author and its answer may be a
  blocking finding, and an unchecked condition is a part of the change nobody
  read.
- **Apply the deferrable findings before landing.** A reviewer that edits the
  change reviews its own work on the next pass. Left to an issue of its own.
