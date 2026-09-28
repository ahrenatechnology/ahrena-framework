---
name: running-the-quality-gate
description: Run every check a pull request must pass before it asks for review, and report each with the output that shows it. Use before marking a pull request ready for review, after fixing a failed check, or when asked whether a change is ready.
type: skill
clade: contributing
references:
  - rules/gates.md
  - rules/pr-quality.md
  - rules/traceability.md
  - rules/stacked-pull-requests.md
---

# Running the quality gate

Gate 2 of `gates.md`. Every check CI will run is run first, here, and each result is reported with the output of its run. CI runs them all again afterwards, and that run is the trace. This one is how the author finds out first.

## 1. Open the pull request as a draft

The forge-tier checks read the pull request itself: its body, the issues it closes, its stack. So it has to exist before they can run. Open it as a draft, which asks nobody for review yet:

```sh
gh pr create --draft --base <base> --title "<type>: <subject>" --body-file <body.md>
```

## 2. Run the checks that need only the tree

Read the project's CI workflow and run every step whose command reads the checkout: test suites, gates over the corpus, linters, the project's own test runner. Run them from the repository root, in the order the workflow runs them. Tests of the checks run before the checks themselves.

A suite that builds scratch git repositories can fail on a machine whose global git config signs every tag or commit. That failure is about the machine, not the change. Rerun the suite with the global config out of the way:

```sh
GIT_CONFIG_GLOBAL=/dev/null python3 <suite>
```

## 3. Run the checks that need the forge

Build the event CI would receive, then run each forge-tier check against it with a token:

```sh
gh api repos/<owner>/<repo>/pulls/<n> | python3 -c 'import sys,json; p=json.load(sys.stdin); json.dump({"pull_request":p,"repository":p["base"]["repo"]},sys.stdout)' > event.json
export GITHUB_TOKEN="$(gh auth token)" GITHUB_REPOSITORY=<owner>/<repo>
python3 contributing/hooks/check-pull-request.py event.json
python3 contributing/hooks/check-stack.py event.json
python3 contributing/hooks/check-traceability.py event.json
python3 contributing/hooks/check-trunk.py event.json
```

`check-traceability` needs the checkout to be the pull request's head, with its base commit fetched.

## 4. Report every check with its output

For each check, the command and the summary line it printed. `24 cases passed.` is a result. "The tests pass" is not. A check that could not run is reported as not run, with the reason. It is never folded into the ones that passed.

A check reported as unchecked, because no token was available or the forge did not answer, is unchecked, not passed. Say which, and why.

## 5. Fix what failed, and run it again

Every finding from this framework's detectors names the fix, as #27 asks of every gate. Apply it, then run that check again, and step 4's report for it is the new output. A fix that changes files the other checks read means running those again too.

A finding that is wrong, where the detector misreads the change, is not fixed by editing the change to satisfy it. Say so in the pull request, and open an issue for the detector with `opening-issues`.

## 6. Mark it ready

When every check passes, put the report in the pull request's verification section and ask for review:

```sh
gh pr ready <n>
```

CI runs everything again. If it disagrees with the local run, CI is right, and the difference is the next thing to find.

## When this skill does not apply

Reviewing the change is `engineering/skills/reviewing-diffs`, and it comes after this. Merging is a person's act (`gates.md` condition 3), and no step here merges.
