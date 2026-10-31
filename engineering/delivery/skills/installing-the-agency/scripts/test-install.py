#!/usr/bin/env python3
"""Tests for install.py.

Each case builds a throwaway repository and a throwaway Claude config
directory, runs the script as a subprocess, and asserts on the exit code, the
report and the files. The config directory is always a temporary one, so no case
reads or writes the real `~/.claude`.

Usage:
    python3 engineering/delivery/skills/installing-the-agency/scripts/test-install.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "install.py"
AGENCY = json.loads((HERE.parent / "references" / "agency.json").read_text(encoding="utf-8"))
MARKETPLACE = HERE.parents[4] / ".claude-plugin" / "marketplace.json"

CORE = [f"{name}@ahrena" for name in AGENCY["plugins"]]
SOURCE = {"source": {"source": "github", "repo": "ahrenatechnology/ahrena-framework"}}


def run(root: Path, config: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, str(root)],
        capture_output=True,
        text=True,
        env=env,
    )


def settings(root: Path) -> dict:
    return json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))


def put(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


class Case:
    """A repository and a config directory that live for one test."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.root = base / "repo"
        self.config = base / "config"
        self.root.mkdir()
        self.config.mkdir()
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return run(self.root, self.config, *args)


FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        FAILURES.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL {name}" + (f"\n     {detail}" if detail else ""))
    else:
        print(f"ok   {name}")


def test_fresh_repo_writes_exact_shape() -> None:
    with Case() as c:
        r = c.run()
        expected = {
            "extraKnownMarketplaces": {"ahrena": SOURCE},
            "enabledPlugins": {plugin: True for plugin in CORE},
        }
        check("fresh: exit 0", r.returncode == 0, r.stderr)
        check("fresh: settings shape", settings(c.root) == expected, str(settings(c.root)))
        text = (c.root / ".claude" / "settings.json").read_text(encoding="utf-8")
        check("fresh: two-space indent and trailing newline", text.endswith("}\n") and '\n  "enabledPlugins"' in text)
        check("fresh: no ref on the marketplace", "ref" not in json.dumps(settings(c.root)["extraKnownMarketplaces"]))
        check("fresh: directive written", "ahrena:agency:start" in (c.root / "CLAUDE.md").read_text(encoding="utf-8"))


def test_preserves_other_keys_and_order() -> None:
    with Case() as c:
        put(
            c.root / ".claude" / "settings.json",
            '{"env": {"A": "1"}, "enabledPlugins": {"other@x": true}, "permissions": {"allow": ["Bash"]},'
            ' "extraKnownMarketplaces": {"mine": {"source": {"source": "github", "repo": "me/mine"}}}}',
        )
        r = c.run()
        data = settings(c.root)
        check("preserve: exit 0", r.returncode == 0, r.stderr)
        check("preserve: key order", list(data) == ["env", "enabledPlugins", "permissions", "extraKnownMarketplaces"], str(list(data)))
        check("preserve: own entries first", list(data["enabledPlugins"])[0] == "other@x")
        check("preserve: other values intact", data["env"] == {"A": "1"} and data["permissions"] == {"allow": ["Bash"]})
        check("preserve: own marketplace first", list(data["extraKnownMarketplaces"]) == ["mine", "ahrena"])


def test_disabled_entry_not_flipped() -> None:
    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {"ahrena-foundation@ahrena": False}})
        r = c.run()
        check("disabled: still false", settings(c.root)["enabledPlugins"]["ahrena-foundation@ahrena"] is False)
        check("disabled: reported", "ahrena-foundation@ahrena is disabled" in r.stdout, r.stdout)
        check("disabled: the others enabled", settings(c.root)["enabledPlugins"]["ahrena-contributing@ahrena"] is True)


def test_existing_marketplace_untouched() -> None:
    with Case() as c:
        mine = {"source": {"source": "github", "repo": "ahrenatechnology/ahrena-framework", "ref": "main"}}
        put(c.root / ".claude" / "settings.json", {"extraKnownMarketplaces": {"ahrena": mine}})
        r = c.run()
        check("marketplace: kept with its ref", settings(c.root)["extraKnownMarketplaces"]["ahrena"] == mine)
        check("marketplace: difference reported", "already declared differently" in r.stdout, r.stdout)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"extraKnownMarketplaces": {"ahrena": SOURCE}})
        r = c.run()
        check("marketplace: identical entry not reported", "differently" not in r.stdout, r.stdout)


