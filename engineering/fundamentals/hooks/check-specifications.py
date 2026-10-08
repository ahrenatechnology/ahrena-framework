#!/usr/bin/env python3
"""Detector for the conditions in engineering/fundamentals/rules/specification-homes.md.

Decides all seven conditions the rule states:

    1. a kind directory sits inside a context, never directly under docs/
    2. a context directory is named in kebab-case
    3. an entity specification is one kebab-case .md file directly in entities/
    4. its heading is one PascalCase word, and the filename is that name
    5. its header declares a classification from the closed set
    6. its header names the context directory it sits in
    7. it carries the seven sections, and no brace placeholder outside code

The subject is a consuming project's tree, not this repository's: the framework
has no bounded context and so no specification, and run here the hook reports
that it has nothing to decide. What backs it is the fixture suite beside it.

Directories are matched by the names a listing returns and never by asking
whether a path exists. On a case-insensitive filesystem `docs/billing/entities`
exists when the directory is spelled `Entities`, and a detector that asked
would read on one platform a tree it ignores on the other.

Standard library only, so a consumer runs the check CI runs with nothing to
install.

Usage:
    python3 engineering/fundamentals/hooks/check-specifications.py [docs-directory]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RULE = "specification-homes"
DEFAULT_DIR = "docs"

# The closed set of kinds. Only the first has conditions on its content; the
# other three are located by conditions 1 and 2 and read no further.
KINDS = ("entities", "contracts", "capabilities", "metrics")
ENTITIES = "entities"

CLASSIFICATIONS = ("aggregate root", "entity", "value object")
REQUIRED_SECTIONS = (
    "why it exists",
    "fields",
    "invariants",
    "business rules",
    "relationships",
    "events",
    "errors",
)

# Not specifications, and not failures: the index a forge renders for a
# directory, and the only way to commit one before its first file exists.
NOT_A_SPECIFICATION = frozenset({"readme.md", ".gitkeep"})

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#\s+(?P<title>.*\S)\s*$")
SECTION = re.compile(r"^##\s+(?P<name>.*\S)\s*$")
HEADER = re.compile(r"^\s*[-*+]\s+\*\*(?P<name>[^*:]+):\*\*\s*(?P<value>.*)$")
CODE_SPAN = re.compile(r"`[^`]*`")
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


@dataclass
class Finding:
    where: str  # path, with :line where a line exists
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


@dataclass
class Specification:
    rel: str
    stem: str
    context: str
    heading: str | None = None
    heading_line: int = 0
    fields: dict = field(default_factory=dict)
    sections: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)
    open_fence: int = 0


def visible_lines(text: str) -> tuple[list[tuple[int, str]], int]:
    """Every line outside a fenced block, numbered from 1, and an unclosed fence.

    A specification quoting a heading or a payload in a block is not making
    one. A fence never closed is different: hiding the rest of the file behind
    it reports sections missing that are plainly there, so nothing is hidden
    and the fence itself is the finding.
    """
    shown: list[tuple[int, str]] = []
    hidden: list[tuple[int, str]] = []
    opened = 0
    for offset, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            opened = 0 if opened else offset
            continue
        (hidden if opened else shown).append((offset, line))
    if opened:
        return sorted(shown + hidden), opened
    return shown, 0


def read_header(spec: Specification, lines: list[tuple[int, str]]) -> None:
    """The heading and the `- **Name:** value` lines above the first section."""
    for number, line in lines:
        if SECTION.match(line):
            return
        heading = HEADING.match(line)
        if heading is not None and spec.heading is None:
            spec.heading, spec.heading_line = heading.group("title"), number
            continue
        header = HEADER.match(line)
        if header is not None:
            spec.fields.setdefault(header.group("name").strip().lower(), (number, header.group("value").strip()))


def read_body(spec: Specification, lines: list[tuple[int, str]]) -> None:
    """The `##` sections, and every line still carrying a brace pair outside a code span."""
    for number, line in lines:
        section = SECTION.match(line)
        if section is not None:
            spec.sections.append(section.group("name").lower())
        if PLACEHOLDER.search(CODE_SPAN.sub("", line)):
            spec.placeholders.append(number)


def parse(path: Path, rel: str, context: str) -> Specification:
    spec = Specification(rel, path.stem, context)
    lines, spec.open_fence = visible_lines(path.read_text(encoding="utf-8-sig"))
    read_header(spec, lines)
    read_body(spec, lines)
    return spec


def check_heading(spec: Specification, name_is_kebab: bool, findings: list[Finding]) -> None:
    """Condition 4. The filename half is skipped when condition 3 already failed the name."""
    if spec.heading is None:
        findings.append(Finding(spec.rel, 4, "no `# ` heading. The heading is the entity's name, as in `# ScheduledTransfer`"))
        return
    where = f"{spec.rel}:{spec.heading_line}"
    if not PASCAL.match(spec.heading):
        findings.append(
            Finding(
                where,
                4,
                f"the heading '{spec.heading}' is not one PascalCase word. It is the entity's "
                "name as the domain says it, with no prefix, as in `# ScheduledTransfer`",
            )
        )
        return
    if name_is_kebab and spec.stem.replace("-", "") != spec.heading.lower():
        findings.append(
            Finding(
                where,
                4,
                f"the heading names '{spec.heading}' and the file is '{spec.stem}.md'. The "
                "filename is the heading in kebab-case, so one of the two is another entity's",
            )
        )


def check_classification(spec: Specification, findings: list[Finding]) -> None:
    """Condition 5."""
    allowed = ", ".join(CLASSIFICATIONS)
    if "classification" not in spec.fields:
        findings.append(
            Finding(spec.rel, 5, f"no `- **Classification:**` line above the first section. It is one of: {allowed}")
        )
        return
    number, value = spec.fields["classification"]
    if value.lower() not in CLASSIFICATIONS:
        findings.append(
            Finding(f"{spec.rel}:{number}", 5, f"the classification '{value}' is not one of: {allowed}")
        )


def check_context(spec: Specification, findings: list[Finding]) -> None:
    """Condition 6."""
    if "context" not in spec.fields:
        findings.append(
            Finding(
                spec.rel,
                6,
                f"no `- **Context:**` line above the first section. This file sits in '{spec.context}'",
            )
        )
        return
    number, value = spec.fields["context"]
    if value != spec.context:
        findings.append(
            Finding(
                f"{spec.rel}:{number}",
                6,
                f"the header names the context '{value}' and the file sits in '{spec.context}'. "
                "A specification moved between contexts is rewritten for the model it joined",
            )
        )


def check_sections(spec: Specification, findings: list[Finding]) -> None:
    """Condition 7: the seven sections, and nothing left in braces."""
    if spec.open_fence:
        findings.append(
            Finding(
                f"{spec.rel}:{spec.open_fence}",
                7,
                "a fenced block is opened here and never closed, so nothing below it can be "
                "told from an example. Close it",
            )
        )
    for name in REQUIRED_SECTIONS:
        if name not in spec.sections:
            findings.append(
                Finding(
                    spec.rel,
                    7,
                    f"no `## {name.capitalize()}` section. A section with nothing to say keeps "
                    "its heading and reads None",
                )
            )
    if spec.placeholders:
        findings.append(
            Finding(
                f"{spec.rel}:{spec.placeholders[0]}",
                7,
                f"{len(spec.placeholders)} line(s) still carry a template placeholder in braces, "
                "the first here. Replace it, or put a literal brace in a code span",
            )
        )


def judge_file(path: Path, rel: str, context: str, findings: list[Finding]) -> bool:
    """Conditions 3 to 7 for one entry of entities/. True when it was a specification."""
    if path.name.lower() in NOT_A_SPECIFICATION:
        return False
    if path.is_dir() or path.suffix != ".md":
        findings.append(
            Finding(
                rel,
                3,
                "an entity specification is one .md file per entity, directly in entities/. "
                "This is not one, and a file a reader cannot address by entity name is not found",
            )
        )
        return False
    name_is_kebab = KEBAB.match(path.stem) is not None
    if not name_is_kebab:
        findings.append(
            Finding(rel, 3, f"'{path.stem}' is not kebab-case. Lowercase, digits and single hyphens, as in scheduled-transfer.md")
        )
    try:
        spec = parse(path, rel, context)
    except UnicodeDecodeError:
        findings.append(Finding(rel, 3, "the file is not UTF-8 text, so none of it can be read"))
        return True
    check_heading(spec, name_is_kebab, findings)
    check_classification(spec, findings)
    check_context(spec, findings)
    check_sections(spec, findings)
    return True


def judge_context(context: Path, kinds: list[Path], root: Path, findings: list[Finding]) -> int:
    """Condition 2 for the context, then every entry of its entities/. Returns the count judged."""
    rel = context.relative_to(root.parent).as_posix()
    if not KEBAB.match(context.name):
        findings.append(
            Finding(
                rel,
                2,
                f"the context '{context.name}' is not kebab-case. It is the bounded context's "
                "name in lowercase, digits and single hyphens, as in scheduled-payments",
            )
        )
    judged = 0
    for kind in kinds:
        if kind.name != ENTITIES:
            continue
        for entry in sorted(kind.iterdir()):
            judged += judge_file(entry, f"{rel}/{ENTITIES}/{entry.name}", context.name, findings)
    return judged


def judge_tree(root: Path, findings: list[Finding]) -> tuple[int, int]:
    """Every directory under the docs root. Returns the contexts and the specifications judged."""
    contexts = 0
    judged = 0
    for child in sorted(entry for entry in root.iterdir() if entry.is_dir()):
        if child.name in KINDS:
            findings.append(
                Finding(
                    child.relative_to(root.parent).as_posix(),
                    1,
                    f"the kind '{child.name}' sits above the contexts. The order is "
                    f"{root.name}/<context>/{child.name}/, so that one context is one directory",
                )
            )
            continue
        kinds = [entry for entry in child.iterdir() if entry.is_dir() and entry.name in KINDS]
        if kinds:
            contexts += 1
            judged += judge_context(child, kinds, root, findings)
    return contexts, judged


def _absent(directory: Path, given: str | None) -> int:
    """A directory that is not there. Silence for the default path, a failure for one given."""
    if given is None:
        print(f"{directory}: no documentation directory here, nothing to decide.")
        return 0
    print(
        f"{directory}: not a directory. A missing one is nothing to decide only at the default "
        f"path, {DEFAULT_DIR}; a path given on the command line and not found is a typo or a "
        "step wired to the wrong directory, and passing would hide it."
    )
    return 1


def main(argv: list[str]) -> int:
    given = argv[1] if len(argv) > 1 else None
    directory = Path(given if given is not None else DEFAULT_DIR)
    if not directory.is_dir():
        return _absent(directory, given)

    findings: list[Finding] = []
    contexts, judged = judge_tree(directory.resolve(), findings)
    for finding in findings:
        print(finding)
    if not contexts and not findings:
        print(f"{directory}: no specifications here, nothing to decide.")
        return 0
    print(f"{judged} entity specification(s) in {contexts} context(s), {len(findings)} failure(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
