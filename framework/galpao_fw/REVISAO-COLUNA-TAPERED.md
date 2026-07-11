# Revisão — Coluna de alma variável (tapered)

Conferência do sênior. Fecha o **Q1 do parecer da alma variável** (fase 6.b), que
ficou no backlog: estender a máquina tapered — hoje só no rafter/mísula — para a
**coluna** do pórtico. Fase 6.4. Criado 2026-07-11.

> **STATUS: A REVISAR (parecer 1 respondido).** Implementado sobre a máquina tapered
> já homologada ([ALMA-VARIAVEL](REVISAO-ALMA-VARIAVEL.md),
> [ALMA-VARIAVEL-INTEG](REVISAO-ALMA-VARIAVEL-INTEG.md)). Reusa
> `secao_tapered`/`props_I` sem alteração. Back-compat total: sem `h_col_base`, a
> coluna segue prismática (ref numérica intocada).

## Parecer sênior 1 — respostas

| Pt | Alegação | Veredito |
|---|---|---|
| 1 | FLT "seção mais funda + fórmula prismática" não tem respaldo / usar γ do DG25 | **IMPROCEDENTE.** NBR 8800 **Anexo J.4.2** manda **usar a seção de MAIOR altura** para λ/λp/λr (verbatim do PDF). O γ é do AISC DG25, **não normativo na NBR**. Além disso o código **já migrou** para o Anexo J na fase 6.6 ([FLT-MISULA](REVISAO-FLT-MISULA.md)): Cb racional §5.4.2.3a + demanda na seção de max M/Wx. Doc atualizado (§4). |
| 2 | Compressão global (`Nc,Rd` por flexão) omitida | **PROCEDENTE — corrigido.** A verificação por segmento usava `L=L_seg` (~0,75 m) → não capturava a flambagem global. Adicionada **compressão global por Anexo J.3** (seção de MENOR altura, comprimento total H). §4. |
| 3 | Teste de continuidade com tolerância 20% é absurdo | **PROCEDENTE — corrigido.** Comparava pontos-médios (proxy fraco). Reescrito para igualdade **estrita no nó** (`math.isclose rel_tol=1e-9`). §2. |
| 4a | Cortante da inclinação das mesas | **FLAG.** Flambagem por cisalhamento da alma **já** é verificada por segmento (`chk.verifica`, 3 domínios kv=5); a componente da inclinação das mesas (DG25) fica como refino. |
| 4b | Limite h/tw no joelho | **JÁ COBERTO.** `momento_resistente` **levanta ValueError** se `h/tw > λr` (alma esbelta) — a seção funda é barrada. |

## Escopo

Coluna com altura variando **linearmente da base (rasa) ao joelho (funda)**,
casando `h_joelho` do rafter no nó do joelho (continuidade da mesa/alma). Entra na
análise (rigidez por segmento no frame2d), na verificação (estados locais por
segmento + FLT member-level da coluna), no gate/mapper e no build 3D (loft).

## 1. Geração da seção (reuso)

`alma_variavel.secao_tapered(h_col_base, h_joelho, bf, tw, tf, nseg=NSEG)` — mesmo
gerador homologado do rafter (I duplamente simétrico, props no ponto médio de cada
segmento). Nada novo de método; só nova **origem/destino** das alturas.

## 2. Frame (galpao_portico)

- `_coluna_tapered()` — True sse `TAPERED` tem `h_col_base` (senão coluna
  prismática).
- `_secoes_coluna()` — seções **base→joelho** (base rasa no seg 0, joelho fundo no
  último). No `_frame()`, a coluna vira `_chain_var` (uma seção A/I por segmento)
  quando tapered; se há console, o trecho console→beiral usa a seção do topo
  (joelho, a coluna não afina acima do console).
- **Continuidade** (mne-3, corrigido pelo parecer pt.3): no nó do joelho ambas as
  cadeias (coluna base→joelho, rafter joelho→cumeeira) têm `h = h_joelho`, logo a
  inércia da seção do nó é **idêntica por construção**. `test_coluna_joelho_casa_rafter`
  extrapola a geometria linear de cada cadeia até a coordenada do nó e exige
  `math.isclose(I_col_node, I_raf_node, rel_tol=1e-9)` (antes: pontos-médios com
  tol 20%, proxy fraco apontado pelo sênior).

## 3. Envelope por segmento

`analyse()` devolve `coluna_segmentos`: envelope ELU de `M/N/V` **por elemento** da
coluna (só os `NSEG` elementos base→joelho; console/beiral fora) + seção local +
combinação governante — espelha `rafter_segmentos`. A **base não governa
necessariamente**: em pórtico de nó rígido o `M` pica no joelho (topo, seção
funda), mas `Wx` também é máximo ali; a verificação por segmento resolve qual
domina. `coluna_tapered: bool` no retorno.

