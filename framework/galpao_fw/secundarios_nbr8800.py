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

# UPE maiores (EN 10365) para a escada da longarina. Fonte: structolution.com
# (props, It=J e Iw=Cw). A CONFIRMAR no catalogo do fornecedor (Gerdau/AM).
UPE120 = {"nome": "UPE120", "A": 15.40e-4,
          "Ix": 364e-8, "Wx": 60.6e-6, "Zx": 70.3e-6, "rx": 0.0486,
          "Iy": 55.5e-8, "Wy": 13.8e-6, "Zy": 24.8e-6, "ry": 0.0190,
          "d": 0.120, "bf": 0.060, "tf": 0.0080, "tw": 0.0050,
          "J": 2.90e-8, "Cw": 1.120e-9, "_fonte": "structolution.com EN10365 - A CONFIRMAR"}
UPE140 = {"nome": "UPE140", "A": 18.40e-4,
          "Ix": 600e-8, "Wx": 85.6e-6, "Zx": 98.8e-6, "rx": 0.0571,
          "Iy": 78.8e-8, "Wy": 18.2e-6, "Zy": 32.58e-6, "ry": 0.0207,
          "d": 0.140, "bf": 0.065, "tf": 0.0090, "tw": 0.0050,
          "J": 4.05e-8, "Cw": 2.200e-9, "_fonte": "structolution.com EN10365 - A CONFIRMAR"}
UPE160 = {"nome": "UPE160", "A": 21.70e-4,
          "Ix": 911e-8, "Wx": 114e-6, "Zx": 132e-6, "rx": 0.0648,
          "Iy": 107e-8, "Wy": 22.6e-6, "Zy": 40.72e-6, "ry": 0.0222,
          "d": 0.160, "bf": 0.070, "tf": 0.0095, "tw": 0.0055,
          "J": 5.20e-8, "Cw": 3.960e-9, "_fonte": "structolution.com EN10365 - A CONFIRMAR"}
UPE180 = {"nome": "UPE180", "A": 25.10e-4,
          "Ix": 1350e-8, "Wx": 150e-6, "Zx": 173e-6, "rx": 0.0734,
          "Iy": 144e-8, "Wy": 28.6e-6, "Zy": 51.47e-6, "ry": 0.0239,
          "d": 0.180, "bf": 0.075, "tf": 0.0105, "tw": 0.0055,
          "J": 6.99e-8, "Cw": 6.810e-9, "_fonte": "structolution.com EN10365 - A CONFIRMAR"}
# Escada da longarina, do mais leve ao mais pesado.
ESCADA_UPE = [UPE100, UPE120, UPE140, UPE160, UPE180]

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
    """Mrd,y = min(Zy ; 1,5*Wy)*fy / ga1 (5.4.2, sem FLT no eixo fraco).
    PREMISSA (parecer senior 3.1): a flexao no eixo Y (peso do tapamento)
    TRACIONA as pontas das abas e comprime a alma -> sem FLM critica nas abas.
    Se houver inversao que comprima as pontas das abas, incluir FLM (bf/tf)."""
    return min(sec["Zy"], 1.5 * sec["Wy"]) * fy / GA1


