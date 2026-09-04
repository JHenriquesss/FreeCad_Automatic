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
import estaca_profunda as estp
import premoldado_nbr9062 as pm
import fogo_nbr15200 as fogo
import estabilidade_global_nbr6118 as eg

GF = 1.4
PSI0_VENTO = 0.6                    # fator de combinacao do vento (NBR 8681 Tab.1)
PSI0_SOBRECARGA = 0.7              # sobrecarga de cobertura
GAMMA_CONC = 25.0                  # peso especifico do concreto (kN/m3)

# escadas de secao (adota a MENOR que passa). Pilar: hx (// vento) >= hy.
_SECOES_PILAR = [(0.20, 0.40), (0.20, 0.50), (0.25, 0.50), (0.30, 0.50),
                 (0.30, 0.60), (0.30, 0.70), (0.40, 0.70), (0.40, 0.90)]
_SECOES_VIGA = [(0.20, 0.40), (0.20, 0.50), (0.20, 0.60), (0.25, 0.60),
                (0.25, 0.70), (0.30, 0.80), (0.30, 1.00)]


TRAVAMENTOS_LONGITUDINAIS = ("nenhum", "topo")


def _le_por_direcao(H, hy, travamento):
    """Comprimentos de flambagem do pilar do galpao, por direcao (m).

    x (plano do portico, // hx): o pilar e um BALANCO engastado na fundacao e livre
    no topo -> le_x = 2H. Isso e geometria do portico e nao depende de opcao.

    y (longitudinal, // hy): depende de EXISTIR sistema de travamento longitudinal.
      'nenhum' (default) -> o pilar tambem e balanco nesta direcao: le_y = 2H.
      'topo'             -> o topo e vinculado pelo sistema longitudinal e vale a
                            regra de 15.6 para elemento vinculado nas DUAS
                            extremidades: le = min(l0 + h ; l), com l = H (distancia
                            entre eixos) e l0 = altura livre.

    Por que isso e explicito e nao um default embutido: com 'nenhum' e H = 6 m,
    le_y = 12 m leva a lambda_y = 3,46*12/hy > 90 para toda secao usual, e acima de
    200 para hy <= 0,20 m - faixa que a NBR 6118 15.8.1 nem admite. O modelo atual do
    galpao de concreto NAO tem sistema de contraventamento longitudinal, entao o
    default honesto e 'nenhum', que REPROVA. Assumir 'topo' calado seria escolher a
    hipotese que faz passar."""
    if travamento not in TRAVAMENTOS_LONGITUDINAIS:
        raise ValueError("travamento_longitudinal deve ser um de %s (recebido %r)"
                         % (list(TRAVAMENTOS_LONGITUDINAIS), travamento))
    le_x = 2.0 * H
    if travamento == "nenhum":
        return le_x, 2.0 * H
    l0 = H                                   # altura livre entre os elementos
    return le_x, min(l0 + hy, H)


