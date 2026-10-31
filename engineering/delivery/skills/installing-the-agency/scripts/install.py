#!/usr/bin/env python3
"""Install the agency: enable its plugins in settings.json, write the directive.

Two things make build work enter through the `athena` agent, and this script
does both, idempotently:

1. It merges the declared agency set (`references/agency.json`) into the
   project's `.claude/settings.json`: the `ahrena` marketplace under
   `extraKnownMarketplaces` and `<plugin>@ahrena: true` under `enabledPlugins`,
   for the core plugins plus the language plugins the repository uses.
2. It writes the entry directive between clear markers into the platform's
   always-loaded instruction file, `CLAUDE.md` for Claude Code and `AGENTS.md`
   for Codex, replacing only what sits between them.

The settings merge is declarative on purpose and is NOT `claude plugin
marketplace add`. That command rewrites a marketplace entry the user already
has: it turned a user's own `ahrena` marketplace from `@main` into no ref. This
script only adds what is missing, preserves every other key and its order,
never flips an entry the user set to false, and never overwrites an `ahrena`
marketplace entry that exists, reporting it when it differs. The file is
rewritten only when its content changed.

It mirrors the code-graph doctor's discipline: standard library only, so a
consumer runs it with nothing installed; ensure-or-report, never clobber; and a
report is a valid outcome. It is NOT run by the gate, because it changes a
consumer's own files, which no corpus check should do.

Usage:
    python3 install.py [--check] [--platform claude|codex]
                       [--language python|typescript|go|rust[,...]] [root]

With no flags it writes. `--check` writes nothing: it reports the directive
state per file and each plugin as enabled, missing or disabled, counting the
project's `.claude/settings.json`, its `.claude/settings.local.json` and the
user's `settings.json` under `$CLAUDE_CONFIG_DIR` or `~/.claude`. It exits 0
when everything is in place and 1 when anything is missing, or disabled and
enabled nowhere else. Malformed settings JSON is an error, exit 2, and the
file is never touched. `root` defaults to the current directory, the consuming
repository's root. `--language` is repeatable or a comma list and replaces the
detection from the marker files. With no `--platform` the directive goes into
every instruction file present, and into both when neither exists; `--platform`
limits the run to one. `--platform codex` skips settings.json, which
Codex does not read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

START = "<!-- ahrena:agency:start -->"
END = "<!-- ahrena:agency:end -->"

AGENCY_FILE = ("references", "agency.json")
AGENCY_URL = (
    "https://raw.githubusercontent.com/ahrenatechnology/ahrena-framework/main/"
    "engineering/delivery/skills/installing-the-agency/references/agency.json"
)

TARGET = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}

DIRECTIVE = """## Build work enters through the agency

Build work enters through the `athena` agent. She plans the issue, routes the
concern, and delegates each layer to `iris` (frontend), `apollo` (backend) or
`clio` (data), running the develop→Argos loop (at most three rounds) before each
stacked pull request. Do not implement build work directly — delegate to the
agency. Athena orchestrates; she does not write production code, pass a review
verdict, or apply a fix."""

CODEX_NOTE = (
    "codex: the binding flattens to stay within agents.max_depth=1 — Athena spawns the\n"
    "       build agents directly and they do not sub-spawn. For a deeper tree, set\n"
    "       agents.max_depth = 2 in Codex's config (max_threads defaults to 6)."
)


class SettingsError(Exception):
    """A settings file that cannot be read as the object this script merges into."""


def load_agency() -> dict:
    """The declared set: the file beside this script, else the one on trunk.

    Piped from curl, `python3 -` has no `__file__` and no `references/` beside
    it, so the declaration is fetched from the same trunk the script came from.
    `AHRENA_AGENCY_URL` replaces that address, which is how a test serves it.
    """
    here = globals().get("__file__")
    if here:
        path = Path(here).resolve().parent.parent.joinpath(*AGENCY_FILE)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    url = os.environ.get("AHRENA_AGENCY_URL", AGENCY_URL)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def block() -> str:
    """The full marker-delimited block, as it is written and compared."""
    return f"{START}\n{DIRECTIVE}\n{END}"


def detect_platforms(root: Path, given: str | None) -> tuple[list[str], str | None]:
    """The platforms to install for, as (platforms, error).

    `--platform` limits the run to one. Otherwise every instruction file that is
    present is written, and when neither is, both are created.
    """
    if given is not None:
        if given not in TARGET:
            return [], f"--platform is 'claude' or 'codex', not '{given}'"
        return [given], None
    present = [name for name, filename in TARGET.items() if (root / filename).is_file()]
    return present or list(TARGET), None


def current_block(text: str) -> str | None:
    """The exact text between the markers, or None when they are not both present."""
    start = text.find(START)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start : end + len(END)]


def splice(text: str) -> str:
    """`text` with the marker region replaced by the current block, or appended.

    Everything outside the markers is preserved exactly; nothing else moves.
    """
    start = text.find(START)
    end = text.find(END)
    if start != -1 and end != -1 and end >= start:
        return text[:start] + block() + text[end + len(END) :]
    if not text.strip():
        return block() + "\n"
    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block() + "\n"


def check_directive(path: Path, platform: str) -> bool:
    """Report the directive's state in `path`; True when present and current."""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    found = current_block(text)
    if found is None:
        print(f"{platform}: directive ABSENT from {path.name}; run install.py to write it")
        return False
    if found == block():
        print(f"{platform}: directive present and current in {path.name}")
        return True
    print(f"{platform}: directive STALE in {path.name}; run install.py to refresh it")
    return False


