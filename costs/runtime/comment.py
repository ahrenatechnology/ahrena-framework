"""The cost comment of a pull request: one comment, one row per model, updated in place.

A pass is one run that spent tokens on the pull request: a development session on somebody's
machine, or a run of the pipeline in CI (review, auto-fix, release train). Each pass has a
stable id, and publishing is a merge by that id, so publishing the same pass twice changes
nothing.

The visible table is the aggregate: one row per model and a total. The passes are not listed;
how many there were and how long they were active is said once, above the table.

The comment carries its own data. A hidden block holds every pass as JSON, so a publisher
with no ledger, which is the CI case, reads the passes already there, adds or replaces its
own and rewrites the comment. A missing or malformed block is rebuilt from the passes the
publisher has, not treated as an error.

`merge_passes`, `parse_payload` and `render` are pure. Everything that talks to GitHub goes
through `gh`, at the bottom of the file. The visible text is Brazilian Portuguese, because
that is the language the platform's pull requests are read in; identifiers stay in English.

The comment holds what the ledger holds and nothing else: ids, times, model ids, counters and
money computed from them. Standard library only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal

from ledger import attribute
from money import PriceTable, token_cost, to_brl
from usage import merge_tokens, sum_kinds

SCHEMA = 1
MARKER = "<!-- ahrena-costs:passes -->"
DATA_OPEN = "<!-- ahrena-costs:data"
DATA = re.compile(r"<!-- ahrena-costs:data\s*(\{.*?\})\s*-->", re.DOTALL)
BODY_LIMIT = 65000
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HEADER = (
    "| Modelo | Entrada | Saída | Escrita de cache | Leitura de cache | Custo de tokens |\n"
    "|---|--:|--:|--:|--:|--:|"
)


def valid_pass(entry: object) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("id"), str) and isinstance(entry.get("tokens"), dict)


def parse_payload(body: str) -> dict:
    """The hidden data of a comment. An absent or broken block yields an empty payload."""
    empty = {"schema": SCHEMA, "passes": [], "branch": None, "brl_per_usd": None}
    match = DATA.search(body or "")
    if not match:
        return empty
    try:
        loaded = json.loads(match.group(1))
    except ValueError:
        return empty
    if not isinstance(loaded, dict) or not isinstance(loaded.get("passes"), list):
        return empty
    return {
        "schema": SCHEMA,
        "passes": [entry for entry in loaded["passes"] if valid_pass(entry)],
        "branch": loaded.get("branch") if isinstance(loaded.get("branch"), str) else None,
        "brl_per_usd": loaded.get("brl_per_usd") if isinstance(loaded.get("brl_per_usd"), (int, float)) else None,
    }


def merge_passes(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Add each incoming pass, replacing the one with the same id; order by start, then id."""
    by_id = {entry["id"]: entry for entry in existing if valid_pass(entry)}
    by_id.update({entry["id"]: entry for entry in incoming if valid_pass(entry)})
    return sorted(by_id.values(), key=lambda entry: (str(entry.get("started_at") or ""), entry["id"]))


def merge_payload(current: dict, incoming: list[dict], context: "Context") -> dict:
    """The payload after a publisher adds its passes and whatever it knows that was missing."""
    return {
        "schema": SCHEMA,
        "passes": merge_passes(current.get("passes", []), incoming),
        "branch": context.branch or current.get("branch"),
        "brl_per_usd": context.brl_per_usd or current.get("brl_per_usd"),
    }


def number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def money(value: Decimal, symbol: str) -> str:
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{symbol} {text}"


def duration(seconds: float | None) -> str:
    if seconds is None:
        return "sem registro"
    minutes = int(round(seconds / 60))
    if minutes < 1:
        return f"{int(round(seconds))}s"
    return f"{minutes // 60}h {minutes % 60:02d}min" if minutes >= 60 else f"{minutes}min"


def token_cells(tokens: dict) -> list[str]:
    kinds = sum_kinds(tokens)
    written = kinds["cache_write_5m"] + kinds["cache_write_1h"]
    return [number(kinds["input"]), number(kinds["output"]), number(written), number(kinds["cache_read"])]


