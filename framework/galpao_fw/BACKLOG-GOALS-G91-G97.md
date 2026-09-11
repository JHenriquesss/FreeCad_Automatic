# Backlog de goals executáveis — pós-G90 (2026-09-10)

> ## FILA CONSUMIDA - os 7 goals (G91-G97) estao FECHADOS
>
> Executados e auditados em 2026-09-10 (G98). Cada um tem verbete em
> `wiki/04-decisions.md` (**D118-D124**) e a fase em `wiki/03-phases.md`.
> **Este arquivo fica como registro do que foi medido e pedido - nao e mais fila.**
>
> | Goal | Verbete | Goal | Verbete |
> |---|---|---|---|
> | G91 lente indice<->disco | D119 | G95 terraplenagem numa rodada | D123 |
> | G92 a casa fecha 17 codigos | D120 | G96 triagem do FreeCAD no aco | D118 |
> | G93 o galpao nomeia o codigo | D121 | G97 portao que esconde portao | D124 |
> | G94 caderno de casa e predio | D122 | *(auditoria do lote)* | **G98** |
>
> **Aberto e medido, para o proximo arco** (nao estava nesta fila): PE-EL-01/02/04 da casa
> saem declaradas "sem emissor ligado" e os emissores existem e estao provados; `mezanino`
> e executado pelo turnkey e nao existe no indice; o portao das tres tipologias do G91 mede
> indice x mapa, nao indice x disco.

Cada goal abaixo é **autocontido**: um agente que abra este arquivo sem ter visto a
conversa consegue executá-lo. Traz o que foi **medido** (com endereço no código), o que
entregar, o critério de aceite e as armadilhas conhecidas deste projeto que se aplicam.

**Regra de leitura:** o que está aqui foi medido em 2026-09-10 na branch
`feat/tipologias-e-verticais-de-projeto`, no commit `72a210e` (suíte non-build:
3686 passed / 0 failed). O que **não** foi medido está dito como não medido. Nenhum item é
palpite sobre o que "provavelmente" falta — se um goal depender de dado que o usuário
precisa declarar, isso está escrito nele.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**
(`not_available` com artigo, ou `... nao declarado`), nunca se preenche.

**O norte:** o framework existe para gerar **construções inteiras confiáveis**. Cálculo
correto que não vira folha entregue não é obra; e folha que some em silêncio é pior que
folha ausente declarada, porque o pacote parece completo.

---

## Convenções que todo goal deste repo segue

Estas cinco regras são caras — cada uma custou um bug. Um agente que as ignore vai
reintroduzir um defeito conhecido.

1. **Baseline nos dois sentidos.** Varredura/guarda sem baseline congelado nos dois
   sentidos é relatório, não portão. Toda lente nova precisa de um teste que fique
   **vermelho quando o defeito é injetado** e verde no caso bom. Sem isso a suíte fica
   verde com o gap novo dentro dela.
2. **Vermelho por injeção, nunca mutando o repo.** Injete o defeito em diretório
   temporário (`tmp_path`). Teste que muta a árvore viva já derrubou a suíte inteira.
3. **A escada: substring → parse → renderizar.** Asserção por substring não vê geometria.
   Parseie o XML (`ET.fromstring`); para folha, use `desenho_svg_base.confere_folha_svg`;
   e quando o alvo for legibilidade, **renderize e olhe** (Edge headless
   `--headless=new --screenshot --window-size`, sem cairosvg/svglib).
4. **Saturação silenciosa.** Tabela que satura no maior valor + gate que não reprova +
   `OK=True` é a classe de bug recorrente deste repo. Ao passar de *verificar* para
   *dimensionar*, o portão é o **detalhamento entregue** (adotado × necessário).
5. **Asserção tautológica.** Se o valor de comparação deriva do resultado, a asserção não
   mede nada. Compare com fonte independente (norma, exemplo resolvido, simetria).

