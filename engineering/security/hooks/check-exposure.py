#!/usr/bin/env python3
"""Detector for rules/layer-exposure.md: nothing sensitive leaves the layer that owns it.

Decides three conditions of one rule, over the lines a change adds:

    engineering/security/rules/layer-exposure.md
      1. a caught error handed whole to an exit: its text, its message, its
         stack, or the error value itself, in a response, a log, a trace
         attribute or standard output
      2. a dependency's whole response handed to an exit: the body, text,
         content or decoded JSON of what an upstream call returned
      3. an access policy or a whole configuration handed to an exit: a
         policy document, the whole process environment, an object's whole
         attribute map; and a Terraform output whose value is a policy or a
         whole resource or module

Condition 4 of the rule (every other sensitive class, and whether what a
line emits is an allowlist) needs a reader and is not attempted here.

An exit is recognised by the call or the shape on the line: a logging,
printing or tracing call, a response constructor or writer, a returned
literal that carries a status code or a body, an HTTP error raised with a
detail. A value is recognised by its binding: the names a file binds to a
caught error (`except ... as e`, `catch (e)`, `.catch(e =>`, `Err(e)`,
`rescue => e`, and `err` in Go) are read from the whole file, so an exit
line the change adds is judged even when the `except` above it is older.

A line carrying an `ADR-N` pointer is exempt: the decision that its reader
is inside the layer (an operator reading their own tool's error, say) was
recorded, the same exemption rules/backstage-language.md gives a name a
contract fixes. Lines inside a triple-quoted string are prose and are skipped.

String literals are masked before a line is read, keeping only what they
interpolate (`{e}` in an f-string or `format!`, `${e}` in a template), so
`{"error": "not found"}` names no error and `f"failed: {e}"` does.

The subject is a change. `--changed <spec>` passes the spec to a pinned git
diff and only the lines it adds are read; without it, every line of every
file handed to the run is read. The diff is read here rather than through
another plugin's module, because a hook takes no dependency, and a plugin
installed alone must still run its own gate.

Report-only. The correction is a list of named fields, and which fields a
caller needs is the author's choice, not this script's.

Usage:
    python3 engineering/security/hooks/check-exposure.py [path ...]
    python3 engineering/security/hooks/check-exposure.py --changed origin/main...HEAD [path ...]
    python3 engineering/security/hooks/check-exposure.py --changed --cached [path ...]
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RULE = "layer-exposure"

SOURCE = re.compile(r"\.(py|pyi|ts|tsx|mts|cts|js|jsx|mjs|cjs|go|rs|java|kt|kts|cs|rb|php|swift|scala)$")
TERRAFORM = re.compile(r"\.tf$")
SKIP_DIRS = frozenset(".git .venv venv node_modules __pycache__ dist build vendor target .terraform".split())

SPEC_OPTIONS = ("--cached", "--staged")
PINNED = ("--no-color", "--no-ext-diff", "--no-textconv", "--src-prefix=a/", "--dst-prefix=b/", "--unified=0")
UNMERGED = ("diff --cc ", "diff --combined ", "* Unmerged path ")
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

EXIT_PATTERNS = (
    r"\bprint(ln)?!?\(",
    r"\be?print(ln)?!\(",
    r"\bconsole\.\w+\(",
    r"\blog(ger|ging)?\.(trace|debug|info|warn|warning|error|exception|critical|fatal|log|Print\w*|Fatal\w*|Panic\w*)\(",
    r"\b(logrus|slog|zap|structlog|winston|pino|tracing|log)\b(::|\.)\w+!?\(",
    r"\b(trace|debug|info|warn|error)!\(",
    r"\bfmt\.(Print|Fprint)\w*\(",
    r"\b(set_?[Aa]ttribute|setTag|record_?[Ee]xception|add_event|addEvent)\(",
    r"\bsys\.std(out|err)\.write\(",
    r"\bSystem\.(out|err)\.print",
    r"\b(Response|JSONResponse|PlainTextResponse|HTMLResponse|HttpResponse|HTTPResponse|JsonResponse|NextResponse|ResponseEntity)\b",
    r"\b(jsonify|make_response|abort|http\.Error|HTTPException|HttpException|HttpError)\(",
    r"\b(res|reply|ctx|c|w|rw|writer)\.(status\(.*\)\.)?(json|send|write|end|body|JSON|String|Write|WriteString|throw)\(",
    r"""["'](body|statusCode|detail|message|error|errors)["']\s*:""",
    r"\b(body|detail|message|error|errors)\s*:\s*(?![A-Z]|(str|string|int|bool|number|dict|object|unknown|any)\b)",
    r"\bStatusCode::\w+",
    r"^\s*return\s*[\[{(]",
)
EXIT = re.compile("|".join(f"(?:{p})" for p in EXIT_PATTERNS))