def cost_cell(tokens: dict, table: PriceTable) -> str:
    cost = token_cost(tokens, table)
    text = money(cost.usd, "US$")
    return f"{text} (parcial)" if cost.unpriced else text


def summed(passes: list[dict]) -> tuple[dict, float]:
    tokens: dict = {}
    seconds = 0.0
    for entry in passes:
        merge_tokens(tokens, entry["tokens"])
        seconds += float(entry.get("active_seconds") or 0)
    return tokens, seconds


def model_row(label: str, tokens: dict, table: PriceTable) -> str:
    return "| " + " | ".join([label, *token_cells(tokens), cost_cell(tokens, table)]) + " |"


def table_lines(passes: list[dict], table: PriceTable) -> list[str]:
    """The table: one row per model, then the total."""
    tokens, _ = summed(passes)
    lines = [HEADER]
    lines += [model_row(f"`{model}`", {model: tokens[model]}, table) for model in sorted(tokens)]
    lines.append(model_row("**Total**", tokens, table).replace(cost_cell(tokens, table), f"**{cost_cell(tokens, table)}**"))
    return lines


def headline(passes: list[dict]) -> str:
    _, seconds = summed(passes)
    count = f"{len(passes)} passe{'s' if len(passes) != 1 else ''}"
    return f"**{count}, {duration(seconds)} de tempo ativo.** Este comentário é atualizado a cada passe."


def attribution_note(branch: str | None) -> str:
    if not branch:
        return "- Atribuição: o branch deste pull request não foi informado por quem publicou."
    found = attribute(branch)
    if found["issue"] is not None:
        return f"- Atribuição: issue #{found['issue']}, pelo nome do branch `{branch}`."
    return f"- Sem issue atribuída: o branch `{branch}` não carrega número de issue. O relatório local resolve pelas issues que este pull request fecha."


def cross_checks(passes: list[dict], table: PriceTable) -> list[str]:
    """One note per pass whose runner reported a cost that differs from the computed one."""
    notes = []
    for entry in passes:
        reported = entry.get("reported_cost_usd")
        cost = token_cost(entry["tokens"], table)
        if not isinstance(reported, (int, float)) or cost.unpriced:
            continue
        stated = Decimal(str(reported))
        if abs(stated - cost.usd) > max(Decimal("0.01"), cost.usd / 100):
            notes.append(
                f"- Conferência: o passe `{entry['id']}` informou {money(stated, 'US$')} por conta própria; "
                f"pela tabela de preços, os mesmos tokens dão {money(cost.usd, 'US$')}."
            )
    return notes


def notes(payload: dict, table: PriceTable) -> list[str]:
    passes = payload["passes"]
    tokens, _ = summed(passes)
    cost = token_cost(tokens, table)
    rate = payload.get("brl_per_usd")
    brl = to_brl(cost.usd, rate)
    lines = [
        f"- Custo de tokens em reais: **{money(brl, 'R$')}**, com câmbio de {str(rate).replace('.', ',')} por dólar."
        if brl is not None
        else "- Custo de tokens em reais: câmbio não configurado.",
        attribution_note(payload.get("branch")),
    ]
    for model, count in sorted(cost.unpriced.items()):
        lines.append(f"- Sem preço na tabela para o modelo `{model}`: {number(count)} tokens ficaram fora do custo.")
    if any(entry.get("output_lower_bound") for entry in passes):
        lines.append("- Em pelo menos um passe a saída é um piso: parte das respostas foi registrada antes de terminar.")
    lines += cross_checks(passes, table)
    lines.append("- O custo é o preço de lista da API aplicado aos tokens de cada passe. Não é a fatura, e não inclui o tempo de pessoas.")
    return lines


def encode_payload(payload: dict) -> str:
    """The payload as JSON that cannot close the HTML comment it sits in."""
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text.replace("--", "-\\u002d").replace("<", "\\u003c").replace(">", "\\u003e")


