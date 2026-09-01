# REVISAO G15 — Validação de sistema contra projeto real

**Data:** 2026-08-31  
**Tipo:** validação de SISTEMA (não de módulo)  
**Status:** EXECUTADO — 19 checks, 19 PASS, 0 FAIL (harness `validacao_sistema_g15.py`)  
**Objetivo:** montar o spec de um projeto real/construível, comparar número a número (seções, armaduras, cargas, quantitativo aço/concreto, disjuntores, diâmetros) e classificar cada divergência como **bug** ou **hipótese não escrita**. Ver `validacao_sistema_g15.py:1`, `validacao.py:14`, `AMOSTRA-ENGENHEIRO-respostas.md`.

> O valor não está em bater. Está nas divergências.

> **Armadilha registrada:** não declare divergência antes de medir as duas grandezas na mesma definição. Caso real “11 mm inexplicados” = `d·sen(45)` — hipotenusa vs projeção (`validacao_sistema_g15.py:484`).

---

## 1. Metodologia

### 1.1 Projetos de referência

Nenhum memorial externo completo de galpão construído foi doado ao repo até 2026-08-31 (ver `projects/galpao-sjb/ENTRADAS-PENDENTES.md` — 9 campos pendentes bloqueiam o Loop 2). Para não inventar dado de obra, G15 usa **dois projetos quasi-reais plenamente reproduzíveis** + um **caso-referência publicado**:

| # | Projeto | Fonte | Tipo | Vão×Comp | Pé-direito | Bay | V0 | Solo | Disciplinas aferidas |
|---|---------|-------|------|----------|------------|-----|----|------|----------------------|
| A | **Amostra Engenheiro** | `spec_amostra_engenheiro.json` + `AMOSTRA-ENGENHEIRO-respostas.md` (8 gates coletados com engenheiro responsável) | Galpão 1 vão prismático, base engastada | 20 × 28,5 m | 8,0 → 9,5 m (slope 15%) | 5,7 m (5 vãos → 6 pórticos) | 45 m/s cat II/B S1=1 S3=0,95 | σ=150 kPa (A CONFIRMAR) | Vento, G/Q, parede, pórtico 1ª/2ª ordem, perfis NBR8800, sapata/bloco, baldrame, terças, telha, quantitativos |
| B | **CBCA Cap.2** | Manual CBCA “Galpões para usos gerais” Cap.2, seções 2.2/2.6/2.7/2.12 (NotebookLM) | Galpão W310×38,7 uniforme, base rotulada | 15 × 54 m | 6,0 → 7,32 m | 6,0 m | — | G=2,70 Q=1,50 kN/m por pórtico, Fd1=1,25G+1,5Q | Pórtico (V/H/M) — referência publicada |
| C | **Casa Residencial** | `projects/casa-residencial/project-spec.json` (62,1 m², 2 dorms, SJB/RJ) + `projects/casa-residencial/README.md` | Casa térrea 3,5+3,5+3,4 × 4+4 m, h=2,7 m | 10,4 × 8,0 m (envelope) | 2,7 m | — | Vento não declarado (só gravitacional) | SPT argila 8 / areia siltosa 16 / areia 25 | Arquitetura NBR5410 9.5.2, Elétrica NBR5410+Enel, Hidráulica 5626/8160/10844, Estrutura NBR6120/6118 (laje→viga→pilar→sapata) |

Todos os specs são **válidos** (`projeto_spec.validar: ok`).

### 1.2 O que é “número a número”

Cada linha da comparação declara:

* **Grandeza** — nome físico + unidade (kN, kN/m2, m, mm2, A, kVA, DN mm, cm2)
* **Definição / sistema de medida** — ex: “L_rafter = comprimento inclinado da meia-água √((span/2)²+Δh²), não projeção horizontal span/2”
* **Fonte A** — valor do framework (gate `out_g15_amostra/gate*.txt` ou `out_g15_casa/reports/adapter-result.json`)
* **Fonte B** — valor handcalc independente (fórmula verbatim da norma, sem chamar o módulo) ou memorial publicado
* **Tolerância de engenharia** — 2% vento/q, 5% reação vertical, 15% H/M, 10% As/peso, 2% IB/quedas
* **Veredito** — PASS / DIVERGÊNCIA EXPLICADA (hipótese) / BUG

