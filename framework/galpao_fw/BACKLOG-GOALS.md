# Backlog de goals executáveis — pós-G77 (2026-09-09)

> ## ⚠ FILA CONSUMIDA — os 11 goals (G78–G88) estão FECHADOS
>
> Executados e auditados em 2026-09-09 (G89/G90). Cada um tem verbete em
> `wiki/04-decisions.md` (**D106–D117**) e a fase em `wiki/03-phases.md`.
> **Este arquivo fica como registro do que foi medido e pedido — não é mais fila.**
> Não reexecute nenhum goal daqui: o que sobrou aberto está nomeado no fim deste
> bloco e no `BACKLOG.md`.
>
> | Goal | Verbete | Goal | Verbete |
> |---|---|---|---|
> | G78 planta baixa da casa | D106 | G84 declara-ou-recusa | D114 |
> | G79 terraplenagem desenha | D109 | G85 módulos sem teste | D115 |
> | G80 fundação do prédio | D110 | G86 telhado no federado | D107 |
> | G81 folha da escada | D111 | G87 orçamento 3 estados | D116 |
> | G82 hidráulica 3×1 | D112 | G88 documentação | D117 |
> | G83 guardas de um eixo | D113 | *(auditoria do lote)* | **D108/G89** |
>
> **Aberto e medido, para o próximo arco** (não estava nesta fila): a casa promete
> 16 pranchas no índice e mapeia 3 (só PE-AR); o galpão não tem laço índice↔disco;
> o caderno executivo em PDF só existe no galpão.
>
> **A fila aberta agora e' `BACKLOG-GOALS-G91-G97.md`** (G91-G97, medidos em
> `72a210e`). Este arquivo nao e' fila.

Cada goal abaixo é **autocontido**: um agente que abra este arquivo sem ter visto a
conversa consegue executá-lo. Traz o que foi **medido** (com endereço no código), o que
entregar, o critério de aceite e as armadilhas conhecidas deste projeto que se aplicam.

**Regra de leitura:** o que está aqui foi medido em 2026-09-09 na branch
`feat/tipologias-e-verticais-de-projeto` (HEAD `fb53107`). O que **não** foi medido está
dito como não medido. Nenhum item é palpite sobre o que "provavelmente" falta — se um
goal depender de dado que o usuário precisa declarar, isso está escrito nele.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara** (`not_available`
com artigo, ou `... nao declarado`), nunca se preenche.

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

**Ferramentas prontas que devem ser reusadas, não reescritas:**
`desenho_svg_base.confere_folha_svg` (guarda de folha), `desenho_svg_base.censo_de_folhas`
(censo por AST), `varredura_defaults_veredito.py` (defaults que decidem veredito),
`varredura_faixa_validade.py` (faixa de validade declarada), `colisoes_de_rotulo_svg`
(**estimador, não guarda** — conservador por construção, acusa pares legíveis).

---

# GOALS

## G78 · A casa promete 3 folhas de arquitetura e não emite nenhuma — e as posições já estão declaradas

**Prioridade: alta.** É o maior buraco medido, e o dado está a uma chave de distância.

**Medido:**
- `pacote_legal._PRANCHAS["arquitetura"]` (linha 25) promete **PE-AR-01 Planta de
  implantação, PE-AR-02 Planta baixa, PE-AR-03 Cortes e fachadas**.
- O censo de emissores (`desenho_svg_base.censo_de_folhas`) acha **32 folhas** e
  **nenhuma** delas é de arquitetura.
- `desenho_casa_residencial.py:472-473` pula a planta baixa com o motivo
  `"posicoes_dos_ambientes_nao_declaradas"`.
- **Esse motivo é falso para o spec persistido.** `projects/casa-residencial/project-spec.json`
  declara 7 cômodos com `x_m`, `y_m`, `width_m`, `depth_m` em
  `turnkey.eletrico.circuits.layout.rooms` — os mesmos 7 nomes do programa de arquitetura
  (`turnkey.arquitetura.ambientes`). A planta **elétrica** residencial já desenha esses
  retângulos (verificado em PNG no G77).
