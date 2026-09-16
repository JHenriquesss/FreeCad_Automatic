# Backlog de goals executáveis — pós-G148 / D176 (2026-09-15)

> **FILA CONSUMIDA** (2026-09-16): G149–G153 executados; auditoria em D179 (commit
> `6d94510`). A fila aberta é [BACKLOG-GOALS-G154-G157.md](BACKLOG-GOALS-G154-G157.md).
> **Correção (D179):** a "Atenção no G149" abaixo afirmava que o FS 3,0 da estaca é valor
> normativo da NBR 6122 — a página (NBR 6122:2022 p.18, 6.2.1.2.1) diz **2,0**; o 3,0 é o
> valor adotado no D38.

Fila **ABERTA**. Cinco goals (G149–G153) e uma decisão pendente do usuário. As filas anteriores
estão fechadas e ficam apenas como registro — não reexecute nada de lá: `BACKLOG-GOALS.md`
(G78–G88), `BACKLOG-GOALS-G91-G97.md`, `BACKLOG-GOALS-G99-G105.md`,
`BACKLOG-GOALS-G107-G112.md`, `BACKLOG-GOALS-G114-G118.md`, `BACKLOG-GOALS-G120-G124.md`,
`BACKLOG-GOALS-G126-G130.md`, `BACKLOG-GOALS-G132-G136.md`, `BACKLOG-GOALS-G137-G142.md` e
`BACKLOG-GOALS-G143-G148.md`.

Cada goal é **autocontido**: traz o que foi **medido** (com endereço), o que entregar, o
aceite e as armadilhas. Medido em 2026-09-15 na branch `feat/tipologias-e-verticais-de-projeto`
(commit `076a69f`), na auditoria do lote G143–G148 (D176). O que não foi medido está dito.

**Não fazer, em nenhum goal:** arbitrar valor normativo, inventar dado de projeto, ou
transformar ausência de dado em default silencioso. A ausência se **declara**.

**O norte:** construções inteiras confiáveis — o cliente informa o projeto e recebe cálculo,
3D e todas as folhas. O arco G143–G148 tirou o default calado da estaca **do galpão de
concreto** e os `or 0` dos emissores. A auditoria D176 mediu o que ficou do lado de fora dessas
duas cercas: **a mesma estaca calada em outras três portas** (galpão metálico, wizard, prédio),
**o mesmo fallback escrito como `.get(chave, 0)`** (64 nos emissores, invisível à lente do
G145), o **carimbo que corta o título** (23 folhas), a **folha de disciplina reprovada que não
diz que reprovou**, e o piso de memória que aborta a suíte por **uma amostra só**.

---

## Fontes do acervo (medido em `fontes/catalogo.csv`)

**Nenhuma norma ausente trava este arco.** As NBR citadas nas linhas novas do lote G143–G148
(13714, 6118, 6122, 8800) estão no catálogo; `tests/test_normas_catalogo.py` verde na regra do
lote da D176. Seguem as 4 sem entrada já triadas (nenhuma é fonte de conta):
- **NBR 5413** — substituída pela NBR ISO/CIE 8995-1:2013, no acervo (F102); lacuna congelada
  em `tests/test_normas_catalogo.LACUNAS_PRE_EXISTENTES`.
- **NBR 13438** — nome de material na tabela de pesos (`cargas_nbr6120.py:115`); mesma lacuna
  congelada (junto com a NBR 5444, simbologia, coberta pela IEC 60617 F148).
- **NBR 8522** e **NBR 8965** — remissões do texto da NBR 6118 transcrito nas lentes G116/G122;
  isentas em `REMISSOES_DA_NORMA_TRANSCRITA`.

**Atenção no G149:** o fator de segurança global da estaca (`estaca_profunda.FS_GLOBAL = 3.0`,
`:68`) é valor normativo (NBR 6122, no acervo). O goal **declara a origem** do número que o
código usa; **não** troca o número nem escolhe outro de memória.