def verifica_longarina(sec, fy, cfg):
    """Longarina de parede (girt, perfil U) - flexao biaxial NBR 8800.

    cfg (do gate): vao (m, = distancia entre porticos), q_vento (kN/m2, pressao
    liquida na parede, do modulo vento), trib (m, altura de influencia da
    longarina), g_tapamento (kN/m2, peso do fechamento), n_tirantes (linhas de
    tirante de parede), continua (bool), gamma (dict opcional).

    PREMISSA (parecer senior 3.2): o centro de cisalhamento do U fica FORA da
    secao (atras da alma). O vento na alma induz TORCAO. A interacao biaxial so
    e valida se o tapamento (telha parafusada) TRAVAR O GIRO da secao; senao o U
    fica subdimensionado. Confirmar a fixacao do tapamento (gate).
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


def _util(r):
    """Utilizacao de um resultado (longarina usa 'inter'; escora/montante usa
    'interacao' do check)."""
    return r.get("inter", r.get("interacao"))


def _passa(r):
    if r.get("OK") is not None:
        return bool(r["OK"])
    u = _util(r)
    return u is not None and u <= 1.0


def dimensiona_secundarios(fy, cfg_long, cfg_esc, cfg_mont,
                           n_tir_seed=2, n_tir_max=6):
    """Dimensiona as secoes SECUNDARIAS ao esforco real:
      - longarina (U): aumenta as LINHAS DE TIRANTE (sag rods) ate passar (reduz o
        Lb do FLT). Sem inventar dados de catalogo (so geometria);
      - escora/cumeeira e montante (I): sobem na escada HEA ate passar.
    Retorna o dict com perfil/tirantes adotados + utilizacao + ok de cada um."""
    import perfis
    # --- longarina: escada UPE x linhas de tirante (sag rods). Adota o UPE mais
    # leve que passa, esgotando os tirantes antes de subir o perfil. ---
    long_r, long_perf, nt_ad = None, UPE100, n_tir_seed
    achou = False
    for perf in ESCADA_UPE:
        for nt in range(n_tir_seed, n_tir_max + 1):
            long_r, long_perf, nt_ad = (verifica_longarina(
                perf, fy, dict(cfg_long, n_tirantes=nt)), perf, nt)
            if _passa(long_r):
                achou = True
                break
        if achou:
            break
    # --- escora / montante: escada HEA (160 -> 220) ---
    HEA = [("HEA160", HEA160)] + [(nm, perfis.PERFIS[nm])
                                  for nm in ("HEA180", "HEA200", "HEA220")
                                  if nm in perfis.PERFIS]

    def _sobe(verif, cfg):
        best = None
        for nm, sec in HEA:
            r = verif(sec, fy, cfg)
            if best is None:
                best = (nm, r)
            if _passa(r):
                return (nm, r)
        return best
    esc_nm, esc_r = _sobe(verifica_escora, cfg_esc)
    mnt_nm, mnt_r = _sobe(verifica_montante_oitao, cfg_mont)
    return {
        "longarina": {"perfil": long_perf.get("nome", "UPE100"),
                      "dims": (long_perf["d"] * 1000, long_perf["bf"] * 1000,
                               long_perf["tw"] * 1000, long_perf["tf"] * 1000),
                      "n_tirantes": nt_ad, "inter": _util(long_r),
                      "ok": _passa(long_r)},
        "escora": {"perfil": esc_nm, "inter": _util(esc_r), "ok": _passa(esc_r)},
        "montante": {"perfil": mnt_nm, "inter": _util(mnt_r), "ok": _passa(mnt_r)},
        "resultados": {"longarina": long_r, "escora": esc_r, "montante": mnt_r},
    }


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


def verifica_montante_oitao(sec, fy, cfg):
    """Montante de oitao (poste do frontao, perfil I) - flexo-compressao NBR 8800.

    Poste vertical na empena, biapoiado (base + viga do oitao), sob VENTO normal
    ao frontao (flexao no eixo forte) + axial de gravidade pequeno. As longarinas
    do oitao travam o eixo fraco (Lb = espacamento das longarinas).
    cfg (do gate): altura (m, altura do poste governante = mais alto), q_gable
    (kN/m2, pressao liquida na empena = |Cpe-Cpi| pior * q), trib (m, espacamento
    entre montantes), Nsd (kN, axial de gravidade), Lb (m), gamma_W.
    """
    H = cfg["altura"]
    gW = cfg.get("gamma_W", 1.40)
    w = cfg["q_gable"] * cfg["trib"]               # linha de vento (kN/m)
    Msd = gW * w * H ** 2 / 8.0                     # biapoiado
    Vsd = gW * w * H / 2.0
    Nsd = cfg.get("Nsd", 5.0)                       # gravidade (pequeno) - A CONFIRMAR
    Lb = cfg.get("Lb", H)
    res = ck.verifica(sec, fy, L=H, Nsd=Nsd, Msd=Msd, Vsd=Vsd,
                      Kx=1.0, Ky=1.0, Lb=Lb, Cb=cfg.get("Cb", 1.0),
                      nome=cfg.get("nome", "Montante de oitao (HEA160)"))
    res["tipo"] = "escora"                          # mesmo layout de relatorio (perfil I)
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
        L += ["  PREMISSA: interacao biaxial valida so se o tapamento (telha",
              "  parafusada) TRAVAR o giro do U (centro de cisalhamento fora da",
              "  secao induz torcao). Flexao no eixo Y traciona as abas (sem FLM)."]
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
    # Montante de oitao HEA160: vento na empena (net barlavento ~+1,30*q), poste
    # ~6,33 m, trib 3,33 m, travado pelas longarinas do oitao (Lb=2 m).
    cfg_m = {"altura": 6.33, "q_gable": 1.30 * q, "trib": 3.33, "Nsd": 5.0,
             "Lb": 2.0, "nome": "Montante de oitao (HEA160)"}
    rm = verifica_montante_oitao(HEA160, fy, cfg_m)
    print("\n" + relatorio_pt(rm))
    assert "interacao" in rm
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
