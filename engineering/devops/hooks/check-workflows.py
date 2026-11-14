#!/usr/bin/env python3
"""Detector for the GitHub Actions rules of the ahrena-engineering-devops plugin.

Decides, over the workflow files (`.github/workflows/*.yml|yaml`) and the
composite actions (`.github/actions/**/action.yml|yaml`) of a repository, every
condition of these rules that a reader of the file can decide:

    token-permissions      1-2  permissions declared; no write-all or read-all
    action-pinning         1-2  third-party actions on a full commit SHA or in
                                the workflow lockfile, reusable workflows on a
                                full SHA; docker images by digest
    cloud-credentials      1-3  no long-lived AWS, Google Cloud or Azure
                                credential handed to a login, an env or a CLI
    script-injection       1    no untrusted context expanded into a script
    privileged-triggers    1    no pull_request_target or workflow_run job that
                                checks out the contributor's code
    log-exposure           1-5  no secret, environment, context, token,
                                account identity or Terraform debug log
                                printed to the job log
    protected-deployments  1-2  a deploy job holds a concurrency group and does
                                not cancel a deploy in flight
    job-timeouts           1    every job that runs steps has timeout-minutes

The conditions that need the forge's settings (a required reviewer on an
environment) or a reader (a rollback stated, a write scope the job uses) are
not here; each rule says who decides them.

The YAML reader is written against the standard library because the hook must
run on a machine with nothing installed. It reads the block style workflows
are written in: mappings, sequences, plain, quoted and block scalars, and flow
collections. Anchors and aliases are kept as text, not resolved. A file it
cannot read is reported as a failure naming actionlint, never passed silently.

A finding on a line that carries a decision-record pointer (`ADR-12`) is
skipped for cloud-credentials, which is the one condition a recorded reason may
excuse.

Usage:
    python3 engineering/devops/hooks/check-workflows.py [root ...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Union

# ---------------------------------------------------------------------------


class YamlError(Exception):
    pass


class Scalar(str):
    line: int = 0

    def __new__(cls, value: str, line: int) -> "Scalar":
        obj = super().__new__(cls, value)
        obj.line = line
        return obj


class YMap(dict):
    def __init__(self, line: int) -> None:
        super().__init__()
        self.line = line
        self.key_lines: dict[str, int] = {}


class YList(list):
    def __init__(self, line: int) -> None:
        super().__init__()
        self.line = line


Node = Union[Scalar, YMap, YList, None]
ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "0": ""}
BLOCK_INDICATOR = re.compile(r"^[|>][+-]?[1-9]?[+-]?$")


def strip_comment(text: str) -> str:
    """`text` without a trailing comment; a `#` inside quotes or not after a space is kept."""
    quote = ""
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"" and (index == 0 or text[index - 1] in " \t:[{,-"):
            quote = char
        elif char == "#" and (index == 0 or text[index - 1] in " \t"):
            return text[:index].rstrip()
    return text.rstrip()


def split_key(text: str) -> Optional[tuple[str, str]]:
    """(key, rest) when `text` is a mapping entry, else None."""
    if text[:1] in "'\"":
        close = text.find(text[0], 1)
        if close != -1 and text[close + 1 : close + 2] == ":" and text[close + 2 : close + 3] in ("", " "):
            return text[1:close], text[close + 2 :].strip()
        return None
    match = re.match(r"^([^\s:#\[\]{},][^:#]*?|[^\s:#\[\]{},]):(\s+|$)(.*)$", text)
    if not match or "${{" in match.group(1):
        return None
    return match.group(1).strip(), match.group(3).strip()


def balanced(text: str) -> bool:
    depth, quote = 0, ""
    for char in text:
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
    return depth <= 0 and not quote


def split_flow(text: str) -> list[str]:
    parts, depth, quote, start = [], 0, "", 0
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def scalar(text: str, line: int) -> Node:
    text = text.strip()
    if text.startswith("[") or text.startswith("{"):
        if not balanced(text) or text[-1] not in "]}":
            raise YamlError(f"line {line}: unterminated flow collection")
        inner = text[1:-1]
        if text[0] == "[":
            out = YList(line)
            out.extend(scalar(p, line) for p in split_flow(inner))
            return out
        mapping = YMap(line)
        for part in split_flow(inner):
            pair = split_key(part) or (part, "")
            mapping[pair[0]] = scalar(pair[1], line) if pair[1] else None
            mapping.key_lines[pair[0]] = line
        return mapping
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return Scalar(re.sub(r'\\(["\\/nt0])', lambda m: ESCAPES[m.group(1)], text[1:-1]), line)
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return Scalar(text[1:-1].replace("''", "'"), line)
    if text[:1] in "'\"":
        raise YamlError(f"line {line}: unterminated quoted scalar")
    return Scalar(text, line)


class Reader:
    def __init__(self, text: str) -> None:
        self.lines = text.replace("\t", "  ").splitlines()

    def significant(self, index: int) -> Optional[int]:
        while index < len(self.lines):
            stripped = self.lines[index].strip()
            if stripped and not stripped.startswith("#") and stripped not in ("---", "..."):
                return index
            index += 1
        return None

    def indent(self, index: int) -> int:
        line = self.lines[index]
        return len(line) - len(line.lstrip(" "))

    def parse(self) -> Node:
        first = self.significant(0)
        if first is None:
            return None
        node, index = self.block(first, self.indent(first))
        rest = self.significant(index)
        if rest is not None:
            raise YamlError(f"line {rest + 1}: content outside the document's structure")
        return node

    def block(self, index: int, indent: int) -> tuple[Node, int]:
        text = self.lines[index].strip()
        if text == "-" or text.startswith("- "):
            return self.sequence(index, indent)
        return self.mapping(index, indent)

    def mapping(self, index: int, indent: int) -> tuple[YMap, int]:
        result = YMap(index + 1)
        current: Optional[int] = index
        while current is not None and self.indent(current) == indent:
            text = strip_comment(self.lines[current].strip())
            if text == "-" or text.startswith("- "):
                break
            pair = split_key(text)
            if pair is None:
                raise YamlError(f"line {current + 1}: expected a mapping entry")
            key, rest = pair
            result.key_lines[key] = current + 1
            value, current = self.value(current, indent, rest)
            result[key] = value
            current = self.significant(current)
        if current is not None and self.indent(current) > indent:
            raise YamlError(f"line {current + 1}: unexpected indentation")
        return result, current if current is not None else len(self.lines)

    def sequence(self, index: int, indent: int) -> tuple[YList, int]:
        result = YList(index + 1)
        current: Optional[int] = index
        while current is not None and self.indent(current) == indent:
            raw = self.lines[current]
            text = raw.strip()
            if not (text == "-" or text.startswith("- ")):
                break
            body = text[1:].lstrip(" ")
            column = indent + (len(text) - len(body))
            if not strip_comment(body):
                after = self.significant(current + 1)
                if after is not None and self.indent(after) > indent:
                    item, current = self.block(after, self.indent(after))
                else:
                    item, current = None, current + 1
            elif split_key(strip_comment(body)) and not body.startswith(("'", '"')) or (
                body[:1] in "'\"" and split_key(strip_comment(body))
            ):
                self.lines[current] = " " * column + body
                item, current = self.mapping(current, column)
            else:
                item, current = self.value(current, indent, strip_comment(body), item=True)
            result.append(item)
            current = self.significant(current)
        return result, current if current is not None else len(self.lines)

    def value(self, index: int, indent: int, rest: str, item: bool = False) -> tuple[Node, int]:
        """The value after a key (or a sequence dash) on line `index`, and the next line to read."""
        line = index + 1
        if BLOCK_INDICATOR.match(rest):
            return self.block_scalar(index, indent, rest)
        if rest:
            text = rest
            following = index + 1
            while (text[:1] in "[{" and not balanced(text)) and following < len(self.lines):
                text += " " + strip_comment(self.lines[following].strip())
                following += 1
            nxt = self.significant(following)
            while not item and text[:1] not in "[{'\"" and nxt is not None and self.indent(nxt) > indent:
                text += " " + strip_comment(self.lines[nxt].strip())
                following = nxt + 1
                nxt = self.significant(following)
            return scalar(text, line), following
        nxt = self.significant(index + 1)
        if nxt is None:
            return None, index + 1
        if self.indent(nxt) > indent:
            return self.block(nxt, self.indent(nxt))
        stripped = self.lines[nxt].strip()
        if self.indent(nxt) == indent and (stripped == "-" or stripped.startswith("- ")) and not item:
            return self.sequence(nxt, indent)
        return None, index + 1

    def block_scalar(self, index: int, indent: int, indicator: str) -> tuple[Scalar, int]:
        collected: list[str] = []
        current = index + 1
        body_indent: Optional[int] = None
        while current < len(self.lines):
            raw = self.lines[current]
            if raw.strip():
                width = len(raw) - len(raw.lstrip(" "))
                if width <= indent:
                    break
                if body_indent is None:
                    body_indent = width
                collected.append(raw[min(width, body_indent) :])
            else:
                collected.append("")
            current += 1
        while collected and not collected[-1]:
            collected.pop()
        joiner = "\n" if indicator.startswith("|") else " "
        result = Scalar(joiner.join(collected), index + 2)
        return result, current


def load(text: str) -> Node:
    return Reader(text).parse()


# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    where: str
    rule: str
    condition: int
    message: str

    def __str__(self) -> str:
        return f"{self.where}\n    [{self.rule}] {self.rule} condition {self.condition}: {self.message}"


SKIP_PARTS = frozenset({".git", "node_modules", "vendor"})
ADR = re.compile(r"\bADR-\d+\b")
FULL_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
LOCKFILE = ".github/workflows/actions.lock"
GITHUB_OWNERS = frozenset({"actions", "github"})
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.S)

UNTRUSTED = [
    re.compile(p)
    for p in (
        r"github\.event\.(issue|pull_request|discussion)\.(title|body)\b",
        r"github\.event\.(comment|review|review_comment)\.body\b",
        r"github\.event\.pages\b.*\.page_name\b",
        r"github\.event\.(head_commit|commits\b[^}]*?)\.(message|author\.(email|name)|committer\.(email|name))\b",
        r"github\.event\.pull_request\.head\.(ref|label|repo\.default_branch)\b",
        r"github\.head_ref\b",
        r"github\.event\.workflow_run\.(head_branch|display_title|head_commit\.(message|author\.(email|name)))\b",
        r"github\.event\.workflow_run\.pull_requests\b.*\.head\.ref\b",
        r"toJSON\(\s*github\.event\s*\)",
    )
]

HEAD_REF = re.compile(
    r"github\.event\.pull_request\.head\.(sha|ref|repo\.full_name)|github\.head_ref|"
    r"github\.event\.workflow_run\.head_(sha|branch|repository\.full_name)|refs/pull/|github\.event\.number|"
    r"github\.event\.pull_request\.number"
)
HEAD_CHECKOUT_COMMAND = re.compile(r"\bgh\s+pr\s+checkout\b|\bgit\s+(fetch|checkout|switch)\b[^\n]*(" + HEAD_REF.pattern + ")")

LOGIN_KEY_INPUTS = {
    "aws-actions/configure-aws-credentials": ("aws-access-key-id", "aws-secret-access-key"),
    "google-github-actions/auth": ("credentials_json",),
    "azure/login": ("creds",),
}
CREDENTIAL_ENV = re.compile(
    r"^(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|GOOGLE_CREDENTIALS|GOOGLE_CLOUD_KEYFILE_JSON|GCP_SA_KEY|"
    r"GOOGLE_APPLICATION_CREDENTIALS_JSON|ARM_CLIENT_SECRET|AZURE_CLIENT_SECRET|ARM_CLIENT_CERTIFICATE_PASSWORD|"
    r"AZURE_CLIENT_CERTIFICATE_PASSWORD|AZURE_CREDENTIALS)$"
)
CREDENTIAL_COMMAND = re.compile(
    r"\bgcloud\s+auth\s+activate-service-account\b[^\n]*--key-file|"
    r"\baz\s+login\b[^\n]*--service-principal\b[^\n]*(\s-p\s|--password|--secret)|"
    r"\baz\s+login\b[^\n]*(\s-p\s|--password)[^\n]*--service-principal"
)

PRINT_VERBS = frozenset({"echo", "printf", "print", "cat", "Write-Host", "Write-Output", "write-host", "write-output"})
SECRET_EXPR = re.compile(r"\bsecrets\.[A-Za-z_][A-Za-z0-9_]*|\bsecrets\[")
WHOLE_SECRETS = re.compile(r"toJSON\(\s*secrets\s*\)")
WHOLE_CONTEXT = re.compile(r"toJSON\(\s*(github|env|vars|job|steps|needs|runner|strategy|inputs)\s*\)")
DUMP = re.compile(
    r"^(env|printenv|export\s+-p|export|set|declare\s+-p|declare\s+-x|"
    r"(Get-ChildItem|gci|dir|ls)\s+env:|Get-Item\s+env:\*?)$"
)
TRACE = re.compile(r"\bset\s+-[a-wyz]*x[a-z]*\b|\bset\s+-o\s+xtrace\b|\bbash\s+-[a-wyz]*x[a-z]*\b")
MINT_OR_IDENTIFY = re.compile(
    r"\bgcloud\s+auth\s+(print-access-token|print-identity-token|application-default\s+print-access-token)\b|"
    r"\bgcloud\s+config\s+list\b|"
    r"\baz\s+account\s+(get-access-token|show)\b|"
    r"\baws\s+sts\s+(get-caller-identity|get-session-token|assume-role|assume-role-with-web-identity|get-federation-token)\b|"
    r"\baws\s+ecr\s+get-login-password\b|\baws\s+codeartifact\s+get-authorization-token\b"
)
TF_LOG_OFF = frozenset({"", "off", "OFF", "Off", "false", "0"})


@dataclass
class File:
    rel: str
    raw: list[str]
    doc: YMap
    findings: list[Finding]
    locked: bool = False

    def report(self, line: int, rule: str, condition: int, message: str) -> None:
        self.findings.append(Finding(f"{self.rel}:{line}", rule, condition, message))


def has_adr(raw: list[str], line: int) -> bool:
    """Whether the file's line `line` carries a decision-record pointer."""
    return 0 < line <= len(raw) and bool(ADR.search(raw[line - 1]))