- Existe primitiva compartilhada pronta: `layout_ambientes.py` (retângulo finito, id
  único, nenhum par sobreposto), já usada por `bim_casa_residencial` e
  `layout_eletrico_residencial`.
- **Cross-check inédito:** área do programa (`largura_m × comprimento_m`) × área do layout
  (`width_m × depth_m`) batem nos 7 cômodos hoje — **e nada confere isso**. São duas
  declarações do mesmo fato sem cruzamento: o anti-padrão que este repo persegue por nome
  ("duas descrições que envelhecem e passam a discordar em silêncio").

**Entregar:**
1. Decidir e escrever **onde o layout mora canonicamente**. Hoje ele está sob a disciplina
   elétrica, que é a consumidora, não a dona. O natural é a arquitetura declarar e a
   elétrica ler — mas isso muda o contrato do spec, então a decisão vai no verbete, com
   migração e chave antiga recusando com endereço (molde do G74:
   `contraventamento_banzo_inf` → `..._m`).
2. `planta_baixa_svg` de verdade: cômodos posicionados, nomes, áreas, cotas gerais.
   **Sem inventar** parede, porta ou janela que não esteja declarada — o que não houver
   fica de fora e o escopo diz por quê.
3. PE-AR-01 e PE-AR-03 (implantação e cortes/fachadas): **triar antes de implementar.**
   Implantação precisa de recuos/orientação do lote; cortes precisam de pé-direito e
   níveis. Se o spec não declara, **não implemente** — deixe `not_available` com o dado
   que falta nomeado, e diga isso no goal fechado. Não arbitre recuo nem cota de soleira.
4. **Guarda de cross-check:** área do programa × área do layout, com tolerância declarada;
   vermelho por injeção (mude uma dimensão do layout e a suíte tem de acusar).
5. Registrar a(s) folha(s) nova(s) em `FOLHAS` de `tests/test_folhas_g77.py` — o portão do
   censo vai ficar **vermelho** até isso ser feito. É de propósito.

**Aceite:** o laço índice↔disco da casa fecha (nenhuma PE-AR prometida sem arquivo **ou**
sem motivo escrito); a folha passa em `confere_folha_svg`; renderizada e olhada; o
cross-check de área fica vermelho por injeção.

**Armadilha:** a tentação de gerar planta baixa "aproximada" a partir de área e perímetro.
O módulo já recusa isso na sua própria abertura (`desenho_casa_residencial.py:11`), e a
recusa está certa — geometria inventada é pior que folha ausente.

---

## G79 · Terraplenagem calcula e não desenha: PE-TP-01 e PE-TP-02 prometidas, zero emissor

**Medido:**
- `terraplenagem.py` calcula: `volumes_corte_aterro` (l.27), `greide_equilibrio` (l.46),
  `movimento_terra` (l.74), `vazao_racional` (l.87), `canaleta_manning` (l.95),
  `dimensiona_drenagem` (l.125).
- `pacote_legal._PRANCHAS["terraplenagem"]` (l.26) promete **PE-TP-01 Terraplenagem
  (corte/aterro)** e **PE-TP-02 Drenagem do lote**.
- O arquivo **não tem uma única função `*_svg`** (conferido no censo: 32 folhas, nenhuma
  de terraplenagem). O índice promete 2 folhas e o disco recebe 0.

**Entregar:** dois emissores SVG lendo o que já é calculado — mapa de corte/aterro por
célula da malha (com o greide de equilíbrio cotado) e planta de drenagem (canaletas com
Q, largura, declividade, n de Manning). Quadro-resumo com os volumes e o empolamento
**declarado**, não assumido.

**Aceite:** as duas folhas passam em `confere_folha_svg`, entram em `FOLHAS` do
`test_folhas_g77`, e a contagem desenhada bate com o dado (*drawing-vs-data*: número de
células desenhadas == número de células da malha; canaletas desenhadas == dimensionadas).
Renderizar e olhar.

