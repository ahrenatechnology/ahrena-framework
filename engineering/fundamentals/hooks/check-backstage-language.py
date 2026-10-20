#!/usr/bin/env python3
"""Detector for rules/backstage-language.md: names behind the scenes are in English.

Decides two conditions stated in one rule:

    engineering/fundamentals/rules/backstage-language.md
      1. a name a change writes in a name position that is not English by either
         test below
      2. a path a change adds with a segment that is not English by either test

Telling English from any other language in general needs a dictionary or a
model, which is why the predecessor's lex-commit-language was never enforced
(contributing/docs/contribution-flow.md). This detector does not attempt it. It
decides two narrower states that need neither, and leaves the rest to review:

    - the name carries a Portuguese diacritic, one of á à â ã é ê í ó ô õ ú ü ç,
      which no English identifier carries;
    - a segment of the name, split on camelCase, snake_case, kebab-case, dots and
      slashes, is a word on a closed list of Portuguese words that are not also
      English words. The list is asserted, not measured, the way
      rules/debt-markers.md asserts its markers; a word that is also English
      (data, total, valor, tempo, pasta, mural, nova) is left off it, so the list
      can only miss, never misfire on English.

A segment is matched whole, so `portal` is not `porta` and `dadosx` is not
`dados`. Each listed word carries the English it translates to, and the finding
offers it.

The subject is a name, not text. The user's language belongs on screen, and
screen copy lives in string literals and comments, so this detector masks both
before it reads a line and never treats their prose as a name. What it reads is
a fixed set of name positions: a declaration after its keyword, a key or member
at the start of a line, an assignment where the language declares by assigning,
an environment-variable member, a `.env` key, a CSS selector and custom
property, a `className` value, an SQL table and column definition, and a string
literal whose whole shape is a name: an object or JSON key, a route, a URL path
and its parameter names, a CLI option, an UPPER_SNAKE environment-variable name.
A name in any other position is out of reach and stays a reviewer's.

A line carrying an `ADR-N` pointer is exempt, because a name fixed by a contract
this repository does not own (a field of a government API, a column of a
database it only reads) is a decision somebody recorded rather than a slip.
`--exclude <glob>` leaves a path out of the run, for vendored code and recorded
fixtures of such an API.

The condition's subject is a change rather than a file, so the change is a
second, explicit input. `--changed <spec>` passes the spec to a pinned git diff:
condition 1 is decided over the lines that diff adds, and condition 2 over the
paths it adds or renames. With no `--changed`, every line and every path the
run was handed is in scope, the honest default rules/debt-markers.md argues for.
The diff machinery is changes.py's, shared with check-structure.py and
check-comments.py, so the three detectors scope a change the same way.

Report-only. There is no `--fix`: a rename crosses every file that uses the
name, and the English word is the author's choice, not this script's.

Usage:
    python3 engineering/fundamentals/hooks/check-backstage-language.py [path ...]
    python3 engineering/fundamentals/hooks/check-backstage-language.py --changed --cached [path ...]
    python3 engineering/fundamentals/hooks/check-backstage-language.py --changed origin/main...HEAD [path ...]
    python3 engineering/fundamentals/hooks/check-backstage-language.py --exclude 'tests/fixtures/*' [path ...]
"""

from __future__ import annotations

import bisect
import fnmatch
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changes import Unavailable, added_paths, report, scoped, split_argv  # noqa: E402

SKIP_DIRS = frozenset(
    ".git .hg .svn .tox .nox .venv venv .eggs .mypy_cache .pytest_cache"
    " .ruff_cache __pycache__ node_modules build dist vendor target".split()
)

RULE = "backstage-language"


# ----------------------------------------------------------------------------


@dataclass
class Finding:
    where: str
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] condition {self.condition}: {self.message}"


@dataclass
class Source:
    """One file, as text, with the lines this run is scoped to, or None for all."""

    rel: str
    text: str
    family: str
    scope: frozenset[int] | None = None

    def in_scope(self, line: int) -> bool:
        return self.scope is None or line in self.scope


# ----------------------------------------------------------------------------

