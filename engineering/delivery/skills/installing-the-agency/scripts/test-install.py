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


def test_fresh_repo_writes_exact_shape() -> None:
    with Case() as c:
        r = c.run()
        expected = {
            "extraKnownMarketplaces": {"ahrena": SOURCE},
            "enabledPlugins": {plugin: True for plugin in CORE},
        }
        assert r.returncode == 0, "fresh: exit 0" + ": " + str(r.stderr)
        assert settings(c.root) == expected, "fresh: settings shape" + ": " + str(str(settings(c.root)))
        text = (c.root / ".claude" / "settings.json").read_text(encoding="utf-8")
        assert text.endswith("}\n") and '\n  "enabledPlugins"' in text, "fresh: two-space indent and trailing newline"
        assert "ref" not in json.dumps(settings(c.root)["extraKnownMarketplaces"]), "fresh: no ref on the marketplace"
        assert "ahrena:agency:start" in (c.root / "CLAUDE.md").read_text(encoding="utf-8"), "fresh: directive written"


def test_default_writes_every_file_present() -> None:
    with Case() as c:
        c.run()
        for name in ("CLAUDE.md", "AGENTS.md"):
            assert "ahrena:agency:start" in (c.root / name).read_text(encoding="utf-8"), name

    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# Mine\n", encoding="utf-8")
        c.run()
        assert not (c.root / "AGENTS.md").exists(), "only the file present is written"
        assert "ahrena:agency:start" in (c.root / "CLAUDE.md").read_text(encoding="utf-8")

    with Case() as c:
        (c.root / "AGENTS.md").write_text("# Mine\n", encoding="utf-8")
        c.run()
        assert not (c.root / "CLAUDE.md").exists() and not (c.root / ".claude").exists(), "codex alone skips settings"

    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# a\n", encoding="utf-8")
        (c.root / "AGENTS.md").write_text("# b\n", encoding="utf-8")
        r = c.run()
        assert r.returncode == 0, r.stderr
        for name in ("CLAUDE.md", "AGENTS.md"):
            assert "ahrena:agency:start" in (c.root / name).read_text(encoding="utf-8"), name


def test_platform_limits_the_run_to_one_file() -> None:
    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# a\n", encoding="utf-8")
        (c.root / "AGENTS.md").write_text("# b\n", encoding="utf-8")
        c.run("--platform", "claude")
        assert "ahrena:agency" not in (c.root / "AGENTS.md").read_text(encoding="utf-8")
        assert "ahrena:agency" in (c.root / "CLAUDE.md").read_text(encoding="utf-8")


def test_check_reports_each_file() -> None:
    with Case() as c:
        c.run()
        md = c.root / "AGENTS.md"
        md.write_text(md.read_text(encoding="utf-8").replace("athena", "someone"), encoding="utf-8")
        r = c.run("--check")
        assert "claude: directive present" in r.stdout and "codex: directive STALE" in r.stdout, r.stdout
        assert r.returncode == 1


def test_piped_from_stdin() -> None:
    with Case() as c:
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(c.config), "AHRENA_AGENCY_URL": (HERE.parent / "references" / "agency.json").as_uri()}
        r = subprocess.run([sys.executable, "-", str(c.root)], input=SCRIPT.read_text(encoding="utf-8"), capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        assert settings(c.root)["enabledPlugins"]["ahrena-foundation@ahrena"] is True
        assert (c.root / "CLAUDE.md").exists() and (c.root / "AGENTS.md").exists()


def test_preserves_other_keys_and_order() -> None:
    with Case() as c:
        put(
            c.root / ".claude" / "settings.json",
            '{"env": {"A": "1"}, "enabledPlugins": {"other@x": true}, "permissions": {"allow": ["Bash"]},'
            ' "extraKnownMarketplaces": {"mine": {"source": {"source": "github", "repo": "me/mine"}}}}',
        )
        r = c.run()
        data = settings(c.root)
        assert r.returncode == 0, "preserve: exit 0" + ": " + str(r.stderr)
        assert list(data) == ["env", "enabledPlugins", "permissions", "extraKnownMarketplaces"], "preserve: key order" + ": " + str(str(list(data)))
        assert list(data["enabledPlugins"])[0] == "other@x", "preserve: own entries first"
        assert data["env"] == {"A": "1"} and data["permissions"] == {"allow": ["Bash"]}, "preserve: other values intact"
        assert list(data["extraKnownMarketplaces"]) == ["mine", "ahrena"], "preserve: own marketplace first"


def test_disabled_entry_not_flipped() -> None:
    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {"ahrena-foundation@ahrena": False}})
        r = c.run()
        assert settings(c.root)["enabledPlugins"]["ahrena-foundation@ahrena"] is False, "disabled: still false"
        assert "ahrena-foundation@ahrena is disabled" in r.stdout, "disabled: reported" + ": " + str(r.stdout)
        assert settings(c.root)["enabledPlugins"]["ahrena-contributing@ahrena"] is True, "disabled: the others enabled"