**Armadilha medida neste repo:** a planta de incêndio já desenhou `cols*rows ≠ N` uma vez
(grade que não batia com a contagem do resumo). Faça a folha **count-driven**.

---

## G80 · O prédio dimensiona fundação por pilar e não entrega folha de fundação

**Medido:**
- `edificio_adapter.py:1002-1014` mapeia **13 códigos** para arquivo; os de concreto são
  `PE-CO-01` planta de formas, `PE-CO-02` armação de vigas, `PE-CO-03` planta de laje.
  **Não há folha de fundação.**
- `fundacao_edificio.py:509` — *"Dimensiona a fundacao de TODOS os pilares do edificio"*.
  O dado existe: geometria por pilar, momento na base por pilar (G17), sapata de divisa e
  viga de equilíbrio (G17), viga baldrame e recalque (G18).
- A única sapata desenhada na árvore é `desenho_concreto._svg_sapata` (l.195), e ela é um
  detalhe **dentro** da prancha de armação do galpão pré-moldado — não serve ao prédio.

**Entregar:** planta de locação/formas de fundação do prédio — sapatas (ou blocos) na
malha de pilares, com dimensões, cota de apoio e a carga de projeto por elemento; quadro
com o tipo de fundação escolhido e a tensão admissível **declarada** (nunca arbitrada — o
framework não tem default de tensão de solo, e isso é intencional).

**Aceite:** *drawing-vs-data* — um elemento desenhado por pilar, dimensões desenhadas ==
dimensionadas. Passa em `confere_folha_svg`, entra em `FOLHAS`, e o índice ganha a entrada
correspondente (sem entrada em `_PRANCHAS` a folha **evapora** no `continue` do índice —
é o defeito D89 que já aconteceu duas vezes, com a fundação no G56 e a alvenaria no G62).

**Bloqueio conhecido, não confundir:** a *validação de sistema* da fundação contra caso
externo com laudo SPT está **BLOQUEADA** por falta de fonte (ver `06-open-threads#T44` e
`REVISAO-G28-FUNDACAO-FONTE-BLOQUEADA.md`). Isso **não bloqueia** esta folha: aqui se
desenha o que já é calculado.

---

## G81 · A escada é calculada e não tem folha

**Medido:** a escada tem cálculo próprio (Blondel, lances e patamares, largura pela NBR
9077 — a largura é declaração única desde o G12) e aparece **só como texto** no quadro da
planta de incêndio (`desenho_incendio.py:452-457`). Não há emissor `*_svg` de escada no
censo, e o índice não promete um.

**Entregar:** folha da escada — planta e corte com espelho, piso, número de degraus por
lance, patamares, largura exigida × adotada, e a verificação de Blondel visível.

**Triar antes:** o comprimento do patamar hoje é **`A CONFIRMAR`** (igualado à largura do
lance; NBR 9050/9077 não traz o valor na base — ver `04-decisions.md:631`). Desenhe o que
está declarado e deixe o `A CONFIRMAR` visível na folha; **não** feche esse número por
conta própria.

**Aceite:** passa em `confere_folha_svg`, entra em `FOLHAS`, entra em `_PRANCHAS` com
código próprio, renderizada e olhada.

---

## G82 · A hidráulica promete três folhas e o galpão entrega uma

**Medido:**
- `_PRANCHAS["hidraulica"]` promete **PE-HI-01 Água fria, PE-HI-02 Esgoto/ventilação,
  PE-HI-03 Pluvial**.
- O prédio cumpre os três (`edificio_adapter.py:1009-1011`, três arquivos distintos).
- O **galpão** tem um emissor só, `desenho_hidraulica.esquema_hidraulica_svg`, que desenha
  as três redes **na mesma folha** (cores por rede em `COR`, l.17; pluvial l.50-60, esgoto
  l.64-67).
