#!/usr/bin/env python3
"""Detector for the promise conditions in the TypeScript engineering rule.

Decides four of the five conditions stated in
engineering/typescript/rules/promises.md:

    2. no async function is passed to `forEach`
    3. no rejection handler or catch block discards what it caught, unless a
       comment inside it says why
    4. a process-level `unhandledRejection` or `uncaughtException` listener
       ends the process: it throws, or calls `process.exit`
    5. nothing runs Node with `--unhandled-rejections` set to a mode that
       stops an unhandled rejection from ending the process

Condition 1, that no promise floats, is typescript-eslint's to decide:
whether a call returns a promise is a fact about its type, and a scan of the
source cannot know it. This hook decides the shapes that need no type.

`QUIETING` names three of Node's five documented modes: `throw` is the
default since v15 and `strict` is stricter, and the other three let the
process run on past an unhandled rejection, which is the state condition 5
refuses. `LAUNCHERS` is the set of files where a Node flag is set in
practice; a flag set from anywhere else is a gap the rule's boundary section
names. A listener passed by reference has no body here to read, and is left
to review. `LISTENER` is matched on the blanked code, where the event name is a
blanked string, and the name is then read from the raw text at that offset.

Usage:
    python3 engineering/typescript/hooks/check-promises.py [path ...]
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import re  # noqa: E402
from pathlib import Path  # noqa: E402

from tssource import SCRIPT, Finding, Source, closing, display, load, report, walk  # noqa: E402

RULE = "promises"

ASYNC_FOREACH = re.compile(r"\.forEach\s*\(\s*async\b")

CATCH_CALL = re.compile(r"\.catch\s*\(")
EMPTY_CALLBACK = re.compile(r"^\(\s*(?:async\s+)?(?:\([^()]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{\s*\}\s*\)$|^\(\s*(?:async\s+)?function\b[^{]*\{\s*\}\s*\)$")

CATCH_BLOCK = re.compile(r"\bcatch\s*(?:\([^()]*\))?\s*\{")

LISTENER = re.compile(r"\bprocess\s*\.\s*(?:on|once|addListener|prependListener)\s*(\()\s*[\"']")
EVENTS = re.compile(r"[\"'](unhandledRejection|uncaughtException)[\"']")
INLINE_FUNCTION = re.compile(r"=>|\bfunction\b")
ENDS_PROCESS = re.compile(r"\bthrow\b|\bprocess\s*\.\s*(?:exit|abort|kill)\s*\(")

QUIETING = re.compile(r"--unhandled-rejections[= ](none|warn-with-error-code|warn)\b")

LAUNCHERS = re.compile(r"^(package\.json|\.npmrc|Procfile|.*Dockerfile.*|.*\.dockerfile|(docker-)?compose.*\.ya?ml|\.env(\..*)?|.*\.sh)$")


def check_async_foreach(source: Source, findings: list[Finding]) -> None:
    for match in ASYNC_FOREACH.finditer(source.code):
        line = source.line(match.start())
        findings.append(
            Finding(RULE, f"{source.rel}:{line}", 2, "an async callback to forEach floats every promise it returns; use for...of with await, or Promise.all over map")
        )


def _has_comment_between(source: Source, start: int, end: int) -> bool:
    """Whether a comment sits in this span of an otherwise empty block.

    The blanked code and the raw text differ exactly where a comment or a
    string was; inside a block with no code there is no string, so a
    difference is a comment.
    """
    return source.code[start:end] != source.text[start:end]


def check_empty_handlers(source: Source, findings: list[Finding]) -> None:
    code = source.code
    for match in CATCH_CALL.finditer(code):
        opening = match.end() - 1
        close = closing(code, opening)
        if close == -1:
            continue
        if EMPTY_CALLBACK.match(code[opening : close + 1]) and not _has_comment_between(source, opening, close):
            line = source.line(match.start())
            findings.append(Finding(RULE, f"{source.rel}:{line}", 3, ".catch with an empty handler discards the rejection; handle it, log it, or say why inside"))
    for match in CATCH_BLOCK.finditer(code):
        opening = match.end() - 1
        close = closing(code, opening)
        if close == -1 or code[opening + 1 : close].strip():
            continue
        if not _has_comment_between(source, opening, close):
            line = source.line(match.start())
            findings.append(Finding(RULE, f"{source.rel}:{line}", 3, "an empty catch block discards what it caught; handle it, rethrow it, or say why inside"))


def check_listeners(source: Source, findings: list[Finding]) -> None:
    code = source.code
    for match in LISTENER.finditer(code):
        named = EVENTS.match(source.text, match.end() - 1)
        if not named:
            continue
        close = closing(code, match.start(1))
        body = code[named.end() : close] if close != -1 else ""
        if not INLINE_FUNCTION.search(body):
            continue
        if not ENDS_PROCESS.search(body):
            line = source.line(match.start())
            event = named.group(1)
            findings.append(
                Finding(RULE, f"{source.rel}:{line}", 4, f"a {event} listener that does not end the process keeps it running in an unknown state; exit or rethrow")
            )


def check_launchers(roots: list[Path], base: Path, findings: list[Finding]) -> int:
    files = [path for path in walk(roots, ("",)) if LAUNCHERS.match(path.name)]
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, text in enumerate(lines, start=1):
            for match in QUIETING.finditer(text):
                findings.append(
                    Finding(
                        RULE,
                        f"{display(path, base)}:{number}",
                        5,
                        f"--unhandled-rejections={match.group(1)} lets the process run past a rejection nobody handled; use the default, throw, or strict",
                    )
                )
    return len(files)


SOURCE_CHECKS = (check_async_foreach, check_empty_handlers, check_listeners)


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    base = Path.cwd()
    findings: list[Finding] = []
    checked = check_launchers(roots, base, findings)
    for path in walk(roots, SCRIPT):
        source = load(path, display(path, base))
        for check in SOURCE_CHECKS:
            check(source, findings)
        checked += 1
    return report(findings, checked)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