def render(payload: dict, repository: str, table: PriceTable) -> str:
    """The whole comment body for a payload. Deterministic: the same payload, the same text."""
    lines = [
        MARKER,
        "### Custo deste pull request",
        "",
        headline(payload["passes"]),
        "",
        *table_lines(payload["passes"], table),
        "",
        *notes(payload, table),
        "",
        f"{DATA_OPEN}\n{encode_payload(payload)}\n-->",
    ]
    body = "\n".join(lines) + "\n"
    if len(body) > BODY_LIMIT:
        raise ValueError(f"the cost comment would be {len(body)} characters, over GitHub's limit")
    return body


@dataclass
class Target:
    repository: str
    pull_request: int


@dataclass
class Context:
    """What a publisher knows besides its passes."""

    table: PriceTable
    brl_per_usd: float | None = None
    branch: str | None = None


@dataclass
class Outcome:
    action: str
    body: str = ""
    removed: list[int] = field(default_factory=list)


class GhError(RuntimeError):
    """`gh` is missing, not authenticated, offline, or refused the call."""


def gh_installed() -> bool:
    return shutil.which("gh") is not None


def gh(arguments: list[str], payload: dict | None = None) -> str:
    """Run `gh` and return its output; raise GhError for every way it can fail."""
    if not gh_installed():
        raise GhError("gh is not installed")
    stdin = json.dumps(payload) if payload is not None else None
    try:
        result = subprocess.run(["gh", *arguments], input=stdin, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        raise GhError(f"gh did not run: {error}") from error
    if result.returncode != 0:
        raise GhError(f"gh {arguments[0]} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def open_pull_request(repository: str, branch: str) -> int | None:
    """The number of the open pull request of a branch, or None when there is none."""
    out = gh(["pr", "list", "--repo", repository, "--head", branch, "--state", "open", "--json", "number", "--limit", "1"])
    found = json.loads(out or "[]")
    return int(found[0]["number"]) if found else None


def marked_comments(target: Target) -> list[dict]:
    """Every comment of the pull request that carries the marker, oldest first."""
    path = f"repos/{target.repository}/issues/{target.pull_request}/comments"
    out = gh(["api", path, "--paginate", "--jq", ".[] | {id, body}"])
    comments = [json.loads(line) for line in out.splitlines() if line.strip()]
    return sorted((c for c in comments if MARKER in str(c.get("body") or "")), key=lambda c: c["id"])


def write_comment(target: Target, comment_id: int | None, body: str) -> None:
    if comment_id is None:
        gh(["api", f"repos/{target.repository}/issues/{target.pull_request}/comments", "--method", "POST", "--input", "-"], {"body": body})
    else:
        gh(["api", f"repos/{target.repository}/issues/comments/{comment_id}", "--method", "PATCH", "--input", "-"], {"body": body})


def publish(target: Target, passes: list[dict], context: Context) -> Outcome:
    """Merge passes into the pull request's cost comment, creating it when there is none.

    Two publishers that raced can each have created a comment. Their passes are merged into
    the oldest and the others are removed, so the pull request converges on one comment.
    """
    if not REPOSITORY.match(target.repository):
        raise GhError(f"'{target.repository}' is not an owner/name repository")
    comments = marked_comments(target)
    payload = {"passes": []}
    for comment in comments:
        found = parse_payload(comment["body"])
        payload = {**found, "passes": merge_passes(payload["passes"], found["passes"])}
    body = render(merge_payload(payload, passes, context), target.repository, context.table)
    first = comments[0] if comments else None
    same = first is not None and str(first["body"]).replace("\r\n", "\n").strip() == body.strip()
    outcome = Outcome("unchanged" if same else "updated" if first else "created", body)
    if outcome.action != "unchanged":
        write_comment(target, first["id"] if first else None, body)
    for extra in comments[1:]:
        gh(["api", f"repos/{target.repository}/issues/comments/{extra['id']}", "--method", "DELETE"])
        outcome.removed.append(extra["id"])
    return outcome
