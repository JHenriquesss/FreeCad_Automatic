# ============================================================================
# ponte_rolante.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Acao de PONTE ROLANTE em galpao industrial pela ABNT NBR 8800:2008 (+ NBR 8400
# para as classes). Fornece as cargas e verifica a VIGA DE ROLAMENTO, e empacota
# a reacao para o PORTICO (console/pilar). Referencia do metodo: livro
# "Dimensionamento de elementos estruturais de aco e mistos" (cap. 4) + NBR 8800.
#
# Tres direcoes de forca (item 4 do livro / NBR 8800):
#   VERTICAL: peso da ponte + trole + carga icada, MAJORADO pelo coef. de impacto
#     phi (do fabricante ou NBR 8400 - parametro A CONFIRMAR; 1,10 leve .. 1,25
#     pesada/siderurgica).
#   TRANSVERSAL (surto): percentual de (carga icada + trole), acel./desalinhamento
#     do trole; dividido entre as rodas. frac_lateral A CONFIRMAR (~0,10).
#   LONGITUDINAL (frenagem): percentual das cargas de roda no trilho; frenagem da
#     ponte. frac_long A CONFIRMAR (~0,10).
#
# Cargas de roda (Rmax/Rmin): ponte encostada, trole na aproximacao minima 'a' de
# um trilho -> reacao maxima naquele trilho; por roda = R_trilho / n_rodas.
#
# Viga de rolamento (vao = distancia entre porticos): momento por CARGA MOVEL (2
# rodas, formula do momento maximo absoluto - mecanica exata), flexao lateral do
# surto (eixo fraco), verificacao NBR 8800 (Anexo G + biaxial), flecha e FADIGA.
# ELS (NBR 8800): flecha vertical L/600 (<200 kN) / L/800 (>=200) / L/1000
# (siderurgica); horizontal L/400 (L/600 siderurgica); NAO majorar por impacto.
# Coluna: deslocamento no nivel da viga de rolamento <= Hvr/400.
# FADIGA (NBR 8800 Anexo K): CALCULA a faixa de tensoes da carga movel vertical
# (sigma_SR = Msdx/Wx) e compara com a faixa admissivel sigma_adm=(327*Cf/N)^0,333
# >= sigma_TH (K.4, Tabela K.1). A CATEGORIA do detalhe (default B = metal-base
# junto a solda longitudinal; enrijecedor/trilho pode ser C ou pior) e o numero de
# CICLOS N (regime, NBR 8400) sao INPUT (a skill pergunta) - nao inventa o detalhe.
#
# Generico e parametrico (dados da ponte = gate/fabricante). NAO inventa
# coeficientes normativos: phi, frac_lateral, frac_long entram flagados. Calcula
# apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Acao de ponte rolante + viga de rolamento - ABNT NBR 8800:2008 / NBR 8400."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck

GA1 = ck.GA1


def cargas_de_roda(Q, peso_ponte, peso_trole, vao_ponte, aprox_min, n_rodas_lado):
    """Reacao maxima/minima por roda (kN), ponte com trole na aproximacao minima.

    Q = capacidade icada ; pesos em kN ; vao_ponte = distancia entre trilhos (m) ;
    aprox_min = distancia minima do gancho ao trilho (m). O peso da ponte divide-se
    igualmente nos dois trilhos; a carga movel (Q+trole) vai por braco de alavanca.
    """
    S = vao_ponte
    movel = Q + peso_trole
    R_trilho_max = peso_ponte / 2.0 + movel * (S - aprox_min) / S
    R_trilho_min = peso_ponte / 2.0 + movel * aprox_min / S
    return (R_trilho_max / n_rodas_lado, R_trilho_min / n_rodas_lado,
            R_trilho_max, R_trilho_min)


def forcas_horizontais(Q, peso_trole, R_roda_max, n_rodas_lado, frac_lateral,
                       frac_long):
    """Forca transversal por roda (surto) e longitudinal por trilho (frenagem).
    NOTA (parecer 3.2): a frenagem age nas RODAS MOTORAS. Aqui frac_long incide
    sobre as cargas de roda do trilho; se so parte das rodas for motorizada, o
    eng. reduz frac_long por (n_motoras/n_rodas) na entrada (A CONFIRMAR)."""
    n_total = 2 * n_rodas_lado
    H_transv_roda = frac_lateral * (Q + peso_trole) / n_total
    H_long_trilho = frac_long * R_roda_max * n_rodas_lado
    return H_transv_roda, H_long_trilho


