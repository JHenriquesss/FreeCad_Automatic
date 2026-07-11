# Revisão — Console da ponte rolante (NBR 8800 + grupo de solda elástico)

Verificação da **ligação do console** da ponte rolante à coluna (a chapa/solda
que recebe a viga de rolamento excêntrica). Só existe quando há ponte. Compõe os
primitivos de solda de `ligacoes.py`; as cargas vêm de `ponte_rolante`.

Código: `console_ponte.py`. Criado 2026-07-09.

> **STATUS: 🔁 PARECER 1 (REPROVADO) ATENDIDO — REVER** — sênior reprovou a
> versão anterior por **erros de segurança** no grupo de solda (§4). Correções
> aplicadas (§5): SRSS de colineares → soma algébrica; 2 cordões (A_w=2L,
> Sw=L²/3); excentricidade de Ht; e **flexão da chapa em balanço** (faltava). O
> grupo de solda elástico permanece FLAG (mecânica/AISC, não é item da NBR;
> análogo ao T-stub EN 1993 aceito no joelho). **A geometria/direção assumida
> (§5, nota) precisa do aval final do sênior.**

---

## PARECER SÊNIOR 1 — 🛑 REPROVADO (erros de segurança) → corrigido

1. **SRSS indevido de componentes colineares.** `f=√(f_v²+f_h²+f_b²)` supõe as 3
   ortogonais; as componentes no mesmo eixo horizontal devem somar
   **algebricamente** antes do SRSS. SRSS de colineares **subestima** a
   resultante → inseguro.
2. **1 cordão × 2 cordões.** `fw_rd_filete` dá capacidade de **um** filete; com 2
   cordões a demanda usa A_w=2L e Sw=L²/3 (`f_v=Rv/2L`, `f_b=3M/L²`). A versão
   antiga (÷L) superdimensionava 2×.
3. **Momento de Ht omitido.** Ht atua no topo do trilho, com braço até o
   centroide da solda → `Mz=Ht·(L/2+h_trilho)`; adiciona tensão horizontal.
4. **Chapa só verificada ao cisalhamento.** Console é **viga em balanço**: falta
   a **flexão na raiz** `M_Sd=Rv·ecc` vs `M_Rd`, e FLAG de flambagem local.
5. **Selftest incongruente** (M=18 vs texto 20,7 kN·m) — rastreabilidade.

## 5. Correções aplicadas (2026-07-11)

Núcleo reescrito. Direções (chapa no plano de carga; **z** vertical = direção do
cordão; **x** horizontal):

| componente | fórmula | eixo |
|---|---|---|
| f_v (cisalh. vertical direto) | `Rv/(2L)` | z |
| f_h (cisalh. horiz. direto) | `Ht/(2L)` | x |
| f_bV (flexão Rv·ecc) | `3·M/L²`, `M=Rv·ecc` | x |
| f_bH (flexão de Ht) | `3·Mz/L²`, `Mz=Ht·(L/2+h_trilho)` | x |

**f_h, f_bV, f_bH colineares (x)** → soma algébrica; só então compõe com f_v (z):

```
f_dem = √( f_v² + (f_h + f_bV + f_bH)² )
```

| # parecer | mudança |
|---|---|
| 1 | soma algébrica dos colineares (x); SRSS só entre x e z. Teste: `f_dem > SRSS-de-3`. |
| 2 | 2 cordões: `A_w=2L`, `Sw=L²/3` → `f_v=Rv/2L`, `f_b=3M/L²`. Capacidade continua por 1 filete (`fw_rd_filete`), consistente. |
| 3 | `h_trilho` (default 0); `Mz=Ht·(L/2+h_trilho)`→`f_bH`. Teste: h_trilho↑ → f_dem↑. |
| 4 | novo estado `chapa_flexao`: `W=t·L²/6`, `M_Rd=W·fy/γa1`, `M_Sd=Rv·ecc`. Governante inclui as 3 verificações. |
| 5 | selftest com `Rv=120, ecc=0,15 → M=18 kN·m` explícito; `__main__` idem. |

> **Nota de geometria (aval do sênior):** assumido console = chapa **no plano de
> carga**, 2 cordões verticais, Rv excêntrico no plano e Ht transversal
> colinear com a flexão no plano. O parecer rotulou f_v+f_b como colineares
> (verticais); nesta implementação os colineares são os **horizontais**
> (f_h+f_bV+f_bH) — a diferença é só de convenção de eixo, e o resultado é
> **conservador** (soma algébrica). Confirmar o arranjo real do console (chapa
> simples × perfil T/I) antes da ART.

## 2. Selftest (atualizado)

Console t=16 mm, mísula L=450 mm, Rv=120 kN, Ht=12 kN, ecc=150 mm (**M=18 kN·m**):
- `f_v=133,3 kN/m` ; `f_horiz=f_h+f_bV+f_bH=320,0 kN/m` ; `f_dem=346,7 kN/m` ✅
- `f_dem > √(f_v²+f_h²+f_bV²+f_bH²)` (soma algébrica > SRSS) ✅
- perna dimensionada = menor padrão (6 mm) que cobre a demanda ✅
- chapa cisalhamento `V_Rd=0,6·fy·t·L/γa1=981,8 kN` (util 0,12) ✅
- chapa flexão `M_Rd=W·fy/γa1=122,7 kN·m` (util 0,15) ✅
- `h_trilho=0,10` → `f_dem` maior ✅
- caso enorme (Rv=3000, ecc=600, t=6, L=120) → nem 12 mm basta → **NÃO ATENDE** ✅
- `ecc=0, Ht=0` → `f_horiz=0` ✅

**PASSED.**

## 3. FLAGs

- Grupo de solda elástico (mecânica/AISC) — o responsável confirma o método.
- **Geometria/direção do console** (§5 nota) — chapa simples no plano × perfil T/I.
- Flexão da chapa usa `W` elástico (conservador); `Z=t·L²/4` disponível mas
  **flambagem local do bordo comprimido** fica FLAG (esbeltez t/L, enrijecedores).
- `L` = altura de solda da mísula (build 450 mm) — confirmar comprimento efetivo.
- `h_trilho` (altura do topo do trilho acima da solda) default 0 — informar real.
- `Ht`/impacto e `ecc` vêm do módulo de ponte (fabricante/NBR 8400, A CONFIRMAR).
- fu da chapa = 400 MPa (MR250).
