# ============================================================================
# redimensionamento.py - AUTO-SIZING para 1 ou N vaos (assimetricos inclusive)
# Otimizacao GULOSA: inicia todos os perfis no mais leve, identifica a
# coluna mais solicitada, sobe um degrau nela, reavalia, itera.
# Cada coluna pode ter um perfil diferente (util para vaos assimetricos).
# ============================================================================
from __future__ import annotations
import math, re
import galpao_portico as gp
import estabilidade_b1b2 as est
import check_nbr8800 as chk
import perfis

FY = 250e3
LIM_INT = 1.00
LIM_FLECHA = gp.EAVE / 300.0
LB_COL = 2.0
LB_VIGA = 1.67

# Escada de perfis (do mais leve ao mais pesado)
_ESC_COL = ["HEA160","HEA180","HEA200","HEA220","HEA240",
            "HEB200","HEB220","HEB240","HEB260","HEB280","HEB300",
            "IPE300","IPE330","IPE360","IPE400","IPE450","IPE500","IPE550"]
_ESC_RAF = ["HEA160","HEA180","HEA200","HEA220","HEA240",
            "IPE300","IPE330","IPE360","IPE400","IPE450","IPE500","IPE550",
            "HEB200","HEB220","HEB240","HEB260","HEB280","HEB300"]
# Indices maximos validos
_MAX_COL_IDX = len(_ESC_COL) - 1
_MAX_RAF_IDX = len(_ESC_RAF) - 1


def _aplica(cols_perfil, raf, fixed=True):
    """cols_perfil: lista de N+1 nomes de perfis, um por coluna.
    raf: nome do perfil da viga (usado em todas)."""
    nv = gp.N_VAOS
    pr = perfis.PERFIS[raf]
    gp.A_RAF, gp.I_RAF = pr["A"], pr["Ix"]
    gp.BASE_FIXED = fixed
    while len(est.SEC_COLS) < nv + 1:
        est.SEC_COLS.append({"A": gp.A_RAF, "I": gp.I_RAF, "L": gp.EAVE})
    while len(est.SEC_VIGAS) < nv * 2:
        est.SEC_VIGAS.append({"A": pr["A"], "I": pr["Ix"],
                              "L": math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)})
    for i in range(nv + 1):
        sec = perfis.PERFIS[cols_perfil[i]]
        est.SEC_COLS[i].update(A=sec["A"], I=sec["Ix"], L=gp.EAVE)
        if i == 0:
            gp.A_COL, gp.I_COL = sec["A"], sec["Ix"]
    # colunas podem ter perfis distintos por linha -> avisa o sincronizar() do
    # estabilidade a NAO sobrescrever as secoes por-coluna com a unica gp.A_COL
    # (senao o B1 por-coluna usaria o Ne da coluna 0 p/ todas). Bug 8.21.
    est.SEC_COLS_EXTERNO = True
    Lr = math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)
    for i in range(nv * 2):
        est.SEC_VIGAS[i].update(A=pr["A"], I=pr["Ix"], L=Lr)


def _peso(cols_perfil, raf):
    lc = gp.EAVE
    lr = math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)
    peso_col = sum(perfis.PERFIS[p]["A"] * lc for p in cols_perfil)
    peso_raf = 2 * gp.N_VAOS * perfis.PERFIS[raf]["A"] * lr
    return peso_col + peso_raf


