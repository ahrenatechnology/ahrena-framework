# Padrões de texto com cara de máquina, em português

Lista de sinais que um editor procura em um texto em pt-BR, do mais forte ao mais fraco dentro de cada família. Cada padrão tem o que procurar, por que pesa, um antes e um depois.

Os exemplos usam um caso inventado, a loja Acme Shop (frete, cupom, prazo). Nenhuma pessoa, cliente ou sistema real aparece neles. O depois nunca acrescenta um fato que o antes não tenha.

Os padrões que uma expressão regular decide têm o mesmo id em `deterministic-patterns.json`; os outros dependem de um leitor e não têm regex. Um padrão marcado como `fraco` não justifica uma edição sozinho: precisa de companhia de outros sinais no mesmo trecho.

## Índice

- Família 1, encenar em vez de afirmar: `not-x-but-y`, `not-only-but-also`, `not-split-contrast`, `staged-opener`, `closer-phrase`, `closer-fragment`, `deep-saying`, `arguing-with-no-one`
- Família 2, ritmo por regra: `forced-triad`, `repeated-openings`, `dash-connector`, `stacked-hedges`
- Família 3, inflação: `inflated-verbs`, `inflated-words`, `inflated-scene`, `inflated-significance`, `borrowed-authority`, `avoiding-is-has`
- Família 4, formatação por regra: `bold-labels`, `emoji-markers`, `decorative-headings`
- Família 5, sobras do chat e do rascunho: `chatbot-opener`, `chatbot-closer`, `chatbot-self-reference`, `chatbot-handoff`, `document-announces-itself`, `heading-repeated`
- Família 6, leitor errado: `re-explaining`
- Família 7, vícios do português: `gerundismo`, `officialese`, `enem-ism`
- Quando não agir

## Família 1, encenar em vez de afirmar

Os sinais mais fortes e mais frequentes. Um avistamento já justifica a edição.

### 1. «Não é X, é Y» (`not-x-but-y`)

**Procure:** «não é só um relatório, é uma decisão»; «não foi sorte, foi método»; «não é custo, é investimento»; a forma invertida «X em vez de Y»; um rabo seco no fim da frase («..., sem achismo»).

**Problema:** A metade negativa nega algo que ninguém disse, e a positiva parece maior por contraste. Não acrescenta afirmação. Diga o ponto direto. Mantenha o contraste só quando a negação corrige uma crença que o leitor tem de fato, ou quando as duas metades informam.

**Antes:**
> O frete grátis acima de R$ 150 não é um custo, é um argumento de venda.

**Depois:**
> O frete grátis acima de R$ 150 é um argumento de venda.

### 2. «Não apenas… mas também» (`not-only-but-also`)

**Procure:** «não apenas X, mas também Y»; «não só X, como também Y»; «além de X, também Y» repetido em todo parágrafo.

**Problema:** A construção promete duas coisas grandes e entrega duas frases comuns. O peso vem da fórmula, não do conteúdo. Escreva as duas informações como duas orações simples.

**Antes:**
> O novo checkout não apenas reduz o prazo de entrega de 5 para 3 dias úteis, mas também melhora a experiência de compra.

**Depois:**
> O novo checkout reduz o prazo de entrega de 5 para 3 dias úteis e melhora a experiência de compra.

A afirmação vaga «melhora a experiência de compra» é do autor e fica no texto. A lacuna (qual melhoria, medida como) vai para o relatório; a prova não se inventa.

### 3. Contraste partido em duas frases (`not-split-contrast`)

**Procure:** «Isso não significa X. Significa Y.»; «Não se trata de X, mas de Y.»; «A questão não é X. É Y.»

**Problema:** O mesmo «não é X, é Y» espalhado por duas frases ou por um parágrafo. A escala maior não muda o defeito.

**Antes:**
> Isso não significa que todo pedido é urgente. Significa que o atraso custa caro, R$ 12 por dia.

**Depois:**
> Nem todo pedido é urgente, mas cada dia de atraso custa R$ 12.