- **Observação aberta do G77, não redesenhada:** `planta_rede_edificio_svg(H, R,
  rede="agua")` desenha **um único ramal** num pavimento vazio. É o que foi dimensionado —
  mas a folha é magra para uma planta de pavimento-tipo.

**Entregar:** decidir e escrever qual é o contrato — três folhas separadas também no
galpão, ou uma folha que **cobre** os três títulos com o índice dizendo isso. Qualquer das
duas serve; o que não serve é o índice prometer 3 e ninguém saber que 1 arquivo responde
por eles. E triar a folha magra da água: há mais a desenhar (ramais por aparelho,
prumadas, registros), ou o escopo deve dizer por que não?

**Aceite:** laço índice↔disco fechado para a hidráulica nas duas tipologias, com o motivo
escrito onde um arquivo responde por mais de um código.

---

## G83 · A varredura das guardas de um eixo só

**Prioridade: alta — é barata e generaliza um defeito já confirmado.**

**Medido:** o G77 achou uma guarda que media **só o X**: `test_desenho_concreto.py:37`
(`test_tudo_cabe_no_canvas`), por regex sobre a fonte do SVG, com 4 coletas de `x`/`cx`/`x1`/`x2`
e nenhuma de `y`. O defeito que ela deixou passar por anos: a cota de largura do pilar caía
**3,5 px abaixo** da folha, invisível no entregue. Uma varredura rasa mostrou que
`test_desenho_concreto.py` referencia Y só 2 vezes.

**Entregar:** uma lente que ache, na suíte inteira, asserção geométrica que mede **um eixo
só** ou que lê coordenada por **regex/substring em vez de parse**. Não precisa ser
sofisticada: `x`-sem-`y`, `width`-sem-`height`, `re.findall` sobre string de SVG. Triar o
que ela achar — nem todo caso é defeito (uma guarda pode ser legitimamente unidimensional);
o que não pode é ser unidimensional **por esquecimento**.

**Aceite:** lente com baseline nos dois sentidos (injete uma guarda X-only num arquivo
temporário e ela acusa), triagem escrita de cada achado, e as guardas realmente cegas
promovidas a parse + `confere_folha_svg`.

**Nota:** o próprio `test_tudo_cabe_no_canvas` continua no repo e continua útil; ele só
não é suficiente. Não o apague — complete-o.

---

## G84 · Declara-ou-recusa (padrão G75) nos quatro módulos com mais `A CONFIRMAR`

**Medido** (contagem de `A CONFIRMAR` por arquivo, fora de testes):
`galpao_hidraulica.py` **16**, `piso_industrial.py` **14**, `secundarios_nbr8800.py` **13**,
`montagem.py` **13**. (Os próximos: `ponte_rolante` 12, `fotovoltaico` 12, `pacote_legal` 11,
`esgoto_reuso` 11.)

**O que isso significa e o que não significa.** `A CONFIRMAR` **não é** defeito — é a forma
honesta de nomear dado que o projetista precisa declarar, e este repo prefere isso a
arbitrar. O goal **não é zerar a contagem**. É passar a lente do G75
(`varredura_defaults_veredito.py`) nesses quatro e separar três casos:
- (a) `A CONFIRMAR` legítimo — dado do usuário, fica, e o escopo o nomeia;
- (b) `A CONFIRMAR` que já tem fonte no acervo — vira cálculo com citação;
- (c) **default silencioso disfarçado** — o `.get(chave, valor)` ou `cfg.get(k) or padrão`
  que decide veredito sem ninguém declarar. Esse é o alvo real, e é o defeito que o G75
  achou na Tab. 9 da alvenaria (a nota "a" trocava o teto de esbeltez de 24 para 30 **e** o
  gamma de 2,0 para 3,0: `he/te = 27` reprovava sem a nota e passava com ela).

**Aceite:** cada recusa nova grep-ável por `... nao declarado`; a triagem de (a)/(b)/(c)
escrita com número, não com opinião; `varredura_defaults_veredito` com baseline atualizado
nos dois sentidos.

