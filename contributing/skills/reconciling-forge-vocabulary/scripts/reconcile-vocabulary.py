#!/usr/bin/env python3
"""Reconcile a repository's labels and its organisation's issue types against
the files that declare them.

Two files declare the vocabulary, each read on its own:

    .github/labels.yml        the project's labels, else Ahrena's default
    .github/issue-types.yml   the project's issue types, else Ahrena's default

The defaults are in references/ beside this script. A project's file replaces
the default whole, file by file: a project that keeps only labels.yml gets its
own labels and Ahrena's issue types.

Without --apply nothing is written. Every declared label and issue type the
forge lacks, or holds with a different color or description, is listed with
what would change. With --apply the missing ones are created and the differing
ones updated. Nothing is ever deleted: a label the forge holds and no file
declares, such as `client:<name>`, is left as it is.

Issue types live on the organisation, and creating one needs an organisation
admin. When the token cannot read or write them, or the owner is a user with
no issue types, that is reported and the labels are reconciled anyway.

The files are read by a parser for the subset they use: a list of mappings of
scalar fields, quoted or not, with comments. Anything else is refused with its
line number rather than guessed at.

Usage:
    python3 reconcile-vocabulary.py                     plan for the current repository
    python3 reconcile-vocabulary.py <owner/repo>        plan for another one
    python3 reconcile-vocabulary.py --apply             create and update
    python3 reconcile-vocabulary.py --root <dir>        read .github/ under <dir>

Exit status: 0 when the plan was listed or applied, 1 when a file is refused
or a write to the repository failed.

Standard library only; the forge is reached through `gh`, authenticated with a
token that can write the repository's labels, and the organisation's issue
types where it should create those too.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS = Path(__file__).resolve().parent.parent / "references"

# --- the parser

FIELD = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?:[ ]+(?P<value>.*)|[ ]*)$")
DOUBLE = re.compile(r'^"(?P<text>(?:[^"\\]|\\.)*)"(?P<rest>.*)$')
SINGLE = re.compile(r"^'(?P<text>(?:[^']|'')*)'(?P<rest>.*)$")
ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t"}
TRAILING = re.compile(r"^(?:[ ]+#.*)?[ ]*$")

# What a value's first character would make it, in the YAML this subset leaves out.
CONSTRUCTS = {
    "[": "a flow sequence",
    "{": "a flow mapping",
    "|": "a block scalar",
    ">": "a block scalar",
    "&": "an anchor",
    "*": "an alias",
    "!": "a tag",
    "%": "a directive",
    "@": "a reserved indicator",
    "`": "a reserved indicator",
}


class Refused(Exception):
    """A file holds something outside the subset, or a field its schema does not allow."""


@dataclass
class Entry:
    line: int
    fields: dict[str, str] = field(default_factory=dict)
    lines: dict[str, int] = field(default_factory=dict)


@dataclass
class Reader:
    path: str
    entries: list[Entry] = field(default_factory=list)
    indent: int = 0
    started: bool = False

    def refuse(self, number: int, message: str) -> Refused:
        return Refused(f"{self.path}:{number}: {message}")


def parse(text: str, path: str) -> list[Entry]:
    """The file as a list of entries, or Refused naming the first line outside the subset."""
    reader = Reader(path)
    for number, raw in enumerate(text.splitlines(), 1):
        read_line(reader, number, raw.rstrip("\r"))
    return reader.entries


def read_line(reader: Reader, number: int, raw: str) -> None:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return
    if stripped == "---" and not reader.started:
        reader.started = True
        return
    reader.started = True
    body = raw.lstrip(" ")
    indent = len(raw) - len(body)
    if body.startswith("\t"):
        raise reader.refuse(number, "a tab in the indentation; indent with spaces")
    if body == "-" or body.startswith("- "):
        start_entry(reader, number, indent, body)
        return
    if not reader.entries:
        raise reader.refuse(number, "expected a list item, `- name: ...`; the file is a list of mappings")
    if indent != reader.indent:
        raise reader.refuse(number, f"indented {indent} spaces where the item's fields are at {reader.indent}; nesting is outside the subset")
    read_field(reader, number, body)


def start_entry(reader: Reader, number: int, indent: int, body: str) -> None:
    if indent:
        raise reader.refuse(number, "a list inside an item; only the top-level list is in the subset")
    rest = body[1:].lstrip(" ")
    if not rest or rest.startswith("#"):
        raise reader.refuse(number, "an item with no field on its own line; write `- name: ...`")
    if rest.startswith("- "):
        raise reader.refuse(number, "a list inside an item; only the top-level list is in the subset")
    reader.entries.append(Entry(number))
    reader.indent = len(body) - len(rest)
    read_field(reader, number, rest)


def read_field(reader: Reader, number: int, text: str) -> None:
    match = FIELD.match(text)
    if not match:
        raise reader.refuse(number, "not a `key: value` field; multi-line values and complex keys are outside the subset")
    entry, key = reader.entries[-1], match.group("key")
    if key in entry.fields:
        raise reader.refuse(number, f"`{key}` is given twice in one item")
    value = match.group("value")
    if value is None or not value.strip() or value.lstrip().startswith("#"):
        raise reader.refuse(number, f"`{key}` has no value; a nested mapping or list is outside the subset")
    entry.fields[key] = scalar(reader, number, value)
    entry.lines[key] = number


def scalar(reader: Reader, number: int, value: str) -> str:
    if value.startswith('"'):
        return quoted(reader, number, DOUBLE.match(value), unescape)
    if value.startswith("'"):
        return quoted(reader, number, SINGLE.match(value), lambda text: text.replace("''", "'"))
    if value[0] in CONSTRUCTS:
        raise reader.refuse(number, f"{CONSTRUCTS[value[0]]}; only a plain or quoted scalar is in the subset")
    plain = re.split(r"[ ]+#", value, maxsplit=1)[0].rstrip()
    if ": " in plain or plain.endswith(":") or plain.startswith("- "):
        raise reader.refuse(number, "a value that reads as a nested mapping or list; quote it if it is text")
    return plain


def quoted(reader: Reader, number: int, match: re.Match | None, decode) -> str:
    if not match:
        raise reader.refuse(number, "a quoted value that does not close on its line")
    if not TRAILING.match(match.group("rest")):
        raise reader.refuse(number, "text after a quoted value; only a comment may follow it")
    try:
        return decode(match.group("text"))
    except KeyError as error:
        raise reader.refuse(number, f"an escape `\\{error.args[0]}` outside the subset") from error


def unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda m: ESCAPES[m.group(1)], text)


# --- the two vocabularies


@dataclass(frozen=True)
class Declared:
    name: str
    color: str
    description: str


@dataclass(frozen=True)
class Kind:
    noun: str
    filename: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    color: re.Pattern
    color_hint: str


LABELS = Kind("label", "labels.yml", ("name", "color"), ("description",),
              re.compile(r"^#?[0-9A-Fa-f]{6}$"), "six hex digits")
TYPES = Kind("issue type", "issue-types.yml", ("name",), ("color", "description"),
             re.compile(r"^(?:gray|blue|green|yellow|orange|red|pink|purple)$"),
             "gray, blue, green, yellow, orange, red, pink or purple")


@dataclass(frozen=True)
class Source:
    kind: Kind
    shown: str
    items: tuple[Declared, ...]


def source(kind: Kind, root: Path) -> Source:
    """The project's own file where it has one, else Ahrena's default."""
    own = root / ".github" / kind.filename
    if own.is_file():
        path, shown = own, f".github/{kind.filename}"
    else:
        path, shown = DEFAULTS / kind.filename, f"{kind.filename} (Ahrena's default)"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise Refused(f"{shown}: cannot be read: {error}") from error
    return Source(kind, shown, declared(kind, parse(text, shown), shown))


def declared(kind: Kind, entries: list[Entry], path: str) -> tuple[Declared, ...]:
    items: list[Declared] = []
    seen: dict[str, int] = {}
    for entry in entries:
        item = checked(kind, entry, path)
        if item.name.lower() in seen:
            raise Refused(f"{path}:{entry.line}: {kind.noun} {item.name!r} is declared twice, first on line {seen[item.name.lower()]}")
        seen[item.name.lower()] = entry.line
        items.append(item)
    return tuple(items)


def checked(kind: Kind, entry: Entry, path: str) -> Declared:
    for key, value in entry.fields.items():
        if key not in kind.required + kind.optional:
            allowed = ", ".join(kind.required + kind.optional)
            raise Refused(f"{path}:{entry.lines[key]}: `{key}` is not a field of a {kind.noun}; the fields are {allowed}")
    for key in kind.required:
        if not entry.fields.get(key, "").strip():
            raise Refused(f"{path}:{entry.line}: the {kind.noun} has no `{key}`")
    color = entry.fields.get("color", "")
    if color and not kind.color.match(color):
        raise Refused(f"{path}:{entry.lines['color']}: color {color!r} is not {kind.color_hint}")
    return Declared(entry.fields["name"].strip(), color.lstrip("#"), entry.fields.get("description", ""))


# --- the forge, through gh


class ForgeError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


# The answers that mean the token may not, or the owner has none, rather than a fault.
NOT_PERMITTED = {401, 403, 404, 410}


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        status = re.search(r"HTTP (\d{3})", message)
        raise ForgeError(int(status.group(1)) if status else 0, message)
    return result.stdout


def current_labels(repo: str) -> list[dict]:
    out = gh("api", "--paginate", f"repos/{repo}/labels?per_page=100", "--jq", ".[] | {name, color, description}")
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def current_types(org: str) -> list[dict]:
    return json.loads(gh("api", f"orgs/{org}/issue-types") or "[]")


# --- the plan


@dataclass(frozen=True)
class Change:
    item: Declared
    current: dict | None
    differences: tuple[str, ...]

    def __str__(self) -> str:
        if self.current is None:
            what = f"color {self.item.color}, " if self.item.color else ""
            return f"create  {self.item.name!r}  {what}{self.item.description!r}"
        return f"update  {self.item.name!r}  " + "; ".join(self.differences)


def differences(item: Declared, current: dict) -> tuple[str, ...]:
    found: list[str] = []
    if current.get("name") != item.name:
        found.append(f"name {current.get('name')!r} -> {item.name!r}")
    held = (current.get("color") or "").lower()
    if item.color and held != item.color.lower():
        found.append(f"color {held or 'none'} -> {item.color}")
    if (current.get("description") or "") != item.description:
        found.append(f"description {current.get('description') or ''!r} -> {item.description!r}")
    if current.get("is_enabled") is False:
        found.append("disabled -> enabled")
    return tuple(found)


def plan(items: tuple[Declared, ...], current: list[dict]) -> list[Change]:
    by_name = {(c.get("name") or "").lower(): c for c in current}
    changes: list[Change] = []
    for item in items:
        held = by_name.get(item.name.lower())
        if held is None:
            changes.append(Change(item, None, ()))
        elif differences(item, held):
            changes.append(Change(item, held, differences(item, held)))
    return changes


# --- the writes


def label_write(repo: str, change: Change) -> list[str]:
    item = change.item
    fields = ["-f", f"color={item.color}", "-f", f"description={item.description}"]
    if change.current is None:
        return ["api", "-X", "POST", f"repos/{repo}/labels", "-f", f"name={item.name}", *fields]
    path = urllib.parse.quote(change.current["name"], safe="")
    return ["api", "-X", "PATCH", f"repos/{repo}/labels/{path}", "-f", f"new_name={item.name}", *fields]


def type_write(org: str, change: Change) -> list[str]:
    item = change.item
    fields = ["-f", f"name={item.name}", "-f", f"description={item.description}", "-F", "is_enabled=true"]
    if item.color:
        fields += ["-f", f"color={item.color}"]
    if change.current is None:
        return ["api", "-X", "POST", f"orgs/{org}/issue-types", *fields]
    return ["api", "-X", "PATCH", f"orgs/{org}/issue-types/{change.current['id']}", *fields]


# --- the run


@dataclass(frozen=True)
class Options:
    repo: str
    root: Path
    apply: bool


@dataclass
class Tally:
    failures: int = 0
    written: int = 0
    planned: int = 0


def show_plan(src: Source, changes: list[Change], target: str) -> None:
    print(f"{src.kind.noun}s: from {src.shown}, against {target}")
    for change in changes:
        print(f"  {change}")
    created = sum(1 for c in changes if c.current is None)
    print(f"  {len(src.items)} declared, {created} to create, {len(changes) - created} to update.")


def apply_changes(changes: list[Change], writes: list[list[str]], tally: Tally) -> list[ForgeError]:
    """Each write in turn; the refusals are returned rather than stopping the rest."""
    refused: list[ForgeError] = []
    for change, args in zip(changes, writes):
        verb = "created" if change.current is None else "updated"
        try:
            gh(*args)
        except ForgeError as error:
            print(f"  failed  {change.item.name!r}: {error}")
            refused.append(error)
            continue
        print(f"  {verb}  {change.item.name!r}")
        tally.written += 1
    return refused


def reconcile_labels(opts: Options, src: Source, tally: Tally) -> None:
    try:
        changes = plan(src.items, current_labels(opts.repo))
    except ForgeError as error:
        print(f"labels: cannot read the labels of {opts.repo}: {error}")
        tally.failures += 1
        return
    show_plan(src, changes, opts.repo)
    tally.planned += len(changes)
    if opts.apply:
        tally.failures += len(apply_changes(changes, [label_write(opts.repo, c) for c in changes], tally))


def reconcile_types(opts: Options, src: Source, tally: Tally) -> None:
    org = opts.repo.split("/")[0]
    target = f"the organisation {org}"
    try:
        changes = plan(src.items, current_types(org))
    except ForgeError as error:
        print(f"issue types: not reconciled, the token cannot read the issue types of {org}: {error}")
        print("  An owner with no organisation, or a token without organisation access, has none to read.")
        return
    show_plan(src, changes, target)
    tally.planned += len(changes)
    if not opts.apply:
        return
    refused = apply_changes(changes, [type_write(org, c) for c in changes], tally)
    denied = [e for e in refused if e.status in NOT_PERMITTED]
    if denied:
        print(f"  {len(denied)} issue type(s) need an admin of {org} to create or update; the labels are unaffected.")
    tally.failures += len(refused) - len(denied)


def options(argv: list[str]) -> Options:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", help="owner/repo; the current repository when omitted")
    parser.add_argument("--apply", action="store_true", help="create and update; without it nothing is written")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="the project whose .github/ is read")
    args = parser.parse_args(argv)
    return Options(args.repo or "", args.root, args.apply)


def current_repo() -> str:
    return gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()


def main(argv: list[str]) -> int:
    opts = options(argv)
    try:
        labels, types = source(LABELS, opts.root), source(TYPES, opts.root)
    except Refused as error:
        print(f"refused: {error}")
        return 1
    try:
        repo = opts.repo or current_repo()
    except ForgeError as error:
        print(f"cannot tell which repository this is, pass owner/repo: {error}")
        return 1
    opts = Options(repo, opts.root, opts.apply)
    tally = Tally()
    reconcile_labels(opts, labels, tally)
    reconcile_types(opts, types, tally)
    if not opts.apply:
        print(f"dry run: {tally.planned} change(s) listed, nothing written. Run again with --apply to make them.")
    else:
        print(f"applied: {tally.written} written, {tally.failures} failed, nothing deleted.")
    return 1 if tally.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