### 4. Entrada encenada (`staged-opener`)

**Procure:** «vamos mergulhar», «vamos explorar», «vamos desvendar»; «vale ressaltar», «vale destacar», «vale a pena mencionar»; «é importante destacar que», «é fundamental notar que»; «cumpre salientar»; «sem mais delongas»; «o que você precisa saber».

**Problema:** O autor anuncia o ponto ou encena importância em vez de fazer o ponto. Tire a entrada inteira, não só o tom. «Vale lembrar» dentro de uma frase informal é comum; o sinal é a abertura solta antes de uma afirmação de rotina.

**Antes:**
> Vamos mergulhar no funcionamento do frete. Vale ressaltar que ele é grátis acima de R$ 150.

**Depois:**
> O frete é grátis acima de R$ 150.

### 5. Fecho em fórmula (`closer-phrase`)

**Procure:** «em suma», «em resumo», «em síntese», «em conclusão», «no fim do dia», «ao final do dia», «no fim das contas», «em última análise», «para concluir», «diante do exposto».

**Problema:** O fecho repete o que o texto acabou de dizer e finge uma conclusão. Corte, ou troque pelo próximo passo ou pela consequência que o texto ainda não disse. «No fim do dia» no meio de uma frase sobre horário é uso comum; o sinal é a fórmula no começo da frase final.

**Antes:**
> O cupom vale na primeira compra e o frete é grátis acima de R$ 150. Em suma, o novo fluxo é mais simples e vantajoso para todos.

**Depois:**
> O cupom vale na primeira compra e o frete é grátis acima de R$ 150.

### 6. Frase solta que repete (`closer-fragment`)

**Procure:** «Esse é o verdadeiro ganho.»; «Essa é a grande diferença.»; «E isso muda tudo.»; «Simples assim.»; «Pense nisso.»; o mesmo fecho depois de várias seções; uma fileira de fragmentos («Sem filas. Sem espera. Sem estresse.»).

**Problema:** A linha pede que o leitor pare em uma afirmação em vez de acrescentar algo. Uma frase curta serve quando traz um fato novo. Corte a que repete, inclusive a que explica um exemplo que o leitor acabou de ver. Una a fileira de fragmentos em uma frase com afirmação específica.

**Antes:**
> O cache evita refazer o cálculo do frete a cada clique.
>
> Esse é o verdadeiro ganho.

**Depois:**
> O cache evita refazer o cálculo do frete a cada clique.

### 7. Máxima que soa profunda (`deep-saying`)

**Procure:** «no fundo», «em sua essência», «a verdadeira questão é», «o que realmente importa é», «a chave está em», «o coração do», «X é a linguagem de Y», «X não é uma ferramenta, é um espelho».

**Problema:** Um ponto comum vestido de verdade escondida, sem nenhum detalhe a mais. Troque a máxima pela afirmação específica que ela esconde.

**Antes:**
> No fundo, o que realmente importa é a confiança do cliente, e a confiança depende de cumprir o prazo de 3 dias úteis.

**Depois:**
> A confiança do cliente depende de cumprir o prazo de 3 dias úteis.

### 8. Discutir com ninguém (`arguing-with-no-one`)

**Procure:** «não estou dizendo que», «não me entenda mal», «para ser justo,», «alguém poderia pensar que», «você pode achar que… mas», «seria tentador apenas».

**Problema:** O texto responde a uma objeção, ou recusa uma opção, que não aparece em lugar nenhum; costuma sobrar de um rascunho anterior. Tire a defesa; se ela guarda uma afirmação real, escreva a afirmação. Mantenha a objeção que o texto atribui a alguém ou responde por inteiro.

**Antes:**
> Não estou dizendo que o cupom seja ruim, e você poderia pensar que bastava baixar o preço. O frete subiu em março.

**Depois:**
> O frete subiu em março.

## Família 2, ritmo por regra

Formas e pontuação aplicadas em todo lugar, quer o sentido peça, quer não.

