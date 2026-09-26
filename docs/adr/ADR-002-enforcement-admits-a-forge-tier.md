# ADR-002: Enforcement admits a forge tier

- **Status:** accepted
- **Date:** 2026-09-26
- **Issue:** #45

## Context

`foundation/rules/frontmatter.md` closes the `enforcement` field at two values.
`hook` means a script decides the condition and `enforced-by` names it; `judgment`
means the condition needs a reader. The closure is deliberate — the framework
owns both ends of that schema — and the whole claim of a hook rests on one
property, stated in `contributing/docs/contribution-flow.md`: a hook runs
offline, on a consumer's machine, on a stdlib-only Python, with no token and no
network. That is what lets a consumer run the same gate the repository runs.

Issue-driven development breaks against that boundary on its first rule. The
conditions #39 wants to check are almost all remote: the referenced issue exists
and is open; a closing keyword in the pull-request body binds to the reference
that immediately follows it, so `Closes #4, #5, #6` closes one issue and not
three; the size label matches the computed diff; exactly one state label sits on
the item. None of these is a state of the working tree. The pull-request body is
not in the tree, the issue is not in the tree, and the labels are not in the
tree. The survey in #45 counts fourteen such conditions across the subject and
finds about ten of them reachable today with the default `GITHUB_TOKEN` on a
`pull_request` trigger and no new secret.

So a condition can be perfectly mechanical and still be unreachable from a
checkout, because the state it reads is the forge's rather than the tree's. The
two-value schema has no way to say that. Marking these rules `hook` is a lie —
the script cannot run where a hook is promised to run. Marking them `judgment` is
also a lie — a reader is not needed; a script decides them exactly, just not
offline. The distinction the schema is missing is not mechanical versus judgment.
It is **where the detector runs.**

The owner settled the higher question in #45 first: enforcement that reads GitHub
state is in, because without it most of IDD ships as `judgment` and "a quality
process, not bookkeeping" has no teeth. This record settles the schema shape that
decision forces, which #45 open question 3 and `ROADMAP.md` open question 8 both
name and neither answers.

## Decision

Enforcement keeps its two values and gains one optional field, `enforced-in`,
whose value is `tree` or `forge`.

- `enforced-in: tree` is the default and the current model. A hook decides the
  condition from the working tree alone, offline, stdlib-only, no token. Omitting
  the field means `tree`, so every rule that exists today is unchanged and no
  file has to be edited to keep meaning what it meant.
- `enforced-in: forge` means the detector still decides the condition
  mechanically, but it reads the forge's state and therefore runs only in CI,
  with the default `GITHUB_TOKEN`. It is not run as an offline hook, because it
  cannot be.

`enforced-in` is meaningful only when `enforcement` is `hook`, since `judgment`
names no detector to place. `enforced-by` continues to name the script for both
tiers; what changes is only where that script is run and what it is allowed to
reach.

A forge-tier detector reads whatever access is present and names what it could
not read, rather than refusing to run when the forge is absent. This is the
`unchecked` pattern the reviewer already uses, and it is what keeps a
forge-tier rule from failing a consumer who runs the gate offline: offline, the
condition is reported unchecked, not failed.

## Consequences

The closed schema in `foundation/rules/frontmatter.md` gains a field and its
validator gains a condition: `enforced-in`, when present, is `tree` or `forge`,
and is rejected when `enforcement` is `judgment`. That change is a foundation
change and lands in its own pull request, ahead of the first rule that needs the
forge tier. This record is what that pull request cites.

The one-line footprint is untouched. `enforced-in` never reaches the agent,
because a hook rule contributes zero lines to the always-loaded tier whether it
runs in the tree or the forge. The field is schema, not instruction.

CI grows a job class it did not have: a step that runs a forge-tier detector
against the pull request with `GITHUB_TOKEN`, distinct from the steps that run
tree hooks and their test suites. `contributing/docs/contribution-flow.md`
already establishes that the enforcement point for this plugin is CI and that the
checks judge a pull request only; a forge-tier detector is the same enforcement
point with a wider reach, not a new one.

The offline guarantee is now a property of a tier rather than of every hook. A
consumer cloning the framework and running the gate with no network still runs
every `tree` hook and gets the same answer the repository does. The `forge` hooks
report unchecked offline and decide in CI. The guarantee that mattered — that the
gate a consumer runs is the gate the repository runs — holds for the `tree` tier
unchanged and holds for the `forge` tier wherever a token is present.

The cost is that the framework now ships a detector that is green by seeing
nothing whenever it runs without a token. `contributing/rules/decision-records.md`
already refuses that failure mode for a path given and not found; the forge tier
reintroduces it by construction, because "no token" and "nothing to report" look
alike. The mitigation is that the CI job that owns these detectors always has the
token, so the only place they run without one is a consumer's offline checkout,
where unchecked is the honest answer rather than a false green.

## Alternatives considered

- **A third `enforcement` value, `ci`.** Rejected because it conflates two axes.
  Whether a condition is mechanical or needs a reader is one question; where a
  mechanical detector runs is another. Folding them into one enum makes `ci` a
  sibling of `judgment`, which reads as "a different kind of judgment" when it is
  the opposite — a `ci` condition is more decidable than a `hook` one, not less.
  A second field keeps the two axes orthogonal, so `hook`+`tree`, `hook`+`forge`
  and `judgment` are the three real combinations and the schema says why.
- **Leave IDD's remote conditions as `judgment`.** This is the shipped state
  before this record and it is what #45 open question 4 rejects: a reader is not
  needed for a condition a script decides exactly, and calling it judgment means
  an agent can claim it passed without anything checking. It also loses the ten
  conditions that are reachable today for no new secret.
- **A network-capable hook in the `tree` tier.** Rejected because it destroys the
  property the `tree` tier exists to guarantee. A hook that sometimes needs a
  token is a hook a consumer cannot trust to run offline, and the whole value of
  the tree tier is that its answer does not depend on where it runs.
- **Require a secret and a richer token.** Rejected on the survey's own
  measurement: about ten of the fourteen conditions are reachable with the default
  `GITHUB_TOKEN` on a `pull_request` trigger. Asking a consumer to provision a
  secret before any of IDD enforces is a cost paid before the first benefit, and
  the forge tier is defined against the default token for that reason. A condition
  that genuinely needs more than the default token is a later record, with the
  case that forced it.
