# Ligacoes parafusadas e soldadas (NBR 8800) - ligacoes.py

Arquivo: `projects/galpao/calc/ligacoes.py`  
Gerado: 2026-07-05  
Base: NBR 8800 6.3 (parafusos), 6.2.5 (solda de filete), 6.1.5.2 (forca
minima 45 kN). PARAMETRICO: qualquer ligacao parafusada ou soldada.

## Codigo completo

```python
# ============================================================================
# ligacoes.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica LIGACOES de estrutura de aco (parafusadas e soldadas) pela ABNT
# NBR 8800:2008. Generico e parametrico (qualquer ligacao: joelho viga-coluna,
# emenda, ligacao de contravento, chapa de terca, etc.).
#   - Parafusos (6.3.3): cisalhamento Fv,Rd=0,4*Ab*fub/ga2 (rosca no plano) ou
#     0,5 (fora); tracao Ft,Rd=Abe*fub/ga2 ; pressao de contato/esmagamento
#     Fc,Rd=min(1,2*lf*t*fu ; 2,4*db*t*fu)/ga2 ; interacao tracao+corte
#     (Ft/FtRd)^2+(Fv/FvRd)^2<=1 (6.3.3.4).
#   - Solda de filete (6.2.5): metal da solda Fw,Rd=0,60*fw*Aw/gw2
#     (Aw=0,707*perna*comprimento) e metal-base 0,60*fy*AMB/ga1 (menor).
#   - Forca minima de ligacao 45 kN (6.1.5.2), com as excecoes da norma
#     (tirantes redondos, travessas, TERCAS de cobertura, travejamento).
# NAO cobre estados-limites da chapa (rasgamento em bloco/flexao) alem do
# esmagamento - FLAG onde aplicavel. Saidas em portugues. Unidades SI: m, kN.
# ============================================================================
"""Verificacao de ligacoes parafusadas e soldadas conforme ABNT NBR 8800:2008."""

from __future__ import annotations

import math

GA2 = 1.35         # ruptura (parafuso/solda de ruptura)
GA1 = 1.10         # escoamento (metal-base)
GW2 = 1.35         # solda (Nota k, Tabela 8)
FORCA_MIN = 45.0   # kN (6.1.5.2)


# ---- parafusos -------------------------------------------------------------
def _area(db):
    Ab = math.pi * db ** 2 / 4.0
    return Ab, 0.75 * Ab            # bruta, efetiva (rosqueada)


def fv_rd(db, fub, rosca_no_plano=True, n_planos=1):
    Ab, _ = _area(db)
    c = 0.4 if rosca_no_plano else 0.5
    return c * Ab * fub / GA2 * n_planos


def ft_rd(db, fub):
    _, Abe = _area(db)
    return Abe * fub / GA2


def fc_rd(db, t, fu, lf):
    """Esmagamento/rasgamento (deformacao limitante, 6.3.3.3)."""
    return min(1.2 * lf * t * fu, 2.4 * db * t * fu) / GA2


def parafusos(caso):
    n = caso["n"]
    db, fub = caso["db"], caso["fub"]
    t, fu, lf = caso["t_chapa"], caso["fu_chapa"], caso["lf"]
    Fvrd = fv_rd(db, fub, caso.get("rosca_no_plano", True), caso.get("n_planos", 1))
    Ftrd = ft_rd(db, fub)
    Fcrd = fc_rd(db, t, fu, lf)
    Vsd = caso.get("V", 0.0) / n
    Nsd = caso.get("N", 0.0) / n           # tracao por parafuso (se houver)
    # resistencia ao corte por parafuso = min(corte, esmagamento)
    Fv_lim = min(Fvrd, Fcrd)
    inter = (Nsd / Ftrd) ** 2 + (Vsd / Fvrd) ** 2 if Nsd > 0 else Vsd / Fv_lim
    return {"tipo": "parafusos", "n": n, "Fv_Rd": Fvrd, "Ft_Rd": Ftrd,
            "Fc_Rd": Fcrd, "Fv_lim": Fv_lim, "Vsd": Vsd, "Nsd": Nsd,
            "u_corte": Vsd / Fv_lim, "u_tracao": (Nsd / Ftrd) if Nsd else 0.0,
            "interacao": inter, "OK": inter <= 1.0 and (Vsd / Fv_lim) <= 1.0}


# ---- solda de filete -------------------------------------------------------
def fw_rd_filete(perna, Lw, fw):
    """Metal da solda (6.2.5): garganta = 0,707*perna."""
    Aw = 0.707 * perna * Lw
    return 0.60 * fw * Aw / GW2, Aw


def fw_rd_base(t_base, Lw, fy):
    """Metal-base ao cisalhamento (0,60*fy*AMB/ga1)."""
    AMB = t_base * Lw
    return 0.60 * fy * AMB / GA1


def solda(caso):
    perna, Lw, fw = caso["perna"], caso["Lw"], caso["fw"]
    Fw, Aw = fw_rd_filete(perna, Lw, fw)
    Fb = fw_rd_base(caso["t_base"], Lw, caso["fy_base"])
    Frd = min(Fw, Fb)
    Fsd = caso["F"]
    return {"tipo": "solda", "Aw": Aw, "Fw_metal": Fw, "Fw_base": Fb,
            "Fw_Rd": Frd, "Fsd": Fsd, "u": Fsd / Frd, "OK": Fsd <= Frd,
            "governa": "metal-base" if Fb < Fw else "metal da solda"}


# ---- forca minima 6.1.5.2 --------------------------------------------------
def forca_minima(Fsd, excecao=False):
    """Retorna a forca de dimensionamento (>=45 kN) e se foi governada pelo
    minimo. excecao=True para tirantes redondos, travessas, TERCAS, travejamento."""
    if excecao:
        return Fsd, False
    if abs(Fsd) < FORCA_MIN:
        return FORCA_MIN, True
    return Fsd, False


def verifica_ligacao(caso):
    Fsd_orig = caso.get("F", caso.get("V", 0.0))
    Fdim, governou = forca_minima(Fsd_orig, caso.get("excecao_terca", False))
    caso = dict(caso)
    # aplica a forca de dimensionamento minima ao esforco principal
    if governou:
        if "F" in caso:
            caso["F"] = Fdim
        else:
            caso["V"] = Fdim
    r = solda(caso) if caso["tipo"] == "solda" else parafusos(caso)
    r["nome"] = caso.get("nome", "ligacao")
    r["forca_dim"] = Fdim
    r["min_governou"] = governou
    return r


def relatorio_pt(rs):
    L = ["VERIFICACAO DE LIGACOES (ABNT NBR 8800:2008 - 6.2 / 6.3 / 6.1.5)"]
    for r in rs:
        L += ["", f"  --- {r['nome']} ({r['tipo']}) ---"]
        if r["min_governou"]:
            L.append(f"    Forca de dimensionamento = 45,0 kN (minimo 6.1.5.2)")
        if r["tipo"] == "parafusos":
            L += [f"    n={r['n']} parafusos ; Fv,Rd={r['Fv_Rd']:.1f} ; "
                  f"Ft,Rd={r['Ft_Rd']:.1f} ; Fc,Rd(esmag.)={r['Fc_Rd']:.1f} kN",
                  f"    por parafuso: V={r['Vsd']:.1f} ; N={r['Nsd']:.1f} kN ; "
                  f"corte/min(Fv,Fc)={r['u_corte']:.2f} ; tracao={r['u_tracao']:.2f}",
                  f"    interacao/util = {r['interacao']:.2f}  -> "
                  f"{'OK' if r['OK'] else 'NAO PASSA'}"]
        else:
            L += [f"    Aw={r['Aw']*1e4:.2f} cm2 ; metal solda={r['Fw_metal']:.1f} ; "
                  f"metal-base={r['Fw_base']:.1f} -> Fw,Rd={r['Fw_Rd']:.1f} kN "
                  f"(governa {r['governa']})",
                  f"    Fsd={r['Fsd']:.1f} kN ; util={r['u']:.2f}  -> "
                  f"{'OK' if r['OK'] else 'NAO PASSA'}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # parafuso: Fv,Rd = 0,4*Ab*fub/1,35
    Ab, _ = _area(0.016)
    assert abs(fv_rd(0.016, 800e3) - 0.4 * Ab * 800e3 / 1.35) < 1e-6
    # solda: Fw = 0,60*fw*0,707*perna*L/1,35
    Fw, Aw = fw_rd_filete(0.006, 0.200, 485e3)
    assert abs(Fw - 0.60 * 485e3 * Aw / 1.35) < 1e-6
    # forca minima
    assert forca_minima(30.0)[0] == 45.0 and forca_minima(30.0, excecao=True)[0] == 30.0
    print("ligacoes self-test PASSED")
    print(f"  Fv,Rd(d16, fub800) = {fv_rd(0.016,800e3):.1f} kN")
    print(f"  Fw,Rd filete 6mm x 200mm (fw=485) metal = {Fw:.1f} kN")


# ---- exemplos PLACEHOLDER (a skill pergunta ao usuario) --------------------
EXEMPLOS = [
    {"nome": "Joelho viga-coluna (parafusos M20 A325)", "tipo": "parafusos",
     "n": 6, "db": 0.020, "fub": 825e3, "t_chapa": 0.0125, "fu_chapa": 400e3,
     "lf": 0.035, "V": 130.0, "N": 90.0, "rosca_no_plano": True},
    {"nome": "Chapa de terca (parafusos M12) - excecao terca", "tipo": "parafusos",
     "n": 2, "db": 0.012, "fub": 400e3, "t_chapa": 0.006, "fu_chapa": 400e3,
     "lf": 0.025, "V": 8.0, "excecao_terca": True},
    {"nome": "Ligacao de contravento (solda filete)", "tipo": "solda",
     "perna": 0.006, "Lw": 0.240, "fw": 485e3, "t_base": 0.008, "fy_base": 250e3,
     "F": 45.0},
]


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt([verifica_ligacao(c) for c in EXEMPLOS]))
```