def avalia(cols_perfil, raf, fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA):
    """Avalia um conjunto de perfis (lista de colunas + viga).
    Retorna dict com interacao maxima, drift, etc."""
    _aplica(cols_perfil, raf, fixed)
    a = est.analyse()
    drift = gp.analyse()["drift"]
    lim = gp.EAVE / 300.0
    nv = gp.N_VAOS
    # Interacao POR ELEMENTO (nao so a global): o guloso precisa saber QUAL peca
    # governa para subir a peca certa (senao esgota a coluna 0 antes da viga).
    int_cols = [0.0] * (nv + 1)
    int_raf = 0.0
    for combo in a["combos"]:
        for i in range(nv + 1):
            gc = combo[f"col_{i}"]
            sec = perfis.PERFIS[cols_perfil[i]]
            r = chk.verifica(sec, FY, gp.EAVE, Nsd=gc["Nsd"], Msd=gc["Msd"],
                             Vsd=gc["Vsd"], Kx=1.0, Ky=1.0, Lb=lb_col)
            int_cols[i] = max(int_cols[i], r["interacao"])
        for i in range(nv):
            for side in (0, 1):
                sname = "E" if side == 0 else "D"
                gv = combo[f"viga_{i}_{sname}"]
                r = chk.verifica(perfis.PERFIS[raf], FY, est.SEC_VIGAS[0]["L"],
                                 Nsd=gv["Nsd"], Msd=gv["Msd"], Vsd=gv["Vsd"],
                                 Kx=1.0, Ky=1.0, Lb=lb_raf)
                int_raf = max(int_raf, r["interacao"])
    worst_int = max(max(int_cols), int_raf)
    return {"cols": list(cols_perfil), "raf": raf, "B2": a["B2max"],
            "drift": drift, "lim_flecha": lim, "int_pior": worst_int,
            "int_cols": int_cols, "int_raf": int_raf,
            "peso": _peso(cols_perfil, raf), "passa": worst_int <= LIM_INT and drift <= lim}


def melhor(fixed=True, lb_col=LB_COL, lb_raf=LB_VIGA, seed=None):
    """Otimizacao GULOSA: comeca do mais leve, sobe o perfil da peca
    mais solicitada ate tudo passar. seed: (cols_tuple, raf) ou None."""
    nv = gp.N_VAOS
    # Perfil inicial
    col_leve = "HEA200" if "HEA200" in perfis.PERFIS else _ESC_COL[0]
    raf_leve = "HEA180" if "HEA180" in perfis.PERFIS else _ESC_RAF[0]
    cols = [col_leve] * (nv + 1)
    raf = raf_leve
    if seed:
        cols = list(seed[0]) if isinstance(seed, tuple) else [seed[0]] * (nv + 1)
        raf = seed[-1] if len(seed) > nv + 1 else seed[1] if nv == 0 else raf_leve
    iteracoes, max_iter = 0, 200
    while iteracoes < max_iter:
        iteracoes += 1
        r = avalia(cols, raf, fixed, lb_col, lb_raf)
        if r["passa"]:
            return {"aprovado": r, "candidatos": [r], "iteracoes": iteracoes,
                    "tabela": _tabela(r)}
        arts = []
        for i in range(nv + 1):
            try:
                idx = _ESC_COL.index(cols[i])
                if idx < _MAX_COL_IDX:
                    arts.append((r["int_cols"][i], "col", i, idx + 1))
            except ValueError:
                pass
        try:
            idx = _ESC_RAF.index(raf)
            if idx < _MAX_RAF_IDX:
                arts.append((r["int_raf"], "raf", 0, idx + 1))
        except ValueError:
            pass
        if not arts:
            break
        arts.sort(key=lambda x: -x[0])
        _, tipo, i, novo_idx = arts[0]
        if tipo == "col":
            cols[i] = _ESC_COL[novo_idx]
        else:
            raf = _ESC_RAF[novo_idx]
    # Ultimo teste com o que temos
    r = avalia(cols, raf, fixed, lb_col, lb_raf)
    return {"aprovado": r if r["passa"] else None, "candidatos": [r],
            "iteracoes": iteracoes, "tabela": _tabela(r)}


def _tabela(r):
    L = ["=" * 80, f"REDIMENSIONAMENTO - {gp.N_VAOS} vao(s) - otimizacao gulosa",
         f"Flecha: {r['drift']*1000:.1f}mm <= H/300 = {r['lim_flecha']*1000:.1f}mm",
         f"Interacao pior: {r['int_pior']:.2f}",
         "Perfis:"]
    for i, p in enumerate(r["cols"]):
        L.append(f"  Col {i}: {p}")
    L.append(f"  Viga: {r['raf']}")
    L += [f"  B2max = {r['B2']:.3f}",
          f"  {'PASSA' if r['passa'] else 'NAO PASSA'}"]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    r = melhor()
    print(r["tabela"])
    if r["aprovado"]:
        print(f"Aprovado: cols={r['aprovado']['cols']} raf={r['aprovado']['raf']}")