**Sexta regra, nova (custou o G89):** *"a folha está certa"* e *"a folha sai"* são **dois
aceites**. Todo goal que produz folha tem de provar o segundo — o emissor ligado a um
adaptador, o arquivo no manifesto da rodada. `desenho_terraplenagem` cumpriu o critério do
G79 ao pé da letra e era ilha, com zero folhas no disco.

**Ferramentas prontas que devem ser reusadas, não reescritas:**
`desenho_svg_base.confere_folha_svg` (guarda de folha), `desenho_svg_base.censo_de_folhas`
(censo por AST), `varredura_defaults_veredito.py` (defaults que decidem veredito),
`varredura_faixa_validade.py` (faixa de validade declarada), `tests/test_alcancabilidade.py`
(ilhas), `caderno_turnkey.montar_caderno_de_pdfs` (consolidação de PDF, agnóstica de
tipologia), `colisoes_de_rotulo_svg` (**estimador, não guarda** — conservador por
construção, acusa pares legíveis).

---

## Ordem e dependência

- **Bloco 1 (G91 → G92 → G93):** nesta ordem. O G91 entra **vermelho de propósito** na
  árvore viva (casa e galpão o reprovam no minuto em que ele existir); G92 e G93 o fecham.
- **Bloco 2 (G94, G95, G96):** o G94 depende do Bloco 1 (sem o laço, o caderno herda o
  buraco). G95 e G96 são independentes e podem ser feitos a qualquer momento.
- **Bloco 3 (G97):** independente. É barato e protege todos os censos que já existem.

---

# GOALS

## G91 · Uma lente de índice↔disco para as três tipologias, em vez de três implementações

**Prioridade: alta.** É o portão que faltou ao arco inteiro do G78–G88 e teria pego
sozinho o buraco da casa.

**Medido:**
- O índice de pranchas é `pacote_legal._PRANCHAS` (linha 24): prefixo + títulos por
  disciplina. `pacote_legal.indice_de_pranchas(disciplinas)` devolve os códigos
  (`PE-AR-01`, `PE-CO-04`, …). Quem promete a disciplina é `gestao_casa.disciplinas_pacote`
  (`gestao_casa.py:824`) e `gestao_edificio.disciplinas_pacote` (`gestao_edificio.py:758`).
- **Prédio:** `edificio_adapter.py:1028` tem `_PRANCHA_ARQUIVO` com **15 entradas**, e o
  laço em `edificio_adapter.py:995-1017` confronta o índice de **todas** as disciplinas do
  pacote + coordenação. Fecha 15/15; o que não sai vira `skipped` **nomeado**.
- **Casa:** `casa_residencial.py:786` tem `_PRANCHA_ARQUIVO_CASA` com **3 entradas**
  (PE-AR-01/02/03) e o laço em `casa_residencial.py:759-772` lê
  `indice_de_pranchas(["arquitetura"])` — um recorte do próprio escopo (ver G92).
- **Galpão:** **não tem mapa nenhum**. `galpao_adapter._emit_drawings`
  (`galpao_adapter.py:242`) registra a árvore inteira por `_register_tree`, sem código de
  prancha (ver G93).
- Três implementações do mesmo contrato: nenhuma delas **é** o contrato.

**Entregar:**
- `varredura_indice_disco.py`, no padrão das outras lentes do repo. Função pura:
  recebe `(codigos_prometidos, mapa_codigo_arquivo, nomes_no_disco, motivos_escritos)` e
  devolve, no mínimo:
  - `faltando` — código prometido sem arquivo e **sem motivo escrito**;
  - `sobrando` — entrada no mapa que o índice não promete (o nome morto, irmão do que
    derrubou o portão do G77);
  - `sem_mapa` — código prometido que nem entrada no mapa tem;
  - `OK`.
- Um teste-portão que aplique a lente às **três** tipologias a partir dos mapas reais.
- `BASELINE_G91` congelando o estado conhecido, nos dois sentidos.

**Aceite:**
- O portão fica vermelho **na árvore viva** ao entrar, com casa e galpão nomeados. Isso é
  o resultado esperado, não um erro: registre no verbete e feche com G92/G93.