def as_map(node: Node) -> YMap:
    return node if isinstance(node, YMap) else YMap(0)


def as_list(node: Node) -> YList:
    return node if isinstance(node, YList) else YList(0)


def line_of(node: Node, fallback: int) -> int:
    return getattr(node, "line", 0) or fallback


def triggers(doc: YMap) -> set[str]:
    on = doc.get("on", doc.get("true"))
    if isinstance(on, Scalar):
        return {str(on)}
    if isinstance(on, YList):
        return {str(x) for x in on}
    if isinstance(on, YMap):
        return set(on)
    return set()


def jobs(doc: YMap) -> Iterator[tuple[str, YMap, int]]:
    jobs_node = as_map(doc.get("jobs"))
    for name, body in jobs_node.items():
        yield name, as_map(body), jobs_node.key_lines.get(name, jobs_node.line)


def steps_of(body: YMap) -> Iterator[YMap]:
    for step in as_list(body.get("steps")):
        if isinstance(step, YMap):
            yield step


def env_of(node: YMap) -> YMap:
    return as_map(node.get("env"))


def uses_parts(uses: str) -> tuple[str, str]:
    """(action path without ref, ref)."""
    target, _, ref = uses.partition("@")
    return target.strip(), ref.strip()


def run_text(step: YMap) -> Optional[Scalar]:
    run = step.get("run")
    return run if isinstance(run, Scalar) else None


