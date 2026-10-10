# ADR-014: A separate agent applies the fixes, and the review runs again

- **Status:** accepted
- **Date:** 2026-10-10
- **Issue:** #137

## Context

`ADR-013` let a clean review approve and land a change, and listed one thing
it would not do: apply the findings. Its reason was precise — "a reviewer that
edits the change reviews its own work on the next pass" — and it left the fix
to an issue of its own. So today a fixable finding, one whose correction the
review already spelled out in full, still waits for the author to type it.

Two things make applying it worth building now. The findings a review in this
framework produces already carry, for most conditions, the exact change that
resolves them: the file, what to replace, and with what. And the review itself
is cheap to run again, so a fix can be checked by the same gate that found the
problem.

The reason `ADR-013` gave not to do it still holds, and it is the constraint
this record is built around: the party that fixes must not be the party that
reviews. If one agent did both, its second review would be reading its own
edit, and the second reading — the whole value of a reviewer — would be gone.

A third fact changes what the separation buys. Argos, and the fixer this record
introduces, are intended to run as distinct bots with their own forge
identities, shared across organisations (#57). On a shared account `ADR-009`
and `ADR-013` could only say the separation in words, because every act carried
the owner's login. As distinct bots the fixer's commit and the reviewer's
approval carry different identities, so the separation is a fact on the forge
and not a promise.

## Decision

A distinct agent applies the fixes a review found, and the review runs again
before anything lands.

**The fixer is its own agent.** `engineering/fundamentals/agents/hephaestus.md`,
role `change-fixer`, orchestrates `skills/applying-fixes`. It is not Argos, it
does not review, and it does not merge.

**It applies only applicable findings.** A finding is applicable when it is
`blocking` or `deferrable`, its correction is a concrete instruction, and its
discipline is one where applying that instruction changes only what the finding
named: `reviewing-sensitive-data`, `reviewing-untrusted-input`, the language
reviewers, clean-code, and `reviewing-secrets` under the caveat below. A
`question` or an `unchecked` finding is never applied, because neither carries a
correction that can be made without a decision.

**The cycle is review, fix, review, land.** Argos reviews and publishes its
findings. Hephaestus applies the applicable ones as a commit and pushes. Argos
reviews the new commit as it reviews any — it is a second party reading a commit
a different agent wrote. `skills/landing-approved-changes` merges only if that
review is clean. The fixer runs a bounded number of times on one pull request;
whatever is still blocking after the bound goes to a person.

**Secrets are fixed in the code and rotated by a person.** Hephaestus applies
`reviewing-secrets`' code change — a literal becomes a read from the secret
store — but a credential that reached a commit is live in history, and rotating
it is an action outside the diff that the fixer does not perform. The finding's
rotation requirement stays a human action, and it keeps the change from landing
until a person has done it.

**The fixer never reviews, decides or merges.** It does not write a verdict, it
does not approve, it does not land, and it does not invent a correction the
finding did not state.

## Consequences

A fixable finding reaches trunk without the author typing the fix, and the
second reading that `ADR-013` protects is intact because a different agent did
the fixing. The forge shows it: Hephaestus authored the fix commit, Argos
approved, and `landing-approved-changes` merged.

The cycle can fail to converge. A fix that does not clear its finding, or that
the re-review finds a new fault in, repeats until the attempt bound, then stops
and a person takes it. The bound is what keeps a reviewer and a fixer from
trading commits forever.

Applying a change is executing intent the review expressed, so the fixer
inherits the same refusal the reviewer has: it does not build or run an external
fork's checkout, because applying a fix there would run the author's code on the
fixer's machine. On an external fork nothing is fixed automatically, and the
findings wait for the author as before.

The scope is deliberately not every discipline. Architecture, contract and
scope findings turn on a judgment the fixer cannot make, so they stay with a
person even when their correction looks mechanical.

This record does not require the bot identities. It is written so the agents
work on a shared account too, where the separation is words again and the fixer
simply hands back a branch for the next review. #57 is what makes the
separation checkable, and it is worth doing and not worth blocking on, the same
position `ADR-013` took.

## Alternatives considered

- **The reviewer applies its own findings.** One agent reviews and fixes.
  Rejected by `ADR-013`'s reason: its next review reads its own edit, and the
  second reading is gone.
- **Only publish the patch as a suggestion.** The review already carries the
  correction; a suggestion the author still applies by hand is close to today
  and was the state this issue set out to change.
- **A per-finding applicability flag on the published verdict**, set by Argos,
  instead of the fixer deciding from the finding's fields. It is cleaner and it
  is how a predecessor did it, but it changes the findings model, the verdict
  body and the publishing procedure at once. Deferred: the fixer decides from
  the finding's discipline, severity and correction for now.
- **Fix and leave the merge to a person.** A middle option. Rejected because
  the merge was never what held a fixable change back; the typing was, and
  `ADR-013` already lets a clean review land.
