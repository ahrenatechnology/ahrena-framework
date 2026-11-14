#!/usr/bin/env python3
"""Tests for check-gcp-grants.py, and for the plugin passing the artifact gate.

Each condition the hook decides is pinned by a failing fixture and by the
neighbour it must not flag: a narrower role that shares the `roles/` prefix, a
comment that mentions a public principal, a grant allowed with a reason, and the
marker without one. Each case builds a throwaway tree and runs the hook as a
subprocess.

Two cases run the hook with `--changed` in a throwaway git repository: a
grant that was already in a modified file is not the change's, and a grant
the change adds is (#307/AC-1).

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
    ("a Cloud KMS key", "kms.sh", "gcloud kms keys create k --keyring r --purpose encryption --rotation-period 90d\n"),
    ("an API key", "apikey.sh", "gcloud services api-keys create --display-name web\n"),
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


def git(root: str, *args: str) -> None:
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True)


def check_changed() -> list[str]:
    """#307/AC-1: with --changed, only the lines the range adds are read."""
    with tempfile.TemporaryDirectory() as root:
        git(root, "init", "-q")
        git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        tf = Path(root) / "main.tf"
        tf.write_text('role = "roles/editor"\n', encoding="utf-8")
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "old")
        tf.write_text('role = "roles/editor"\nname = "unrelated"\n', encoding="utf-8")
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "clean")
        quiet = subprocess.run([sys.executable, str(HOOK), "--changed", "HEAD~1...HEAD"], cwd=root, capture_output=True, text=True)
        tf.write_text('role = "roles/editor"\nname = "unrelated"\nmember = "allUsers"\n', encoding="utf-8")
        loud = subprocess.run([sys.executable, str(HOOK), "--changed", "HEAD"], cwd=root, capture_output=True, text=True)
        git(root, "config", "diff.noprefix", "true")
        noprefix = subprocess.run([sys.executable, str(HOOK), "--changed", "HEAD"], cwd=root, capture_output=True, text=True)
        option = subprocess.run([sys.executable, str(HOOK), "--changed", "--name-only"], cwd=root, capture_output=True, text=True)
    errors: list[str] = []
    if noprefix.returncode != 1 or "main.tf:3" not in noprefix.stdout:
        errors.append(f"--changed lost the added line under diff.noprefix: {noprefix.stdout!r}{noprefix.stderr!r}")
    if option.returncode != 2:
        errors.append(f"--changed accepted an option as the range: {option.returncode} {option.stdout!r}")
    if quiet.returncode != 0:
        errors.append(f"--changed reported a line the range did not add: {quiet.stdout!r}{quiet.stderr!r}")
    if loud.returncode != 1 or "main.tf:3" not in loud.stdout or "main.tf:1" in loud.stdout:
        errors.append(f"--changed did not report only the added line 3: {loud.stdout!r}{loud.stderr!r}")
    return errors


def check_gate() -> list[str]:
    """#298/AC-6, #307/AC-4: the artifact gate passes with this plugin listed, graph acyclic."""
    gate = REPO / "foundation" / "hooks" / "validate-artifacts.py"
    result = subprocess.run([sys.executable, str(gate), str(REPO)], capture_output=True, text=True)
    if result.returncode != 0:
        return [f"artifact gate failed:\n{result.stdout}{result.stderr}"]
    return []


def main() -> int:
    errors = check_failing() + check_clean() + check_changed() + check_gate()
    for error in errors:
        print(error)
    total = len(CASES) + len(CLEAN) + 2
    print(f"{total - len(errors)} of {total} cases passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
