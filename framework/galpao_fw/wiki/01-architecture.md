# 01 — Arquitetura

## Princípios
- **ProjetoSpec = fonte única da verdade** (`projeto_spec.py`). `validar()` bloqueia calc/model até todos os gates respondidos. Builder lê só do spec (sem cópia hardcoded).
- **Calcula apenas; CONCEITUAL** — pendente revisão + ART do eng. responsável. Nada é executivo.
- **Ask, Do Not Invent**: σ_solo,adm, μ, coesão, fck, fyk, φ (impacto ponte), frações laterais/long — INPUT do caso; a skill pergunta. Defaults entram flagados.
- **Método extraído das normas** (`pesquisa/aço/*.pdf`), não de memória. Cada módulo cita item da NBR.

## Cadeia de cálculo (por candidato de perfil)
1. `galpao_portico` — pórtico 2D, flecha lateral no beiral (ELS).
2. `estabilidade_b1b2` — 2ª ordem **MAES** (rigidez 0,8 + forças nocionais) → Nsd/Msd/Vsd amplificados. Permite **K=1** (NBR 8800 4.9.6.2).
3. `check_nbr8800` — verificação por peça, K=1, todas as combinações → pior interação (flexo-compressão 5.5.1.2, split 0,2; FLT Anexo G).
4. `redimensionamento` — first-fit: par (coluna,viga) mais leve que passa ELU (interação≤1) **E** ELS (flecha ≤ **H/300**, Tab. C.1). Ver [[04-decisions#D5]].

## Envelope de combinações (por elemento)
`rodar_galpao._casos_base_envelope()` lê a reação do nó de base **direto do solve de 2ª ordem** (`R[3·nBaseL+{0,1,2}]` = V,N,M) por combinação ELU. Alimenta:
- **fundação** `fundacao_sapata.dimensiona_sapata_env` — menor geometria que passa TODAS as combos (bearing=N máx, tombamento=N mín+M).
- **base** `base_chumbador` — placa + chumbadores, caso "Base engastada — M=…".
Mesmo `R` para redim/fundação/base → consistência; M do engaste não é recalculado.

## Módulos
| Grupo | Módulos | Norma |
|---|---|---|
| Análise | `galpao_portico`, `estabilidade_b1b2`, `frame2d` (solver genérico), **`diafragma`** (rigidez de cobertura) | NBR 8800 An. D, NBR 15421 §8.3.2 |
| Verificação | `check_nbr8800`, `perfis` (tabela), **`torcao_nbr8800`**, **`empocamento_nbr8800`** | NBR 8800 §5.5.2 / §9.3 |
| Ações | `vento_nbr6123` (+§8 Cpe local borda/canto + atrito §6.4), `ponte_rolante`, `sismo_nbr15421` | NBR 6123, 8800/8400, **15421** |
| Secundários | `tercas_iteracao` (+distorcional FSM), `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, **`telha_cobertura`**, **`escada`** (patamares Blondel) | NBR 14762, 8800, NBR 9050 |
| Ligações/base | `ligacoes` (joelho/parafusos + furos/Tab.14/block shear/T-stub), `base_chumbador` | NBR 8800 + AISC DG1 + ACI 318 + EN 1993-1-8 |
| Fundação | `fundacao_sapata` (rasa), `sapata_divisa` (divisa rasa), **`viga_equilibrio`** (divisa sobre estacas), **`viga_baldrame`** (amarração), **`estaca_profunda`** (profunda) | NBR 6118, 6122 + Aoki/Décourt/Teixeira |
| Montagem/Obra | **`montagem`** (sequência 10 passos, guindaste, estai, prumo H/500) | NBR 8800 §12.3 + AISC 303 + Bellei 7.6.4 |
| Fabricação 3D/2D | **`marcas_peca`** (takeoff/corte 3D), **`tolerancias_fabricacao`** (tabela 2D Q09T) | NBR 8800 §12.2/12.3 + Bellei Ap. C |
| Verif. flexão avançada | **`props_I_mono`** (perfil I monossimétrico), **`dg25_ltb`** (DG25 FLT + envelope), **`forcas_localizadas`** (NBR 8800 §5.7), **`console_ponte`** (FLT Anexo G Tab G.1) | AISC DG25 + NBR 8800 Anexo G / §5.7 |
| Fogo (aço) | **`fogo_nbr14323`** (θ_aço/θ_crítica, ISO 834, proteção intumescente/spray) | NBR 14323 |
| Interoperabilidade BIM | **`modelo_neutro`**, **`ifc_emit`**, **`ifc_map`** + analítico via `galpao_portico.modelo_analitico()` e `ifc_emit.emitir_ifc_analitico` (não é módulo próprio) | IFC4 Physical (ISO 16739-1) / IFC4 Structural |
| Auto-sizing | `redimensionamento` | usa check |
| Orquestração | `rodar_galpao`, `rodar_projeto`, `framework`, `projeto_spec`, **`romaneio`**, `acos` | — |
| Geometria/saída | `build_galpao`, `terreno` (KML), `techdraw_exec` (pranchas A1 — ver executivo) | — |
| Verticais — concreto | **`galpao_concreto`** (orquestrador), `pilar_concreto`, `viga_concreto`, `viga_protendida`, `perdas_protensao_nbr6118`, `premoldado_nbr9062`, `fogo_nbr15200`, `fissuracao_nbr6118`, `estabilidade_global_nbr6118`, `torcao_nbr6118`, `geotecnia_spt`, `piso_industrial` | NBR 6118/9062/6122; combinações NBR 8681 |
| Verticais — elétrico | **`galpao_eletrico`** (orquestrador), `cargas_eletricas`, `condutores_nbr5410`, `curto_circuito`, `protecao_nbr5410`, `fator_potencia`, `subestacao_nbr14039`, `aterramento_nbr15749`, `spda_nbr5419`, `luminotecnica_nbr8995`, `iluminacao_externa_nbr5101`, `instalacao_eletrica`, `fotovoltaico` | NBR 5410/14039/5419/8995/5101/15749; Mamede |
| Verticais — incêndio/AVCB | **`galpao_seguranca_incendio`** (orquestrador), `iluminacao_emergencia_nbr10898`, `sinalizacao_nbr16820`, `deteccao_alarme_nbr17240`, `proteccao_sprinklers_nbr10897`, `hidrantes_nbr13714` | NBR 10898/16820/17240/10897/13714 |
| Verticais — hidráulica | **`galpao_hidraulica`** (orquestrador), `hidraulica_predial`, `esgoto_reuso` | NBR 5626:2020/8160/10844 (+7229/15527) |
| Verticais — climatização | **`galpao_climatizacao`** (orquestrador), `climatizacao_nbr16401` | NBR 16401-1/2/3 |
| Turnkey | **`galpao_turnkey`** (orquestrador-mestre), `caderno_turnkey` (caderno único PDF), `caderno_encargos`, `compatibilizacao` (BCF-like), `pacote_legal`, `orcamento`, `cronograma`, `terraplenagem` | despacha os verticais; BCF (coordenação) |
| BIM federado / build 3D | `build_federado` (disciplinas num doc + interferência OCCT), `build_concreto`, `build_eletrico`, `desenho_coordenacao` (SVG), `techdraw_coordenacao` (A1) | IFC4 (ISO 16739-1) + clash AABB |
| Executivo dos verticais | `techdraw_concreto`, `techdraw_eletrico`, `techdraw_incendio`, `techdraw_hidraulica`, `techdraw_climatizacao` (A1 TechDraw), `desenho_concreto`, `desenho_eletrico`, `desenho_incendio`, `desenho_hidraulica`, `desenho_climatizacao`, `desenho_piso` (SVG puro-Python), `executivo_concreto` (quadro de aço) | ISO 5457 (pranchas A1); NBR 6118 §9.4 |


**Sismo no envelope:** `galpao_portico`/`estabilidade_b1b2` têm caso `SISMO` (global `gp.SISMO`, `case_sismo` no beiral) + combos excepcionais C6 (1,2G±E / 1,0G±E, sem vento/Q, NBR 15421 §5.4) — entram no envelope do pórtico, base e joelho. `rodar_galpao` computa `E = H·(vão/comprimento)` e θ/P-Δ. Zona 0 (default) → E=0 → nada muda.

**Gate de divisa (`rodar_galpao`):** com `params["divisa"]`, ramifica — se há
`params["estaca"]`+`res["estaca"]` → `viga_equilibrio` (variante PROFUNDA, usa a `P_adm`
da estaca já calculada); senão → `sapata_divisa` (rasa). `res["divisa"]["tipo"]` ∈
{estaca, sapata}. Aliases `est_res`/`veq` p/ evitar shadowing.

**Fundação profunda/baldrame:** opt-in via `params["estaca"]` / `params["baldrame"]`. `estaca_profunda` = 3 métodos de capacidade (Aoki-Velloso/Décourt-Quaresma/Teixeira) + tração/grupo/atrito negativo/recalque + bloco de coroamento (bielas-tirantes+ancoragem+punção). N_pilar/N_uplift do envelope de base.

## Quadro de verificações (pass/fail consolidado)
`rodar_galpao` monta o **QUADRO DE VERIFICAÇÕES** no topo do MEMORIAL-CONSOLIDADO: uma
linha por elemento (`util = solicitação/resistência ≤ 1,0`) + alerta se algo não atende.
Único ponto de verdade pass/fail. Regras (pós-auditoria [[04-decisions#D49]]):
- Toda verificação com pass/fail calculado entra no quadro: coluna/viga/tesoura, base,
  sapata, joelho, zona de painel, terça, telha, secundários, contravento/gusset, viga de
  rolamento, console, fogo, estaca/travamento/baldrame, sismo θ, junta, calha, divisa,
  terreno, escada, plataforma.
- Helpers `_uok(util,ok)`/`_uokd(dict)` forçam `util>1` quando a flag de OK reprova mesmo
  com `util≤1` (base sob interação T-V, sapata sob punção, viga-rolamento sob fadiga/
  flecha). Elemento não rodado → linha ausente (não conta como falha).
- `fogo_nbr14323` reporta `θ_aço/θ_crítica` (não °C absoluto). `rodar_projeto` exporta o mesmo
  conjunto (`resultados`+`estados`) para a tabela das pranchas TechDraw.

## Auditoria geométrica
`verifica_conexoes` mede as formas reais no modelo 3D (assentamento medido `_assenta`) → auto-captura defeitos de conexão/geometria. Sapata desenhada (bloco+pedestal) no take-off com densidade própria (concreto categoria separada, não soma na tonelagem de aço).

## Projeto executivo (2D) — split calc/model/executivo
Pipeline: **calc** (`rodar_projeto.calcular`, python) → **3D** (`build_galpao`, freecadcmd ou MCP) → **executivo** (`rodar_projeto.rodar_executivo` lança `freecad.exe` c/ `techdraw_exec`). `build_final.py` encadeia + gera memorial PDF (`relatorio_calculo`). Detalhes D33–D36.
- **`techdraw_exec`** roda DENTRO do freecad.exe (config gerada FORA por `config_de_spec`, injetada via `script_bootstrap`). `construtores` = lista de builders `_pr_*`; detalhes (`_pr_base/_joelho/_contravent/_ligacoes`) recebem `todos` (inclui miudezas); gerais recebem `objs` (sem `_MIUDEZAS`).
- **Padrão de detalhe:** crop `Part.makeBox`+`Shape.common` → compound `<PREFIXO>_CROP` → `_vista` HLR. Eixo de vista curado (`_AXES`), não heurística.
- **Guard de cobertura** `_cobertura`: toda peça (tipo, normalizado por lado) desenhada em ≥1 prancha; `PREFIXOS_SEM_DESENHO`=("VAO",). Guard anti-silhueta `_n_edges`≥15. `smoke_executivo` sela 4 geometrias.

## Verticais multidisciplina

Fora da cadeia do aço, o framework cobre 5 disciplinas. Cada vertical segue o **mesmo
padrão stateless** (confirmado por grep nos 5 orquestradores): `rodar(spec)` →
`membros_bim(r)` → `emitir_bim(r, path)` → `montar_pranchas(r, out_dir, …)` + `_selftest()`.
Sem estado global — entrada é o spec, saída é um dict `r` (vereditos/gates).

- **Concreto pré-moldado** (`galpao_concreto.rodar`, pilar engastado + viga de cobertura +
  sapata): `pilar_concreto` (flexão composta reta/oblíqua), `viga_concreto`,
  `viga_protendida` (pré-tração), `perdas_protensao_nbr6118`, `premoldado_nbr9062`
  (cálice/içamento), `fogo_nbr15200` (tabular), `fissuracao_nbr6118` (ELS-W),
  `estabilidade_global_nbr6118` (α/γz), `torcao_nbr6118`, `geotecnia_spt` (SPT→σ_adm),
  `piso_industrial` (placa sobre solo). Normas: NBR 6118/9062/6122; combinações NBR 8681.
- **Elétrico BT** (`galpao_eletrico.rodar`): `cargas_eletricas` (demanda),
  `condutores_nbr5410` (3 critérios), `curto_circuito`, `protecao_nbr5410`,
  `fator_potencia` (FP≥0,92), `subestacao_nbr14039` (MT), `aterramento_nbr15749`,
  `spda_nbr5419`, `luminotecnica_nbr8995`, `iluminacao_externa_nbr5101`,
  `instalacao_eletrica` (circuitos separados), `fotovoltaico` (on-grid). Normas:
  NBR 5410/14039/5419/8995/5101/15749; Mamede.
- **Incêndio/AVCB** (`galpao_seguranca_incendio.rodar`): `iluminacao_emergencia_nbr10898`,
  `sinalizacao_nbr16820`, `deteccao_alarme_nbr17240`, `proteccao_sprinklers_nbr10897`,
  `hidrantes_nbr13714`. Normas: NBR 10898/16820/17240/10897/13714.
- **Hidráulica predial** (`galpao_hidraulica.rodar`): dimensiona (NBR 5626:2020/8160/10844)
  e roteia pluvial/esgoto/água fria no federado, participando do clash. Sub-módulos:
  `hidraulica_predial`, `esgoto_reuso` (fossa NBR 7229 + reuso Rippl); `calhas` (tabela
  acima) pertence à envoltória do aço.
- **Climatização (HVAC)** (`galpao_climatizacao.rodar`): `climatizacao_nbr16401` (carga
  térmica, renovação, capacidade em TR/kW). Norma: NBR 16401-1/2/3.

## Turnkey federado

`galpao_turnkey.rodar(spec)` (galpao_turnkey.py:138) é o **orquestrador-mestre**: despacha
as disciplinas de `DISCIPLINAS` (galpao_turnkey.py:40 = concreto, aço, elétrico, incêndio,
climatização, hidráulica) e consolida gates + ATENDE:

- **Isolamento de falha por disciplina:** cada vertical roda em bloco próprio; falha numa
  disciplina → `{"rodou": False, "ATENDE": False, "reprovados": ["ERRO"]}` sem abortar as
  demais. `R["ATENDE"] = len(executadas) > 0 and len(reprovados) == 0` (global).
- **BIM federado:** `emitir_bim(R, …)` gera o IFC por disciplina + `turnkey_federado.ifc`
  (frame comum); `montar_3d_federado` monta o 3D sólido; `checa_interferencia_federada`
  roda o clash AABB com triagem esperado×revisar (`_clash_esperado`) — o clash NÃO entra
  no ATENDE do rodar (coordenação, não bloqueio).
- **Caderno executivo único:** `caderno_turnkey.montar_caderno(spec, out_dir, …)` agrega
  capa + índice + prancha de coordenação (render do federado + apêndice de clash) +
  pranchas A1 de TODAS as disciplinas num único PDF (mescla PyMuPDF/fitz via
  `montar_caderno_de_pdfs`, camada pura testável).
- **Apoio turnkey (STATELESS):** `caderno_encargos` (especificações por disciplina),
  `pacote_legal` (ART, PPCI/AVCB, LOD-BIM, O&M), `orcamento` (5D), `cronograma` (CPM +
  curva S), `terraplenagem` (corte/aterro + greide).

## BIM federado

- **IFC federado:** `galpao_turnkey.emitir_bim` emite o IFC de cada disciplina + o
  `turnkey_federado.ifc` consolidado (disciplinas num frame comum, IFC4 ISO 16739-1).
- **Clash AABB:** `checa_interferencia_federada(R, spec, folga, vol_min)` compara caixas
  envolventes entre disciplinas e classifica esperado×revisar; interferência intencional
  não vira pendência.
- **3D sólido federado:** `build_federado.run()` monta as disciplinas num ÚNICO documento
  FreeCAD e roda a interferência REAL (OCCT) entre disciplinas (`_interferencias_cross`);
  fechamento/telha (`_TIPOS_IGNORADOS` = Covering/Cladding) fica fora do clash.
- **Coordenação:** `desenho_coordenacao` (SVG: planta+elevação das disciplinas coloridas +
  clash a revisar) e `techdraw_coordenacao` (prancha A1) — wired no turnkey.
- **Compatibilização:** `compatibilizacao.gerar_pendencias(rep_clash)` transforma o clash
  em pendências rastreáveis BCF-like (ID CLH-NNN, severidade, status, ação, responsável) +
  `matriz_coordenacao` + `bcf_topics`.

## Executivo dos verticais (pranchas A1)

Mesmo padrão do executivo do aço (config gerada fora por `config_de_spec`, `script_bootstrap`
injetado no freecad.exe headless): cada vertical desenha via `montar_pranchas(r, out_dir, …)`
+ geradores `techdraw_*`:

- `techdraw_concreto`, `techdraw_eletrico`, `techdraw_incendio`, `techdraw_hidraulica`,
  `techdraw_climatizacao`, `techdraw_coordenacao` — pranchas A1 TechDraw (ISO 5457), a
  partir do 3D salvo (build_* → .FCStd).
- `desenho_*` — desenhos SVG puro-Python (sem FreeCAD): `desenho_concreto` (formas +
  armação), `desenho_eletrico` (unifilar + quadro de cargas + planta iluminação/tomadas),
  `desenho_incendio` (planta de segurança/AVCB), `desenho_hidraulica`, `desenho_climatizacao`,
  `desenho_coordenacao` (federado + clash), `desenho_piso` (juntas do piso).
- `executivo_concreto` — quadro de aço (lista de dobramento) + memorial (NBR 6118 §9.4).

## Convenções
- Convenção do modelo: **comprimento em X, vão em Y, altura em Z** (build_galpao; `comp_x=True` fixo no executivo).
- `L` // eixo do momento do pórtico. Momento no plano do pórtico → dimensão L.
- γa1=1,10, γa2=1,35, γw2=1,35 (aço); γc=γn=1,40 (concreto).
- `_vg` (relatorio_calculo) troca ponto decimal por vírgula nos memoriais (preserva nº de item tipo 6.118).
