# Artefatos

Páginas publicadas no claude.ai que explicam este framework. O arquivo aqui é a fonte da
verdade; o claude.ai guarda só a cópia do momento da publicação. Cada pasta tem o
`index.html` e um `artifact.json` com o link por organização.

| Pasta | O que é |
|---|---|
| `argos-system-prompts/` | O revisor Argos: camadas do prompt, roteador e skills (aba Prompts) e o ciclo de review (aba Orquestração). |
| `erodos-system-prompts/` | O corretor Erodos: agente, `applying-fixes` e o contrato de achados (aba Prompts) e seu lugar no ciclo (aba Orquestração). |

`build.py` gera os dois `index.html` a partir dos arquivos deste repositório
(`engineering/quality` e irmãos). Uma entrada cujo arquivo não existe no checkout é
ignorada, então o mesmo build roda contra a `main` ou contra uma branch. Rode-o e
republique com a skill `ahrena-artifacts`; as páginas são privadas.

```bash
python3 artifacts/build.py
```
