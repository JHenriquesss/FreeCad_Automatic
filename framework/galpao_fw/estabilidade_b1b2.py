# ============================================================================
# estabilidade_b1b2.py - Analise de 2a ordem APROXIMADA (MAES, NBR 8800 Anexo D)
# Suporta 1 ou N vaos (multi-span). Decompoe cada combinacao ELU em nt/lt,
# calcula B1 (local) e B2 (global), e amplifica Msd/Nsd/Vsd por grupo de
# secoes (colunas por linha, vigas por tramo). Saidas em PT.
# ============================================================================
"""2a ordem aproximada (MAES) conforme NBR 8800 Anexo D. Multi-vao."""

from __future__ import annotations
import math, re
import numpy as np
import frame2d as f2d
import galpao_portico as gp
import vento_nbr6123 as vento

H_STORY = gp.EAVE
RS = 0.85
E = gp.E

# True quando as secoes por coluna sao definidas EXTERNAMENTE (redimensionamento
# multi-perfil, colunas com perfis distintos): sincronizar() NAO deve sobrescreve-
# las com a secao unica gp.A_COL/I_COL (senao o B1 por-coluna usaria o Ne errado).
SEC_COLS_EXTERNO = False

# Secoes: dict por grupo. Inicializado com uma coluna e uma viga (1 vao).
# Para N vaos: cols = [sec0, sec1, ...] (N+1), vigas = [sec0, ...] (N*2)
SEC_COLS = [{"A": gp.A_COL, "I": gp.I_COL, "L": gp.EAVE}]
SEC_VIGAS = [{"A": gp.A_RAF, "I": gp.I_RAF,
              "L": math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)}]


def reset():
    global SEC_COLS_EXTERNO, SEC_COLS, SEC_VIGAS
    SEC_COLS_EXTERNO = False
    SEC_COLS.clear()
    SEC_COLS.append({"A": gp.A_COL, "I": gp.I_COL, "L": gp.EAVE})
    SEC_VIGAS.clear()
    SEC_VIGAS.append({"A": gp.A_RAF, "I": gp.I_RAF,
                      "L": math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)})