def _m_max_movel(P, d, L):
    """Momento maximo absoluto de 2 cargas iguais P espacadas d, vao L (biapoiada).
    Formula da mecanica (momento maximo absoluto): Mmax = (2P/L)*(L/2 - d/4)^2.
    Compara com uma roda so no meio (P*L/4) caso d seja grande."""
    if d < L:
        m2 = (2.0 * P / L) * (L / 2.0 - d / 4.0) ** 2
    else:
        m2 = 0.0
    return max(m2, P * L / 4.0)


def limite_flecha_vertical(cap_kN, siderurgica):
    """NBR 8800: L/600 (<200 kN) ; L/800 (>=200) ; L/1000 (siderurgica >=200)."""
    if siderurgica and cap_kN >= 200.0:
        return 1000.0
    if cap_kN >= 200.0:
        return 800.0
    return 600.0


# NBR 8800 Tabela K.1 - parametros de fadiga (valores lidos do PDF, nao de
# memoria): (Cf [x10^8], sigma_TH [MPa]). Categorias tipicas da viga de rolamento
# soldada: B = metal-base junto a solda longitudinal continua (mesa-alma);
# C = enrijecedores/ligacoes transversais soldadas; A = metal-base sem solda.
_FADIGA_K1 = {
    "A": (250e8, 165.0), "B": (120e8, 110.0), "B'": (61e8, 83.0),
    "C": (44e8, 69.0), "D": (22e8, 48.0), "E": (11e8, 31.0), "E'": (3.9e8, 18.0),
}


def faixa_admissivel_fadiga(cat, N):
    """NBR 8800 K.4a: sigma_SR = (327*Cf/N)^0,333 >= sigma_TH [MPa].
    Cf e sigma_TH da Tabela K.1 ; N = numero de ciclos na vida util."""
    Cf, sTH = _FADIGA_K1[cat]
    return max((327.0 * Cf / N) ** (1.0 / 3.0), sTH)


def verifica_fadiga(M_fad, Wx, cat="B", N=2.0e6, M_lat=0.0, Wy_top=None,
                    frac_lat=0.5):
    """Fadiga da viga de rolamento (NBR 8800 Anexo K). Faixa de variacao de
    tensoes (K.3, analise elastica) vs faixa admissivel (K.4).

    Carga de fadiga B.7.3.4 (lida do PDF): 1 ponte, cargas verticais majoradas
    pelo impacto + **50 % das forcas horizontais**. Logo a faixa de tensoes na
    fibra extrema da MESA SUPERIOR combina a flexao vertical e a lateral (surto):
        sigma_SR = M_fad/Wx + frac_lat*M_lat/Wy_top          (frac_lat = 0,50)
    M_fad e M_lat sao os momentos CARACTERISTICOS com impacto (a carga movel zera
    quando a ponte se afasta -> a faixa e ~ o proprio momento). Wy_top = modulo do
    BANZO SUPERIOR (o surto atua no topo do trilho). Sem Wy_top, so a vertical.
    M em kN.m ; W em m3 -> sigma em MPa. Retorna dict."""
    sig_x = (M_fad / Wx) / 1000.0                   # kN/m2 -> MPa (vertical)
    sig_y = (frac_lat * M_lat / Wy_top) / 1000.0 if (Wy_top and Wy_top > 0) else 0.0
    sig_sr = sig_x + sig_y                          # soma simples na fibra do topo
    sig_rd = faixa_admissivel_fadiga(cat, N)
    return {"sigma_sr": sig_sr, "sigma_sr_x": sig_x, "sigma_sr_y": sig_y,
            "sigma_rd": sig_rd, "cat": cat, "N": N,
            "u_fadiga": sig_sr / sig_rd if sig_rd > 0 else float("inf"),
            "ok": sig_sr <= sig_rd + 1e-9}