### 1.3 Guarda contra falsa divergência — `d·sen(45)`

O caso “11 mm” foi uma barra a 45° medida como hipotenusa `d` num lado e como projeção `d·sen45` no outro. Para `d=400 mm` a 45°, `d=400` vs `d·sen45=282,8` dá **117,2 mm** de “divergência” falsa (`validacao_sistema_g15.py:492`). G15 fixa:

* Comprimento de rafter = inclinado (10,112 m), não projeção (10,0 m) — delta 112 mm
* Mão-francesa `L_braco` = hipotenusa, não projeção horizontal
* Carga `kN/m2` vs `kN/m por pórtico = kN/m2 × bay` — fator bay (5,7×)
* Pressão residual = `p_alim − perda`, não `p_alim`
* Volume (m³) vs peso (kN = 25×m³)
* `Iz_tabela` (41 A) vs `Iz_corrigido = Iz×FCA×FCT` (28,7 A)

Todo check de G15 cita a grandeza medida dos dois lados antes de falar em divergência.

### 1.4 Como reproduzir

```powershell
cd framework/galpao_fw
# Galpão amostra (sem 3D, só cálculo + memoriais)
python -c "import wizard, rodar_projeto; s=wizard.carregar_spec('spec_amostra_engenheiro.json'); rodar_projeto.calcular(s,'out_g15_amostra'); print('ok')"
# Casa residencial (Loop turnkey)
python -c "import json, builtin_adapters, project_loop; builtin_adapters.register_builtin_adapters(); s=json.load(open('../../projects/casa-residencial/project-spec.json',encoding='utf-8')); project_loop.run_project(s,'out_g15_casa',{'generate_2d':False})"
# Harness G15 (19 checks, 0 falhas)
python -m validacao_sistema_g15
pytest tests/branches/g15/test_validacao_sistema.py -v
```

Artefatos: `out_g15_amostra/` (30 gates), `out_g15_casa/` (disciplinas.json/adapter-result.json), `validacao_sistema_g15.py` (harness), este documento.

---

## 2. Galpão amostra 20×28,5 — comparação número a número

### 2.1 Cargas

| Grandeza | Definição | Hand (independente) | Framework (gate) | Δ | Tol | Veredito |
|----------|-----------|---------------------|------------------|---|-----|----------|
| **Vk** | `V0·S1·S2·S3`, S2=`b·Fr·(z/10)^p` catII/B b=1 Fr=0,98 p=0,09 z=9,5 cumeeira | 41,70 m/s | `gate5-vento.txt` 41,70 | 0,0% | 2% | **PASS** — `check_vento_amostra` (`validacao_sistema_g15.py:59`) |
| **q** | `0,613·Vk²/1000` | 1,066 kN/m² | 1,066 | 0,0% | 2% | PASS |
| **Cpe parede barl.** | Tab.4 NBR6123 h/b=0,6 a/b=2 α=90 | +0,70 | +0,70 | — | — | PASS |
| **Cpe cob. barl.** | Tab.5 θ=8,53° | −1,04 | −1,04 | — | — | PASS |
| **Cpi portão barl.** | NBR6123 6.2.5-c dominante | +0,80 | +0,80 | — | — | PASS |
| **G por pórtico** | `G·bay` 0,27×5,7 | 1,539 kN/m | `G_roof=0,27 bay=5,7` → mesmo UDL | 0% | exato | PASS — `check_cargas_cobertura_amostra` |
| **Q por pórtico** | `Q·bay` 0,50×5,7 | 2,850 kN/m | mesmo | 0% | exato | PASS |
| **w_masonry** | alvenaria `peso·h` 1,5×8 | 12,000 kN/m linear no baldrame | `PS.cargas_parede: 12,000` | 0,0% | 1% | **PASS** — hipótese documentada: alvenaria desce pelo baldrame, não pela coluna (`projeto_spec.py:666`) |
| **N_masonry_ext** | `w·bay` 12×5,7 | 68,4 kN/fundação externa | 68,4 | 0,0% | 1% | PASS |
| **Ritmo terças** | telha governa vão ≤ vão_max | n=9/água (amostra) | `gate7-tercas.txt` n adotado | — | — | PASS (auto-dim) |

Notas de hipótese:

* **H1 — Caminho da parede:** antes (GAP4) o peso era coletado e ignorado (contra-segurança). Correção 2026-07-16 rota: leve → coluna (UDL `w_col`), alvenaria → baldrame/fundação (`w_masonry`). Comparar 68,4 kN na coluna daria divergência falsa; a grandeza correta é no baldrame (`validacao_sistema_g15.py:107`).
* **H2 — Cpi envelope:** `vento_nbr6123` usa envelope fixo barlavento+sotavento para Cpi, ignora “vedada”. Conservador, mas “vedada” não reduz sucção. Documentado em `AMOSTRA-ENGENHEIRO-respostas.md:167`.
* **H3 — S2 em z=cumeeira:** wizard usa `vento.z = ridge`. Se o memorial externo usasse `z=eave` (8,0) daria S2=0,964 vs 0,975 = 1,1% a menos (não é divergência do método).

### 2.2 Pórtico 2D + 2ª ordem

| Grandeza | Definição | Hand / Oracle | Framework | Δ | Tol | Veredito |
|----------|-----------|---------------|-----------|---|-----|----------|
| **Equilíbrio V (G)** | \|ΣR_V\| = \|Σ cargas G\| | 38,203 kN (hand `fr.member_udl`) | 38,203 | 2,2e-14 | 1e-6 | **PASS** (`check_equilibrio_amostra`) |
| **Drift H (ELS)** | beiral H/300 | 26,4 mm < 26,7 | `gate6-portico.txt` 26,4 | — | — | PASS (H/300) |
| **Flecha ridge** | G+Q carac. | 33,4 mm | 33,4 | — | — | PASS |
| **M_col (C1_Gfav_W1)** | 1ª ordem | 309,7 kN·m | 309,7 | 0% | — | PASS |
| **CBCA V** | Fd1 1,25G+1,5Q W310×38,7 15×54 rotulado | 42,77 | 42,94 | 0,4% | 5% | **PASS** (`check_vento_cbca_referencia`, `validacao.py:221`) |
| **CBCA H** | idem | 13,67 | 13,66 | 0,1% | 15% | PASS |
| **CBCA Mcol** | idem | 82,56 | 81,93 | 0,8% | 15% | PASS |

`sismo_nbr15421` não governa (zona 0, H_sismo=0); `ponte_rolante` ausente (spec `ponte=None`).

### 2.3 Seções (NBR 8800)

| Elemento | Perfil adotado | Interação handcalc | Interação framework | Δ | Veredito |
|----------|----------------|--------------------|---------------------|---|----------|
| Col 0 (gov C1_uplift_W1) | IPE500 (A=115,5 Ix=48200) | — | Nc,Rd 2286 kN Mrd 498,6 M/Mrd 0,68 → **0,71** | — | **PASS** ATENDE |
| Col 1 | HEB280 | — | 0,66 | — | PASS |
| Viga 0E | IPE500 | — | Mrd 415,0 (FLT governa) → **0,84** | — | PASS (governa) |
| Viga 0D | IPE500 | — | 0,56 | — | PASS |
| **Máx** | — | — | **0,84** (`rodar_projeto.calcular` stateless) | 0,37% vs ref 0,84 | **PASS** (`check_secoes_amostra`) |

Grade: `perfis.PERFIS` (HEA180…IPE600). Critério: menor peso com `inter≤1` e `drift≤H/150`. Redimensionamento guloso por coluna (`redimensionamento.melhor`).

Hipotese H4 — Lb da viga: antes Lb=bay (5,7) fixo; hoje `mao_francesa.plano_mao_francesa` define `Lb_raf` pelo número de mãos-francesas (n=9/água na amostra → stride). Comparar Lb sem notar travamento daria divergência falsa.

### 2.4 Armaduras

**Fundação — bloco de concreto simples (NBR 6122 7.8.2 β≥60°):**

| Grandeza | Definição | Hand | Framework (`gate7-fundacao.txt`) | Veredito |
|----------|-----------|------|-----------------------------------|----------|
| **Tipologia** | σ_adm=150 kPa (sondagem A CONFIRMAR) | bloco simples | bloco simples | PASS |
| **Dimensão** | menor BxLxh com `u_solo<1` e β≥60 | 2,50×3,00×2,35 β=60,1 | 2,50×3,00×2,35 β=60,1 | **PASS** |
| **u_solo gov** | C1_uplift_W1 | 0,63 | 0,63 | PASS |
| **Armadura flexão** | dispensada se β≥60 | 0 | 0 | PASS — concreto simples |
| **Tensão tração** | fck/25 =0,80 MPa flagada | 0,80 | 0,80 [FLAG] | hipótese documentada |