def write_directive(path: Path, platform: str) -> None:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    updated = splice(text)
    if updated == text:
        print(f"{platform}: directive already current in {path.name}; nothing written")
        return
    path.write_text(updated, encoding="utf-8")
    verb = "refreshed" if current_block(text) is not None else "wrote"
    print(f"{platform}: {verb} the directive in {path.name}")


def detect_languages(root: Path, agency: dict) -> list[str]:
    """The languages whose marker file sits at the repository root, in map order."""
    return [
        name
        for name, spec in agency["languages"].items()
        if any((root / marker).is_file() for marker in spec["markers"])
    ]


def parse_languages(values: list[str], agency: dict) -> tuple[list[str], str | None]:
    """`--language` values, repeatable or comma lists, as (languages, error)."""
    names = [part.strip() for value in values for part in value.split(",") if part.strip()]
    unknown = [n for n in names if n not in agency["languages"]]
    if unknown:
        known = ", ".join(agency["languages"])
        return [], f"--language is one of {known}, not '{unknown[0]}'"
    return list(dict.fromkeys(names)), None


def wanted_plugins(agency: dict, languages: list[str]) -> list[str]:
    """The plugin ids to enable: the core set, then each language plugin."""
    marketplace = agency["marketplace"]["name"]
    names = list(agency["plugins"]) + [agency["languages"][lang]["plugin"] for lang in languages]
    return [f"{name}@{marketplace}" for name in names]


def read_settings(path: Path) -> dict | None:
    """The parsed settings object, None when the file is absent.

    Raises SettingsError for a file that is not valid JSON or not an object, so
    the caller can report it and leave the file as it found it.
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SettingsError(f"{path}: not valid JSON ({exc}); left untouched") from exc
    if not isinstance(data, dict):
        raise SettingsError(f"{path}: top level is not a JSON object; left untouched")
    return data


def merge_settings(data: dict, agency: dict, plugins: list[str]) -> tuple[dict, list[str]]:
    """`data` with the marketplace and plugins added, and the report lines.

    Additive only. Existing keys keep their value and their position; new keys
    land at the end of their object. An entry set to false is reported, never
    flipped. An existing `ahrena` marketplace is never overwritten.
    """
    merged = json.loads(json.dumps(data))
    notes: list[str] = []
    name = agency["marketplace"]["name"]
    entry = {"source": agency["marketplace"]["source"]}

    markets = merged.setdefault("extraKnownMarketplaces", {})
    if not isinstance(markets, dict):
        raise SettingsError("extraKnownMarketplaces is not an object; left untouched")
    if name not in markets:
        markets[name] = entry
        notes.append(f"added marketplace {name}")
    elif markets[name] != entry:
        notes.append(f"marketplace {name} is already declared differently; left untouched")

    enabled = merged.setdefault("enabledPlugins", {})
    if not isinstance(enabled, dict):
        raise SettingsError("enabledPlugins is not an object; left untouched")
    for plugin in plugins:
        if plugin not in enabled:
            enabled[plugin] = True
            notes.append(f"enabled {plugin}")
        elif enabled[plugin] is False:
            notes.append(f"{plugin} is disabled; left as is")
        elif enabled[plugin] is not True:
            notes.append(f"{plugin} is present, not boolean; left as is")
    return merged, notes


def render_settings(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_settings(root: Path, agency: dict, plugins: list[str]) -> None:
    path = root / ".claude" / "settings.json"
    shown = f".claude/{path.name}"
    data = read_settings(path)
    merged, notes = merge_settings(data if data is not None else {}, agency, plugins)
    changed = data is None or merged != data
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_settings(merged), encoding="utf-8")
    for note in notes:
        print(f"settings: {note}")
    if changed:
        print(f"settings: wrote {shown}")
    else:
        print(f"settings: already current in {shown}; nothing written")


def settings_files(root: Path) -> list[Path]:
    """The three files whose `enabledPlugins` Claude Code layers, project first."""
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return [
        root / ".claude" / "settings.json",
        root / ".claude" / "settings.local.json",
        config / "settings.json",
    ]


def plugin_states(root: Path, plugins: list[str]) -> dict[str, tuple[str, list[str]]]:
    """Each plugin as (state, scopes): enabled, disabled, invalid or missing.

    Enabled in any file wins. Otherwise a disabled entry, then a non-boolean
    one, which is its own state rather than a missing plugin.
    """
    layers = {path: (read_settings(path) or {}).get("enabledPlugins", {}) for path in settings_files(root)}
    states: dict[str, tuple[str, list[str]]] = {}
    for plugin in plugins:
        found = {p: e[plugin] for p, e in layers.items() if isinstance(e, dict) and plugin in e}
        on = [str(p) for p, v in found.items() if v is True]
        off = [str(p) for p, v in found.items() if v is False]
        odd = [str(p) for p, v in found.items() if v is not True and v is not False]
        for state, scopes in (("enabled", on), ("disabled", off), ("invalid", odd)):
            if scopes:
                states[plugin] = (state, scopes)
                break
        else:
            states[plugin] = ("missing", [])
    return states


def marketplace_state(root: Path, agency: dict) -> str:
    """The marketplace in the project's settings: declared, absent or differs."""
    data = read_settings(root / ".claude" / "settings.json") or {}
    markets = data.get("extraKnownMarketplaces")
    name = agency["marketplace"]["name"]
    if not isinstance(markets, dict) or name not in markets:
        return "absent"
    return "declared" if markets[name] == {"source": agency["marketplace"]["source"]} else "differs"