### 9. Trios forçados (`forced-triad`)

**Procure:** três itens paralelos para soar completo: «rápido, simples e seguro»; «inovação, inspiração e resultados»; três exemplos seguidos de uma lição.

**Problema:** As ideias chegam de três em três porque soa completo, não porque o sentido tenha três partes. Confira se cada item acrescenta uma ideia distinta. Se não, junte, desenvolva o mais forte ou varie a estrutura. Mantenha três itens quando são três de verdade.

**Antes:**
> A Acme Shop oferece rapidez, praticidade e segurança, com entrega em 3 dias úteis e o cupom BEMVINDO10.

**Depois:**
> A Acme Shop entrega em 3 dias úteis e aceita o cupom BEMVINDO10.

### 10. Frases que começam igual (`repeated-openings`)

**Procure:** várias frases seguidas com o mesmo sujeito: «O cupom… O cupom… O cupom…»; «Ele… Ele… Ele…».

**Problema:** A repetição soa como molde. Una as frases, mude o sujeito ou comece pela ação. Não proíba a palavra repetida: uma repetição de propósito, para ritmo, é voz do autor.

**Antes:**
> O cliente escolhe o produto. O cliente informa o CEP. O cliente aplica o cupom.

**Depois:**
> O cliente escolhe o produto, informa o CEP e aplica o cupom.

### 11. Travessão como conector universal (`dash-connector`)

**Procure:** travessão (—), meia-risca (–), hífen com espaços usado como travessão ( - ) e dois hifens ( -- ) no meio da frase.

**Problema:** O traço deixa o autor sem escolher como duas orações se relacionam, então ele aparece em toda parte. Muita gente usa travessão com critério; um só é sinal fraco. Um texto cheio deles não é. Troque por ponto, vírgula, dois-pontos ou parênteses, ou refaça a frase. Se o usuário deu uma amostra de escrita com travessão, siga a taxa da amostra. Deixe traços dentro de código, caminhos e links.

**Antes:**
> O frete — que subiu em março — agora é grátis acima de R$ 150, e o prazo — 3 dias úteis — não mudou.

**Depois:**
> O frete subiu em março. Agora é grátis acima de R$ 150, e o prazo continua em 3 dias úteis.

### 12. Ressalvas empilhadas (`stacked-hedges`)

**Procure:** «pode ser que talvez», «talvez possa», «poderia potencialmente», «parece que talvez», «em alguns casos pode ser que».

**Problema:** Duas ou três cautelas na mesma afirmação. Mantenha uma, onde a dúvida é real, sem aumentar a certeza do autor.

**Antes:**
> Talvez possa ajudar a reduzir, em alguns casos, o custo do frete.

**Depois:**
> Pode reduzir o custo do frete.

## Família 3, inflação

Fatos comuns vestidos de decisivos ou de apoiados por especialistas.

### 13. Verbos de palco (`inflated-verbs`)

**Procure:** «potencializar», «alavancar», «impulsionar», «agregar valor», «desvendar», «otimizar a experiência».

**Problema:** O verbo faz uma ação comum parecer estratégia e não diz o que muda. Use o verbo simples: aumentar, usar, melhorar, mostrar.

**Antes:**
> O novo cupom vai potencializar as vendas e alavancar o catálogo atual.

**Depois:**
> O novo cupom deve aumentar as vendas do catálogo atual.

### 14. Palavras infladas (`inflated-words`)

**Procure:** «jornada», «robusto», «fundamental», «crucial», «holístico», «disruptivo», «transformador», «inovador», «de ponta», «sinergia», «paradigma», «ecossistema», «de classe mundial».

**Problema:** A palavra não carrega fato que se possa conferir. Nomeie a propriedade concreta (quantos, quão rápido, para quem) ou tire a palavra. «Jornada do cliente» é termo de ofício em produto, e «robusto» pode ser exato em engenharia: tire só quando serve de enfeite.