## 4. Verificação (rodar_galpao, gate6)

Mesma lógica homologada do rafter (parecer 2 da alma variável):

- **Estados LOCAIS por segmento** (FLA/FLM/flexo-compressão): `check_nbr8800.verifica`
  com a seção local, esforços amplificados pelo **B2 do MAES** (2ª ordem) e `Lb→0`
  (neutraliza a FLT local — ela é fenômeno de trecho, não de fatia).
- **FLT de TRECHO (member-level) — NBR 8800 Anexo J** (via `flt_misula`, fase 6.6,
  [FLT-MISULA](REVISAO-FLT-MISULA.md)): λ/λp/λr da seção de **maior altura**
  (**J.4.2**), `Cb` por análise racional §5.4.2.3a (**J.4.1**) e demanda na seção de
  **maior tensão M/Wx** — não `M_max` cego. `Lb = params["Lb"]["col"]` (contrato de
  travamento). O fator γ (AISC DG25) **não é adotado** — não é normativo na NBR.
- **Compressão GLOBAL por flexão — NBR 8800 Anexo J.3** (parecer pt.2): a verificação
  por segmento usa `L = L_seg` e **não** captura a flambagem global ao longo dos `H`
  metros. Adicionada `Nc,Rd` pela seção de **menor altura** (base, J.3) com o
  comprimento do membro inteiro (`H = eave`, `K=1` no plano não-sway; o `B2` do MAES
  já amplifica o sway). `res["alma_variavel"].util_col_global`.
- **Cortante**: flambagem por cisalhamento da alma verificada por segmento
  (`chk.verifica`, 3 domínios, kv=5). [FLAG] componente da inclinação das mesas
  (alívio/agravo do cortante em alma variável, DG25) = refino não implementado.
- `res["alma_variavel"]` ganha `util_col_local_max`, `util_col_flt`,
  `util_col_global`, `cb_misula_col`, `interacao_max_col`, `h_col_base_mm`. Seção
  "COLUNA TAPERED" no `gate6-alma-variavel.txt` (inclui a linha "compressao GLOBAL
  (Anexo J.3 …)").

## 5. Gate + mapper (projeto_spec)

- Campo **opcional** `estrutura.tapered.h_col_base` (m). `validar()` **avisa** (não
  bloqueia) se `h_col_base ≥ h_joelho` (coluna não afina) ou `≤ 2·tf` (seção I
  inválida).
- `to_rodar_params` já passava o dict tapered inteiro (h_col_base propaga);
  `to_build_kwargs` inclui `h_col_base` em mm quando presente.

## 6. Build 3D (build_galpao, numpy-free)

`tapered_column(doc, p_base, p_topo, name)` — loft I base(h_col_base)→joelho(h_joelho)
via `_sweep_tapered` (mesmo do rafter). Coluna vira loft quando
`TAPERED_MODEL.h_col_base`; cai no `i_member` prismático se `h_col_base==h_joelho`.
Build 20×10 coluna tapered: **0 interferências**.

## 7. Não-regressão

Sem `h_col_base` → coluna prismática (teste `test_coluna_prismatica_sem_h_col_base`:
`|I_base − I_topo| < 1e-12` e `coluna_segmentos` vazio). Suítes prismático /
alma-var-só-rafter / tesoura inalteradas; smoke verde.

## Checklist de testes (`tests/test_fase64_coluna_tapered.py`)

| Teste | Cobre |
|---|---|
| `test_coluna_tapered_secao_variavel` | joelho > base·1.5 (rigidez cresce da base ao joelho) |
| `test_coluna_joelho_casa_rafter` | continuidade **estrita no nó** `isclose 1e-9` (mne-3, parecer pt.3) |
| `test_analyse_retorna_coluna_segmentos` | envelope + props por segmento |
| `test_coluna_prismatica_sem_h_col_base` | back-compat (mne-2) |
| `test_coluna_tapered_valida` / `test_h_col_base_maior_que_joelho_avisa` | gate + aviso |
| `test_mapper_passa_h_col_base` | mapper rodar (m) + build (mm) |
| `test_verificacao_coluna_por_segmento` | util local + FLT (Anexo J) + **compressão global J.3** |
| `test_compressao_global_menor_que_por_segmento` | compressão global bem definida (parecer pt.2) |
| `test_build_coluna_tapered` | loft 3D, 0 interferências (mne-5) |

11 testes verdes (10 fast + 1 build).
