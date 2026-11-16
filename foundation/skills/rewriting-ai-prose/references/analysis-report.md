# O relatório do modo analyze

O modo `analyze` não muda o texto. Devolve este relatório na língua do leitor, para que a pessoa leia e decida se reescreve. Os três blocos abaixo são o primeiro passo de uma reescrita, escrito por extenso.

## Os blocos

1. **Veredito.** Uma de três palavras, `nenhum`, `algum` ou `a maior parte`, sobre quanto do texto parece escrito por máquina, e o porquê em até três frases. O veredito é um julgamento editorial sobre o texto como ele está. Não é uma medida nem uma probabilidade, e não diz quem escreveu o texto: um texto humano pode ter todos os sinais e um texto de máquina pode não ter nenhum.
2. **Sinais encontrados.** Uma lista por família e por força (`forte`, `médio`, `fraco`), com o trecho exato ou o número da linha e a correção que o sinal pede. Um sinal fraco só entra com companhia, como diz o passo 3 do `SKILL.md`. Um trecho por linha; a mesma ocorrência repetida vira uma linha com a contagem.
3. **Fatos a manter.** Todo nome, número, data, link, citação, prazo, condição e responsável do texto, um por linha. Um fato por linha basta; não se interpreta nem se reordena. É a lista que o passo de conferência de uma reescrita usa depois.

Termine com uma frase que diga o que a pessoa pode pedir a seguir: reescrever, reescrever só um trecho, ou deixar como está.

## Como o relatório cita um sinal

O nome da família e o do padrão vêm de `patterns-pt-br.md`, em português simples (por exemplo «encenar em vez de afirmar», «Não é X, é Y»). Não cite o id da lista.

## Exemplo

Caso inventado. O texto analisado:

> Vamos mergulhar no novo checkout da Acme Shop. Ele não é só mais rápido, é uma nova jornada de compra. O frete é grátis acima de R$ 150 — e o prazo caiu de 5 para 3 dias úteis. Em suma, uma solução robusta. Espero ter ajudado!

O relatório:

> **Veredito: a maior parte.** O texto traz uma encenação de entrada, um contraste que ninguém pediu, palavras infladas e uma sobra de chat, e quase todo o conteúdo concreto cabe em duas frases. Os fatos estão intactos; o que pesa é a embalagem.
>
> **Sinais**
> - Encenar em vez de afirmar, forte: «Vamos mergulhar no novo checkout da Acme Shop.» Corte a entrada e comece pelo fato.
> - Encenar em vez de afirmar, forte: «Ele não é só mais rápido, é uma nova jornada de compra.» Diga o que muda: o prazo.
> - Inflação, médio: «jornada de compra», «solução robusta». Nomeie a propriedade concreta ou corte.
> - Encenar em vez de afirmar, forte: «Em suma, uma solução robusta.» Repete o que o texto já disse.
> - Ritmo por regra, fraco: um travessão em «R$ 150 — e o prazo». Um só; não justifica edição sozinho.
> - Sobras do chat, forte: «Espero ter ajudado!» Apague.
>
> **Fatos a manter**
> - Frete grátis acima de R$ 150.
> - Prazo de entrega: de 5 para 3 dias úteis.
> - O checkout é novo e é descrito como mais rápido.
>
> Posso reescrever o texto inteiro, reescrever só um trecho ou deixar como está.

Neste exemplo o «mais rápido» é uma afirmação do autor e fica entre os fatos a manter, mesmo sem número que a sustente.
