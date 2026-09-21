# Backlog de goals executáveis — pós-G157 (2026-09-21)

Fila **ABERTA**. Seis goals: **G158, G159, G160, G161, G162 e G163**, nesta ordem, **um de
cada vez**. As decisões do usuário estão tomadas (2026-09-21, seção "Decisões tomadas"):
nenhum goal para para perguntar — exceto o G163, cuja *entrega* é a tabela de decisão.

As filas anteriores estão fechadas e ficam apenas como registro — não reexecute nada de lá:
`BACKLOG-GOALS.md` (G78–G88), `BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`,
`BACKLOG-GOALS-G107-G112.md`, `BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md`,
`BACKLOG-GOALS-G126-G130.md`, `BACKLOG-GOALS-G132-G136.md`, `BACKLOG-GOALS-G137-G142.md`,
`BACKLOG-GOALS-G143-G148.md`, `BACKLOG-GOALS-G149-G153.md` e `BACKLOG-GOALS-G154-G157.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em **2026-09-21** na branch
`feat/tipologias-e-verticais-de-projeto` (commit `a85bdbe`, árvore limpa), lendo o código e o
`git log` — **sem** rodar a suíte. O que não foi medido está dito, goal por goal. O G158 é a
auditoria que mede o resto: o que ele achar **corrige este arquivo** antes do G159.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis — o cliente informa o projeto e recebe cálculo,
3D e todas as folhas. O arco G154–G157 fechou (D180, D181, D182, D187). Este arco fecha o que
o fechamento **deixou aberto**: a **auditoria do lote que não rodou**, e um **módulo de conta
normativa de 600 linhas que entrou na produção por fora do protocolo** — invisível à guarda
do G157 (que casa por prefixo de commit) e à lente do G156 (que só enxerga `NBR`), com ~476
células de tabela transcritas de uma norma de distribuidora sem uma única conferência na
imagem. E fecha as **sete pendências normativas** que o lote empilhou nos verbetes.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`, 151 linhas)

**Nenhuma norma ausente trava este arco.**

- **WKI-OMBR-MAT-18-0263-INBR-R01** (Instrução de Trabalho 263, v.01 de 02/03/2018, "Cálculo
  de Demanda para Medição de Cliente em Baixa Tensão") — **está no acervo**: **F131**,
  `fontes/05_ELETRICA/ELETRICA__ENEL-RIO__WKI-OMBR-MAT-18-0263-INBR-R01__calculo-demanda-bt.pdf`
  (1 443 120 bytes). **É PDF digital, não escaneado**: a p.14 devolve texto extraível
  (conferido em 2026-09-21). A convenção 3 continua valendo mesmo assim — a célula se confere
  **na imagem da página**, porque extração de texto de tabela embaralha coluna.
  No catálogo a linha o marca `norma_distribuidora_enel_rio_apoio` /
  `listada_enel_rio_2026`, com a nota: "a listagem oficial a descreve como exclusiva para
  cálculo de demanda, com demais requisitos nas normas de conexão BT".
- **Não medido:** se a WKI R01/2018 foi substituída por revisão posterior. O catálogo diz
  "listada_enel_rio_2026" (estava na listagem oficial consultada em 2026-08-14), não
  "vigência conferida". **Isso é pendência do G163**, não trava do arco.
- As 4 sem entrada seguem triadas e congeladas, sem mudança: **NBR 5413** (substituída pela
  ISO/CIE 8995-1:2013, F102), **NBR 13438** (nome de material em `cargas_nbr6120.py:115`),
  **NBR 8522** e **NBR 8965** (remissões do texto da 6118 transcrito) — em
  `tests/test_normas_catalogo.LACUNAS_PRE_EXISTENTES` e `REMISSOES_DA_NORMA_TRANSCRITA`.

**Estar no catálogo não é ter lido o item** (D179). **Transcrever a tabela não é ter
conferido a célula** (G2: seis células de Bares vieram com OCR errado).

**Bloqueado por DADO de projeto, não por norma (fora deste arco):** PE-IN-03 escada do galpão
(geometria não declarada; fronteira G101), PE-EL-03 da casa (malha e SPDA não declarados;
D171), PE-AR-01 implantação e PE-AR-03 cortes da casa (lote, recuos, cotas), fundação por
laudo SPT externo (T44).

---

## O que fechou, e o que o fechamento deixou aberto (medido)

**Fechou.** `cd319d4` G157 (D187), `6d3b16d` G156 (D182), `4432af0` G155 (D181), `4018471`
G154 (D180). Os quatro verbetes têm número D e linha de fase.

**Aberto 1 — a auditoria do lote não rodou.** Todo lote anterior fechou com auditoria, e é a
auditoria que achou os defeitos mais caros: `d998a5f` (D172, o hidrante inventado pelo `or 1`
e a INC03 que derrubava o incêndio), `076a69f` (D176, o worker que sobrevivia ao piso e a viga
com duas marcas), `6d94510` (D179, o FS 3,0 que se dizia normativo). Depois do `cd319d4` **não
há commit de auditoria** — há quatro commits de outra coisa (abaixo). A auditoria é também o
passo que **mede** o backlog seguinte; sem ela, fila nova é afirmação (é a própria lição do
D179, que achou a afirmação falsa **no backlog anterior**).

**Aberto 2 — entrou código de produção por fora do protocolo.** Quatro commits depois do
G157, todos em 2026-09-19:

| commit | mensagem | o que mexeu |
|---|---|---|
| `dc686af` | `feat(p70): complete WKI motor tables` | `demanda_residencial_enel.py` + teste |
| `700afd8` | `feat(p71): apply motor efficiency` | idem (co-autor Cursor) |
| `6734fc8` | `fix(revisao): consolida motores de mesma potencia na tabela WKI` | idem (+52 linhas de teste) |
| `a85bdbe` | `fix(demand): read kitchen module from the transcribed WKI table` | idem |

Medido sobre eles:

- **`demanda_residencial_enel.py` tem 600 linhas** e está **vivo na produção**:
  `residencial_eletrica.py:16` importa, `:313` chama `calculate_residential_demand(payload)`,
  `:355` chama de novo para os warnings; `residencial_eletrica` é a vertical elétrica da casa
  (`casa_residencial.py:53`, `builtin_adapters.py:17`). O número chega à folha:
  `desenho_eletrico_residencial.py:273-276` imprime `demanda %s kVA` de
  `calculation.demand.final_kva`.
- **Sem verbete, sem número D, sem linha em `wiki/03-phases.md`.** Grep por `wki`/`enel`/
  `demanda_residencial` em `wiki/*.md`: **zero**.
- **A guarda do G157 não enxerga.** `tests/test_verbete_fase_g157.py:46-66`: `GOAL_MINIMO =
  149`, `GOAL_CORRENTE = "G157"`, MAPA goal→D, e a varredura casa **prefixo de commit
  `G1xx:`**. `feat(p70)` / `fix(demand)` passam por fora por construção — é o padrão do **G98**
  (módulo novo invisível ao censo) outra vez, agora do lado do registro.
- **A lente do G156 não enxerga.** `tests/test_citacao_norma_g156.py:42`:
  `PAT_NBR = re.compile(r"NBR\s+(?:NM\s+)?\d{3,5}...")`. As citações do módulo dizem
  "WKI Enel item 6.1, PDF p. 5" (`:146`), "WKI TABELA 2 (PDF p. 14)" (`:74`), "WKI TABELA 3
  (PDF p. 14)" (`:106`), "WKI 6.2.3.3" (`:164`), "WKI notes 1 and 2 (p. 7)" (`:380`), "item
  6.2.3.2 ... TABELAS 2 e 3" (`:433`), mais as mensagens de recusa (`:450`, `:462`, `:474`,
  `:511`, `:523`). **Nenhuma passa pelo `PAT_NBR`.** Trazem item e página (bom comportamento),
  mas **nenhuma foi triada contra a imagem** — não estão na BASELINE do G156.