**Bloqueado por DADO de projeto, não por norma (fora deste arco):** PE-IN-03 escada do galpão
(geometria não declarada; fronteira G101), PE-EL-03 da casa (malha e SPDA não declarados;
D171), PE-AR-01 implantação e PE-AR-03 cortes da casa (lote, recuos, cotas), fundação por laudo
SPT externo (T44).

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
    `…\VENV~1\Scripts\python.exe tools/suite_paralela.py -n 3` (~25 min; grava
    `resumo.json` — o goal só fecha com `rc_pytest` 0 **e** `quebras` vazio). O runner põe
    `PYTHONUTF8=1` (D172) e aborta abaixo de 200 MB livres terminando só a árvore do próprio
    filho (G148/D176). Não edite o repositório com a suíte rodando. Teste novo que sobe
    freecad.exe/freecadcmd.exe entra em `tests/censo_freecad.GRUPO_FREECAD` com o motivo medido.
    A serial `pytest tests` e os portões de auditoria (`GALPAO_AUDITORIA=1`: executivo de aço
    D165 e galpão do G102 D177) rodam **na auditoria do lote**, não em cada goal. Máquina de 8 GB: rodada pesada uma por vez; os
    aplicativos do usuário ficam abertos.
13. **(D172) Emissor ou conta reaproveitados trazem os fallbacks deles.** Rode com o dado
    **ausente** e com **zero**, um por um; folha nova ligada em código comum fica num `try`
    próprio; injete a falha **só na folha nova**.
14. **NOVO (D176) — a prova tem de exercitar o caminho que falha.** Kill/abort se prova com
    **processo real ocupado** (teste lento no worker) e a árvore de processos lida no instante
    do aborto — recorte rápido que termina antes não prova nada. Folha com várias páginas ou
    reaproveitada: confira as **marcas entre as páginas e contra o BIM**, olhando o PNG. E o
    **verbete** de cada goal entra no `04-decisions` antes do commit (G143–G145 fecharam sem).

**Regra do lote — a lista completa, por nome de arquivo.** Ao fim de cada goal, rode **estes**
antes da suíte: `varredura_faixa_validade.confere_cobertura()`,
`varredura_asserts_sequencia.confere()`, `varredura_constantes_orfas.confere()`,
`tests/test_folhas_g77.py`, `tests/test_alcancabilidade.py`, `tests/test_guardas_d86_g69.py`,
`tests/test_disciplina_prancha_g103.py`, `tests/test_indice_disco_g91.py`,
`tests/test_carimbo_mapa_g112.py`, `tests/test_normas_catalogo.py`,
`tests/test_galpao_indice_g93.py`, `tests/test_suite_paralela_d164.py`,
`tests/test_auditoria_g137_g142_d172.py`, `tests/test_auditoria_g143_g148_d176.py` e
`tests/test_fallback_folha_g145.py` — mais o portão próprio de cada fonte que o goal tocar.
Goal que muda folha do galpão roda também o portão do galpão do G102 **isolado e serial**
(`GALPAO_AUDITORIA=1 pytest -s tests/test_indice_disco_rodada_g102.py::test_10_portao_rodada_real_galpao_na_auditoria`,
~13 min; re-congela o custo com o número medido se ele mudar). Sem a variável ele sai pulado (D177).

**Otimização de conta (D158):** só com prova de número idêntico. **O verbete é parte da
entrega.** **Uma fonte só:** dado que o cliente recebe mora na produção.

---

## Ordem e dependência

- **G149** primeiro: é o único que pode mudar **veredito** (o G143 mediu que o tipo de estaca
  inverte ATENDE/REPROVA no concreto; nas outras portas o mesmo default segue calado).
- **G150** antes de **G152**: a folha reprovada vai passar por emissores cujos `.get(…, 0)` a
  lente ainda não triou.
- **G151** independente (carimbo; mexe em título, não em conta).
- **G153** independente (runner); roda por último se a máquina estiver em uso.
- **Decidido (D177):** a parte 2 do G148 foi aprovada pelo usuário — o galpão do G102 roda só na
  auditoria do lote (`test_10`). O `test_01` caiu de 838,8 s para 31,8 s, mas o ganho de parede
  **não se demonstrou** na corrida do D177 (máquina carregada): o G153 mede.

