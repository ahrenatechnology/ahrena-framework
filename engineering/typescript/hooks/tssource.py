"""The lexical reading every TypeScript hook in this plugin shares.

There is no TypeScript parser in the Python standard library, and the hooks
take no dependency, so they do not parse. They scan. The scan does the one
thing a regular expression over raw text cannot: it knows where code is. A
comment, a string, the text of a template literal and the body of a regular
expression are blanked to spaces, with every newline kept, so an offset in the
blanked text is the same offset in the file and its line number is the same
line number. The comments are kept apart, by the lines they occupy, because two
of the hooks read them: a reason written beside a hole, and a directive to the
compiler.

What a scan cannot know is anything a type checker knows. The conditions these
hooks decide are therefore the ones the source spells: a keyword, a call, a
comment, a path. Everything that needs a type is left to `tsc` and to
typescript-eslint, and the rules that cite these hooks say so condition by
condition.

The one place the scan is knowingly wrong is JSX text. `<p>Note: any user</p>`
is prose to a reader and code to this scanner. The rules' boundary sections
name that cost rather than pay for a JSX parser.

Three constants carry decisions. `SKIP_NAMES` holds the vendored and
generated trees a walk does not enter; dot-prefixed directories are skipped by
shape, so a cache nobody has heard of yet is skipped too. `REGEX_AFTER` and
`REGEX_KEYWORDS` decide whether a slash opens a regular expression or divides:
after an identifier, a closing bracket or a literal it divides, and after
anything else it opens one. That is the rule every JavaScript tokenizer that
does not parse uses, and its failure case, a regex right after the `)` of an
`if` condition, does not occur in formatted code. `DIRECTIVE` recognises a
comment that only instructs a tool, which is not a reason; the lint directives
carry a description after ` -- `, and Biome's after the first colon, and that
description is a reason, because it is what those tools ask an author to
write.

This module is imported by the `check-*.py` hooks beside it and runs nothing
on its own.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field
from pathlib import Path

TYPESCRIPT = (".ts", ".tsx", ".mts", ".cts")
SCRIPT = TYPESCRIPT + (".js", ".jsx", ".mjs", ".cjs")

SKIP_NAMES = frozenset({"node_modules", "dist", "build", "out", "coverage"})

REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")
REGEX_KEYWORDS = frozenset(
    {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else", "yield", "await"}
)

DIRECTIVE = re.compile(
    r"^(?:eslint-disable(?:-next-line|-line)?|eslint-enable|oxlint-disable(?:-next-line|-line)?|"
    r"biome-ignore(?:-all|-start|-end)?|prettier-ignore|istanbul\s+ignore|c8\s+ignore|v8\s+ignore|@ts-[a-z-]+)\b"
)


@dataclass
class Comment:
    """One comment: where it opens and closes, and its text without delimiters.

    The scan records offsets; `load` turns them into line numbers.
    """

    start: int
    end: int
    text: str


@dataclass
class Source:
    """One file: its raw text, the same text with every non-code span blanked, and its comments."""

    path: Path
    rel: str
    text: str
    code: str
    comments: list[Comment] = field(default_factory=list)
    starts: list[int] = field(default_factory=list)

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset)


def reason_near(source: Source, line: int) -> bool:
    """Whether a comment on this line, or one ending on the line above, says why."""
    near = [c for c in source.comments if c.start <= line <= c.end or c.end == line - 1]
    return any(is_reason(comment.text) for comment in near)


def is_reason(comment: str) -> bool:
    text = " ".join(part.strip().lstrip("*").strip() for part in comment.splitlines()).strip()
    if not DIRECTIVE.match(text):
        return bool(text)
    if " -- " in text:
        return bool(text.split(" -- ", 1)[1].strip())
    if text.startswith("biome-ignore") and ":" in text:
        return bool(text.split(":", 1)[1].strip())
    return False


class _Scanner:
    """Walks the text once, blanking what is not code.

    `templates` holds the brace depth at each open `${`, so the `}` that
    closes one resumes the template text instead of closing a block.
    `previous` is the last significant character, or `w` after a word, and
    decides whether a slash opens a regular expression.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.out = list(text)
        self.comments: list[Comment] = []
        self.templates: list[int] = []
        self.depth = 0
        self.previous = ""
        self.word = ""

    def blank(self, start: int, end: int) -> None:
        for index in range(start, end):
            if self.out[index] != "\n":
                self.out[index] = " "

    def comment(self, start: int, end: int, body_start: int, body_end: int) -> int:
        self.comments.append(Comment(start, end, self.text[body_start:body_end]))
        self.blank(start, end)
        return end

    def line_comment(self, at: int) -> int:
        end = self.text.find("\n", at)
        end = len(self.text) if end == -1 else end
        return self.comment(at, end, at + 2, end)

    def block_comment(self, at: int) -> int:
        close = self.text.find("*/", at + 2)
        end = len(self.text) if close == -1 else close + 2
        return self.comment(at, end, at + 2, end - 2 if close != -1 else end)

    def string(self, at: int) -> int:
        quote = self.text[at]
        index = at + 1
        while index < len(self.text) and self.text[index] not in (quote, "\n"):
            index += 2 if self.text[index] == "\\" else 1
        self.blank(at + 1, min(index, len(self.text)))
        self.previous, self.word = '"', ""
        return index + 1

    def template(self, at: int) -> int:
        """Scan template text from `at` to its close or to the next `${`."""
        index = at
        while index < len(self.text):
            char = self.text[index]
            if char == "\\":
                index += 2
                continue
            if char == "`":
                self.blank(at, index)
                self.previous, self.word = '"', ""
                return index + 1
            if char == "$" and self.text.startswith("${", index):
                self.blank(at, index)
                self.templates.append(self.depth)
                self.depth += 1
                self.previous, self.word = "{", ""
                return index + 2
            index += 1
        self.blank(at, index)
        return index

    def regex(self, at: int) -> int:
        index, in_class = at + 1, False
        while index < len(self.text) and self.text[index] != "\n":
            char = self.text[index]
            if char == "\\":
                index += 2
                continue
            if char == "[":
                in_class = True
            elif char == "]":
                in_class = False
            elif char == "/" and not in_class:
                break
            index += 1
        self.blank(at + 1, index)
        self.previous, self.word = '"', ""
        return index + 1

    def regex_allowed(self) -> bool:
        return self.previous in REGEX_AFTER or self.previous == "" or self.word in REGEX_KEYWORDS

    def close_brace(self, at: int) -> int:
        self.depth -= 1
        if self.templates and self.depth == self.templates[-1]:
            self.templates.pop()
            return self.template(at + 1)
        self.previous, self.word = "}", ""
        return at + 1

    def step(self, at: int) -> int:
        char, after = self.text[at], self.text[at + 1 : at + 2]
        if char == "/" and after == "/":
            return self.line_comment(at)
        if char == "/" and after == "*":
            return self.block_comment(at)
        if char in "\"'":
            return self.string(at)
        if char == "`":
            return self.template(at + 1)
        if char == "/" and self.regex_allowed():
            return self.regex(at)
        if char == "{":
            self.depth += 1
        if char == "}":
            return self.close_brace(at)
        return self.token(at)

    def token(self, at: int) -> int:
        char = self.text[at]
        if char.isspace():
            return at + 1
        if char.isalnum() or char in "_$":
            end = at
            while end < len(self.text) and (self.text[end].isalnum() or self.text[end] in "_$"):
                end += 1
            self.previous, self.word = "w", self.text[at:end]
            return end
        self.previous, self.word = char, ""
        return at + 1

    def run(self) -> tuple[str, list[Comment]]:
        index = 0
        while index < len(self.text):
            index = self.step(index)
        return "".join(self.out), self.comments


