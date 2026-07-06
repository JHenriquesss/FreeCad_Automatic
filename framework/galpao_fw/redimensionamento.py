# ============================================================================
# redimensionamento.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Busca a combinacao de perfis (coluna + viga) mais leve que faz o portico
# PASSAR, com BASE ENGASTADA, rodando a cadeia de calculo completa para cada
# candidato:
#   1) portico (galpao_portico) -> flecha lateral no beiral (ELS);
#   2) 2a ordem (estabilidade_b1b2, MAES + rigidez 0,8 + nocional) -> esforcos
#      amplificados Msd/Nsd/Vsd;
#   3) verificacao NBR 8800 (check_nbr8800) com K=1 em todas as combinacoes ->
#      pior interacao por peca.
# Criterio de aprovacao: interacao <= 1,00 (ELU) E flecha <= H/150 (ELS, telha
# metalica). Reporta uma tabela e o primeiro candidato (mais leve) que passa.
# NAO redefine o metodo - so orquestra os modulos ja validados variando perfis.
# ============================================================================
"""Iteracao de perfis com base engastada. Saidas em portugues. Usa modulos ja
validados (portico, 2a ordem, check). Unidades: m, kN."""

from __future__ import annotations

import re

import perfis
import galpao_portico as gp
import estabilidade_b1b2 as est
import check_nbr8800 as chk

FY = 250e3                 # aco MR250
LIM_INT = 1.00             # interacao ELU
LIM_FLECHA = gp.EAVE / 150.0   # telha metalica (NBR 8800 Anexo C / Bellei)
LB_COL = 2.0               # travamento lateral da coluna (espac. das longarinas)
LB_VIGA = 1.67             # travamento lateral da viga (espac. das tercas)

# escada de candidatos (coluna, viga), do mais leve ao mais pesado (peso ~ A)
CANDIDATOS = [
    ("HEA200", "HEA180"),   # atual (base rotulada reprovava)
    ("HEB200", "IPE300"),
    ("HEB220", "IPE330"),
    ("HEB240", "IPE360"),
    ("HEB260", "IPE400"),
]


def _aplica(col, raf, fixed=True):
    """Injeta o candidato nos modulos (secoes + condicao de base)."""
    pc, pr = perfis.PERFIS[col], perfis.PERFIS[raf]
    gp.A_COL, gp.I_COL = pc["A"], pc["Ix"]
    gp.A_RAF, gp.I_RAF = pr["A"], pr["Ix"]
    gp.BASE_FIXED = fixed
    est.SEC["coluna"].update(A=pc["A"], I=pc["Ix"])
    est.SEC["viga"].update(A=pr["A"], I=pr["Ix"])


def _peso_rel(col, raf):
    """Peso relativo ~ soma das areas (proxy do consumo de aco)."""
    return perfis.PERFIS[col]["A"] + perfis.PERFIS[raf]["A"]


def avalia(col, raf, fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA):
    _aplica(col, raf, fixed)
    a = est.analyse()                       # esforcos amplificados (2a ordem)
    drift = gp.analyse()["drift"]           # flecha lateral (ELS, base atual)
    lim_flecha = gp.EAVE / 150.0            # H/150 com o pe-direito atual
    inter = {}
    for g, prof, Lb in (("coluna", col, lb_col), ("viga", raf, lb_raf)):
        sec = perfis.PERFIS[prof]
        L = est.SEC[g]["L"]
        worst = max((chk.verifica(sec, FY, L=L, Nsd=r[g]["Nsd"], Msd=r[g]["Msd"],
                                  Vsd=r[g]["Vsd"], Kx=1.0, Ky=1.0, Lb=Lb)
                     for r in a["combos"]), key=lambda x: x["interacao"])
        inter[g] = worst["interacao"]
    passa = (inter["coluna"] <= LIM_INT and inter["viga"] <= LIM_INT
             and drift <= lim_flecha)
    return {"col": col, "raf": raf, "B2": a["B2max"], "drift": drift,
            "lim_flecha": lim_flecha, "int_col": inter["coluna"],
            "int_viga": inter["viga"], "peso": _peso_rel(col, raf), "passa": passa}


def melhor(fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA, seed=None):
    """Escolhe o par (coluna, viga) MAIS LEVE que passa (interacao<=1 + flecha),
    partindo do seed (perfil atual) e subindo pela escada. Deixa o estado global
    no perfil ADOTADO (aprovado; ou o seed se nada passar). Retorna
    {aprovado, candidatos, tabela}."""
    escada = []
    if seed:
        seed = tuple(seed)
        if seed not in CANDIDATOS:
            escada.append(seed)
    escada += list(CANDIDATOS)
    linhas, aprovado = [], None
    for col, raf in escada:
        if col not in perfis.PERFIS or raf not in perfis.PERFIS:
            continue
        r = avalia(col, raf, fixed, lb_col, lb_raf)
        linhas.append(r)
        if r["passa"] and aprovado is None:
            aprovado = r
    fin = aprovado or (avalia(*seed, fixed=fixed, lb_col=lb_col, lb_raf=lb_raf)
                       if seed else None)
    if fin:
        _aplica(fin["col"], fin["raf"], fixed)      # estado = perfil adotado
    return {"aprovado": aprovado, "candidatos": linhas,
            "tabela": _tabela(linhas, aprovado, lb_col, lb_raf)}


def _tabela(linhas, aprovado, lb_col, lb_raf):
    lim = gp.EAVE / 150.0
    L = ["=" * 74, "REDIMENSIONAMENTO - par (coluna, viga) mais leve que passa",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 74, "",
         "Criterio: interacao ELU <= 1,00 (NBR 8800, K=1 com 2a ordem) E",
         f"          flecha lateral <= H/150 = {lim*1000:.1f} mm (telha metalica).",
         f"Travamento: coluna Lb={lb_col:.2f} m ; viga Lb={lb_raf:.2f} m.", "",
         f"{'Coluna':>8} {'Viga':>7} | {'B2max':>6} | {'flecha':>8} {'lim':>6} |"
         f" {'int.col':>7} {'int.viga':>8} | resultado", "-" * 74]
    for r in linhas:
        tag = "PASSA" if r["passa"] else "nao passa"
        L.append(f"{r['col']:>8} {r['raf']:>7} | {r['B2']:6.3f} | "
                 f"{r['drift']*1000:7.1f}mm {lim*1000:5.1f} | {r['int_col']:7.2f} "
                 f"{r['int_viga']:8.2f} | {tag}")
    L += ["-" * 74, ""]
    if aprovado:
        L += [f"ADOTADO (mais leve que passa): COLUNA {aprovado['col']} + "
              f"VIGA {aprovado['raf']}",
              f"  B2,max = {aprovado['B2']:.3f} ; flecha = {aprovado['drift']*1000:.1f} mm "
              f"(<= {lim*1000:.1f}) ; int. coluna = {aprovado['int_col']:.2f} ; "
              f"viga = {aprovado['int_viga']:.2f}"]
    else:
        L += ["NENHUM candidato passou - ampliar a escada ou revisar o esquema",
              "estrutural (mao-francesa, contraventamento, inclinacao)."]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def memoria_pt(fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA, seed=None):
    """Roda a escada e devolve a tabela + o adotado (memorial standalone)."""
    return melhor(fixed=fixed, lb_col=lb_col, lb_raf=lb_raf, seed=seed)["tabela"]


if __name__ == "__main__":
    print(memoria_pt())