---

# GOALS

## G149 · A estaca calada nas outras três portas (galpão metálico, wizard, prédio)

**Prioridade: alta.**

**Medido.**
- **Galpão metálico** — `rodar_galpao.py:845-850`, com `params["estaca"]` presente:
  `ecfg.setdefault("D", 0.30); ecfg.setdefault("L", 10.0)` e
  `ecfg.setdefault("bloco", {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3})` — diâmetro,
  comprimento, pilar do bloco, **fck 25 MPa** e aço do bloco sem declaração no resultado
  (`res["estaca"]`, `:864-870`, não diz a origem). Não medido: se muda veredito.
- **Wizard** — `wizard.py:318-323` monta `fundacao.estaca` com `r.get("est_tipo",
  "pre_moldada")`, `r.get("est_D", 0.30)`, `r.get("est_L", 10.0)`, `r.get("est_FS", 3.0)`. Sem
  SPT o `validar()` bloqueia (`:314-317`); com SPT os quatro entram calados.
- **Prédio** — `fundacao_edificio.py:403` `estaca_cfg.get("D_m", 0.30)` e `:666` idem, **sem
  aviso**; `:405` e `:678` `tipo_estaca` "pre_moldada" **sem aviso**; o L tem aviso quando
  ausente (`:959-964`, `comprimento_de_estaca_lido_da_sondagem`).
- **Núcleo** — `estaca_profunda.verifica_estaca` (`:485-493`): `cfg.get("tipo_estaca",
  "pre_moldada")` nas três capacidades e `cfg.get("FS", FS_GLOBAL)` (`FS_GLOBAL = 3.0`, `:68`).
- O G143 (D176, resumo) mediu no concreto: pre_moldada→escavada muda util 0,116→0,198 e, no
  perfil fraco, **inverte o veredito**. A fonte única da recusa/declaração já existe:
  `estaca_parametros_g143.py`.
- Specs do repo: os 3 `projects/*/project-spec.json` têm `"estaca": null` (nenhum depende hoje).

**Entregar.**
1. Por porta (convenção 11: spec do metálico, wizard, spec do prédio, núcleo chamado direto),
   medir por injeção se D, L, tipo, bloco (a_pilar/fck/fyk) e FS mudam capacidade, n de estacas
   ou veredito — tabela no verbete, número antes e depois.
2. Declara-ou-recusa (D102), por item, com motivo escrito, lendo da fonte única (estender
   `estaca_parametros_g143` ou equivalente — nunca uma cópia por módulo). O `fck` do bloco
   calado em 25 MPa: medir de onde o metálico deveria ler (material declarado do projeto) antes
   de decidir; nunca inventar o valor.
3. FS: declarar a origem do 3,0 no resultado e no memorial; **não** trocar o número.

**Aceite.** Vermelho por injeção em cada porta (ausente → recusa ou declaração que chega ao
resultado, memorial e folha; declarado → o número do spec); casa byte-idêntica; o
`test_estaca_g143` segue verde; os três aceites da folha de fundação do prédio com estaca,
olhando o PNG.

**Não fazer.** Escolher D, L, tipo, fck ou FS "melhores"; mudar Aoki-Velloso/Décourt/Teixeira;
recusar o caminho que já declara (o L do prédio com aviso).

**Armadilhas.** O wizard grava o default no spec antes da conta — a origem se perde ali, não na
conta (injete no wizard, não só no `rodar`). `setdefault` no dict copiado (`dict(params
["estaca"])`) não aparece no spec de entrada: confira o resultado, não o spec.

---

## G150 · O `or 0` que a lente não vê: `.get(chave, 0)` nos emissores

**Prioridade: média-alta.**

