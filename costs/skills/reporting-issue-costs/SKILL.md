---
name: reporting-issue-costs
description: Report what an issue, or every issue of a repository, cost to build, in tokens, active and wall-clock hours, and money, from the local cost ledger the session hook fills. Use when someone asks what an issue, a pull request or a repository cost, how many tokens or hours went into a change, how much of the spend is unattributed, or types /issue-cost. Also use to set the exchange rate, the hourly rate or the idle threshold the report reads, and to find out why a session was not recorded.
type: skill
clade: costs
references:
  - docs/cost-ledger.md
---

# Reporting issue costs

The numbers come from the ledger, never from memory and never from an estimate. `docs/cost-ledger.md` says what the ledger holds, how a session is attributed to an issue and what each figure means; read it before explaining a number somebody questions.

Run every command from this skill's own directory.

## 1. Settle the scope

One report covers one repository: the one named, else the one the current directory is a clone of. An issue number narrows it to that issue. Do not ask which; take it and say which one it was.

## 2. Run the report

```sh
python3 scripts/report.py --repository owner/name
python3 scripts/report.py --repository owner/name --issue 37
python3 scripts/report.py --repository owner/name --json
```

`scripts/report.py` reads the ledger, and asks `gh` for the pull request of each branch whose name carries no issue number. Add `--offline` to skip that lookup. `--home` reads a ledger other than the default.

An empty report means no session of that repository was recorded on this machine. Go to step 4 before saying the issue cost nothing.

## 3. Say what the report says, and what it does not

Give the figures as printed, in a table when there is more than one issue. Three things are never smoothed over:

- **"not configured" stays "not configured".** A cost in reais needs the exchange rate, and the development cost needs the hourly rate. Without them, say which one is missing and how to set it. Never show zero in its place and never supply a rate yourself.
- **"no price for model" stays out of the total.** Name the model and its token count. The price table is data in `runtime/prices.json`; a missing model is added there, with its source and date, by whoever reads the price.
- **The unattributed part is part of the answer.** State its share of the total and the branches behind it.

Token cost is the API list price applied to the tokens. Say so when the reader could take it for an invoice.

## 4. When a session is missing or a rate has to be set

Configuration lives in `config.json` in the ledger directory, and the hook writes what it caught to `errors.log` beside it. The doc lists every key, the environment variable that overrides it, and where the ledger directory is.

A session is missing when the plugin was not installed when it ran, or when the hook failed and said so in `errors.log`. A transcript that still exists can be recorded after the fact; the doc gives the command.

## When this skill does not apply

Publishing a CI run's cost on a pull request. That is one workflow step, written out in `docs/cost-ledger.md`, and it runs in the pipeline, not in a session.

Estimating what a change will cost before it is built. The ledger records what happened.

Sizing or pricing a client's infrastructure.