- **~476 células numéricas transcritas, nenhuma conferida na imagem** (contado em
  2026-09-21): `_MOTOR_TABLE_KVA` **370 células** (370 linhas de tabela), `_HEATING_TABLE`
  **90**, `ROOM_MODULES_KVA` 7, `LOCATION_FACTORS` 4, `_SPECIAL_LIGHTING_POWER_FACTORS` 4,
  `_MOTOR_TABLE_MAX_QUANTITY` 1, `_MOTOR_NO_PLATE_KW_PER_CV` 1.
- **Um erro de número já foi entregue e corrigido sem verbete.** O `6734fc8` diz: motores de
  mesma potência declarados em linhas separadas eram somados como grupos próprios, dando
  **2,584 kVA** onde a coluna de quantidade 2 da tabela imprime **2,28 kVA**. Ou seja: a conta
  que vai ao cliente esteve errada, e a correção não tem D. Isso é a prova de que a
  transcrição precisa de aferição — o defeito só apareceu porque alguém releu a tabela.
- **Não há fixture de exemplo resolvido da fonte.** Grep por `exemplo`/`anexo`/`worked` em
  `tests/branches/project_loop/test_residential_electrical_demand.py`: **zero**. Os verticais
  maduros deste repo têm aferição contra exemplo resolvido (concreto: Bastos/Araújo/Carvalho;
  fundação: Alonso). Este não tem.
- **O módulo está isento na lente de faixa**, com motivo declarado:
  `varredura_faixa_validade.py:592` — "demanda por tabelas Enel; sem faixa no vocabulário da
  lente." (Isenção com motivo é o certo, G98 — fica como está.)
- **Não medido:** se a suíte inteira está verde no `a85bdbe` (o `6734fc8` reporta "47 passed"
  só da suíte de demanda residencial); se `_HEATING_TABLE` e `ROOM_MODULES_KVA` têm o mesmo
  problema de consolidação que os motores tinham; se a WKI tem exemplo resolvido.

**Aberto 3 — sete pendências normativas empilhadas nos verbetes** (`wiki/04-decisions.md`,
`:5517-5523` no D182 e `:5597-5602` no D187). Todas declaradas no código, nenhuma trava nada.
Ver **G163**.

---

