# Revisão — Console da ponte rolante (NBR 8800 + grupo de solda elástico)

Verificação da **ligação do console** da ponte rolante à coluna (a chapa/solda
que recebe a viga de rolamento excêntrica). Só existe quando há ponte. Compõe os
primitivos de solda de `ligacoes.py`; as cargas vêm de `ponte_rolante`.

Código: `console_ponte.py`. Criado 2026-07-09.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo. A conferir: o **grupo de solda
> elástico** (soma vetorial cisalhamento+flexão na linha de solda) é
> **mecânica/AISC, não item da NBR** (FLAG, análogo ao T-stub EN 1993 aceito no
> joelho); e o comprimento de solda `L` = altura da mísula (build 450 mm).

---

## 1. Método

Cargas de `ponte_rolante`: reação vertical máxima do trilho `Rv`, força
transversal `Ht`, excentricidade `ecc` (trilho→face da coluna) → momento
`M = Rv·ecc`.

1. **Grupo de solda elástico** (linha vertical de comprimento L, dois cordões):
   demanda por comprimento `f = √(f_v² + f_h² + f_b²)`, com `f_v = Rv/L`,
   `f_h = Ht/L`, `f_b = 6·M/L²` (módulo da linha `Sw = L²/6`). Capacidade por
   comprimento = `ligacoes.fw_rd_filete(perna, 1, fw)` (metal da solda 6.2.5).
   **Dimensiona** a perna do filete: menor perna-padrão (≥ mínimo Tab.9) cuja
   capacidade cobre a demanda (first-fit 6/8/10/12 mm); se nem 12 mm bastar,
   adota 12 e sinaliza (requer penetração/redesenho).
2. **Cisalhamento da chapa** (5.4): `V_Rd = 0,6·fy·(t·L)/γa1 ≥ Rv`.

Governa = maior utilização.

## 2. Selftest

Console t=16 mm, mísula L=450 mm, Rv=120 kN, Ht=12 kN, ecc=150 mm:
- Grupo elástico `f_dem` bate com `√(f_v²+f_h²+f_b²)` ✅
- Perna dimensionada = menor padrão que cobre a demanda ✅
- Cisalhamento da chapa `V_Rd = 0,6·fy·t·L/γa1` ✅
- Caso enorme (Rv=3000, ecc=600, t=6, L=120) → nem 12 mm basta → adota 12,
  **NÃO ATENDE** ✅
- `ecc=0` → `f_b=0` ✅

Caso real (galpão 20×15, ponte 50 kN): `M = 20,7 kN·m`, perna 6 mm,
util solda 0,69 → **ATENDE**.

**PASSED.**

## 3. FLAGs

- Grupo de solda elástico (mecânica/AISC) — o responsável confirma o método.
- `L` = altura de solda da mísula (build 450 mm) — confirmar comprimento efetivo.
- `Ht`/impacto e `ecc` vêm do módulo de ponte (fabricante/NBR 8400, A CONFIRMAR).
- fu da chapa = 400 MPa (MR250).
