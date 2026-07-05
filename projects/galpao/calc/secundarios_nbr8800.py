# ============================================================================
# secundarios_nbr8800.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica as PECAS SECUNDARIAS de perfil laminado pela ABNT NBR 8800:2008 que
# o resto do toolkit ainda nao cobria:
#   (1) LONGARINA DE PAREDE (girt, perfil U laminado) - flexao BIAXIAL:
#       - eixo forte (x): vento normal a parede (pressao/succao), vao = distancia
#         entre porticos; mesa comprimida sob SUCCAO travada por linha(s) de
#         tirante de parede -> Lb = vao/(n_tirantes+1).
#       - eixo fraco (y): peso do tapamento + peso proprio; vao = idem eixo forte
#         reduzido pelos tirantes.
#       - interacao de flexao biaxial (5.5.1, N=0): Mx/Mrdx + My/Mrdy <= 1.
#       - Mrdx: Anexo G completo (FLT+FLM+FLA). O FLT do U usa J e Cw do U vindos
#         do CATALOGO (nao de formula de I) - dado marcado "A CONFIRMAR"; o METODO
#         (G.2) e o mesmo do check. Sem J/Cw no dict -> INCONCLUSIVO (nao inventa).
#       - Mrdy = min(Zy, 1,5*Wy)*fy / ga1 (5.4.2, sem FLT no eixo fraco).
#   (2) ESCORA DE BEIRAL / CUMEEIRA (perfil I laminado) - FLEXO-COMPRESSAO:
#       axial do contraventamento longitudinal (vento no oitao) + flexao do peso
#       proprio no vao entre porticos. Reusa check_nbr8800.verifica (perfil I).
#
# Generico e parametrico: TODAS as cargas/geometrias sao parametros (cfg) que a
# skill pergunta ao usuario no gate (peso do tapamento, n de tirantes, pressao de
# vento, axial da escora, etc.). Defaults = galpao 20x10 de referencia, cada um
# marcado "A CONFIRMAR". NAO calcula esforcos globais nem inventa dados de
# catalogo. Calcula apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Verificacao de pecas secundarias (longarina U, escora I) - NBR 8800:2008."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck

E = ck.E          # 200e6 kN/m2
GA1 = ck.GA1      # 1,10

# --- Propriedades de catalogo (SI). A CONFIRMAR no catalogo do fornecedor -----
# Perfil U laminado (UPE, abas paralelas). Inclui eixo fraco (Iy, Wy, Zy) para a
# flexao biaxial. Valores nominais europeus - CONFERIR (Gerdau/ArcelorMittal).
UPE100 = {"nome": "UPE100", "A": 12.53e-4,
          "Ix": 207e-8, "Wx": 41.4e-6, "Zx": 48.8e-6, "rx": 0.0407,
          "Iy": 38.3e-8, "Wy": 12.9e-6, "Zy": 23.5e-6, "ry": 0.0175,
          "d": 0.100, "bf": 0.055, "tf": 0.0075, "tw": 0.0045,
          # Torcao/empenamento do U (para o FLT, Anexo G): CATALOGO, nao formula.
          "J": 2.01e-8, "Cw": 7.9e-10,
          "_fonte": "A CONFIRMAR no catalogo (props, J e Cw)"}

# Perfil I/H para escora/cumeeira (formato aceito por check_nbr8800.verifica).
HEA160 = {"A": 38.77e-4, "Ix": 1673e-8, "Iy": 615.6e-8, "ry": 0.0398,
          "Zx": 245.1e-6, "Wx": 220.1e-6, "d": 0.152, "bf": 0.160,
          "tf": 0.009, "tw": 0.006, "_fonte": "A CONFIRMAR no catalogo"}