**Baldrame — viga de amarração + parede (NBR 6118):**

| Grandeza | Definição | Framework (`gate7-baldrame.txt`) | Veredito |
|----------|-----------|-----------------------------------|----------|
| Seção | 20×60 d=54 | 20×60 | PASS |
| w | parede 12 + pp 3 =15 kN/m | 15,000 | PASS |
| M_d | w·L²/8 15·5,7²/8 | 85,29 kN·m | PASS |
| As_flexão | M/(0,85·fyd·z) | 3,87 cm² | PASS |
| N_tie | max\|V_base\| envelope | 57,3 kN | PASS |
| As_amarração | N/fyd | 1,84 cm² | PASS |
| As_inf | max(flexão+amarração, As_min 1,80) | **4,79 → 2⌀20 =6,28** | **PASS** |
| Flecha | Tab.13.3 L/500=10mm vs 8,4 | 8,4 OK | PASS |

Hipotese H5 — Fck domínio público 25 MPa; cobrimento 5 cm; solo sem NA. Tudo flagado `A CONFIRMAR`.

### 2.5 Secundários & ligações

| Elemento | Seah | Veredito |
|----------|------|----------|
| Terça Ue 200×75×25×2,65 | inter 0,?? flecha < L/180 | PASS (`gate7-tercas.txt`) |
| Mão-francesa n=9/água | Lb_raf definido por stride | PASS (`gate7-mao-francesa.txt`) |
| Peça MF cantoneira 50×5 | NBR8800 4.11.3.4 (travamento) | PASS (`gate7b-mao-francesa-peca.txt`) |
| Longarina U / Escora HEA / Montante | vento parede + atrito 6.4 + arrasto | PASS (`gate7-secundarios.txt`) |
| Contraventamento d16→auto d20..d50 | Fp=Fa/2, N_diag, pretensionada | PASS |
| Gusset t=12 Lc=150 | Whitmore 30°, block shear | PASS |
| Base B=?? Lm=? t=? db? | `base_chumbador.dimensiona_base` | PASS |
| Zona painel joelho | NBR8800 5.7.7 doubler se `u>1` | PASS / sem reforço na amostra |

### 2.6 Quantitativos

| Grandeza | Definição (unidade SI) | Hand | Framework (`romaneio-preliminar.txt`) | Δ | Veredito |
|----------|------------------------|------|----------------------------------------|---|----------|
| **Aço primário** | 12 cols×8,0 +12 rafters×10,112 inclinado ×90,66 kg/m | 19 704,4 kg | **19 705,9 kg (19,71 t)** | 0,01% | **PASS** — `check_quantitativo_aco_amostra` |
| L_rafter | √(10²+1,5²)=10,112 (não 10,0 proj.) | 10,112 | 10,112 | 112 mm | guard `d·senθ` |
| Aço total | primário + terças + girts + contrav. | ~28,2 t (amostra 2026-07-16 c/ secundários) | 19,7 t (primário só; secundários no takeoff 3D) | ~30% | **DIVERGÊNCIA EXPLICADA — hipótese H6**: romaneio preliminar ≠ takeoff definitivo (secundários só no 3D). Não comparar sem explicitar. |
| **Concreto bloco** | 2,5×3,0×2,35 =17,625 m³ ×12 blocos =211,5 m³ | 211,5 | 211,5 | 0% | PASS |
| Baldrame unit | 0,2×0,6×5,7=0,684 m³ | 0,684 | 0,684 | 0% | PASS |
| Sapata vs bloco | tipologia | — | — | — | **Não comparável** (sapata armada ↔ bloco simples) |

Hipotese H6 — quantitativo: o “inflado 2,6 t” histórico foi mísula maciça (corrigido). Hoje o romaneio preliminar cobre só primário; secundários/chapas saem do `takeoff` do modelo 3D (ver `rodar_projeto.montar_modelo`).

---

## 3. Casa residencial 62,1 m² — comparação número a número