ERROR_BINDINGS = (
    r"\bexcept\b[^:#]*\bas\s+(\w+)",
    r"\bcatch\s*\(\s*(?:[\w.|]+\s+)?(\w+)\s*(?::\s*\w+)?\s*\)",
    r"\.catch\(\s*(?:async\s*)?\(?\s*(\w+)",
    r"\bErr\(\s*(\w+)\s*\)",
    r"\bmap_err\(\s*\|\s*(\w+)\s*\|",
    r"\brescue\b[^=\n]*=>\s*(\w+)",
    r"\b(\w*[eE]rr)\s*:?=",
)
BINDING = re.compile("|".join(ERROR_BINDINGS))
CONVENTIONAL = {".go": frozenset({"err"})}
TRIPLE = re.compile("[\"]{3}|[']{3}")
DECIDED = re.compile(r"\bADR-\d+\b")

ERROR_TEXT = r"(message|msg|args|stack|detail|details|response|body|text|description|reason|Error\(\)|toString\(\)|getMessage\(\)|__str__\(\)|to_string\(\))"
NOT_WHOLE_BEFORE = re.compile(r"(\.|\btype\(|\btypeof\s+|\bisinstance\(|\binstanceof\s+|\berrors\.(Is|As)\()\s*$")
TEXT_OF = re.compile(rf"\s*\.\s*{ERROR_TEXT}(?![\w\[.])")
FIELD_OF = re.compile(r"\s*(\.|\[|=(?!=)|:=)")
STACK = re.compile(r"\btraceback\.(format_exc|format_exception|print_exc)\(|\bprintStackTrace\(|\bdebug\.Stack\(|\bBacktrace::")

UPSTREAM = re.compile(
    r"\b\w*(resp|response|upstream)\w*\.(text|content|body|data|raw|json\(\)|read\(\)|text\(\))(?!\s*[\[.(])",
    re.IGNORECASE,
)
WHOLE_CONFIG = re.compile(
    r"\bos\.environ\b(?!\s*(\[|\.get\b))|\bprocess\.env\b(?!\s*(\.|\[))|\bvars\(\s*\w+\s*\)|\.__dict__\b|\bos\.Environ\(\)"
)
POLICY = re.compile(
    r"\b((iam|bucket|access|role|resource|key|trust|inline|managed|assume_?role|permissions?)_?)?"
    r"polic(y|ies)(_?(document|version|json))?\b(?!\s*[\[.(=]|\s*:\s)",
    re.IGNORECASE,
)

TF_OUTPUT = re.compile(r'^\s*output\s+"([^"]+)"')
TF_VALUE = re.compile(r"^\s*value\s*=\s*(.+?)\s*$")
TF_POLICY = re.compile(r"\.(policy|json|assume_role_policy|inline_policy)\b|policy_document")
TF_WHOLE = re.compile(r"^(module\.[\w-]+|data\.[\w-]+\.[\w-]+|[a-z][a-z0-9]*_[\w-]+\.[\w-]+)$")