def test_second_run_writes_nothing() -> None:
    with Case() as c:
        c.run()
        settings_path = c.root / ".claude" / "settings.json"
        before = (settings_path.read_bytes(), (c.root / "CLAUDE.md").read_bytes(), settings_path.stat().st_mtime_ns)
        r = c.run()
        after = (settings_path.read_bytes(), (c.root / "CLAUDE.md").read_bytes(), settings_path.stat().st_mtime_ns)
        check("idempotent: exit 0", r.returncode == 0, r.stderr)
        check("idempotent: nothing rewritten", before == after)
        check("idempotent: says so", "nothing written" in r.stdout and "already current" in r.stdout, r.stdout)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", '{"enabledPlugins":{"x@y":true}}')
        c.run()
        c.run()
        check("idempotent: reformatting not repeated", settings(c.root)["enabledPlugins"]["x@y"] is True)


def test_unchanged_file_keeps_its_formatting() -> None:
    with Case() as c:
        c.run()
        path = c.root / ".claude" / "settings.json"
        compact = json.dumps(settings(c.root))
        path.write_text(compact, encoding="utf-8")
        c.run()
        check("no rewrite when content is complete", path.read_text(encoding="utf-8") == compact)


def test_malformed_json() -> None:
    with Case() as c:
        path = c.root / ".claude" / "settings.json"
        put(path, "{ not json")
        r = c.run()
        check("malformed: exit 2", r.returncode == 2, str(r.returncode))
        check("malformed: file untouched", path.read_text(encoding="utf-8") == "{ not json")
        check("malformed: reported on stderr", "not valid JSON" in r.stderr, r.stderr)
        check("malformed: directive not written either", not (c.root / "CLAUDE.md").exists())

    with Case() as c:
        put(c.root / ".claude" / "settings.json", "[]")
        r = c.run()
        check("non-object: exit 2", r.returncode == 2, str(r.returncode))

    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": []})
        r = c.run()
        check("wrong-typed enabledPlugins: exit 2", r.returncode == 2, str(r.returncode))


def test_language_detection() -> None:
    cases = {
        "pyproject.toml": "ahrena-engineering-python",
        "requirements.txt": "ahrena-engineering-python",
        "setup.py": "ahrena-engineering-python",
        "tsconfig.json": "ahrena-engineering-typescript",
        "package.json": "ahrena-engineering-typescript",
        "go.mod": "ahrena-engineering-go",
        "Cargo.toml": "ahrena-engineering-rust",
    }
    for marker, plugin in cases.items():
        with Case() as c:
            (c.root / marker).write_text("", encoding="utf-8")
            c.run()
            extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
            check(f"detect {marker}", extra == [f"{plugin}@ahrena"], str(extra))

    with Case() as c:
        c.run()
        check("detect: none leaves only the core", list(settings(c.root)["enabledPlugins"]) == CORE)

    with Case() as c:
        (c.root / "go.mod").write_text("", encoding="utf-8")
        (c.root / "Cargo.toml").write_text("", encoding="utf-8")
        c.run()
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        check("detect: two languages", sorted(extra) == ["ahrena-engineering-go@ahrena", "ahrena-engineering-rust@ahrena"], str(extra))


def test_language_flag() -> None:
    with Case() as c:
        (c.root / "pyproject.toml").write_text("", encoding="utf-8")
        c.run("--language", "go")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        check("--language replaces detection", extra == ["ahrena-engineering-go@ahrena"], str(extra))

    with Case() as c:
        c.run("--language", "go", "--language", "rust")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        check("--language repeatable", extra == ["ahrena-engineering-go@ahrena", "ahrena-engineering-rust@ahrena"], str(extra))

    with Case() as c:
        c.run("--language", "python,typescript")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        check("--language comma list", extra == ["ahrena-engineering-python@ahrena", "ahrena-engineering-typescript@ahrena"], str(extra))

    with Case() as c:
        r = c.run("--language", "cobol")
        check("--language unknown: exit 2", r.returncode == 2 and "cobol" in r.stderr, r.stderr)
        check("--language unknown: nothing written", not (c.root / ".claude").exists())