def _mrd_eixo_forte_U(sec, fy, Lb, Cb=1.0):
    """Mrd,x do perfil U (kN.m) pelo Anexo G (FLT, FLM, FLA). Mesmas formulas de
    check_nbr8800.momento_resistente, mas J e Cw vem do CATALOGO do U (nao de
    formula de I). Se faltarem J/Cw no dict -> INCONCLUSIVO (nao inventa)."""
    if "Cw" not in sec or "J" not in sec:
        return None, "INCONCLUSIVO: faltam J/Cw do U (catalogo) para o FLT.", {
            "Lp": None, "compacto": None}
    Zx, Wx, Iy = sec["Zx"], sec["Wx"], sec["Iy"]
    bf, tf, d, tw, ry = sec["bf"], sec["tf"], sec["d"], sec["tw"], sec["ry"]
    Cw, J = sec["Cw"], sec["J"]
    rE = math.sqrt(E / fy)
    h = d - 2 * tf
    Mpl = Zx * fy
    sr = 0.3 * fy
    # FLM (mesa, elemento AL): b/t da aba do U
    lam_m = bf / tf; lamp_m = 0.38 * rE; lamr_m = 0.83 * math.sqrt(E / (fy - sr))
    Mcr_m = 0.69 * E * Wx / lam_m ** 2
    Mn_flm = ck._interp_M(lam_m, lamp_m, lamr_m, Mpl, (fy - sr) * Wx, Mcr_m)
    # FLA (alma): h/tw
    lam_a = h / tw; lamp_a = 3.76 * rE; lamr_a = 5.70 * rE
    Mn_fla = ck._interp_M(lam_a, lamp_a, lamr_a, Mpl, fy * Wx, Mpl)
    # FLT (Anexo G, com J e Cw do catalogo)
    lam = Lb / ry; lamp = 1.76 * rE
    Mr = (fy - sr) * Wx
    b1 = Mr / (E * J)
    lamr = (1.38 * math.sqrt(Iy * J)) / (ry * J * b1) * \
        math.sqrt(1 + math.sqrt(1 + 27 * Cw * b1 ** 2 / Iy))
    Mcr = (Cb * math.pi ** 2 * E * Iy / Lb ** 2) * \
        math.sqrt(Cw / Iy + 0.039 * J * Lb ** 2 / Iy)
    Mn_flt = ck._interp_M(lam, lamp, lamr, Mpl, Mr, Mcr, Cb)
    Mn = min(Mn_flt, Mn_flm, Mn_fla)
    gov = ["FLT", "FLM", "FLA"][[Mn_flt, Mn_flm, Mn_fla].index(Mn)]
    return Mn / GA1, gov, {"Lp": lamp * ry, "Lr": lamr * ry,
                           "compacto": lam_m <= lamp_m and lam_a <= lamp_a,
                           "Mn_flt": Mn_flt, "Mn_flm": Mn_flm, "Mn_fla": Mn_fla}


def _mrd_eixo_fraco(sec, fy):
    """Mrd,y = min(Zy ; 1,5*Wy)*fy / ga1 (5.4.2, sem FLT no eixo fraco)."""
    return min(sec["Zy"], 1.5 * sec["Wy"]) * fy / GA1


def verifica_longarina(sec, fy, cfg):
    """Longarina de parede (girt, perfil U) - flexao biaxial NBR 8800.

    cfg (do gate): vao (m, = distancia entre porticos), q_vento (kN/m2, pressao
    liquida na parede, do modulo vento), trib (m, altura de influencia da
    longarina), g_tapamento (kN/m2, peso do fechamento), n_tirantes (linhas de
    tirante de parede), continua (bool), gamma (dict opcional).
    """
    vao = cfg["vao"]; g = cfg.get("gamma", {})
    gW = g.get("W", 1.40); gG = g.get("G", 1.25)   # ELU (Tabela 1)
    n_t = cfg.get("n_tirantes", 1)
    Lb = vao / (n_t + 1)                            # destravamento (eixo forte, succao)
    Ly = vao / (n_t + 1)                            # vao do eixo fraco (peso) c/ tirante
    # linhas de carga caracteristicas (kN/m)
    qx = cfg["q_vento"] * cfg["trib"]              # vento normal -> eixo forte
    qy = (cfg["g_tapamento"] + cfg.get("peso_proprio", 0.10)) * cfg["trib"]  # peso -> fraco
    # coeficientes estaticos (biapoiada ou continua)
    cM = 1.0 / 10.0 if cfg.get("continua") else 1.0 / 8.0
    # momentos solicitantes ELU
    Msdx = gW * qx * vao ** 2 * cM
    Msdy = gG * qy * Ly ** 2 * cM
    # resistencias
    Mrdx, modo_x, detx = _mrd_eixo_forte_U(sec, fy, Lb)
    Mrdy = _mrd_eixo_fraco(sec, fy)
    r = {"tipo": "longarina", "nome": sec.get("nome", "U"), "vao": vao, "Lb": Lb,
         "Ly": Ly, "qx": qx, "qy": qy, "Msdx": Msdx, "Msdy": Msdy,
         "Mrdx": Mrdx, "modo_x": modo_x, "Mrdy": Mrdy, "Lp": detx["Lp"],
         "compacto": detx["compacto"]}
    if Mrdx is None:
        r.update(inter=None, OK=False)
        return r
    inter = Msdx / Mrdx + Msdy / Mrdy               # 5.5.1 biaxial (N=0)
    r.update(inter=inter, u_x=Msdx / Mrdx, u_y=Msdy / Mrdy, OK=inter <= 1.0)
    return r


