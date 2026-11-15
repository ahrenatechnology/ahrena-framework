---
id: vulnerable-dependencies
type: rule
clade: engineering
subclade: security
title: Known vulnerabilities do not enter and are not left unrecorded
statement: A change adds no dependency with a critical or high CVE and locks each new one; a CVE found in production is recorded unless something already does.
enforcement: judgment
references:
  - docs/vulnerable-dependencies.md
---

# Known vulnerabilities do not enter and are not left unrecorded

Three conditions about dependencies: two decided on a pull request and one by a scheduled scan of what is already deployed. The rule requires no particular security monitor. Dependabot, code scanning and any other tool are the project's choice, and each condition is decided with whichever the project has or with none. [`docs/vulnerable-dependencies.md`](../docs/vulnerable-dependencies.md) gives the origin of each figure. Each condition carries its catalog id from the PR quality rubric (epic 323).

## Conditions

1. **SEC-1: no dependency the pull request adds or changes has a critical or high CVE.** The threshold is 0 in development, which is every dependency the lockfile resolves for the change. Severity is the advisory's CVSS v3 base score: 9.0 or above is critical and 7.0 or above is high, taken from the scanner's own database when it gives a score and from the NVD entry otherwise. Decided by an advisory scan of the lockfile diff with a tool that reads a public advisory database, such as `npm audit --audit-level=high`, `osv-scanner`, `pip-audit` or `govulncheck`. A finding names the package, the version and the advisory id. A vulnerability with no fixed version is reported and may be accepted only with a pointer, `#N` or `ADR-N`, in the pull request description, because a JSON lockfile has no comments. An advisory in a function the tree never calls is accepted under the same pointer, as `SUP-6` of `skills/reviewing-supply-chain` already allows.

2. **SEC-2: every dependency the pull request adds is pinned in the lockfile and runs no install script nobody reviewed.** The threshold is 0 occurrences. Decided by reading the lockfile diff for a new entry without a resolved version and integrity hash, and the new package's manifest for `preinstall`, `install` or `postinstall` scripts, each of which needs a pointer, `#N` or `ADR-N`, in the pull request description to the review that accepted it; an install script that only builds in-tree code is accepted under the same pointer, as `SUP-3` allows.

3. **SEC-5: a CVE found in a dependency of what is already published becomes an issue, unless something of the project already records it.** The threshold is every such CVE recorded. Decided by a scheduled scan of the production lockfile or image that, for each critical or high finding, searches the project's open issues, and the closed ones marked not planned that carry a pointer to the accepted risk, and whatever security monitor the project has for the advisory id and opens an issue only when neither holds it. The scan runs at least weekly. Where the project has no monitor, the scan and the issues are the only record. This condition does not block a pull request.

## Where this stops

**No condition requires a specific monitor.** SEC-5 reads the project's monitor where one exists, whatever it is, and does not depend on it existing. Code scanning and automated update pull requests are optional.

**SEC-1 and SEC-2 are the pipeline form of `SUP-6`, `SUP-1` and `SUP-3` of `skills/reviewing-supply-chain`**, and accept what those exempt under the same pointer.

**SEC-1 is held to critical and high.** A medium or low advisory is reported by the scan and is not a failure. In production, SEC-5 takes the same two severities and for the same reason: they are the ones a person is asked to act on.

**A scan reads a database, and a database is incomplete.** A clean result means no known advisory, not no vulnerability. Reviewing a new dependency's reputation and maintenance is `skills/reviewing-supply-chain`'s.

**SEC-2 reads npm's install scripts and a lockfile entry's version and hash.** Other ecosystems run code at build time through `setup.py`, `build.rs` or a build tag, and a project on one of them reads those by hand in the new package until its language plugin names a detector. A hash is required only where the lockfile format records one.

**SEC-1 does not reach a transitive dependency the change did not move.** A vulnerability already in the lockfile before the pull request is SEC-5's, so a legacy finding does not block unrelated work.

**No detector ships with this rule.** The scripts for SEC-1, SEC-2 and SEC-5 are #332's, and until they land a reviewer reads the scan output.
