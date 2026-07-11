# Revisão — Coluna de alma variável (tapered)

Conferência do sênior. Fecha o **Q1 do parecer da alma variável** (fase 6.b), que
ficou no backlog: estender a máquina tapered — hoje só no rafter/mísula — para a
**coluna** do pórtico. Fase 6.4. Criado 2026-07-11.

> **STATUS: A REVISAR (sênior).** Implementado sobre a máquina tapered já
> homologada ([ALMA-VARIAVEL](REVISAO-ALMA-VARIAVEL.md),
> [ALMA-VARIAVEL-INTEG](REVISAO-ALMA-VARIAVEL-INTEG.md)). Reusa
> `secao_tapered`/`props_I` sem alteração. Back-compat total: sem `h_col_base`, a
> coluna segue prismática (ref numérica intocada).

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
- **Continuidade** (mne-3): a seção do topo da coluna (joelho) casa a seção da base
  do rafter — teste `test_coluna_joelho_casa_rafter` exige `|I_col_topo −
  I_raf_base| / I_raf_base < 20%` (diferença só pelo ponto-médio do segmento).

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
- **FLT de TRECHO (member-level)**: uma vez, com a **seção mais funda da coluna** (o
  joelho, conservador — AISC DG25 / NBR 8800 Anexo H) e `Lb = params["Lb"]["col"]`
  (contrato de travamento: mesa externa pela longarina de fechamento, mesa interna
  pela mão-francesa).
- `res["alma_variavel"]` ganha `util_col_local_max`, `util_col_flt`,
  `interacao_max_col`, `h_col_base_mm`. Seção "COLUNA TAPERED" no `gate6-alma-variavel.txt`.

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
| `test_coluna_joelho_casa_rafter` | continuidade no nó (mne-3) |
| `test_analyse_retorna_coluna_segmentos` | envelope + props por segmento |
| `test_coluna_prismatica_sem_h_col_base` | back-compat (mne-2) |
| `test_coluna_tapered_valida` / `test_h_col_base_maior_que_joelho_avisa` | gate + aviso |
| `test_mapper_passa_h_col_base` | mapper rodar (m) + build (mm) |
| `test_verificacao_coluna_por_segmento` | util local + FLT member-level da coluna |
| `test_build_coluna_tapered` | loft 3D, 0 interferências (mne-5) |

9 testes verdes (8 fast + 1 build).