## Protocolo de execução em sequência (inalterado desde 2026-09-17)

1. **Um goal por vez, na ordem G158 → G159 → G160 → G161 → G162 → G163.** Nunca abra dois ao
   mesmo tempo, nem em outra janela/sessão. O próximo só começa depois do commit do anterior.
2. **Checagem de entrada (antes de editar qualquer arquivo):**
   - `git log --oneline` tem o commit do goal anterior (G158: `a85bdbe`; G159: o commit
     "G158:"; e assim por diante). Se não tiver, **não comece**: encerre dizendo qual falta.
   - `git status --short` só pode mostrar o WIP **do próprio goal**. Arquivo modificado que não
     é do goal → **não comece**: encerre listando os arquivos. Nunca apague, reverta ou faça
     stash de trabalho alheio.
   - Nenhum `pytest`/`suite_paralela`/`freecad*` rodando (liste os processos). Se houver, é
     outra execução: encerre dizendo o PID.
3. **Sem perguntas no meio.** Escolha que o backlog não previu segue a **regra conservadora**:
   não muda número, veredito, default nem trava; declara a ausência; a escolha vai ao verbete
   numa linha **"Pendência ao usuário:"**; o goal **continua** até o commit.
4. **Fechamento:** suíte pelo runner no código final (conv. 12 e 16), verbete com número D e
   linha no `wiki/03-phases.md` **no mesmo commit**, commit com o prefixo `G1xx:`. O goal só
   termina com a árvore limpa (`git status --short` vazio).
5. **Interrupção** (queda, contexto, máquina): o próximo disparo do **mesmo** goal retoma pelo
   `git status`/`git diff` — nunca começa o goal seguinte.

**Números D:** o último verbete é o **D187** (G157). Os D livres começam em **D188**, na ordem
em que os goals fecharem.

---

## Decisões tomadas (usuário, 2026-09-21)

- **A auditoria do lote G154–G157 é o G158**, primeiro goal da fila. O que ela medir corrige
  este backlog antes do G159.
- **O módulo WKI se regulariza E as duas portas se fecham:** verbete com D e linha de fase
  para o que os quatro commits entregaram (**G159**); a guarda do G157 passa a medir por
  **arquivo de produção tocado**, não por prefixo de commit (**G159**); a lente do G156 passa
  a cobrir **fonte de distribuidora**, e as citações WKI são triadas na imagem do F131
  (**G160**).
- **As sete pendências normativas ganham goal próprio (G163):** eu confiro cada uma na imagem
  da página do acervo e entrego a tabela (frase, item, página, confere/diverge) para o usuário
  decidir item a item. **Nenhum número muda dentro do goal.**
- **FS da estaca:** segue **(a) 3,0 adotado e declarado** (decisão de 2026-09-17). O G163 traz
  a linha ao usuário de novo por estar na tabela, mas nenhum goal deste arco muda o número ou
  a trava do `validar`.

---

## Convenções que todo goal deste repo segue

1. **Baseline nos dois sentidos**, e toda lente nova com teste que fica **vermelho quando o
   defeito é injetado**.
2. **Injeção em `tmp_path`**, nunca mutando o repo.
3. **Substring → parse → renderizar.** Para norma e para folha: **olhe a imagem**.
4. **Saturação silenciosa**, incluindo `OK` por item que não chega ao veredito (G113) e texto
   cortado (G106).
5. **Asserção tautológica**, incluindo teste que confere um literal contra ele mesmo (G119).
6. **Três aceites por folha:** está certa, sai no manifesto, diz o que desenha.
7. **Instrumento tem de conseguir acusar** (G119) — e acusar **por parte** (G125).
8. **Constante "medida" que a produção não lê é comentário** (G119).
9. **A lente parte de onde o dado é PRODUZIDO** — a conta, o emissor — e confere a citação
   contra ele (G125).
10. **O resumo da suíte se lê inteiro antes de fechar** (G125); a lista inclui `tests/branches`
    e `tests/trunk` (`find tests -name 'test_*.py'`).
11. **Injete o valor em cada lugar de entrada que o produto aceita** (G131); "não se aplica"
    é um terceiro valor declarado.
12. **A suíte do goal roda pelo runner paralelo** (D164/D165), a partir de
    `framework/galpao_fw`, com o interpretador de nome curto 8.3:
    `…\VENV~1\Scripts\python.exe tools/suite_paralela.py -n 3` (~17 min; grava
    `resumo.json` — o goal só fecha com `rc_pytest` 0 **e** `quebras` vazio). O runner põe
    `PYTHONUTF8=1` (D172), confirma o piso de 200 MB em 3 amostras seguidas (D178) e termina só
    a árvore do próprio filho (D176). Não edite o repositório com a suíte rodando. Teste novo
    que sobe freecad.exe/freecadcmd.exe entra em `tests/censo_freecad.GRUPO_FREECAD` com o
    motivo medido. A serial `pytest tests` e os portões de auditoria (`GALPAO_AUDITORIA=1`:
    executivo de aço D165 e galpão do G102 D177) rodam **na auditoria do lote**, não em cada
    goal. Máquina de 8 GB: rodada pesada uma por vez; os aplicativos do usuário ficam abertos.
