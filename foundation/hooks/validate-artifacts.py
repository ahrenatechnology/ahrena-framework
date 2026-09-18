#!/usr/bin/env python3
"""Gate for the Ahrena artifact corpus.

Decides the conditions stated in the three foundation rules:

    foundation/rules/pilars.md       types, authority, references
    foundation/rules/naming.md       names and paths
    foundation/rules/frontmatter.md  required and undeclared fields

Standard library only, on purpose. A consumer who installs the plugin can run
the same gate the repository runs, without installing anything to do it.

Usage:
    python3 foundation/hooks/validate-artifacts.py [repo-root]
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- the model, as the rules state it -------------------------------------

FLAT_DIRS = {"rules": "rule", "docs": "doc", "agents": "agent", "commands": "command"}
SKILLS_DIR = "skills"
TYPES = {"rule", "doc", "skill", "agent", "command"}

ALLOWED_REFS = {
    "rule": {"doc"},
    "doc": {"doc", "rule"},
    "skill": {"rule", "doc", "skill"},
    "agent": {"rule", "doc", "skill", "agent"},
    "command": {"skill", "agent"},
}

REQUIRED = {
    "rule": ("id", "type", "clade", "title", "statement", "enforcement"),
    "doc": ("id", "type", "clade", "title", "summary"),
    "skill": ("name", "description", "type", "clade"),
    "agent": ("name", "description", "type", "clade"),
    "command": ("name", "description", "type", "clade"),
}

# Ours end to end, so the schema is closed.
OPTIONAL = {
    "rule": ("subclade", "references", "enforced-by"),
    "doc": ("subclade", "references"),
}
# skill, agent and command are read by four platforms that add fields on their
# own schedule, so undeclared fields pass there.
CLOSED_SCHEMA = frozenset(OPTIONAL)

IDENTITY_FIELD = {"rule": "id", "doc": "id", "skill": "name", "agent": "name", "command": "name"}

STATEMENT_MAX = 160

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KEY = re.compile(r"^[a-z][a-z0-9-]*$")
MD_LINK = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)")
FENCE = re.compile(r"^\s*(```|~~~)")
SKIP_LINK = ("http://", "https://", "mailto:", "#")


# --- findings --------------------------------------------------------------


@dataclass
class Finding:
    where: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] {self.message}"


# --- frontmatter -----------------------------------------------------------


class FrontmatterError(Exception):
    pass


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict, int]:
    """Parse a flat map of scalars and lists of scalars.

    Returns the map and the line number the body starts on (1-indexed). Anything
    outside that shape raises, which is what frontmatter.md promises.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file does not open with a frontmatter block on line 1")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise FrontmatterError("frontmatter block is never closed")

    data: dict = {}
    current: str | None = None
    for offset, raw in enumerate(lines[1:end]):
        n = offset + 2
        if not raw.strip():
            current = None
            continue
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current is None:
                raise FrontmatterError(f"line {n}: list item with no key above it")
            data[current].append(_unquote(stripped[2:].strip()))
            continue
        if raw[0] in " \t":
            raise FrontmatterError(f"line {n}: indented line that is not a list item; nested maps are not allowed")
        if ":" not in raw:
            raise FrontmatterError(f"line {n}: not a 'key: value' pair")
        key, _, value = raw.partition(":")
        key, value = key.strip(), value.strip()
        if not KEY.match(key):
            raise FrontmatterError(f"line {n}: '{key}' is not a valid field name")
        if key in data:
            raise FrontmatterError(f"line {n}: '{key}' is declared twice")
        if value == "":
            data[key] = []
            current = key
        else:
            if value[0] in "[{|>&*":
                raise FrontmatterError(f"line {n}: inline collections and block scalars are not allowed")
            data[key] = _unquote(value)
            current = None
    return data, end + 2


# --- artifacts -------------------------------------------------------------


@dataclass
class Artifact:
    path: Path  # absolute
    rel: str  # plugin-relative, posix
    plugin: Path
    kind: str  # derived from location
    name: str  # derived from location
    data: dict = field(default_factory=dict)
    body_start: int = 1
    body: str = ""