def verifica_viga_rolamento(sec, fy, cfg):
    """Viga de rolamento (perfil I) sob carga movel + surto lateral - NBR 8800.

    cfg: vao (m, entre porticos), P_vertical (kN, carga de roda majorada por
    impacto), H_transv (kN, surto por roda), d_rodas (m, base entre rodas),
    E_Ix (opcional, para flecha), cap_kN, siderurgica, phi (impacto).
    """
    L = cfg["vao"]
    P = cfg["P_vertical"]; Ht = cfg["H_transv"]; d = cfg.get("d_rodas", 0.0)
    Msdx = _m_max_movel(P, d, L)                    # flexao vertical (movel)
    Msdy = _m_max_movel(Ht, d, L)                   # flexao lateral (surto)
    # resistencias (Anexo G eixo forte ; eixo fraco plastico)
    Mnx, gov, det = ck.momento_resistente(sec, fy, cfg.get("Lb", L), cfg.get("Cb", 1.0))
    Mrdx = Mnx / GA1
    # Flexao lateral do surto atua no TOPO DO TRILHO -> so a MESA SUPERIOR resiste
    # (NBR 8800 / Fakury 4.4.2). Para I bissimetrico, ~metade das props globais;
    # para seca MONOSSIMETRICA (mesa sup com U/chapa de reforco) Wy_top != Wy/2 ->
    # aceitar override direto do banzo superior (parecer 4). Fallback = Wy/2.
    Wy = sec.get("Wy", sec["Iy"] / (sec["bf"] / 2.0))
    Zy = sec.get("Zy", 1.5 * Wy)
    Wy_top = sec.get("Wy_top", Wy / 2.0)
    Zy_top = sec.get("Zy_top", Zy / 2.0)
    Mrdy = min(Zy_top, 1.5 * Wy_top) * fy / GA1
    inter = Msdx / Mrdx + Msdy / Mrdy
    # flecha (carga movel SEM impacto, combinacao rara): P_carac = P/phi
    lim = limite_flecha_vertical(cfg["cap_kN"], cfg.get("siderurgica", False))
    flecha = None; flecha_ok = None
    if "E_Ix" in cfg and cfg["E_Ix"]:
        Pk = P / cfg.get("phi", 1.10)
        if 0.0 < d < L:                               # 2 rodas simetricas no vao
            flecha = Pk * (L - d) / (48.0 * cfg["E_Ix"]) * (2 * L ** 2 + 2 * L * d - d ** 2)
        else:                                         # 1 roda no meio
            flecha = Pk * L ** 3 / (48.0 * cfg["E_Ix"])
        flecha_ok = flecha <= L / lim
    # FADIGA (NBR 8800 Anexo K + B.7.3.4): vertical + 50% da lateral (surto) na
    # fibra da mesa superior. Wx do perfil ; Wy_top do banzo superior (surto no
    # topo do trilho). M_fad = Msdx e M_lat = Msdy (caracteristicos com impacto).
    Wx = sec.get("Wx", sec["Ix"] / (sec.get("d", sec.get("h", 1.0)) / 2.0))
    fad = verifica_fadiga(Msdx, Wx, cfg.get("cat_fadiga", "B"),
                          cfg.get("n_ciclos", 2.0e6),
                          M_lat=Msdy, Wy_top=Wy_top,
                          frac_lat=cfg.get("frac_fadiga_lat", 0.5))
    return {"tipo": "viga_rolamento", "nome": cfg.get("nome", "Viga de rolamento"),
            "L": L, "Msdx": Msdx, "Msdy": Msdy, "Mrdx": Mrdx, "Mrdy": Mrdy,
            "M_gov": gov, "inter": inter, "u_x": Msdx / Mrdx, "u_y": Msdy / Mrdy,
            "flecha_mm": None if flecha is None else flecha * 1000.0,
            "flecha_lim": lim, "flecha_ok": flecha_ok, "fadiga": fad,
            "OK": inter <= 1.0 and (flecha_ok in (None, True)) and fad["ok"],
            "fadiga_flag": ("FADIGA (Anexo K + B.7.3.4) cat.%s N=%.0e: sig_SR=%.0f "
                            "(vert %.0f + 50%% lat %.0f) <= sig_adm=%.0f MPa (u=%.2f). "
                            "Categoria do DETALHE real (enrijecedor/trilho/solda) e "
                            "nciclos do regime (NBR 8400) = A CONFIRMAR." %
                            (fad["cat"], fad["N"], fad["sigma_sr"], fad["sigma_sr_x"],
                             fad["sigma_sr_y"], fad["sigma_rd"], fad["u_fadiga"]))}