- Injetar o defeito (apagar uma entrada de `_PRANCHA_ARQUIVO` numa cópia em `tmp_path`)
  deixa a suíte vermelha; o caso bom fica verde.
- A mensagem de falha nomeia **todos os lados numa rodada só** (ver G97) — não um assert
  por vez.

**Armadilhas:**
- Não reescrever `confere_folha_svg` nem o censo do G77: são outra coisa (conteúdo da
  folha, não existência dela).
- O laço do prédio tem um `except` que registra `"(indice)"` com o erro nomeado quando a
  própria conferência falha. Preserve esse comportamento na lente: garantia que cai em
  silêncio é saturação silenciosa vestida de rede de segurança.

---

## G92 · A casa confronta o índice que ela promete, não só o PE-AR

**Prioridade: alta.** Correção pequena, buraco grande.

**Medido:**
- `casa_residencial.py:760` chama `pl.indice_de_pranchas(["arquitetura"])` — 3 códigos, 3
  mapeados, verde.
- Mas `gestao_casa.disciplinas_pacote` (`gestao_casa.py:824`) promete, no pacote que vai ao
  cliente: `arquitetura`, as disciplinas calculadas (concreto, hidráulica, elétrico — a
  fundação é coberta por `FUNDACAO_COBERTA_POR`) e `madeira` quando há telhado calculado.
  O pacote sai por `gestao_casa.py:974` → `ep.pacote_no_manifesto`.
- Resultado medido na última rodada completa: **16 códigos prometidos, 3 mapeados**. Os 13
  restantes evaporam no `continue` do índice — o mesmo D89 que já custou duas vezes.
- O laço confere um **recorte do próprio escopo**: é saturação silenciosa (regra 4) na
  forma de portão.

**Entregar:**
- O laço da casa passa a ler **a mesma fonte** que o pacote: `disciplinas_pacote(result)`.
  Uma fonte só de disciplinas, não duas.
- Para cada um dos 13 códigos: **emitir a folha** ou **nomear o motivo**, um por um, na
  triagem escrita. Códigos cuja folha já existe noutro emissor só precisam da entrada no
  mapa; os demais entram como pulados com o motivo — e o motivo diz **qual dado falta**,
  com nome (como o G78 fez com lote e níveis), nunca "não disponível".

**Aceite:**
- G91 verde para a casa.
- Nenhum código sai com motivo genérico. Motivo sem o dado nomeado é silêncio, não triagem.
- Vermelho por injeção: estreitar a lista de volta para `["arquitetura"]` numa cópia em
  `tmp_path` → G91 acusa os 13.

**Não fazer:** inventar recuo, soleira, cota de nível, vão de janela ou qualquer geometria
para "fazer a folha sair". Ausência se declara.

---

## G93 · O galpão deixa de contar folhas e passa a nomear códigos

**Prioridade: alta.** A tipologia carro-chefe é a única sem mapa.

**Medido:**
- `entregaveis_projeto.pacote_no_manifesto` (`entregaveis_projeto.py:329`) monta o pacote e,
  em `entregaveis_projeto.py:343`, calcula
  `emitidas = sum(1 for item in manifest["artifacts"] if item["kind"] == "drawing")`.
- Em `entregaveis_projeto.py:359`, se `emitidas < len(pacote["indice_pranchas"])`, escreve
  uma linha em `a_confirmar` com **os dois números**.
- Isto é **número contra número**: um desenho a mais, de qualquer nome, fecha a conta sem
  que um único código do índice tenha sido conferido. É parente da asserção tautológica do
  D86 — a comparação não mede o *qual*.
- `emitir_pacote_legal` (`entregaveis_projeto.py:375`) passa
  `turnkey_result["executadas"]` como disciplinas; o registro do entregável está em
  `galpao_adapter.py:409`.