**Armadilha:** o mapa de superfície. No G75, os 10 primeiros testes saíram no palpite
errado sobre **onde** cada recusa pousa (`EntradaEstrutura` levantada, `gates[...]`,
`fechamento_carga["erro"]`, `baldrame_erro`). Descubra a superfície pelo vermelho antes de
escrever a asserção.

---

## G85 · Nove módulos que nenhum teste nomeia

**Medido** — módulos importados por outros (logo **não são ilhas**; a alcançabilidade está
verde), mas cujo nome **não aparece em nenhum arquivo de `tests/`**:

| Módulo | Importadores | Observação |
|---|---|---|
| `fogo_nbr14323` | 2 | aço em situação de incêndio — **normativo** |
| `distorcional_fsm` | 2 | flambagem distorcional pelo método das faixas finitas |
| `recalque_edificio` | 3 | recalque diferencial do prédio |
| `junta_dilatacao` | 2 | junta de dilatação |
| `tercas_iteracao` | 2 | iteração das terças |
| `layout_ambientes` | 3 | primitiva de retângulo de cômodo (ver **G78**) |
| `pycufsm_compat` | 3 | camada de compatibilidade |
| `casa_residencial_sintetica` | 1 | fixture sintética (mantida de propósito) |
| `smoke_executivo` | 2 | smoke do executivo |

**Cuidado com a inferência:** "nenhum teste nomeia" **não é** "sem cobertura" — vários são
exercitados transitivamente. Esta lista é uma **lista de suspeitos**, não de culpados.

**Entregar:** por módulo, medir a cobertura real (rode a suíte com cobertura, ou injete um
defeito e veja se algo fica vermelho — o método do repo) e então **ou** escrever o teste
direto, **ou** registrar por escrito quem o cobre transitivamente. Comece pelos dois de
engenharia pesada: `fogo_nbr14323` e `distorcional_fsm`.

**Aceite:** tabela fechada, um veredito por módulo, com o defeito injetado como evidência
onde se alegar cobertura transitiva. `casa_residencial_sintetica` já tem decisão registrada
(mantida como o único adaptador nativo com `hooks={}`) — confirme, não redecida.

---

## G86 · O telhado reprovado some do federado, em silêncio

**Medido:** `ATENDE` é condição para o telhado entrar no modelo federado
(`04-decisions.md:925`, D101/G72, registrado como *"Aberto, nomeado, não redesenhado"*).
Um telhado **reprovado** desaparece do clash — justo quando a interferência mais importa —
e é a **única disciplina com essa condição**.

**Entregar:** decisão de contrato, não cálculo novo. Duas saídas aceitáveis: (a) entra
sempre e a folha/o federado carimbam REPROVADO; (b) não entra nunca, e o escopo diz por
quê com o artigo. O que não serve é o silêncio atual.

**Custo:** pequeno. **Parentesco:** família da saturação silenciosa — o veredito ruim some
em vez de aparecer.

---

## G87 · Orçamento: os sistemas que nunca entraram na tabela

**Medido** (`04-decisions.md:773`): a guarda do G14 nomeia insumo **que está na tabela e
ficou sem quantidade** (`fechamento_lateral`); ela não vê os sistemas que **nunca entraram
na tabela**. A medida que expôs o buraco: R$ 790 mil ÷ 1134 m² ≈ **R$ 700/m²** contra CUB
na casa de R$ 2.500–3.000/m². A diferença é alvenaria, revestimento, esquadria,
impermeabilização, elevador e incêndio.

**Feito:** o `relatorio.txt` traz a seção **A CONFIRMAR** que os nomeia.
**Aberto:** eles seguem fora do orçamento.

**Entregar:** quantificar a partir do **modelo** (o BIM/federado já tem parede, laje,
esquadria), não do preço. A regra permanece **nomear, nunca estimar**: insumo sem preço
declarado sai nomeado, não chutado.

**Aceite:** a guarda passa a distinguir três estados — "a obra não tem", "ninguém
quantificou" e "quantificado sem preço" — e o orçamento parcial não pode se declarar
fechado.