13. **(D172) Emissor ou conta reaproveitados trazem os fallbacks deles.** Rode com o dado
    **ausente** e com **zero**, um por um; folha nova ligada em código comum fica num `try`
    próprio; injete a falha **só na folha nova**.
14. **(D176) A prova tem de exercitar o caminho que falha.** Kill/abort se prova com processo
    real ocupado; folha com várias páginas confere as marcas entre páginas e contra o BIM.
15. **(D179) Norma citada é norma LIDA.** Toda frase que atribui um número a uma norma traz o
    **item** e foi conferida **na imagem da página** do acervo. "Está no catálogo" não é
    leitura. Número do código que diverge da página **não se troca no goal**: a atribuição se
    corrige ("adotado", com o item ao lado) e a escolha vai ao usuário **como pendência no
    verbete, sem parar o goal** (protocolo, item 3).
16. **(D179) O fechamento é do código commitado.** Mudou código depois da corrida que fecha?
    Rode de novo. O verbete tem **número D** e a linha no `wiki/03-phases.md` entra **no mesmo
    commit**. Processo filho que o teste lança **não herda** o censo nem o worker da corrida de
    fora, e arquivo de teste gerado para o runner aninhado leva um `pytest.ini` ao lado.
17. **NOVO (2026-09-21) — transcrever a tabela não é conferir a célula.** Tabela de norma
    copiada para o código é **dado transcrito**: só vira dado conferido quando cada célula que
    a produção lê foi vista **na imagem da página**, e a conferência fica registrada de forma
    que a próxima edição não a apague. A lição é do **G2** (seis células de Bares com OCR
    errado) e do `6734fc8` (2,584 kVA onde a tabela imprime 2,28).
18. **NOVO (2026-09-21) — o registro se mede pelo arquivo tocado, não pelo nome do commit.**
    Guarda que casa prefixo de commit só vê quem escreveu o prefixo. Código de produção que
    entra sem verbete é invisível, e foi assim que 600 linhas de conta normativa entraram sem
    D (é o **G98** do lado do registro).

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**
antes da suíte: `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py`, `tests/test_normas_catalogo.py`,
`tests/test_galpao_indice_g93.py`, `tests/test_suite_paralela_d164.py`,
`tests/test_auditoria_g137_g142_d172.py`, `tests/test_auditoria_g143_g148_d176.py`,
`tests/test_auditoria_g149_g153_d179.py`, `tests/test_fallback_folha_g145.py`,
`tests/test_fallback_get_g150.py`, `tests/test_titulo_carimbo_g151.py`,
`tests/test_veredito_folha_g152.py`, `tests/test_veredito_folha_g155.py`,
`tests/test_citacao_norma_g156.py`, `tests/test_verbete_fase_g157.py`,
`tests/test_piso_memoria_g153.py` e `tests/test_estaca_g149.py` — mais o portão próprio de
cada fonte que o goal tocar. Goal que muda folha do galpão roda também o portão do galpão
**isolado e serial**
(`GALPAO_AUDITORIA=1 pytest -s tests/test_indice_disco_rodada_g102.py::test_10_portao_rodada_real_galpao_na_auditoria`,
~11 min).

**Otimização de conta (D158):** só com prova de número idêntico. **O verbete é parte da
entrega.** **Uma fonte só:** dado que o cliente recebe mora na produção.

---

## Ordem e dependência

Estritamente sequencial, sem ramificação:

1. **G158** — auditoria do lote G154–G157 e da entrada fora do protocolo. Parte de `a85bdbe`.
   **Corrige este backlog** antes do G159.
2. **G159** — registro: verbete do que entrou + guarda por arquivo. Parte do commit do G158.
3. **G160** — lente de citação para fonte de distribuidora. Parte do commit do G159 (e usa o
   verbete que o G159 escreveu).
4. **G161** — as células transcritas conferidas na imagem. Parte do commit do G160 (a lente do
   G160 já terá triado as *frases*; o G161 tria os *números*).
5. **G162** — a demanda na entrega. Parte do commit do G161 (só depois que o número é
   confiável é que a folha o declara).
6. **G163** — a tabela de decisão das pendências. Parte do commit do G162; lê o que todos
   escreveram.

---

# GOALS

## G158 · A auditoria do lote que não rodou

**Prioridade: alta.** É o passo que mede os cinco seguintes.

**Estado de partida:** `a85bdbe` no `git log`, árvore limpa.

**Medido.**
- Os quatro goals fecharam (D180, D181, D182, D187) e **não houve commit de auditoria** depois
  do `cd319d4`. Os três lotes anteriores fecharam com auditoria (`d998a5f` D172, `076a69f`
  D176, `6d94510` D179) e as três acharam defeito entregue.
- Nenhum dos quatro goals rodou a **serial** nem os **portões de auditoria** — por convenção
  12, eles rodam na auditoria do lote, que é este goal: `pytest tests` serial,
  `GALPAO_AUDITORIA=1` do executivo de aço (D165) e do galpão do G102 (D177, ~11 min).