**Antes:**
> Uma jornada de compra robusta, em 3 passos e sem login, com uma solução inovadora.

**Depois:**
> O checkout tem 3 passos e não pede login.

### 15. Cenário de abertura (`inflated-scene`)

**Procure:** «no cenário atual», «no mundo atual», «nos dias de hoje», «na era digital», «em um mundo cada vez mais conectado», «em constante evolução».

**Problema:** Uma abertura que serve para qualquer assunto, sem fato. Apague e comece pelo fato específico.

**Antes:**
> No cenário atual, em que tudo está em constante evolução, toda loja precisa de frete rápido. A Acme Shop entrega em 3 dias úteis.

**Depois:**
> A Acme Shop entrega em 3 dias úteis.

### 16. Importância afirmada, não mostrada (`inflated-significance`)

**Procure:** «desempenha um papel fundamental», «tem um papel crucial», «é um testemunho de», «marca um momento decisivo», «deixa uma marca indelével».

**Problema:** Declara que algo importa em vez de dizer o que faz e para quem. Diga o efeito.

**Antes:**
> O frete grátis acima de R$ 150 desempenha um papel fundamental na conversão e é um testemunho da força da marca.

**Depois:**
> O frete grátis acima de R$ 150 ajuda a converter.

«Testemunho da força da marca» não diz nada que se confira e sai; a afirmação sobre conversão fica.

### 17. Autoridade emprestada (`borrowed-authority`)

**Procure:** «estudos mostram», «pesquisas apontam», «especialistas afirmam», «segundo analistas», «relatórios do setor indicam».

**Problema:** Uma autoridade sem nome, data nem link. Mantenha só se a fonte já está no texto. Se não está, sinalize a lacuna no relatório; nunca invente fonte, número ou estudo para preencher.

**Antes:**
> Estudos mostram que o frete grátis converte mais, e especialistas concordam.

**Depois:**
> O frete grátis converte mais. [Fonte não informada no texto: pedir ao autor ou cortar a afirmação.]

O marcador entre colchetes vai para o relatório ao autor, não para o texto final publicável.

### 18. Verbo comprido onde cabe «é» ou «tem» (`avoiding-is-has`)

**Procure:** «se configura como», «se constitui em», «se posiciona como», «se destaca como», «serve como», «atua como um».

**Problema:** O verbo longo evita o verbo simples e soa mais importante sem dizer mais. Volte para «é», «tem», «fica».

**Antes:**
> O módulo de frete se configura como o núcleo do checkout e serve como ponto de partida do prazo.

**Depois:**
> O módulo de frete é o núcleo do checkout e é o ponto de partida do prazo.

## Família 4, formatação por regra

### 19. Negrito como rótulo (`bold-labels`)

**Procure:** cada item de lista abrindo com um rótulo em negrito: «- **Objetivo:** …», «1. **Prazo** …». Um sinal fraco isolado; forte quando todo item faz isso.

**Problema:** O negrito vira decoração e o leitor deixa de saber o que de fato importa. Use itens simples; destaque só o que o leitor procura ao varrer o texto.

**Antes:**
> - **Prazo:** 3 dias úteis
> - **Frete:** grátis acima de R$ 150
> - **Cupom:** BEMVINDO10, 10% na primeira compra

**Depois:**
> O prazo é de 3 dias úteis. O frete é grátis acima de R$ 150. O cupom BEMVINDO10 dá 10% na primeira compra.

Uma tabela de referência com rótulos é legítima; o sinal é a lista de prosa travestida de ficha.

### 20. Emoji como marcador (`emoji-markers`)

**Procure:** emoji abrindo título ou item: «## 🚀 Novidades», «- ✅ Frete grátis».

**Problema:** O emoji não diz nada que o texto não diga. Tire, a não ser que carregue um estado de que o leitor precisa (um checklist de status).

**Antes:**
> ## 🚀 Novidades
> - ✅ Frete grátis acima de R$ 150
> - ✅ Prazo de 3 dias úteis

