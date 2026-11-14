#!/usr/bin/env python3
"""Tests for the ahrena-engineering-aws plugin's wiring.

Three properties, each one a script can decide:

    1. the artifact gate passes over the whole marketplace, which includes
       the acyclic plugin graph (#296/AC-7)
    2. the plugin is catalogued with its three manifests agreeing (#296/AC-1)
    3. the plugin's review-route fragment selects reviewing-aws for a handler
       that hands an AWS SDK error back to its caller, the anonymised shape of
       the incident behind the framework's exposure rule, and for AWS infrastructure files (#296/AC-5)

Standard library only. Run from anywhere:

    python3 engineering/aws/tests/test-plugin.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ROOT = PLUGIN.parent.parent
NAME = "ahrena-engineering-aws"
SKILL = f"{NAME}:skills/reviewing-aws/SKILL.md"

INCIDENT_HANDLER = """\
from botocore.exceptions import ClientError


def store_credential(client, name, value):
    try:
        client.put_secret_value(SecretId=name, SecretString=value)
    except ClientError as error:
        return {"error": str(error)}, 500
    return {"stored": True}, 201
"""

TEMPLATE = 'AWSTemplateFormatVersion: "2010-09-09"\nResources:\n  Bucket:\n    Type: AWS::S3::Bucket\n'
TERRAFORM = 'resource "aws_s3_bucket" "uploads" {}\n'
POLICY = '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}\n'
PLAIN = "def add(a, b):\n    return a + b\n"


def test_gate_passes() -> list[str]:
    # #296/AC-7
    run = subprocess.run(
        [sys.executable, str(ROOT / "foundation/hooks/validate-artifacts.py"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0 or "no failures" not in run.stdout:
        return [f"the artifact gate failed:\n{run.stdout}{run.stderr}"]
    return []


def test_catalogued() -> list[str]:
    # #296/AC-1
    failures = []
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    entries = [p for p in market["plugins"] if p["name"] == NAME]
    if len(entries) != 1:
        return [f"the marketplace lists {NAME} {len(entries)} time(s)"]
    if entries[0]["source"].get("path") != "engineering/aws":
        failures.append("the marketplace entry does not point at engineering/aws")
    versions = {entries[0]["version"]}
    for platform in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
        manifest = PLUGIN / platform / "plugin.json"
        if not manifest.is_file():
            failures.append(f"{platform}/plugin.json is missing")
            continue
        data = json.loads(manifest.read_text())
        if data.get("name") != NAME:
            failures.append(f"{platform}/plugin.json names {data.get('name')!r}")
        versions.add(data.get("version"))
    if len(versions) != 1:
        failures.append(f"the manifests and the marketplace disagree on the version: {sorted(map(str, versions))}")
    return failures


def routed(files: dict[str, str]) -> dict[str, list[str]]:
    """Stage files in a scratch repository and return {route id: files it fired on}."""
    with tempfile.TemporaryDirectory() as scratch:
        git = ["git", "-C", scratch, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True)
        for path, text in files.items():
            target = Path(scratch) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        subprocess.run([*git, "add", "-A"], check=True)
        run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "engineering/quality/hooks/route-review.py"),
                "--cached",
                "--json",
                "--plugin-routes",
                str(PLUGIN / "review-routes.json"),
            ],
            cwd=scratch,
            capture_output=True,
            text=True,
        )
        if run.returncode != 0:
            raise RuntimeError(f"the router exited {run.returncode}: {run.stderr}")
        report = json.loads(run.stdout)
    fired: dict[str, list[str]] = {}
    for route in report["routes"]:
        if route["skill"] == SKILL:
            fired[route["id"]] = sorted({hit.split(":")[0] for hit in route["on"]})
    return fired


def test_routes() -> list[str]:
    # #296/AC-5
    failures = []
    fired = routed(
        {
            "src/credentials/handler.py": INCIDENT_HANDLER,
            "infra/stack.yaml": TEMPLATE,
            "infra/main.tf": TERRAFORM,
            "infra/policy.json": POLICY,
            "src/math.py": PLAIN,
        }
    )
    expected = {
        "aws-application": ["src/credentials/handler.py"],
        "aws-templates": ["infra/stack.yaml"],
        "aws-terraform": ["infra/main.tf"],
        "aws-policy-documents": ["infra/policy.json"],
    }
    for route, paths in expected.items():
        if fired.get(route) != paths:
            failures.append(f"route {route} fired on {fired.get(route)}, expected {paths}")
    reached = {path for paths in fired.values() for path in paths}
    if "src/math.py" in reached:
        failures.append("a file with no AWS in it was routed to reviewing-aws")
    return failures


def main() -> int:
    failures = []
    for test in (test_gate_passes, test_catalogued, test_routes):
        found = test()
        status = "FAIL" if found else "ok"
        print(f"{status:4}  {test.__name__}")
        failures.extend(found)
    for failure in failures:
        print(f"  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