_L_RAF = SEC_VIGAS[0]["L"]
GVERT = (gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * 2 * _L_RAF * gp.N_VAOS
QVERT = (gp.Q_ROOF * gp.BAY * gp.COS) * 2 * _L_RAF * gp.N_VAOS
PVERT = 0.0
FN_FRAC = 0.003


def sincronizar():
    global _L_RAF, GVERT, QVERT, H_STORY, PVERT
    global SEC_COLS, SEC_VIGAS
    nv = gp.N_VAOS
    # Replicar ou atualizar secoes das colunas
    while len(SEC_COLS) < nv + 1:
        SEC_COLS.append({"A": gp.A_COL, "I": gp.I_COL, "L": gp.EAVE})
    for i in range(nv + 1):
        if SEC_COLS_EXTERNO:
            SEC_COLS[i]["L"] = gp.EAVE       # preserva A/I por-coluna (multi-perfil)
        else:
            SEC_COLS[i].update(A=gp.A_COL, I=gp.I_COL, L=gp.EAVE)
    # Replicar secoes das vigas (2 por vao)
    L_raf = math.hypot(gp.SPANS[0] / 2, gp.RIDGE - gp.EAVE)
    while len(SEC_VIGAS) < nv * 2:
        SEC_VIGAS.append({"A": gp.A_RAF, "I": gp.I_RAF, "L": L_raf})
    for i in range(nv * 2):
        SEC_VIGAS[i].update(A=gp.A_RAF, I=gp.I_RAF, L=L_raf)
    _L_RAF = L_raf
    GVERT = (gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * 2 * _L_RAF * nv
    QVERT = (gp.Q_ROOF * gp.BAY * gp.COS) * 2 * _L_RAF * nv
    PVERT = abs(gp.PONTE["R_vert"]) if gp.PONTE else 0.0
    H_STORY = gp.EAVE


def _forca_nocional(combo):
    return FN_FRAC * (combo.get("G", 0.0) * GVERT + combo.get("Q", 0.0) * QVERT
                      + combo.get("PONTE", 0.0) * PVERT)


def _apply_case(fr, ix, cs, fac):
    nv = gp.N_VAOS
    if cs == "G":
        wy = -(gp.G_ROOF * gp.BAY + gp.RAFTER_SELF) * fac
        for i in range(nv):
            for side in (0, 1):
                for e in ix["rafts"][i][side]:
                    fr.add_member_udl(e, wy=wy)
    elif cs == "Q":
        wy = -(gp.Q_ROOF * gp.BAY * gp.COS) * fac
        for i in range(nv):
            for side in (0, 1):
                for e in ix["rafts"][i][side]:
                    fr.add_member_udl(e, wy=wy)
    elif cs in ("W1", "W2"):
        key = "portao_barlavento" if cs == "W1" else "portao_sotavento"
        r = vento.compute()
        q = r["q_kN_m2"]
        net = r["net"][key]
        for e in ix["cols"][0]:
            fr.add_member_udl(e, wx=+net["parede_barlavento"] * q * gp.BAY * fac)
        for e in ix["cols"][-1]:
            fr.add_member_udl(e, wx=-net["parede_sotavento"] * q * gp.BAY * fac)
        for i in range(nv):
            for side, sgn in ((0, -1), (1, +1)):
                lado = "barlavento" if side == 0 else "sotavento"
                p = net[f"cobertura_{lado}"] * q * gp.BAY * fac
                for e in ix["rafts"][i][side]:
                    fr.add_member_udl(e, wx=-p * sgn * gp.SIN, wy=-p * gp.COS)
    elif cs == "PONTE" and gp.PONTE:
        p = gp.PONTE
        if ix.get("nConsL") is not None:
            fr.add_nodal_load(ix["nConsL"], Fy=-abs(p["R_vert"]) * fac,
                              M=p["M_exc"] * fac, Fx=abs(p["H_transv"]) * fac)
    elif cs == "SISMO" and gp.SISMO:
        E_h = gp.SISMO["E"]
        n_e = len(ix["nEaves"])
        for ne in ix["nEaves"]:
            fr.add_nodal_load(ne, Fx=+E_h / n_e * fac)


def _apply_combo(fr, ix, combo):
    for cs, fac in combo.items():
        _apply_case(fr, ix, cs, fac)


def _combina_grupo(mf_nt, mf_lt, elems, B2, sec, Efac=1.0):
    Nsd1 = 0.0
    for e in elems:
        for Nint in (-(mf_nt[e][0] + mf_lt[e][0]),
                     (mf_nt[e][3] + mf_lt[e][3])):
            if Nint < Nsd1: Nsd1 = Nint
    Ne = math.pi ** 2 * (E * Efac) * sec["I"] / sec["L"] ** 2
    Cm = 1.0
    # B1 (amplificacao local P-delta). Se Nsd1 (compressao) >= Ne (carga critica de
    # Euler), denom<=0 -> flambagem LOCAL elastica (colapso): B1=inf (nao mascarar
    # com max(...,1)). Salvaguarda identica a do B2 (bug 8.16).
    if Nsd1 < 0:
        denom_b1 = 1.0 - abs(Nsd1) / Ne
        B1 = float("inf") if denom_b1 <= 0.0 else max(Cm / denom_b1, 1.0)
    else:
        B1 = 1.0
    Msd = Nsd = Vsd = Mnt = Mlt = 0.0
    for e in elems:
        for im, iN, iV, sgn in ((2, 0, 1, -1.0), (5, 3, 4, +1.0)):
            m = B1 * mf_nt[e][im] + B2 * mf_lt[e][im]
            n = sgn * (mf_nt[e][iN] + B2 * mf_lt[e][iN])
            v = mf_nt[e][iV] + mf_lt[e][iV]
            Msd = max(Msd, abs(m)); Nsd = max(Nsd, abs(n)); Vsd = max(Vsd, abs(v))
            Mnt = max(Mnt, abs(mf_nt[e][im])); Mlt = max(Mlt, abs(mf_lt[e][im]))
    return {"B1": B1, "Ne": Ne, "Nsd1": abs(Nsd1), "Mnt": Mnt, "Mlt": Mlt,
            "Msd": Msd, "Nsd": Nsd, "Vsd": Vsd}


def _scale_E(fr, fac):
    if fac != 1.0:
        for e in fr.elements:
            e["E"] *= fac


def _analisa_combo(nome, combo, Efac=1.0):
    nv = gp.N_VAOS
    fr, ix = gp._frame()
    _scale_E(fr, Efac)
    # Contencao ficticia em TODOS os beirais
    for ne in ix["nEaves"]:
        fr.add_support(ne, u=True)
    _apply_combo(fr, ix, combo)
    fr.solve()
    R0 = fr.reactions()
    Hap = -sum(R0[3 * ne] for ne in ix["nEaves"])
    sgn = 1.0 if Hap >= 0 else -1.0
    Fn = _forca_nocional(combo)
    for ne in ix["nEaves"]:
        fr.add_nodal_load(ne, Fx=sgn * Fn / len(ix["nEaves"]))
    _, mf_nt = fr.solve()
    R_nt = fr.reactions()
    Hfict = [R_nt[3 * ne] for ne in ix["nEaves"]]
    # sumN = reacoes verticais em TODAS as bases
    sumN = sum(R_nt[3 * b + 1] for b in ix["nBases"])
    # ---- lt: sem ficticias, carregada com -Hfict nos beirais ----------------
    fr2, ix2 = gp._frame()
    _scale_E(fr2, Efac)
    for i, ne in enumerate(ix2["nEaves"]):
        fr2.add_nodal_load(ne, Fx=-Hfict[i])
    d_lt, mf_lt = fr2.solve()
    sumH = sum(abs(h) for h in Hfict)
    dh = max(abs(d_lt[3 * ne]) for ne in ix2["nEaves"])
    # ---- B2 (global P-Delta) ------------------------------------------------
    if sumH < 1e-9:
        B2 = 1.0
    else:
        # denom = 1 - (1/Rs)*(dh*sumN)/(H*sumH). A parcela subtraida e a razao
        # entre a carga gravitacional do andar e a carga critica de flambagem
        # lateral global. Se denom <= 0, a carga vertical atingiu/superou a
        # critica -> INSTABILIDADE GLOBAL (colapso por P-Delta). B2 e sempre >= 1,0
        # (o efeito P-Delta so amplifica; nunca alivia).
        denom = 1.0 - (1.0 / RS) * (dh * sumN) / (H_STORY * sumH)
        B2 = float("inf") if denom <= 0.0 else max(1.0 / denom, 1.0)
    out = {"nome": nome, "B2": B2, "dh": dh, "sumN": sumN, "sumH": sumH, "Fn": Fn}
    # ---- esforcos amplificados por GRUPO ------------------------------------
    # Colunas: cada linha de coluna e um grupo (secao pode variar)
    gr_cols = {}
    for i in range(nv + 1):
        gr_cols[f"col_{i}"] = (ix["cols"][i], SEC_COLS[i])
        r = _combina_grupo(mf_nt, mf_lt, ix["cols"][i], B2, SEC_COLS[i], Efac)
        out[f"col_{i}"] = r
    # Viga: cada tramo lateral e seu proprio grupo (2 por vao)
    for i in range(nv):
        for side, sname in ((0, "E"), (1, "D")):
            idx = i * 2 + side
            r = _combina_grupo(mf_nt, mf_lt, ix["rafts"][i][side], B2,
                               SEC_VIGAS[idx], Efac)
            out[f"viga_{i}_{sname}"] = r
    # Retrocompatibilidade 1 vao: coluna e viga como antes
    if nv == 1:
        out["coluna"] = out["col_0"]
        out["viga"] = out["viga_0_E"]
        # pior entre os dois lados da viga
        if out["viga_0_D"]["Msd"] > out["viga_0_E"]["Msd"]:
            out["viga"] = out["viga_0_D"]
    return out


def _classe(B2max):
    if B2max <= 1.1:
        return "pequena deslocabilidade"
    if B2max <= 1.4:
        return "media deslocabilidade"
    return "GRANDE deslocabilidade"


def _combos_ativos():
    return gp._combos_elu(gp.PONTE, gp.SISMO)


def analyse():
    sincronizar()
    combos = _combos_ativos()
    base = [_analisa_combo(n, c, 1.0) for n, c in combos.items()]
    B2max0 = max(r["B2"] for r in base)
    classe = _classe(B2max0)
    reduziu = B2max0 > 1.1
    Efac = 0.8 if reduziu else 1.0
    final = [_analisa_combo(n, c, Efac) for n, c in combos.items()] if reduziu else base
    B2max_f = max(r["B2"] for r in final)
    # Limite de validade do MAES (NBR 8800 4.9.7 / Anexo D): 1,40 com rigidez
    # ORIGINAL (B2max0) ou 1,55 com rigidez REDUZIDA (B2max_f). Acima disso a
    # estrutura e de GRANDE deslocabilidade e o metodo aproximado nao e valido
    # (exige analise rigorosa de 2a ordem). B2 infinito = instabilidade global.
    maes_valido = (math.isfinite(B2max0) and math.isfinite(B2max_f)
                   and B2max0 <= 1.40 and B2max_f <= 1.55)
    return {"combos": final, "B2max": B2max_f, "B2max0": B2max0,
            "classe": classe, "reduziu": reduziu, "Efac": Efac,
            "maes_valido": maes_valido}


def memoria_pt(a):
    nv = gp.N_VAOS
    L = ["=" * 70,
         f"2a ORDEM (MAES) - NBR 8800 Anexo D - {nv} vao(s)",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
         f"Rs = {RS} ; H = {H_STORY:.1f} m ; E = {E/1e6:.0f} GPa", "",
         "COEFICIENTES POR COMBINACAO:"]
    for r in a["combos"]:
        L += [f"  {r['nome']}: B2 = {r['B2']:.3f}  "
              f"(dh={r['dh']*1000:.1f} mm ; sumN={r['sumN']:.1f} kN ; "
              f"sumH={r['sumH']:.1f} kN ; Fnocional={r['Fn']:.2f} kN)"]
        for gc in sorted([k for k in r if k.startswith("col_")], key=lambda x: int(x.split("_")[1])):
            d = r[gc]; L += [f"    {gc}: B1={d['B1']:.3f} Msd={d['Msd']:.1f} Nsd={d['Nsd']:.1f}"]
        for gv in sorted([k for k in r if k.startswith("viga_")], key=lambda x: (int(x.split("_")[1]), x.split("_")[2])):
            d = r[gv]
            if gv.endswith("_E"):
                L += [f"    {gv}: B1={d['B1']:.3f} Msd={d['Msd']:.1f} Nsd={d['Nsd']:.1f}"]
    L += ["", f"Deslocabilidade: B2max = {a['B2max0']:.3f} -> {a['classe']}"]
    if a["reduziu"]:
        L += [f"  Rigidez reduzida 80% ; B2max final = {a['B2max']:.3f}"]
    if not a.get("maes_valido", True):
        L += ["", "*** ATENCAO: MAES INVALIDO (NBR 8800 4.9.7) ***",
              "  B2 excede o limite (1,40 rigidez original / 1,55 reduzida) OU e",
              "  infinito (instabilidade global P-Delta). Estrutura de GRANDE",
              "  deslocabilidade: EXIGE analise rigorosa de 2a ordem e/ou enrijecer",
              "  o portico (aumentar secoes / adicionar contraventamento)."]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    print(memoria_pt(analyse()))