---

## G88 · Dívida de documentação (barata, e enganosa se ficar)

**Medido:**
- `wiki/03-phases.md` para em **S42**, enquanto `wiki/04-decisions.md` já está em **D105**.
  Quem ler as fases acredita que o trabalho parou há ~45 goals.
- `fontes/fontes-faltantes.md` ainda diz *"Destrava o telhado da casa, hoje
  `telhado_madeira: not_available`"* — falso desde o G66.
- **Fechados por medição, não reabrir** (registrados no `BACKLOG.md`): as constantes órfãs
  `LAMBDA_BLOCO`/`ALPHA_C`/`XD_LIM` já foram renomeadas com sufixo `_C50` no G51;
  `s_limite_governante` **acrescenta** o rótulo da NOTA C55–C90 em vez de sobrescrever
  (`pilar_concreto.py:700`); a viga contínua do prédio **é** verificada desde o G34
  (`edificio_multipavimento.py:292-303`).

**Entregar:** fases reconstruídas do git para o arco G43→G77, a linha obsoleta do
`fontes-faltantes.md` corrigida, e um índice que aponte para este arquivo.

---

## Estado do bloco de fontes — **nenhuma norma ausente** (medido em 2026-09-09)

Todo backlog deste projeto abre por aqui, porque as normas que faltam são providenciadas
fora do chat e a lista se perde no scroll. **Desta vez a lista está vazia, e por medição:**
cruzamento entre os 53 identificadores NBR de `fontes/catalogo.csv` e os 57 citados no
código deu 2 candidatas, ambas descartadas — a **NBR ISO/CIE 8995-1** é falso positivo de
regex (o infixo `ISO-CIE` no nome do arquivo) e está no acervo; a **NBR 7229/13969** aparece
só como nota histórica, com a **NBR 17076:2024** no acervo e guarda em
`tests/test_normas_catalogo.py:95`.

**Nenhum goal acima está bloqueado por ausência de fonte.** A única exceção do repo não é
norma, é **caso externo**: a validação de sistema da fundação segue sem laudo SPT
(`06-open-threads#T44`), com critério de desbloqueio escrito.

Se um goal futuro precisar de norma que não esteja no acervo, **o primeiro passo é medir a
ausência contra o `catalogo.csv`** e listá-la aqui — e triar se ela não está superada ou
sob outro identificador (foi o que aconteceu com a 7229).

---

## Ordem sugerida

| # | Goal | Por quê nessa posição | Custo |
|---|---|---|---|
| 1 | **G78** arquitetura da casa | maior buraco medido, dado a uma chave de distância | médio |
| 2 | **G83** guardas de um eixo | barata e generaliza defeito confirmado | baixo |
| 3 | **G86** telhado no federado | pequeno, afiado, decisão de contrato | baixo |
| 4 | **G79** terraplenagem desenha | calcula tudo, entrega zero folha | médio |
| 5 | **G80** fundação do prédio | dado pronto, folha ausente | médio |
| 6 | **G85** módulos sem teste | começa por `fogo_nbr14323` e `distorcional_fsm` | médio |
| 7 | **G84** declara-ou-recusa nos 4 | segue o molde do G75 | médio |
| 8 | **G82** hidráulica 3×1 | decisão de contrato + folha magra | baixo |
| 9 | **G81** folha da escada | depende de `A CONFIRMAR` do patamar | baixo |
| 10 | **G87** orçamento | maior, e depende do modelo | alto |
| 11 | **G88** documentação | meia hora, evita recaçar o que está fechado | baixo |

**G78, G79, G80 e G81 tocam `FOLHAS` em `tests/test_folhas_g77.py`.** O portão do censo
fica **vermelho** enquanto a folha nova não tiver caso lá — isso é o desenho funcionando,
não um obstáculo. Se dois agentes rodarem em paralelo, esperem conflito nesse arquivo e no
`_PRANCHAS` de `pacote_legal.py`.