def collect(plugin: Path, findings: list[Finding]) -> list[Artifact]:
    artifacts: list[Artifact] = []

    for dirname, kind in FLAT_DIRS.items():
        directory = plugin / dirname
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            rel = path.relative_to(plugin).as_posix()
            if path.parent != directory:
                findings.append(
                    Finding(rel, "naming", f"{dirname}/ is flat; this file sits in a subdirectory")
                )
                continue
            artifacts.append(Artifact(path, rel, plugin, kind, path.stem))

    skills = plugin / SKILLS_DIR
    if skills.is_dir():
        for path in sorted(skills.rglob("SKILL.md")):
            rel = path.relative_to(plugin).as_posix()
            parts = path.relative_to(skills).parts
            if len(parts) != 2:
                findings.append(
                    Finding(
                        rel,
                        "naming",
                        "skills/ is exactly one level deep; a nested skill is invisible to DeepSeek",
                    )
                )
                continue
            artifacts.append(Artifact(path, rel, plugin, "skill", parts[0]))
        for path in sorted(skills.glob("*.md")):
            findings.append(
                Finding(
                    path.relative_to(plugin).as_posix(),
                    "naming",
                    "a skill is skills/<name>/SKILL.md, never a flat file",
                )
            )

    return artifacts


def read(artifact: Artifact, findings: list[Finding]) -> bool:
    try:
        text = artifact.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(Finding(artifact.rel, "frontmatter", f"cannot read the file: {exc}"))
        return False
    try:
        artifact.data, artifact.body_start = parse_frontmatter(text)
    except FrontmatterError as exc:
        findings.append(Finding(artifact.rel, "frontmatter", str(exc)))
        return False
    artifact.body = "\n".join(text.splitlines()[artifact.body_start - 1 :])
    return True


# --- the checks ------------------------------------------------------------


def check_fields(a: Artifact, findings: list[Finding]) -> None:
    for name in REQUIRED[a.kind]:
        value = a.data.get(name)
        if value is None:
            findings.append(Finding(a.rel, "frontmatter", f"required field '{name}' is missing"))
        elif not (value if isinstance(value, str) else "".join(value)).strip():
            findings.append(Finding(a.rel, "frontmatter", f"required field '{name}' is empty"))

    if a.kind in CLOSED_SCHEMA:
        declared = set(REQUIRED[a.kind]) | set(OPTIONAL[a.kind])
        for name in sorted(set(a.data) - declared):
            findings.append(
                Finding(
                    a.rel,
                    "frontmatter",
                    f"'{name}' is not a declared field for a {a.kind}; the schema is closed",
                )
            )


def check_type(a: Artifact, findings: list[Finding]) -> None:
    declared = a.data.get("type")
    if not isinstance(declared, str):
        return  # already reported as missing
    if declared not in TYPES:
        findings.append(Finding(a.rel, "pilars", f"'{declared}' is not one of the five types"))
    elif declared != a.kind:
        findings.append(
            Finding(a.rel, "pilars", f"declares type '{declared}' but sits in a {a.kind} directory")
        )


def check_statement(a: Artifact, findings: list[Finding]) -> None:
    if a.kind != "rule":
        return
    statement = a.data.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        return  # already reported
    if len(statement) > STATEMENT_MAX:
        findings.append(
            Finding(
                a.rel,
                "frontmatter",
                f"statement is {len(statement)} characters; the limit is {STATEMENT_MAX}, "
                "and the overflow is rationale that belongs in a doc",
            )
        )


def check_enforcement(a: Artifact, findings: list[Finding]) -> None:
    if a.kind != "rule":
        return
    enforcement = a.data.get("enforcement")
    enforced_by = a.data.get("enforced-by")
    if enforcement not in ("hook", "judgment"):
        if isinstance(enforcement, str) and enforcement.strip():
            findings.append(
                Finding(a.rel, "frontmatter", f"enforcement is '{enforcement}'; it is 'hook' or 'judgment'")
            )
        return
    if enforcement == "hook":
        if not isinstance(enforced_by, str) or not enforced_by.strip():
            findings.append(
                Finding(a.rel, "frontmatter", "enforcement is 'hook' but enforced-by names no file")
            )
        elif not (a.plugin / enforced_by).is_file():
            findings.append(
                Finding(a.rel, "pilars", f"enforced-by points at '{enforced_by}', which does not exist")
            )
    elif enforced_by is not None:
        findings.append(
            Finding(a.rel, "frontmatter", "enforcement is 'judgment', so enforced-by is not allowed")
        )