## Resultado da execucao (self-test + exemplos)

```
ligacoes self-test PASSED
  Fv,Rd(d16, fub800) = 47.7 kN
  Fw,Rd filete 6mm x 200mm (fw=485) metal = 182.9 kN

VERIFICACAO DE LIGACOES (ABNT NBR 8800:2008 - 6,2 / 6,3 / 6.1.5)

  --- Joelho viga-coluna (parafusos M20 A325) (parafusos) ---
    n=6 parafusos ; Fv,Rd=76,8 ; Ft,Rd=144,0 ; Fc,Rd(esmag.)=155,6 kN
    por parafuso: V=21,7 ; N=15,0 kN ; corte/min(Fv,Fc)=0,28 ; tracao=0,10
    interacao/util = 0,09  -> OK

  --- Chapa de terca (parafusos M12) - excecao terca (parafusos) ---
    n=2 parafusos ; Fv,Rd=13,4 ; Ft,Rd=25,1 ; Fc,Rd(esmag.)=51,2 kN
    por parafuso: V=4,0 ; N=0,0 kN ; corte/min(Fv,Fc)=0,30 ; tracao=0,00
    interacao/util = 0,30  -> OK

  --- Ligacao de contravento (solda filete) (solda) ---
    Aw=10,18 cm2 ; metal solda=219,5 ; metal-base=261,8 -> Fw,Rd=219,5 kN (governa metal da solda)
    Fsd=45,0 kN ; util=0,21  -> OK
```