def script_text(step: YMap) -> Optional[Scalar]:
    uses = step.get("uses")
    if isinstance(uses, Scalar) and uses_parts(uses)[0] == "actions/github-script":
        script = as_map(step.get("with")).get("script")
        if isinstance(script, Scalar):
            return script
    return None


def segments(script: str) -> Iterator[tuple[int, str]]:
    """(line offset, command segment) for each simple command of a shell script, roughly."""
    for offset, line in enumerate(script.split("\n")):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for part in re.split(r"\s*(?:&&|\|\||;)\s*", stripped):
            if part:
                yield offset, part


def first_word(segment: str) -> str:
    words = segment.split()
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        words = words[1:]
    return words[0] if words else ""


def redirected(segment: str) -> bool:
    return bool(re.search(r"(^|[^<>&0-9])>{1,2}\s*[^&\s]", segment))


def piped(segment: str) -> bool:
    return bool(re.search(r"(?<!\|)\|(?!\|)", segment))


def captured(script: str, match: re.Match[str]) -> bool:
    before = script[: match.start()]
    line_start = before.rfind("\n") + 1
    prefix = before[line_start:]
    return prefix.count("$(") > prefix.count(")") or prefix.count("`") % 2 == 1


# ---------------------------------------------------------------------------


def check_permissions(f: File) -> None:
    if f.rel.endswith(("action.yml", "action.yaml")) and "/workflows/" not in f.rel:
        return
    top = f.doc.get("permissions")
    for where, node in [("the workflow", top)] + [(f"jobs.{n}", b.get("permissions")) for n, b, _ in jobs(f.doc)]:
        if isinstance(node, Scalar) and str(node).strip() in ("write-all", "read-all"):
            f.report(node.line, "token-permissions", 2,
                     f"{where} grants `{node.strip()}`; list each scope the job uses, or `permissions: {{}}`")
    if top is not None:
        return
    for name, body, line in jobs(f.doc):
        if "permissions" not in body:
            f.report(line, "token-permissions", 1,
                     f"jobs.{name} runs with the repository's default GITHUB_TOKEN permissions, because neither it "
                     "nor the workflow declares `permissions`")