def test_existing_marketplace_untouched() -> None:
    with Case() as c:
        mine = {"source": {"source": "github", "repo": "ahrenatechnology/ahrena-framework", "ref": "main"}}
        put(c.root / ".claude" / "settings.json", {"extraKnownMarketplaces": {"ahrena": mine}})
        r = c.run()
        assert settings(c.root)["extraKnownMarketplaces"]["ahrena"] == mine, "marketplace: kept with its ref"
        assert "already declared differently" in r.stdout, "marketplace: difference reported" + ": " + str(r.stdout)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"extraKnownMarketplaces": {"ahrena": SOURCE}})
        r = c.run()
        assert "differently" not in r.stdout, "marketplace: identical entry not reported" + ": " + str(r.stdout)


def test_second_run_writes_nothing() -> None:
    with Case() as c:
        c.run()
        settings_path = c.root / ".claude" / "settings.json"
        before = (settings_path.read_bytes(), (c.root / "CLAUDE.md").read_bytes() + (c.root / "AGENTS.md").read_bytes(), settings_path.stat().st_mtime_ns)
        r = c.run()
        after = (settings_path.read_bytes(), (c.root / "CLAUDE.md").read_bytes() + (c.root / "AGENTS.md").read_bytes(), settings_path.stat().st_mtime_ns)
        assert r.returncode == 0, "idempotent: exit 0" + ": " + str(r.stderr)
        assert before == after, "idempotent: nothing rewritten"
        assert "nothing written" in r.stdout and "already current" in r.stdout, "idempotent: says so" + ": " + str(r.stdout)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", '{"enabledPlugins":{"x@y":true}}')
        c.run()
        c.run()
        assert settings(c.root)["enabledPlugins"]["x@y"] is True, "idempotent: reformatting not repeated"


def test_unchanged_file_keeps_its_formatting() -> None:
    with Case() as c:
        c.run()
        path = c.root / ".claude" / "settings.json"
        compact = json.dumps(settings(c.root))
        path.write_text(compact, encoding="utf-8")
        c.run()
        assert path.read_text(encoding="utf-8") == compact, "no rewrite when content is complete"


def test_malformed_json() -> None:
    with Case() as c:
        path = c.root / ".claude" / "settings.json"
        put(path, "{ not json")
        r = c.run()
        assert r.returncode == 2, "malformed: exit 2" + ": " + str(r.returncode)
        assert path.read_text(encoding="utf-8") == "{ not json", "malformed: file untouched"
        assert "not valid JSON" in r.stderr, "malformed: reported on stderr" + ": " + str(r.stderr)
        assert not (c.root / "CLAUDE.md").exists(), "malformed: directive not written either"

    with Case() as c:
        put(c.root / ".claude" / "settings.json", "[]")
        r = c.run()
        assert r.returncode == 2, "non-object: exit 2" + ": " + str(r.returncode)

    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": []})
        r = c.run()
        assert r.returncode == 2, "wrong-typed enabledPlugins: exit 2" + ": " + str(r.returncode)


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
            assert extra == [f"{plugin}@ahrena"], f"detect {marker}" + ": " + str(str(extra))

    with Case() as c:
        c.run()
        assert list(settings(c.root)["enabledPlugins"]) == CORE, "detect: none leaves only the core"

    with Case() as c:
        (c.root / "go.mod").write_text("", encoding="utf-8")
        (c.root / "Cargo.toml").write_text("", encoding="utf-8")
        c.run()
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        assert sorted(extra) == ["ahrena-engineering-go@ahrena", "ahrena-engineering-rust@ahrena"], "detect: two languages" + ": " + str(str(extra))


