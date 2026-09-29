#!/usr/bin/env python3
"""Render each default issue form into the reference an agent reads.

The forms in ../references/issue-forms/*.yml are the single source. Each is
rendered to ../references/<form>.md: the sections in the order the form asks
for them, with the form's own descriptions and examples as the guidance. An
issue written from the reference therefore has the same `### <label>` sections
GitHub produces when a person fills the form in.

Usage:
    python3 render_issue_forms.py           write the references
    python3 render_issue_forms.py --check   fail if any reference is stale

Standard library only. Issue forms use a small part of YAML, so the reader
below handles that part and nothing else: mappings, lists, plain and quoted
scalars, `#` comments, and `|` block scalars.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMS = HERE.parent / "references" / "issue-forms"
OUT = HERE.parent / "references"
SKIP = frozenset({"config.yml"})


# --- a reader for the subset of YAML issue forms use


def unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def meaningful(lines: list[str]) -> list[tuple[int, str]]:
    """Each line with its indentation; a blank line has none.

    Comment lines are kept, because inside a `|` block a line starting with `#`
    is content. The structural parsers skip them with `is_gap`.
    """
    return [((len(raw) - len(raw.lstrip(" "))) if raw.strip() else -1, raw.rstrip("\n")) for raw in lines]


def is_gap(line: tuple[int, str]) -> bool:
    """A blank line or a comment, which carries no structure."""
    return line[0] == -1 or line[1].lstrip().startswith("#")


def block_scalar(lines: list[tuple[int, str]], start: int, parent: int) -> tuple[str, int]:
    """The literal text of a `|` scalar, and the index after it."""
    body: list[str] = []
    indent = None
    index = start
    while index < len(lines):
        depth, text = lines[index]
        if depth != -1 and depth <= parent:
            break
        if depth != -1 and indent is None:
            indent = depth
        body.append("" if depth == -1 else text[indent:])
        index += 1
    while body and body[-1] == "":
        body.pop()
    return "\n".join(body) + "\n", index


def parse_value(lines: list[tuple[int, str]], index: int, depth: int, rest: str) -> tuple[object, int]:
    if rest == "|":
        return block_scalar(lines, index, depth)
    if rest:
        return unquote(rest), index
    child = next((line[0] for line in lines[index:] if not is_gap(line)), -1)
    if child <= depth:
        return "", index
    return parse_node(lines, index, child)


def parse_mapping(lines: list[tuple[int, str]], index: int, depth: int) -> tuple[dict, int]:
    node: dict = {}
    while index < len(lines):
        current, text = lines[index]
        if is_gap(lines[index]):
            index += 1
            continue
        if current != depth or text.lstrip().startswith("- "):
            break
        key, _, rest = text.strip().partition(":")
        node[key.strip()], index = parse_value(lines, index + 1, depth, rest.strip())
    return node, index


def parse_list(lines: list[tuple[int, str]], index: int, depth: int) -> tuple[list, int]:
    items: list = []
    while index < len(lines):
        current, text = lines[index]
        if is_gap(lines[index]):
            index += 1
            continue
        if current != depth or not text.lstrip().startswith("- "):
            break
        inner = text.lstrip()[2:]
        if ":" not in inner or inner.startswith(("'", '"')):
            items.append(unquote(inner))
            index += 1
            continue
        lines[index] = (depth + 2, " " * (depth + 2) + inner)
        item, index = parse_mapping(lines, index, depth + 2)
        items.append(item)
    return items, index


def parse_node(lines: list[tuple[int, str]], index: int, depth: int) -> tuple[object, int]:
    if lines[index][1].lstrip().startswith("- "):
        return parse_list(lines, index, depth)
    return parse_mapping(lines, index, depth)


def load(path: Path) -> dict:
    lines = meaningful(path.read_text(encoding="utf-8").splitlines())
    while lines and is_gap(lines[0]):
        lines.pop(0)
    node, _ = parse_mapping(lines, 0, 0)
    return node


# --- rendering


def quoted(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.rstrip("\n").splitlines())


def field_lines(field: dict) -> list[str]:
    attributes = field.get("attributes") or {}
    required = (field.get("validations") or {}).get("required") == "true"
    lines = [f"### {attributes.get('label', field.get('id', ''))}", ""]
    if attributes.get("description"):
        lines += [attributes["description"], ""]
    if attributes.get("options"):
        lines += ["One of:", ""] + [f"- {option}" for option in attributes["options"]] + [""]
    if attributes.get("value"):
        lines += ["Starts as:", "", "```markdown", attributes["value"].rstrip("\n"), "```", ""]
    if attributes.get("placeholder"):
        lines += ["For example:", "", quoted(attributes["placeholder"]), ""]
    lines += ["Required." if required else "Optional.", ""]
    return lines


def render(form: dict, source: str) -> str:
    body = form.get("body") or []
    guidance = [b["attributes"]["value"].rstrip("\n") for b in body if b.get("type") == "markdown"]
    fields = [b for b in body if b.get("type") != "markdown"]
    lines = [
        f"<!-- Generated from issue-forms/{source} by scripts/render_issue_forms.py. Edit the form, then rerun it. -->",
        "",
        f"# {form.get('name', source).strip()}",
        "",
        form.get("description", ""),
        "",
        f"Native issue type: `{form.get('type', 'none')}`. Title: `{form.get('title', '')}`.",
        "",
    ]
    for text in guidance[:1]:
        lines += [text, ""]
    lines += ["## Sections, in order", "", "Write each as a `### <label>` heading, as GitHub does when the form is filled in.", ""]
    for field in fields:
        lines += field_lines(field)
    for text in guidance[1:]:
        lines += [text, ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def targets() -> dict[Path, str]:
    return {
        OUT / f"{path.stem}.md": render(load(path), path.name)
        for path in sorted(FORMS.glob("*.yml"))
        if path.name not in SKIP
    }


def main(argv: list[str]) -> int:
    rendered = targets()
    if "--check" in argv:
        stale = [p for p, text in rendered.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
        for path in stale:
            print(f"{path.relative_to(HERE.parent)} is stale: rerun scripts/render_issue_forms.py")
        print(f"{len(rendered)} reference(s), {len(stale)} stale.")
        return 1 if stale else 0
    for path, text in rendered.items():
        path.write_text(text, encoding="utf-8")
    print(f"{len(rendered)} reference(s) written.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