def test_platform_codex_skips_settings() -> None:
    with Case() as c:
        r = c.run("--platform", "codex")
        check("codex: exit 0", r.returncode == 0, r.stderr)
        check("codex: no settings.json", not (c.root / ".claude").exists())
        check("codex: AGENTS.md written", "ahrena:agency:start" in (c.root / "AGENTS.md").read_text(encoding="utf-8"))
        check("codex: depth note surfaced", "max_depth" in r.stdout)


def test_check_is_read_only_and_reports_states() -> None:
    with Case() as c:
        r = c.run("--check")
        check("check empty: exit 1", r.returncode == 1, str(r.returncode))
        check("check empty: writes nothing", not (c.root / ".claude").exists() and not (c.root / "CLAUDE.md").exists())
        check("check empty: every plugin missing", sum(l.endswith(" missing") for l in r.stdout.splitlines()) == len(CORE), r.stdout)
        check("check empty: directive absent", "ABSENT" in r.stdout, r.stdout)

    with Case() as c:
        c.run()
        r = c.run("--check")
        check("check full: exit 0", r.returncode == 0, r.stdout + r.stderr)
        check("check full: all enabled", r.stdout.count(" enabled") == len(CORE), r.stdout)

    # Enabled by each of the three scopes in turn.
    one = "ahrena-foundation@ahrena"
    for label, path_of in (
        ("project", lambda c: c.root / ".claude" / "settings.json"),
        ("local", lambda c: c.root / ".claude" / "settings.local.json"),
        ("user", lambda c: c.config / "settings.json"),
    ):
        with Case() as c:
            put(path_of(c), {"enabledPlugins": {one: True}})
            r = c.run("--check")
            line = next((l for l in r.stdout.splitlines() if l.startswith(f"plugin: {one}")), "")
            check(f"check {label}: counted as enabled", " enabled" in line, r.stdout)

    # Disabled where nothing else enables it: reported, fails.
    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {one: False}})
        r = c.run("--check")
        line = next((l for l in r.stdout.splitlines() if l.startswith(f"plugin: {one}")), "")
        check("check disabled: reported", " disabled" in line, r.stdout)

    # Disabled in the project but enabled at user scope: counts as enabled.
    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {**{p: True for p in CORE}, one: False}})
        put(c.config / "settings.json", {"enabledPlugins": {one: True}})
        r = c.run("--check")
        check("check disabled-but-enabled-elsewhere: exit 0", r.returncode == 0, r.stdout)

    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {**{p: True for p in CORE}, one: False}})
        r = c.run("--check")
        check("check disabled-and-nowhere-else: exit 1", r.returncode == 1, r.stdout)

    # A stale directive fails even when every plugin is enabled.
    with Case() as c:
        c.run()
        md = c.root / "CLAUDE.md"
        md.write_text(md.read_text(encoding="utf-8").replace("athena", "someone"), encoding="utf-8")
        r = c.run("--check")
        check("check stale directive: exit 1", r.returncode == 1 and "STALE" in r.stdout, r.stdout)

    # Language plugins are part of what --check expects.
    with Case() as c:
        c.run()
        (c.root / "go.mod").write_text("", encoding="utf-8")
        r = c.run("--check")
        check("check language: go plugin missing", r.returncode == 1 and "ahrena-engineering-go@ahrena missing" in r.stdout, r.stdout)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", "{ not json")
        r = c.run("--check")
        check("check malformed: exit 2", r.returncode == 2, str(r.returncode))


def test_directive_untouched_around_markers() -> None:
    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# Mine\n\nkeep this\n", encoding="utf-8")
        c.run()
        text = (c.root / "CLAUDE.md").read_text(encoding="utf-8")
        check("directive: surrounding content kept", text.startswith("# Mine\n\nkeep this\n"))


def test_declared_plugins_exist_in_marketplace() -> None:
    published = {p["name"] for p in json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]}
    declared = set(AGENCY["plugins"]) | {spec["plugin"] for spec in AGENCY["languages"].values()}
    missing = sorted(declared - published)
    check("agency.json: every plugin is in marketplace.json", not missing, f"missing: {missing}")
    check("agency.json: marketplace name matches", AGENCY["marketplace"]["name"] == json.loads(MARKETPLACE.read_text(encoding="utf-8"))["name"])


def main() -> int:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if FAILURES:
        print(f"\n{len(FAILURES)} failed")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