- **Não medido:** se a suíte inteira está verde em `a85bdbe`. Os quatro commits pós-G157
  reportam só "47 passed" da suíte de demanda residencial; o G157 fechou em `cd319d4`, e
  **código de produção mudou depois** (`demanda_residencial_enel.py`) — pela convenção 16, o
  fechamento é do código commitado, então a corrida que vale ainda não existe.

**Entregar.**
1. **A corrida que vale:** runner paralelo em `a85bdbe` (`rc_pytest` 0 e `quebras` vazio), mais
   a serial e os dois portões de auditoria. Quebra achada se conserta neste goal.
2. **Reler o que os quatro goals entregaram**, com os olhos das convenções — em especial:
   - **G155/D181:** as folhas do prédio e da casa que passaram a declarar veredito reprovado.
     Convenção 6 (três aceites por folha) e 14 (folha de várias páginas confere as marcas
     entre páginas). **PNG olhado** de pelo menos uma folha reprovada por tipologia.
   - **G156/D182:** a BASELINE de citações — procurar **asserção tautológica** (convenção 5) e
     **medidor incapaz de disparar** (convenção 7, o padrão do G119).
   - **G154/D180:** a proveniência do material da fundação — conferir que o "declarado" não
     virou carimbo booleano que ninguém lê (padrão do G66).
   - **G157/D187:** a própria guarda — é ela que o G159 vai estender; medir onde ela é cega
     **antes** de mexer (o backlog já mediu uma cegueira; pode haver mais).
3. **Auditar a entrada fora do protocolo** (os quatro commits WKI) com a regra do lote inteira
   + convenções 13 e 17. O que a auditoria achar aqui **reescreve** os goals G159–G162 deste
   arquivo, com endereço.
4. **Verbete D188** com o que foi achado, e a correção deste backlog no **mesmo commit**.

**Aceite.** `rc_pytest` 0 e `quebras` vazio no runner; serial verde; os dois portões de
auditoria verdes; cada achado com arquivo:linha e, quando for folha, o PNG olhado; este
backlog corrigido onde a auditoria divergiu dele; verbete D188 + linha de fase.

**Não fazer.** Começar o G159 dentro desta corrida. Consertar defeito de folha inventando
número. Aceitar "verde" sem ler o resumo inteiro (convenção 10).

**Armadilhas.** Os quatro commits WKI entraram **depois** da última corrida completa conhecida
— uma quebra que aparecer pode ser deles, não dos goals; separe (rode em `cd319d4` antes de
culpar o lote, é a lição do D81). Um dos commits tem co-autor Cursor: código que não passou
pelo protocolo deste repo pode não seguir as convenções, e isso é achado, não ruído.

---

## G159 · O código de produção que entra sem deixar registro

**Prioridade: alta.**

**Estado de partida:** commit do G158 no `git log`, árvore limpa.

**Medido.**
- `tests/test_verbete_fase_g157.py` (D187) exige verbete com D e linha de fase para **todo goal
  fechado no `git log` desde o G149** — e acha os goals por **prefixo de commit `G1xx:`**
  (`:46` `GOAL_MINIMO = 149`, `:51` `GOAL_CORRENTE = "G157"`, `:58-66` o MAPA goal→D).
- Os quatro commits de 2026-09-19 (`dc686af`, `700afd8`, `6734fc8`, `a85bdbe`) não têm esse
  prefixo. Entregaram **600 linhas** de conta normativa viva na produção
  (`residencial_eletrica.py:313`) e um número que chega à folha
  (`desenho_eletrico_residencial.py:273`). Grep por `wki`/`enel`/`demanda_residencial` em
  `wiki/*.md`: **zero**. A guarda fica **verde** com isso na árvore — é a definição de
  instrumento que não consegue acusar (convenção 7).
- **Não medido:** quantos outros commits desde o G149 tocaram produção sem prefixo de goal (o
  censo é parte da entrega deste goal); se algum deles também entregou número ao cliente.

**Entregar.**
1. **Censo por arquivo, não por prefixo:** a guarda passa a listar os commits desde o G149 que
   tocaram **arquivo de produção** (a definição de "produção" já existe nas lentes G145/G150/
   G156 — reusar, nunca recopiar) e a exigir, para cada um, verbete com D **ou** isenção
   **declarada com motivo medido** (padrão G98: isenção com motivo, nunca renomear).
2. **Regularizar o que entrou:** um verbete com número D para o que os quatro commits WKI
   entregaram — o que a conta faz, de onde vem (F131), o que ela recusa, e **o erro de número
   que o `6734fc8` corrigiu** (2,584 → 2,28 kVA), porque erro entregue e corrigido é exatamente
   o que o registro existe para guardar. Linha em `wiki/03-phases.md`.
3. **Baseline nos dois sentidos:** commit que toca produção sem verbete nem isenção → vermelho
   nomeando `commit` e arquivo; isenção sem motivo → vermelho; verbete de commit inexistente →
   vermelho.

**Aceite.** Vermelho por injeção em `tmp_path` nos três sentidos; o censo lista os commits reais
desde o G149 e cada um está coberto (verbete ou isenção com motivo); a guarda do G157 continua
verde no que ela já cobria (nenhum teste de conteúdo mudou); verbete + linha de fase.

