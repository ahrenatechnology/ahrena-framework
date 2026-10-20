#!/usr/bin/env python3
"""Tests for check-backstage-language.py.

A detector that never accepts is as broken as one that never rejects, so every
name position below is pinned by a fixture that must fail and by the screen
text beside it that must not. Each case builds a throwaway tree, runs the hook
against it as a subprocess, and asserts on the exit code and the message.

This file is authored pointer-clean: it carries no bare prose `#` comment, only
word-free separators, and all rationale sits in docstrings.

Usage:
    python3 engineering/fundamentals/hooks/test-check-backstage-language.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "check-backstage-language.py"

CLEAN_TS = """
const fetchSessions = async () => fetch("/api/sessions?page=2");
type Props = { title: string; portal: string };
"""

DIACRITIC_TS = "const sessão = 1;\nfunction atençãoAqui() {}\n"

WORD_TS = """
const buscarSessoes = async () => 1;
const PORT = process.env.PORTA_CONSOLE;
const route = "/api/sessoes/:id";
"""

PARTIAL_WORDS = "const portal = 1;\nconst dadosx = 2;\nconst data = 3;\nconst total = 4;\n"

SCREEN_TEXT_TSX = """
export function Card({ title }: Props) {
  const label = "Sessões ativas";
  const fallback = title ? "Dados" : "Sem dados";
  return (
    <div className="card">
      Sessões: {title}
      {/* comentário em português sobre a sessão */}
      <p>Atenção: dados carregados</p>
    </div>
  );
}
"""

SCREEN_TEXT_PY = '''
def load_sessions():
    """Carrega as sessões e devolve os dados."""
    message = "Sessão não encontrada"
    # comentário com a palavra sessao e atenção
    return message
'''

POSITIONS = {
    "a.ts": 'type Props = {\n  titulo: string;\n};\nconst options = { "rotulo": 1 };\nconst flag = "--porta";\n',
    "b.tsx": 'export const Card = () => <div className="card titulo-card" />;\n',
    "c.py": "def obter_dados():\n    nome = 1\n    return nome\n",
    "d.json": '{"sessao": {"label": "Sessão"}}\n',
    "e.css": ".titulo-grande, .ok {\n  color: #fff;\n}\n",
    "f.sql": "CREATE TABLE sessoes (\n  id uuid,\n  titulo text\n);\n",
    ".env": "PORTA=3000\nAPI_URL=http://localhost\n",
    "g.yaml": "rotulos:\n  - label: x\n",
}

POINTER_LINE = "const razaoSocial = row.razao; // ADR-021 a field of the government API\n"

# ----------------------------------------------------------------------------

BASELINE = "@baseline"
ARGS = "@args"
COMMITTED = "@committed"
RESERVED = (BASELINE, ARGS, COMMITTED)

GIT_IDENTITY = ("-c", "user.email=gate@example.invalid", "-c", "user.name=gate", "-c", "commit.gpgsign=false")


def case(name: str, files: dict, expect: list[str], ok: bool = False, absent: tuple = ()) -> tuple:
    return (name, files, expect, ok, absent)


CASES = [
    case("a clean file passes", {"a.ts": CLEAN_TS}, ["1 file(s), no failures"], ok=True),
    # ----------------------------------------------------------------------------
    case(
        "a name with a Portuguese diacritic fails (#215/AC-1)",
        {"a.ts": DIACRITIC_TS},
        ["a.ts:1", "'sessão'", "a.ts:2", "'atençãoAqui'", "diacritic"],
    ),
    case(
        "a name with a listed Portuguese segment fails (#215/AC-2)",
        {"a.ts": WORD_TS},
        ["'buscarSessoes'", "'PORTA_CONSOLE'", "'/api/sessoes/:id'", "the English is 'sessions'"],
    ),
    case(
        "a segment that only contains a listed word, or is English, passes (#215/AC-2)",
        {"a.ts": PARTIAL_WORDS},
        ["no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "every name position is read (#215/AC-3)",
        POSITIONS,
        [
            "a.ts:2",
            "'titulo'",
            "'rotulo'",
            "'porta'",
            "'titulo-card'",
            "'obter_dados'",
            "'nome'",
            "'sessao'",
            "'titulo-grande'",
            "'sessoes'",
            "'PORTA'",
            "'rotulos'",
        ],
        absent=("condition 1: 'ok'", "condition 1: 'label'", "API_URL"),
    ),
    case(
        "Portuguese in a string, a comment, a docstring or JSX text passes (#215/AC-3)",
        {"a.tsx": SCREEN_TEXT_TSX, "b.py": SCREEN_TEXT_PY},
        ["2 file(s), no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "a Portuguese path segment fails (#215/AC-4)",
        {"src/sessoes/list.md": "text\n"},
        ["src/sessoes/list.md", "condition 2", "'sessoes'"],
    ),
    case(
        "under --changed, an added path fails (#215/AC-4)",
        {BASELINE: {"a.md": "x\n"}, ARGS: ["--changed", "--cached", "."], "relatorios/a.md": "x\n"},
        ["relatorios/a.md", "condition 2"],
    ),
    case(
        "under --changed, an edited file keeps its path unchecked (#215/AC-4)",
        {BASELINE: {"relatorios/a.md": "x\n"}, ARGS: ["--changed", "--cached", "."], "relatorios/a.md": "y\n"},
        ["no failures"],
        ok=True,
    ),
    # ----------------------------------------------------------------------------
    case(
        "a Portuguese name on a line the change did not touch is out of scope (#215/AC-5)",
        {
            BASELINE: {"a.ts": "const sessao = 1;\n"},
            ARGS: ["--changed", "--cached", "."],
            "a.ts": "const sessao = 1;\nconst session = 2;\n",
        },
        ["no failures"],
        ok=True,
    ),
    case(
        "a Portuguese name on a line the change adds is flagged (#215/AC-5)",
        {
            BASELINE: {"a.ts": "const session = 1;\n"},
            ARGS: ["--changed", "base...HEAD", "."],
            COMMITTED: True,
            "a.ts": "const session = 1;\nconst sessao = 2;\n",
        },
        ["a.ts:2", "'sessao'"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "a line carrying an ADR pointer is exempt (#215/AC-6)",
        {"a.ts": POINTER_LINE},
        ["no failures"],
        ok=True,
    ),
    case(
        "--exclude leaves a path out of the run (#215/AC-6)",
        {ARGS: ["--exclude", "fixtures/*", "."], "fixtures/api.json": '{"razao_social": 1}\n', "a.ts": CLEAN_TS},
        ["1 file(s), no failures"],
        ok=True,
    ),
    case(
        "--exclude with no glob is an error, not a pass",
        {ARGS: [".", "--exclude"], "a.ts": WORD_TS},
        ["--exclude needs a glob"],
    ),
    # ----------------------------------------------------------------------------
    case(
        "--changed with no revision is an error, not a pass (#215/AC-7)",
        {ARGS: ["--changed"], "a.ts": WORD_TS},
        ["needs a revision or range"],
    ),
    case(
        "--changed outside a repository is an error, not a pass (#215/AC-7)",
        {ARGS: ["--changed", "HEAD", "."], "a.ts": WORD_TS},
        ["backstage-language:"],
    ),
    case(
        "--changed --name-only is refused, not read as a clean tree (#215/AC-7)",
        {BASELINE: {"a.ts": CLEAN_TS}, ARGS: ["--changed", "--name-only", "."], "a.ts": WORD_TS},
        ["is not a revision or range"],
    ),
]


def write(root: Path, files: dict) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *GIT_IDENTITY, *args], cwd=str(root), capture_output=True, check=True)


def commit(root: Path, subject: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", subject)


def prepare(root: Path, files: dict) -> None:
    """The repository the hook meets: a baseline commit, then the change over it."""
    write(root, files[BASELINE])
    git(root, "init", "-q")
    commit(root, "the tree before the change")
    git(root, "tag", "base")
    write(root, {rel: text for rel, text in files.items() if rel not in RESERVED})
    git(root, "add", "-A")
    if files.get(COMMITTED):
        commit(root, "the change under review")


def run(files: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if BASELINE in files:
            prepare(root, files)
        else:
            write(root, {rel: text for rel, text in files.items() if rel not in RESERVED})
        result = subprocess.run(
            [sys.executable, str(HOOK), *files.get(ARGS, ["."])], cwd=str(root), capture_output=True, text=True
        )
        return result.returncode, result.stdout + result.stderr


def problems_for(expect: list[str], ok: bool, absent: tuple, code: int, output: str) -> list[str]:
    found = []
    if ok and code != 0:
        found.append("expected the hook to pass, it failed")
    if not ok and code == 0:
        found.append("expected the hook to fail, it passed")
    found.extend(f"expected {fragment!r} in the output" for fragment in expect if fragment not in output)
    found.extend(f"did not expect {fragment!r} in the output" for fragment in absent if fragment in output)
    return found


def main() -> int:
    failed = 0
    for name, files, expect, ok, absent in CASES:
        code, output = run(files)
        problems = problems_for(expect, ok, absent, code, output)
        if not problems:
            print(f"ok    {name}")
            continue
        failed += 1
        print(f"FAIL  {name}")
        for problem in problems:
            print(f"        {problem}")
        print("      --- hook output ---")
        for line in output.splitlines():
            print(f"      {line}")

    print()
    if failed:
        print(f"{failed} of {len(CASES)} cases failed.")
        return 1
    print(f"{len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