STRING = re.compile(r"""(?P<prefix>(?:(?<!\w)[fFbBrRuU]{1,2})?)(?P<quote>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)""")
COMMENT_LEADERS = ("#", "//", "/*", "* ")
TRAILING_COMMENT = re.compile(r"\s(?:#|//)\s")
INTERPOLATION = re.compile(r"\$\{([^}]*)\}|\{([^{}:!]+)(?:![rs])?(?::[^{}]*)?\}")


@dataclass(frozen=True)
class Finding:
    where: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{RULE}] condition {self.condition}: {self.message}"


class Unavailable(Exception):
    """git could not say which lines the change added, so nothing was decided.

    The reason is a named field, `why`, so the run prints it and not the exception.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.why = reason


def masked(line: str) -> str:
    """The line with each string literal replaced by what it interpolates."""

    def keep(match: re.Match[str]) -> str:
        body = match.group("quote")
        interpolating = "f" in match.group("prefix").lower() or body.startswith("`")
        found = INTERPOLATION.findall(body) if interpolating or "${" in body else []
        return " ".join(a or b for a, b in found) or '""'

    if line.lstrip().startswith(COMMENT_LEADERS):
        return ""
    return TRAILING_COMMENT.split(STRING.sub(keep, line), maxsplit=1)[0]


def error_names(text: str, conventional: frozenset[str]) -> frozenset[str]:
    """Every name the file binds to a caught error, plus the language's conventional ones."""
    names = {name for match in BINDING.finditer(text) for name in match.groups() if name} | conventional
    return frozenset(name for name in names if name not in {"_", "self", "this"})


def prose_lines(text: str) -> frozenset[int]:
    """The lines inside a triple-quoted string, which are prose, not code."""
    inside, prose = False, set()
    for number, line in enumerate(text.splitlines(), start=1):
        toggles = len(TRIPLE.findall(line))
        if inside or toggles:
            prose.add(number)
        inside = inside != (toggles % 2 == 1)
    return frozenset(prose)


def whole_error(code: str, names: frozenset[str]) -> str | None:
    """The first caught-error name the line uses whole, or by its text.

    An occurrence inside the binding itself (`Err(e) =>`, `except X as e`) is
    the name being bound, not used, and is skipped.
    """
    bound = [match.span() for match in BINDING.finditer(code)]
    for name in sorted(names):
        for match in re.finditer(rf"\b{re.escape(name)}\b", code):
            if any(start <= match.start() < end for start, end in bound):
                continue
            before, after = code[: match.start()], code[match.end() :]
            if NOT_WHOLE_BEFORE.search(before):
                continue
            if TEXT_OF.match(after) or not FIELD_OF.match(after):
                return name
    return None


def source_findings(rel: str, number: int, code: str, names: frozenset[str]) -> list[Finding]:
    """Conditions 1 to 3 on one added line of source that writes to an exit."""
    where = f"{rel}:{number}"
    found = []
    name = whole_error(code, names)
    if name or STACK.search(code):
        shown = f"the caught error `{name}`" if name else "a stack trace"
        found.append(Finding(where, 1, f"{shown} reaches an exit whole. Return a generic error and a correlation id; log named fields (code, operation, request id), never the error's text."))
    if UPSTREAM.search(code):
        found.append(Finding(where, 2, "a dependency's whole response reaches an exit. Map the fields the caller needs into this layer's own type and emit those."))
    if WHOLE_CONFIG.search(code) or POLICY.search(code):
        found.append(Finding(where, 3, "an access policy or a whole configuration reaches an exit. Emit the named fields the reader needs, or nothing."))
    return found


def check_source(rel: str, text: str, scope: frozenset[int] | None) -> list[Finding]:
    names = error_names(text, CONVENTIONAL.get(Path(rel).suffix, frozenset()))
    skipped = prose_lines(text)
    found: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if (scope is not None and number not in scope) or number in skipped or DECIDED.search(line):
            continue
        code = masked(line)
        if EXIT.search(line):
            found += source_findings(rel, number, code, names)
    return found