**Não fazer.** Reescrever os verbetes antigos; renumerar D existentes; mudar a produção do
módulo WKI (isso é G160/G161/G162); transformar a isenção em lista de nomes sem motivo.

**Armadilhas.** "Arquivo de produção" tem de sair de **uma fonte só** — se cada lente tiver a
sua definição, a próxima diverge (é o padrão do G131: a entrega declara um, a conta usa outro).
O `git log` do censo precisa parar num commit fixo (o do G149), não em "desde sempre", senão a
guarda fica vermelha por história antiga. E cuidado com a **tautologia do G91**: a guarda não
pode derivar a lista de commits do mesmo lugar onde grava a cobertura.

---

## G160 · A lente de citação que só enxerga NBR

**Prioridade: média-alta.**

**Estado de partida:** commit do G159 no `git log`, árvore limpa.

**Medido.**
- `tests/test_citacao_norma_g156.py:42`:
  `PAT_NBR = re.compile(r"NBR\s+(?:NM\s+)?\d{3,5}(?:[-:/]\d+)*(?::\d+)?", ...)`. A lente varre
  string e comentário dos `*.py` de produção, exige número com valor e **item** (`PAT_ITEM`,
  `:44`), e tem BASELINE triada com verdicto por frase (`CONFERE … p.N`, `REMISSAO …`,
  `FONTE_NAO_NBR …`).
