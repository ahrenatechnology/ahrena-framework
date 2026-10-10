#!/usr/bin/env python3
"""Build the explainer pages for the review agents, from this repository.

    python3 artifacts/build.py

One page per agent under artifacts/<page>/, generated from the repo's own
engineering/quality (and sibling) files and a shared template. Each page has two
tabs: the prompt composition (layers, routes, the text of each artifact) and the
orchestration (how the agents run together). An entry whose file is absent on
the current checkout is skipped, so the same build runs against main or a branch.
The page only carries the drawing and the texts; publishing is the ahrena-artifacts
skill's job, and it is the one that writes artifact.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
Q = "engineering/quality"

ORCHESTRATION = """\
## How the two agents run together

The framework defines the flow; an outside orchestrator only drives it. Argos reviews, and when it approves it asks the forge to land the change. Erodos — a separate agent, so the reviewer never reads its own edit — applies the findings that are mechanically applicable, and hands the pull request back for Argos to review again. Nothing merges until a review is clean.

- **Request changes** when a blocking finding stands; the author, or Erodos, resolves it.
- **Comment** when only a question or an unchecked condition is left — the review has not finished.
- **Approve, then land** when nothing stops the change; the forge squash-merges the exact commit that was read, once its checks pass.

The fix–review cycle is bounded: whatever is still blocking after the attempt limit goes to a person. A person also lands four kinds of change whatever the review says — a decision record, a layer of a stack, a draft, and a pull request from an external fork. `ADR-013` and `ADR-014` record why the reviewer approves on a clean pass and why the fixer is a second agent.

## Where an external orchestrator fits

Argos and Erodos are addressable agents with a fixed contract: Argos publishes a structured verdict and findings; Erodos consumes applicable findings and returns a commit. An orchestrator — a scheduler, a CI job, a graph of calls — sequences `review → fix → review → land` and decides retries and parallelism across pull requests. It does not re-decide a verdict or a merge: those stay in the agents and the gate. The two agents work the same whether a person runs them by hand or an orchestrator does.
"""

FLOW = """flowchart TD
  PR([Pull request]) --> ARGOS[Argos reviews]
  ARGOS -->|router selects disciplines| DISC[Discipline skills:\\nsecurity, prompts, language, contract...]
  DISC --> VERDICT{Verdict from the findings}
  VERDICT -->|blocking| RC[Request changes]
  VERDICT -->|question / unchecked| COMMENT[Comment: not finished]
  VERDICT -->|nothing stops it| APPROVE[Approve]
  RC --> ERODOS[Erodos applies the applicable fixes]
  ERODOS -->|new commit, bounded attempts| ARGOS
  APPROVE --> LAND[Argos asks the forge to squash-merge the reviewed commit]
  LAND --> TRUNK([Trunk])
  VERDICT -.decision record / stack / draft / fork.-> PERSON([A person lands it])
