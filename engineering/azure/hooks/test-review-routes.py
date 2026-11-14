#!/usr/bin/env python3
"""Tests for review-routes.json: each Azure route fires on the file it is for.

Builds a throwaway git repository with one commit per case, runs the core
router with this plugin's fragment, and checks which Azure routes fired.
Standard library only, like every hook in this repository.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent
ROUTER = REPO / "engineering" / "quality" / "hooks" / "route-review.py"
FRAGMENT = PLUGIN / "review-routes.json"

CASES = [
    ("a Bicep module call fires azure-bicep", "infra/main.bicep",
     "module app 'br/public:avm/res/web/site:0.1.0' = {\n  name: 'app'\n}\n", {"azure-bicep"}),
    ("a Bicep parameters file fires azure-bicep", "infra/main.bicepparam",
     "using 'main.bicep'\nparam location = 'westeurope'\n", {"azure-bicep"}),
    ("an ARM template fires azure-iac", "infra/azuredeploy.json",
     '{"$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#", "resources": []}\n',
     {"azure-iac"}),
    ("a provider block alone fires azure-iac", "infra/providers.tf",
     'provider "azurerm" {\n  features {}\n}\n', {"azure-iac"}),
    ("a workflow signing in to Azure fires azure-pipeline", ".github/workflows/deploy.yml",
     "jobs:\n  d:\n    steps:\n      - uses: azure/login@v2\n      - run: az account show\n", {"azure-pipeline"}),
    ("an SDK exception handler fires azure-sdk", "src/store.py",
     "from azure.core.exceptions import HttpResponseError\n", {"azure-sdk"}),
    ("a package manifest fires no Azure route", "package.json", '{"name": "x"}\n', set()),
    ("a workflow with no Azure step fires no Azure route", ".github/workflows/test.yml",
     "jobs:\n  t:\n    steps:\n      - run: make test\n", set()),
]
AZURE = {"azure-bicep", "azure-iac", "azure-pipeline", "azure-sdk"}


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def fired(path: str, text: str) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git(root, "init", "-q")
        git(root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "base")
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "case")
        out = subprocess.run(
            [sys.executable, str(ROUTER), "--changed", "HEAD~1...HEAD", "--plugin-routes", str(FRAGMENT)],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
    return {line.split()[1] for line in out.splitlines() if line.startswith("route ")} & AZURE


def main() -> int:
    failures = 0
    for name, path, text, expected in CASES:
        got = fired(path, text)
        ok = got == expected
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {name}" + ("" if ok else f": expected {sorted(expected)}, got {sorted(got)}"))
    print(f"\n{len(CASES) - failures} of {len(CASES)} cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