def all_uses(f: File) -> Iterator[tuple[Scalar, bool]]:
    """Every `uses:` value, with whether it is a step's (True) or a reusable-workflow call's (False)."""
    for _, body, _ in jobs(f.doc):
        if isinstance(body.get("uses"), Scalar):
            yield body["uses"], False
        for step in steps_of(body):
            if isinstance(step.get("uses"), Scalar):
                yield step["uses"], True
    for step in steps_of(as_map(f.doc.get("runs"))):
        if isinstance(step.get("uses"), Scalar):
            yield step["uses"], True


def check_pinning(f: File) -> None:
    for uses, step_level in all_uses(f):
        text = uses.strip()
        if text.startswith("./") or "${{" in text:
            continue
        if text.startswith("docker://"):
            if "@sha256:" not in text:
                f.report(uses.line, "action-pinning", 2, f"`{text}` names a container image by tag; pin it by digest")
            continue
        target, ref = uses_parts(text)
        owner = target.split("/", 1)[0]
        if owner in GITHUB_OWNERS or (step_level and f.locked):
            continue
        if not FULL_SHA.match(ref):
            f.report(uses.line, "action-pinning", 1,
                     f"`{text}` is a third-party action on a mutable ref; pin it to a full commit SHA, "
                     "with the release tag in a comment")


