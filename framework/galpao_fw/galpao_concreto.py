# ============================================================================
# galpao_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Orquestra o dimensionamento de um GALPAO DE CONCRETO PRE-MOLDADO (sistema padrao
# industrial brasileiro): PILARES ENGASTADOS NA BASE (via calice/colarinho) e livres
# no topo -> resistem ao vento como balanco (flexo-composta + 2a ordem, le=2H,
# alpha_b de balanco); VIGA DE COBERTURA biapoiada sobre os topos; SAPATA sob cada
# pilar. Reaproveita todo o motor ja existente e agnostico ao material:
#   - vento_nbr6123.compute  (NBR 6123): pressao q e Cpe das paredes;
#   - viga_concreto           (NBR 6118): viga de cobertura;
#   - pilar_concreto          (NBR 6118): pilar em flexo-compressao;
#   - fundacao_sapata         (NBR 6122/6118): sapata sob a reacao de base.
# STATELESS por design: rodar(spec) recebe um dict explicito (sem estado global -
# evita a classe de bug _CFG). Combinacoes ELU (NBR 8681): (1) gravidade principal
# 1,4G+1,4Q+1,4*0,6W ; (2) vento principal 1,0G+1,4W (N minimo, critico p/ o pilar).
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues. Dados de projeto (v0,
# solo, telha) marcados A CONFIRMAR - nunca inventados.
# ============================================================================
"""Galpao de concreto pre-moldado (pilar engastado + viga de cobertura + sapata),
NBR 6118/6123/6122. Orquestrador STATELESS: rodar(spec) -> gates ATENDE/REPROVA."""

from __future__ import annotations

import math

import vento_nbr6123 as vento
import viga_concreto as vc
import viga_protendida as vp
import pilar_concreto as pc
import fundacao_sapata as fs
import premoldado_nbr9062 as pm
import fogo_nbr15200 as fogo

GF = 1.4
PSI0_VENTO = 0.6                    # fator de combinacao do vento (NBR 8681 Tab.1)
PSI0_SOBRECARGA = 0.7              # sobrecarga de cobertura
GAMMA_CONC = 25.0                  # peso especifico do concreto (kN/m3)

# escadas de secao (adota a MENOR que passa). Pilar: hx (// vento) >= hy.
_SECOES_PILAR = [(0.20, 0.40), (0.20, 0.50), (0.25, 0.50), (0.30, 0.50),
                 (0.30, 0.60), (0.30, 0.70), (0.40, 0.70), (0.40, 0.90)]
_SECOES_VIGA = [(0.20, 0.40), (0.20, 0.50), (0.20, 0.60), (0.25, 0.60),
                (0.25, 0.70), (0.30, 0.80), (0.30, 1.00)]


def _dimensiona_pilar_secao(Nk_g, Nk_gq, M_w_k, H, fck, fyk):
    """Adota a MENOR secao de pilar que atende as 2 combinacoes ELU. hx (=h) e a
    dimensao no plano do vento (resiste ao momento de base). Retorna dict."""
    # Biaxial (17.2.5): o vento transversal atua numa direcao (x, plano do portico)
    # e o momento MINIMO (11.3.3.4.3) coexiste na direcao perpendicular (y). Ventos
    # perpendiculares NAO se somam (NBR 6123, um por vez) -> a envoltoria biaxial e
    # Mx_vento + My_min. forcar_biaxial ativa a interacao obliqua com o My minimo.
    for (hy, hx) in _SECOES_PILAR:
        # comb 1 (gravidade principal): Nd=1,4(G+Q), M=1,4*0,6*M_w
        c1 = pc.dimensiona_pilar({"b": hy, "h": hx, "Nk": Nk_gq, "le_x": 2 * H,
            "le_y": 2 * H, "fck": fck, "fyk": fyk, "dl": 0.04, "gamma_f": GF,
            "forcar_biaxial": True,
            "M1d_x": {"tipo": "balanco", "Ma": GF * PSI0_VENTO * M_w_k}})
        # comb 2 (vento principal): Nd=1,0*G (minimo), M=1,4*M_w
        c2 = pc.dimensiona_pilar({"b": hy, "h": hx, "Nk": Nk_g, "le_x": 2 * H,
            "le_y": 2 * H, "fck": fck, "fyk": fyk, "dl": 0.04, "gamma_f": 1.0,
            "forcar_biaxial": True,
            "M1d_x": {"tipo": "balanco", "Ma": GF * M_w_k}})
        gov = c1 if c1["As_cm2"] >= c2["As_cm2"] else c2
        gov = gov if (c1["OK"] and c2["OK"]) else dict(gov, OK=(c1["OK"] and c2["OK"]))
        if c1["OK"] and c2["OK"]:
            gov["comb1_As"] = c1["As_cm2"]; gov["comb2_As"] = c2["As_cm2"]
            return gov
    gov["comb1_As"] = c1["As_cm2"]; gov["comb2_As"] = c2["As_cm2"]
    return gov


def rodar(spec):
    """Dimensiona o galpao de concreto e devolve os gates.
    spec: {
      'vao'         : largura do galpao (m).
      'comprimento' : comprimento (m). 'n_porticos' : nº de porticos transversais.
      'pe_direito'  : altura da coluna H (m). 'theta_graus' (inclinacao, default 5,71).
      'v0'          : velocidade basica do vento (m/s) [A CONFIRMAR].
      'cat','classe','s1','s3' : parametros NBR 6123 (defaults do modulo vento).
      'G_roof','Q_roof' : cargas de cobertura (kN/m2) [A CONFIRMAR telha].
      'q_parede'    : peso da parede de fechamento por m2 de fachada (kN/m2, opc.).
      'fck','fyk'   : (default C30 / CA-50). 'sigma_solo_adm' (kN/m2) [A CONFIRMAR sondagem].
    }"""
    vao = spec["vao"]; comp = spec["comprimento"]; H = spec["pe_direito"]
    n_port = spec.get("n_porticos", max(2, round(comp / 6.0) + 1))
    s = comp / (n_port - 1)                        # espacamento (tributaria interna)
    theta = spec.get("theta_graus", 5.71)
    fck = spec.get("fck", 30e3); fyk = spec.get("fyk", 500e3)
    G_roof = spec.get("G_roof", 0.30); Q_roof = spec.get("Q_roof", 0.25)

    # ---------------------------------------------------------------- VENTO
    v = vento.compute(v0=spec.get("v0"), cat=spec.get("cat"), classe=spec.get("classe"),
                      s1=spec.get("s1"), s3=spec.get("s3"), z=H, theta=theta,
                      larg_b=vao, alt_h=H, comp_a=comp)
    q = v["q_kN_m2"]
    dcp = v["cpe"]["parede_barlavento"] - v["cpe"]["parede_sotavento"]   # +0,70-(-0,60)=1,30
    w_h = dcp * q * s                              # carga horizontal distribuida (kN/m) na coluna
    M_w_k = w_h * H ** 2 / 2.0                     # momento de base caracteristico (balanco)
    V_w_k = w_h * H                                # cortante de base caracteristica

    # ---------------------------------------------------- VIGA DE COBERTURA
    # Tenta CONCRETO ARMADO; se o vao nao vence (> ~12 m), roteia p/ PROTENDIDA
    # (pre-tracao) em vez de so reprovar. tipo_viga registra a solucao adotada.
    w_beam = (G_roof + Q_roof) * s                 # kN/m (biapoiada, vao=vao)
    viga = None
    for (bb, hh) in _SECOES_VIGA:
        viga = vc.verifica_viga({"vao": vao, "b": bb, "h": hh, "fck": fck, "fyk": fyk,
                                 "q": w_beam})
        if viga["OK"]:
            break
    tipo_viga = "concreto armado"
    viga_prot = None
    if not viga["OK"]:
        viga_prot = vp.dimensiona_viga_protendida(
            {"vao": vao, "fck": max(fck, 40e3), "q": w_beam})
        if viga_prot and viga_prot["OK"]:
            tipo_viga = "protendida"
            # adapta ao pipeline downstream (b/h + guards; ferragem = cordoalhas)
            viga = {"b": viga_prot["b"], "h": viga_prot["h"], "OK": True,
                    "arr_inf": None, "arr_sup": None, "As_inf_cm2": 0.0,
                    "s_estribo_max": 0.20, "phi_estribo_mm": 5.0, "protendida": True,
                    "n_cordoalhas": viga_prot["n_cordoalhas"],
                    "phi_cord": viga_prot["phi_cord"]}

    # ------------------------------------------------------------- PILARES
    # reacao vertical em cada pilar = meia reacao da viga + peso da viga + parede
    R_beam_g = G_roof * s * vao / 2.0              # permanente (cobertura), por pilar
    R_beam_q = Q_roof * s * vao / 2.0              # sobrecarga
    peso_viga = GAMMA_CONC * viga["b"] * viga["h"] * vao / 2.0 if viga else 0.0
    q_par = spec.get("q_parede", 0.0) * H * s      # peso de parede tributaria (se houver)
    Nk_g = R_beam_g + peso_viga + q_par            # permanente (sem sobrecarga)
    Nk_gq = Nk_g + R_beam_q                        # permanente + sobrecarga
    pilar = _dimensiona_pilar_secao(Nk_g, Nk_gq, M_w_k, H, fck, fyk)

    # peso proprio do pilar (soma na reacao de fundacao)
    peso_pilar = GAMMA_CONC * pilar["hx"] * pilar["hy"] * H

    # ------------------------------------------- LIGACAO PRE-MOLDADA (NBR 9062)
    # calice/colarinho: liga o pilar engastado a fundacao. hx = // ao momento do
    # vento. Esforcos de projeto da base: N (perm+sobrec), M e V do vento (ELU).
    interface_cal = spec.get("interface_calice", "rugosa")
    calice = pm.dimensiona_calice({"Nd": Nk_gq, "Md": GF * M_w_k, "Vd": GF * V_w_k,
                                   "h": pilar["hx"], "b": pilar["hy"],
                                   "fck": min(fck, 25e3), "fyk": fyk,
                                   "interface": interface_cal})
    # situacao transitoria: icamento do pilar pre-moldado (peso proprio, 2 pegas)
    icamento = pm.verifica_icamento_pilar({"L": H, "b": pilar["hy"], "h": pilar["hx"],
                                           "As": pilar["As_cm2"], "fck": fck, "fyk": fyk,
                                           "t_dias": spec.get("t_saque_dias", 3),
                                           "cimento": spec.get("cimento", "CPV")})

    # ------------------------------------------------------------ FUNDACAO
    # reacao de base de projeto: N (permanente+sobrecarga+p.proprio) e M/V do vento.
    N_base = Nk_gq + peso_pilar
    caso_sap = {"nome": "Pilar galpao concreto", "N": N_base, "V": V_w_k, "M": M_w_k,
                "sigma_solo_adm": spec.get("sigma_solo_adm", 200.0),
                "mu": spec.get("mu_solo", 0.5), "coesao": 0.0, "h_reaterro": 0.5,
                "d_ped": pilar["hx"], "b_ped": pilar["hy"], "h_ped": 0.6,
                "fck": min(fck, 25e3), "fyk": fyk, "cobrimento": 0.04}
    sap = fs.dimensiona_sapata(caso_sap)
    sap_ok = sap["aprovado"] is not None

    # ------------------------------------------ INCENDIO (NBR 15200, tabular)
    # TRRF vem da NBR 14432/legislacao (A CONFIRMAR). Galpao terreo de pequena
    # area/carga de incendio pode ser ISENTO -> sem TRRF, o gate passa com nota.
    TRRF = spec.get("TRRF")
    cob_mm = spec.get("cobrimento_mm", 30.0)
    if TRRF:
        c1_viga = fogo.c1_efetivo(cob_mm, 5.0, 16.0)
        fg_viga = fogo.verifica_viga_fogo(viga["b"] * 1000.0, c1_viga, TRRF,
                                          protendida=(tipo_viga == "protendida"))
        c1_pil = fogo.c1_efetivo(cob_mm, 5.0, 20.0)
        fg_pilar = fogo.verifica_pilar_fogo(pilar["hy"] * 1000.0, c1_pil, TRRF,
                                            faces_expostas=spec.get("faces_fogo_pilar", 4))
        pilar_fogo_ok = bool(fg_pilar.get("OK")) if fg_pilar.get("OK") is not None else False
        fogo_ok = bool(fg_viga["OK"]) and pilar_fogo_ok
        fogo_nota = ("pilar requer Anexo E (multi-face)" if fg_pilar.get("requer_anexo_E")
                     else "")
    else:
        fg_viga = fg_pilar = None
        fogo_ok = True
        fogo_nota = "sem TRRF: galpao terreo pode ser ISENTO (NBR 14432) - A CONFIRMAR"

    # --------------------------------------------------------------- GATES
    gates = {
        "vento": {"q_kN_m2": q, "w_h": round(w_h, 2), "M_base_k": round(M_w_k, 1),
                  "V_base_k": round(V_w_k, 1), "OK": True},
        "viga_cobertura": {"secao": f"{viga['b']*100:.0f}x{viga['h']*100:.0f}",
                           "As_cm2": viga.get("As_inf_cm2", 0.0), "tipo": tipo_viga,
                           "OK": viga["OK"]},
        "pilar": {"secao": f"{pilar['hy']*100:.0f}x{pilar['hx']*100:.0f}",
                  "Nd": pilar["Nd"], "Md_gov": pilar["Md_gov"], "As_cm2": pilar["As_cm2"],
                  "taxa_pct": pilar["taxa_pct"], "OK": pilar["OK"]},
        "fundacao": {"OK": sap_ok,
                     "geom": (f"{sap['aprovado'][0]:.1f}x{sap['aprovado'][1]:.1f}x"
                              f"{sap['aprovado'][2]:.2f}" if sap_ok else "REPROVA")},
        "calice": {"interface": calice["interface"], "Lemb": calice["Lemb"],
                   "Hsfd": calice.get("Hsfd"), "As_h_cm2": calice["As_horizontal_cm2"],
                   "sigma_c": calice["sigma_c_kN_m2"], "lim_comp": calice["lim_comp"],
                   "OK": calice["OK"]},
        "icamento": {"Md": icamento["Md_kN_m"], "Mr_05fyk": icamento["Mr_0.5fyk_kN_m"],
                     "fckj_MPa": icamento["fckj_MPa"], "a_pega": icamento["a_pega"],
                     "OK": icamento["OK"]},
        "fogo": {"TRRF": TRRF, "nota": fogo_nota, "viga": fg_viga, "pilar": fg_pilar,
                 "OK": fogo_ok},
    }
    reprovados = [k for k, g in gates.items() if not g["OK"]]
    return {"spec": {"vao": vao, "comprimento": comp, "H": H, "n_porticos": n_port,
                     "s": round(s, 2), "fck_MPa": fck / 1000.0},
            "vento": v, "viga": viga, "viga_prot": viga_prot, "tipo_viga": tipo_viga,
            "pilar": pilar, "sapata": sap, "calice": calice, "icamento": icamento,
            "fogo": gates["fogo"],
            "gates": gates, "reprovados": reprovados,
            "ATENDE": len(reprovados) == 0}


def membros_bim(r):
    """Constroi a lista de membros BIM (para ifc_emit.emitir_ifc) a partir do
    resultado de rodar(). Convencao do emissor: COORDENADAS em mm, dims de secao em
    m. Eixos: X = vao (largura), Y = comprimento, Z = altura. Pilares (RECT, do
    fundo z=0 ao topo z=H), viga de cobertura (RECT, no topo) por portico, e sapata
    (caixa) sob cada pilar. Material 'Concreto Cxx' -> IfcMaterial no IFC."""
    sp = r["spec"]
    vao = sp["vao"]; comp = sp["comprimento"]; H = sp["H"]; n = sp["n_porticos"]
    fckM = sp["fck_MPa"]
    mat_conc = f"Concreto C{fckM:.0f}"
    hx = r["pilar"]["hx"]; hy = r["pilar"]["hy"]                 # secao do pilar (m)
    vb = r["viga"]["b"]; vh = r["viga"]["h"]                     # secao da viga (m)
    s = comp / (n - 1)
    xL, xR = -vao / 2.0 * 1000.0, vao / 2.0 * 1000.0            # mm
    zt = H * 1000.0
    sec_pil = {"forma": "RECT", "bf": hy, "d": hx}
    sec_vig = {"forma": "RECT", "bf": vb, "d": vh}
    membros = []
    sap = r["sapata"]["aprovado"]
    B = L = hf = None
    if sap:
        B, L, hf = sap[0], sap[1], sap[2]
    for j in range(n):
        y = j * s * 1000.0                                      # mm
        for k, x in enumerate((xL, xR)):
            lado = "E" if k == 0 else "D"
            membros.append({"tipo": "Column", "perfil": f"P{hy*100:.0f}x{hx*100:.0f}",
                            "marca": f"P{j+1}{lado}", "secao": sec_pil,
                            "p1": [x, y, 0.0], "p2": [x, y, zt], "material": mat_conc})
            if sap:
                membros.append({"tipo": "Footing", "perfil": f"S{B:.1f}x{L:.1f}",
                                "marca": f"SAP{j+1}{lado}", "dims": [B, L, hf],
                                "centro": [x, y, -hf / 2.0 * 1000.0],
                                "material": mat_conc})
        membros.append({"tipo": "Beam", "perfil": f"V{vb*100:.0f}x{vh*100:.0f}",
                        "marca": f"VC{j+1}", "secao": sec_vig,
                        "p1": [xL, y, zt], "p2": [xR, y, zt], "material": mat_conc})
    return membros


def emitir_bim(r, path):
    """Emite o IFC4 do galpao de concreto (FreeCAD-free) via ifc_emit.emitir_ifc.
    Retorna o path. Requer ifcopenshell (ifc_emit.disponivel())."""
    import ifc_emit
    return ifc_emit.emitir_ifc(membros_bim(r), path, nome="GalpaoConcreto")


def relatorio_pt(r):
    g = r["gates"]; sp = r["spec"]
    L = ["GALPAO DE CONCRETO PRE-MOLDADO (NBR 6118/6123/6122)",
         f"  Vao {sp['vao']:.1f} m x comprimento {sp['comprimento']:.1f} m ; "
         f"pe-direito {sp['H']:.1f} m ; {sp['n_porticos']} porticos (s={sp['s']:.2f} m) ; C{sp['fck_MPa']:.0f}",
         f"  VENTO: q = {g['vento']['q_kN_m2']:.3f} kN/m2 ; w_h = {g['vento']['w_h']:.2f} kN/m ; "
         f"M_base = {g['vento']['M_base_k']:.1f} kN.m ; V_base = {g['vento']['V_base_k']:.1f} kN",
         f"  VIGA DE COBERTURA ({g['viga_cobertura']['tipo']}): secao "
         f"{g['viga_cobertura']['secao']} cm"
         + (f" ; {r['viga_prot']['n_cordoalhas']} cordoalhas Ø{r['viga_prot']['phi_cord']}"
            if r.get("viga_prot") else f" ; As {g['viga_cobertura']['As_cm2']:.2f} cm2")
         + f" -> {'ATENDE' if g['viga_cobertura']['OK'] else 'REPROVA'}",
         f"  PILAR (balanco): secao {g['pilar']['secao']} cm ; Nd {g['pilar']['Nd']:.0f} kN ; "
         f"Md,tot {g['pilar']['Md_gov']:.1f} kN.m ; As {g['pilar']['As_cm2']:.2f} cm2 "
         f"(taxa {g['pilar']['taxa_pct']:.2f}%) -> {'ATENDE' if g['pilar']['OK'] else 'REPROVA'}",
         f"  FUNDACAO (sapata): {g['fundacao']['geom']} -> {'ATENDE' if g['fundacao']['OK'] else 'REPROVA'}",
         f"  CALICE (NBR 9062, interface {g['calice']['interface']}): Lemb {g['calice']['Lemb']:.2f} m ; "
         f"As_h {g['calice']['As_h_cm2']:.2f} cm2 ; compressao {g['calice']['sigma_c']:.0f}<={g['calice']['lim_comp']:.0f} "
         f"-> {'ATENDE' if g['calice']['OK'] else 'REPROVA'}",
         f"  ICAMENTO (NBR 9062 5.3.2): Md {g['icamento']['Md']:.1f} <= Mr(0,5fyk) {g['icamento']['Mr_05fyk']:.1f} kN.m "
         f"(fckj {g['icamento']['fckj_MPa']:.0f} MPa) -> {'ATENDE' if g['icamento']['OK'] else 'REPROVA'}",
         f"  INCENDIO (NBR 15200): " + (f"TRRF {g['fogo']['TRRF']} min -> "
             f"{'ATENDE' if g['fogo']['OK'] else 'REPROVA/verificar'}"
             + (f" [{g['fogo']['nota']}]" if g['fogo']['nota'] else "")
             if g['fogo']['TRRF'] else g['fogo']['nota']),
         f"  RESULTADO: {'ATENDE' if r['ATENDE'] else 'REPROVADO em ' + ', '.join(r['reprovados'])}",
         "  [A CONFIRMAR: v0 do vento (mapa NBR 6123), sigma do solo (sondagem SPT),",
         "   cargas da telha/cobertura (catalogo). Nao inventados.]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # galpao tipico de concreto armado: 10 m vao, 40 m comprimento, pe-direito 6 m,
    # C30, solo 250 kPa. (Vao RC biapoiado pratico <= ~12 m; alem disso a viga de
    # cobertura pede PROTENSAO ou trelica - fora do escopo P3, e o gate acusa.)
    r = rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
               "v0": 40.0, "cat": "IV", "classe": "B", "s1": 1.0, "s3": 1.0,
               "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
               "sigma_solo_adm": 250.0})
    assert r["gates"]["vento"]["M_base_k"] > 0
    assert r["viga"]["OK"], "viga de cobertura deveria atender"
    assert r["pilar"]["OK"], ("pilar", r["pilar"]["As_cm2"], r["pilar"]["taxa_pct"])
    assert r["gates"]["pilar"]["secao"], r["gates"]["pilar"]
    # ligacao pre-moldada (NBR 9062): calice e icamento entram nos gates
    assert r["gates"]["calice"]["OK"], ("calice", r["calice"])
    assert r["gates"]["icamento"]["OK"], ("icamento", r["icamento"])
    assert r["calice"]["Lemb"] >= pm.LEMB_MIN
    assert r["ATENDE"], r["reprovados"]
    # vao grande (15 m): o RC nao vence -> roteia p/ viga PROTENDIDA e ATENDE
    r15 = rodar({"vao": 15.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                 "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30, "Q_roof": 0.25,
                 "fck": 30e3, "sigma_solo_adm": 250.0})
    assert r15["tipo_viga"] == "protendida" and r15["ATENDE"], "15 m deveria ir p/ protensao"
    print("galpao_concreto self-test PASSED:", relatorio_pt(r).splitlines()[-3].strip())


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(rodar({"vao": 15.0, "comprimento": 40.0, "pe_direito": 6.0,
              "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
              "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0})))
