#!/usr/bin/env python3
"""Build the explainer pages for the review agents, from this repository.

    python3 artifacts/build.py

One page per agent under artifacts/<page>/, generated from the repo's own
engineering/quality (and sibling) files and a shared template. Each page has two
tabs: the prompt composition (layers, routes, the text of each artifact) and the
orchestration (a diagram and prose focused on how THAT agent operates). An entry
whose file is absent on the current checkout is skipped, so the same build runs
against main or a branch. The page only carries the drawing and the texts;
publishing is the ahrena-artifacts skill's job.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
Q = "engineering/quality"


def node(x, y, w, h, lb, sub="", cls="nd", rx=8):
    cx = x + w / 2
    t = f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>'
    if sub:
        t += f'<text class="lb" x="{cx}" y="{y+h/2-2}" text-anchor="middle">{lb}</text>'
        t += f'<text class="sub" x="{cx}" y="{y+h/2+15}" text-anchor="middle">{sub}</text>'
    else:
        t += f'<text class="lb" x="{cx}" y="{y+h/2+5}" text-anchor="middle">{lb}</text>'
    return f"<g>{t}</g>"


def svg(viewbox, body):
    return (f'<svg viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;max-width:720px">'
            '<defs><marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--dim)"/></marker></defs>'
            + body + '</svg>')


# Argos: the reviewer's own pipeline, with the verdict and its hand-offs.
ARGOS_FLOW = svg("0 0 720 440", "".join([
    '<path class="ed" d="M360,66 V96"/>',
    '<text class="el" x="360" y="173" text-anchor="middle">o roteador seleciona quais disciplinas rodam</text>',
    '<path class="ed" d="M360,148 L74,184"/>',
    '<path class="ed" d="M360,148 L214,184"/>',
    '<path class="ed" d="M360,148 L354,184"/>',
    '<path class="ed" d="M360,148 L494,184"/>',
    '<path class="ed" d="M360,148 L634,184"/>',
    '<path class="ed" d="M74,242 L350,292"/>',
    '<path class="ed" d="M214,242 L355,292"/>',
    '<path class="ed" d="M354,242 L360,292"/>',
    '<path class="ed" d="M494,242 L365,292"/>',
    '<path class="ed" d="M634,242 L370,292"/>',
    '<path class="ed" d="M360,344 V372"/>',
    node(220, 14, 280, 52, "argos — agente revisor", "orquestra as skills abaixo, na ordem", cls="nd b"),
    node(230, 96, 260, 52, "reviewing-diffs", "fixa base e head · roda o roteador"),
    node(8, 184, 132, 58, "contrato", "contract-breaks"),
    node(148, 184, 132, 58, "segurança", "6 disciplinas"),
    node(288, 184, 132, 58, "prompts", "reviewing-prompts"),
    node(428, 184, 132, 58, "linguagem", "4 revisores"),
    node(568, 184, 132, 58, "artefatos", "reviewing-artifacts"),
    node(220, 292, 280, 52, "publishing-review-verdicts", "decide e publica o veredito"),
    node(210, 372, 300, 52, "landing-approved-changes", "só após approve · pede o squash-merge"),
]))

# Erodos: the fixer's own procedure, start to hand-back.
ERODOS_FLOW = svg("0 0 720 452", "".join([
    '<path class="ed" d="M300,56 V80"/>',
    '<path class="ed" d="M300,140 V166"/>',
    '<path class="ed" d="M300,214 V240"/>',
    '<path class="ed" d="M300,288 V314"/>',
    '<path class="ed" d="M300,362 V388"/>',
    '<path class="ed ed-d" d="M430,109 H470"/>',          # seleciona -> nao aplicavel (right)
    '<path class="ed ed-d" d="M430,189 H470"/>',          # aplica -> segredo note (right)
    '<path class="ed ed-d" d="M400,411 H470"/>',          # devolve -> Argos (right)
    node(200, 16, 200, 40, "achados do Argos", cls="nd b"),
    node(170, 80, 260, 60, "seleciona os aplicáveis", "bloqueante/deferrable · correção concreta"),
    node(470, 80, 220, 60, "não aplicável → uma pessoa", "pergunta · unchecked · decisão", cls="nd d"),
    node(160, 166, 280, 48, "aplica só o que o achado nomeia"),
    node(470, 160, 230, 60, "segredo", "conserta no código · rotação humana", cls="nd d"),
    node(190, 240, 220, 48, "confere com os testes"),
    node(210, 314, 180, 48, "commita e dá push"),
    node(220, 388, 160, 46, "devolve o PR"),
    node(470, 388, 230, 46, "Argos revisa de novo", cls="nd d"),
    '<text class="el" x="360" y="446" text-anchor="middle">nunca revisa · nunca mescla</text>',
]))

ARGOS_ORCH = """\
## Como o Argos opera

