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

With `--changed <range>` the hook reads only the lines that range adds, as
`git diff` reports them (`base...head`, or `base` alone for the working tree),
so a pre-existing grant in a modified file is not reported as the change's.
Without it, every line of every file under the paths is read.

Exit status: 0 when nothing is reported, 1 when a condition is reported, 2 when
the arguments or git cannot be used. Standard library only, so a consumer runs
exactly what CI runs.

Usage:
    python3 engineering/gcp/hooks/check-gcp-grants.py [path ...]
    python3 engineering/gcp/hooks/check-gcp-grants.py --changed <range> [path ...]
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "identity-and-access"

SUFFIXES = (".tf", ".tf.json", ".tfvars", ".sh", ".bash", ".yaml", ".yml")
SKIP_NAMES = frozenset({"node_modules", "vendor", "build", "dist"})

HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")

ALLOW = re.compile(r"gcp-grant-allowed:\s*\S")

CHECKS = (
    (1, re.compile(r"\broles/(owner|editor|viewer)\b"),
     "basic role {match}; grant the predefined role whose permissions the principal uses"),
    (4, re.compile(r"resource\s+\"google_service_account_key\"|\bservice-accounts\s+keys\s+(create|upload)\b"),
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


def scan(lines: list[str], where: str, only: set[int] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines):
        if only is not None and index + 1 not in only:
            continue
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


def parse_diff(text: str, top: Path) -> dict[Path, set[int]]:
    added: dict[Path, set[int]] = {}
    current: Path | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            name = line[4:]
            current = None if name == "/dev/null" else (top / name[2:]).resolve()
            continue
        match = HUNK.match(line)
        if match and current is not None:
            start, count = int(match.group(1)), int(match.group(2) or "1")
            added.setdefault(current, set()).update(range(start, start + count))
    return added


def changed_lines(spec: str) -> dict[Path, set[int]] | None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    diff = subprocess.run(["git", "diff", "--unified=0", "--no-color", spec], capture_output=True, text=True)
    if top.returncode != 0 or diff.returncode != 0:
        print(f"cannot read the changes in {spec!r}: {(top.stderr or diff.stderr).strip()}", file=sys.stderr)
        return None
    return parse_diff(diff.stdout, Path(top.stdout.strip()))


def under(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def targets(argv: list[str]) -> tuple[list[Path], dict[Path, set[int]] | None] | None:
    args = list(argv[1:])
    if "--changed" not in args:
        return sources([Path(a).resolve() for a in args] or [Path.cwd()]), None
    at = args.index("--changed")
    if at + 1 >= len(args):
        print("--changed needs a range", file=sys.stderr)
        return None
    added = changed_lines(args[at + 1])
    if added is None:
        return None
    roots = [Path(a).resolve() for a in args[:at] + args[at + 2:]] or [Path.cwd()]
    paths = sorted(p for p in added if wanted(p) and p.is_file() and under(p, roots))
    return paths, added


def main(argv: list[str]) -> int:
    chosen = targets(argv)
    if chosen is None:
        return 2
    paths, added = chosen
    base = Path.cwd()
    findings: list[Finding] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        only = added.get(path) if added is not None else None
        findings.extend(scan(lines, display(path, base), only))
    return report(findings, len(paths))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