def scan(text: str) -> tuple[str, list[Comment]]:
    return _Scanner(text).run()


def load(path: Path, rel: str) -> Source:
    text = path.read_text(encoding="utf-8", errors="replace")
    code, comments = scan(text)
    source = Source(path, rel, text, code, starts=[0] + [match.end() for match in re.finditer("\n", text)])
    source.comments = [Comment(source.line(c.start), source.line(max(c.start, c.end - 1)), c.text) for c in comments]
    return source


def display(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def skipped(relative: Path) -> bool:
    """Whether a walk leaves this path alone: vendored, generated or hidden."""
    return any(part in SKIP_NAMES or part.startswith(".") for part in relative.parts[:-1])


def walk(roots: list[Path], suffixes: tuple[str, ...]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if root.is_file():
            if root.name.endswith(suffixes):
                found.add(root)
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.name.endswith(suffixes) and not skipped(path.relative_to(root)):
                found.add(path)
    return sorted(found)


def closing(code: str, opening: int) -> int:
    """The offset of the bracket that closes the one at `opening`, or -1."""
    pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    want = pairs[code[opening]]
    depth = 0
    for index in range(opening, len(code)):
        if code[index] == code[opening]:
            depth += 1
        elif code[index] == want:
            depth -= 1
            if depth == 0:
                return index
    return -1


@dataclass
class Finding:
    """A failure: the rule, the path with its line, the condition and what to do."""

    rule: str
    where: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


def report(findings: list[Finding], checked: int) -> int:
    if not findings:
        print(f"{checked} file(s), no failures.")
        return 0
    print(f"{len(findings)} failure(s) across {checked} file(s):\n")
    for finding in sorted(findings, key=lambda item: (item.where, item.condition, item.message)):
        print(finding)
    return 1
