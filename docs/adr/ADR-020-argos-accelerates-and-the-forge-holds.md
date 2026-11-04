# ADR-020: Argos accelerates, the forge holds, and the pipeline is declared

- **Status:** accepted
- **Date:** 2026-11-04
- **Issue:** #247
- **Supersedes:** ADR-013

## Context

`ADR-013` let a clean review approve and land a change. It kept a question or
an unchecked condition as a `comment`, and it refused the forge's auto-merge
because a repository whose ruleset did not require the checks would merge over
a pending run.

An audit of every Argos review from 30/10 to 04/11/2026 found the outcome was
the opposite of what was meant. There were 305 reviews: 216 from the CI
pipeline over 121 pull requests in eight client repositories, and 89 from
sessions over 44 pull requests in the Ahrena repositories.

- **The rules did not make the review careful. They made it a bottleneck that
  people learned to step around.** Only 15 of the 216 CI reviews had no
  finding. 69 approvals held only because they had three warnings. In one
  repository, 11 of the 13 held pull requests were merged over the hold. A
  deploy-breaking defect filed as a warning went through with them
  (barte-ai-platform#442).
- **The `comment` verdict was not enforced, and approval drifted from it.** 27
  of the 49 session approvals carried a question, an unchecked condition or a
  pending check in their own body.
- **There is no single Argos.** Three texts instruct the reviewer:
  `engineering/quality/agents/argos.md`, `engineering/code-review/agents/argos.md`,
  and the prompt the CI runtime wraps around them. The last one contradicts the
  agent: "ressalvas não-bloqueantes ainda são `approve`".
- **The CI pipeline had a fix step that wrote nothing.** Its Erodos node handed
  every pull request it received to a person. Running it or skipping it was not
  something an installation could choose.

Two facts that `ADR-013` reasoned from have since moved. The client
repositories now require their checks in a ruleset (`ci`, `build`, `tests`,
`argos/verdict` and others). Under such a ruleset, the forge's auto-merge waits
for every required check and cannot merge over a red or pending one. And
`ADR-018` made a process's orchestration declared data, so a step can be
switched by the installation rather than coded in.

What has not moved is that Argos reviews a change it did not write, and that it
can be wrong.

## Decision

**Argos is an accelerator with a high bar.** Its default is to release the
change. It holds only for what it can name. The forge, through the checks its
ruleset requires, holds what the review cannot see.

**The posture is declared per installation: `optimistic` or `conservative`.**

- `optimistic` is the default. A question or an unchecked condition is
  published in the opinion and does not hold the change.
- `conservative` holds the change on either, as `ADR-013` did.

The posture changes only how uncertainty is treated, never the bar below.

**Five things always hold, in either posture:**

- a blocking finding;
- a defect that makes a step the repository declares fail deterministically;
- an exposure of data or of an action to a party the access rules do not allow;
- a change to the review pipeline's own files;
- a repository whose ruleset does not require its checks, because then the
  forge cannot hold what Argos releases. Such a repository runs `conservative`
  whatever it declares.

**Argos releases through the forge's auto-merge.** After approving, it enables
squash auto-merge on the head it reviewed. The forge merges when the required
checks pass, on that head only. Argos does not wait for CI, does not repeat what
a check decides, and never states a coverage it did not have: what it could not
see is named as unchecked.

**The autofix step is declared, on or off.** When it is on, the `como` findings
of the published opinion go to Erodos. Erodos commits the fix and the review
runs again on the new head, within the round bound `ADR-014` set. When it is
off, those findings stay in the opinion for the author. Either way, a finding
that needs a decision goes to a person. `ADR-014` stands; this record makes its
step optional per installation.

**There is one Argos, and every runtime extends it.** The code-review agent,
`engineering/code-review/agents/argos.md`, is the base. It carries every rule of
behaviour: the verdict rule, the severities, what is a finding and what is a
question.

A runtime, the CI pipeline or a session, may extend it in two ways:

- it passes inputs: the merge-base diff, the pull request body, the previous
  opinion, the check results, and the declared posture and autofix setting;
- it adds what is specific to the runtime: the machine-readable shape the
  pipeline parses, and what the runtime cannot do, such as a tool it does not
  grant.

A runtime never contradicts the base or overrides it. It does not redefine a
verdict, a severity or what to list. A rule a runtime needs that the base does
not have goes into the base, for every runtime.

Kept from `ADR-013` unchanged: the two gates (scope is a person's, quality is
the checks and CI is their trace), and the four kinds of change a person
lands — a decision record, a layer of a stack, a draft, and an external fork.

## Consequences

A change with no finding that holds reaches trunk as soon as its checks pass,
with no person and no wait for Argos to see CI. That is the purpose of the
reviewer, and it was being lost to holds nobody honoured.

**The cost is that a question can land unanswered.** Under `optimistic`, a
question addressed to the author may have had a blocking answer, and the change
merges before anyone gives it. The five holds are what bound that cost, and
their quality now decides the reviewer's worth. Severity is the lever: a
finding that belongs to one of the five and is filed as a warning is the
failure this record makes expensive. #249 tightens the severity rule for that
reason.

**The forge becomes load-bearing.** A ruleset that stops requiring a check
silently widens what lands unseen. The rule that such a repository runs
`conservative` closes that only if the runtime reads the ruleset. A runtime
that cannot read it must treat the repository as `conservative`.

**Extending without contradicting moves work into the base.** The CI runtime
loses the lines that patched behaviour: "list all findings" and "ressalvas são
approve". The finding schema stays in the runtime as an output shape, but its
severities are the base's. The base has to carry the verdict rule and the
severities for every runtime, and its tests have to cover what the wrapper
silently did. A runtime prompt that redefines a verdict or a severity has to be
detectable in review, since nothing else stops it.

**Autofix off is a legitimate state.** It is not a degraded one. An
installation that has not given Erodos write access is correct with it off, and
its opinion must say the fixes are the author's.

## Alternatives considered

- **Keep `ADR-013`: a question or an unchecked condition is a `comment` that
  holds.** Rejected. The audit shows the hold was not honoured: most held pull
  requests merged over it. A gate people learn to step around protects nothing,
  and it buries the holds that matter.
- **Fail closed everywhere: no check read means no release.** Rejected as the
  default. Where the ruleset requires the checks, the forge already refuses a
  red or pending merge, so Argos holding too adds a wait and no protection. It
  stays available as `conservative`, and it is forced where the ruleset is
  missing.
- **Let a probabilistic decision model choose between merging and holding.**
  This is the current Decisor. Rejected as the primary rule. Its scores did not
  track the review: the mean probability of merging was 0.67 at zero warnings
  and 0.69 at two, and the same commit was held on one run and merged on the
  next. A model may still veto, with a stated reason, what the deterministic
  rule would release.
- **Let each runtime own its whole prompt, or pass no instruction at all.**
  Rejected both ways. A runtime that owns its prompt drifts from the agent, as
  the CI wrapper did. A runtime with no instruction at all cannot say what shape
  it parses or which tools it withholds. Extension without contradiction keeps
  the runtime's own needs and leaves behaviour in one place.
- **Keep the autofix always on, as `ADR-014` implies.** Rejected. An
  installation may not grant a fixer write access, and a step that cannot write
  must be off by declaration, not on and silently handing everything to a
  person.
- **Keep two agent definitions and let each runtime pick one.** Rejected. The
  two promise different things today. A pull request reviewed in a session and
  again in CI already got different opinions on the same commit: seven pairs,
  one with 0 findings against 4.
