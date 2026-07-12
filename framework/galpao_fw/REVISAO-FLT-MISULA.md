# Revisão — FLT de mísula por NBR 8800 Anexo J (refino tapered)

Conferência do sênior. Fecha o backlog **"fator γ de mísula"** da fase 6.b, mas
**corrigindo o framing**: a NBR 8800 **não usa fator γ** (isso é AISC Design Guide
25). O caminho normativo é o **Anexo J** (barras de seção variável). Fase 6.6.
Criado 2026-07-11.

> **STATUS: ✅ HOMOLOGADO** (2026-07-11). Parecer aprovou **todas** as cláusulas
> (J.1, J.4.2, J.4.1, §5.4.2.3a): *"O script está correto em sua proposta de
> engenharia. A transição para o Anexo J refina o dimensionamento."* Confirmou que
> o γ do AISC DG25 é estranho à NBR e sua exclusão evita erro de método. **Nota
> técnica verificada:** `h_m`/`Wx` de cada segmento vêm do mesmo `props_I(h)`
> (consistentes); `h_secao_flt` = seção de maior altura (J.4.2), `secao_critica` =
> max `M/Wx` (J.4.1) — distintas por projeto, ambas corretas.
>
> Substitui o método conservador da FLT de trecho tapered (seção mais funda +
> `Cb=1,0` + `M_max` cego) pelo método do **Anexo J**. Base verbatim do PDF.

## Por que não "fator γ"

O parecer da fase 6.b listou "fator γ de mísula (AISC DG25)" como refino. Ao ler a
norma, o γ **não é normativo na NBR 8800** — é do AISC DG25. A NBR trata mísula no
**Anexo J**, com prescrições próprias. Adotar o γ seria erro de método
(Ask/Zero-erro). Implementado o **Anexo J**; o γ fica registrado como alternativa
**não adotada**.

## Base normativa (NBR 8800:2008, Anexo J + §5.4.2.3a)

| Cláusula | Prescrição |
|---|---|
| **J.1** | Aplica-se a I/H/caixão com 2 eixos de simetria; mesas de seção constante entre travamentos; alma variando linearmente. ✔ (mísula duplo-simétrica) |
| **J.4.2** | λ, λp, λr (qualquer estado-limite) da seção de **MAIOR altura**. |
| **J.4.1** | FLT (§5.4): `M_Rd,FLT ≥ M_Sd` na seção de **maior tensão de compressão nas mesas**; `Cb` por análise racional (ou 1,0). |
| **§5.4.2.3a** | `Cb = 12,5·Mmax/(2,5·Mmax + 3·MA + 4·MB + 3·MC)·Rm ≤ 3,0`; `Rm=1,0` (duplo-simétrica); `MA/MB/MC` a 1/4, 1/2, 3/4 de `Lb`. |
| **§5.4.2.3b** | Trecho em balanço → `Cb = 1,0`. |
| **§5.4.2.2** | Teto `M_Rd ≤ 1,50·W·fy/γa1` (já em `check_nbr8800`). |
| **J.3 / J.2** | Compressão/tração pela seção de **menor** altura (fora do escopo desta FLT). |

## 1. Módulo `flt_misula.py`

- `cb_momento(Ms, balanco=False)` → `Cb` §5.4.2.3a (Rm=1,0, teto 3,0; balanço→1,0).
- `flt_misula(segmentos, fy, Lb, cb=None, balanco=False)`:
  - **J.4.2**: `momento_resistente` com a **seção mais funda** (maior altura).
  - **J.4.1**: `Cb` racional do diagrama de M do trecho; demanda na seção de
    **max `M/Wx`** (equivalente `max(σ)·Wx_deep`), não `M_max`.
  - retorna `util`, `Cb`, `M_Rd`, `secao_critica`, `h_secao_flt`.
- `_selftest`.

## 2. Integração (rodar_galpao)

FLT de trecho da **rafter** e da **coluna** tapered passam a chamar `flt_misula`
(antes: `momento_resistente(deep, Cb=1,0)` + `M_max`). Dois regimes de `Lb`
(gravidade=terças / sucção=mãos-francesas). O `B2` do MAES amplifica `M`. Gate cita
o **Anexo J** e o `Cb`; `res["alma_variavel"]` ganha `cb_misula_raf`,
`cb_misula_col`, `flt_secao_critica`. Estados locais por segmento **inalterados**.

**Efeito medido** (ref 10 m, mísula 600→300): `Cb=1,121` (gradiente suave do
pórtico raso), FLT `util=0,67`, seção crítica **7** (cumeeira, onde `M/W` pica —
coerente com a tese do parecer 6.b de que o joelho não governa). Onde `Lb < Lp`, a
FLT já está no platô plástico (`Mn=Mpl`) e o `Cb` não altera nada — o refino só
afrouxa quando `Lb` está no regime inelástico (`Lp < Lb < Lr`).

## 3. Não-regressão

Contrato da fase 6.b preservado: campos `util_flt_trecho`/`util_local_max`, headers
"ESTADOS LOCAIS POR SEGMENTO"/"FLT DE TRECHO", `governa_joelho` — todos mantidos.
Prismático intocado (a mudança só afeta o ramo tapered). Suítes 6.b + 6.4 verdes;
smoke 7/7.

## Checklist de testes (`tests/test_fase66_flt_misula.py`)

| Teste | Cobre |
|---|---|
| `test_cb_momento_uniforme` | momento uniforme → `Cb=1,0` |
| `test_cb_momento_gradiente` | gradiente → `Cb>1` |
| `test_cb_teto_3` | teto `Cb≤3,0` (mne-3) |
| `test_flt_misula_usa_secao_maior_altura` | J.4.2 (mne-2) |
| `test_flt_misula_cb_reduz_util` | `Cb>1` reduz util / eleva `M_Rd` |
| `test_flt_misula_demanda_max_sigma` | demanda na seção de max `M/Wx` (J.4.1, mne-4) |
| `test_selftest_roda` | selftest |
| `test_rodar_flt_misula_cita_anexo_j` | integração rafter (gate cita Anexo J) |
| `test_rodar_coluna_tapered_cb` | integração coluna (`cb_misula_col`) |

9 testes. Não-regressão: 6.b + 6.4 (25/25 fast juntos), smoke 7/7.
