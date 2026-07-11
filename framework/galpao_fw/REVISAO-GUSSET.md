# Revisão — Gusset de contraventamento (NBR 8800 + Whitmore)

Verificação da **chapa de gusset** dos nós de contraventamento (onde a diagonal
tracionada se liga ao pórtico/coluna). Não reinventa fórmula: **compõe os
primitivos já homologados** de `ligacoes.py` + a compressão de `check_nbr8800`.

Código: `gusset_ligacao.py`. Criado 2026-07-09.

> **STATUS: ✅ HOMOLOGADO** (2026-07-10) — parecer 1: 4 correções conceituais
> aplicadas (§4/§5). Parecer 2: aprovado com ressalva **só de documentação**
> ("não são necessárias novas alterações lógicas") — selftest do markdown
> reescrito p/ o caso real Ø20 (bw=135,5 / Nt,Rd=369,5), congruente com o código.
> A largura de **Whitmore (30°)** permanece FLAG (convenção AISC/Thornton, não é
> item da NBR; análogo ao T-stub EN 1993 já aceito no joelho).

## PARECER SÊNIOR 1 (matemática ✅ / conceito ❌→corrigido)

> Matemática do selftest **irretocável** (MR250 fy250/fu400, E70XX fEXX485,
> γa1=1,10, γw2=1,35): Whitmore bw=115,47 mm → Nt,Rd=314,91 kN; solda perna 5 mm
> L=300 mm → Fw,Rd=228,60 kN. **Aprovado**. Conceituação exigiu 4 ajustes:

1. **Lc ≠ comprimento de flambagem.** Lc (espraiamento 30°) é o comprimento da
   ligação; o comprimento de flambagem de Thornton é a distância LIVRE do fim da
   ligação à face do apoio. Desacoplar.
2. **w0=0 inviável p/ barra redonda.** Ponto único = singularidade. Barra
   ranhurada/soldada → w0 = diâmetro da barra.
3. **Faltou ruptura da seção líquida** (5.2.3): Nt,Rd=Ae·fu/γa2, subtraindo furos
   da largura de Whitmore, quando parafusada.
4. **K de flambagem = 0,65** (2 bordas, nó de canto, AISC DG29); 1,2 em bandeira.

## 5. Correções aplicadas (2026-07-10)

| # parecer | Mudança no `gusset_ligacao.py` |
|---|---|
| 1 | `L_livre` separado de `Lc`; `Kl = K·L_livre` (default L_livre=Lc, conservador). `_compressao_whitmore` doc explicita Thornton. Teste: `L_livre` maior → χ menor. |
| 2 | `d_barra` vira `w0` quando `w0` omitido (2 soldas laterais, não ponto). Teste: w0=0,020 p/ Ø20. |
| 3 | `_ruptura_whitmore` (5.2.3): `An=(bw−n_furos_transv·dh)·t`, `Ae=Ct·An`, `Nt,Rd=Ae·fu/γa2`; `dh` reusa `ligacoes._diam_furo` (Tab.12). Entra junto do block shear (parafusado). |
| 4 | `K_DUAS_BORDAS=0,65` / `K_UMA_BORDA=1,2`; default 0,65. Teste: `Kl=0,65·L_livre`. |

Selftest **PASSED** após correções (todos os estados + guardas).

---

## 1. Método (estados-limite, ABNT NBR 8800:2008)

Esforço = tração da diagonal de contravento (`contraventamento.n_diagonal`,
barra Ø20 pré-tensionada). Geometria do gusset = default do `build_galpao`
(`_gusset_tri`: L=150 mm, t=12 mm). Estados verificados:

1. **Tração na largura de Whitmore** (5.2.2): `bw = w0 + 2·Lc·tan30°`
   (w0=0 p/ barra redonda), `Ag = bw·t`, `Nt,Rd = Ag·fy/γa1`.
2. **Compressão/flambagem da faixa de Whitmore** (5.3.3): só quando a barra pode
   comprimir — contravento Ø20 pré-tensionado é **tração-only**, então este
   estado entra **flagado** (`r = t/√12`, `λ0 = (Kl/r)/π·√(fy/E)`,
   `χ = chi_compressao(λ0)`, `Nc,Rd = χ·Ag·fy/γa1` — reusa `check_nbr8800`).
3. **Solda de filete gusset→estrutura** (6.2.5): reusa `ligacoes.solda`; perna
   mínima por Tab.9 (`ligacoes.solda_filete_minimo`). Lsolda = 2·L (dois lados).
4. **Rasgamento em bloco** (6.5.6): reusa `ligacoes.block_shear_linha` — só
   quando a ligação da barra ao gusset for **parafusada**.

Governa = maior utilização entre os estados presentes.

## 2. Selftest

Gusset t=12 mm, barra redonda **Ø20 soldada** (w0 = d_barra = 20 mm, parecer 2),
Lc=100 mm, tração 50 kN:
- Whitmore `bw = w0 + 2·Lc·tan30° = 20 + 115,47 = 135,47 mm`
- Tração escoam. `Ag = 135,47·12 = 1625,6 mm²`; `Nt,Rd = Ag·fy/γa1 = 369,46 kN`
  (util 0,14) ✅
- Solda filete perna 5 mm (Tab.9), L=300 mm: `Fw,Rd = 228,6 kN` (util 0,22) ✅ → **governa**
- Compressão (habilitada, tração_only=False): `Kl = 0,65·L_livre`, `0 < χ ≤ 1` ✅
- Block shear + ruptura líquida (parafusado): batem com `ligacoes` (dh Tab.12);
  `Ct = 1,0` (shear-lag já coberto pelo espraiamento 30° de Whitmore) ✅
- Gusset 3 mm sob 5000 kN → **NÃO ATENDE** (guarda de reprovação) ✅

Nota (w0=0, chapa plana): o mesmo gusset com transferência plana daria
`bw = 115,5 mm` / `Nt,Rd = 314,9 kN` — número da iteração anterior, agora
substituído pelo caso real de barra redonda.

**PASSED.**

## 3. FLAGs

- Ângulo de Whitmore 30° (convenção AISC; o responsável confirma).
- ~~`Kl` de flambagem (default 0,6·Lc)~~ **resolvido parecer 1**: `Kl=K·L_livre`,
  K=0,65 (2 bordas), `L_livre` desacoplado de `Lc` (Thornton). L_livre real do
  nó a confirmar (default = Lc, conservador).
- Percurso do bloco de falha (quando parafusado) — herdado de `block_shear_linha`.
- fu do gusset = 400 MPa (MR250); confirmar aço da chapa.
- Integração: contravento é barra Ø20 **soldada** (w0 = d_barra = Ø20; ruptura
  líquida não aplica — sem furos). Ruptura líquida só entra em nó parafusado.