def line_at(text: Scalar, position: int) -> int:
    """The file line of `position` inside a scalar that starts on `text.line`."""
    return text.line + text[:position].count("\n")


def env_maps(f: File) -> Iterator[YMap]:
    yield env_of(f.doc)
    for _, body, _ in jobs(f.doc):
        yield env_of(body)
        for step in steps_of(body):
            yield env_of(step)
    for step in steps_of(as_map(f.doc.get("runs"))):
        yield env_of(step)


def credential_env_lines(env: YMap) -> Iterator[tuple[str, int]]:
    for key, value in env.items():
        if CREDENTIAL_ENV.match(key) and isinstance(value, Scalar) and SECRET_EXPR.search(value):
            yield key, env.key_lines.get(key, env.line)


def login_key_inputs(step: YMap) -> Iterator[tuple[str, str, int]]:
    """(action, input, line) for each long-lived key a cloud login action is given."""
    uses = step.get("uses")
    if not isinstance(uses, Scalar):
        return
    action = uses_parts(uses)[0]
    given = as_map(step.get("with"))
    for name in LOGIN_KEY_INPUTS.get(action, ()):
        if name in given:
            yield action, name, given.key_lines.get(name, given.line)


def check_credentials(f: File) -> None:
    for env in env_maps(f):
        for key, line in credential_env_lines(env):
            if not has_adr(f.raw, line):
                f.report(line, "cloud-credentials", 2,
                         f"`{key}` carries a long-lived cloud credential from a secret; federate with OIDC instead")
    for step in all_steps(f):
        for action, name, line in login_key_inputs(step):
            if not has_adr(f.raw, line):
                f.report(line, "cloud-credentials", 1,
                         f"`{action}` is given `{name}`, a long-lived credential; configure OIDC federation and drop the secret")
        run = run_text(step) or Scalar("", 0)
        for match in CREDENTIAL_COMMAND.finditer(run):
            if not has_adr(f.raw, line_at(run, match.start())):
                f.report(line_at(run, match.start()), "cloud-credentials", 3,
                         "the command signs in with a key file or a client secret; federate with OIDC instead")


