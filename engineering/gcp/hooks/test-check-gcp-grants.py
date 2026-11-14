#!/usr/bin/env python3
"""Tests for check-gcp-grants.py, and for the plugin passing the artifact gate.

Each condition the hook decides is pinned by a failing fixture and by the
neighbour it must not flag: a narrower role that shares the `roles/` prefix, a
comment that mentions a public principal, a grant allowed with a reason, and the
marker without one. Each case builds a throwaway tree and runs the hook as a
subprocess.

The last case runs the repository's artifact gate, which also decides that the
plugin dependency graph stays acyclic: #298/AC-6.

Usage:
    python3 engineering/gcp/hooks/test-check-gcp-grants.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-gcp-grants.py"
REPO = Path(__file__).resolve().parents[3]

CASES = [
    ("basic role in Terraform", "main.tf", 'role = "roles/editor"\n', "condition 1"),
    ("basic role in gcloud", "grant.sh", "gcloud projects add-iam-policy-binding p --role=roles/owner\n", "condition 1"),
    ("key resource", "keys.tf", 'resource "google_service_account_key" "ci" {\n', "condition 4"),
    ("key created by gcloud", "ci.sh", "gcloud iam service-accounts keys create key.json\n", "condition 4"),
    ("public member", "bucket.tf", 'member = "allUsers"\n', "condition 5"),
    ("public authenticated member", "iam.yaml", "member: allAuthenticatedUsers\n", "condition 5"),
    ("marker without a reason", "main.tf", '# gcp-grant-allowed:\nrole = "roles/viewer"\n', "condition 1"),
]

CLEAN = [
    ("narrower role", "main.tf", 'role = "roles/secretmanager.secretAccessor"\n'),
    ("role whose name only starts like a basic one", "main.tf", 'role = "roles/editorial.reader"\n'),
    ("comment", "main.tf", "# never grant allUsers here\n"),
    ("allowed with a reason", "site.tf", '# gcp-grant-allowed: public website assets\nmember = "allUsers"\n'),
    ("markdown is not read", "notes.md", "roles/owner allUsers\n"),
]


def run(name: str, text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as root:
        (Path(root) / name).write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(HOOK), root], capture_output=True, text=True)


def check_failing() -> list[str]:
    errors: list[str] = []
    for label, name, text, expected in CASES:
        result = run(name, text)
        if result.returncode != 1 or expected not in result.stdout:
            errors.append(f"{label}: expected a failure naming {expected}, got {result.stdout!r}")
    return errors


def check_clean() -> list[str]:
    errors: list[str] = []
    for label, name, text in CLEAN:
        result = run(name, text)
        if result.returncode != 0:
            errors.append(f"{label}: expected no failure, got {result.stdout!r}")
    return errors


def check_gate() -> list[str]:
    """#298/AC-6: the artifact gate passes with this plugin listed, graph acyclic."""
    gate = REPO / "foundation" / "hooks" / "validate-artifacts.py"
    result = subprocess.run([sys.executable, str(gate), str(REPO)], capture_output=True, text=True)
    if result.returncode != 0:
        return [f"artifact gate failed:\n{result.stdout}{result.stderr}"]
    return []


def main() -> int:
    errors = check_failing() + check_clean() + check_gate()
    for error in errors:
        print(error)
    total = len(CASES) + len(CLEAN) + 1
    print(f"{total - len(errors)} of {total} cases passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