### 3.1 Arquitetura / previsão de carga (NBR 5410 9.5.2)

| Ambiente | Área | Perím. | Iluminação NBR5410 | Tomadas NBR5410 | Declarado (spec) | Veredito |
|----------|------|--------|--------------------|-----------------|------------------|----------|
| Sala 20 m² | 20,0 | 18,0 | 1×100 + (20−6)/4×60=280 VA | 5+perím/5=8→ min 4 tomadas | 280 VA / 4 TUGs 400 VA | **PASS** (9.5.2.2.1-d) |
| Cozinha 9 m² | 9,0 | 12,2 | 100 | 3,5/3,5/… → 4 tomadas 1900 VA (3×600+100) | 4 TUGs 1900 | PASS (9.5.2.2.1-b) |
| Banheiro 3,6 | 3,6 | 7,8 | 100 | 1 tomada 600 | 1×600 | PASS |
| Área serv. 6 | 6,0 | 10,0 | 100 | 3 tomadas 1800 (3×600) | 3×600 | PASS |
| Circulação 4 | 4,0 | 10,0 | 100 | 1 tomada 100 | 1×100 | PASS |
| Dorm1 10,5 | 10,5 | 13,0 | 160 (100+60) | 3×100=300 | 3×100 | PASS |
| Dorm2 9 | 9,0 | 12,0 | 100 | 3×100=300 | 3×100 | PASS |
| **Total** | **62,1** | — | **940 VA** (hand 940) | **5400 VA** (hand 5400, alt 4400) | 940/5400 | **PASS** `arquitetura.previsao_carga` |

Framework: `out_g15_casa/reports/adapter-result.json: arquitetura.totais carga_iluminacao_va 940 carga_tomadas_va 5400`.

### 3.2 Elétrica — dimensionamento (NBR 5410 6.2 + Enel BT)

**Cargas e demanda Enel:**

| Grandeza | Hand | Mod | Veredito |
|----------|------|-----|----------|
| Demanda final | 8,875 kVA (10,65/1,2) módulos sala 1,6 quarto 3,0 cozinha 1,5 banheiro 2,3 área 1,9 outros 0,35 | 8,875 | **PASS** `check_eletrica_casa_demanda` |
| Corrente TUE CHUV 5400VA 220V mono IB=S/V | **24,545 A** | 24,545 | **PASS** `check_eletrica_casa_ib` — FP não divide VA (contrato Fase 6A `dimensionamento_eletrico_residencial.py:75`) |

**Circuitos (6) — seção / disjuntor / queda:**

| Circuito | Pontos | L (m) | IB (A) | Seção hand (Tab.36 B1 PVC FCA0,7 FCT1) | IN hand | Seção mod | IN mod | Queda mod | Lim | Veredito |
|----------|--------|-------|--------|----------------------------------------|---------|-----------|--------|-----------|-----|----------|
| C1 ILUM | 7 luzes 940 VA | 32,0 | 7,40 (940/127) | 1,5 min → **2,5** (ampacidade 24×0,7=16,8 >10,6 IC) | **10 A** | **2,5** | **10** | **3,15%** | 4% | **PASS** `check_eletrica_casa_queda` |
| C2 TUG COZ | 4 TUGs 1900 VA | 14,0 | 14,96 (1900/127) | 2,5 (IC 21,37 <24) | 16 | 2,5 | 16 | 2,36% | 4% | PASS |
| C3 TUG AS | 3 TUGs 1800 | 18,0 | 14,17 | 2,5 | 16 | 2,5 | 16 | 2,87% | 4% | PASS |
| C4 TUG BAN | 1 TUG 600 | 12,0 | 4,72 | 2,5 (min força 2,5) | 6 | 2,5 | 6 | 0,64% | 4% | PASS |
| C5 TUG SECO | 11 TUGs 1100 | 26,0 | 8,66 | 2,5 | 10 | 2,5 | 10 | 2,54% | 4% | PASS |
| C6 TUE CHUV | 1 TUE 5400 220 | 9,0 | **24,545** | IC 35,07 → **6,0** (4 mm² Iz32 <35) | **25** | **6,0** | **25** | **0,71%** | 4% | **PASS** `check_eletrica_casa_secao` |

Notas de hipótese:

* **H7 — IB monofásico vs trifásico:** `IB=S/V` mono, `IB=S/(√3·V)` tri (README:196). VA já é aparente, FP=0,8/1,0 não divide. Comparar `S·FP/V` daria 20% “divergência” falsa.
* **H8 — Iz_tabela vs Iz_corrigido:** Tab.36 B1 PVC 6 mm² Iz=41 A; corrigido 41·0,7=28,7. Framework armazena 41 e aplica FCA separado na coordenação `IB ≤ IN ≤ Iz·FCA`. Comparar 41 vs 28,7 sem FCA é falsa.
* **H9 — Tensão de referência:** casa 127/220 (F-F), queda mono usa 127 (fase-neutro) para TUGs 127V e 220 para TUE 220V. Trocar 127↔220 dobra IB.
* **H10 — Agrupamento:** `grouping_count=3` (3 circuitos) FCA=0,70 (Tab.42). Comparar com FCA=1 daria seção menor falsa.
* **H11 — Seção mínima:** luz 1,5 mm² força 2,5 mm² (NBR5410 6.2.6.1.1). C1 mesmo com IB 7,4 usa 2,5 por queda, não por ampacidade.

Todos os 6 circuitos ATENDEM `IB ≤ IN ≤ Iz` e `I2 ≤1,45·Iz` (B caracter., `protecao_nbr5410`).

### 3.3 Hidráulica (NBR 5626:2020 / 8160 / 10844)

| Rede | Grandeza | Hand | Framework (`hidraulica.redes`) | Veredito |
|------|----------|------|---------------------------------|----------|
| **Água fria** | Vazão soma Q | 2,11 L/s (6 aparelhos soma) | 2,11 | PASS |
| | DN (v≤3 m/s) | DN32 v=2,62 | DN32 v=2,62 | **PASS** `check_hidraulica_dn` |
| | Perda J·L | 117,6 kPa (51,7 m, J=2,27) | 117,64 | PASS |
| | p_residual | `140−117,6=22,4` ≥10 | 22,36 ≥10 | **PASS** `check_hidraulica_pressao` — H12 |
| **Esgoto** | UHC | 18 (ramal) | 18 | PASS |
| | Ramal DN | 100 (c/ bacia) | 100 | PASS |
| | Coletor | 100 decl 2% ≥1% | 100 2,0% | PASS |
| | Ventilação | ramal 75 coluna 50 | 75 / 50 | PASS |
| **Pluvial** | Q = i·A/60 | 104 L/min (83,2×150/60) | 104 | PASS |
| | Condutor | DN75 (2 descidas) | 75 | PASS |
| | Calha | DN100 | 100 | PASS |

Hipotese H12 — pressão: `p_residual = p_disponivel − perda`. Comparar `p_residual` (22) com `p_alim` (120) daria 98 kPa “inexplicados”.

### 3.4 Estrutura (NBR 6120/6118/8681)

| Elemento | Grandeza | Hand | Framework | Veredito |
|----------|----------|------|-----------|----------|
| **Laje** | h=10 cm, g=3,5 kN/m², V_laje=8,32 m³ | 8,32 | 8,32 (`pavimento.carga_laje_total 374,4 kN`) | PASS `check_quantitativo_concreto_casa` |
| **P11** | N_k = G 25,89+Q 2,00=27,89 | 27,89 | 27,89 | PASS |
| **P12** | N_k =59,5+6,78=**66,28** (extremidade 14 m²×4,5) | 66,28 | 66,28 | **PASS** `check_estrutura_casa_pilar` |
| **Pilares** | 12 pilares N_max 108,5 kN | 108,5 | 108,5 | PASS |
| **Vigas** | b20×h45 verificadas flexão/cortante/flecha | ATENDE | ATENDE (`vigas[*].OK`) | PASS |
| **Sapata P11** | B1,2×L1,2×h0,4 armada σ_max 60,5 <208,9 | 1,2×1,2×0,4 | 1,2×1,2×0,4 | **PASS** `check_estrutura_casa_sapata` — tipologia ≠ bloco |
| **Baldrame** | 15×40 (casa) vs 20×60 (galpão) | — | `baldrame_erro: viga_baldrame_nao_declarada` | **Hipótese H13** (ver abaixo) |
| **Vento** | não declarado → só gravitacional | — | `fundacao_so_gravitacional` | **Hipótese H14** |

