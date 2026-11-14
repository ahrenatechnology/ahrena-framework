#!/usr/bin/env python3
"""Detector for the Terraform rules of the ahrena-engineering-terraform plugin.

Decides, over a repository, every condition of these rules that a reader of
the source can decide without running Terraform:

    state              1-3   no state, plan or .terraform in the repository;
                             a root module on a remote backend; locking left on
    secrets            1-4   no secret in a variable default, an argument
                             literal or a versioned .tfvars file
    outputs            1-3   a sensitive output marked so; no root output of a
                             whole object; no pipeline printing outputs
    pinning            1-5   required_version, versioned providers, exact
                             module versions, the lock file beside the root
    module-boundaries  1-3   no cycle, no call into a root configuration, no
                             provider or backend in a reusable module
    test-placement     1     a test file beside every reusable module

The conditions that need a backend's settings, a reader or a running cloud are
not here; each rule says which those are and who decides them.

The HCL reader is written against the standard library because the hook must
run on a machine with nothing installed. It reads blocks, labels and
attributes, and keeps an attribute's value as source text: every condition
here is a shape in that text, never an evaluated value. It understands
comments, quoted strings with nested interpolation, and heredocs, which is
everything that can make a brace or a `=` mean something other than
structure. JSON configuration (`.tf.json`) is not read.

"In the repository" means tracked or about to be. Inside a git work tree the
files considered are the ones git lists as tracked or as untracked and not
ignored; outside one, every file under the root.

Usage:
    python3 engineering/terraform/hooks/check-terraform.py [root ...]
"""

from __future__ import annotations

import posixpath
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator, Optional

SKIP_PARTS = frozenset({".git", "node_modules", "vendor"})
EXAMPLE_PARTS = frozenset({"examples", "example", "tests", "test"})
CONFIG_SUFFIXES = (".tf", ".tofu")
TEST_FILE = re.compile(r"\.(tftest\.hcl|tftest\.json|tofutest\.hcl)$")
PIPELINE_SUFFIXES = (".sh", ".bash", ".zsh", ".yml", ".yaml", ".mk", ".ps1")
PIPELINE_NAMES = frozenset({"Makefile", "Justfile", "Taskfile", "Jenkinsfile"})

STATE_FILE = re.compile(r"(^|/)([^/]*\.tfstate(\.[^/]*)?|\.terraform\.tfstate\.lock\.info|[^/]*\.tfplan)$")
LOCK_OFF = re.compile(r"-lock=false\b")
PRINTS_OUTPUTS = re.compile(r"\b(terraform|tofu)(\s+-\S+)*\s+(output\b[^|>]*\s-(json|raw)\b|show\b[^|>]*\s-json\b)")
CAPTURED = re.compile(r"[>|`]|\$\(")

SECRET_WORDS = (
    "password|passwd|passphrase|secret|token|credentials?|private_key|api_key|apikey|access_key"
    "|connection_string|conn_str"
)
SECRET_NAME = re.compile(rf"(^|_)({SECRET_WORDS})(_|$)")
NOT_A_SECRET = re.compile(
    r"_(ids?|arns?|names?|versions?|length|ttl|type|path|paths|enabled|count|days|rotation|policy"
    r"|url|uri|endpoint|header|prefix|suffix)$"
)
SENSITIVE_NAME = re.compile(rf"(^|_)({SECRET_WORDS}|policy|kubeconfig|kube_config|dsn)(_|$)")
LOCATOR = re.compile(r"(^|_)(ids?|arns?|names?|versions?)$")
URL_CREDENTIAL = re.compile(r"[a-z][a-z0-9+.-]*://[^\s/\"@]+@")
REFERENCE = re.compile(r"\b[a-z][a-z0-9_]*(?:\.[A-Za-z0-9_-]+|\[[^\]]*\])+")
NAMED_ROOTS = frozenset({"var", "local", "module"})
WHOLE_OBJECT = re.compile(
    r"^(?:(?:data\.)?[a-z][a-z0-9]*_[a-z0-9_]*\.[A-Za-z0-9_-]+|module\.[A-Za-z0-9_-]+)(?:\[[^\]]*\])?$"
)
STRING_LITERAL = re.compile(r'^"(?:[^"\\$%]|\\.)+"$')