O Argos é o revisor. Numa passada ele fixa a base e o head, roda o roteador (um script que lê a mudança contra a tabela de rotas e diz quais disciplinas tocam o diff), delega a cada disciplina selecionada, junta os achados e decide **um** veredito a partir deles — sem olhar a história:

- um achado **bloqueante** → pede mudança;
- uma **pergunta** ou condição **unchecked**, sem bloqueante → comentário (a revisão não terminou);
- nada que trave → **aprova**.

Ao aprovar, ele pede ao forge (o GitHub) para fazer o **squash-merge do commit exato que revisou**, só com os checks verdes. Ele não dá push na trunk nem decide sozinho: quem mescla é o forge, pelas regras dele.

A mudança bloqueante vai para o **Erodos** — um agente separado, para que o Argos nunca leia a própria edição — e o commit que o Erodos devolve volta a esta mesma revisão. Quatro casos ele deixa para uma pessoa, aconteça o que acontecer: registro de decisão, camada de stack, draft e pull request de fork externo. `ADR-013` registra por que a revisão limpa aprova e mescla.
"""

ERODOS_ORCH = """\
## Como o Erodos opera

O Erodos é o corretor, e só entra depois que o Argos publicou os achados. Ele nunca revisa e nunca mescla — aplica o que já foi achado e devolve, para o Argos revisar de novo. O procedimento:

1. **Seleciona os aplicáveis:** achado `blocking` ou `deferrable`, com correção que é uma instrução concreta, numa disciplina onde aplicar muda só o que o achado nomeou. `question` e `unchecked`, e qualquer correção que exija uma decisão, ficam para uma pessoa.
2. **Aplica a menor mudança** que cada achado nomeia — nada além disso.
3. **Segredo tem ressalva:** ele troca o literal por leitura do cofre, mas a credencial que entrou no histórico precisa de **rotação**, que é ação humana e segura o merge até ser feita.
4. **Confere** com os testes do projeto (quando pode executar), **commita e dá push**, e **devolve o pull request**.

Num fork externo ele não aplica nada — rodaria o código do autor na máquina —, igual à recusa do Argos. O ciclo é limitado: o que não fecha depois do limite de tentativas vai para uma pessoa. `ADR-014` registra por que o corretor é um agente à parte do revisor.
"""

PAGES = {
    "argos-system-prompts": {
        "title": "Argos System Prompts",
        "eyebrow": "Ahrena · agente revisor",
        "lead": "O Argos não tem um prompt único. O que ele lê numa revisão é montado em camadas: o agente está sempre lá, e o resto só entra quando a mudança pede. A aba Orquestração mostra como ele opera.",
        "layers": [
            ("Agente", "`agents/argos.md` diz o que o Argos é, quais skills ele orquestra e o que ele se recusa a fazer.", "sempre"),
            ("Roteador", "`route-review.py` lê a mudança contra `routes.json` e imprime as rotas que dispararam. É um script: não gasta contexto.", "sempre"),
            ("Skills", "Cada rota aponta uma skill de revisão. Só as apontadas são carregadas.", "por rota"),
            ("Checklists e regras", "As condições ficam em `references/` e nas regras do `fundamentals`. Cada arquivo só abre pela rota que o nomeia.", "por rota"),
        ],
        "routes": True,
        "flow": ARGOS_FLOW,
        "orchestration": ARGOS_ORCH,
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
        "lead": "O Erodos aplica as correções que a revisão achou e devolve o pull request — nunca revisa nem mescla. Seu contexto é curto: o agente, o procedimento, e o documento de achados que ele lê. A aba Orquestração mostra como ele opera.",
        "layers": [
            ("Agente", "`agents/erodos.md` diz que ele aplica o que o Argos achou, commita e devolve, e que não revisa nem mescla.", "sempre"),
            ("Procedimento", "`applying-fixes` seleciona os achados aplicáveis, aplica a menor mudança que cada um nomeia, confere e committa.", "sempre"),
            ("Contrato de entrada", "`review-findings` define o que torna um achado aplicável — campo a campo — e o que fica para uma pessoa.", "sempre"),
        ],
        "routes": False,
        "flow": ERODOS_FLOW,
        "orchestration": ERODOS_ORCH,
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
            "commit": git("rev-parse", "--short", "HEAD"),
            "layers": [{"name": n, "body": b, "when": w} for n, b, w in spec["layers"]],
            "routes": routes, "entries": entries, "orchestration": spec["orchestration"]}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = HERE / name / "index.html"
    html = template.replace("/*__DATA__*/null", payload).replace("<!--TITLE-->", spec["title"]).replace("<!--FLOW-->", spec["flow"])
    out.write_text(html, encoding="utf-8")
    return len(entries)


def main() -> int:
    template = (HERE / "template.html").read_text(encoding="utf-8")
    for name, spec in PAGES.items():
        n = build_page(name, spec, template)
        print(f"{name}: {n} textos, {len(spec['entries'])} candidatos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