- **Norma de distribuidora não casa `PAT_NBR`.** As 11+ citações do módulo WKI (`:74`, `:106`,
  `:146`, `:164`, `:380`, `:433`, `:450`, `:462`, `:474`, `:511`, `:523`) trazem item e página
  ("WKI Enel item 6.1, PDF p. 5"; "TABELAS 2 e 3 da WKI (PDF p. 14)"; "WKI 6.2.3.3"; "WKI notes
  1 and 2 (p. 7)") e **nenhuma está na BASELINE** — a lente nunca as viu.
- O acervo tem **10 normas ENEL** (F122–F131) e outras fontes não-NBR já usadas no projeto
  (IEC 60617 F148, ISO/CIE 8995-1 F102). A regra atual manda tudo isso para
  `FONTE_NAO_NBR` — **mas norma de distribuidora é fonte de conta**, diferente de livro e
  catálogo, que é o que a isenção original queria dizer.
- **Não medido:** quantas citações de fonte não-NBR existem hoje na produção fora do módulo
  WKI (o censo é entrega deste goal).

**Entregar.**
1. Estender a lente do G156 (a **mesma** lente, nunca uma cópia) para **fonte normativa de
   conta que não é NBR**: distribuidora (WKI/ENEL, por código de documento), IEC, ISO/CIE — com
   a regra escrita no teste, e a isenção de livro/catálogo/fabricante **mantida e dita**.
2. **Triar na imagem** cada frase nova que a lente pegar, começando pelas do módulo WKI, contra
   o **F131** (PDF digital: abra a página como **imagem**, não confie na extração de texto, que
   embaralha coluna). Tabela por frase: frase, arquivo:linha, item, página do arquivo, página
   da norma, confere/diverge/não conferível.
3. Divergência: corrige **a atribuição** (como o D179 e o D182), **nunca o número**, e a linha
   vai ao verbete como pendência ao usuário.

**Aceite.** Baseline nos dois sentidos (citação de fonte de conta sem item → vermelho com
arquivo:linha; entrada de baseline sem frase correspondente → vermelho); toda frase nova triada
com página **vista na imagem**; nenhum número de conta mudou (suíte com os mesmos resultados);
verbete + linha de fase.

**Não fazer.** Trocar número "para bater com a norma"; confiar na extração de texto do PDF;
citar de memória; mandar a WKI para `FONTE_NAO_NBR` (ela é fonte de conta — é o ponto do goal).

**Armadilhas.** O código do documento da distribuidora é longo
(`WKI-OMBR-MAT-18-0263-INBR-R01`) e aparece abreviado no código como "WKI" — o padrão tem de
pegar a abreviação **e** o código, senão vira **filtro de nome morto** (substring que nunca
casa → no-op silencioso). "PDF p. 14" e "p. 7" no mesmo módulo podem se referir a numerações
diferentes (página do arquivo vs página impressa da norma): a tabela tem de separar as duas, ou
a conferência seguinte procura no lugar errado.

---

## G161 · As 476 células transcritas que ninguém conferiu na imagem

**Prioridade: alta** (é a que pode estar entregando número errado agora).

**Estado de partida:** commit do G160 no `git log`, árvore limpa.

**Medido.**
- Contado em `demanda_residencial_enel.py` em 2026-09-21: **`_MOTOR_TABLE_KVA` 370 células**
  (370 linhas), **`_HEATING_TABLE` 90**, `ROOM_MODULES_KVA` 7, `LOCATION_FACTORS` 4,
  `_SPECIAL_LIGHTING_POWER_FACTORS` 4, `_MOTOR_TABLE_MAX_QUANTITY` 1,
  `_MOTOR_NO_PLATE_KW_PER_CV` 1. **Total ~476.** Os comentários dizem "complete source
  transcription" (`:74`, `:106`) — **transcrição**, não conferência.
- **Um erro já saiu daí e foi entregue:** `6734fc8` corrigiu motores de mesma potência somados
  como grupos separados — **2,584 kVA** onde a coluna de quantidade 2 imprime **2,28 kVA**. O
  defeito não era de célula, era de *leitura da tabela* (o item 6.2.3.2 consulta por quantidade
  consolidada); ambos os modos de erro vivem na mesma transcrição.
- **Não há aferição contra exemplo resolvido:** grep por `exemplo`/`anexo`/`worked` em
  `tests/branches/project_loop/test_residential_electrical_demand.py` → **zero**. Os verticais
  maduros deste repo têm (concreto: Bastos/Araújo/Carvalho; fundação: Alonso).
- O **F131 é PDF digital** (p.14 devolve texto extraível), então a página abre como imagem sem
  OCR — mas extração de texto de tabela **embaralha coluna**, e é por isso que a conferência é
  na imagem.
- **Não medido:** se a WKI traz exemplo resolvido (anexo/apêndice); se `_HEATING_TABLE` e
  `ROOM_MODULES_KVA` têm o mesmo modo de erro de *leitura* que os motores tinham.

**Entregar.**
1. **Conferir célula a célula, na imagem**, as tabelas que a produção lê — `_MOTOR_TABLE_KVA`
   (TABELAS 2 e 3, p.14) e `_HEATING_TABLE`, mais as 16 células soltas. Cada divergência achada
   é **achado**, com célula, valor do código, valor da página e a imagem conferida.
2. **A conferência fica registrada de forma que a próxima edição não a apague** (convenção 17):
   teste que confere a estrutura da transcrição contra o que foi visto — e que **consegue
   acusar** (convenção 7). Atenção à convenção 5: conferir o literal contra ele mesmo não mede
   nada; a prova tem de vir de fora do módulo.
3. **Aferição pelo exemplo resolvido da fonte**, se existir: fixture com o exemplo da WKI e o
   resultado batendo. Se não existir, declarar que não existe (não inventar exemplo) e aferir
   pelo modo de *leitura*: para cada tabela, um caso que exercita a consulta consolidada (o
   caminho do `6734fc8`) e um que exercita a recusa.
4. Divergência de célula: **não se troca o número em silêncio** — se o código diverge da
   página, o número da página é o certo (é transcrição, não adoção de projeto), mas a troca vai
   ao verbete com a imagem, e a linha vai à tabela de pendências do G163.

**Aceite.** Toda célula que a produção lê conferida na imagem, com o registro que a próxima
edição não apaga; vermelho por injeção (célula alterada em `tmp_path` → a guarda acusa a
célula); caso de consulta consolidada e caso de recusa por tabela; se houve divergência, o
número corrigido com a página ao lado e o verbete dizendo; suíte com `rc_pytest` 0.

**Não fazer.** Interpolar valor que a fonte não imprime (o módulo já recusa isso em `:462` e
`:523` — manter); "arredondar para bater"; conferir pela extração de texto; aceitar que a
tabela está certa porque os testes passam (os testes vieram da mesma transcrição — é o padrão
do **aço-classe-fonte-Pfeil**: o teste cristaliza o erro da fonte inventada).

**Armadilhas.** 370 células é muita página: faça o censo **por parte** (convenção 7 — o medidor
tem de acusar por parte), e registre o que foi conferido incrementalmente, para a interrupção
retomar (protocolo, item 5). A coluna de quantidade 1..10 da TABELA 2/3 é onde o erro do
`6734fc8` morava — comece por ela.

---

## G162 · A demanda que chega à folha como um número sem origem

**Prioridade: média.**

**Estado de partida:** commit do G161 no `git log`, árvore limpa.

**Medido.**
- `desenho_eletrico_residencial.py:273-276`: a folha imprime **uma linha** —
  `"demanda %s kVA" % _num(calculation.demand.final_kva)` — alinhada à direita sobre o barramento
  do QD. Não diz a fonte (WKI/F131), o item, o fator locacional, nem como a demanda foi composta.
- O `_num` (`:175-178`) **declara a ausência** (`A_CONFIRMAR` quando não é número) — isso está
  certo, não mexer.
- A folha **sabe reprovar**: `_reprovado(design)` por circuito (`:181`), "REPROVA" em `:308`,
  `:367`, `:412`, `:593`, e a fonte única do G152/G155 entra em `:630`
  (`injetar_veredito_no_svg`).
- **Não medido:** se a folha diz alguma coisa quando a **própria demanda** recusa — o módulo
  tem recusas nomeadas (motor bifásico `:450`, combinação sem linha exata `:462`/`:523`,
  quantidade acima de 10 `:511`, fator locacional fora da tabela `:241`) e
  `residencial_eletrica.py:313-330` estende os `errors`; falta medir se esses erros chegam ao
  veredito que a folha lê, ou se morrem no resultado. **Este é o primeiro passo do goal.**
- Também não medido: se `final_kva` ausente (recusa) faz a folha sair com `A_CONFIRMAR` e
  **sem** dizer por quê — que é o padrão **G106** (dado que some sem aviso).

**Entregar.**
1. Medir, por injeção, cada recusa do módulo até a folha: a folha diz que a demanda recusou, e
   **qual** recusa? Se não diz, passa a dizer, lendo do resultado pela **fonte única do G152**
   (estender, nunca copiar).
2. A linha da demanda declara **de onde veio** o número (fonte + item), pela mesma regra do
   G154 (declarado vs modelo) e do G131 (a entrega declara o que a conta usou).
3. Três aceites da folha (convenção 6): está certa, sai no manifesto, diz o que desenha —
   conferidos com **PNG olhado**.

**Aceite.** Vermelho por injeção para cada recusa do módulo (a folha declara); ATENDE
**byte-idêntica** (hash) quando nada recusa; PNG olhado da folha com demanda e da folha com
demanda recusada; `test_veredito_folha_g152` e `g155` verdes; G102 casa verde.

**Não fazer.** Parar de emitir a folha quando a demanda recusa; decidir gate na folha; mudar o
número da demanda; tocar o carimbo (já fechado no G151).

**Armadilhas.** `residencial_eletrica` chama `calculate_residential_demand` **duas vezes**
(`:313` e `:355`, a segunda só para os warnings) — mudança na composição do resultado tem de
valer para as duas, ou o warning diverge do cálculo (padrão G131). A folha é do vertical da
casa, que o `casa_residencial` compõe: injete a recusa **em cada porta de entrada que o produto
aceita** (convenção 11).

---

## G163 · A tabela de decisão: as sete pendências e os links sem verbete

**Prioridade: média-baixa.** É o goal cuja **entrega é a decisão do usuário**.

**Estado de partida:** commit do G162 no `git log`, árvore limpa.

**Medido.** `wiki/04-decisions.md`:
- **D182 (`:5517-5523`), seis pendências**, todas declaradas no código, nenhuma trava nada:
  (1) confirmar **1,4** ante o **1,30** da madeira (Tab.1) e o par **0,9/1,4** da tesoura/terças
  ante a Tab.1 (adotados, conservadores); (2) confirmar o item da **faixa 3,0–5,0 m** do
  incêndio (grupo 1 OK no Anexo A); (3) confirmar **θcrítica 550 / μ 0,6** ante a 14323 Tab.B.6;
  (4) confirmar **Rippl** ante a 15527 (pode ser ed. 2007); (5) confirmar **Wenner** ante
  7117-1/Negrisoli e o **10 Ω** ante a 5419-3:2026; (6) confirmar **ψ2 0,2/0,4/0,6** ante a
  14323 6.3.1 e os **10% da cinta** (6122/Alonso).
- **D187 (`:5597-5602`):** os links `[[04-decisions#D152]]`, `[[04-decisions#D153]]` e
  `[[04-decisions#D154]]` nos bullets do G126, G127 e G128 **não têm verbete** `## D152/D153/D154`
  — o lote G126–G130 registrou D152–D157 no índice mas os verbetes do G126–G128 não levaram
  esses números. Fora do escopo do G157 (que só ia do G149 para frente).
- **D179:** o **FS 3,0** da estaca — decisão **(a) manter adotado e declarado**, tomada em
  2026-09-17. Entra na tabela como **decidido**, para o registro; **nenhum goal deste arco muda
  o número ou a trava** do `projeto_spec.validar()`.
- **Do G160/G161:** as divergências que aquelas triagens acharem entram nesta mesma tabela.
- **Do bloco de fontes:** confirmar se a **WKI R01/2018** foi substituída por revisão posterior
  (o catálogo diz "listada em 2026", não "vigência conferida").

**Entregar.** Uma tabela única — **frase, arquivo:linha, norma, item, página do acervo,
o que o código usa, o que a página diz, confere/diverge/não conferível** — com **cada linha
conferida na imagem da página**, mais a recomendação conservadora ao lado. Os links
D152/D153/D154 entram como item próprio (ganham numeração nova ou os links caem). A tabela vai
ao verbete e ao usuário. **Nenhum número, veredito, default ou trava muda dentro deste goal.**

**Aceite.** Toda linha da tabela com a página **vista na imagem** ou marcada "não conferível"
**com o motivo**; nenhum número de conta mudou (suíte com os mesmos resultados); a tabela no
verbete + linha de fase; a pergunta ao usuário sai em uma lista fechada, item a item.

**Não fazer.** Decidir por conta própria qualquer uma das linhas; trocar número para bater com
a norma; reescrever verbete antigo; renumerar D existentes; abrir goal novo a partir da tabela
(a fila seguinte nasce da auditoria deste lote, não daqui).

**Armadilhas.** Várias das seis são **adotadas conservadoras** — "diverge da norma" aí não
significa "está errado", significa "está mais seguro e não estava dito"; a tabela tem de
separar as duas coisas, ou o usuário decide sobre a pergunta errada. A 5419-3:2026 e a 15527
podem estar no acervo em edição diferente da citada: conferir a **edição** antes da página (é o
padrão do G131 — a entrega declara um, a conta usa outro).
