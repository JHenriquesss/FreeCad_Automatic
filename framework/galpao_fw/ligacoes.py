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
#     (Aw=0,707*perna*comprimento). Metal-base (Tabela 8 -> 6.5.5): menor entre
#     escoamento 0,60*fy*AMB/ga1 e ruptura 0,60*fu*AMB/ga2.
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


def fw_rd_base(t_base, Lw, fy, fu=None):
    """Metal-base ao cisalhamento (Tabela 8 filete -> 6.5.5): menor entre
    escoamento 0,60*fy*Ag/ga1 e ruptura 0,60*fu*Anv/ga2. Ao longo da solda nao
    ha furos -> Anv=Ag=AMB. Sem fu -> so escoamento (retrocompativel)."""
    AMB = t_base * Lw
    Fesc = 0.60 * fy * AMB / GA1
    if fu is None:
        return Fesc
    Frup = 0.60 * fu * AMB / GA2
    return min(Fesc, Frup)


def solda(caso):
    perna, Lw, fw = caso["perna"], caso["Lw"], caso["fw"]
    Fw, Aw = fw_rd_filete(perna, Lw, fw)
    Fb = fw_rd_base(caso["t_base"], Lw, caso["fy_base"], caso.get("fu_base"))
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


# Escada da ligacao de momento do joelho (n parafusos, db, t_chapa) em m.
ESCADA_JOELHO = [
    (4, 0.020, 0.0125),
    (4, 0.024, 0.0160),        # referencia
    (6, 0.024, 0.0190),
    (6, 0.027, 0.0220),
    (8, 0.027, 0.0250),
    (8, 0.030, 0.0315),
]


def dimensiona_ligacao(caso, escada=None):
    """Escolhe a ligacao de momento (n parafusos, db, t_chapa) MAIS LEVE que passa
    (interacao<=1) sob o esforco do caso (N tracao da mesa, V). Parte do seed.
    Retorna {aprovado:(n,db,t,r,caso)|None, linhas, tabela}."""
    escada = escada or ESCADA_JOELHO
    seed = (int(caso["n"]), round(caso["db"], 3), round(caso["t_chapa"], 4))
    cand = list(escada)
    if seed not in cand:
        cand = [seed] + cand
    linhas, aprovado = [], None
    for (n, db, t) in cand:
        c = dict(caso)
        c.update(n=n, db=db, t_chapa=t, lf=caso.get("lf", 1.5 * db))
        r = parafusos(c)
        linhas.append((n, db, t, r))
        if r["OK"] and aprovado is None:
            aprovado = (n, db, t, r, c)
    return {"aprovado": aprovado, "linhas": linhas,
            "tabela": _tabela_ligacao(linhas, aprovado, caso)}


def _tabela_ligacao(linhas, aprovado, caso):
    L = ["=" * 68, "DIMENSIONAMENTO DA LIGACAO DE MOMENTO (JOELHO)",
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL", "=" * 68, "",
         f"Esforco: N(tracao mesa)={caso.get('N',0):.1f} kN ; V={caso.get('V',0):.1f} kN",
         "Criterio: interacao (Nsd/Ft,Rd)^2+(Vsd/Fv,Rd)^2 <= 1 ; corte<=1.", "",
         f"{'n':>2} {'db(mm)':>6} {'t(mm)':>5} | {'u.trac':>6} {'u.corte':>7}"
         f" {'inter':>6} | resultado", "-" * 68]
    for (n, db, t, r) in linhas:
        tag = "PASSA" if r["OK"] else "nao passa"
        L.append(f"{n:>2} {db*1000:6.0f} {t*1000:5.1f} | {r['u_tracao']:6.2f}"
                 f" {r['u_corte']:7.2f} {r['interacao']:6.2f} | {tag}")
    L += ["-" * 68, ""]
    if aprovado:
        n, db, t = aprovado[:3]
        L += [f"ADOTADA: {n} parafusos d{db*1000:.0f} mm ; chapa de topo {t*1000:.0f} mm"]
    else:
        L += ["NENHUMA ligacao da escada passou - ampliar a escada ou rever o no."]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


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
    # metal-base filete (6.5.5): menor entre escoamento e ruptura
    AMB = 0.008 * 0.200
    esc, rup = 0.60 * 250e3 * AMB / 1.10, 0.60 * 400e3 * AMB / 1.35
    assert abs(fw_rd_base(0.008, 0.200, 250e3, 400e3) - min(esc, rup)) < 1e-6
    assert abs(fw_rd_base(0.008, 0.200, 250e3) - esc) < 1e-6   # sem fu -> escoamento
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
     "fu_base": 400e3, "F": 45.0},
]


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt([verifica_ligacao(c) for c in EXEMPLOS]))
