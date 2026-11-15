#!/usr/bin/env python3
"""Check a skill folder against Anthropic's Agent Skills format.

Decides the conditions a script can decide: the frontmatter holds only fields
Anthropic documents, `name` and `description` stay inside their documented
limits, the body stays under 500 lines and every relative link resolves inside
the folder. Whether the description says what the skill does and when to use
it is left to review (foundation/skills/reviewing-artifacts).

Every limit is cited in foundation/docs/anthropic-skill-format.md.

Usage:
    python3 foundation/hooks/validate-anthropic-skill.py [--profile portable|claude-code] <skill-dir>...

Profiles:
    portable     the six fields every Agent Skills surface accepts (default).
                 claude.ai uploads and the Skills API reject any other field.
    claude-code  the portable fields plus those only Claude Code reads.

Exit status is 0 when every folder passes, 1 when one fails, 2 on a usage error. Standard library only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PORTABLE_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_CODE_FIELDS = PORTABLE_FIELDS | {
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "background",
    "hooks",
    "paths",
    "shell",
}
PROFILES = {"portable": PORTABLE_FIELDS, "claude-code": CLAUDE_CODE_FIELDS}

NAME_MAX = 64
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500
BODY_MAX_LINES = 500
RESERVED_WORDS = ("anthropic", "claude")
NAME_SHAPE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
XML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
FIRST_PERSON = re.compile(r"^(I|I'm|I'll|We|My|You|Your)\b")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str] | None, int]:
    """Top-level keys with their value, or None when there is no block.

    A key with an empty inline value keeps the indented lines under it as its
    value, which is how `metadata` and a list-valued `allowed-tools` arrive.
    The second item is the number of lines the block takes, closing fence
    included.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0
    data: dict[str, str] = {}
    current: str | None = None
    for index, raw in enumerate(lines[1:], start=1):
        if raw.strip() == "---":
            return {k: re.sub(r"^[>|][+-]?\s*", "", v) for k, v in data.items()}, index + 1
        match = KEY.match(raw) if not raw.startswith((" ", "\t", "-")) else None
        if match:
            current = match.group(1)
            data[current] = unquote(match.group(2))
        elif current is not None and raw.strip():
            data[current] = (data[current] + "\n" + raw.strip()).strip()
    return None, 0


def check_name(folder: Path, data: dict[str, str]) -> list[str]:
    if "name" not in data:
        return ["name: required and missing"]
    name = data["name"]
    if not name:
        return ["name: required and empty"]
    problems = []
    if len(name) > NAME_MAX:
        problems.append(f"name: {len(name)} characters, the limit is {NAME_MAX}")
    if XML_TAG.search(name):
        problems.append("name: contains an XML tag")
    if not NAME_SHAPE.match(name):
        problems.append(
            "name: only lowercase letters, numbers and single hyphens, none at either end "
            f"(got {name!r})"
        )
    for word in RESERVED_WORDS:
        if word in name:
            problems.append(f"name: contains the reserved word {word!r}")
    if name != folder.name:
        problems.append(f"name: {name!r} does not match the directory {folder.name!r}")
    return problems


def check_description(data: dict[str, str]) -> list[str]:
    if "description" not in data:
        return ["description: required and missing"]
    description = data["description"]
    if not description:
        return ["description: required and empty"]
    problems = []
    if len(description) > DESCRIPTION_MAX:
        problems.append(f"description: {len(description)} characters, the limit is {DESCRIPTION_MAX}")
    if XML_TAG.search(description):
        problems.append("description: contains an XML tag")
    if FIRST_PERSON.match(description):
        problems.append("description: written in first or second person; write it in the third person")
    return problems


def check_optional(data: dict[str, str]) -> list[str]:
    problems = []
    compatibility = data.get("compatibility")
    if compatibility is not None and not 1 <= len(compatibility) <= COMPATIBILITY_MAX:
        problems.append(f"compatibility: {len(compatibility)} characters, the limit is {COMPATIBILITY_MAX}")
    return problems


def check_fields(data: dict[str, str], profile: str) -> list[str]:
    allowed = PROFILES[profile]
    return [
        f"{key}: undeclared field for the {profile} profile (Anthropic documents {', '.join(sorted(allowed))})"
        for key in data
        if key not in allowed
    ]


def check_body(folder: Path, body: list[str]) -> list[str]:
    problems = []
    if len(body) > BODY_MAX_LINES:
        problems.append(f"body: {len(body)} lines, keep it under {BODY_MAX_LINES} lines and move detail to references/")
    in_fence = False
    for line in body:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(line):
            if re.match(r"^([a-z][a-z0-9+.-]*:|#)", target):
                continue
            path = target.split("#", 1)[0]
            if "\\" in path:
                problems.append(f"link {target}: backslash in a path, use forward slashes")
                continue
            resolved = (folder / path).resolve()
            if folder.resolve() not in (resolved, *resolved.parents):
                problems.append(f"link {target}: points outside the skill folder")
            elif not resolved.exists():
                problems.append(f"link {target}: no such file in the skill folder")
    return problems


def check_skill(folder: Path, profile: str) -> list[str]:
    skill_file = folder / "SKILL.md"
    if not skill_file.is_file():
        return ["SKILL.md: missing"]
    text = skill_file.read_text(encoding="utf-8")
    data, consumed = parse_frontmatter(text)
    if data is None:
        return ["SKILL.md: no frontmatter block opened by --- on line 1 and closed by ---"]
    body = text.splitlines()[consumed:]
    return (
        check_fields(data, profile)
        + check_name(folder, data)
        + check_description(data)
        + check_optional(data)
        + check_body(folder, body)
    )


def main(argv: list[str]) -> int:
    args = argv[1:]
    profile = "portable"
    if args[:1] == ["--profile"]:
        if len(args) < 2 or args[1] not in PROFILES:
            print(f"--profile takes one of: {', '.join(PROFILES)}", file=sys.stderr)
            return 2
        profile = args[1]
        args = args[2:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2

    failed = 0
    for arg in args:
        folder = Path(arg)
        problems = check_skill(folder, profile)
        for problem in problems:
            print(f"{folder}: {problem}")
        failed += bool(problems)
    if failed:
        print(f"\n{failed} of {len(args)} skill(s) fail the {profile} profile.")
        return 1
    print(f"{len(args)} skill(s), no failures ({profile} profile).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
