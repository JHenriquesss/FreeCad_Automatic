# Revisão — DG25 envelope de estados-limite de flexão (§5.4.4/5/6/7)

Estende `dg25_ltb.py` com os estados-limite de flexão que faltavam do AISC Design
Guide 25 §5.4: **FLB** (flambagem local da mesa comprimida, §5.4.4), **TFY**
(escoamento da mesa tracionada, §5.4.5), **ruptura da mesa tracionada** (§5.4.6) e
o **envelope** Mn = min(CFY, LTB, FLB, TFY, TFR) (§5.4.7). Fecha o backlog "FLB/TFY
DG25 §5.4.4/5/6" (residual dos itens 43/44). Fase 6.16. Criado 2026-07-13.

> **STATUS: ⏳ AGUARDANDO PARECER** (2026-07-13). **INFORMATIVO** — dimensionamento
> segue a NBR 8800 (Anexo G/J). Cross-check independente.

## Base normativa (AISC DG25 §5.4 — verbatim das imagens, pág 62–64)

### §5.4.4 Compression Flange Local Buckling (FLB) — 3 regiões por λ = bfc/(2·tfc)

```
(a) compacta   λ ≤ 0,38·√(E/Fy):                 FLB não aplica (retorna teto CFY)
(b) não-compacta 0,38√(E/Fy) < λ < 0,95√(kc·E/FL):
     Mn = Rpg·[Rpc·Myc − (Rpc·Myc − FL·Sxc)·(λ−λpf)/(λrf−λpf)]        (5.4-22)
(c) esbelta   λ ≥ 0,95·√(kc·E/FL):
     Mn = Rpg·0,9·E·kc·Sxc/λ²                                          (5.4-23)
kc = 4/√(hc/tw),  0,35 ≤ kc ≤ 0,76                                     (5.4-24)
λpf = 0,38·√(E/Fy) ; λrf = 0,95·√(kc·E/FL)
```

### §5.4.5 Tension Flange Yielding (TFY) — só se Sxt < Sxc

```
Sxt ≥ Sxc:  TFY não aplica.
Sxt < Sxc:  Mn = Rpt·Fy·Sxt                                           (5.4-25)
Rpt:  hc/tw ≤ λpw           → Mp/Myt                                   (5.4-26)
      λpw < hc/tw ≤ λrw     → [Mp/Myt − (Mp/Myt−1)(λ−λpw)/(λrw−λpw)] ≤ Mp/Myt (5.4-27)
      hc/tw > λrw ou Iyc/Iy ≤ 0,23 → 1,0                              (5.4-28)
Mp = Fy·Zx ≤ 1,6·Fy·Sxt (5.4-28) ; Myt = Fy·Sxt (5.4-29)
λpw = 3,76·√(E/Fy) ; λrw = 5,70·√(E/Fy)
```

### §5.4.6 Tension Flange Rupture (com furos)

```
Fu·Afn ≥ Yt·Fy·Afg:  ruptura não aplica.
Fu·Afn < Yt·Fy·Afg:  Mn = (Fu·Afn/Afg)·Sxt                            (5.4-30, F13.1)
Yt = 1,0 se Fy/Fu ≤ 0,8 ; senão 1,1
Afg = bft·tft ; Afn = Afg − n_furos·dh·tft
```

### §5.4.7 Razão de resistência — envelope

`Mn = min(CFY, LTB, FLB, TFY, TFR)` — o menor dos estados aplicáveis governa.
`CFY = Rpc·Rpg·Myc` (teto); `LTB = mn_ltb_dg` (item 44, já homologado).

## O que revisar

1. **FLB (5.4-22/23/24):** parse das 3 regiões, `λrf` com `kc` e `FL` (não Fy),
   `kc` limitado a [0,35;0,76]. Região (a) retorna o teto CFY (neutro no `min`).
2. **Rpt (5.4-26/27/28):** espelha `Rpc` mas referido a `Myt=Fy·Sxt`; gate
   `Iyc/Iy≤0,23 ou alma esbelta → 1,0`.
3. **TFR (5.4-30):** `Yt` por `Fy/Fu≤0,8`; só aplica com furos informados
   (Ask-Do-Not-Invent: `n_furos`/`dh` são dado de fabricação).
4. **Envelope:** governante = `min` dos estados **aplicáveis**; TFY só entra se
   `Sxt<Sxc`; TFR só com `fu` + furos.
5. **Regressão:** duplo-simétrico → TFY não aplica (`Sxt=Sxc`), FLB compacta neutra.
   `test_fase614` + `dg25 --selftest` inalterados (28 testes verdes).

## Cobertura de teste (fase 6.16)

`tests/test_fase616_dg25_envelope.py` — 10 testes: FLB compacta/não-compacta/esbelta;
TFY duplo-sim não aplica / mono aplica; TFR sem furos não aplica / com furos reduz;
envelope governa o menor estado; mono c/ furos inclui CFY/LTB/FLB/TFY/TFR; prismático
Lb curto → CFY/LTB/FLB.

## Escopo

**Informativo.** Envelope de verificação independente; o dimensionamento e a
homologação seguem a NBR 8800. Mesa comprimida governa FLB via `bfc/tfc`
(mono-aware por `props_I_mono`, item 6.15).