def all_steps(f: File) -> Iterator[YMap]:
    for _, body, _ in jobs(f.doc):
        yield from steps_of(body)
    yield from steps_of(as_map(f.doc.get("runs")))


def scripts_of(step: YMap) -> Iterator[Scalar]:
    for text in (run_text(step), script_text(step)):
        if text is not None:
            yield text


def check_injection(f: File) -> None:
    for text in (t for step in all_steps(f) for t in scripts_of(step)):
        for match in EXPRESSION.finditer(text):
            if any(p.search(match.group(1)) for p in UNTRUSTED):
                f.report(line_at(text, match.start()), "script-injection", 1,
                         f"`${{{{{match.group(1).strip()}}}}}` expands text a contributor controls into the script; "
                         "pass it through `env:` and quote the variable")


def head_checkout_inputs(step: YMap) -> Iterator[tuple[str, Scalar]]:
    """(input, value) for each `actions/checkout` input that names the contributor's code."""
    uses = step.get("uses")
    if not (isinstance(uses, Scalar) and uses_parts(uses)[0] == "actions/checkout"):
        return
    given = as_map(step.get("with"))
    for key in ("ref", "repository"):
        value = given.get(key)
        if isinstance(value, Scalar) and HEAD_REF.search(value):
            yield key, value


def check_triggers(f: File) -> None:
    privileged = triggers(f.doc) & {"pull_request_target", "workflow_run"}
    if not privileged:
        return
    event = "/".join(sorted(privileged))
    for step in all_steps(f):
        for key, value in head_checkout_inputs(step):
            f.report(value.line, "privileged-triggers", 1,
                     f"a {event} workflow checks out the contributor's code (`{key}: {value.strip()}`) "
                     "with the base repository's secrets and token in reach")
        run = run_text(step) or Scalar("", 0)
        for match in HEAD_CHECKOUT_COMMAND.finditer(run):
            f.report(line_at(run, match.start()), "privileged-triggers", 1,
                     f"a {event} workflow fetches the contributor's code into a job with the base "
                     "repository's secrets and token in reach")


def secret_env_names(*maps: YMap) -> set[str]:
    return {k for m in maps for k, v in m.items() if isinstance(v, Scalar) and SECRET_EXPR.search(v)}


def context_env_names(*maps: YMap) -> set[str]:
    return {k for m in maps for k, v in m.items() if isinstance(v, Scalar) and WHOLE_CONTEXT.search(v)}


def prints_var(segment: str, names: set[str]) -> Optional[str]:
    if first_word(segment) not in PRINT_VERBS or redirected(segment) or piped(segment):
        return None
    for name in names:
        if re.search(rf"\$\{{?{re.escape(name)}\b|\$env:{re.escape(name)}\b", segment):
            return name
    return None