**Depois:**
> ## O que mudou
> - Frete grátis acima de R$ 150
> - Prazo de 3 dias úteis

### 21. Títulos de prateleira (`decorative-headings`)

**Procure:** «Introdução», «Conclusão», «Considerações finais», «Resumo executivo», «Visão geral», «Principais pontos», «Pontos-chave» em um texto curto.

**Problema:** O título nomeia um lugar no texto, não o conteúdo. Dê à seção o nome do que ela diz, ou tire o título. Em documento longo, «Visão geral» pode ser convenção do gênero; avalie pelo uso.

**Antes:**
> ## Conclusão
> O frete é grátis acima de R$ 150.

**Depois:**
> ## Frete grátis acima de R$ 150

## Família 5, sobras do chat e do rascunho

Frases que nunca foram escritas para o leitor.

### 22. Abertura de resposta de chat (`chatbot-opener`)

**Procure:** «Claro!», «Com certeza!», «Certamente!», «Ótima pergunta!», «Você tem toda a razão», «Entendido!» como primeira linha.

**Problema:** É embalagem de resposta de chat. Apague a linha.

**Antes:**
> Claro! Ótima pergunta! O prazo de entrega da Acme Shop é de 3 dias úteis.

**Depois:**
> O prazo de entrega da Acme Shop é de 3 dias úteis.

### 23. Oferta ou despedida de chat (`chatbot-closer`)

**Procure:** «Espero ter ajudado!», «Fico à disposição», «Posso ajudar com mais alguma coisa?», «Quer que eu…?», «Gostaria que eu…?», «Qualquer dúvida, é só avisar».

**Problema:** Oferece o que ninguém pediu. Apague. Mantenha o próximo passo real, se houver. Uma despedida de carta ou comentário é anterior aos chatbots e não é este padrão.

**Antes:**
> O prazo é de 3 dias úteis. Espero ter ajudado! Quer que eu detalhe o frete também?

**Depois:**
> O prazo é de 3 dias úteis.

### 24. O modelo fala de si (`chatbot-self-reference`)

**Procure:** «como modelo de linguagem», «como uma IA», «até a minha última atualização», «não tenho acesso a informações em tempo real», «com base nas informações disponíveis».

**Problema:** Mistura a voz do assistente com a do texto. Apague. Se um fato é desconhecido, diga qual e quem pode informá-lo; não preencha.

**Antes:**
> Até a minha última atualização, o frete era de R$ 12, mas como modelo de linguagem não tenho acesso ao seu catálogo.

**Depois:**
> O frete era de R$ 12 na última informação disponível; confirme o valor atual no catálogo.

### 25. Frase que apresenta o texto (`chatbot-handoff`)

**Procure:** «Aqui está o texto reescrito:», «Segue abaixo a versão final:», «Aqui vai o resumo:» seguidos do conteúdo.

**Problema:** A frase apresenta o texto em vez de estar nele. No modo embutido (descrição de PR, mensagem), devolva só o texto.

**Antes:**
> Aqui está a descrição do pull request:
>
> Reduz o prazo de entrega de 5 para 3 dias úteis.

**Depois:**
> Reduz o prazo de entrega de 5 para 3 dias úteis.

### 26. O texto descreve a si mesmo (`document-announces-itself`)

**Procure:** «Neste artigo, vamos explorar…», «Este documento tem como objetivo apresentar…», «Neste guia você vai aprender…»; um índice ou legenda do que o leitor já vê.

**Problema:** Gasta a primeira linha com o que o leitor está prestes a ler. Comece pelo primeiro fato.

**Antes:**
> Este documento tem como objetivo apresentar as regras de frete e de cupom da Acme Shop. O frete é grátis acima de R$ 150 e o cupom BEMVINDO10 dá 10% na primeira compra.

**Depois:**
> O frete da Acme Shop é grátis acima de R$ 150. O cupom BEMVINDO10 dá 10% na primeira compra.

### 27. Título repetido na primeira frase (`heading-repeated`)

