#!/usr/bin/env python3
"""Tests for the ahrena-engineering-llm-systems plugin's wiring.

Each property is one a script can decide:

    1. the artifact gate passes over the whole marketplace, including the
       acyclic plugin graph (#351/AC-5, #352/AC-4, #353/AC-3)
    2. the plugin is catalogued and its three manifests agree with the
       catalogue on name and version (#351/AC-1)
    3. the plugin declares references only to itself and to
       ahrena-engineering-fundamentals, so the edge Claudionor adds from
       ahrena-foundation cannot close a cycle (ADR-021)
    4. the plugin's review-routes.json sends a change that calls a model and
       a manifest that adds an agent framework to reviewing-llm-systems, and
       leaves code with no model in it alone

Standard library only. Run from anywhere:

    python3 -B engineering/llm-systems/tests/test-plugin.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ROOT = PLUGIN.parent.parent
NAME = "ahrena-engineering-llm-systems"
ALLOWED = {NAME, "ahrena-engineering-fundamentals"}
SKILL = f"{NAME}:skills/reviewing-llm-systems/SKILL.md"
AGENT_CODE = """\
import anthropic

def classify(client, text):
    return client.messages.create(model=MODEL, max_tokens=64, messages=[{"role": "user", "content": text}])
"""
MANIFEST = '[project]\nname = "support"\ndependencies = ["langgraph==1.1.4"]\n'
PLAIN = "def total(lines):\n    return sum(line.amount for line in lines)\n"
QUALIFIED = re.compile(r"^\s*-\s*(ahrena-[a-z0-9-]+):", re.MULTILINE)


def test_gate_passes() -> list[str]:
    """#351/AC-5, #352/AC-4, #353/AC-3"""
    run = subprocess.run(
        [sys.executable, "-B", str(ROOT / "foundation/hooks/validate-artifacts.py"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0 or "no failures" not in run.stdout:
        return [f"the artifact gate failed:\n{run.stdout}{run.stderr}"]
    return []


def test_catalogued() -> list[str]:
    """#351/AC-1"""
    catalogue = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    entries = [p for p in catalogue["plugins"] if p["name"] == NAME]
    if len(entries) != 1:
        return [f"{NAME} is listed {len(entries)} times in the marketplace"]
    entry = entries[0]
    errors = []
    if entry["source"]["path"] != "engineering/llm-systems":
        errors.append(f"the marketplace points {NAME} at {entry['source']['path']}")
    for platform in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
        path = PLUGIN / platform / "plugin.json"
        if not path.is_file():
            errors.append(f"{platform}/plugin.json is missing")
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for key in ("name", "version"):
            if manifest.get(key) != entry[key]:
                errors.append(f"{platform}/plugin.json {key} is {manifest.get(key)!r}, the marketplace has {entry[key]!r}")
    return errors


def test_references_stay_downstream_of_nothing() -> list[str]:
    """ADR-021: only itself and fundamentals."""
    errors = []
    for path in sorted(PLUGIN.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        frontmatter = text.split("---", 2)[1]
        for owner in QUALIFIED.findall(frontmatter):
            if owner not in ALLOWED:
                errors.append(f"{path.relative_to(ROOT)} references {owner}, which ADR-021 does not allow")
    return errors


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
                "-B",
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
    """#353/AC-2: a change that builds an LLM system reaches the review skill."""
    fired = routed({"src/support/classify.py": AGENT_CODE, "pyproject.toml": MANIFEST, "src/math.py": PLAIN})
    expected = {"llm-systems-code": ["src/support/classify.py"], "llm-systems-manifests": ["pyproject.toml"]}
    return [
        f"route {route} fired on {fired.get(route)}, expected {paths}"
        for route, paths in expected.items()
        if fired.get(route) != paths
    ]


if __name__ == "__main__":
    failures = []
    for test in (test_gate_passes, test_catalogued, test_references_stay_downstream_of_nothing, test_routes):
        errors = test()
        print(f"{'ok  ' if not errors else 'FAIL'}  {test.__name__}")
        failures += errors
    for error in failures:
        print(f"  {error}")
    sys.exit(1 if failures else 0)