REGISTRY_SOURCE = re.compile(r"^([A-Za-z0-9.-]+\.[A-Za-z]{2,}/)?[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+$")
GIT_SOURCE = re.compile(r"^(git::|hg::|git@|github\.com/|bitbucket\.org/)")
EXACT_VERSION = re.compile(r"^=?\s*v?\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")
GIT_REF = re.compile(r"[?&]ref=([^&]+)")
BRANCH_NAMES = frozenset({"main", "master", "develop", "development", "dev", "trunk", "HEAD"})
CONSTRAINT_OPERATOR = re.compile(r"\s*(~>|>=|<=|!=|>|<|=)?")
UPPER_BOUNDS = frozenset({None, "~>", "<", "<=", "="})
BUILTIN_PROVIDERS = frozenset({"terraform"})

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
HEREDOC = re.compile(r"<<-?([A-Za-z_][A-Za-z0-9_]*)[ \t]*\n")
OPENERS = frozenset("([{")
CLOSERS = frozenset(")]}")


# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    where: str
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] {self.rule} condition {self.condition}: {self.message}"


@dataclass(frozen=True)
class Token:
    kind: str
    line: int
    start: int
    end: int


@dataclass(frozen=True)
class Attr:
    value: str
    line: int


@dataclass
class Body:
    attrs: dict[str, Attr] = field(default_factory=dict)
    blocks: list["Block"] = field(default_factory=list)


@dataclass
class Block:
    kind: str
    labels: list[str]
    line: int
    body: Body

    @property
    def name(self) -> str:
        return self.labels[0] if self.labels else ""


@dataclass
class Source:
    text: str
    tokens: list[Token]

    def word(self, index: int) -> str:
        token = self.tokens[index]
        return self.text[token.start : token.end]


@dataclass
class TfFile:
    rel: str
    body: Body


@dataclass
class Module:
    path: str
    files: list[TfFile] = field(default_factory=list)

    def blocks(self, kind: str) -> Iterator[tuple[TfFile, Block]]:
        for tf in self.files:
            for block in tf.body.blocks:
                if block.kind == kind:
                    yield tf, block

    def settings(self, kind: str) -> Iterator[tuple[TfFile, Block]]:
        """The blocks of `kind` nested in this module's `terraform` blocks."""
        for tf, terraform in self.blocks("terraform"):
            for block in terraform.body.blocks:
                if block.kind == kind:
                    yield tf, block


@dataclass
class Repo:
    root: Path
    paths: list[str]
    modules: dict[str, Module]
    children: set[str] = field(default_factory=set)
    findings: list[Finding] = field(default_factory=list)

    def report(self, where: str, rule: str, condition: int, message: str) -> None:
        self.findings.append(Finding(where, rule, condition, message))


def roots(repo: Repo) -> list[Module]:
    return [m for p, m in sorted(repo.modules.items()) if p not in repo.children and not is_example(p)]


def reusable(repo: Repo) -> list[Module]:
    return [m for p, m in sorted(repo.modules.items()) if p in repo.children and not is_example(p)]


def configurations(repo: Repo) -> list[Module]:
    return roots(repo) + reusable(repo)


def where_of(module: Module) -> str:
    return f"{module.path}/"


# ---------------------------------------------------------------------------