WORDS = {
    "abrir": "open",
    "agente": "agent",
    "agentes": "agents",
    "ambiente": "environment",
    "arquivo": "file",
    "arquivos": "files",
    "atencao": "attention",
    "ativo": "active",
    "ativos": "active",
    "atualizar": "update",
    "aviso": "warning",
    "avisos": "warnings",
    "botao": "button",
    "botoes": "buttons",
    "buscar": "fetch",
    "busca": "search",
    "calcular": "compute",
    "caminho": "path",
    "caminhos": "paths",
    "carregar": "load",
    "carregando": "loading",
    "cartao": "card",
    "cartoes": "cards",
    "chave": "key",
    "chaves": "keys",
    "cliente": "client",
    "clientes": "clients",
    "coluna": "column",
    "colunas": "columns",
    "configuracao": "settings",
    "configuracoes": "settings",
    "conta": "account",
    "contas": "accounts",
    "conversa": "conversation",
    "conversas": "conversations",
    "criar": "create",
    "custo": "cost",
    "custos": "costs",
    "dados": "data",
    "decisao": "decision",
    "decisoes": "decisions",
    "editar": "edit",
    "endereco": "address",
    "enviar": "send",
    "erro": "error",
    "erros": "errors",
    "evento": "event",
    "eventos": "events",
    "excluir": "delete",
    "falha": "failure",
    "fechar": "close",
    "fila": "queue",
    "grafico": "chart",
    "historico": "history",
    "inicio": "start",
    "listar": "list",
    "lista": "list",
    "maquina": "machine",
    "maquinas": "machines",
    "mensagem": "message",
    "mensagens": "messages",
    "mostrar": "show",
    "nome": "name",
    "nomes": "names",
    "notificacao": "notification",
    "notificacoes": "notifications",
    "nucleo": "core",
    "obter": "get",
    "pagina": "page",
    "paginas": "pages",
    "painel": "panel",
    "pedido": "order",
    "pedidos": "orders",
    "porta": "port",
    "portas": "ports",
    "preco": "price",
    "projeto": "project",
    "projetos": "projects",
    "proximo": "next",
    "quadro": "board",
    "quantidade": "quantity",
    "registro": "record",
    "registros": "records",
    "relatorio": "report",
    "relatorios": "reports",
    "remover": "remove",
    "repositorio": "repository",
    "repositorios": "repositories",
    "resumo": "summary",
    "rotulo": "label",
    "rotulos": "labels",
    "salvar": "save",
    "senha": "password",
    "sessao": "session",
    "sessoes": "sessions",
    "sucesso": "success",
    "tamanho": "size",
    "tarefa": "task",
    "tarefas": "tasks",
    "tela": "screen",
    "telas": "screens",
    "titulo": "title",
    "titulos": "titles",
    "ultimo": "last",
    "usuario": "user",
    "usuarios": "users",
    "validar": "validate",
    "vazio": "empty",
    "verificar": "check",
    "versao": "version",
}

DIACRITIC = re.compile("[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]")

SEGMENT = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+")

POINTER = re.compile(r"(?<![0-9A-Za-z])ADR-[0-9]+")


def foreign(name: str) -> str | None:
    """Why a name is not English by this detector's two tests, or None when it passes."""
    mark = DIACRITIC.search(name)
    if mark:
        return f"it carries the diacritic {mark.group()!r}, which no English name carries"
    for segment in SEGMENT.findall(name):
        english = WORDS.get(segment.lower())
        if english:
            return f"{segment!r} is Portuguese; the English is {english!r}"
    return None


# ----------------------------------------------------------------------------

FAMILY_BY_SUFFIX = {
    **dict.fromkeys(
        "ts mts cts js mjs cjs go rs java kt kts cs swift scala c h cc cpp hpp php dart".split(), "c"
    ),
    **dict.fromkeys("tsx jsx".split(), "jsx"),
    **dict.fromkeys("py pyi rb sh bash zsh toml".split(), "hash"),
    **dict.fromkeys("css scss sass less".split(), "css"),
    **dict.fromkeys("json jsonc json5".split(), "json"),
    **dict.fromkeys("yml yaml".split(), "yaml"),
    "sql": "sql",
}

LINE_COMMENTS = {
    "c": ("//",),
    "jsx": ("//",),
    "hash": ("#",),
    "css": ("//",),
    "json": ("//",),
    "yaml": ("#",),
    "sql": ("--",),
    "env": ("#",),
}

BLOCK_COMMENTS = {
    "c": (("/*", "*/"),),
    "jsx": (("/*", "*/"),),
    "css": (("/*", "*/"),),
    "json": (("/*", "*/"),),
    "sql": (("/*", "*/"),),
}