def _dimensiona_pilar_secao(Nk_g, Nk_gq, M_w_k, H, fck, fyk, travamento="nenhum",
                          V_w_k=0.0):
    """Adota a MENOR secao de pilar que atende as 2 combinacoes ELU. hx (=h) e a
    dimensao no plano do vento (resiste ao momento de base). Retorna dict.
    V_w_k = cortante de base caracteristico do vento (kN); chega ao fuste como
    Vd de CALCULO por combinacao (NBR 8681): comb1 Vd=1,4*0,6*V_w_k (gravidade
    principal), comb2 Vd=1,4*V_w_k (vento principal, governa o cortante)."""
    # Biaxial (17.2.5): o vento transversal atua numa direcao (x, plano do portico)
    # e o momento MINIMO (11.3.3.4.3) coexiste na direcao perpendicular (y). Ventos
    # perpendiculares NAO se somam (NBR 6123, um por vez) -> a envoltoria biaxial e
    # Mx_vento + My_min. forcar_biaxial ativa a interacao obliqua com o My minimo.
    for (hy, hx) in _SECOES_PILAR:
        le_x, le_y = _le_por_direcao(H, hy, travamento)
        # comb 1 (gravidade principal): Nd=1,4(G+Q), M=1,4*0,6*M_w, V=1,4*0,6*V_w_k
        c1 = pc.dimensiona_pilar({"b": hy, "h": hx, "Nk": Nk_gq, "le_x": le_x,
            "le_y": le_y, "fck": fck, "fyk": fyk, "dl": 0.04, "gamma_f": GF,
            "forcar_biaxial": True, "Vd": GF * PSI0_VENTO * abs(V_w_k),
            "M1d_x": {"tipo": "balanco", "Ma": GF * PSI0_VENTO * M_w_k}})
        # comb 2 (vento principal): Nd=1,0*G (minimo), M=1,4*M_w, V=1,4*V_w_k
        c2 = pc.dimensiona_pilar({"b": hy, "h": hx, "Nk": Nk_g, "le_x": le_x,
            "le_y": le_y, "fck": fck, "fyk": fyk, "dl": 0.04, "gamma_f": 1.0,
            "forcar_biaxial": True, "Vd": GF * abs(V_w_k),
            "M1d_x": {"tipo": "balanco", "Ma": GF * M_w_k}})
        gov = c1 if c1["As_cm2"] >= c2["As_cm2"] else c2
        gov = gov if (c1["OK"] and c2["OK"]) else dict(gov, OK=(c1["OK"] and c2["OK"]))
        if c1["OK"] and c2["OK"]:
            gov["comb1_As"] = c1["As_cm2"]; gov["comb2_As"] = c2["As_cm2"]
            gov["comb1_Vd"] = c1["Vd"]; gov["comb2_Vd"] = c2["Vd"]
            gov["Vd_gov"] = max(c1["Vd"], c2["Vd"])
            gov["u_cort"] = max(c1["u_cort"], c2["u_cort"])
            gov["cort_ok"] = bool(c1["cort_ok"] and c2["cort_ok"])
            # G44: o Asw do fuste segue a combinacao que governa o cortante
            # (vento principal, maior Vd) — nao a que governa a longitudinal.
            gcorr = c1 if c1["Vd"] >= c2["Vd"] else c2
            for k in ("Asw_s_cm2_m", "Asw_s_req_cm2_m", "Asw_s_min_cm2_m",
                      "Asw_prov_cm2_m", "phi_estribo_mm", "s_estribo",
                      "s_estribo_max", "VRd3", "Asw_atendido",
                      "n_ramos_estribo", "s_t", "s_t_max", "st_ok"):
                if k in gcorr:
                    gov[k] = gcorr[k]
            gov["travamento_longitudinal"] = travamento
            return gov
    gov["comb1_As"] = c1["As_cm2"]; gov["comb2_As"] = c2["As_cm2"]
    gov["comb1_Vd"] = c1["Vd"]; gov["comb2_Vd"] = c2["Vd"]
    gov["Vd_gov"] = max(c1["Vd"], c2["Vd"])
    gov["u_cort"] = max(c1["u_cort"], c2["u_cort"])
    gov["cort_ok"] = bool(c1["cort_ok"] and c2["cort_ok"])
    gcorr = c1 if c1["Vd"] >= c2["Vd"] else c2
    for k in ("Asw_s_cm2_m", "Asw_s_req_cm2_m", "Asw_s_min_cm2_m",
              "Asw_prov_cm2_m", "phi_estribo_mm", "s_estribo",
              "s_estribo_max", "VRd3", "Asw_atendido",
              "n_ramos_estribo", "s_t", "s_t_max", "st_ok"):
        if k in gcorr:
            gov[k] = gcorr[k]
    gov["travamento_longitudinal"] = travamento
    if not gov.get("esbeltez_valida", True):
        gov.setdefault("avisos", []).append(
            "Nenhuma secao da lista atende: com travamento_longitudinal='%s' o "
            "comprimento de flambagem longitudinal e le_y = %.2f m e a esbeltez sai "
            "fora da faixa de validade do metodo (NBR 6118 15.8.3.3.2, lambda <= 90). "
            "Se o galpao tiver sistema de contraventamento longitudinal, declare "
            "travamento_longitudinal='topo'." % (travamento,
                                                 _le_por_direcao(H, gov["hy"],
                                                                 travamento)[1]))
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
      'travamento_longitudinal' : 'nenhum' (default) | 'topo'. Define o comprimento de
                      flambagem NA DIRECAO LONGITUDINAL (ver _le_por_direcao). Com
                      'nenhum' o pilar e balanco tambem nessa direcao (le_y = 2H) e a
                      esbeltez costuma estourar o limite de 15.8.3.3.2.
    }"""
    vao = spec["vao"]; comp = spec["comprimento"]; H = spec["pe_direito"]
    if vao <= 0 or comp <= 0 or H <= 0:
        raise ValueError("[A CONFIRMAR] geometria invalida: vao=%g, comprimento=%g, "
                         "pe_direito=%g (devem ser > 0)." % (vao, comp, H))
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
    pilar = _dimensiona_pilar_secao(Nk_g, Nk_gq, M_w_k, H, fck, fyk,
                                    spec.get("travamento_longitudinal", "nenhum"),
                                    V_w_k)

    # peso proprio do pilar (soma na reacao de fundacao)
    peso_pilar = GAMMA_CONC * pilar["hx"] * pilar["hy"] * H

    # ------------------------------------- ESTABILIDADE GLOBAL (NBR 6118 15.5)
    # portico = 2 pilares em balanco; deslocamento no plano do vento (hx). n=1
    # pavimento -> criterio e o parametro alpha (gamma_z so vale >= 4 andares).
    estab = eg.verifica_estabilidade_galpao(H=H, Nk=2.0 * (Nk_gq + peso_pilar),
                                            b_col=pilar["hy"], h_col=pilar["hx"],
                                            n_col=2, fck=fck, n_andares=1)

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
    # tipo_fundacao: 'sapata' (default, solo competente raso) ou 'estaca' (fundacao
    # profunda; exige perfil SPT da sondagem - A CONFIRMAR).
    N_base = Nk_gq + peso_pilar
    # GEOTECNIA (opcional): quando o spec traz 'perfil_spt' (sondagem), o tipo de
    # fundacao e a tensao admissivel do solo passam a ser DERIVADOS da sondagem
    # (antes: sigma_solo_adm era dado manual e o tipo escolhido a mao). O explicito
    # do spec sempre vence a recomendacao.
    geo = None
    if spec.get("perfil_spt"):
        import geotecnia_spt as gspt
        geo = gspt.recomenda_fundacao(spec["perfil_spt"], N_base,
                                      cota_apoio_m=spec.get("cota_apoio", 0.5),
                                      B_max_m=spec.get("B_max_sapata", 2.5))
    tipo_fund = spec.get("tipo_fundacao")
    if tipo_fund is None:
        tipo_fund = (geo["tipo"] if geo and geo["tipo"] in ("sapata", "estaca")
                     else "sapata")
    sap = None; estaca = None
    if tipo_fund == "estaca":
        if not spec.get("perfil_spt"):
            raise ValueError("tipo_fundacao='estaca' exige 'perfil_spt' (sondagem SPT) "
                             "- A CONFIRMAR, nao inventado")
        D_e = spec.get("D_estaca", 0.30); L_e = spec.get("L_estaca", 8.0)
        estaca = estp.verifica_estaca({
            "perfil": spec["perfil_spt"], "D": D_e, "L": L_e,
            "tipo_estaca": spec.get("tipo_estaca", "pre_moldada"),
            "N_pilar": N_base, "Mx": M_w_k,
            "bloco": {"a_pilar": pilar["hx"], "fck": min(fck, 25e3), "fyk": fyk,
                      "cobrimento": 0.05}})
        fund_ok = (estaca["grupo"]["util"] <= 1.0
                   and estaca.get("grupo_momento", {}).get("OK", True))
        fund_geom = (f"{estaca['grupo']['n']} estacas D{D_e*100:.0f} L{L_e:.0f} "
                     f"(util {estaca['grupo']['util']:.2f})")
    else:
        # sigma_solo: explicito do spec > derivado do SPT (N/50) > default 200
        sigma_solo = spec.get("sigma_solo_adm")
        if sigma_solo is None and geo and geo.get("sapata"):
            sigma_solo = geo["sapata"]["sigma_adm_kNm2"]
        if sigma_solo is None:
            sigma_solo = 200.0
        caso_sap = {"nome": "Pilar galpao concreto", "N": N_base, "V": V_w_k, "M": M_w_k,
                    "sigma_solo_adm": sigma_solo,
                    "mu": spec.get("mu_solo", 0.5), "coesao": 0.0, "h_reaterro": 0.5,
                    "d_ped": pilar["hx"], "b_ped": pilar["hy"], "h_ped": 0.6,
                    "fck": min(fck, 25e3), "fyk": fyk, "cobrimento": 0.04,
                    "verificacao_estabilidade": spec.get("verificacao_estabilidade")}
        sap = fs.dimensiona_sapata(caso_sap)
        fund_ok = sap["aprovado"] is not None
        fund_geom = (f"{sap['aprovado'][0]:.1f}x{sap['aprovado'][1]:.1f}x"
                     f"{sap['aprovado'][2]:.2f}" if fund_ok else "REPROVA")
    sap_ok = fund_ok

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

    # -------------------------------------------- PISO INDUSTRIAL (opcional)
    # Placa de concreto sobre solo de Winkler (Westergaard + tracao na flexao
    # NBR 6118 8.2.5). So dimensiona quando o spec traz 'piso' com as cargas de
    # operacao (roda de empilhadeira, pe de porta-palete); sem isso fica FORA dos
    # gates - a espessura nunca e' inventada. Cobre a area do galpao por default.
    piso = None
    piso_cfg = spec.get("piso")
    if piso_cfg:
        import piso_industrial as pisom
        caso_piso = dict(piso_cfg)
        caso_piso.setdefault("L", comp)
        caso_piso.setdefault("W", vao)
        caso_piso.setdefault("fck_MPa", fck / 1000.0)
        if ("k_MN_m3" not in caso_piso and "cbr_pct" not in caso_piso
                and spec.get("cbr_pct")):
            caso_piso["cbr_pct"] = spec["cbr_pct"]
        piso = pisom.verifica_piso(caso_piso)

    # --------------------------------------------------------------- GATES
    gates = {
        "vento": {"q_kN_m2": q, "w_h": round(w_h, 2), "M_base_k": round(M_w_k, 1),
                  "V_base_k": round(V_w_k, 1), "OK": True},
        "viga_cobertura": {"secao": f"{viga['b']*100:.0f}x{viga['h']*100:.0f}",
                           "As_cm2": viga.get("As_inf_cm2", 0.0), "tipo": tipo_viga,
                           "OK": viga["OK"]},
        "pilar": {"secao": f"{pilar['hy']*100:.0f}x{pilar['hx']*100:.0f}",
                  "Nd": pilar["Nd"], "Md_gov": pilar["Md_gov"], "As_cm2": pilar["As_cm2"],
                  "taxa_pct": pilar["taxa_pct"],
                  "Vd_gov": pilar.get("Vd_gov", pilar.get("Vd", 0.0)),
                  "VRd2": pilar.get("VRd2", 0.0),
                  "u_cort": pilar.get("u_cort", 0.0),
                  "Asw_s_cm2_m": pilar.get("Asw_s_cm2_m", 0.0),
                  "phi_estribo_mm": pilar.get("phi_estribo_mm", 5.0),
                  "s_estribo": pilar.get("s_estribo",
                                         pilar.get("s_estribo_max", 0.15)),
                  "Asw_prov_cm2_m": pilar.get("Asw_prov_cm2_m", 0.0),
                  "Asw_atendido": pilar.get("Asw_atendido", True),
                  "n_ramos_estribo": pilar.get("n_ramos_estribo", 2),
                  "s_t": pilar.get("s_t", 0.0),
                  "s_t_max": pilar.get("s_t_max", 0.0),
                  "cort_ok": pilar.get("cort_ok", True), "OK": pilar["OK"]},
        "fundacao": {"OK": fund_ok, "tipo": tipo_fund, "geom": fund_geom},
        "calice": {"interface": calice["interface"], "Lemb": calice["Lemb"],
                   "Hsfd": calice.get("Hsfd"), "As_h_cm2": calice["As_horizontal_cm2"],
                   "sigma_c": calice["sigma_c_kN_m2"], "lim_comp": calice["lim_comp"],
                   "OK": calice["OK"]},
        "icamento": {"Md": icamento["Md_kN_m"], "Mr_05fyk": icamento["Mr_0.5fyk_kN_m"],
                     "fckj_MPa": icamento["fckj_MPa"], "a_pega": icamento["a_pega"],
                     "OK": icamento["OK"]},
        "fogo": {"TRRF": TRRF, "nota": fogo_nota, "viga": fg_viga, "pilar": fg_pilar,
                 "OK": fogo_ok},
        "estab_global": {"alpha": estab["alpha"], "alpha1": estab["alpha1"],
                         "nos": estab["nos"], "OK": estab["OK"]},
    }
    if piso is not None:
        gates["piso"] = {"h_cm": piso.get("h_cm"), "fck_MPa": piso.get("fck_MPa"),
                         "k_MN_m3": piso.get("k_MN_m3"),
                         "vol_m3": piso.get("volume_concreto_m3"),
                         "motivo": piso.get("motivo", ""), "OK": bool(piso["OK"])}
    res = {"spec": {"vao": vao, "comprimento": comp, "H": H, "n_porticos": n_port,
                    "s": round(s, 2), "fck_MPa": fck / 1000.0},
           "vento": v, "viga": viga, "viga_prot": viga_prot, "tipo_viga": tipo_viga,
           "pilar": pilar, "sapata": sap, "estaca": estaca, "tipo_fundacao": tipo_fund,
           "calice": calice, "icamento": icamento, "piso": piso, "geotecnia": geo,
           "fogo": gates["fogo"], "estab_global": estab, "gates": gates}
    # varredura de interpenetracao no modelo 3D (pega sapatas sobrepostas p/ s < L)
    interf = checa_interferencia(res)
    gates["interferencia"] = {"conflitos": len(interf["conflitos"]),
                              "detalhe": interf["conflitos"][:5], "OK": interf["OK"]}
    res["interferencia"] = interf
    reprovados = [k for k, g in gates.items() if not g["OK"]]
    res["reprovados"] = reprovados
    res["ATENDE"] = len(reprovados) == 0
    return res


def membros_bim(r):
    """Constroi a lista de membros BIM (para ifc_emit.emitir_ifc) a partir do
    resultado de rodar(). Convencao do emissor (ifc_emit): COORDENADAS em mm, dims
    de secao (bf/d) em m e dims de CAIXA (sapata) em mm - a caixa vai crua para o
    IfcRectangleProfileDef, entao emiti-la em metros gerava uma sapata 1000x menor
    no IFC (achado do G8, medindo a bbox real do IfcFooting). Eixos: X = vao (largura), Y = comprimento, Z = altura. Pilares (RECT, do
    fundo z=0 ao topo z=H), viga de cobertura (RECT, no topo) por portico, e sapata
    (caixa) sob cada pilar. Material 'Concreto Cxx' -> IfcMaterial no IFC.
    Contratos: fronteiras.F01 (dims mm), F03 (p1/p2 mm), F04 (secao m), F05 (ancoragem base)."""
    sp = r["spec"]
    vao = sp["vao"]; comp = sp["comprimento"]; H = sp["H"]; n = sp["n_porticos"]
    fckM = sp["fck_MPa"]
    mat_conc = f"Concreto C{fckM:.0f}"
    hx = r["pilar"]["hx"]; hy = r["pilar"]["hy"]                 # secao do pilar (m)
    vb = r["viga"]["b"]; vh = r["viga"]["h"]                     # secao da viga (m)
    s = comp / (n - 1)
    xL, xR = -vao / 2.0 * 1000.0, vao / 2.0 * 1000.0            # mm
    zt = H * 1000.0
    # bf ocupa o eixo X global e d o eixo Y (ver _aabb e o emissor IFC). hx e a
    # dimensao no PLANO DO PORTICO (// vao = X); hy e a longitudinal (Y). Invertido,
    # o pilar entrava no BIM/3D/clash girado 90 graus - o eixo forte fora do plano.
    sec_pil = {"forma": "RECT", "bf": hx, "d": hy}
    sec_vig = {"forma": "RECT", "bf": vb, "d": vh}
    # quantitativo de armadura (vira Pset_Armadura no IFC) por tipo de peca
    arm_pil = {"As_long_cm2": r["pilar"].get("As_cm2", 0.0),
               "taxa_pct": r["pilar"].get("taxa_pct", 0.0)}
    if r.get("tipo_viga") == "protendida" and r.get("viga_prot"):
        arm_vig = {"protendida": True, "n_cordoalhas": float(r["viga_prot"]["n_cordoalhas"]),
                   "phi_cordoalha_mm": float(r["viga_prot"]["phi_cord"])}
    else:
        arm_vig = {"protendida": False, "As_inf_cm2": r["viga"].get("As_inf_cm2", 0.0)}
    membros = []
    # so a sapata vira caixa no BIM; estaca/bloco tem geometria propria (fora deste
    # emissor simplificado) -> quando a fundacao e profunda, omite o footing.
    sap = r["sapata"]["aprovado"] if r.get("sapata") else None
    B = L = hf = None
    if sap:
        B, L, hf = sap[0], sap[1], sap[2]
    for j in range(n):
        y = j * s * 1000.0                                      # mm
        for k, x in enumerate((xL, xR)):
            lado = "E" if k == 0 else "D"
            membros.append({"tipo": "Column", "perfil": f"P{hy*100:.0f}x{hx*100:.0f}",
                            "marca": f"P{j+1}{lado}", "secao": sec_pil,
                            "p1": [x, y, 0.0], "p2": [x, y, zt], "material": mat_conc,
                            "armadura": arm_pil})
            if sap:
                membros.append({"tipo": "Footing", "perfil": f"S{B:.1f}x{L:.1f}",
                                "marca": f"SAP{j+1}{lado}",
                                "dims": [B * 1000.0, L * 1000.0, hf * 1000.0],
                                "centro": [x, y, -hf / 2.0 * 1000.0],
                                "material": mat_conc})
        # ancoragem 'base': p1/p2 e' a FACE INFERIOR da viga, que se apoia no topo
        # do pilar (z = zt) e sobe vh. Declarado porque o emissor IFC centra o
        # perfil no eixo por padrao - sem esta chave, o IFC enterrava meia viga
        # dentro do pilar e discordava do 3D do FreeCAD em vh/2.
        membros.append({"tipo": "Beam", "perfil": f"V{vb*100:.0f}x{vh*100:.0f}",
                        "marca": f"VC{j+1}", "secao": sec_vig, "ancoragem": "base",
                        "p1": [xL, y, zt], "p2": [xR, y, zt], "material": mat_conc,
                        "armadura": arm_vig})
    return membros


def _aabb(mb):
    """Caixa envolvente (AABB) de um membro do membros_bim, em mm:
    (x0,x1,y0,y1,z0,z1). Barra (p1/p2 + secao RECT) ou caixa (dims/centro)."""
    if "dims" in mb and "centro" in mb:               # footing (caixa, dims em mm)
        B, L, h = mb["dims"]
        cx, cy, cz = mb["centro"]
        return (cx - B / 2, cx + B / 2, cy - L / 2, cy + L / 2, cz - h / 2, cz + h / 2)
    p1, p2 = mb["p1"], mb["p2"]                         # barra (secao RECT em m)
    bf = mb["secao"]["bf"] * 1000.0; d = mb["secao"]["d"] * 1000.0
    x0, x1 = sorted((p1[0], p2[0])); y0, y1 = sorted((p1[1], p2[1]))
    z0, z1 = sorted((p1[2], p2[2]))
    # engorda pela secao (bf no plano X, d no plano Y) - conservador
    return (x0 - bf / 2, x1 + bf / 2, y0 - d / 2, y1 + d / 2, z0, z1)


def _overlap_vol(a, b, folga=1.0):
    """Volume de interpenetracao de dois AABB (mm3). folga (mm) ignora toques.
    Peças que compartilham face (viga sobre pilar) tocam mas nao interpenetram."""
    dx = min(a[1], b[1]) - max(a[0], b[0]) - folga
    dy = min(a[3], b[3]) - max(a[2], b[2]) - folga
    dz = min(a[5], b[5]) - max(a[4], b[4]) - folga
    return dx * dy * dz if (dx > 0 and dy > 0 and dz > 0) else 0.0


def checa_interferencia(r):
    """Varredura de interpenetracao (AABB) nos membros do galpao de concreto -
    analogo puro-Python do checa_interferencia do 3D FreeCAD. Pega o caso REAL de
    SAPATAS que se sobrepoem quando os porticos ficam proximos (s < L da sapata) e
    pilares que colidem. Ignora toques de face (viga sobre pilar). Retorna dict com
    a lista de conflitos e OK."""
    ms = membros_bim(r)
    boxes = [(mb.get("marca", mb["tipo"]), mb["tipo"], _aabb(mb)) for mb in ms]
    conflitos = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (mi, ti, ai), (mj, tj, aj) = boxes[i], boxes[j]
            v = _overlap_vol(ai, aj)
            if v > 1.0:                                # > 1 mm3 -> interpenetracao real
                conflitos.append({"a": mi, "b": mj, "tipos": f"{ti}x{tj}",
                                  "vol_mm3": round(v, 0)})
    return {"n_membros": len(ms), "conflitos": conflitos, "OK": not conflitos}


def emitir_bim(r, path):
    """Emite o IFC4 do galpao de concreto (FreeCAD-free) via ifc_emit.emitir_ifc.
    Retorna o path. Requer ifcopenshell (ifc_emit.disponivel())."""
    import ifc_emit
    return ifc_emit.emitir_ifc(membros_bim(r), path, nome="GalpaoConcreto")


def montar_3d(r, out_dir, doc_name="galpao_concreto", headless=None,
              host="http://localhost:9875", timeout=180):
    """Constroi o MODELO 3D SOLIDO (FreeCAD) do galpao de concreto: pilares, vigas
    de cobertura e sapatas viram Part::Box, exportados em FCStd + STEP + IFC4.

    Diferente do BIM puro (emitir_bim -> IFC do emissor Python), este gera a
    GEOMETRIA SOLIDA no FreeCAD e roda a varredura de interferencia sobre os solidos
    REAIS (OCCT common(), nao AABB). Envia build_concreto.py como FONTE + o modelo
    neutro (membros_bim) como PAYLOAD DE DADOS - reusa o despacho bridge/headless do
    rodar_projeto (fallback automatico + kill de zumbi). Como o payload e plain data,
    NAO ha modulo irmao para o freecad.exe cachear (a armadilha do 3D do aco nao se
    aplica aqui). Retorna o dict de rodar_projeto._montar_* ({result:{...}} | {erro}).

    headless: None tenta o bridge (9875) e cai p/ freecadcmd; True forca headless."""
    import os
    import rodar_projeto as RP
    import framework as FW
    bk = {"membros": membros_bim(r),
          "export_dir": str(out_dir).replace("\\", "/"),
          "doc_name": doc_name}
    src_path = FW.raiz_repo() / "framework" / "galpao_fw" / "build_concreto.py"
    src = RP._ship_build_src(src_path)
    if headless is None:
        headless = os.environ.get("FREECAD_HEADLESS", "").strip() in ("1", "true", "True")
    if headless:
        return RP._montar_headless(src, bk, out_dir, timeout)
    import xmlrpc.client
    try:
        return RP._montar_bridge(src, bk, host, timeout)
    except (OSError, xmlrpc.client.ProtocolError) as e:
        import sys
        print("[montar_3d] bridge indisponivel (%s); caindo p/ headless" % e,
              file=sys.stderr)
        return RP._montar_headless(src, bk, out_dir, timeout)


def montar_pranchas(r, out_dir, fcstd_path, spec=None, freecad_exe=None,
                    timeout=1200):
    """Gera o PROJETO EXECUTIVO (pranchas A1 TechDraw) do galpao de concreto a
    partir do modelo 3D ja salvo (fcstd_path, do montar_3d/build_concreto). Roda o
    freecad.exe em modo grafico HEADLESS (GUI disponivel p/ exportar PDF, sem
    interacao: job por QTimer, janela fecha sozinha). Exporta PDF + SVG + PNG por
    prancha em out_dir/pranchas. Le o resultado de out_dir/pranchas/_status.json.

    Mesma mecanica do rodar_projeto.rodar_executivo do aco (freecad.exe novo a cada
    projeto -> import de irmao em processo LIMPO; kill de zumbi garantido na saida).
    Retorna {ok, pranchas, arquivos, fcstd} | {erro}."""
    import os, json, time, tempfile, subprocess
    import techdraw_concreto as TDC
    import rodar_projeto as RP

    exe = freecad_exe or os.environ.get("FREECAD_EXE") or \
        r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
    if not os.path.exists(exe):
        return {"erro": f"freecad.exe nao encontrado: {exe}"}
    if not os.path.exists(fcstd_path):
        return {"erro": f"FCStd ausente ({fcstd_path}) - rode montar_3d antes"}

    cfg = TDC.config_de_spec(r, fcstd_path, str(out_dir), spec)
    prdir = os.path.join(str(out_dir), "pranchas")
    os.makedirs(prdir, exist_ok=True)
    status = os.path.join(prdir, "_status.json")
    try:
        os.remove(status)
    except OSError:
        pass

    boot = tempfile.NamedTemporaryFile(mode="w", suffix="_exec_conc.py",
                                       delete=False, encoding="utf-8")
    boot.write(TDC.script_bootstrap(cfg))
    boot.close()

    proc = subprocess.Popen([exe, boot.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    res = None
    try:
        while time.time() - t0 < timeout:
            if os.path.exists(status):
                time.sleep(0.5)
                with open(status, encoding="utf-8") as f:
                    res = json.load(f)
                break
            if proc.poll() is not None and not os.path.exists(status):
                time.sleep(2)
                if os.path.exists(status):
                    with open(status, encoding="utf-8") as f:
                        res = json.load(f)
                else:
                    res = {"erro": "freecad.exe encerrou sem gerar _status.json"}
                break
            time.sleep(2)
        if res is None:
            res = {"erro": f"timeout {timeout}s aguardando pranchas"}
    finally:
        RP._matar_processo_freecad(proc)          # reusa o kill escalonado (WMI)
        try:
            os.unlink(boot.name)
        except OSError:
            pass
    return res


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
         f"(taxa {g['pilar']['taxa_pct']:.2f}%) ; Vd {g['pilar'].get('Vd_gov', 0.0):.1f} <= "
         f"VRd2 {g['pilar'].get('VRd2', 0.0):.1f} kN (u={g['pilar'].get('u_cort', 0.0):.3f}) -> "
         f"{'ATENDE' if g['pilar']['OK'] else 'REPROVA'}",
         f"  FUNDACAO ({g['fundacao']['tipo']}): {g['fundacao']['geom']} -> {'ATENDE' if g['fundacao']['OK'] else 'REPROVA'}"
         + (f"\n  GEOTECNIA (SPT): {r['geotecnia']['justificativa']}" if r.get("geotecnia") else ""),
         f"  ESTABILIDADE GLOBAL (NBR 6118 15.5): alpha {g['estab_global']['alpha']:.3f} "
         f"{'<=' if g['estab_global']['nos']=='fixos' else '>'} {g['estab_global']['alpha1']:.2f} "
         f"-> nos {g['estab_global']['nos']}",
         f"  CALICE (NBR 9062, interface {g['calice']['interface']}): Lemb {g['calice']['Lemb']:.2f} m ; "
         f"As_h {g['calice']['As_h_cm2']:.2f} cm2 ; compressao {g['calice']['sigma_c']:.0f}<={g['calice']['lim_comp']:.0f} "
         f"-> {'ATENDE' if g['calice']['OK'] else 'REPROVA'}",
         f"  ICAMENTO (NBR 9062 5.3.2): Md {g['icamento']['Md']:.1f} <= Mr(0,5fyk) {g['icamento']['Mr_05fyk']:.1f} kN.m "
         f"(fckj {g['icamento']['fckj_MPa']:.0f} MPa) -> {'ATENDE' if g['icamento']['OK'] else 'REPROVA'}",
         f"  INCENDIO (NBR 15200): " + (f"TRRF {g['fogo']['TRRF']} min -> "
             f"{'ATENDE' if g['fogo']['OK'] else 'REPROVA/verificar'}"
             + (f" [{g['fogo']['nota']}]" if g['fogo']['nota'] else "")
             if g['fogo']['TRRF'] else g['fogo']['nota']),
         f"  INTERFERENCIA 3D: {r['gates']['interferencia']['conflitos']} conflito(s) "
         f"-> {'OK' if r['gates']['interferencia']['OK'] else 'REVISAR (pecas se interpenetram)'}",]
    if g.get("piso"):
        gp = g["piso"]
        L.append(f"  PISO INDUSTRIAL (placa sobre solo, Westergaard + NBR 6118 8.2.5): "
                 + (f"h {gp['h_cm']:.0f} cm ; C{gp['fck_MPa']:.0f} ; k {gp['k_MN_m3']:.0f} MN/m3 ; "
                    f"vol {gp['vol_m3']:.0f} m3 -> ATENDE" if gp["OK"]
                    else f"REPROVA [{gp.get('motivo','')}]"))
    L += [
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
               "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})
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
                 "fck": 30e3, "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})
    assert r15["tipo_viga"] == "protendida" and r15["ATENDE"], "15 m deveria ir p/ protensao"
    print("galpao_concreto self-test PASSED:", relatorio_pt(r).splitlines()[-3].strip())


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(rodar({"vao": 15.0, "comprimento": 40.0, "pe_direito": 6.0,
              "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
              "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"})))