def lex(text: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1
    while index < len(text):
        end, kind = next_token(text, index)
        if kind:
            tokens.append(Token(kind, line, index, end))
        line += text.count("\n", index, end)
        index = end
    return tokens


def next_token(text: str, index: int) -> tuple[int, str]:
    """Where the token at `index` ends, and its kind; an empty kind is skipped."""
    char = text[index]
    if char == "\n":
        return index + 1, "newline"
    if char in " \t\r":
        return index + 1, ""
    if char == "#" or text.startswith("//", index):
        end = text.find("\n", index)
        return (end if end >= 0 else len(text)), ""
    if text.startswith("/*", index):
        end = text.find("*/", index + 2)
        return (end + 2 if end >= 0 else len(text)), ""
    if char == '"':
        return string_end(text, index), "string"
    heredoc = HEREDOC.match(text, index)
    if heredoc:
        return heredoc_end(text, heredoc), "heredoc"
    word = IDENT.match(text, index)
    if word:
        return word.end(), "ident"
    return index + 1, "punct"


def string_end(text: str, index: int) -> int:
    """The index past the quoted string opening at `index`, through any interpolation."""
    position = index + 1
    depth = 0
    while position < len(text):
        char = text[position]
        if char == "\\":
            position += 2
            continue
        if depth == 0 and char in '"\n':
            return position + (char == '"')
        if text.startswith(("${", "%{"), position):
            depth += 1
            position += 2
            continue
        if depth and char == '"':
            position = string_end(text, position)
            continue
        depth += (char == "{") - (char == "}") if depth else 0
        position += 1
    return position


def heredoc_end(text: str, opening: re.Match[str]) -> int:
    marker = re.compile(rf"^[ \t]*{re.escape(opening.group(1))}[ \t]*$", re.M)
    closing = marker.search(text, opening.end())
    return closing.end() if closing else len(text)


def parse(text: str) -> Body:
    source = Source(text, lex(text))
    body, _ = parse_body(source, 0)
    return body


def parse_body(source: Source, position: int) -> tuple[Body, int]:
    body = Body()
    while position < len(source.tokens):
        if source.word(position) == "}":
            return body, position + 1
        if source.tokens[position].kind != "ident":
            position += 1
            continue
        position = parse_statement(source, position, body)
    return body, position


def parse_statement(source: Source, position: int, body: Body) -> int:
    """Read the attribute or block whose name is at `position` into `body`."""
    after = position + 1
    while after < len(source.tokens) and source.tokens[after].kind in ("string", "ident"):
        after += 1
    following = source.word(after) if after < len(source.tokens) else ""
    if following == "=" and after == position + 1:
        value, end = parse_expression(source, after + 1)
        body.attrs[source.word(position)] = Attr(value, source.tokens[position].line)
        return end
    if following == "{":
        labels = [source.word(i).strip('"') for i in range(position + 1, after)]
        inner, end = parse_body(source, after + 1)
        body.blocks.append(Block(source.word(position), labels, source.tokens[position].line, inner))
        return end
    return position + 1


def parse_expression(source: Source, position: int) -> tuple[str, int]:
    """The source text of the expression starting at `position`, and where it ends."""
    start = position
    depth = 0
    while position < len(source.tokens):
        word = source.word(position)
        if depth == 0 and (source.tokens[position].kind == "newline" or word in CLOSERS):
            break
        depth += (word in OPENERS) - (word in CLOSERS)
        position += 1
    if position == start:
        return "", position
    first, last = source.tokens[start], source.tokens[position - 1]
    return source.text[first.start : last.end].strip(), position


def walk(body: Body) -> Iterator[Block]:
    for block in body.blocks:
        yield block
        yield from walk(block.body)


# ---------------------------------------------------------------------------


def is_example(path: str) -> bool:
    return any(part in EXAMPLE_PARTS for part in PurePosixPath(path).parts)


def skipped(path: str) -> bool:
    return any(part in SKIP_PARTS for part in PurePosixPath(path).parts)


def git_files(root: Path) -> Optional[list[str]]:
    """The files git holds or would add under `root`, or None outside a work tree."""
    if shutil.which("git") is None:
        return None
    command = ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return [path for path in result.stdout.split("\0") if path and (root / path).is_file()]


def inventory(root: Path) -> list[str]:
    listed = git_files(root)
    if listed is None:
        listed = [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()]
    return sorted(path for path in listed if not skipped(path))


UNREADABLE: list[str] = []


def read(root: Path, rel: str) -> str:
    """The file's text; a file that cannot be read is recorded, and the run fails on it."""
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        if rel not in UNREADABLE:
            UNREADABLE.append(rel)
        return ""


def load_modules(root: Path, paths: list[str]) -> dict[str, Module]:
    modules: dict[str, Module] = {}
    for rel in paths:
        if not rel.endswith(CONFIG_SUFFIXES) or ".terraform" in PurePosixPath(rel).parts:
            continue
        directory = posixpath.dirname(rel) or "."
        module = modules.setdefault(directory, Module(directory))
        module.files.append(TfFile(rel, parse(read(root, rel))))
    return modules


def literal(value: str) -> str:
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else ""


def local_calls(module: Module) -> Iterator[tuple[TfFile, Block, str]]:
    """Each module call with a local source, and the directory it resolves to."""
    for tf, block in module.blocks("module"):
        source = literal(block.body.attrs.get("source", Attr("", 0)).value)
        if source.startswith(("./", "../")):
            yield tf, block, posixpath.normpath(posixpath.join(module.path, source))


def build(root: Path) -> Repo:
    paths = inventory(root)
    repo = Repo(root, paths, load_modules(root, paths))
    called = {target for module in repo.modules.values() for _, _, target in local_calls(module)}
    repo.children.update(path for path in called if path in repo.modules and not backend_kinds(repo.modules[path]))
    repo.children.update(path for path in repo.modules if "modules" in PurePosixPath(path).parts)
    return repo


def pipeline_lines(repo: Repo) -> Iterator[tuple[str, str]]:
    """Each line of every script and pipeline file, as (where, line)."""
    for rel in repo.paths:
        name = PurePosixPath(rel).name
        if not (rel.endswith(PIPELINE_SUFFIXES) or name in PIPELINE_NAMES) or ".terraform" in rel:
            continue
        for number, line in enumerate(read(repo.root, rel).splitlines(), start=1):
            yield f"{rel}:{number}", line


def marked(body: Body) -> bool:
    return any(body.attrs.get(key, Attr("", 0)).value == "true" for key in ("sensitive", "ephemeral"))


def backend_kinds(module: Module) -> list[str]:
    kinds = [block.name for _, block in module.settings("backend")]
    return kinds + ["cloud" for _ in module.settings("cloud")]


# ---------------------------------------------------------------------------


def dot_terraform(path: str) -> Optional[str]:
    parts = PurePosixPath(path).parts
    if ".terraform" not in parts:
        return None
    return "/".join(parts[: parts.index(".terraform") + 1]) + "/"


def check_state_files(repo: Repo) -> None:
    reported: set[str] = set()
    for path in repo.paths:
        directory = dot_terraform(path)
        if directory is None and STATE_FILE.search(path):
            repo.report(path, "state", 1, "state and saved plans hold every value in plain text; remove the file "
                        "from the repository and ignore it (`*.tfstate`, `*.tfstate.*`, `*.tfplan`)")
        elif directory is not None and directory not in reported:
            reported.add(directory)
            repo.report(directory, "state", 1, "the working directory holds backend settings and may hold "
                        "credentials; remove it from the repository and ignore `.terraform/`")


def check_backends(repo: Repo) -> None:
    for module in roots(repo):
        kinds = backend_kinds(module)
        if not kinds:
            repo.report(where_of(module), "state", 2, "a root module declares no backend, so its state is a local "
                        "plaintext file; declare a remote backend that locks, or a `cloud` block")
        elif "local" in kinds:
            repo.report(where_of(module), "state", 2, "the `local` backend keeps state as a plaintext file on one "
                        "machine; declare a remote backend that locks")


def check_lock_flags(repo: Repo) -> None:
    for where, line in pipeline_lines(repo):
        if LOCK_OFF.search(line):
            repo.report(where, "state", 3, "`-lock=false` lets two runs write the same state; remove the flag")


# ---------------------------------------------------------------------------


def secret_named(name: str) -> bool:
    lowered = name.lower()
    return bool(SECRET_NAME.search(lowered)) and not NOT_A_SECRET.search(lowered)


def check_secret_variables(repo: Repo) -> None:
    for module in repo.modules.values():
        for tf, block in module.blocks("variable"):
            if not secret_named(block.name):
                continue
            where = f"{tf.rel}:{block.line}"
            default = block.body.attrs.get("default")
            if default is not None and default.value != "null":
                repo.report(f"{tf.rel}:{default.line}", "secrets", 1, f'variable "{block.name}" carries a default; a secret has '
                            "none, and arrives from the environment or a secret store")
            if not marked(block.body):
                repo.report(where, "secrets", 2, f'variable "{block.name}" names a secret and is not marked '
                            "`sensitive = true` (or `ephemeral = true`)")


def check_literal_credentials(repo: Repo) -> None:
    for module in repo.modules.values():
        for tf in module.files:
            for block in walk(tf.body):
                report_literals(repo, tf.rel, block.body, 3)


def report_literals(repo: Repo, rel: str, body: Body, condition: int) -> None:
    for name, attr in body.attrs.items():
        if secret_named(name) and STRING_LITERAL.match(attr.value):
            repo.report(f"{rel}:{attr.line}", "secrets", condition, f"`{name}` is given a literal; take it "
                        "from a sensitive or ephemeral variable, an ephemeral resource or a secret store")


def check_tfvars(repo: Repo) -> None:
    for rel in repo.paths:
        if rel.endswith(".tfvars"):
            report_literals(repo, rel, parse(read(repo.root, rel)), 4)


# ---------------------------------------------------------------------------


def sensitive_name(name: str) -> bool:
    lowered = name.lower()
    return bool(SENSITIVE_NAME.search(lowered)) and not LOCATOR.search(lowered)


def sensitive_reference(chain: str, sensitive_vars: set[str]) -> bool:
    segments = [part for part in re.sub(r"\[[^\]]*\]", "", chain).split(".") if part]
    if segments and segments[0] == "data":
        segments = segments[1:]
    if len(segments) < 2:
        return False
    if segments[0] in NAMED_ROOTS:
        hidden = segments[0] == "var" and segments[1] in sensitive_vars
        return hidden or any(sensitive_name(part) for part in segments[1:])
    final = segments[-1] if len(segments) > 2 else ""
    if final and sensitive_name(final):
        return True
    return bool(final) and sensitive_name(segments[0]) and not LOCATOR.search(final)


def carries(block: Block, sensitive_vars: set[str]) -> str:
    """What makes this output sensitive, or an empty string."""
    if sensitive_name(block.name):
        return "a name that says it is sensitive"
    value = block.body.attrs.get("value", Attr("", 0)).value
    if URL_CREDENTIAL.search(value):
        return "a connection string with credentials"
    for chain in REFERENCE.findall(value):
        if sensitive_reference(chain, sensitive_vars):
            return f"`{chain}`"
    return ""


def check_output_sensitivity(repo: Repo) -> None:
    for module in repo.modules.values():
        hidden = {block.name for _, block in module.blocks("variable") if marked(block.body)}
        for tf, block in module.blocks("output"):
            reason = "" if marked(block.body) else carries(block, hidden)
            if reason:
                repo.report(f"{tf.rel}:{block.line}", "outputs", 1, f'output "{block.name}" carries {reason} '
                            "and is not marked `sensitive = true`")


def check_whole_objects(repo: Repo) -> None:
    for module in roots(repo):
        for tf, block in module.blocks("output"):
            value = block.body.attrs.get("value", Attr("", 0)).value
            if WHOLE_OBJECT.match(value):
                repo.report(f"{tf.rel}:{block.line}", "outputs", 2, f'output "{block.name}" exports the whole '
                            f"`{value}`; export the named attributes a consumer reads")


def check_printed_outputs(repo: Repo) -> None:
    for where, line in pipeline_lines(repo):
        if PRINTS_OUTPUTS.search(line) and not CAPTURED.search(line):
            repo.report(where, "outputs", 3, "this prints sensitive values in plain text to the log; write it "
                        "to a file the job keeps private, or read the one value the step needs")


# ---------------------------------------------------------------------------


def provider_requirements(module: Module) -> dict[str, Attr]:
    found: dict[str, Attr] = {}
    for _, block in module.settings("required_providers"):
        found.update(block.body.attrs)
    return found


def constraint_of(requirement: Attr) -> str:
    if requirement.value.startswith('"'):
        return literal(requirement.value)
    found = re.search(r'\bversion\s*=\s*"([^"]*)"', requirement.value)
    return found.group(1) if found else ""


def upper_bounded(constraint: str) -> bool:
    items = [item for item in constraint.split(",") if item.strip()]
    return any(CONSTRAINT_OPERATOR.match(item).group(1) in UPPER_BOUNDS for item in items)  # type: ignore[union-attr]


def used_providers(module: Module) -> set[str]:
    used = {block.name.split("_")[0] for kind in ("resource", "data", "ephemeral") for _, block in module.blocks(kind)}
    used.update(block.name for _, block in module.blocks("provider"))
    return {name for name in used if name and name not in BUILTIN_PROVIDERS}


def check_required_version(repo: Repo) -> None:
    for module in configurations(repo):
        if not any("required_version" in block.body.attrs for _, block in module.blocks("terraform")):
            repo.report(where_of(module), "pinning", 1, "no `required_version` in a `terraform` block; state the "
                        "Terraform versions this configuration was written for")


def check_provider_versions(repo: Repo) -> None:
    for module in configurations(repo):
        requirements = provider_requirements(module)
        for name in sorted(used_providers(module) - set(requirements)):
            repo.report(where_of(module), "pinning", 2, f"provider `{name}` is used and not declared in "
                        "`required_providers` with a source and a version")
        for name, requirement in sorted(requirements.items()):
            check_constraint(repo, module, name, requirement)


def check_constraint(repo: Repo, module: Module, name: str, requirement: Attr) -> None:
    constraint = constraint_of(requirement)
    where = f"{module.path}/ (line {requirement.line})"
    if not constraint:
        repo.report(where, "pinning", 2, f"provider `{name}` has no version constraint")
    elif module.path in repo.children and upper_bounded(constraint):
        repo.report(where, "pinning", 3, f"reusable module {where_of(module)} caps provider `{name}` at "
                    f'"{constraint}"; a reusable module states only its minimum, with `>=`')
    elif module.path not in repo.children and not upper_bounded(constraint):
        repo.report(where, "pinning", 3, f'root module caps provider `{name}` nowhere ("{constraint}"); '
                    "use `~>` so an upgrade is a change somebody makes")


def module_pin_problem(block: Block) -> str:
    """Why this module call is not pinned, or an empty string."""
    source = literal(block.body.attrs.get("source", Attr("", 0)).value)
    version = literal(block.body.attrs.get("version", Attr("", 0)).value)
    if not GIT_SOURCE.match(source):
        registry = REGISTRY_SOURCE.match(source) and not EXACT_VERSION.match(version)
        return f'registry module "{source}" needs an exact `version`, not "{version}"' if registry else ""
    ref = GIT_REF.search(source)
    if ref is None:
        return f'"{source}" has no `?ref=`, so it follows the default branch'
    if ref.group(1) in BRANCH_NAMES:
        return f'"{source}" is pinned to the branch `{ref.group(1)}`; pin a tag or a commit'
    return ""


def check_module_pins(repo: Repo) -> None:
    for module in repo.modules.values():
        for tf, block in module.blocks("module"):
            problem = module_pin_problem(block)
            line = block.body.attrs.get("source", Attr("", block.line)).line
            if problem:
                repo.report(f"{tf.rel}:{line}", "pinning", 4, problem)


def locked_sources(repo: Repo, lock: str) -> set[str]:
    """The provider sources a lock file records, as `namespace/type` in lower case."""
    blocks = parse(read(repo.root, lock)).blocks
    return {"/".join(block.name.lower().split("/")[-2:]) for block in blocks if block.kind == "provider"}


def declared_sources(module: Module) -> set[str]:
    sources = set()
    for name, requirement in provider_requirements(module).items():
        found = re.search(r'\bsource\s*=\s*"([^"]*)"', requirement.value)
        source = found.group(1) if found else f"hashicorp/{name}"
        sources.add("/".join(source.lower().split("/")[-2:]))
    return sources


def check_lock_file(repo: Repo) -> None:
    for module in roots(repo):
        if not (provider_requirements(module) or used_providers(module)):
            continue
        lock = posixpath.normpath(posixpath.join(module.path, ".terraform.lock.hcl"))
        if lock not in repo.paths:
            repo.report(where_of(module), "pinning", 5, "no `.terraform.lock.hcl` beside this root module; run "
                        "`terraform init` and commit the lock file it writes")
            continue
        for source in sorted(declared_sources(module) - locked_sources(repo, lock)):
            repo.report(lock, "pinning", 5, f"the lock file records no `{source}`; run `terraform init` "
                        "and commit the lock file it rewrites")


# ---------------------------------------------------------------------------


def call_graph(repo: Repo) -> dict[str, list[tuple[str, str]]]:
    """Each module's local calls, as (target, where), restricted to modules that exist."""
    graph: dict[str, list[tuple[str, str]]] = {path: [] for path in repo.modules}
    for path, module in repo.modules.items():
        for tf, block, target in local_calls(module):
            if target in repo.modules:
                graph[path].append((target, f"{tf.rel}:{block.line}"))
    return graph


def visit(graph: dict[str, list[tuple[str, str]]], node: str, state: dict[str, int], back: list[str]) -> None:
    state[node] = 1
    for target, where in graph[node]:
        if state.get(target) == 1:
            back.append(f"{where}  {node} -> {target}")
        elif target not in state:
            visit(graph, target, state, back)
    state[node] = 2


def check_cycles(repo: Repo) -> None:
    graph = call_graph(repo)
    state: dict[str, int] = {}
    back: list[str] = []
    for node in sorted(graph):
        if node not in state:
            visit(graph, node, state, back)
    for edge in back:
        where, _, path = edge.partition("  ")
        repo.report(where, "module-boundaries", 1, f"this call closes a cycle ({path}); calls run one way, "
                    "from the configuration down to the modules it composes")


def check_calls_into_roots(repo: Repo) -> None:
    for module in repo.modules.values():
        for tf, block, target in local_calls(module):
            callee = repo.modules.get(target)
            if callee is not None and backend_kinds(callee):
                repo.report(f"{tf.rel}:{block.line}", "module-boundaries", 2, f"`{target}` declares a backend, "
                            "so it is a root configuration; nothing calls a root configuration")


def check_reusable_settings(repo: Repo) -> None:
    for module in reusable(repo):
        for tf, block in module.blocks("provider"):
            repo.report(f"{tf.rel}:{block.line}", "module-boundaries", 3, "a reusable module carries no "
                        "`provider` block; its caller configures providers and passes them in")
        if backend_kinds(module):
            repo.report(where_of(module), "module-boundaries", 3, "a reusable module declares no backend; only "
                        "the root configuration owns state")


def check_tests_beside(repo: Repo) -> None:
    for module in reusable(repo):
        prefix = "" if module.path == "." else f"{module.path}/"
        beside = [p for p in repo.paths if p.startswith(prefix) and TEST_FILE.search(p)]
        if not any(posixpath.dirname(p[len(prefix):]) in ("", "tests") for p in beside):
            repo.report(where_of(module), "test-placement", 1, "no `.tftest.hcl` in this module's folder or its "
                        "`tests/`; write the test beside the module it tests")


# ---------------------------------------------------------------------------


CHECKS = (
    check_state_files,
    check_backends,
    check_lock_flags,
    check_secret_variables,
    check_literal_credentials,
    check_tfvars,
    check_output_sensitivity,
    check_whole_objects,
    check_printed_outputs,
    check_required_version,
    check_provider_versions,
    check_module_pins,
    check_lock_file,
    check_cycles,
    check_calls_into_roots,
    check_reusable_settings,
    check_tests_beside,
)


def report(findings: list[Finding], modules: int) -> int:
    for rel in UNREADABLE:
        print(f"skipped, cannot be read as UTF-8: {rel}", file=sys.stderr)
    if not findings and not UNREADABLE:
        print(f"{modules} module(s), no failures.")
        return 0
    print(f"{len(findings)} failure(s); {modules} module(s) checked:\n")
    for finding in sorted(findings, key=lambda item: (item.where, item.rule, item.condition)):
        print(finding)
    return 1


def main(argv: list[str]) -> int:
    roots = [Path(argument).resolve() for argument in argv[1:]] or [Path.cwd()]
    findings: list[Finding] = []
    modules = 0
    for root in roots:
        repo = build(root)
        for check in CHECKS:
            check(repo)
        findings.extend(repo.findings)
        modules += len(repo.modules)
    return report(findings, modules)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
