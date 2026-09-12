# Backlog de goals executáveis — pós-G119 (2026-09-12)

> **FILA CONSUMIDA (2026-09-12).** Os cinco goals foram executados e auditados (G125,
> [[04-decisions#D151]]). Não reexecute. A fila aberta é `BACKLOG-GOALS-G126-G130.md`.
>
> | Goal | Verbete | Auditoria |
> |---|---|---|
> | G121 memória do portão | D146 | medidor cego para o freecad.exe — corrigido |
> | G120 os 8 códigos da F150 | D147 | bateu (`{'0BD8': 188}`, ∞ na imagem) |
> | G122 2014 → 2023 fora da Emenda | D148 | 5 contas da 8.2.5 fora do item; endereço cobrado no texto inteiro — corrigidos |
> | G123 edição declarada | D149 | 4 folhas de concreto de casa/prédio sem carimbo — corrigido |
> | G124 constantes órfãs | D150 | bateu (15 resíduos sem leitor no repo) |

Fila ~~ABERTA~~ consumida. Cinco goals (G120–G124). As filas anteriores estão fechadas e ficam apenas
como registro — não reexecute nada de lá: `BACKLOG-GOALS.md` (G78–G88),
`BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`, `BACKLOG-GOALS-G107-G112.md` e
`BACKLOG-GOALS-G114-G118.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-12 na branch `feat/tipologias-e-verticais-de-projeto`,
na auditoria do lote G114–G118 (G119, verbete D145). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis. O lote G114–G118 deixou a NBR 6118:2023
legível e mediu o impacto de migrar. Este arco fecha o que a auditoria achou — o resto da
cifra, o resto da edição nova — e ataca uma classe que apareceu duas vezes seguidas: o
**instrumento que não consegue acusar**.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

Nenhuma norma ausente.

- **F150 — NBR 6118:2023, Versão corrigida 2.** Camada de texto **decodificada** no G117
  (`f150_decodifica.py` → `...-dec.txt`, 260 p., 14662 linhas, fora do git). Corrigida no
  G119: 8 códigos saíam **trocados** (não ausentes) e foram mapeados contra a página
  renderizada. **Restam 8 códigos / 372 ocorrências** saindo como marcador `[<U+XXXX>]` —
  é o G120. Fórmulas, tabelas e figuras seguem fora.
- **F098 — Emenda 1:2026.** Texto legível. 51 itens inventariados no G116
  (`wiki/07-nbr6118-2023-em1-impacto-g116.md`), **incluindo as 7 instruções `Excluir`**.
- **F016 — NBR 6118:2014.** Texto extraível. É por ela que o framework calcula.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma: **leia a página renderizada**. Vale mesmo
   agora que a F150 tem texto — o G119 nasceu de confiar na camada de texto.
4. **Saturação silenciosa**, incluindo `OK` por item que não chega ao veredito (G113).
5. **Asserção tautológica**, incluindo teste que reimplementa a fórmula (G113) e — novo no
   G119 — **teste que confere um literal contra ele mesmo** (a âncora do G114 valia 578
   porque estava escrito 578, e a produção não a lia).
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.
7. **NOVO (G119) — instrumento tem de conseguir acusar.** Todo acumulador de ausência
   (`faltando`, `desconhecidos`, `nao_coberto`) precisa de um teste que o faça **disparar**.
   O `DESCONHECIDO_FMT` do G117 existia, era contado e relatado — e nada nunca o escrevia:
   o medidor dizia zero por ser estruturalmente incapaz de acusar, e sob ele
   "fck ≤ 50 MPa" saía "fck ± 50 MPa".
8. **NOVO (G119) — constante "medida" que a produção não lê é comentário.** Se um número
   foi medido, alguma conta tem de derivar dele.

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**:
`varredura_faixa_validade.confere_cobertura()`, `varredura_asserts_sequencia.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py` e
`tests/test_carimbo_mapa_g112.py`.

**O verbete é parte da entrega.** O lote G114–G118 foi o primeiro com verbete em todos os
goals — mantenha.

**Uma fonte só.** Dado que o cliente recebe mora na produção; lente e teste importam de lá.

---

## Ordem e dependência

- **G120 antes do G122:** o G122 lê a 2023 inteira; os 372 marcadores atrapalham.
- **G121** é independente. Faça-o cedo: o portão do G102 voltou a caber depois do G114,
  mas nada impede a regressão — o teto que existe mede tempo, e o que o matava era memória.
- **G123** depende do G116 (já entregue) e é o único que toca veredito — leia o aviso dele.
- **G124** é independente.

---

# GOALS

## G120 · Os 8 códigos que a F150 ainda não lê

**Prioridade: alta.** Destrava o G122 e fecha a cifra.

**Medido (G119):**
- Depois do G119, `f150_decodifica.decodifica_pdf` relata
  `desconhecidos={'0BD8': 188, '00ED': 143, '0092': 16, '0BC5': 12, '0101': 7, '00EE': 4,
  '00A8': 1, '0081': 1}` — **372 ocorrências**, hoje visíveis como `[<U+XXXX>]` no `.txt`.
- Antes do G119 esse relatório dizia `{}`: o marcador nunca era escrito. Os 8 saíam como
  outro caractere plausível, junto com os 8 que o G119 já corrigiu.
- Contextos já levantados (decodificados ao redor): `0x00ED` em "ça cortante ⟨?⟩ Estado"
  (143×, provável travessão/bullet); `0x0BD8` sempre antes de item de lista "a)" (188×);
  `0x0101` em "0,85 ⟨?⟩ [1,0 –"; `0x00EE` em "igual a -15 ⟨?⟩ 10"; `0x0092` isolado (16×).
- **Não medido:** o glifo real de cada um. Cada um exige a página renderizada.

**Entregar:**
- Cada código conferido na **página renderizada** (regra 3) e mapeado em `TABELA_ESPECIAL`
  com a página anotada, no formato que o G119 deixou (`0x9D: "ª",  # p.124 "2ª ordem"`).
- O que não for legível na imagem **continua marcador** — e o motivo vai escrito. Não
  adivinhe pelo contexto: foi exatamente assim que "≤" virou "±".
- `.txt` regerado; `catalogo.csv` (F150) atualizado com o novo número de restantes.

**Aceite:** `desconhecidos` cai para os que foram declarados ilegíveis, com a lista nominal;
âncora nova em `AMOSTRA_G117` para cada código mapeado (o baseline do tamanho da amostra
muda junto, com triagem escrita); `test_04_codigos_que_saiam_trocados_g119` ganha as linhas
novas. Nenhum mapeamento sem página anotada.

**Não fazer:** deduzir glifo por frequência ou por contexto sem abrir a imagem. Subir ao
NotebookLM sem o OK do usuário.

---

## G121 · O teto do portão mede tempo, e o que matava era memória

**Prioridade: alta.** Devolve tempo e confiança em toda suíte seguinte.

**Medido (G119):**
- `tests/test_indice_disco_rodada_g102.py` **completou pela primeira vez nesta máquina**
  depois do reuso do turnkey do G114: **6 passed em 1230 s**, com ~1,4 GB livres e sem
  processo órfão. Na auditoria do G113 ele morreu de memória **quatro vezes**, a última
  rodando sozinho.
- O portão tem `CUSTO_TETO_SEG = 1800` e `test_01` cobra o total **medido na rodada**
  (correção do G106). Mas o teto é de **tempo**: nas quatro mortes do G113 o tempo nunca
  chegou perto do teto — o processo era morto antes. **O portão não vê o que o matava.**
- **`CUSTO_MEDIDO_SEG` NÃO foi re-congelado, e isto fica aberto de propósito.**
  Ele ainda diz `{"casa": 2.7, "predio": 35.7, "galpao": 923.0}` — os 923 s são de
  ANTES do reuso do G114. A rodada com `-s` que capturaria o número por tipologia foi
  **morta por falta de memória** na auditoria (a máquina estava em uso ao lado dela);
  a corrida limpa e isolada completou, mas o pytest engole o `print` sem `-s`, então só
  o total do arquivo (1230 s) ficou medido. Escrever um número por tipologia sem
  medi-lo seria dado arbitrado. **Remedir e re-congelar é a primeira tarefa deste goal**,
  com a máquina livre.
- **Não medido:** o pico de memória residente da rodada. Observado à mão durante a corrida:
  freecad.exe chegou a ~803 MB com a máquina em 8 GB / ~1,4 GB livres.

**Entregar:**
- O portão mede o **pico de memória** da rodada (o processo e os filhos `freecad.exe`) e o
  registra ao lado dos segundos, no mesmo formato de `CUSTO_MEDIDO_SEG`.
- Um teto de memória declarado, com a folga escrita — e o motivo do valor, como o teto de
  tempo tem.

**Aceite:** o pico medido sai no `print` do `test_01` junto com os segundos; vermelho por
injeção (teto artificialmente baixo em `tmp_path` reprova); a rodada completa segue verde
na máquina de 8 GB. Se o pico não for mensurável de forma confiável no Windows com os
filhos do FreeCAD, **diga isso e entregue o que der** — medida parcial declarada vale mais
que teto inventado.

**Armadilha (custou 4 mortes no G113):** com stdout redirecionado o pytest usa buffer de
bloco. **Arquivo de saída com 0 byte no meio da corrida não significa que o processo morreu
antes do primeiro ponto** — confira o processo, não o arquivo.

---
## G122 · As diferenças 2014 → 2023 que não estão na Emenda

**Prioridade: alta. Mede e escreve — não muda cálculo.** Depende do G120.

**Medido (G116/G119):**
- O G116 inventariou os **51 itens da Emenda 1:2026** e as cláusulas de interseção que
  sondou: 2014 = 2023 pré-Em1 em 13.2.5.1-b, 15.8.1, 17.3.5.2.4, 17.4.1.1.3, 19.5.4 e 20.1.
- **Uma exceção já achada:** 15.7.3 — o parágrafo do galpão **não existe na 2014** e **já
  está na 2023**. Novidade da edição, fora da Emenda. Achada por sondagem, não por varredura.
- **A lacuna, declarada na Tabela 2 do inventário:** o resto do 2014 → 2023 **nunca foi
  medido**. A 2023 é edição nova (4ª), não a 2014 corrigida.
- A 2014 tem 238 p. extraíveis; a 2023 tem 260 p. agora decodificadas.

**Entregar:**
- Confronto **seção a seção** 2014 × 2023 (pré-Emenda), não por amostragem: para cada
  cláusula que o framework cita, o texto das duas e o veredito (igual / editorial /
  regra muda / número muda).
- Toda divergência que mude número entra na Tabela 1 do
  `wiki/07-nbr6118-2023-em1-impacto-g116.md`, no mesmo formato, com o caso do repo.

**Aceite:** cobertura nos dois sentidos — cada citação de "6118" no código tem linha no
inventário, e cada seção divergente tem endereço `arquivo:linha`. O que ficar ilegível
(fórmula, tabela) é **declarado por cláusula**, nunca silenciado. Diferença achada por
comparação de texto tem de ser confirmada na **imagem** das duas edições antes de virar
veredito.

**Não fazer:** trocar a base normativa de módulo nenhum (é o G123, e é decisão do usuário).

---

## G123 · O projeto declara por qual edição da norma foi calculado

**Prioridade: alta.** É o único goal do arco que toca o que o cliente recebe.

**Medido (G116/G119):**
- O framework calcula pela **NBR 6118:2014** (F016) e **nenhuma folha, pacote legal ou
  relatório diz isso**. O cliente recebe um projeto de concreto sem a edição declarada,
  quando a vigente é a 2023 + Em1:2026.
- O G116 já mediu onde a conta mudaria: **2 pontos NÚMERO-MUDA** — 13.2.5.1-b (furo
  circular de 12,1–12,5 cm passa a dispensar verificação; o framework hoje pede a mais,
  é conservador) e 12.3.3 (s = 0,20 para todo C60+: C60 CPIII a 7 d dá 41032 kN/m²
  pela 2014 contra 49124 pela 2023+Em1, **+19,7 %** — conferido nesta auditoria) —
  além de 6 REGRA-MUDA e 2 PROCESSO-NOVO (5.3 ATP, 20.6 balanço/marquise).

**Entregar (só a parte 1 é automática):**
1. **Declaração.** Toda peça de concreto que sai para o cliente (pranchas, pacote legal,
   relatório) carimba a edição pela qual foi calculada, vinda de **uma fonte só** na
   produção. Ausência de declaração reprova num portão.
2. **A chave, desligada.** Um parâmetro explícito de edição, sem default silencioso: o
   projeto declara `2014` ou `2023+Em1`, e os 2 pontos NÚMERO-MUDA leem dele. Sem o
   parâmetro, o comportamento é o de hoje **e a folha diz qual é**.

**Aceite:** vermelho por injeção (peça sem a declaração reprova); os dois pontos calculam
pelas duas edições no mesmo caso do repo e o número bate com o do inventário (12.3.3:
41032 × 49124); o portão confere que **nenhum** módulo troca de edição por conta própria.

**Não fazer — leia com atenção:** **não decida qual edição o projeto usa.** Migrar é decisão
do usuário. Este goal entrega a declaração e a chave; quem vira a chave é ele. E não
implemente os PROCESSO-NOVO (ATP, marquise): são gate novo, não troca de conta.

---

## G124 · As 51 constantes que ninguém lê

**Prioridade: média.** A classe que apareceu duas vezes no G119.

**Medido (G119), por AST sobre `framework/galpao_fw/*.py`:**
- **95** constantes de módulo (MAIÚSCULAS) são escritas e **nunca lidas no próprio módulo**;
  destas, **51 não são lidas em lugar nenhum do repo** — nem por import, nem por teste.
- Várias são **valor normativo**: `R_MAX_EXPLOSIVO` (aterramento_nbr15749),
  `Q_BORDA_GUARDA_CORPO` e `Q_ELEMENTO_ISOLADO_COBERTURA` (cargas_nbr6120),
  `DV_TERMINAL_MAX` (condutores_nbr5410), `FVK_ARMADA_*` (alvenaria_estrutural, 5 delas),
  `NOTA_B_TAB2` e `COMB_FACHADA` (desempenho_nbr15575).
- Concentração: alvenaria_estrutural 5, deteccao_alarme/iluminacao_emergencia/luminotecnica/
  madeira 3 cada.
- **Por que importa:** um limite de norma escrito numa constante que nenhuma conta lê
  significa uma de três coisas — a exigência está implementada **em outro lugar** (número
  duplicado, livre para divergir), **não está implementada** (a folha não a verifica), ou
  a constante é resíduo. As três precisam de resposta diferente, e nenhuma pode ficar como
  está. A âncora do G114 era o caso 3 disfarçado de caso 1.

**Entregar:**
- Triagem das 51, uma linha cada: **usada em outro lugar** (com `arquivo:linha` do número
  duplicado — e então a constante vira a fonte única), **não implementada** (vira dívida
  declarada, com a cláusula), ou **resíduo** (removida).
- Lente `varredura_constantes_orfas.py` (script avulso, como as outras) com baseline
  congelado nos dois sentidos e isenção **com motivo escrito** — nunca renomeando a
  constante para escapar (lição do G98).

**Aceite:** a lente roda no lote e reprova quando uma constante órfã nova entra (vermelho
por injeção em `tmp_path`); toda isenção tem motivo; nenhuma constante de norma sai da
triagem sem endereço.

**Não fazer:** ligar uma constante numa conta só para "usá-la" — isso muda veredito por
motivo administrativo. Se a exigência não está implementada, declare a dívida.

---

