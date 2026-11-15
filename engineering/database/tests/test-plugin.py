#!/usr/bin/env python3
"""Tests for the ahrena-engineering-database plugin's wiring.

Each property is one a script can decide:

    1. the artifact gate passes over the whole marketplace, which includes the
       acyclic plugin graph and the agent's skills and delegation (#324/AC-1)
    2. the plugin is catalogued, its three manifests agree, and the installer
       enables it as a core plugin, since Apollo and Clio delegate to it
    3. the agent loads the three skills and states that it writes no
       production code, opens no pull request and publishes no verdict
       (#324/AC-1)
    4. Apollo delegates the persistence design before the OLTP layer and passes
       it to Hephaestus; Clio does the same before a transactional schema
       (#324/AC-5)
    5. the core review table routes a migration, a SQL file, the mode registry
       and an adapter that writes to reviewing-persistence, and leaves a module
       with no persistence in it alone (#324/AC-5)

Standard library only. Run from anywhere:

    python3 engineering/database/tests/test-plugin.py
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
NAME = "ahrena-engineering-database"
AGENT = f"{NAME}:chronos"
SKILL = f"{NAME}:skills/reviewing-persistence/SKILL.md"
SKILLS = ("designing-persistence", "reviewing-persistence", "diagnosing-database")

MIGRATION = "CREATE TABLE orders (id uuid PRIMARY KEY, version integer NOT NULL);\n"
REGISTRY = "tables:\n  orders:\n    mode: upsert-with-history\n"
ADAPTER = """\
def save(session, order):
    session.execute("UPDATE orders SET status = :status WHERE id = :id", order)
"""
TS_ADAPTER = 'import { Pool } from "pg";\nexport const pool = new Pool();\n'
PLAIN = "def total(lines):\n    return sum(line.amount for line in lines)\n"


def test_gate_passes() -> list[str]:
    run = subprocess.run(
        [sys.executable, str(ROOT / "foundation/hooks/validate-artifacts.py"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0 or "no failures" not in run.stdout:
        return [f"the artifact gate failed:\n{run.stdout}{run.stderr}"]
    return []


def test_catalogued() -> list[str]:
    failures = []
    market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    entries = [p for p in market["plugins"] if p["name"] == NAME]
    if len(entries) != 1:
        return [f"the marketplace lists {NAME} {len(entries)} time(s)"]
    if entries[0]["source"].get("path") != "engineering/database":
        failures.append("the marketplace entry does not point at engineering/database")
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
    agency = ROOT / "engineering/development/skills/installing-the-agency/references/agency.json"
    if NAME not in json.loads(agency.read_text())["plugins"]:
        failures.append("the installer does not enable the plugin as core, yet Apollo and Clio delegate to it")
    return failures


def test_agent() -> list[str]:
    failures = []
    body = (PLUGIN / "agents/chronos.md").read_text()
    for skill in SKILLS:
        if f"  - {NAME}:{skill}\n" not in body:
            failures.append(f"chronos does not load {skill}")
    for claim in ("write no production code", "open no pull request", "publish no review verdict"):
        if claim not in body:
            failures.append(f"chronos does not state: {claim}")
    return failures


def _delegates(body: str, situation: str) -> bool:
    rows = [line for line in body.splitlines() if line.startswith("| ") and f"`{AGENT}`" in line]
    return any(situation in row and "`mode: design`" in row for row in rows)


def test_builders_call_the_design() -> list[str]:
    failures = []
    apollo = (ROOT / "engineering/backend/agents/apollo.md").read_text()
    if not _delegates(apollo, "oltp"):
        failures.append("apollo has no delegation row to chronos in design mode before the oltp layer")
    step4 = next((line for line in apollo.splitlines() if line.startswith("4. ")), "")
    if f"`{AGENT}`" not in step4 or "oltp" not in step4:
        failures.append("apollo's step 4 does not delegate the persistence design before the oltp layer")
    if not re.search(r"hephaestus`.*`design` at the oltp layer", apollo):
        failures.append("apollo does not pass the design to hephaestus at the oltp layer")
    hephaestus = (ROOT / "engineering/backend/agents/hephaestus.md").read_text()
    if "- `design`:" not in hephaestus:
        failures.append("hephaestus takes no `design` input")
    clio = (ROOT / "engineering/data/agents/clio.md").read_text()
    if not _delegates(clio, "transactional schema"):
        failures.append("clio has no delegation row to chronos in design mode before a transactional schema")
    mnemosyne = (ROOT / "engineering/data/agents/mnemosyne.md").read_text()
    if "- `design`:" not in mnemosyne:
        failures.append("mnemosyne takes no `design` input")
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
            [sys.executable, str(ROOT / "engineering/quality/hooks/route-review.py"), "--cached", "--json"],
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
    failures = []
    fired = routed(
        {
            "db/migrations/0007_orders.sql": MIGRATION,
            "db/migrations/persistence-modes.yaml": REGISTRY,
            "src/orders/repository.py": ADAPTER,
            "src/orders/pool.ts": TS_ADAPTER,
            "src/orders/pricing.py": PLAIN,
        }
    )
    expected = {
        "persistence-schema": ["db/migrations/0007_orders.sql", "db/migrations/persistence-modes.yaml"],
        "persistence-adapters": ["src/orders/pool.ts", "src/orders/repository.py"],
    }
    for route, paths in expected.items():
        if fired.get(route) != paths:
            failures.append(f"route {route} fired on {fired.get(route)}, expected {paths}")
    reached = {path for paths in fired.values() for path in paths}
    if "src/orders/pricing.py" in reached:
        failures.append("a module with no persistence in it was routed to reviewing-persistence")
    return failures


def main() -> int:
    failures = []
    for test in (test_gate_passes, test_catalogued, test_agent, test_builders_call_the_design, test_routes):
        found = test()
        status = "FAIL" if found else "ok"
        print(f"{status:4}  {test.__name__}")
        failures.extend(found)
    for failure in failures:
        print(f"  {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