def test_language_flag() -> None:
    with Case() as c:
        (c.root / "pyproject.toml").write_text("", encoding="utf-8")
        c.run("--language", "go")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        assert extra == ["ahrena-engineering-go@ahrena"], "--language replaces detection" + ": " + str(str(extra))

    with Case() as c:
        c.run("--language", "go", "--language", "rust")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        assert extra == ["ahrena-engineering-go@ahrena", "ahrena-engineering-rust@ahrena"], "--language repeatable" + ": " + str(str(extra))

    with Case() as c:
        c.run("--language", "python,typescript")
        extra = [p for p in settings(c.root)["enabledPlugins"] if p not in CORE]
        assert extra == ["ahrena-engineering-python@ahrena", "ahrena-engineering-typescript@ahrena"], "--language comma list" + ": " + str(str(extra))

    with Case() as c:
        r = c.run("--language", "cobol")
        assert r.returncode == 2 and "cobol" in r.stderr, "--language unknown: exit 2" + ": " + str(r.stderr)
        assert not (c.root / ".claude").exists(), "--language unknown: nothing written"


def test_platform_codex_skips_settings() -> None:
    with Case() as c:
        r = c.run("--platform", "codex")
        assert r.returncode == 0, "codex: exit 0" + ": " + str(r.stderr)
        assert not (c.root / ".claude").exists(), "codex: no settings.json"
        assert "ahrena:agency:start" in (c.root / "AGENTS.md").read_text(encoding="utf-8"), "codex: AGENTS.md written"
        assert "max_depth" in r.stdout, "codex: depth note surfaced"


def test_bad_platform_reports_its_own_error() -> None:
    with Case() as c:
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(c.config), "AHRENA_AGENCY_URL": "file:///nonexistent/agency.json"}
        script = SCRIPT.read_text(encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-", "--platform", "cursor", str(c.root)],
            input=script,
            capture_output=True,
            text=True,
            env=env,
        )
        assert r.returncode == 2 and "--platform" in r.stderr and "cursor" in r.stderr, "bad platform: its own error" + ": " + str(r.stderr)
        assert "agency declaration" not in r.stderr, "bad platform: not masked by the load failure"


def test_codex_note_only_when_agents_md_is_targeted() -> None:
    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# Mine\n", encoding="utf-8")
        r = c.run()
        assert "max_depth" not in r.stdout, "claude only: no depth note"

    with Case() as c:
        (c.root / "AGENTS.md").write_text("# a\n", encoding="utf-8")
        (c.root / "CLAUDE.md").write_text("# b\n", encoding="utf-8")
        assert "max_depth" in c.run().stdout, "both files: depth note"
        assert "max_depth" not in c.run("--platform", "claude").stdout, "--platform claude: no depth note"


ONE = "ahrena-foundation@ahrena"
SCOPES = {
    "project": lambda c: c.root / ".claude" / "settings.json",
    "local": lambda c: c.root / ".claude" / "settings.local.json",
    "user": lambda c: c.config / "settings.json",
}


def plugin_line(r: subprocess.CompletedProcess, plugin: str = ONE) -> str:
    return next((l for l in r.stdout.splitlines() if l.startswith(f"plugin: {plugin}")), "")


def core_with(**overrides) -> dict:
    return {
        "extraKnownMarketplaces": {"ahrena": SOURCE},
        "enabledPlugins": {**{p: True for p in CORE}, ONE: overrides["one"]},
    }


def test_check_on_an_empty_repository() -> None:
    with Case() as c:
        r = c.run("--check")
        assert r.returncode == 1, f"exit 1: {r.returncode}"
        assert not (c.root / ".claude").exists() and not (c.root / "CLAUDE.md").exists(), "writes nothing"
        assert sum(l.endswith(" missing") for l in r.stdout.splitlines()) == len(CORE), r.stdout
        assert "ABSENT" in r.stdout, r.stdout