**Entregar:**
- `_PRANCHA_ARQUIVO_GALPAO`: código do índice → arquivo em `drawings/`, medido contra o que
  o galpão realmente emite hoje (não contra o que se supõe que ele emita).
- O laço da lente do G91 em `galpao_adapter._emit_drawings`, com os pulados nomeados.
- A contagem de `pacote_no_manifesto` **continua** no `.md` (é informação útil ao leitor),
  mas deixa de ser o portão.

**Aceite:**
- G91 verde para o galpão.
- Aceite duplo (regra 6): (1) o código tem arquivo mapeado; (2) o arquivo **sai na rodada** e
  aparece no manifesto.
- Vermelho por injeção em `tmp_path`.

**Armadilha medida:** as folhas de hidráulica do galpão são **1 arquivo cobrindo 3 códigos**
(PE-HI-01/02/03) — o contrato foi escrito no G82 e está em `desenho_hidraulica.py:136` e em
`desenho_hidraulica.confere_cobertura_galpao`. O mapa tem de aceitar N:1 sem que isso vire
"faltando"; reuse a função que já existe em vez de reimplementar a regra.

---

## G94 · Caderno executivo em PDF para a casa e para o prédio

**Prioridade: média.** Depende do Bloco 1.

**Medido:**
- O galpão entrega um caderno consolidado (capa + índice + pranchas A1 de todas as
  disciplinas): `caderno_turnkey.montar_caderno` (`caderno_turnkey.py:333`), acionado em
  `galpao_adapter.py:252`. Última medição conhecida: **36 páginas**.
- A consolidação em si é **agnóstica de tipologia**:
  `caderno_turnkey.montar_caderno_de_pdfs` (`caderno_turnkey.py:230`) e
  `_add_pagina_imagem` (`caderno_turnkey.py:203`), que recebe **PNG**.
  Quem depende de FreeCAD é `_dispatch_pranchas` (`caderno_turnkey.py:285`), não o
  consolidador.
- Casa e prédio **não** têm caderno de pranchas. O prédio tem `caderno_encargos`
  (`edificio_adapter.py:1584`) — é o caderno de **especificações**, outra coisa. Ambos
  entregam `.md` e `.json`.
- Como as folhas de casa e prédio são SVG puro, a rota é **SVG → PNG → página**. O
  renderizador do repo é o Edge headless (regra 3), já usado nas guardas de legibilidade;
  não introduzir cairosvg/svglib.

**Entregar:**
- Caderno consolidado para casa e prédio, reusando `montar_caderno_de_pdfs`.
- Cada página com carimbo: código da prancha, título, disciplina, projeto.
- As folhas **declaradas ausentes** entram no caderno como página de declaração, com o dado
  que falta nomeado — não somem.

**Aceite:**
- `páginas do PDF == folhas emitidas + folhas declaradas ausentes`. Caderno com menos
  páginas que o índice é o orçamento parcial em forma de prancha (a classe do G87).
- O PDF abre e as páginas têm conteúdo (não basta o arquivo existir — regra 3: parse, e
  abrir para olhar pelo menos uma).

---

## G95 · Terraplenagem exercitada por um projeto real, não só pelo teste

**Prioridade: média.** Fecha a metade que faltou do que o G89 começou.

**Medido:**
- O G89 tirou `desenho_terraplenagem` da ilha: `entregaveis_projeto._folhas_terraplenagem`
  liga PE-TP-01/02 dentro de `emitir_obras_sitio`, a partir do resultado **já calculado**.
  As guardas estão em `tests/test_terraplenagem_pranchas_g79.py` (três testes G89).
- **Nenhum spec persistido em `projects/` declara `site.terraplenagem`.** O caminho está
  ligado e nunca roda numa rodada de verdade — só nos testes, com dado de fixture.

**Entregar:**
- Um projeto em `projects/` (ou uma seção num projeto existente) que declare, **pelo
  projetista**: grid do terreno, cota de plataforma, área de célula, empolamento e o caso de
  drenagem.
