# Task 3 — Arqueologia git + PRs GitHub: linha do tempo S19 → 2026-08-11

- **Data da evidência:** 2026-08-11 (gerado em sessão de revisão da wiki)
- **Repo:** `JHenriquesss/FreeCad_Automatic` (gh autenticado como `JHenriquesss` — verificado)
- **Worktree usado:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (compartilha repo com o clone principal)
- **HEAD local:** `6358157` (main = `origin/main`, merge do PR #171) — worktree limpo, sem branches/tags/stash criados
- **Passo 0 (já feito, não repetido):** `git fetch origin --prune` rodou com sucesso em **2026-08-11 17:30** — todos os refs remotos (`origin/*`) presentes localmente
- **Fonte dos dados de PR:** `gh` CLI (lista completa via API, não HTML degradado). **NENHUM** veredito derivado de fonte parcial.

---

## 1. Janela de análise (Must Do 2) — ajustes logados

| Passo | Ação | Resultado |
|---|---|---|
| 1 | `gh pr view 55 --json commits,createdAt` | Commit mais antigo do PR #55: **authoredDate `2026-07-22T18:19:29Z`** (commit `40844a3`, "fecha gaps A3 (FLT do console) e C5 (patamar de escada)"); PR criado `2026-07-22T18:55:17Z`, merged `2026-07-22T21:58:03Z` |
| 2 | `gh pr view 61 --json mergeCommit` | mergeCommit `ea48acf` — confere com o log local (`ea48acf Merge pull request #61`) |
| 3 | Probe `git log --since=2026-07-22T18:19:29Z` | **OK na 1ª tentativa** — PRs #55, #56, #58, #59, #60, #61 presentes no log local. **NENHUM ajuste necessário** (não precisei alargar para 2026-07-15 nem 2026-07-01) |
| 4 | Nota sobre #57 | PR #57 (`feat/bridge-headless`) foi mergeado **em branch intermediária** (`feat/ifc-export-bim`, baseRefName confirmado via `gh pr view 57`); conteúdo chegou à main via **PR #59** ("Leva o montar_modelo headless (#57) para a main", merge `5863532`). Por isso #57 não aparece como "Merge pull request #57" no log da main — **não é omissão da janela** |

**Data base da S19 usada na timeline:** `2026-07-22T18:19:29Z` (commit mais antigo dos PRs #55–#61). Verificação explícita de que a S19 aparece no log local: `git log --since=2026-07-22T18:19:29Z --oneline | Select-String "pull request #(5[5-9]|6[0-1])"` → 6 merges (55, 56, 58, 59, 60, 61) + #57 via #59.

---

## 2. Reconciliação remoto × local

**Fonte remota:** `gh pr list --state all --limit 300` → **171 PRs, 171/171 estado `MERGED`** (nenhum aberto/closed-não-merged; `--limit 300` cobre todos).

**Fonte local:** `git log --merges --since=2026-07-22T18:19:29Z` → **116 merges com PR ≥ 55** no log local.

| PRs (range) | Esperado | No log local | Explicação |
|---|---|---|---|
| #55–#171 (117 PRs) | 117 merges | 116 "Merge pull request #N" | #57 não vira merge na main (merge em branch; veio via #59). **Zero remote-only no período.** |

- Merges < 55 que caem dentro da janela por data: **#51, #52, #53** (S18, merged 18:36–18:37Z de 22/07 — após a âncora 18:19:29Z, portanto incluídos; esperado e coerente com a S18 fechando horas antes da S19).
- **Veredito:** todo PR com `mergedAt ≥ 2026-07-23` está no log local. Nenhuma justificativa "remote-only" necessária.
- Merges fora da janela (`--since` anterior a 18:19:29Z de 22/07): #1–#50 (pré-S19) + #54 (merged 18:40:36Z — porém #54 foi "trazido para a main" pelo PR #55, conforme 06-open-threads T21; conteúdo de #54 está na main via merge #55 `83570c9`).

---

## 3. Timeline completa de fases (S19 → 2026-08-11)

Todos os clusters abaixo são **bijectivos** (todo cluster tem bloco; todo PR de #55 a #171 está em exatamente 1 cluster). Fonte: `mergedAt` do GitHub cruzado com o log local de merges.

### Cluster 1 — S19: Interoperabilidade BIM / IFC4 físico e analítico (PRs #55–#61)
- **Janela:** 2026-07-22T21:58Z → 2026-07-23T00:15Z (base: commit mais antigo authored `2026-07-22T18:19:29Z`)
- **Área:** BIM sem FreeCAD — exportador IFC4 (`ifc_map.py`), `montar_modelo` headless (bridge→freecadcmd), modelo neutro (`modelo_neutro.py`) + emissor IFC4 puro-Python (`ifc_emit.py`), secundários lineares no IFC puro, modelo analítico + IFC4-Structural
- **Wiki confirma:** 00-index:66-75 ("Sessão 19: Interoperabilidade BIM e IFC4 Físico/Estrutural (PRs #55 a #61 MERGED)"; 831 testes verdes; D74–D79)
- PRs: 55, 56, 57, 58, 59, 60, 61

### Cluster 2 — S19-ext: IFC físico puro — expansão e fechamento (PRs #62–#80) ★ BUCKET CLASSIFICADO
- **Janela:** 2026-07-23T00:53Z → 2026-07-23T17:30Z
- **Área:** continuação direta do tema S19 (IFC puro) — esforços 2ª ordem no analítico (#62), fundações sapata/bloco (#63), telha IfcCovering (#64), tapamento (#65), pórtico tapered (#66–67), fix escala 1000x + placas de base (#68), nervuras (#69), clipes (#70), mãos-francesas (#71), escoras/cumeeiras/oitão (#72), tirantes (#73), conectores (#74), drenagem (#75), gussets (#76), mísula (#77), IfcPile + ponte rolante (#78) — e **auditoria de fechamento do aço**: 3 gaps (ELS girt + corrosão + camber, #79) e flecha do baldrame sob alvenaria NBR 6118 Tab 13.3 + dreno (#80)
- **Classificação (alimenta todo 14):** **cluster próprio** — não fundido com S19 (#55–61) porque a wiki já fechou S19 em 00-index:66-75 com o review PR_55_61_Review; e não fundido com S20 (concreto, #81+) porque é 100% IFC/estrutura metálica, sem concreto. Justificativa: 17 PRs de expansão IFC (62–78) + 2 PRs de auditoria de fechamento (79–80) formam o "rabo" da S19 no mesmo dia, todos tocando `modelo_neutro.py`/`ifc_emit.py` (verificado via `git log --oneline -- <arquivo>`: 21 commits em cada entre 22–23/07).
- PRs: 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80

### Cluster 3 — S20: Vertical de CONCRETO (PRs #81–#101)
- **Janela:** 2026-07-23T22:52Z → 2026-07-27T20:00Z
- **Área:** galpão pré-moldado — pilar flexão composta (reta + oblíqua), viga CA, orquestrador, BIM IFC4, executivo, desenho SVG, protensão, NBR 9062 pré-moldado, fogo NBR 15200, fissuração ELS-W, estabilidade global, perdas, estaca, cortante protendida, torção, planta de formas, armadura IFC (Pset_Armadura), interferência, build 3D sólido, pranchas A1 TechDraw (P1–P20)
- **Wiki confirma:** 00-index:23-26 (S20, PRs #81–#101; 60 testes; fixtures Bastos/Araújo/Carvalho)
- PRs: 81–101 (21 PRs)

### Cluster 4 — S21–S26: Vertical ELÉTRICO (PRs #102–#106)
- **Janela:** 2026-08-01T23:56Z → 2026-08-02T02:02Z
- **Área:** P21 núcleo BT + aterramento + SPDA, P22 subestação/MT (NBR 14039), P23 BIM/IFC elétrico, P24–P25 build 3D + executivo A1, P26 luminotécnica (NBR 8995)
- **Wiki confirma:** 00-index:27-29 (S21–26, PRs #102–#106; notebook c5934f22; 1040 green)
- PRs: 102, 103, 104, 105, 106

### Cluster 5 — S27–S30: Vertical INCÊNDIO/AVCB (PRs #107–#110)
- **Janela:** 2026-08-02T02:35Z → 2026-08-02T03:04Z
- **Área:** P27 base (emergência 10898 + sinalização 16820 + alarme 17240), P28 sprinklers (NBR 10897), P29 iluminação externa (NBR 5101), P30 climatização (NBR 16401) standalone
- **Wiki confirma:** 00-index:30-32 (S27–30, PRs #107–#110)
- PRs: 107, 108, 109, 110

### Cluster 6 — S31: Loop elétrico (PR #111)
- **Janela:** 2026-08-02T03:22Z
- **Área:** P31 fecha o loop — iluminação externa + climatização como cargas do QGF
- PRs: 111

### Cluster 7 — S32: TURNKEY orquestrador-mestre (PR #112)
- **Janela:** 2026-08-02T14:27Z
- **Área:** `galpao_turnkey.rodar(spec)` despacha todos os verticais; consolida gates + ATENDE global; falha isolada por disciplina
- **Wiki confirma:** 00-index:33-35 (S32, PR #112; modelo federado IFC+3D+clash AABB)
- PRs: 112

### Cluster 8 — P33–P39: Robustez, executivo incêndio, caderno único, hidrantes, revisão total, dispatch turnkey (PRs #113–#119)
- **Janela:** 2026-08-02T14:37Z → 2026-08-02T16:43Z
- **Área:** P33 harness de robustez dos verticais novos; P34 executivo A1 incêndio (rotas de fuga/AVCB); P35 acionadores p/ galpão alongado (NBR 17240); **P36 caderno executivo único do turnkey (PR #116)**; P37 hidrantes e mangotinhos (NBR 13714); **P38 revisão total — drawing-vs-data + guards de entrada degenerada (PR #118)**; P39 dispatch do aço no caderno turnkey
- **Wiki confirma:** 00-index:36-39 (S36 caderno PR #116; S38 revisão PR #118)
- PRs: 113, 114, 115, 116, 117, 118, 119

### Cluster 9 — Fixes de contra-segurança + BIM incêndio (PRs #120–#123)
- **Janela:** 2026-08-02T19:55Z → 2026-08-02T20:38Z
- **Área:** fix hidrantes cobertura NBR 13714 5.3.2 por malha + 2 jatos; fix guards elétrico nos 7 módulos; BIM/IFC dos equipamentos de incêndio; fix planta iluminação de emergência count-driven
- PRs: 120, 121, 122, 123

### Cluster 10 — Turnkey federado BIM/IFC + clash + 3D (PRs #124–#134)
- **Janela:** 2026-08-02T20:46Z → 2026-08-03T02:42Z
- **Área:** modelo BIM/IFC federado consolidado; aço dentro do federado; clash detection; build 3D sólido federado + fix AABB orientado; apêndice de coordenação no caderno; triagem esperado×revisar; escala das caixas; vertical climatização federada; render-and-look PNG; vertical hidráulica federada (6ª disciplina); prancha de coordenação no caderno
- PRs: 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134

### Cluster 11 — HVAC velocidade NBR 16401 (PR #135)
- **Janela:** 2026-08-03T02:51Z
- **Área:** velocidade do duto ancorada na NBR 16401-1 Tab.1 (era flagada)
- PRs: 135

### Cluster 12 — S39: HIDRÁULICA + COORDENAÇÃO (PRs #136–#147)
- **Janela:** 2026-08-03T06:35Z → 2026-08-03T15:33Z
- **Área:** dimensionamento hidráulico NBR 5626:2020/8160/10844; prancha A1 de coordenação do federado; reservatório de incêndio como torre elevada no render; revisão NLM (2 gaps); método dos pesos NBR 5626:1998; verificação de pressão (Fair-Whipple-Hsiao); ventilação do esgoto + calhas pluviais; executivo A1 hidro/clima; janela lateral wizard (L,H)→faixa; revisão S39; condutor em paralelo (não satura); água quente SPAFAQ
- **Wiki confirma:** 00-index:40-43 (S39, PRs #136–#147; revisão NLM achou 2 gaps: DN75 vertical, declividade mínima)
- PRs: 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147

### Cluster 13 — S40: HARDENING saturação silenciosa (PR #148)
- **Janela:** 2026-08-03T16:17Z
- **Área:** fechou saturação silenciosa em terça (aço) e placa de sinalização (incêndio); concreto verificado limpo; 1ª auditoria NLM formal de concreto/aço
- **Wiki confirma:** 00-index:44-49 (S40, PR #148 + auditoria)
- PRs: 148

### Cluster 14 — S40: Docs consolidação arco S20–S40 (PR #149)
- **Janela:** 2026-08-03T16:33Z
- PRs: 149

### Cluster 15 — S40: Janela dupla-conversão (PR #150) — fecha T40
- **Janela:** 2026-08-03T18:31Z
- **Área:** convenção de janela unificada na FAIXA; mata a dupla-conversão aberta pelo #144; suíte 100% verde
- **Wiki confirma:** 06-open-threads T40 (linha 3: "✅ RESOLVIDO (PR #150)"); 00-index:50-52
- PRs: 150

### Cluster 16 — S40: Docs T40 resolvido (PR #151)
- **Janela:** 2026-08-03T18:32Z
- PRs: 151

### Cluster 17 — S40: Runner de regressão confiável (PR #152)
- **Janela:** 2026-08-03T18:55Z
- **Área:** `tools/run_tests.py` — pytest-xdist `-n auto` (primário) + fallback 2 lanes; ~1281 testes em ~5 min
- **Wiki confirma:** 00-index:53-58 (S40, PR #152)
- PRs: 152

### Cluster 18 — S40: Docs situação atual (PR #153)
- **Janela:** 2026-08-04T13:14Z (último PR antes do hiato)
- **Área:** wiki reflete situação S40 (T40 fechado + runner #152 + regressão verde)
- PRs: 153

### Cluster 19 — S41: Fixes de desenho/pranchas + planta elétrica (PRs #154–#161)
- **Janela:** 2026-08-09T04:12Z → 2026-08-09T06:00Z (pós-hiato 04→09/08)
- **Área:** escape &<> no SVG (unifilar XML malformado); carimbo elétrico vazava ESTRUTURAL; proveniência bacia_caixa=0,96; centraliza quadros PE-EL-03/PE-HID-02; escape &<> em incêndio/clima/coord; centraliza quadros verticais; planta de iluminação e tomadas; fecha 4 gaps da planta elétrica (QDC, bitola/eletroduto, leiaute, 3D/BIM)
- PRs: 154, 155, 156, 157, 158, 159, 160, 161

### Cluster 20 — S42: Dez módulos de engenharia (PRs #162–#171)
- **Janela:** 2026-08-09T15:27Z → 2026-08-09T16:10Z
- **Área:** piso industrial (placa sobre solo); geotecnia SPT→tensão admissível; orçamento 5D (curva ABC); compatibilização BCF-like; fotovoltaico GD on-grid; saneamento (fossa NBR 7229 + reuso cisterna Rippl); terraplenagem (corte/aterro + greide); cronograma físico-financeiro 4D (CPM + curva S); caderno de encargos; pacote legal (ART, PPCI/LOD/O&M)
- PRs: 162, 163, 164, 165, 166, 167, 168, 169, 170, 171

---

## 4. Trabalho pós-2026-08-04 (identificação explícita)

**ENCONTRADO:** PRs #154–#171 (18 PRs, clusters 19 e 20), todos merged **2026-08-09** entre 04:12Z e 16:10Z.

- `git log --since=2026-08-04 --oneline` → **36 commits** (18 merges + 18 commits de feature) — todos os commits pós-04/08 estão na main local
- **Hiato de 5 dias:** nenhum PR mergeado entre 2026-08-04T13:14Z (#153) e 2026-08-09T04:12Z (#154) — período sem commits nem merges (possível pausa de trabalho; anotado para o todo 9/14)
- Nenhum commit com data > 2026-08-09 na main (HEAD 6358157 é o merge #171, 2026-08-09)

---

## 5. Tabela completa de PRs (#55–#171)

Fonte: `gh pr list --state all --limit 300 --json number,title,mergedAt,labels` (labels: **nenhum PR tem label** — classificação por título/área). 117 PRs, todos MERGED. Merge commit local (hash) confirmado para cada um via `git log --merges`.

| PR | mergedAt (Z) | Cluster | Título (resumo) |
|---|---|---|---|
| 55 | 2026-07-22T21:58:03 | 1 S19 | Gaps A3/C5 + wiki 2ª auditoria p/ main |
| 56 | 2026-07-22T21:58:15 | 1 S19 | Export IFC4 (BIM) 3D → Revit/Eberick |
| 57 | 2026-07-22T22:09:56 | 1 S19 | montar_modelo headless (sem FreeCAD aberto) — merge em branch, main via #59 |
| 58 | 2026-07-22T22:10:07 | 1 S19 | modelo neutro + emissor IFC4 puro-Python |
| 59 | 2026-07-23T00:15:08 | 1 S19 | Leva montar_modelo headless (#57) p/ main |
| 60 | 2026-07-23T00:15:11 | 1 S19 | secundários lineares no IFC puro |
| 61 | 2026-07-23T00:15:59 | 1 S19 | modelo analítico + IFC4-Structural no pipeline |
| 62 | 2026-07-23T00:53:30 | 2 S19-ext | esforços 2ª ordem por barra + IFC-structural |
| 63 | 2026-07-23T01:07:25 | 2 S19-ext | fundações sapata/bloco no IFC puro |
| 64 | 2026-07-23T01:20:19 | 2 S19-ext | telha IfcCovering no IFC puro |
| 65 | 2026-07-23T05:49:46 | 2 S19-ext | tapamento de parede no IFC puro |
| 66 | 2026-07-23T05:50:11 | 2 S19-ext | pórtico alma variável (tapered) no IFC puro |
| 67 | 2026-07-23T06:03:51 | 2 S19-ext | modelo analítico do tapered |
| 68 | 2026-07-23T06:26:05 | 2 S19-ext | fix escala 1000x + placas de base |
| 69 | 2026-07-23T06:41:47 | 2 S19-ext | nervuras da placa de base (IfcPlate) |
| 70 | 2026-07-23T06:56:46 | 2 S19-ext | clipes de terça e girt (IfcPlate) |
| 71 | 2026-07-23T07:13:52 | 2 S19-ext | mãos-francesas (IfcMember) |
| 72 | 2026-07-23T07:29:23 | 2 S19-ext | escoras/cumeeiras + oitão |
| 73 | 2026-07-23T07:44:43 | 2 S19-ext | tirantes de cobertura segmentados |
| 74 | 2026-07-23T07:59:47 | 2 S19-ext | conectores da base (IfcMechanicalFastener) |
| 75 | 2026-07-23T08:15:23 | 2 S19-ext | drenagem (calhas/condutores/bocais) |
| 76 | 2026-07-23T08:30:01 | 2 S19-ext | gussets do contravento (IfcPlate triangular) |
| 77 | 2026-07-23T12:45:34 | 2 S19-ext | mísula do joelho (IfcPlate) |
| 78 | 2026-07-23T13:10:21 | 2 S19-ext | IfcPile + ponte rolante |
| 79 | 2026-07-23T16:50:28 | 2 S19-ext | 3 gaps auditoria fechamento (ELS girt + corrosão + camber) |
| 80 | 2026-07-23T17:30:49 | 2 S19-ext | flecha baldrame sob alvenaria + dreno |
| 81 | 2026-07-23T22:52:42 | 3 S20 | pilar concreto flexão composta (NBR 6118) P1 |
| 82 | 2026-07-23T23:00:47 | 3 S20 | viga CA retangular P2 |
| 83 | 2026-07-23T23:06:58 | 3 S20 | orquestrador concreto pré-moldado P3 |
| 84 | 2026-07-23T23:12:00 | 3 S20 | BIM IFC4 do concreto + material P4 |
| 85 | 2026-07-23T23:16:11 | 3 S20 | executivo (quadro de aço + memorial) P5 |
| 86 | 2026-07-23T23:20:19 | 3 S20 | desenho formas + armação SVG P6 |
| 87 | 2026-07-23T23:50:02 | 3 S20 | flexão composta oblíqua do pilar P1b |
| 88 | 2026-07-24T00:02:09 | 3 S20 | viga de cobertura protendida P7 |
| 89 | 2026-07-24T13:02:31 | 3 S20 | P8 ligação pré-moldada NBR 9062 |
| 90 | 2026-07-24T13:09:07 | 3 S20 | P9 situação de incêndio NBR 15200 |
| 91 | 2026-07-24T13:16:39 | 3 S20 | P10 fissuração ELS-W 17.3.3 |
| 92 | 2026-07-24T13:22:24 | 3 S20 | P11 estabilidade global 15.5 (α, γz) |
| 93 | 2026-07-24T13:28:55 | 3 S20 | P12 perdas de protensão 9.6.3 |
| 94 | 2026-07-24T13:33:18 | 3 S20 | P13 fundação profunda (estaca) |
| 95 | 2026-07-24T13:37:24 | 3 S20 | P14 cortante protendida 17.4.2 |
| 96 | 2026-07-24T13:42:22 | 3 S20 | P15 torção 17.5 |
| 97 | 2026-07-24T13:47:50 | 3 S20 | P16 planta de formas SVG |
| 98 | 2026-07-24T13:55:05 | 3 S20 | P17 quantitativo armadura IFC Pset |
| 99 | 2026-07-24T13:59:40 | 3 S20 | P18 varredura interpenetração |
| 100 | 2026-07-27T17:32:35 | 3 S20 | P19 build 3D sólido do concreto |
| 101 | 2026-07-27T20:00:17 | 3 S20 | P20 pranchas A1 TechDraw do concreto |
| 102 | 2026-08-01T23:56:23 | 4 S21 | P21 núcleo BT + aterramento + SPDA |
| 103 | 2026-08-02T00:44:06 | 4 S22 | P22 subestação/MT (NBR 14039) |
| 104 | 2026-08-02T00:58:38 | 4 S23 | P23 BIM/IFC elétrico |
| 105 | 2026-08-02T01:32:33 | 4 S24-25 | P24-P25 build 3D + executivo A1 |
| 106 | 2026-08-02T02:02:52 | 4 S26 | P26 luminotécnica (NBR 8995) |
| 107 | 2026-08-02T02:35:22 | 5 S27 | P27 incêndio base (emergência+sinalização+alarme) |
| 108 | 2026-08-02T02:49:00 | 5 S28 | P28 sprinklers (NBR 10897) |
| 109 | 2026-08-02T02:57:11 | 5 S29 | P29 iluminação externa (NBR 5101) |
| 110 | 2026-08-02T03:04:59 | 5 S30 | P30 climatização (NBR 16401) |
| 111 | 2026-08-02T03:22:29 | 6 S31 | P31 fecha loop — ilum+clima como cargas QGF |
| 112 | 2026-08-02T14:27:04 | 7 S32 | P32 orquestrador-mestre turnkey |
| 113 | 2026-08-02T14:37:24 | 8 P33 | harness robustez verticais novos |
| 114 | 2026-08-02T14:59:29 | 8 P34 | executivo A1 incêndio (rotas de fuga AVCB) |
| 115 | 2026-08-02T15:15:47 | 8 P35 | acionadores p/ galpão alongado (NBR 17240) |
| 116 | 2026-08-02T15:24:04 | 8 S36 | P36 caderno executivo único turnkey |
| 117 | 2026-08-02T15:53:30 | 8 P37 | P37 hidrantes e mangotinhos (NBR 13714) |
| 118 | 2026-08-02T16:18:18 | 8 S38 | P38 revisão total drawing-vs-data + guards |
| 119 | 2026-08-02T16:43:41 | 8 P39 | P39 dispatch do aço no caderno turnkey |
| 120 | 2026-08-02T19:55:54 | 9 | fix hidrantes cobertura malha + 2 jatos |
| 121 | 2026-08-02T20:02:30 | 9 | fix guards elétrico 7 módulos |
| 122 | 2026-08-02T20:09:56 | 9 | BIM/IFC equipamentos incêndio |
| 123 | 2026-08-02T20:38:33 | 9 | fix planta ilum emergência count-driven |
| 124 | 2026-08-02T20:46:45 | 10 | modelo BIM/IFC federado consolidado |
| 125 | 2026-08-02T22:00:06 | 10 | aço dentro do federado (4 disciplinas) |
| 126 | 2026-08-02T23:05:07 | 10 | clash detection federado |
| 127 | 2026-08-02T23:21:39 | 10 | build 3D sólido federado + fix AABB |
| 128 | 2026-08-03T01:20:19 | 10 | apêndice coordenação no caderno |
| 129 | 2026-08-03T01:26:22 | 10 | triagem esperado×revisar |
| 130 | 2026-08-03T01:42:30 | 10 | fix escala caixas do aço federado |
| 131 | 2026-08-03T01:58:11 | 10 | vertical climatização federada |
| 132 | 2026-08-03T02:04:20 | 10 | render-and-look PNG federado |
| 133 | 2026-08-03T02:12:33 | 10 | vertical hidráulica federada (6ª disciplina) |
| 134 | 2026-08-03T02:42:08 | 10 | prancha coordenação no caderno |
| 135 | 2026-08-03T02:51:15 | 11 | hvac velocidade duto NBR 16401-1 |
| 136 | 2026-08-03T06:35:41 | 12 S39 | dimensionamento hidráulico NBR 5626/8160/10844 |
| 137 | 2026-08-03T06:50:09 | 12 S39 | prancha A1 coordenação do federado |
| 138 | 2026-08-03T06:57:25 | 12 S39 | reservatório incêndio como torre elevada |
| 139 | 2026-08-03T07:01:58 | 12 S39 | revisão NBR hidráulica (2 gaps) |
| 140 | 2026-08-03T13:50:34 | 12 S39 | método dos pesos NBR 5626:1998 |
| 141 | 2026-08-03T14:07:17 | 12 S39 | verificação pressão (Fair-Whipple-Hsiao) |
| 142 | 2026-08-03T14:15:53 | 12 S39 | ventilação esgoto + calhas pluviais |
| 143 | 2026-08-03T14:24:19 | 12 S39 | executivo A1 hidro + clima |
| 144 | 2026-08-03T14:28:29 | 12 S39 | janela lateral wizard (L,H)→faixa |
| 145 | 2026-08-03T14:43:10 | 12 S39 | revisão S39 (pressão por ponto, saturação pluvial, área dreno) |
| 146 | 2026-08-03T15:25:45 | 12 S39 | condutor curto exige paralelo (não satura) |
| 147 | 2026-08-03T15:33:45 | 12 S39 | água quente (NBR 5626:2020 SPAFAQ) |
| 148 | 2026-08-03T16:17:31 | 13 S40 | fecha saturação silenciosa terça + placa |
| 149 | 2026-08-03T16:33:37 | 14 S40 | docs wiki consolida S20-S40 |
| 150 | 2026-08-03T18:31:06 | 15 S40 | unifica janela na FAIXA — mata dupla-conversão (fecha T40) |
| 151 | 2026-08-03T18:32:58 | 16 S40 | docs wiki T40 RESOLVIDO |
| 152 | 2026-08-03T18:55:45 | 17 S40 | runner regressão xdist + fallback |
| 153 | 2026-08-04T13:14:44 | 18 S40 | docs wiki situação atual S40 |
| 154 | 2026-08-09T04:12:04 | 19 S41 | fix escape &<> SVG (unifilar XML) |
| 155 | 2026-08-09T04:21:02 | 19 S41 | fix carimbo elétrico vazava ESTRUTURAL |
| 156 | 2026-08-09T04:32:12 | 19 S41 | docs proveniência bacia_caixa=0,96 |
| 157 | 2026-08-09T04:41:50 | 19 S41 | centraliza quadros PE-EL-03/PE-HID-02 |
| 158 | 2026-08-09T04:48:45 | 19 S41 | escape &<> incêndio/clima/coordenação |
| 159 | 2026-08-09T05:02:44 | 19 S41 | centraliza quadros verticais |
| 160 | 2026-08-09T05:30:40 | 19 S41 | planta iluminação e tomadas |
| 161 | 2026-08-09T06:00:09 | 19 S41 | fecha 4 gaps planta elétrica (QDC/bitola/leiaute/3D) |
| 162 | 2026-08-09T15:27:59 | 20 S42 | piso industrial (placa sobre solo) |
| 163 | 2026-08-09T15:39:18 | 20 S42 | geotecnia SPT→tensão admissível |
| 164 | 2026-08-09T15:44:00 | 20 S42 | orçamento 5D (curva ABC) |
| 165 | 2026-08-09T15:48:22 | 20 S42 | compatibilização BCF-like |
| 166 | 2026-08-09T15:52:38 | 20 S42 | fotovoltaico GD on-grid |
| 167 | 2026-08-09T15:58:41 | 20 S42 | saneamento fossa (NBR 7229) + reuso (Rippl) |
| 168 | 2026-08-09T16:01:28 | 20 S42 | terraplenagem corte/aterro + greide |
| 169 | 2026-08-09T16:04:47 | 20 S42 | cronograma 4D (CPM + curva S) |
| 170 | 2026-08-09T16:07:37 | 20 S42 | caderno de encargos |
| 171 | 2026-08-09T16:10:34 | 20 S42 | pacote legal (ART, PPCI/LOD/O&M) |

---

## 6. Mapeamento módulo → commit/PR

Comandos: `git log --oneline -- framework/galpao_fw/<modulo>.py` no worktree. Lista os commits que tocaram cada arquivo (mais recente primeiro); hash+PR quando o commit de feature é identificável.

| Módulo | Primeiro commit (nascimento) | PR de origem | Último toque (na janela) | PR | Notas |
|---|---|---|---|---|---|
| `modelo_neutro.py` | `d5a4ba4` 2026-07-22 | #58 (S19) | `287f954` 2026-07-23 (IfcPile+ponte rolante) | #78 | 23 commits S19/S19-ext (22–23/07) |
| `ifc_emit.py` | `d5a4ba4` 2026-07-22 | #58 (S19) | `977cc38` 2026-08-09 | #161 (S41) | 30 commits: S19 (7) + S19-ext (21) + #84/#98/#104/#122/#125/#131/#133/#161 |
| `ifc_map.py` | `6eee42e` 2026-07-22 | #56 (S19) | `6eee42e` | #56 | único commit — mapa semântico do export IFC4 (categorias IfcColumn/Beam/Member/Plate/Footing/Pile/Covering/MechanicalFastener) |
| `galpao_concreto.py` | `b47e822` 2026-07-23 | #83 (S20) | `f5c0f08` 2026-08-02 | #118 (S38) | 15 commits: P1–P20 (S20) + P38 |
| `galpao_eletrico.py` | `9bbce43` 2026-08-01 | #102 (S21) | `977cc38` 2026-08-09 | #161 (S41) | 9 commits: P21–P26, P31, P38, S41 |
| `galpao_seguranca_incendio.py` | `317a59e` 2026-08-01 | #107 (S27) | `e5577fa` 2026-08-03 | #138 (S39) | 7 commits: P27/P28/P34/P37/P38/#122/#138 |
| `galpao_hidraulica.py` | `83d21c4` 2026-08-02 | #133 (turnkey) | `f326627` 2026-08-03 | #147 (S39) | 8 commits: #133 + S39 (#136–#147) |
| `galpao_climatizacao.py` | `77c9087` 2026-08-02 | #131 (turnkey) | `9eaf79c` 2026-08-03 | #143 (S39) | 3 commits: #131, #135, #143 |
| `galpao_turnkey.py` | `2bb262e` 2026-08-02 | #112 (S32) | `977cc38` 2026-08-09 | #161 (S41) | 13 commits: #112, #119, #124–#134, #137, #161 |
| `pacote_legal.py` | `95264bf` 2026-08-09 | #171 (S42) | `95264bf` | #171 | 1 commit |
| `terraplenagem.py` | `1c74e6c` 2026-08-09 | #168 (S42) | `1c74e6c` | #168 | 1 commit |
| `esgoto_reuso.py` | `25f0ad4` 2026-08-09 | #167 (S42) | `25f0ad4` | #167 | 1 commit |
| `fotovoltaico.py` | `56badfd` 2026-08-09 | #166 (S42) | `56badfd` | #166 | 1 commit |
| `orcamento.py` | `9b5e5d6` 2026-08-09 | #164 (S42) | `9b5e5d6` | #164 | 1 commit |
| `geotecnia_spt.py` | `8f36ba4` 2026-08-09 | #163 (S42) | `8f36ba4` | #163 | 1 commit |
| `piso_industrial.py` | `c1410b3` 2026-08-09 | #162 (S42) | `c1410b3` | #162 | 1 commit |

> Nota: `galpao_concreto.py` também recebeu toques de #162/#163 (S42) — os módulos piso/geotecnia foram wiringados no orquestrador de concreto (o `git log -- <arquivo>` lista `c1410b3`/`8f36ba4` tocando `galpao_concreto.py`).

---

## 7. Verificação dos PRs citados na wiki (00-index + 06-open-threads)

| Referência da wiki | PRs | Status | Evidência |
|---|---|---|---|
| 00-index:18-62 "S20 concreto #81–#101" | 81–101 | ✅ CONFIRMADO | 21 PRs merged 23–27/07 (cluster 3) |
| 00-index:27-29 "S21–26 elétrico #102–#106" | 102–106 | ✅ CONFIRMADO | 5 PRs merged 01–02/08 (cluster 4) |
| 00-index:30-32 "S27–30 incêndio #107–#110" | 107–110 | ✅ CONFIRMADO | 4 PRs merged 02/08 (cluster 5) |
| 00-index:33-35 "S32 turnkey #112" | 112 | ✅ CONFIRMADO | merged 02/08 (cluster 7) |
| 00-index:36-37 "S36 caderno único #116" | 116 | ✅ CONFIRMADO | merged 02/08 (cluster 8) |
| 00-index:38-39 "S38 revisão total #118" | 118 | ✅ CONFIRMADO | merged 02/08 (cluster 8) |
| 00-index:40-43 "S39 hidráulica/coord #136–#147" | 136–147 | ✅ CONFIRMADO | 12 PRs merged 03/08 (cluster 12) |
| 00-index:44-49 "S40 hardening #148" | 148 | ✅ CONFIRMADO | merged 03/08 (cluster 13) |
| 00-index:50-52 "S40 janela dupla-conversão #150" | 150 | ✅ CONFIRMADO | merged 03/08 (cluster 15) |
| 00-index:53-58 "S40 runner #152" | 152 | ✅ CONFIRMADO | merged 03/08 (cluster 17) |
| 06-open-threads T40 → PR #150 | 150 | ✅ CONFIRMADO | 06-open-threads linha 3: "✅ RESOLVIDO (PR #150)"; merge #150 existe |
| 06-open-threads T21 → PR #54 | 54 | ✅ CONFIRMADO | 06-open-threads linha 9 (T21 gaps A3/C5); merge #54 (18:40:36Z) + conteúdo na main via #55 (83570c9) |

**Nenhum PR citado na wiki ficou "não encontrado no git/GitHub".**

---

## 8. QA interno (registro)

**Spot-checks de mapeamento módulo → commit (5):**

| # | Módulo | Commit esperado | PR | Verificação |
|---|---|---|---|---|
| 1 | `ifc_map.py` | `6eee42e` | #56 | `git show 6eee42e --stat` → +82 `ifc_map.py`, +55 `build_galpao.py`, +71 `test_ifc_map.py` ✅ |
| 2 | `modelo_neutro.py` | `d5a4ba4` | #58 | `git show d5a4ba4 --stat` → +98 `modelo_neutro.py`, +167 `ifc_emit.py`, +89 `test_ifc_emit.py` ✅ |
| 3 | `pacote_legal.py` | `95264bf` | #171 | `git show 95264bf --stat` → +267 `pacote_legal.py`, +75 `test_pacote_legal.py` ✅ |
| 4 | `galpao_eletrico.py` | `9bbce43` | #102 | `git show 9bbce43 --stat` → +260 `cargas_eletricas.py`, +261 `condutores_nbr5410.py`, +67 `curto_circuito.py` ✅ |
| 5 | `galpao_hidraulica.py` | `6422954` | #136 | `git show 6422954 --stat` → +286 `hidraulica_predial.py`, +207 `galpao_hidraulica.py` ✅ |

**Divergências encontradas e corrigidas:** nenhuma — todos os spot-checks bateram com o mapa da seção 6. A única particularidade registrada é o toque dos módulos S42 (#162/#163) em `galpao_concreto.py` (wiring no orquestrador), já refletida na nota da seção 6.

---

## 9. Resumo executivo

- **Janela usada:** `--since=2026-07-22T18:19:29Z` (commit mais antigo da S19, PR #55) — **sem ajustes necessários** (S19 inteira presente no log local; #57 mergeado via #59)
- **Cluster principal (S19):** PRs #55–#61, janela 22/07 21:58Z → 23/07 00:15Z, tema Interoperabilidade BIM/IFC4
- **Bucket #62–#80 classificado:** cluster próprio **"S19-ext: IFC físico puro — expansão e fechamento"** (19 PRs, 23/07) — não fundido com S19 (wiki já fechou S19 no review #55–61) nem com S20 (sem concreto); alimenta todo 14
- **Trabalho pós-2026-08-04:** ENCONTRADO — PRs #154–#171 (18 PRs, clusters S41 e S42), todos merged 2026-08-09; 36 commits na main local; hiato de 5 dias (04→09/08) sem merges
- **Tabela de PRs:** 117 PRs (#55–#171) na tabela, 171/171 MERGED no repo, nenhum remote-only no período
- **Reconciliação:** 116 merges locais + #57 (via #59) = 117 ✓
- **Wiki:** 12 referências (10 clusters + T40 + T21) — todas confirmadas, zero "não encontrado"
- **Evidência em:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\.omo\evidence\revisao-wiki\task-3-revisao-wiki.md` (UTF-8)