"""

PAGES = {
    "argos-system-prompts": {
        "title": "Argos System Prompts",
        "eyebrow": "Ahrena · agente revisor",
        "lead": "O Argos não tem um prompt único. O que ele lê numa revisão é montado em camadas: o agente está sempre lá, e o resto só entra quando a mudança pede. A aba Orquestração mostra como ele e o Erodos rodam juntos.",
        "layers": [
            ("Agente", "`agents/argos.md` diz o que o Argos é, quais skills ele orquestra e o que ele se recusa a fazer.", "sempre"),
            ("Roteador", "`route-review.py` lê a mudança contra `routes.json` e imprime as rotas que dispararam. É um script: não gasta contexto.", "sempre"),
            ("Skills", "Cada rota aponta uma skill de revisão. Só as apontadas são carregadas.", "por rota"),
            ("Checklists e regras", "As condições ficam em `references/` e nas regras do `fundamentals`. Cada arquivo só abre pela rota que o nomeia.", "por rota"),
        ],
        "routes": True,
        "entries": [
            ("Agente", "argos", f"{Q}/agents/argos.md", "O revisor. Diz o que ele é, quais skills orquestra e o que não faz."),
            ("Toda revisão", "reviewing-diffs", f"{Q}/skills/reviewing-diffs/SKILL.md", "Sempre, e primeiro. Fixa base e head, roda o roteador e lê as regras de engenharia."),
            ("Toda revisão", "publishing-review-verdicts", f"{Q}/skills/publishing-review-verdicts/SKILL.md", "Escolhe o veredito pelos achados e publica um comentário por commit."),
            ("Toda revisão", "landing-approved-changes", f"{Q}/skills/landing-approved-changes/SKILL.md", "Só depois de um approve. Pede ao forge o squash do commit revisado, com os checks verdes."),
            ("Contrato", "detecting-contract-breaks", f"{Q}/skills/detecting-contract-breaks/SKILL.md", "Rota contract: contrato publicado, evento, migration ou superfície exportada."),
            ("Segurança", "reviewing-secrets", f"{Q}/skills/reviewing-secrets/SKILL.md", "Rota secrets (baseline): credencial escrita, viajando, embutida ou defaultada."),
            ("Segurança", "reviewing-supply-chain", f"{Q}/skills/reviewing-supply-chain/SKILL.md", "Rota supply-chain: dependência, imagem, pipeline ou registry."),
            ("Segurança", "reviewing-untrusted-input", f"{Q}/skills/reviewing-untrusted-input/SKILL.md", "Rota untrusted-input: entrada externa chegando a query, comando, caminho, URL, template."),
            ("Segurança", "reviewing-access", f"{Q}/skills/reviewing-access/SKILL.md", "Rota access: autenticação, autorização, dono, webhook, cross-origin."),
            ("Segurança", "reviewing-sensitive-data", f"{Q}/skills/reviewing-sensitive-data/SKILL.md", "Rota sensitive-data: o que é logado, devolvido, guardado e cifrado."),
            ("Segurança", "reviewing-model-use", f"{Q}/skills/reviewing-model-use/SKILL.md", "Rotas language-models e agent-authority: prompt, saída de modelo, ferramenta, instrução plantada."),
            ("Prompts", "reviewing-prompts", f"{Q}/skills/reviewing-prompts/SKILL.md", "Rotas de instrução: texto que um modelo lê como instrução."),
            ("Linguagens", "reviewing-python", "engineering/python/skills/reviewing-python/SKILL.md", "Rota python."),
            ("Linguagens", "reviewing-typescript", "engineering/typescript/skills/reviewing-typescript/SKILL.md", "Rota typescript."),
            ("Linguagens", "reviewing-go", "engineering/go/skills/reviewing-go/SKILL.md", "Rota go."),
            ("Linguagens", "reviewing-rust", "engineering/rust/skills/reviewing-rust/SKILL.md", "Rota rust."),
            ("Artefatos do framework", "reviewing-artifacts", "foundation/skills/reviewing-artifacts/SKILL.md", "Rota framework-artifacts: regra, doc, skill, agente ou comando do framework."),
            ("Documentos de apoio", "review-routes", f"{Q}/docs/review-routes.md", "O formato das rotas e por que a seleção é uma tabela."),
            ("Documentos de apoio", "review-findings", f"{Q}/docs/review-findings.md", "Os quatro campos de um achado e as quatro severidades."),
            ("Documentos de apoio", "review-verdicts", f"{Q}/docs/review-verdicts.md", "Quando o revisor aprova, e a separação que o auto-fix preserva."),
        ],
    },
    "erodos-system-prompts": {
        "title": "Erodos System Prompts",
        "eyebrow": "Ahrena · agente corretor",
        "lead": "O Erodos aplica as correções que a revisão achou e devolve o pull request — nunca revisa nem mescla. Seu contexto é curto: o agente, o procedimento, e o documento de achados que ele lê. A aba Orquestração mostra onde ele entra no ciclo.",
        "layers": [
            ("Agente", "`agents/erodos.md` diz que ele aplica o que o Argos achou, commita e devolve, e que não revisa nem mescla.", "sempre"),
            ("Procedimento", "`applying-fixes` seleciona os achados aplicáveis, aplica a menor mudança que cada um nomeia, confere e committa.", "sempre"),
            ("Contrato de entrada", "`review-findings` define o que torna um achado aplicável — campo a campo — e o que fica para uma pessoa.", "sempre"),
        ],
        "routes": False,
        "entries": [
            ("Agente", "erodos", f"{Q}/agents/erodos.md", "O corretor. Aplica as correções, commita e devolve; nunca revisa nem mescla."),
            ("Procedimento", "applying-fixes", f"{Q}/skills/applying-fixes/SKILL.md", "Seleciona os achados aplicáveis, aplica, confere, committa e devolve."),
            ("Contrato de entrada", "review-findings", f"{Q}/docs/review-findings.md", "Os quatro campos de um achado e as quatro severidades — o que o Erodos pode aplicar."),
            ("Decisão", "review-verdicts", f"{Q}/docs/review-verdicts.md", "Por que o corretor é um agente separado do revisor."),
        ],
    },
}


def body_of(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    head, _, body = text[4:].partition("\n---\n")
    described = ""
    for line in head.splitlines():
        key, sep, value = line.partition(":")
        if sep and key in ("description", "summary"):
            described = value.strip()
    return described, body.lstrip("\n")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"


def build_page(name: str, spec: dict, template: str) -> int:
    entries = []
    for group, ident, path, when in spec["entries"]:
        f = ROOT / path
        if not f.is_file():
            continue
        described, body = body_of(f.read_text(encoding="utf-8"))
        entries.append({"id": ident, "group": group, "name": ident, "source": path, "when": when,
                        "description": described, "text": body, "lines": body.count("\n") + 1})
    routes = []
    if spec["routes"]:
        table = json.loads((ROOT / Q / "skills/reviewing-diffs/references/routes.json").read_text(encoding="utf-8"))
        routes = table["routes"]
    data = {"title": spec["title"], "eyebrow": spec["eyebrow"], "lead": spec["lead"],
            "commit": git("rev-parse", "--short", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "layers": [{"name": n, "body": b, "when": w} for n, b, w in spec["layers"]],
            "routes": routes, "entries": entries, "orchestration": ORCHESTRATION, "flow": FLOW}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = HERE / name / "index.html"
    out.write_text(template.replace("/*__DATA__*/null", payload).replace("<!--TITLE-->", spec["title"]), encoding="utf-8")
    return len(entries)


def main() -> int:
    template = (HERE / "template.html").read_text(encoding="utf-8")
    for name, spec in PAGES.items():
        n = build_page(name, spec, template)
        print(f"{name}: {n} textos, {len(spec['entries'])} candidatos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