**Medido.**
- A lente do G145 (`varredura_fallback_folha.py:96-115`) só acha `BoolOp Or` com constante
  0/1. O mesmo fallback escrito como `.get(chave, 0|0.0|1|1.0)` não entra. AST nos 10 emissores
  do G145 + `techdraw_mezanino`, `techdraw_incendio`, `techdraw_concreto`: **64**
  ocorrências — `desenho_pavimento` 24, `desenho_casa_residencial` 16,
  `desenho_fundacao_edificio` 8, `desenho_alvenaria` 8, `desenho_escada_edificio` 3,
  `desenho_eletrico` 2, `techdraw_concreto` 2, `desenho_hidraulica` 1.
- Exemplos no caminho do mezanino (G146): `desenho_pavimento.py:361-366`
  (`tramo.get("M_d_kNm", 0)`, `As_inf_cm2`, `As_sup_cm2`…), `:569` e `:659-661`
  (`lance.get("As_cm2", 0)`, `Nd`, `taxa_pct`); fora de 0/1 no adaptador novo:
  `rp.get("hy", mz.get("hy", 0.0))` e `techdraw_mezanino.config_de_spec`
  `mz.get("fyk", 500e3)` — **mortos hoje** (a D176 mediu `fyk`, `hx`, `hy` presentes no
  resultado do mezanino), mas sem baseline que acuse quando o produtor mudar.
- Não medido: quantos são vivos.

**Entregar.**
1. Estender a lente (uma fonte só, a do G145) para `Call .get(chave, constante)` com constante
   numérica, com a mesma chave estável e a triagem MORTO/VIVO contra o produtor; os dois do
   adaptador do mezanino entram na triagem pelo nome.
2. Baseline nos dois sentidos com vermelho por injeção; cada VIVO declara a ausência na folha
   com teste ausente/zero/presente, um por um (convenção 13).

**Aceite.** `confere()` OK com os 64 (+ os do adaptador) triados; injeção de um `.get(…, 0)`
novo reprova nomeando arquivo/função; prédio e casa byte-idênticos onde nenhum vivo foi curado;
PNG olhado em cada folha curada.

**Não fazer.** Apagar default "morto" sem prova do produtor; transformar a lente num grep.

---

## G151 · O título que o carimbo corta em 26 caracteres

**Prioridade: média.**

**Medido.**
- `techdraw_exec._cap_titulo(t, maxlen=26)` (`:527-541`) encurta e, no limite, corta com "…".
  AST de toda chamada `_carimbo*` com título literal: **23 cortados** —
  `techdraw_exec` 6 (4 viram abreviação limpa: "BASE DE COLUNA", "LIGACAO JOELHO",
  "FECHAMENTO / TERCAS", "BLOCO DE COROAMENTO"; 2 cortam: "CROQUIS DE FABRICACAO (pe…",
  "PLANO DE MONTAGEM E ESCOR…"), `techdraw_eletrico` 3, `techdraw_hidraulica` 2,
  `techdraw_climatizacao` 2, `techdraw_incendio` 2 (+1 em `galpao_seguranca_incendio:203`),
  `techdraw_concreto` 1 (+1 em `galpao_concreto:781`), `techdraw_coordenacao` 1. A MZ01 foi
  curada na D176 (`TITULO_CARIMBO_MZ01`, 25).
- Na rota SVG pura o rodapé (`prancha_svg_direta._linhas_carimbo`, `:92-105`) imprime o
  título já cortado; o "…" sai como "-" na fonte helv (visto no PNG da MZ01).
- `sheet_number` fora da contagem de páginas: a MZ01 tem 3 páginas e carimba "01/01" nas três
  (medido na D176); não medido nas outras folhas multipágina.

**Entregar.** Lente AST (todo título de carimbo passa por `_cap_titulo` sem reticência; a
abreviação limpa é declarada numa tabela com motivo), títulos corrigidos sem mudar
`drawing_number`, e `sheet_number` coerente com as páginas de cada PDF. Baseline nos dois
sentidos; PNG olhado de cada folha tocada.