def check_terraform(rel: str, text: str, scope: frozenset[int] | None) -> list[Finding]:
    """Condition 3 on a Terraform output whose value is a policy or a whole object."""
    found, output = [], None
    for number, line in enumerate(text.splitlines(), start=1):
        opened = TF_OUTPUT.match(line)
        output = opened.group(1) if opened else output
        value = TF_VALUE.match(line)
        in_scope = scope is None or number in scope
        if output and value and in_scope and (TF_POLICY.search(value.group(1)) or TF_WHOLE.match(value.group(1))):
            found.append(Finding(f"{rel}:{number}", 3, f"output `{output}` publishes a policy or a whole object to every reader of the plan and the pipeline log. Output the one attribute a consumer needs, marked sensitive where it is."))
    return found


def git(args: list[str], cwd: Path) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if done.returncode != 0:
        raise Unavailable(done.stderr.decode("utf-8", "replace").strip() or f"git {args[0]} failed")
    return done.stdout.decode("utf-8", "replace")


def changed_lines(spec: str) -> dict[Path, frozenset[int]]:
    """The lines a pinned diff says the change adds, keyed by absolute path."""
    if spec.startswith("-") and spec not in SPEC_OPTIONS:
        raise Unavailable(f"{spec!r} is not a revision or range; the only options --changed takes are {', '.join(SPEC_OPTIONS)}")
    top = Path(git(["rev-parse", "--show-toplevel"], Path.cwd()).strip()).resolve()
    diff = git(["-c", "color.ui=false", "diff", spec, *PINNED], top)
    if any(row.startswith(UNMERGED) for row in diff.split("\n")):
        raise Unavailable("the diff holds an unresolved merge, so no line can be scoped")
    return parse_diff(diff, top)


def parse_diff(diff: str, top: Path) -> dict[Path, frozenset[int]]:
    added: dict[Path, set[int]] = {}
    current: set[int] | None = None
    remaining = 0
    for row in diff.split("\n"):
        if remaining:
            remaining -= 0 if row.startswith("\\") else 1
            continue
        if row.startswith("+++ b/"):
            current = added.setdefault((top / row[6:]).resolve(), set())
        elif row.startswith("+++ /dev/null"):
            current = None
        hunk = HUNK.match(row)
        if hunk:
            removed, start, count = int(hunk.group(1) or 1), int(hunk.group(2)), int(hunk.group(3) or 1)
            remaining = removed + count
            if current is not None:
                current.update(range(start, start + count))
    return {path: frozenset(lines) for path, lines in added.items()}


def walk(paths: list[str]) -> list[Path]:
    files = []
    for raw in paths or ["."]:
        path = Path(raw)
        found = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and not SKIP_DIRS & set(p.parts))
        files += [p for p in found if SOURCE.search(p.name) or TERRAFORM.search(p.name)]
    return files


def run(paths: list[str], spec: str | None) -> list[Finding]:
    scopes = changed_lines(spec) if spec else None
    findings: list[Finding] = []
    for path in walk(paths):
        scope = None if scopes is None else scopes.get(path.resolve(), frozenset())
        if scope is not None and not scope:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        check = check_terraform if TERRAFORM.search(path.name) else check_source
        findings += check(str(path), text, scope)
    return findings


def split_argv(argv: list[str]) -> tuple[list[str], str | None]:
    if "--changed" not in argv:
        return argv, None
    at = argv.index("--changed")
    if at + 1 == len(argv):
        raise Unavailable("--changed needs a revision or range to pass to the diff")
    return argv[:at] + argv[at + 2 :], argv[at + 1]


def main(argv: list[str]) -> int:
    try:
        paths, spec = split_argv(argv)
        findings = run(paths, spec)
    except Unavailable as error:
        print(f"check-exposure: cannot scope the change: {error.why}", file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