def verifica_escora(sec, fy, cfg):
    """Escora de beiral / cumeeira (perfil I) - flexo-compressao NBR 8800.

    cfg (do gate): vao (m), Nsd (kN, axial de compressao do contraventamento
    longitudinal), peso_proprio (kN/m), Lb (m, travamento lateral), Cb.
    Reusa check_nbr8800.verifica (mesma verificacao do portico).
    """
    vao = cfg["vao"]
    qz = cfg.get("peso_proprio", 0.31)             # kN/m (peso proprio HEA160 ~0,30)
    gG = cfg.get("gamma_G", 1.25)
    Msd = gG * qz * vao ** 2 / 8.0                  # flexao do peso proprio no vao
    Vsd = gG * qz * vao / 2.0
    Nsd = cfg["Nsd"]                               # axial (A CONFIRMAR: vento long.)
    Lb = cfg.get("Lb", vao)
    res = ck.verifica(sec, fy, L=vao, Nsd=Nsd, Msd=Msd, Vsd=Vsd,
                      Kx=1.0, Ky=1.0, Lb=Lb, Cb=cfg.get("Cb", 1.0),
                      nome=cfg.get("nome", "Escora/cumeeira (HEA160)"))
    res["tipo"] = "escora"
    return res


def relatorio_pt(r):
    if r["tipo"] == "longarina":
        L = ["=" * 68, f"LONGARINA DE PAREDE (perfil U) - {r['nome']}",
             "NBR 8800 Anexo G + interacao biaxial (vento eixo forte, peso fraco)",
             "=" * 68,
             f"  Vao (entre porticos) ........ {r['vao']:.2f} m",
             f"  Lb (mesa interna, succao) ... {r['Lb']:.2f} m  (Lp={r['Lp']:.2f} m ; "
             f"compacto={r['compacto']})",
             f"  qx (vento) .................. {r['qx']:.3f} kN/m -> Msdx={r['Msdx']:.2f} kN.m",
             f"  qy (peso) ................... {r['qy']:.3f} kN/m -> Msdy={r['Msdy']:.2f} kN.m"]
        if r["Mrdx"] is None:
            L += [f"  Mrd,x ....................... {r['modo_x']}",
                  "  >> NAO CONCLUI: ver modo_x acima."]
        else:
            L += [f"  Mrd,x ({r['modo_x']}) = {r['Mrdx']:.2f} kN.m",
                  f"  Mrd,y (min(Zy;1,5Wy)*fy) .... {r['Mrdy']:.2f} kN.m",
                  f"  Interacao Mx/Mrdx+My/Mrdy ... {r['u_x']:.2f}+{r['u_y']:.2f}="
                  f"{r['inter']:.2f} -> {'OK' if r['OK'] else 'NAO PASSA'}"]
        L.append("=" * 68)
        out = "\n".join(L)
    else:
        out = ck.relatorio_pt([r], r.get("fy_MPa", 250) * 1e3 if False else 250e3)
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", out)


def _selftest():
    import vento_nbr6123 as vento
    fy = 250e3
    q = vento.compute()["q_kN_m2"]                  # pressao dinamica de referencia
    # Longarina UPE100: vento de succao pior na parede (|net|=1,40*q), trib 2,0 m,
    # tapamento 0,10 kN/m2, vao = BAY 5 m. Com 1 tirante NAO passa; com 2 passa.
    base = {"vao": 5.0, "q_vento": 1.40 * q, "trib": 2.0, "g_tapamento": 0.10,
            "peso_proprio": 0.10, "continua": False}
    r1 = verifica_longarina(UPE100, fy, {**base, "n_tirantes": 1})
    r2 = verifica_longarina(UPE100, fy, {**base, "n_tirantes": 2})
    print(relatorio_pt(r2))
    assert r1["OK"] is False and r2["OK"] is True   # + tirante -> menor Lb -> passa
    assert r2["inter"] < r1["inter"]
    # Escora HEA160: axial do vento longitudinal (A CONFIRMAR) + peso proprio, vao 5 m
    cfg_esc = {"vao": 5.0, "Nsd": 60.0, "peso_proprio": 0.31, "Lb": 5.0,
               "nome": "Escora de beiral (HEA160)"}
    re_ = verifica_escora(HEA160, fy, cfg_esc)
    print("\n" + relatorio_pt(re_))
    assert re_["OK"] and "interacao" in re_
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