**Aceite.** Nenhum título com "…"; injeção de título longo reprova nomeando arquivo:linha;
`test_carimbo_mapa_g112` e `test_galpao_indice_g93` verdes; portão do galpão do G102 (`test_10`,
`GALPAO_AUDITORIA=1`) se folha do galpão mudar.

**Não fazer.** Aumentar a célula do template ISO 5457 às cegas (o `_cap_titulo` existe porque o
título invadia "Created by"); mudar código de prancha.

---

## G152 · A folha de disciplina reprovada que não diz que reprovou

**Prioridade: média.**

**Medido.**
- `grep REPROVAD|NAO ATENDE` em `techdraw_*.py` e `prancha_svg_direta.py`: **0**. O carimbo
  genérico sai com `document_status` "PARA APROVACAO" (`techdraw_exec.py:637`) qualquer que
  seja o veredito.
- O veredito existe e é declarado **fora** da folha: capa do caderno "REPROVA -> …"
  (`caderno_turnkey.py:217,237`); o adaptador passa `native_atende`/`reprovados`
  (`galpao_adapter.py:679,820`).
- MZ01 com mezanino reprovado (`q_uso=60`, `reprovados` viga_X/viga_Y/vigas): a página de
  armação marca REPROVA por viga; as páginas de formas e do quadro não dizem nada (PNG visto
  na D176).
- Não medido: as folhas das outras disciplinas com o veredito reprovado injetado.

**Entregar.** Medir, disciplina por disciplina, o que cada folha diz com a disciplina reprovada
(injeção no resultado, sem mudar a conta); a folha de disciplina reprovada declara o veredito
no carimbo e na própria folha, nomeando os gates reprovados — texto, nunca omissão. Uma fonte
só: o veredito lido do resultado.

**Aceite.** Vermelho por injeção em cada disciplina com folha; ATENDE → folha byte-idêntica;
PNG olhado; `test_carimbo_mapa_g112` verde.

**Não fazer.** Parar de emitir a folha reprovada (o engenheiro precisa dela para revisar);
decidir gate.

---

## G153 · O piso que aborta a suíte por uma amostra

**Prioridade: média.**

**Medido.**
- `tools/suite_paralela.py` (G148/D176) aborta na **primeira** amostra abaixo de 200 MB
  (`main`, laço do `Popen`). O G142 **passou** com mínimo de 159 MB; com o piso de hoje teria
  sido abortado. O resumo guarda só o mínimo, não a série — não há como saber se 159 foi um
  pico de 1 s ou minutos.
- Depois do aborto, a D176 termina a árvore do filho; não medido quanto tempo leva para a
  memória voltar com um freecad.exe (1,5–2 GB) ocupado.
- **D177:** com o galpão do G102 fora da suíte do goal, o `test_01` caiu de 838,8 s para 31,8 s,
  mas a corrida levou 1664,6 s contra 1574,4 s do D176. Os testes do FreeCAD intocados ficaram
  1,4–2,3× mais lentos e o Cursor do usuário somava ~3,3 mil s de CPU: a comparação não isola o
  diff. O resumo não grava a carga da máquina.

**Entregar.** Gravar a série de amostras no resumo; medir em duas corridas reais (máquina em
uso normal) a duração das quedas abaixo do piso; decidir a regra de confirmação **só com os
números**, com vermelho por injeção nos dois sentidos (queda transitória não aborta; queda
sustentada aborta e mata a árvore). Medir o tempo até a memória voltar com freecad ocupado,
sem fechar aplicativo do usuário. Gravar a carga da máquina no resumo e medir o ganho de parede
do D177 contra o D176 em corrida comparável (os testes intocados servem de régua da carga).

**Aceite.** Resumo com a série; regra escrita com a derivação; teste com amostrador falso para
transitório e sustentado; suíte pelo runner `rc_pytest` 0 e `quebras` vazio.

**Não fazer.** Baixar o piso para "caber"; mover mais cobertura para a auditoria sem decisão do
usuário (o D177 moveu só o galpão do G102).