def reacao_no_portico(R_roda_max, n_rodas_lado, H_transv_roda, H_long_trilho,
                      excentricidade):
    """Empacota a reacao da viga de rolamento para o PORTICO (console/pilar).
    R_vert = soma das rodas no trilho ; M_exc = R_vert * excentricidade (trilho
    fora do eixo do pilar) ; H_transv e H_long entram na analise/contraventamento."""
    R_vert = R_roda_max * n_rodas_lado
    return {"R_vertical_kN": R_vert, "M_excentrico_kNm": R_vert * excentricidade,
            "H_transversal_kN": H_transv_roda * n_rodas_lado,
            "H_longitudinal_kN": H_long_trilho}


def relatorio_pt(esf, viga, reac):
    L = ["=" * 70, "PONTE ROLANTE (ABNT NBR 8800:2008 / NBR 8400)", "=" * 70,
         "  CARGAS DE RODA (ponte encostada, trole na aproximacao minima):",
         f"    R_roda_max = {esf['R_roda_max']:.1f} kN ; R_roda_min = {esf['R_roda_min']:.1f} kN",
         f"    Coef. de impacto phi = {esf['phi']:.2f} (A CONFIRMAR: fabricante/NBR 8400)",
         f"    P_vertical (com impacto) = {esf['P_vertical']:.1f} kN/roda",
         f"    Surto transversal = {esf['H_transv']:.1f} kN/roda "
         f"(frac {esf['frac_lateral']:.2f} A CONFIRMAR)",
         f"    Frenagem longitudinal = {esf['H_long']:.1f} kN/trilho "
         f"(frac {esf['frac_long']:.2f} A CONFIRMAR)",
         "-" * 70, "  VIGA DE ROLAMENTO (carga movel + surto lateral):",
         f"    Vao = {viga['L']:.2f} m ; Msd,x = {viga['Msdx']:.1f} kN.m ; "
         f"Msd,y = {viga['Msdy']:.1f} kN.m",
         f"    Mrd,x ({viga['M_gov']}) = {viga['Mrdx']:.1f} ; Mrd,y = {viga['Mrdy']:.1f} kN.m",
         f"    Interacao Mx/Mrdx+My/Mrdy = {viga['u_x']:.2f}+{viga['u_y']:.2f}="
         f"{viga['inter']:.2f} -> {'OK' if viga['inter'] <= 1 else 'NAO PASSA'}"]
    if viga["flecha_mm"] is not None:
        L.append(f"    Flecha vertical (sem impacto) = {viga['flecha_mm']:.1f} mm "
                 f"(limite L/{viga['flecha_lim']:.0f}) -> "
                 f"{'OK' if viga['flecha_ok'] else 'NAO'}")
    L += [f"    >> {viga['fadiga_flag']}",
          "-" * 70, "  REACAO NO PORTICO (console/pilar):",
          f"    R_vertical = {reac['R_vertical_kN']:.1f} kN ; M_excentrico = "
          f"{reac['M_excentrico_kNm']:.1f} kN.m",
          f"    H_transversal = {reac['H_transversal_kN']:.1f} kN ; H_longitudinal = "
          f"{reac['H_longitudinal_kN']:.1f} kN",
          "    (entram na analise do portico e no contraventamento longitudinal)",
          "  ELS: deslocamento no nivel da viga de rolamento <= Hvr/400 "
          "(50 mm siderurgica); diferencial entre pilares <= 15 mm.", "=" * 70]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def analisa(cfg):
    """Roda a cadeia da ponte a partir de um cfg (dados do fabricante/gate)."""
    Rmx, Rmn, Rtmx, Rtmn = cargas_de_roda(
        cfg["Q"], cfg["peso_ponte"], cfg["peso_trole"], cfg["vao_ponte"],
        cfg["aprox_min"], cfg["n_rodas_lado"])
    phi = cfg["phi"]
    Ht, Hl = forcas_horizontais(cfg["Q"], cfg["peso_trole"], Rmx,
                                cfg["n_rodas_lado"], cfg["frac_lateral"],
                                cfg["frac_long"])
    P = phi * Rmx
    esf = {"R_roda_max": Rmx, "R_roda_min": Rmn, "phi": phi, "P_vertical": P,
           "H_transv": Ht, "H_long": Hl, "frac_lateral": cfg["frac_lateral"],
           "frac_long": cfg["frac_long"]}
    vcfg = {"vao": cfg["vao_viga"], "P_vertical": P, "H_transv": Ht,
            "d_rodas": cfg.get("d_rodas", 0.0), "cap_kN": cfg["Q"],
            "siderurgica": cfg.get("siderurgica", False), "phi": phi,
            "Lb": cfg.get("Lb", cfg["vao_viga"]), "E_Ix": cfg.get("E_Ix"),
            "cat_fadiga": cfg.get("cat_fadiga", "B"),          # detalhe (Tab.K.1)
            "n_ciclos": cfg.get("n_ciclos", 2.0e6),            # regime (NBR 8400)
            "nome": "Viga de rolamento"}
    viga = verifica_viga_rolamento(cfg["perfil_viga"], cfg["fy"], vcfg)
    reac = reacao_no_portico(Rmx, cfg["n_rodas_lado"], Ht, Hl,
                             cfg.get("excentricidade", 0.30))
    return esf, viga, reac


