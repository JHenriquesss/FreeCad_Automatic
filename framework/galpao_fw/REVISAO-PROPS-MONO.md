# Revisão — props_I_mono: propriedades de perfil I monossimétrico

Novo utilitário `props_I_mono.py` (mesas comprimida ≠ tracionada) que habilita o
**ramo monossimétrico real** do AISC Design Guide 25 (F_L 5.4-15 via Sxt/Sxc,
rt 5.4-11 via bfc, Rpc/Rpg via hc real). Fecha o refino pendente do item 44
(o parecer do DG25 full pediu "pacote de props assimétricas `props_I_mono`
com Wxt/Wxc, Iyc/Iy, hc/hp"). Fase 6.15. Criado 2026-07-13.

> **STATUS: ✅ HOMOLOGADO SEM RESSALVAS** (2026-07-13). Parecer inicial: aprovado com
> ressalva (rt 5.4-11 hc²→hw²); correção aplicada e re-aprovada sem ressalvas.
> Ver §Parecer abaixo.

## O que faz

Perfil I soldado de altura `d`, mesa comprimida `bfc×tfc` (topo), mesa tracionada
`bft×tft` (base), alma `tw`. Retorna dict **superset** do consumido por
`check_nbr8800`/`dg25_ltb`:
`A, Ix, Iy, Wx(=Wxc), Wxc, Wxt, Zx, Wy, Zy, rx, ry, rt, d, bf(=bfc), tf(=tfc),
tw, Av, bfc, tfc, bft, tft, hw, hc, hp, ho, Iyc, Iyt, Iyc_Iy, J, Cw, ybar, cc, ct`.

## Critério de aceite (o que revisar)

1. **Redução exata ao duplo-simétrico.** `bfc=bft, tfc=tft` reproduz
   `alma_variavel.props_I` em A, Ix, Iy, Wx, Zx, rx, ry, Av (tol 1e-9). Teste
   `test_reduz_ao_duplo_simetrico`.
2. **Mecânica de seção (verificar as fórmulas):**
   - centroide `ybar` da base (fibra tracionada) por 1º momento; `cc=d−ybar`,
     `ct=ybar`; `Wxc=Ix/cc`, `Wxt=Ix/ct`.
   - `hc = 2·((d−tfc) − ybar)` (2× alma comprimida, elástico); `hp = 2·((d−tfc) − yp)`
     (plástico, `yp`=LN plástica que divide a área ao meio).
   - `ho = (d − tfc/2) − (tft/2)` (entre centroides das mesas).
   - `Iyc = tfc·bfc³/12`, `Iyt = tft·bft³/12`, `Iyc_Iy = Iyc/Iy`.
   - `Cw = ho²·Iyc·Iyt/(Iyc+Iyt)` (empenamento I monossimétrico; reduz a `Iy·ho²/4`
     a menos do termo `tw³` da alma — ver `test_cw_reduz_a_Iy_ho2_sobre_4`, tol 1e-3).
   - `J = Σ[b·t³/3·(1−0,63 t/b)]_mesas + hw·tw³/3` (Saint-Venant, seção aberta).
   - `Zx` por integração exata `∫ largura·|y−yp| dy` (retângulos, LN plástica).
   - `rt = bfc/√(12·(ho/d + (1/6)·aw·hw²/(ho·d)))`, `aw = hc·tw/(bfc·tfc)`
     (DG25 5.4-11). **`aw` usa hc (alma comprimida); o termo ao quadrado usa
     h = hw (alma LIVRE)** — ver §Parecer.
3. **Integração com o DG25 (mono-aware por `.get()`):** os helpers
   `hc/ho/aw/rt/J_dg` de `dg25_ltb` passaram a ler as chaves mono
   (`hc, ho, bfc, tfc, bft, tft, hw, Iyc_Iy, rt`) quando presentes, com **fallback
   idêntico** ao duplo-simétrico. Regressão: `dg25_ltb --selftest` inalterado
   (prismático razão 0,998); `test_dg25_duplo_sim_inalterado_via_mono` (Mn por
   `props_I` ≡ Mn por `props_I_mono` duplo-sim, tol 1e-3).

## Nota de convenção (Iyc/Iy≈0,5)

No duplo-simétrico `Iyc/Iy = 0,4997` (não 0,5) porque o `Iy` inclui o termo `tw³/12`
da alma, que o DG25 aproxima por 0,5. Sem efeito no gate de `J=0` (>0,23) nem no Rpc.

## Cobertura de teste (fase 6.15)

`tests/test_fase615_props_mono.py` — 11 testes: redução duplo-sim; Wxc=Wxt no
simétrico; centroide sobe c/ mesa comprimida maior (Wxc>Wxt, Iyc/Iy>0,5); Zx>S_min;
Cw→Iy·ho²/4; rt escala com bfc; **rt usa h livre (hw) e não hc (5.4-11)**; F_L clampa
em 0,5Fy (Sxt/Sxc<0,5); rampa 5.4-15 (0,5<Sxt/Sxc<0,7); Mn roda em seção mono;
duplo-sim inalterado via mono.

## Parecer do sênior (2026-07-13) — correção do `rt` (5.4-11 / Spec. F4-10)

**Ressalva procedente.** A eq DG25 5.4-11 (= AISC 360 F4-10, pág 61 do DG25, imagem
conferida) é:

```
rt = bfc / √( 12 ( ho/d + (1/6)·aw·h²/(ho·d) ) )      aw = hc·tw/(bfc·tfc)
```

O `h` que vai **ao quadrado** é a **altura livre da alma** (`h = hw = d−tfc−tft`),
**não** `hc`. O `hc` entra **só** no `aw`. A implementação usava `hc²` no lugar de
`hw²`.

- **Por que passou despercebido:** no duplo-simétrico `hc = hw = d−2tf`, então
  `hc² ≡ hw²` — a regressão e o selftest (0,998) eram byte-idênticos. O desvio só
  aparece no **monossimétrico**, onde `hc ≠ hw`.
- **Magnitude:** seção mono forte (mesa comp. 300×19, tracionada 150×9,5, alma 8):
  `hc = 354 mm` vs `hw = 571 mm` (−38%) → `rt` estava **superestimado ~2,3%** →
  capacidade de FLT **contra a segurança**. Correção reduz `rt` (conservadora).
- **Correção aplicada:** `props_I_mono.py` linha 105 (`hc**2`→`hw**2`) e o fallback
  de `dg25_ltb.rt` (linha 69, `h = hc`→`h = hw`; latente pois mono sempre traz `rt`
  pronto, mas corrigido por robustez). Comentários atualizados.
- **Teste de regressão novo:** `test_rt_usa_h_livre_da_alma_nao_hc` — em seção mono
  com `hc < 0,9·hw`, exige `rt ≡ fórmula(hw)` e `rt ≠ fórmula(hc)`. Suíte fase 6.15
  passa a **11 testes** (614/615/616 = 40 verdes; selftests dupl-sim inalterados).

## Escopo

Utilitário de propriedades — **não dimensiona** e **não altera** nenhum
resultado existente (duplo-simétrico byte-idêntico). Serve o DG25 (informativo)
e qualquer verificação futura que precise de `Wxc≠Wxt`.