QUOTES = {
    "c": ("`", '"', "'"),
    "jsx": ("`", '"', "'"),
    "hash": ('"""', "'''", '"', "'"),
    "css": ('"', "'"),
    "json": ('"',),
    "yaml": ('"', "'"),
    "sql": ("'",),
    "env": ('"', "'"),
}

MULTILINE = frozenset(("`", '"""', "'''"))


def family_of(path: Path) -> str | None:
    """The lexical family a file is read as, or None when only its path is checked."""
    name = path.name
    if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
        return "env"
    return FAMILY_BY_SUFFIX.get(path.suffix.lstrip(".").lower())


@dataclass(frozen=True)
class Literal:
    """A string literal: its line, its span in the text, and its body."""

    line: int
    start: int
    end: int
    body: str


def _comment_end(text: str, at: int, family: str) -> int | None:
    """Where a comment that opens at `at` ends, or None when none opens there."""
    for marker in LINE_COMMENTS.get(family, ()):
        if text.startswith(marker, at):
            close = text.find("\n", at)
            return len(text) if close < 0 else close
    for opener, closer in BLOCK_COMMENTS.get(family, ()):
        if text.startswith(opener, at):
            close = text.find(closer, at + len(opener))
            return len(text) if close < 0 else close + len(closer)
    return None


def _string_end(text: str, at: int, quote: str) -> int:
    """The offset just past the literal whose body starts at `at`.

    A backslash escapes the next character. A single-line quote that meets a
    newline ends there, so one stray apostrophe masks a line, not a file.
    """
    while at < len(text):
        if text[at] == "\\":
            at += 2
        elif text.startswith(quote, at):
            return at + len(quote)
        elif text[at] == "\n" and quote not in MULTILINE:
            return at
        else:
            at += 1
    return len(text)


def _blank(chars: list[str], start: int, end: int) -> None:
    for at in range(start, min(end, len(chars))):
        if chars[at] != "\n":
            chars[at] = " "


def mask(text: str, family: str) -> tuple[str, list[Literal]]:
    """The text with comments and string bodies blanked, and the literals found.

    Blanking keeps every offset and every newline, so a line number read from
    the masked text is the line number in the file. Quote characters are kept,
    so a reader can tell where a literal stood.
    """
    chars = list(text)
    newlines = [at for at, char in enumerate(text) if char == "\n"]
    literals: list[Literal] = []
    quotes = QUOTES.get(family, ())
    at = 0
    while at < len(text):
        close = _comment_end(text, at, family)
        if close is not None:
            _blank(chars, at, close)
            at = close
            continue
        quote = next((q for q in quotes if text.startswith(q, at)), None)
        if quote is None:
            at += 1
            continue
        end = _string_end(text, at + len(quote), quote)
        inner = max(end - len(quote), at + len(quote))
        literals.append(Literal(bisect.bisect(newlines, at) + 1, at, end, text[at + len(quote) : inner]))
        _blank(chars, at + len(quote), inner)
        at = max(end, at + 1)
    return "".join(chars), literals


# ----------------------------------------------------------------------------

NAME = r"(?!\d)[$\w]+"

DECLARATION = re.compile(
    r"\b(?:const|let|var|function|class|interface|type|enum|def|struct|trait|fn|func|val|fun"
    rf"|namespace|module|record)\s+\*?\s*({NAME})"
)

METHOD = re.compile(rf"\bfunc\s*\([^)]*\)\s*({NAME})")

KEY_PREFIX = (
    r"^\s*(?:-\s+)?(?:(?:export|readonly|public|private|protected|static|declare|abstract|async"
    r"|override)\s+)*"
)

KEY = re.compile(rf"{KEY_PREFIX}({NAME})\s*\??\s*:(?!:)")

LOWER_KEY = re.compile(rf"{KEY_PREFIX}((?![A-Z]){NAME})\s*\??\s*:(?!:)")

ASSIGN = re.compile(rf"^\s*(?:export\s+)?({NAME})\s*=(?!=)")

MEMBER_ASSIGN = re.compile(rf"^\s*(?:self|this)\.({NAME})\s*=(?!=)")

ENV_MEMBER = re.compile(rf"\benv\.({NAME})")

CUSTOM_PROPERTY = re.compile(r"^\s*(--[\w-]+)\s*:")

