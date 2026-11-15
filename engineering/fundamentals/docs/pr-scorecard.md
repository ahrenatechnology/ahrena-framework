---
id: pr-scorecard
type: doc
clade: engineering
subclade: quality
title: The pull-request scorecard and the detector contract
summary: How the scorecard runner turns registered detectors into one JSON card per change, the contract a detector signs to be registered (condition id, languages, threshold and where it comes from, eliminatory or indicator, scope, and a clean and a planted fixture), how the ratchet reads added lines and totals, and why Argos reports a failed eliminatory condition without re-judging it.
references:
  - docs/duplication.md
---

# The pull-request scorecard and the detector contract

A quality condition is a yes or a no with a threshold, and a script decides it. `hooks/scorecard.py` is the one place those scripts run together over a change and become a card. Without it each detector is a script someone may or may not run, and the reviewer keeps re-judging what a script already decided.

## What the runner does

```text
python3 engineering/fundamentals/hooks/scorecard.py --base <rev> --head <rev> [--out card.json]
```

It exports the head and the merge base of the two revisions, runs every registered detector as a subprocess over the head (and over the base when a condition ratchets on its total), and writes one JSON document. Per condition id: `status` (`passed` or `failed`), `kind` (`eliminatory` or `indicator`), the entries behind it with their threshold and its source, and each failure with its file and line. Exit 0 when no eliminatory condition failed, 1 when one did, 2 when a detector could not answer: it crashed, it failed with output the runner cannot read, or it printed a condition the registry does not name. An error is never a pass.

## The contract a detector signs

A detector is registered in `hooks/scorecard-detectors.json`, with its script and languages and one entry per condition it decides:

| Field | Meaning |
|---|---|
| `id` | the entry's own name, unique |
| `condition` | the id of the catalogue condition (`STR-1`, `TST-1`); several entries may serve one condition |
| `rule`, `number` | what the detector prints for it: `[rule] condition N` |
| `kind` | `eliminatory` blocks the merge; `indicator` shows on the card and never blocks |
| `scope` | `added` or `total`, the ratchet below |
| `threshold` | the number of failures tolerated under that scope |
| `threshold_source` | `measured:`, `inherited:` or `policy:` and where: a threshold is measured, attributed to the source it came from, or declared maintainer policy |
| `fixtures` | a `clean` tree and a `planted` tree |

`scorecard.py --fixtures` is the CI proof. A detector must report nothing over its clean tree and must report its own `rule` and `number` over its planted one; either miss is a defect of the detector. The fixtures sit beside the detector's plugin, one folder per entry.

## The ratchet

Limits apply to what a change adds, because legacy cannot be fixed in the pull request that happens to touch it.

- `added`: a failure counts when its line is one the change adds. A failure with no line (a file with no test beside it) counts when the file is new. The condition fails when more than `threshold` count.
- `total`: the whole tree counts, and the condition fails only when the head has more failures than the merge base, or than `threshold` when that is higher. An indicator that gets worse fails; one that stays or improves does not.

## One runner

The runner reuses the suites' shape (a hook run as a subprocess over a tree, judged on its exit code and its output) and the change-scoped diff of `hooks/changes.py`. It does not import the TypeScript plugin's `harness.py`: plugins do not depend on one another, so a shared module would be the dependency the framework's no-dependency constraint forbids, and the suite harnesses stay per plugin. A second runner for any other language registers its detectors here instead.

## What Argos does with the card

A failed eliminatory condition is a script's answer, not an opinion, so Argos reports it as a blocking finding under the detector's name and does not re-argue it, in the same way it treats any check the pull request already failed. An indicator that failed is reported as deferrable when it worsened. Argos never overrides a passed condition either.

## Where this stops

- It decides nothing a detector does not: a condition with no registered detector is not on the card, and the card never claims it passed.
- It is not a linter or a type checker; a detector may wrap one, and then the card says what the wrapped tool said.
- It does not adopt the cards on a consumer repository, and it does not add conditions: the catalogue of #323 and its sibling issues do.