def test_check_on_an_installed_repository() -> None:
    with Case() as c:
        c.run()
        r = c.run("--check")
        assert r.returncode == 0, r.stdout + r.stderr
        assert r.stdout.count(" enabled") == len(CORE), r.stdout


def test_check_counts_each_scope() -> None:
    for label, path_of in SCOPES.items():
        with Case() as c:
            put(path_of(c), {"enabledPlugins": {ONE: True}})
            assert " enabled" in plugin_line(c.run("--check")), label


def test_check_reports_a_disabled_plugin() -> None:
    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {ONE: False}})
        assert " disabled" in plugin_line(c.run("--check"))

    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", core_with(one=False))
        assert c.run("--check").returncode == 1, "disabled and nowhere else"

    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", core_with(one=False))
        put(c.config / "settings.json", {"enabledPlugins": {ONE: True}})
        assert c.run("--check").returncode == 0, "disabled here, enabled at user scope"


def test_check_reports_a_non_boolean_plugin_as_its_own_state() -> None:
    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", core_with(one=["x"]))
        r = c.run("--check")
        assert r.returncode == 1, r.stdout
        assert " invalid" in plugin_line(r) and " missing" not in plugin_line(r), r.stdout
        assert "not true or false" in r.stdout, r.stdout


def test_install_leaves_a_non_boolean_plugin_alone_and_reports_it() -> None:
    with Case() as c:
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {ONE: "yes"}})
        r = c.run()
        assert settings(c.root)["enabledPlugins"][ONE] == "yes", "value kept"
        assert f"{ONE} is present, not boolean; left as is" in r.stdout, r.stdout


def test_check_reports_the_marketplace() -> None:
    with Case() as c:
        c.run()
        assert "marketplace: ahrena declared" in c.run("--check").stdout

    with Case() as c:
        c.run()
        put(c.root / ".claude" / "settings.json", {"enabledPlugins": {p: True for p in CORE}})
        r = c.run("--check")
        assert r.returncode == 1 and "marketplace: ahrena absent" in r.stdout, r.stdout

    with Case() as c:
        c.run()
        other = {"source": {"source": "github", "repo": "me/fork"}}
        data = {**settings(c.root), "extraKnownMarketplaces": {"ahrena": other}}
        put(c.root / ".claude" / "settings.json", data)
        r = c.run("--check")
        assert r.returncode == 0 and "declared differently" in r.stdout, r.stdout


def test_check_fails_on_a_stale_directive() -> None:
    with Case() as c:
        c.run()
        md = c.root / "CLAUDE.md"
        md.write_text(md.read_text(encoding="utf-8").replace("athena", "someone"), encoding="utf-8")
        r = c.run("--check")
        assert r.returncode == 1 and "STALE" in r.stdout, r.stdout


def test_check_expects_the_language_plugin() -> None:
    with Case() as c:
        c.run()
        (c.root / "go.mod").write_text("", encoding="utf-8")
        r = c.run("--check")
        assert r.returncode == 1 and "ahrena-engineering-go@ahrena missing" in r.stdout, r.stdout


def test_check_on_malformed_settings() -> None:
    with Case() as c:
        put(c.root / ".claude" / "settings.json", "{ not json")
        assert c.run("--check").returncode == 2


def test_directive_untouched_around_markers() -> None:
    with Case() as c:
        (c.root / "CLAUDE.md").write_text("# Mine\n\nkeep this\n", encoding="utf-8")
        c.run()
        text = (c.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.startswith("# Mine\n\nkeep this\n"), "directive: surrounding content kept"


def test_declared_plugins_exist_in_marketplace() -> None:
    published = {p["name"] for p in json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]}
    declared = set(AGENCY["plugins"]) | {spec["plugin"] for spec in AGENCY["languages"].values()}
    missing = sorted(declared - published)
    assert not missing, "agency.json: every plugin is in marketplace.json" + ": " + str(f"missing: {missing}")
    assert AGENCY["marketplace"]["name"] == json.loads(MARKETPLACE.read_text(encoding="utf-8"))["name"], "agency.json: marketplace name matches"


def main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            fn()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
        else:
            print(f"ok   {name}")
    print(f"\n{failures} failed" if failures else "\nall passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