def job_holds_secret(body: YMap, top_env: YMap) -> bool:
    texts = [str(v) for m in (top_env, env_of(body)) for v in m.values() if isinstance(v, Scalar)]
    for step in steps_of(body):
        texts += [str(v) for v in env_of(step).values() if isinstance(v, Scalar)]
        texts += [str(v) for v in as_map(step.get("with")).values() if isinstance(v, Scalar)]
        texts.append(str(run_text(step) or ""))
    return any(SECRET_EXPR.search(t) or WHOLE_SECRETS.search(t) for t in texts)


@dataclass
class Unit:
    """One job, or a composite action's steps, with what the log-exposure checks read from it."""

    body: YMap
    steps: list[YMap]
    top_env: YMap
    holds_secret: bool

    def shell(self) -> Node:
        return as_map(as_map(self.body.get("defaults")).get("run")).get("shell")


def exposure_units(f: File) -> Iterator[Unit]:
    top_env = env_of(f.doc)
    for _, body, _ in jobs(f.doc):
        yield Unit(body, list(steps_of(body)), top_env, job_holds_secret(body, top_env))
    composite = list(steps_of(as_map(f.doc.get("runs"))))
    if composite:
        holds = any(SECRET_EXPR.search(str(run_text(s) or "")) for s in composite)
        yield Unit(YMap(0), composite, top_env, holds)


def check_tf_log(f: File, unit: Unit) -> None:
    for env in (unit.top_env, env_of(unit.body)):
        value = env.get("TF_LOG")
        if isinstance(value, Scalar) and value.strip() not in TF_LOG_OFF:
            f.report(env.key_lines.get("TF_LOG", env.line), "log-exposure", 5,
                     f"`TF_LOG: {value.strip()}` writes Terraform's unredacted debug log to the job log")


def check_traced_shell(f: File, unit: Unit, step: YMap) -> None:
    shell = step.get("shell") or unit.shell()
    if unit.holds_secret and isinstance(shell, Scalar) and TRACE.search(shell):
        f.report(shell.line, "log-exposure", 3,
                 f"`shell: {shell.strip()}` traces every command, expanded, in a job that holds a secret")


def check_printed_expressions(f: File, run: Scalar) -> None:
    for match in EXPRESSION.finditer(run):
        inner, line = match.group(1), line_at(run, match.start())
        printed = print_segment_at(run, match.start())
        if WHOLE_SECRETS.search(inner):
            f.report(line, "log-exposure", 1, "the whole `secrets` context is expanded into the script")
        elif SECRET_EXPR.search(inner) and printed:
            f.report(line, "log-exposure", 1, f"`{inner.strip()}` is printed to the job log")
        elif WHOLE_CONTEXT.search(inner) and printed:
            f.report(line, "log-exposure", 2, f"`{inner.strip()}` prints a whole context to the job log")


def check_printed_variables(f: File, line: int, segment: str, names: tuple[set[str], set[str]]) -> None:
    secrets, contexts = names
    if name := prints_var(segment, secrets):
        f.report(line, "log-exposure", 1, f"`${name}` holds a secret and is printed to the job log")
    if name := prints_var(segment, contexts):
        f.report(line, "log-exposure", 2, f"`${name}` holds a whole context and is printed to the job log")


def check_dump_and_trace(f: File, line: int, segment: str, traced: bool) -> None:
    command = segment.split("|")[0].strip()
    if DUMP.match(command) and not redirected(segment):
        f.report(line, "log-exposure", 2, f"`{command}` prints the whole environment to the job log")
    if traced and TRACE.search(segment):
        f.report(line, "log-exposure", 3, "shell tracing prints every command, expanded, in a job that holds a secret")


def mint_printed(run: Scalar, match: re.Match[str]) -> bool:
    end = run.find("\n", match.end())
    rest = run[match.start() : end if end != -1 else len(run)]
    if piped(rest) or redirected(rest):
        return False
    return not captured(run, match) or print_segment_at(run, match.start())


def check_minted(f: File, run: Scalar) -> None:
    for match in MINT_OR_IDENTIFY.finditer(run):
        if mint_printed(run, match):
            f.report(line_at(run, match.start()), "log-exposure", 4,
                     f"`{match.group(0)}` prints a token or the account's identity to the job log; "
                     "capture it, mask it, or drop the step")