# --- perfil de viga de rolamento (exemplo; A CONFIRMAR no catalogo) ----------
VS500 = {"A": 98.0e-4, "Ix": 40000e-8, "Iy": 2000e-8, "ry": 0.045,
         "Zx": 1800e-6, "Wx": 1600e-6, "Zy": 300e-6, "Wy": 200e-6,
         "d": 0.500, "bf": 0.250, "tf": 0.016, "tw": 0.008,
         "_fonte": "A CONFIRMAR (perfil soldado VS ; props do catalogo)"}


def _selftest():
    # Ponte de 100 kN (10 tf), vao 10 m (entre trilhos ~ vao do galpao), viga de
    # rolamento no BAY de 5 m. Coeficientes tipicos (A CONFIRMAR fabricante/8400).
    cfg = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "vao_ponte": 9.5,
           "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10, "frac_lateral": 0.10,
           "frac_long": 0.10, "vao_viga": 5.0, "d_rodas": 3.0, "fy": 250e3,
           "perfil_viga": VS500, "siderurgica": False, "excentricidade": 0.30,
           "E_Ix": ck.E * VS500["Ix"]}
    esf, viga, reac = analisa(cfg)
    print(relatorio_pt(esf, viga, reac))
    assert esf["R_roda_max"] > esf["R_roda_min"]
    assert viga["Msdx"] > 0 and viga["inter"] > 0
    assert reac["R_vertical_kN"] > 0 and reac["M_excentrico_kNm"] > 0
    # FADIGA (Anexo K): faixa admissivel e a formula K.4 conferidas contra o PDF
    import math as _m
    assert abs(faixa_admissivel_fadiga("A", 2e6) - max((327.0*250e8/2e6)**(1/3), 165.0)) < 1e-6
    assert faixa_admissivel_fadiga("C", 1e5) > 69.0            # poucos ciclos -> > sigma_TH
    assert abs(faixa_admissivel_fadiga("E", 1e9) - 31.0) < 1e-6   # muitos ciclos -> piso sigma_TH
    fad = viga["fadiga"]
    # B.7.3.4: vertical + 50% da lateral no banzo superior (Wy_top = Wy/2 fallback)
    Wy_top = VS500["Wy"] / 2.0
    sr_exp = (viga["Msdx"]/VS500["Wx"])/1000.0 + 0.5*viga["Msdy"]/Wy_top/1000.0
    assert abs(fad["sigma_sr"] - sr_exp) < 1e-6, (fad["sigma_sr"], sr_exp)
    assert fad["sigma_sr_y"] > 0 and fad["sigma_sr"] > fad["sigma_sr_x"]   # lateral entra
    assert fad["ok"] and 0 < fad["u_fadiga"] < 1.0            # VS500 passa a fadiga
    # categoria pior (E') aperta a faixa admissivel
    assert faixa_admissivel_fadiga("E'", 2e6) < faixa_admissivel_fadiga("B", 2e6)
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