SELECTOR = re.compile(r"(?<![\w-])[.#](-?(?!\d)[\w-]+)")

SQL_TYPES = (
    "int|integer|bigint|smallint|serial|bigserial|text|varchar|char|character|uuid|bool|boolean"
    "|timestamp|timestamptz|date|time|numeric|decimal|real|double|float|json|jsonb|bytea|blob"
)

SQL_OBJECT = re.compile(
    r"(?i)\b(?:create|alter)\s+(?:or\s+replace\s+)?(?:temporary\s+|temp\s+|unique\s+|materialized\s+)?"
    r"(?:table|view|index|type|schema|sequence|function)\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)"
)

SQL_COLUMN = re.compile(rf"(?i)^\s*\"?({NAME})\"?\s+(?:{SQL_TYPES})\b")

SQL_ADD = re.compile(rf"(?i)\badd\s+column\s+(?:if\s+not\s+exists\s+)?\"?({NAME})")

LINE_READERS = {
    "c": (DECLARATION, METHOD, KEY, MEMBER_ASSIGN, ENV_MEMBER),
    "jsx": (DECLARATION, LOWER_KEY, MEMBER_ASSIGN, ENV_MEMBER),
    "hash": (DECLARATION, KEY, ASSIGN, MEMBER_ASSIGN, ENV_MEMBER),
    "css": (KEY, CUSTOM_PROPERTY),
    "json": (),
    "yaml": (KEY,),
    "sql": (SQL_OBJECT, SQL_COLUMN, SQL_ADD),
    "env": (ASSIGN,),
}


def _selectors(line: str) -> list[str]:
    """The class and id names in the selector part of a CSS line."""
    if "{" in line:
        head = line.split("{", 1)[0]
    elif line.rstrip().endswith(","):
        head = line
    else:
        return []
    return SELECTOR.findall(head)


def line_names(line: str, family: str) -> list[str]:
    """Every name in a name position on one masked line."""
    names = [match.group(1) for reader in LINE_READERS[family] for match in reader.finditer(line)]
    if family == "css":
        names.extend(_selectors(line))
    return names


# ----------------------------------------------------------------------------

ROUTE = re.compile(r"^/[\w\-.:{}\[\]$*@/]*(?:\?\S*)?$")

URL = re.compile(r"^https?://[^/\s?#]+(/\S*)$")

OPTION = re.compile(r"^--((?!\d)[\w][\w-]*)(?:=.*)?$")

ENV_NAME = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")

CLASS_ATTRIBUTE = re.compile(r"\bclass(?:Name)?\s*=\s*\{?\s*$")

PARAMETER = re.compile(r"[?&]([^=&#]+)")


def _route_names(route: str) -> list[str]:
    """A route's path, and the names of its query parameters, never their values."""
    path, _, query = route.partition("?")
    return [path, *PARAMETER.findall("?" + query)] if query else [path]


def _shaped_names(body: str) -> list[str]:
    """The names a literal is, when its whole shape is a name and not text."""
    if ROUTE.match(body) and re.search("[A-Za-z]", body):
        return _route_names(body)
    url = URL.match(body)
    if url:
        return _route_names(url.group(1))
    option = OPTION.match(body)
    if option:
        return [option.group(1)]
    return [body] if ENV_NAME.match(body) else []


def _neighbours(masked: str, literal: Literal) -> tuple[str, str]:
    """The non-blank character before a literal and after it, or '' at an edge."""
    before = masked[: literal.start].rstrip(" \t")
    after = masked[literal.end :].lstrip(" \t")
    return (before[-1:] or "\n"), after[:1]


def literal_names(masked: str, literal: Literal) -> list[str]:
    """The names a string literal holds: a key, a class list, or a name-shaped body."""
    before, after = _neighbours(masked, literal)
    if after == ":" and before in "{,\n":
        return [literal.body]
    line_start = masked.rfind("\n", 0, literal.start) + 1
    if CLASS_ATTRIBUTE.search(masked[line_start : literal.start]):
        return literal.body.split()
    return _shaped_names(literal.body)


def names(src: Source) -> Iterable[tuple[int, str]]:
    """Each (line, name) in a name position of the file, in or out of scope."""
    masked, literals = mask(src.text, src.family)
    for number, line in enumerate(masked.split("\n"), 1):
        for name in line_names(line, src.family):
            yield number, name
    for literal in literals:
        for name in literal_names(masked, literal):
            yield literal.line, name


