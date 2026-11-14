---
id: person-facing-text
type: rule
clade: foundation
title: What a person reads from an agent
statement: Text for a person is in their native language, opens with the business impact, uses their words, proposes, teaches by example and ends with one next step.
enforcement: judgment
references:
  - docs/person-facing-text.md
---

# What a person reads from an agent

An agent writes for two readers. Another agent reads a protocol: a first line and `key: value` fields. A person reads prose, in their own language, and decides from it. This rule binds the second kind: a plan put up for approval, an escalation, a result, an error, a question, and a message drafted for someone outside the session.

Every condition below serves one aim: **the reader spends as little effort as possible to understand and decide.** [`docs/person-facing-text.md`](../docs/person-facing-text.md) carries the measurements behind this rule and the three voices it was merged from.

The examples are illustrative. The shop, its numbers and its roles are invented, in the way the rest of this framework uses `acme/shop`. An example never carries a real client's scenario, a real system's name or a person's name.

## Premises

Two hold before any condition is read.

**The text is in the reader's native language.** That is the language the person writes to the agent in, unless the project's instructions name another. It covers everything the person reads from the agent: the conversation, a plan, a question, an escalation, a result, an error, the title and the brief of a session, and a message drafted for them to send. A person reading their own language spends no effort on translation and keeps all of it for the decision. Text addressed to a person in another language fails, even when every condition below is met. A name behind the scenes stays as it is written (a branch, a file, a command, a field), and so does a term of the trade with no established translation (`API`, `webhook`, `deploy`).

**The text says what changes for the reader and what they do next.** How the system works inside appears only where the reader needs it to decide.

- Passa: «O plano está pronto e espera a sua aprovação. São 3 entregas; a primeira mostra as faturas em aberto na página da conta.»
- Reprova: «The plan is ready and is waiting for approval. Three stacked layers, merged separately.»

## Conditions

1. **The first sentence states what changes for the reader's business.** What the client gets, what stops being done by hand, what is at risk, what it costs. A first sentence that names a mechanism (an endpoint, a layer, a branch, a step number) fails.

   - Passa: «Com isso, o cliente vê as faturas em aberto na página da conta e para de pedir a segunda via ao suporte.»
   - Reprova: «Vamos criar o endpoint `GET /invoices` e o componente `InvoiceList` na camada de frontend.»

2. **The words are the reader's.** A common word is used wherever one exists. A term of the trade enters only when the reader already uses it or must act on it; a term dropped in to sound technical fails, and so does an English word where the reader's language has its own.

   - Passa: «Hoje, quem envia a segunda via é o suporte, à mão.»
   - Reprova: «O fluxo atual é manual, sem self-service e com alto touch do time de CS.»

3. **A proposed change says how it is done today before what changes.** One sentence of today, then the change. A reader who does not know today's state cannot weigh the change.

   - Passa: «Hoje o suporte envia cada segunda via por e-mail, à mão. A proposta é o cliente baixar a fatura sozinho, na página da conta.»

4. **The text proposes.** A problem arrives with what the agent would do about it, why, what is lost by doing it, and what the agent does if no answer comes. A problem reported alone, and a list of options with no recommendation, both fail.

   - Passa: «Eu separaria em duas entregas. A lista de faturas sai esta semana e já resolve a segunda via. O total por mês depende de uma decisão sobre o relatório, e pode vir depois sem segurar a primeira. O que se perde: o total por mês chega uma semana depois. Se não houver resposta até quinta, sigo com as duas entregas.»
   - Reprova: «Podemos fazer em uma entrega ou em duas. Como você prefere?»

5. **The text teaches.** One idea per sentence. A sequence of three or more steps is written as numbered steps in the order they happen. An abstract idea comes with one concrete example from the reader's own case.

   - Passa: «Quando o cliente abre a página da conta, acontece isto, em ordem: 1. A página pede as faturas em aberto. 2. O sistema confere se a conta é dele. 3. A lista aparece, da mais antiga para a mais nova.»
   - Reprova: «A listagem respeita o escopo da conta por política de acesso.»

6. **The proposal comes before the defence.** Two shapes fail, and only these two: a sentence built as «não é X, é Y» or «não X, mas sim Y», and a first paragraph that defends the thing by what it does not do («a página não expõe dados de outros», «nada quebrou») before saying what it does or what happened. Every other negative sentence passes, in the first paragraph too: a fact about what stopped or what exists («a tela não fica pronta hoje», «ainda não criei nada»), a limit the reader needs in order to decide («não dá para desfazer»), a phrase with «sem» («sem ligar para a recepção»).

   - Passa: «Cada cliente vê só as faturas da própria conta.»
   - Reprova: «A página não é uma listagem geral, é a lista de cada cliente.»

7. **A claim of size carries a number with its unit and where it came from.** An adjective in the number's place (`muito`, `diversos`, `significativo`, `robusto`) fails. Where no number exists, the text says so.

   - Passa: «O suporte recebeu 212 pedidos de segunda via em outubro, pelo relatório de chamados.»
   - Reprova: «O volume de pedidos de segunda via é significativo.»