def check_naming(a: Artifact, findings: list[Finding]) -> None:
    if not KEBAB.match(a.name):
        findings.append(Finding(a.rel, "naming", f"'{a.name}' is not kebab-case"))

    if a.name == a.kind or a.name.startswith(f"{a.kind}-"):
        findings.append(Finding(a.rel, "naming", f"'{a.name}' repeats its type; the directory already says it"))

    clade = a.data.get("clade")
    if isinstance(clade, str) and clade and (a.name == clade or a.name.startswith(f"{clade}-")):
        findings.append(Finding(a.rel, "naming", f"'{a.name}' repeats its clade; the plugin already says it"))

    if a.kind == "skill" and not a.name.split("-")[0].endswith("ing"):
        findings.append(
            Finding(a.rel, "naming", f"'{a.name}' is not in the gerund; a skill is named for the activity")
        )

    identity = IDENTITY_FIELD[a.kind]
    declared = a.data.get(identity)
    if isinstance(declared, str) and declared and declared != a.name:
        on_disk = "directory" if a.kind == "skill" else "filename"
        findings.append(
            Finding(a.rel, "naming", f"{identity} is '{declared}' but the {on_disk} says '{a.name}'")
        )


def check_references(a: Artifact, index: dict[str, str], findings: list[Finding]) -> None:
    refs = a.data.get("references", [])
    if isinstance(refs, str):
        findings.append(Finding(a.rel, "frontmatter", "references is a list, even with one entry"))
        return
    for ref in refs:
        if ref.startswith("/") or ".." in Path(ref).parts:
            findings.append(
                Finding(a.rel, "pilars", f"reference '{ref}' escapes the plugin; references are plugin-relative")
            )
            continue
        target = index.get(ref)
        if target is None:
            exists = (a.plugin / ref).exists()
            findings.append(
                Finding(
                    a.rel,
                    "pilars",
                    f"reference '{ref}' is not an artifact" if exists else f"reference '{ref}' does not exist",
                )
            )
            continue
        if target not in ALLOWED_REFS[a.kind]:
            findings.append(
                Finding(a.rel, "pilars", f"a {a.kind} may not reference a {target} ('{ref}')")
            )


def check_links(a: Artifact, findings: list[Finding]) -> None:
    in_fence = False
    for offset, line in enumerate(a.body.splitlines()):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for href in MD_LINK.findall(line):
            if href.startswith(SKIP_LINK):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            if not (a.path.parent / target).exists():
                n = a.body_start + offset
                findings.append(
                    Finding(f"{a.rel}:{n}", "pilars", f"link target '{target}' does not exist")
                )


# --- entry point -----------------------------------------------------------


def find_root(argv: list[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).resolve()
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / ".claude-plugin" / "marketplace.json").is_file():
            return candidate
    raise SystemExit("cannot locate the repository root: no .claude-plugin/marketplace.json found")


def plugin_paths(root: Path) -> list[Path]:
    manifest = root / ".claude-plugin" / "marketplace.json"
    catalog = json.loads(manifest.read_text(encoding="utf-8"))
    paths = []
    for entry in catalog.get("plugins", []):
        subdir = entry.get("source", {}).get("path")
        if not subdir:
            raise SystemExit(f"plugin '{entry.get('name')}' declares no source.path in the marketplace")
        path = root / subdir
        if not path.is_dir():
            raise SystemExit(f"plugin '{entry.get('name')}' points at '{subdir}', which is not a directory")
        paths.append(path)
    return paths


def main(argv: list[str]) -> int:
    root = find_root(argv)
    findings: list[Finding] = []
    checked = 0

    for plugin in plugin_paths(root):
        artifacts = [a for a in collect(plugin, findings) if read(a, findings)]
        index = {a.rel: a.kind for a in artifacts}
        for a in artifacts:
            check_fields(a, findings)
            check_type(a, findings)
            check_statement(a, findings)
            check_enforcement(a, findings)
            check_naming(a, findings)
            check_references(a, index, findings)
            check_links(a, findings)
        checked += len(artifacts)

    if findings:
        print(f"{len(findings)} failure(s) across {checked} artifact(s):\n")
        for finding in findings:
            print(finding)
        return 1

    print(f"{checked} artifact(s), no failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