def check_step_exposure(f: File, unit: Unit, step: YMap) -> None:
    run = run_text(step)
    if run is None:
        return
    maps = (unit.top_env, env_of(unit.body), env_of(step))
    names = (secret_env_names(*maps), context_env_names(*maps))
    check_traced_shell(f, unit, step)
    check_printed_expressions(f, run)
    for offset, segment in segments(run):
        check_printed_variables(f, run.line + offset, segment, names)
        check_dump_and_trace(f, run.line + offset, segment, unit.holds_secret)
    check_minted(f, run)


def check_exposure(f: File) -> None:
    for unit in exposure_units(f):
        check_tf_log(f, unit)
        for step in unit.steps:
            check_step_exposure(f, unit, step)


def print_segment_at(script: str, position: int) -> bool:
    start = script.rfind("\n", 0, position) + 1
    end = script.find("\n", position)
    line = script[start : end if end != -1 else len(script)]
    column = position - start
    for part in re.split(r"(?:&&|\|\||;)", line):
        if column <= len(part):
            segment = part.strip()
            return first_word(segment) in PRINT_VERBS and not redirected(segment) and not piped(segment)
        column -= len(part) + (2 if line[len(part) : len(part) + 2] in ("&&", "||") else 1)
    return False


def check_deployments(f: File) -> None:
    top = f.doc.get("concurrency")
    for name, body, line in jobs(f.doc):
        if "environment" not in body:
            continue
        own = body.get("concurrency")
        guard = own if own is not None else top
        if guard is None:
            f.report(line, "protected-deployments", 1,
                     f"jobs.{name} deploys to an environment with no concurrency group, so two runs can deploy at once")
            continue
        cancel = as_map(guard).get("cancel-in-progress")
        if isinstance(cancel, Scalar) and cancel.strip().lower() == "true":
            f.report(cancel.line, "protected-deployments", 2,
                     f"jobs.{name} cancels a deploy in flight when a newer run starts; queue it instead")


def check_timeouts(f: File) -> None:
    for name, body, line in jobs(f.doc):
        if "uses" in body or "timeout-minutes" in body:
            continue
        f.report(line, "job-timeouts", 1,
                 f"jobs.{name} has no `timeout-minutes`, so a hung step holds the runner until the platform's limit")


CHECKS = (check_permissions, check_pinning, check_credentials, check_injection, check_triggers, check_exposure,
          check_deployments, check_timeouts)


# ---------------------------------------------------------------------------


def candidates(root: Path) -> Iterator[Path]:
    github = root / ".github"
    if not github.is_dir():
        return
    for path in sorted(github.rglob("*")):
        if not path.is_file() or SKIP_PARTS & set(path.relative_to(root).parts):
            continue
        rel = path.relative_to(github).as_posix()
        if re.match(r"^workflows/[^/]+\.ya?ml$", rel) or re.match(r"^actions/(.+/)?action\.ya?ml$", rel):
            yield path


def check_file(root: Path, path: Path) -> list[Finding]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        doc = load(text)
    except (YamlError, RecursionError) as error:
        return [Finding(rel, "parse", 0, f"could not read this file ({error}); run actionlint on it")]
    if not isinstance(doc, YMap):
        return [Finding(rel, "parse", 0, "could not read this file as a mapping; run actionlint on it")]
    f = File(rel, text.splitlines(), doc, [], (root / LOCKFILE).is_file())
    for check in CHECKS:
        check(f)
    return f.findings


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or [Path.cwd()]
    findings: list[Finding] = []
    seen = 0
    for root in roots:
        for path in candidates(root.resolve()):
            seen += 1
            findings.extend(check_file(root.resolve(), path))
    for finding in sorted(set(findings), key=lambda x: (x.where.split(":")[0], int(x.where.rsplit(":", 1)[-1])
                                                    if x.where.rsplit(":", 1)[-1].isdigit() else 0, x.rule)):
        print(finding)
    if findings:
        print(f"\n{len(set(findings))} failure(s) in {seen} file(s).")
        return 1
    print(f"no failures in {seen} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