def check_names(src: Source, findings: list[Finding]) -> None:
    raw = src.text.split("\n")
    seen: set[tuple[int, str]] = set()
    for number, name in names(src):
        if not src.in_scope(number) or (number, name) in seen:
            continue
        seen.add((number, name))
        if POINTER.search(raw[number - 1]):
            continue
        reason = foreign(name)
        if reason:
            findings.append(
                Finding(
                    f"{src.rel}:{number}",
                    RULE,
                    1,
                    f"{name!r} is a name behind the scenes, and {reason}. Name it in English and "
                    "keep the user's language in the text they read; a name a contract this "
                    "repository does not own fixes takes an ADR-N on its line",
                )
            )


def check_path(rel: str, findings: list[Finding]) -> None:
    for part in rel.split("/"):
        reason = foreign(part)
        if reason:
            findings.append(
                Finding(
                    rel,
                    RULE,
                    2,
                    f"the path segment {part!r} is a name behind the scenes, and {reason}. "
                    "Name the file or directory in English",
                )
            )
            return


# ----------------------------------------------------------------------------



# ----------------------------------------------------------------------------



EXCLUDE_FLAG = "--exclude"


def split_excludes(argv: list[str]) -> tuple[list[str], list[str]]:
    """The arguments without each `--exclude <glob>` pair, and the globs."""
    rest: list[str] = []
    globs: list[str] = []
    at = 0
    while at < len(argv):
        if argv[at] != EXCLUDE_FLAG:
            rest.append(argv[at])
            at += 1
            continue
        if at + 1 == len(argv):
            raise Unavailable(f"{EXCLUDE_FLAG} needs a glob, matched against each path as shown")
        globs.append(argv[at + 1])
        at += 2
    return rest, globs


# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Walked:
    """A file the run reaches, and the path its names are read from."""

    path: Path
    rel: str


def _shown(path: Path, root: Path, base: Path) -> str:
    """The path as the reader sees it: from the working directory, or else the root."""
    for anchor in (base, root.parent):
        try:
            return path.relative_to(anchor).as_posix()
        except ValueError:
            continue
    return path.name


def sources(roots: list[Path], base: Path, globs: list[str]) -> list[Walked]:
    found: list[Walked] = []
    for root in roots:
        candidates = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in candidates:
            rel = _shown(path, root, base)
            if not SKIP_DIRS.isdisjoint(Path(rel).parts):
                continue
            if not any(fnmatch.fnmatch(rel, glob) for glob in globs):
                found.append(Walked(path, rel))
    return found


def load(walked: Walked, family: str, scope: frozenset[int] | None) -> Source | None:
    """The file as text, or None once the reason it could not be read is reported."""
    try:
        return Source(walked.rel, walked.path.read_text(encoding="utf-8"), family, scope)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"{walked.rel}\n    skipped, this file could not be read: {exc}", file=sys.stderr)
        return None



@dataclass(frozen=True)
class Run:
    """What the arguments resolve to: the files, and what of each is in scope."""

    walked: tuple[Walked, ...]
    lines: Callable[[Path], frozenset[int] | None]
    path_in_scope: Callable[[Path], bool]


def read(argv: list[str]) -> Run:
    base = Path.cwd()
    rest, globs = split_excludes(argv)
    rest, spec = split_argv(rest)
    walked = sources([Path(a).resolve() for a in rest] or [base], base, globs)
    if spec is None:
        return Run(tuple(walked), lambda _path: None, lambda _path: True)
    scope = scoped(spec, [w.path for w in walked])
    added = added_paths(spec)
    return Run(tuple(walked), lambda path: scope.get(path, frozenset()), lambda path: path in added)


def run_report(run: Run) -> int:
    findings: list[Finding] = []
    checked = 0
    unread = 0
    for walked in run.walked:
        if run.path_in_scope(walked.path):
            check_path(walked.rel, findings)
        family = family_of(walked.path)
        source = None if family is None else load(walked, family, run.lines(walked.path))
        if family is not None and source is None:
            unread += 1
            continue
        if source is not None:
            check_names(source, findings)
        checked += 1
    return report(findings, checked, unread)


def main(argv: list[str]) -> int:
    try:
        run = read(argv[1:])
    except Unavailable as exc:
        print(f"{RULE}: {exc}", file=sys.stderr)
        return 2
    return run_report(run)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
