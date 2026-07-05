# Flambagem distorcional (FSM) - distorcional_fsm.py

Arquivo: `projects/galpao/calc/distorcional_fsm.py`  
Gerado: 2026-07-05  
Base: NBR 14762 9.3/9.8.2.3 (analise de estabilidade elastica). Motor FSM
= pycufsm (port validado do CUFSM). Requer numpy<2. Fecha a lacuna do Mdist
da terca (que era entrada manual).

## Codigo completo

```python
# ============================================================================
# distorcional_fsm.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Calcula o MOMENTO DE FLAMBAGEM DISTORCIONAL ELASTICO (Mdist) de um perfil U
# enrijecido (Ue) formado a frio, pelo METODO DAS FAIXAS FINITAS (FSM) - a
# "analise de estabilidade elastica" que a ABNT NBR 14762:2010 (9.3/9.8.2.3)
# exige e NAO fornece em forma fechada. Em vez de codar as matrizes de rigidez
# (alto risco de erro), USA a biblioteca validada pycufsm (port do CUFSM).
#   Entra: bw, bf, D, t (mm), fy, E, nu.
#   Monta a linha media da secao, roda a curva assinatura (signature curve) sob
#   flexao Mxx, e identifica os minimos LOCAL (menor meia-onda) e DISTORCIONAL
#   (minimo intermediario). Retorna Mcrl (local) e Mdist (distorcional) para
#   alimentar chi_distorcional / chi local do modulo tercas_nbr14762.
# ATENCAO: exige numpy < 2 (pycufsm 0.2.0 nao roda em numpy 2.x). O motor FSM e
# do pycufsm (validado); este script so monta a secao e extrai os minimos.
# Saidas em portugues. Unidades internas: mm, N, MPa (N/mm2).
# ============================================================================
"""Mdist (flambagem distorcional elastica) via FSM (pycufsm). Para a terca Ue."""

from __future__ import annotations

import numpy as np

try:
    import pycufsm.fsm as _fsm
    from pycufsm.pre.cutwp import prop2 as _prop2
    _HAS_PYCUFSM = True
except Exception:                       # pragma: no cover
    _HAS_PYCUFSM = False


def _seg(p0, p1, n):
    return [(p0[0] + (p1[0] - p0[0]) * k / n,
             p0[1] + (p1[1] - p0[1]) * k / n) for k in range(n + 1)]


def secao_ue(bw, bf, D, t, nw=12, nf=6, nl=4):
    """Linha media do Ue (mm): lip sup -> mesa sup -> alma -> mesa inf -> lip inf.
    Alma centrada em x=0. Retorna (coord, ends)."""
    pts = (_seg((bf, bw / 2 - D), (bf, bw / 2), nl)
           + _seg((bf, bw / 2), (0, bw / 2), nf)[1:]
           + _seg((0, bw / 2), (0, -bw / 2), nw)[1:]
           + _seg((0, -bw / 2), (bf, -bw / 2), nf)[1:]
           + _seg((bf, -bw / 2), (bf, -bw / 2 + D), nl)[1:])
    coord = np.array(pts, dtype=float)
    ends = np.array([[i, i + 1, t] for i in range(len(coord) - 1)], dtype=float)
    return coord, ends


def curva_assinatura(bw, bf, D, t, fy=250.0, E=200000.0, nu=0.3,
                     Lmin=20.0, Lmax=4000.0, n=80):
    """Roda a curva assinatura (FSM, flexao Mxx). Retorna lengths, LF, My."""
    if not _HAS_PYCUFSM:
        raise RuntimeError("pycufsm indisponivel (requer numpy<2). "
                           "Instale: pip install 'numpy<2' pycufsm")
    G = E / (2 * (1 + nu))
    coord, ends = secao_ue(bw, bf, D, t)
    nn = len(coord)
    sp = _prop2(coord, ends)
    cy = sp["cy"]
    ymax = max(abs(coord[:, 1] - cy))
    stress = fy * (coord[:, 1] - cy) / ymax          # fibra extrema = fy
    nodes = np.zeros((nn, 8))
    nodes[:, 0] = np.arange(nn)
    nodes[:, 1] = coord[:, 0]
    nodes[:, 2] = coord[:, 1]
    nodes[:, 3:7] = 1
    nodes[:, 7] = stress
    props = np.array([[0, E, E, nu, nu, G]])
    elements = np.array([[i, i, i + 1, t, 0] for i in range(nn - 1)], dtype=float)
    lengths = np.logspace(np.log10(Lmin), np.log10(Lmax), n)
    m_all = np.ones((len(lengths), 1))
    gbt = {"glob": [0], "dist": [0], "local": [0], "other": [0],
           "o_space": 1, "couple": 1, "orth": 2, "norm": 0}
    sig, _curve, _shapes = _fsm.strip(props, nodes, elements, lengths,
                                      np.array([]), np.array([]), gbt, "S-S",
                                      m_all, 10, sp)
    LF = np.array([float(np.ravel(s)[0]) for s in sig])
    Wc = sp["Ixx"] / ymax
    My = fy * Wc                                      # N.mm (fy MPa, Wc mm3)
    return lengths, LF, My


def _minimos_locais(x, y):
    """Indices dos minimos locais interiores de y(x)."""
    idx = []
    for i in range(1, len(y) - 1):
        if y[i] <= y[i - 1] and y[i] < y[i + 1]:
            idx.append(i)
    return idx


def mdist(bw, bf, D, t, fy=250.0, E=200000.0, nu=0.3):
    """Retorna dict com Mcrl (local), Mdist (distorcional) em kN.m e detalhes.
    Identifica o minimo LOCAL (menor meia-onda) e o DISTORCIONAL (proximo
    minimo intermediario). Ignora o ramo global descendente (sem minimo)."""
    L, LF, My = curva_assinatura(bw, bf, D, t, fy, E, nu)
    mins = _minimos_locais(L, LF)
    res = {"My_kNm": My / 1e6, "lengths": L, "LF": LF, "minimos": mins}
    if not mins:
        res.update(erro="nenhum minimo local encontrado (curva monotona)")
        return res
    # local = primeiro minimo ; distorcional = segundo (se houver)
    i_loc = mins[0]
    i_dist = mins[1] if len(mins) >= 2 else mins[0]
    res["Lcrl_mm"] = float(L[i_loc])
    res["Lcrd_mm"] = float(L[i_dist])
    res["Mcrl_kNm"] = float(LF[i_loc] * My / 1e6)      # local
    res["Mdist_kNm"] = float(LF[i_dist] * My / 1e6)    # distorcional
    res["Mdist_SI"] = float(LF[i_dist] * My) / 1e6     # kN.m (=Mdist_kNm)
    res["so_um_minimo"] = (len(mins) < 2)
    return res


def relatorio_pt(bw, bf, D, t, fy=250.0):
    r = mdist(bw, bf, D, t, fy)
    L = ["FLAMBAGEM DISTORCIONAL ELASTICA (FSM / pycufsm) - NBR 14762 9.3/9.8.2.3",
         f"  Perfil Ue {bw:.0f}x{bf:.0f}x{D:.0f}x{t:.2f} mm ; fy = {fy:.0f} MPa",
         f"  My = fy*Wc = {r['My_kNm']:.2f} kN.m"]
    if "erro" in r:
        L.append("  " + r["erro"])
    else:
        L += [f"  Local:        Lcrl = {r['Lcrl_mm']:.0f} mm -> Mcrl = {r['Mcrl_kNm']:.2f} kN.m",
              f"  Distorcional: Lcrd = {r['Lcrd_mm']:.0f} mm -> Mdist = {r['Mdist_kNm']:.2f} kN.m"]
        if r["so_um_minimo"]:
            L.append("  [AVISO] so um minimo detectado (local~distorcional); conferir a curva.")
        L.append(f"  -> passar Mdist = {r['Mdist_kNm']:.2f} kN.m para tercas_nbr14762 (cfg['Mdist'])")
    return "\n".join(L).replace(".", ",") if False else "\n".join(L)


def _selftest():
    if not _HAS_PYCUFSM:
        print("distorcional_fsm: pycufsm indisponivel (requer numpy<2) - SKIP")
        return
    # Ue 200x75x20 t=2.0 : deve achar local + distorcional com Mdist finito
    r = mdist(200.0, 75.0, 20.0, 2.0, fy=250.0)
    assert "Mdist_kNm" in r and r["Mdist_kNm"] > 0, r
    # sanidade: momentos elasticos de flambagem positivos e Lcrd > Lcrl
    assert r["Lcrd_mm"] >= r["Lcrl_mm"], r
    # sanidade independente: a tensao de flambagem LOCAL do FSM deve ficar na
    # ordem da flambagem de placa da alma sob flexao (k=23,9, formula fechada).
    E, nu, bw, t = 200000.0, 0.3, 200.0, 2.0
    Wc = (r["Mcrl_kNm"] * 1e6) / (r["Mcrl_kNm"] and 1)  # nao usado; ver abaixo
    sig_local_fsm = r["Mcrl_kNm"] * 1e6 / (r["My_kNm"] * 1e6 / 250.0)  # = Mcrl/Wc
    sig_web = 23.9 * 3.14159265 ** 2 * E / (12 * (1 - nu ** 2)) * (t / bw) ** 2
    ratio = sig_local_fsm / sig_web
    assert 0.5 < ratio < 2.0, (sig_local_fsm, sig_web, ratio)
    print("distorcional_fsm self-test PASSED")
    print(f"  Ue200x75x20x2.0: Mcrl={r['Mcrl_kNm']:.2f} ; Mdist={r['Mdist_kNm']:.2f} kN.m ;"
          f" My={r['My_kNm']:.2f} kN.m")
    print(f"  sanidade local: sigma_FSM={sig_local_fsm:.0f} vs sigma_placa_alma(k=23,9)="
          f"{sig_web:.0f} MPa (razao {ratio:.2f}, ordem confere)")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(200.0, 75.0, 20.0, 2.0, fy=250.0))
```

## Resultado da execucao (self-test + exemplo)

```
distorcional_fsm self-test PASSED
  Ue200x75x20x2.0: Mcrl=24.94 ; Mdist=19.55 kN.m ; My=12.46 kN.m
  sanidade local: sigma_FSM=500 vs sigma_placa_alma(k=23,9)=432 MPa (razao 1.16, ordem confere)

FLAMBAGEM DISTORCIONAL ELASTICA (FSM / pycufsm) - NBR 14762 9.3/9.8.2.3
  Perfil Ue 200x75x20x2.00 mm ; fy = 250 MPa
  My = fy*Wc = 12.46 kN.m
  Local:        Lcrl = 114 mm -> Mcrl = 24.94 kN.m
  Distorcional: Lcrd = 654 mm -> Mdist = 19.55 kN.m
  -> passar Mdist = 19.55 kN.m para tercas_nbr14762 (cfg['Mdist'])
```
