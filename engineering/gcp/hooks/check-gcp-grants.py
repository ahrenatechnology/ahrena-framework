#!/usr/bin/env python3
"""Detector for the line-decidable forms of the Google Cloud identity rule.

Decides, over infrastructure source, three of the five conditions stated in
engineering/gcp/rules/identity-and-access.md, in the forms one line shows:

    1. no basic role: `roles/owner`, `roles/editor` or `roles/viewer`
    4. no service account key: a `google_service_account_key` resource, or
       `gcloud iam service-accounts keys create` or `keys upload`
    5. nothing public: a binding to `allUsers` or `allAuthenticatedUsers`

The files read are the ones a grant is written in: Terraform (`.tf`,
`.tf.json`, `.tfvars`), shell (`.sh`, `.bash`) and YAML (`.yaml`, `.yml`, which
covers Config Connector and Cloud Build). What a line cannot show is left to
the reviewer, as the rule says: a role name computed from a variable, a grant
made in the console, a runbook in prose, the scope a narrower role sits on.

A grant the change means to make anyway is allowed by a comment carrying
`gcp-grant-allowed:` and a reason, on the line itself or the line above. The
marker without a reason does not count, because the rule asks for the reason.

Standard library only, so a consumer runs exactly what CI runs.

Usage:
    python3 engineering/gcp/hooks/check-gcp-grants.py [path ...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "identity-and-access"

SUFFIXES = (".tf", ".tf.json", ".tfvars", ".sh", ".bash", ".yaml", ".yml")
SKIP_NAMES = frozenset({"node_modules", "vendor", "build", "dist"})

ALLOW = re.compile(r"gcp-grant-allowed:\s*\S")

CHECKS = (
    (1, re.compile(r"\broles/(owner|editor|viewer)\b"),
     "basic role {match}; grant the predefined role whose permissions the principal uses"),
    (4, re.compile(r"resource\s+\"google_service_account_key\"|\bkeys\s+(create|upload)\b"),
     "service account key ({match}); attach the service account, or use Workload Identity Federation"),
    (5, re.compile(r"\ballAuthenticatedUsers\b|\ballUsers\b"),
     "public principal {match}; grant to the callers that need it"),
)


@dataclass(frozen=True)
class Finding:
    where: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


def wanted(path: Path) -> bool:
    return path.name.endswith(SUFFIXES)


def skipped(relative: Path) -> bool:
    return any(part.startswith(".") or part in SKIP_NAMES for part in relative.parts)


def sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.extend([root] if wanted(root) else [])
            continue
        found.extend(p for p in root.rglob("*") if p.is_file() and wanted(p) and not skipped(p.relative_to(root)))
    return sorted(set(found))


def allowed(lines: list[str], index: int) -> bool:
    previous = lines[index - 1] if index > 0 else ""
    return bool(ALLOW.search(lines[index]) or ALLOW.search(previous))


def is_comment(line: str) -> bool:
    return line.lstrip().startswith(("#", "//"))


def scan(lines: list[str], where: str) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines):
        if is_comment(line) or allowed(lines, index):
            continue
        for condition, pattern, message in CHECKS:
            match = pattern.search(line)
            if match:
                text = message.format(match=f"`{match.group(0)}`")
                findings.append(Finding(f"{where}:{index + 1}", condition, text))
    return findings


def display(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def report(findings: list[Finding], checked: int) -> int:
    if not findings:
        print(f"{checked} file(s), no failures.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s):\n")
    for finding in findings:
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    paths = sources(roots)
    for path in paths:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        findings.extend(scan(lines, display(path, base)))
    return report(findings, len(paths))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