def check_marketplace(root: Path, agency: dict) -> bool:
    """Report the marketplace declaration; only an absent one fails the check."""
    state = marketplace_state(root, agency)
    name = agency["marketplace"]["name"]
    wording = {
        "declared": f"marketplace: {name} declared in .claude/settings.json",
        "absent": f"marketplace: {name} absent from .claude/settings.json; run install.py to declare it",
        "differs": f"marketplace: {name} declared differently in .claude/settings.json; left as is",
    }
    print(wording[state])
    return state != "absent"


def check_plugins(root: Path, plugins: list[str]) -> bool:
    """Report every plugin's state; True when all are enabled somewhere."""
    ok = True
    hints = {
        "missing": "run install.py to enable the missing ones",
        "disabled": "a disabled plugin is the owner's to enable",
        "invalid": "an enabledPlugins value that is not true or false is the owner's to fix",
    }
    seen = set()
    for plugin, (state, scopes) in plugin_states(root, plugins).items():
        where = f" ({scopes[0]})" if scopes else ""
        print(f"plugin: {plugin} {state}{where}")
        if state != "enabled":
            ok = False
            seen.add(state)
    for state in hints:
        if state in seen:
            print(f"plugin: {hints[state]}")
    return ok


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Install the agency: enable its plugins and write the entry directive.",
    )
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    parser.add_argument("--platform", help="claude or codex; default is every instruction file present, else both")
    parser.add_argument(
        "--language",
        action="append",
        default=[],
        help="python, typescript, go or rust; repeatable or a comma list; replaces detection",
    )
    parser.add_argument("root", nargs="?", help="the repository root; default is the current directory")
    return parser


def resolve_languages(args: argparse.Namespace, root: Path, agency: dict) -> tuple[list[str], str | None]:
    if args.language:
        return parse_languages(args.language, agency)
    return detect_languages(root, agency), None


def preread_settings(root: Path, check: bool) -> None:
    """Parse the settings files first, so a malformed one stops the whole run."""
    for path in settings_files(root) if check else settings_files(root)[:1]:
        read_settings(path)


def note_codex(platform: str) -> None:
    if platform == "codex":
        print(CODEX_NOTE)


def check_agency(root: Path, platforms: list[str], plugins: list[str], agency: dict) -> bool:
    ok = True
    if "claude" in platforms:
        preread_settings(root, check=True)
        ok = check_marketplace(root, agency)
        ok = check_plugins(root, plugins) and ok
    for platform in platforms:
        ok = check_directive(root / TARGET[platform], platform) and ok
        note_codex(platform)
    return ok


def write_agency(root: Path, platforms: list[str], plugins: list[str], agency: dict) -> bool:
    if "claude" in platforms:
        preread_settings(root, check=False)
        write_settings(root, agency, plugins)
    for platform in platforms:
        write_directive(root / TARGET[platform], platform)
        note_codex(platform)
    return True


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    root = Path(args.root).resolve() if args.root else Path.cwd()
    if not root.is_dir():
        print(f"{root}: not a directory", file=sys.stderr)
        return 2
    platforms, error = detect_platforms(root, args.platform)
    if error is not None:
        print(error, file=sys.stderr)
        return 2
    try:
        agency = load_agency()
    except (OSError, ValueError) as exc:
        print(f"cannot read the agency declaration: {exc}", file=sys.stderr)
        return 2
    languages, error = resolve_languages(args, root, agency)
    if error is not None:
        print(error, file=sys.stderr)
        return 2
    try:
        print(f"languages: {', '.join(languages) if languages else 'none detected'}")
        run = check_agency if args.check else write_agency
        ok = run(root, platforms, wanted_plugins(agency, languages), agency)
    except SettingsError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
