# Revisão — Gusset de contraventamento (NBR 8800 + Whitmore)

Verificação da **chapa de gusset** dos nós de contraventamento (onde a diagonal
tracionada se liga ao pórtico/coluna). Não reinventa fórmula: **compõe os
primitivos já homologados** de `ligacoes.py` + a compressão de `check_nbr8800`.

Código: `gusset_ligacao.py`. Criado 2026-07-09.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo. A conferir: a premissa da
> **largura de Whitmore (30°)** — convenção AISC/Thornton, **não é item da NBR**
> (documentada como FLAG, análogo ao T-stub EN 1993 já aceito no joelho) — e o
> comprimento de flambagem `Kl` da faixa (default 0,6·Lc).

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

Gusset t=12 mm, Ø20, Lc=100 mm, tração 50 kN:
- Whitmore `bw = 115,5 mm`; `Nt,Rd = 314,9 kN` (util 0,16) ✅
- Solda filete perna 5 mm (Tab.9), L=300 mm: `Fw,Rd = 228,6 kN` (util 0,22) ✅
- Compressão (habilitada): `0 < χ ≤ 1` ✅
- Block shear parafusado: bate com `ligacoes.block_shear_linha` ✅
- Gusset 3 mm sob 5000 kN → **NÃO ATENDE** (guarda de reprovação) ✅

Caso real (galpão 20×10, nó de parede): `bw = 173 mm`, tração util 0,10, solda
util 0,20 → governa solda, **ATENDE**.

**PASSED.**

## 3. FLAGs

- Ângulo de Whitmore 30° (convenção AISC; o responsável confirma).
- `Kl` de flambagem da faixa (default 0,6·Lc) — só relevante se compressão.
- Percurso do bloco de falha (quando parafusado) — herdado de `block_shear_linha`.
- fu do gusset = 400 MPa (MR250); confirmar aço da chapa.