**Procure:** o título «Prazo de entrega» seguido de «O prazo de entrega é…».

**Problema:** A primeira frase repete o título e o leitor não ganha nada. Comece pelo conteúdo.

**Antes:**
> ## Prazo de entrega
> O prazo de entrega da Acme Shop é de 3 dias úteis, contados a partir da confirmação do pagamento.

**Depois:**
> ## Prazo de entrega
> São 3 dias úteis, contados a partir da confirmação do pagamento.

## Família 6, leitor errado

### 28. Explicar o que o leitor já sabe (`re-explaining`)

**Procure:** uma resposta curta que repete o problema, refaz o diagnóstico e lista as provas antes de chegar à decisão; contexto que a outra pessoa escreveu ou já tem; uma consulta ou um comando incluídos só para provar que o plano funciona.

**Problema:** A decisão chega por último. Abra com a resposta e deixe o diagnóstico para quem pedir.

**Antes:**
> Você perguntou se dá para reduzir o prazo. O prazo atual é de 5 dias úteis e a meta é de 3. O atraso vem da separação, que hoje é manual e ocupa 2 dias. Portanto, sim, é possível.

**Depois:**
> Dá para chegar a 3 dias úteis, hoje 5: o atraso está na separação, que é manual e ocupa 2 dias.

## Família 7, vícios do português

Sinais próprios do português, não uma tradução da lista em inglês.

### 29. Gerundismo: «estaremos enviando» (`gerundismo`)

**Procure:** «vou estar enviando», «vamos estar analisando», «estaremos enviando», «estarei verificando», «estaria fazendo».

**Problema:** O futuro de estar mais gerúndio alonga o verbo e esconde o compromisso. Use o futuro simples ou o presente: «envio», «enviaremos», «analisamos». Quando a ação é de fato contínua num momento marcado («às 15h estarei dirigindo»), o gerúndio é correto.

**Antes:**
> Estaremos enviando o relatório amanhã e vamos estar analisando o prazo com a logística.

**Depois:**
> Enviaremos o relatório amanhã e analisaremos o prazo com a logística.

### 30. Oficialês (`officialese`)

**Procure:** «cumpre salientar», «no âmbito de», «no que tange a», «no que diz respeito a», «diante do exposto», «haja vista», «a nível de».

**Problema:** Linguagem de ofício para uma afirmação comum. Use a construção direta: «em», «sobre», «por causa de». Em texto jurídico ou oficial por gênero, avalie a repetição mecânica, não a mera presença.

**Antes:**
> No que diz respeito ao frete, cumpre salientar que, no âmbito do checkout, o prazo foi alterado para 3 dias úteis.

**Depois:**
> O prazo do checkout mudou para 3 dias úteis.

### 31. Frase de efeito de redação (`enem-ism`)

**Procure:** um parágrafo final que ergue o assunto a «uma sociedade melhor», «um futuro mais justo», «o desafio que nos cabe enfrentar»; «Dessa forma, constrói-se…».

**Problema:** Uma moral genérica colada no fim, no estilo de redação escolar. Troque por uma reflexão específica do próprio texto ou corte.

**Antes:**
> O frete grátis acima de R$ 150 passou a valer em março. Dessa forma, constrói-se um comércio mais justo e um futuro melhor para todos.

**Depois:**
> O frete grátis acima de R$ 150 passou a valer em março.

## Quando não agir

Cada padrão é uma escolha comum que uma pessoa também faz de propósito. Deixe como está dentro de uma citação, de um título, de um nome próprio, de um trecho que fala da expressão em vez de usá-la, e de um gênero em que a expressão é convenção (carta, ofício, contrato, bula). Não reescreva texto normativo nem de segurança crítica.

Mantenha o que carrega a voz de quem escreveu, a não ser que atrapalhe o sentido: um detalhe específico e incomum, uma dúvida não resolvida, uma referência datada, uma escolha de primeira pessoa que o autor sabe explicar, um aparte ou uma autocorreção genuínos.