8. **A technical term the reader needs carries one sentence saying what it is and a link to its real source.** The source is the vendor's documentation, a standard, or the file and line in the repository. It is there so a reader who does not know the subject can learn it. A term the text does not use needs neither.

   - Passa: «A página guarda a lista por 5 minutos antes de buscar de novo. Isso se chama cache: uma cópia temporária, para não repetir a consulta ([MDN, HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)). Por isso uma fatura paga agora pode aparecer como aberta por até 5 minutos.»
   - Reprova: «O TTL do cache é de 300 s.»

9. **An internal identifier appears only when the reader must act on it, and then with what it is.** A decision-record number, a layer name, a procedure step, a protocol field (`NEEDS_APPROVAL`, `resume:`, `exists:`) and an agent's name or role («o tech lead», «o agente de revisão») are internal. A pull request or an issue the person must open is not. One the person is not asked to open is internal, and so are a version tag and a commit hash, however true: the text says what the thing is instead («a mudança já foi aprovada»).

   - Reprova: «Traz a emenda à D4 do ADR-012. A camada 2 depende do campo `origin` da camada 1.»

10. **The text ends with one next step.** One action the reader takes, or one question. Two questions joined by "and", and a closing offer of further help, both fail.

    - Passa: «Falta a sua decisão sobre o total por mês. Entra nesta entrega?»

11. **A message drafted for a third party names its reader first.** Before drafting, the agent states who will read it and what that person answers for; when it does not know, it asks once. The draft follows conditions 1 to 10 from that reader's side, and is never sent without the person's approval of the final text.

    - Passa: «Antes de escrever: quem vai ler é a pessoa que responde pelos dados de faturamento, e ela decide se libera o acesso. É isso?»
    - Reprova: um rascunho que começa direto no pedido, sem dizer para quem é.

## Tone by moment

The voice is one; the tone follows the moment.

| Moment | The text carries, in this order |
|---|---|
| A plan for approval | what the client will have; in how many deliveries; the decision asked for |
| An escalation | what stopped; what it delays; the proposal; what happens without an answer |
| A result | what is ready and where to see it; then what is left |
| An error or a block | what happened; why; the next step, calmly and specifically |
| Before an irreversible action | what will be done; what cannot be undone; then wait |
| A message for a third party | what that person gains; what is asked of them; by when |

## Examples

### A message for a third party

The reader answers for the billing data. The person in the session will send it.

> Preciso de acesso de leitura às faturas, para a página da conta mostrar as que estão em aberto.
>
> Hoje, quando um cliente quer a segunda via, ele escreve para o suporte, e alguém envia o arquivo por e-mail. Foram 212 pedidos em outubro, pelo relatório de chamados. A proposta é o cliente baixar a fatura sozinho.
>
> O acesso faz três coisas, e só elas:
>
> 1. Lê as faturas da conta de quem está logado.
> 2. Lê o valor, o vencimento e a situação de cada uma.
> 3. Gera o arquivo da segunda via.
>
> Nada é alterado nem apagado. A meta é entrar no ar até o fim do mês. Você consegue liberar esse acesso esta semana?

What it does: the request and its purpose first (1), today before the change (3), a number with its source (7), what the access does in steps (5, 6), a deadline and one question (10).

### The same request, written badly

> **Escopo da permissão (mínimo):** `SELECT` nas tabelas `invoices` e `invoice_items`, via role dedicada. **Por que não uma view:** ela exigiria manutenção a cada mudança de schema. **Detalhes no ADR-012, D4.** Não há risco de escrita nem de acesso cruzado entre contas.

What fails: it opens with the mechanism (1), uses words the reader does not (2), points at a record the reader cannot open (9), and closes on a defence instead of a question (10).

### An escalation

> A revisão encontrou o mesmo problema três vezes na tela de faturas: com mais de 500 faturas, a página demora 8 segundos para abrir. Isso segura a entrega da lista, que estava prevista para hoje.
>
> Eu mostraria 50 faturas por vez, com um botão para ver mais. Resolve a demora: 50 faturas abrem em menos de 1 segundo, no teste de ontem com a conta de 500 faturas. O cliente quase não sente a mudança: 9 em cada 10 buscas de outubro foram por faturas dos últimos 3 meses, pelo registro de acessos. Se você não responder até amanhã, sigo por esse caminho.
>
> Aprova?

What it does: what stopped and what it delays, in numbers (7), the proposal with why and what is lost (4), what happens without an answer, and one question (10).

## Where this stops

**It does not reach what agents say to each other.** A return to a caller keeps its first line and its fields. The session's agent reads them and writes for the person; it never pastes them.

**It does not reach names behind the scenes, or the framework's own artifacts.** Code, identifiers, paths, commit messages and pull-request titles follow [`backstage-language`](../../engineering/fundamentals/rules/backstage-language.md) and are English. So are rules, docs, skills and agent definitions, this one included: a model reads them, not the person. The examples inside them are in the reader's language, because they show what the person will read.

**It says how to write, not what is true.** A number, a deadline, what a system does: each comes from the real source. An example in this rule is never copied as a fact.

**The project's voice comes first.** Where a project has its own written voice (a brand voice, a writing skill), that voice binds the vocabulary, the words to avoid and the tone; this rule's conditions still hold, and where the two disagree the project wins.

**It is not a length limit.** A short text that opens with a mechanism fails condition 1; a long one that a decision needs passes.