- Se algum desses dados não puder ser declarado sem ser inventado, o goal entrega o spec com
  o campo **ausente e nomeado** e a rodada mostrando a frente como não calculada — isso é
  entrega válida, e é o comportamento correto.

**Aceite:**
- As duas folhas no manifesto da rodada, com `confere_folha_svg` passando nas duas.
- O `project-run.json` mostra `obras_sitio` com `status: generated` e os dois artefatos.

**Não fazer:** arbitrar empolamento, intensidade de chuva ou cota de plataforma para o spec
"rodar bonito". Um número inventado num spec persistido é pior que um campo vazio: ele
sobrevive ao goal.

---

## G96 · Triar se o aço executivo do galpão precisa mesmo do FreeCAD

**Prioridade: média. Este goal termina em decisão escrita, não em código.**

**Medido:**
- O executivo em aço depende do TechDraw via FreeCAD e **dá timeout** na geração
  (`caderno_turnkey._dispatch_pranchas`, `caderno_turnkey.py:285`, com orçamento de tempo
  por estágio em `_stage_timeout`). Não foi medido **quanto** cada prancha custa
  individualmente — medir isso é parte do goal.

**Entregar:**
- Medição, prancha a prancha: quais exigem geometria 3D real (corte de peça, vista
  projetada de conjunto) e quais são desenho 2D que os emissores SVG puros do repo já sabem
  fazer.
- Verbete em `wiki/04-decisions.md` com a lista e o custo medido de cada via.
- Se a resposta for "precisa do FreeCAD", o goal **seguinte** é o *harness* de medição, não
  a iteração manual (a lição de `ferramenta-antes-de-iterar`).

**Armadilhas medidas:**
- O `freecad.exe` **persiste e roda a versão antiga do módulo irmão** — toda medição roda com
  o processo reiniciado, ou o número é de outro código.
- FreeCAD travado não morre com `taskkill`/`Stop-Process`; o caminho é WMI `Terminate`.

---

## G97 · Portão que esconde portão: asserts em sequência mascaram os seguintes

**Prioridade: média. Barato, e protege todos os censos que já existem.**

**Medido:**
- `tests/test_varredura_faixa_validade_g51.py:376` — `test_09_cobertura_todo_py_varrido_ou_isento`
  tem **quatro** asserts independentes em sequência: `faltando`, `sobrando`, `sem_motivo`,
  `ausentes`. O primeiro que estoura impede a avaliação dos outros três.
- Consequência real: o portão do G77 ficou **vermelho desde o próprio commit `fb53107`** e
  ninguém viu. O `sobrando` (a isenção de `desenho_svg_base.py` que virou nome morto, porque
  a prosa da linha 229 passou a casar com a `VALIDADE_RE`) estava escondido atrás do
  `faltando`. Cada conserto revelava um achado que já estava lá havia commits.
- O padrão se repete: `tests/test_guardas_d86_g69.py`, `tests/test_folhas_g77.py`,
  `tests/test_defaults_veredito_g75.py` e o G91 acima têm a mesma forma.

**Entregar:**
- Lente AST sobre os testes-portão: acusar dois ou mais asserts independentes em sequência
  num mesmo portão de censo/cobertura.
- A receita substituta: **coletar todos os lados**, montar uma mensagem única e falhar uma
  vez só, com o relatório completo.
- Aplicar aos portões existentes: G51, G69, G75, G77, G83 — e ao G91.

**Aceite:**
- Vermelho por injeção: devolver a isenção morta do G77 numa cópia em `tmp_path` e verificar
  que a mensagem de falha nomeia **os dois** lados numa rodada só.
- Baseline nos dois sentidos: um portão novo com asserts em sequência é acusado; os já
  corrigidos ficam verdes.

**Armadilha:** nem todo assert em sequência é o defeito. Assert que **depende** do anterior
(guard clause: `assert r is not None` antes de `assert r["x"] == 3`) é correto e tem de ser
isento com motivo escrito — isenção sem motivo é silêncio, não triagem.