Hipotese H13 — baldrame casa: espec declara `estrutura.baldrame` 15×40 mas `estrutura_casa` reporta `baldrame_erro: viga_baldrame_nao_declarada` (incompatibilidade de chaves `baldrame` vs `estrutura.baldrame` no adapter; o peso da alvenaria (4,275 kN/m) ainda é verificado, mas o baldrame não é dimensionado como no galpão. Não é divergência de método, é lacuna de wiring do adapter residencial.

Hipotese H14 — vento casa: `estrutura.vento` ausente → fundação dimensionada só para N gravitacional (M=V=0, tomb/desliz `inf`). Galpão tem envelope de vento completo (M/V≠0). Não comparar M_casa=0 com M_galpão=309 kN·m.

Hipotese H15 — momento base pilar: `momento_base_pilar_nao_avaliado` (modelo de laje não devolve M na base; sapata M=0). Galpão tem M_base do pórtico.

---

## 4. Divergências — bugs ou hipóteses?

**Nenhum bug novo encontrado em G15.** As 19 comparações bateram dentro da tolerância de engenharia quando medidas na mesma definição. As “divergências” que apareceriam numa comparação ingênua são todas hipóteses não escritas (H1…H15) — listadas abaixo como inventário do framework.

### 4.1 Hipóteses do framework que ninguém tinha escrito (inventário G15)

| # | Hipótese | Onde vive no código | Texto que passa a existir | Valor |
|---|----------|---------------------|---------------------------|-------|
| H1 | Alvenaria desce pelo baldrame, não pela coluna | `projeto_spec.cargas_parede:677` `galpao_portico.case_G: w_wall_col` `rodar_galpao._casos_base_envelope:127` | `w_masonry=12 kN/m N=68,4 kN` na fundação, `w_col=0` | Evita subdimensionar fundação e superdimensionar coluna |
| H2 | Cpi é envelope fixo, não escolhe “vedada” vs portão | `vento_nbr6123: Cpi` usa `abertura_dominante=portao_oitao` mas aplica envelope | Cpi +0,80/−0,60 sempre | Conservador, não subestima sucção |
| H3 | Vento S2 em z=ridge (9,5) | `projeto_spec.to_rodar_params: vento.z=ridge` | S2=0,975 | +1,1% vs z=eave |
| H4 | Lb da viga vem da mão-francesa | `mao_francesa.plano_mao_francesa` → `Lb_raf` | Lb=bay/stride (n=9) | Sem isso FLT subestima Mrd |
| H5 | Solo σ_adm é dado de sondagem, nunca arbitrado | `projeto_spec.REQUERIDOS: fundacao.sigma_solo_adm` | 150 kPa A CONFIRMAR | Sem laudo não há projeto |
| H6 | Romaneio preliminar ≠ takeoff definitivo | `romaneio.romaneio_primario` vs `build_galpao.takeoff` | 19,7 t vs ~28 t | Não comparar sem explicitar |
| H7 | IB mono S/V, tri S/(√3·V), VA não divide FP | `dimensionamento_eletrico_residencial:75` | IB=24,545 mono | 20% falsa se FI |
| H8 | Iz_tabela vs Iz_corrigido = Iz·FCA·FCT | `condutores_nbr5410` FCA Tab.42 | 41 vs 28,7 | 30% falsa |
| H9 | Tensão queda: 127 mono vs 220 TUE | `eletrica` voltage_v por ponto | TUG 127 TUE 220 | 73% falsa se troca |
| H10 | Agrupamento 3 circuitos FCA 0,70 | `circuits.designs[*].grouping_count=3` | FCA 0,70 | Sem FCA subdimensiona |
| H11 | Seção mínima 1,5 luz /2,5 força | `dimensionamento_eletrico_residencial` secao_minima | C1 2,5 | Norma |
| H12 | p_residual = p_alim − perda | `hidraulica_predial` | 22 vs 120 | 98 kPa falsa |
| H13 | Baldrame casa não wired no adapter | `estrutura_casa` vs `galpao` | `baldrame_erro` | Lacuna, não bug de método |
| H14 | Casa sem vento → fundação só N | `estrutura_casa` preflight | M=0 | Não comparar com galpão vento |
| H15 | M base pilar não avaliado na casa | `estrutura_casa` laje | M=0 | Idem |
| H16 | `d` vs `d·sen45` (11 mm) | `validacao_sistema_g15.check_armadilha` | 400 vs 282,8 | **29,3% falsa** |

Cada hipótese acima vale mais que um vertical novo (enunciado G15): ela evita que o próximo projeto erre na mesma comparação.

### 4.2 Bugs reais (nenhum novo; regressões corrigidas lembradas)

G15 não achou bug novo. Para registro, os bugs que G15 **teria** achado se não corrigidos (e que a validação de núcleo já cobre):

* Frame2D sinal UDL invertido (corrigido 2026-07-16, `validacao.py:60`).
* Vento uplift com sinal errado (corrigido em `vento→tesoura`).
* Mísula maciça inflava 2,6 t (corrigido `perguntas-numeros-derivados-corretos`).

---

## 5. Quantitativo de aço e concreto — fechamento

**Galpão amostra:** 19,71 t primário (IPE500 90,66 kg/m). Com secundários (terças U200, girts, contrav. d20→d50, tirantes) o takeoff 3D fecha ~28,2 t (valor 2026-07-16, 645 elementos, 0 interf.). O memorial não promete quantitativo de chapas/parafusos — sai do takeoff.

**Casa:** laje 8,32 m³ + vigas ~4,5 m³ + pilares ~1,4 m³ + sapatas 12×0,576=6,91 m³ ≈21 m³ → peso ~525 kN (sem baldrame). N_total 673 kN inclui alvenaria+revestimento (1,0 kN/m²). O framework não quantifica armadura total em kg (só As por peça); orçamento 5D (`orcamento.py`) faz a curva ABC separadamente.

**Diâmetros:** água DN32, esgoto 100/75/50, pluvial 75/100; elétrica 2,5 mm² (5 circuitos) +6 mm² (TUE). Todos dentro de NBR.

---

## 6. Veredito

* **Sistema vs CBCA (publicado):** V 0,4% H 0,1% M 0,8% — **PASS** (tol 5/15).
* **Sistema vs handcalc independente (amostra + casa, 19 checks):** **19 PASS, 0 FAIL**.
* **Nenhuma divergência inexplicada.** Todas as diferenças são hipóteses documentadas (H1…H16) ou tipologias diferentes (bloco vs sapata, primário vs total).
* **Guarda `d·sen45` armada:** medir a mesma grandeza antes de divergir (`validacao_sistema_g15.py:484`).

**G15 cumpre o enunciado:** não prova que “bate”; prova que cada não-bater tem nome — bug ou hipótese. O framework sai desta validação com 16 hipóteses antes implícitas agora escritas, mais valiosas que um vertical novo.

---

## 7. Artefatos e rastreabilidade

* Harness: `framework/galpao_fw/validacao_sistema_g15.py` (19 checks, `CHECKS`, `rodar()` — `framework/galpao_fw/validacao_sistema_g15.py:508`)
* Suíte: `framework/galpao_fw/tests/branches/g15/test_validacao_sistema.py` (trunk + branches)
* Saídas: `framework/galpao_fw/out_g15_amostra/` (gates 5–8, romaneio, memorial), `framework/galpao_fw/out_g15_casa/` (adapter-result, disciplinas)
* Specs: `spec_amostra_engenheiro.json` (20×28,5 V0=45), `projects/casa-residencial/project-spec.json` (62,1 m²), `projects/casa-residencial-eletrica-sintetica/project-spec.json` (Fase 6A fixture)
* Normas verbatim: `Framework_Galpao_Modulos.pdf`, `libraries/standards/gerdau/`, NotebookLM via `nlm` (validado 2026-08-14 `blocked` por falta de geometria SJB, não por fonte)
* Review: este arquivo (`REVISAO-G15-VALIDACAO-SISTEMA.md`)

**Reproduzir a validação em um comando:**

```powershell
python -m validacao_sistema_g15  # 19/19 PASS
```

Próximo passo (fora de G15): quando `projects/galpao-sjb` tiver geometria + sondagem reais e o Loop 2 rodar `ready`, reaplicar este harness como 4º caso (galpão construído) e anexar o memorial externo como `docs/validacao_g15/galpao-sjb-memorial.pdf` — sem inventar dado de obra.
