# ============================================================================
# escada_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ESCADA DE CONCRETO ARMADO do edificio multipavimento (ABNT NBR 6118:2014). O
# framework so tinha `escada.py`, que e escada METALICA industrial (longarinas de
# perfil, degrau de chapa xadrez, NBR 8800) - outro problema estrutural.
#
# A escada de concreto e tratada como LAJE ARMADA EM UMA DIRECAO, inclinada, com o
# vao medido na PROJECAO HORIZONTAL:
#   1) GEOMETRIA: numero de degraus a partir do desnivel e do espelho maximo; piso
#      pela relacao de Blondel (2e + p ~ 63 cm). Gate proprio de faixa ergonomica.
#   2) CARGA (o ponto onde mais se erra): o peso proprio da laje inclinada, quando
#      lancado sobre a PROJECAO HORIZONTAL, cresce por 1/cos(alpha) - a laje e mais
#      comprida que a projecao. Some-se o peso dos DEGRAUS (prismas triangulares,
#      cujo volume por metro de projecao e e/2 vezes a largura, nao e x p) e o
#      revestimento. A carga variavel vem da Tabela 10 da NBR 6120 (escada
#      residencial privativa 2,5 ; de uso comum 3,0 ; com acesso publico 3,0).
#   3) ESFORCOS: faixa de 1 m, M = w*L^2/8 (biapoiada) ou os coeficientes de
#      `laje_concreto.COEF_1D` para engastada-apoiada / biengastada.
#   4) ARMADURA: reusa `laje_concreto.dimensiona_seccao` (flexao 17.2.2 + minimos da
#      Tab.19.1 + detalhamento 20.1) e `armadura_secundaria` para a distribuicao.
#   5) CORTANTE de laje sem armadura transversal (19.4.1) e ELS de flecha (17.3.2,
#      Branson + fluencia), com os limites da Tabela 13.3.
#
# ARMADURA NEGATIVA NO PATAMAR / MUDANCA DE INCLINACAO: onde o lance encontra o
# patamar ha uma quebra do eixo. Se a concavidade for tal que a resultante das
# tracoes tenda a "arrancar" o cobrimento, a armadura NAO pode ser simplesmente
# dobrada seguindo o eixo - tem de ser interrompida e ancorada. O modulo sinaliza
# esse ponto; o detalhe fica declarado no relatorio.
#
# PROVENIENCIA: a relacao de Blondel e as dimensoes de patamar vem da pratica de
# engenharia e da NBR 9050/9077, que NAO constam do acervo de normas do projeto
# (mesma limitacao ja declarada em `escada.py`) -> A CONFIRMAR. Tudo o que e de
# concreto (13.2.4.1, 17.2.2, 19.3.3/19.4.1, 20.1, 13.3, 17.3.2) vem da NBR 6118 e
# esta implementado nos modulos ja aferidos que este aqui consome. As cargas de uso
# vem da Tabela 10 da NBR 6120, transcrita em `cargas_nbr6120`.
#
# Unidades: m, kN ; fck/fyk em kN/m2. Saidas em portugues.
# ============================================================================
"""Escada de concreto armado (NBR 6118:2014) como laje armada em uma direcao:
geometria de Blondel, carga da laje inclinada + degraus, flexao, cortante de laje e
ELS de flecha, reusando as primitivas ja aferidas de laje_concreto."""

from __future__ import annotations

import math

import cargas_nbr6120 as cg
import laje_concreto as lj
import viga_baldrame as vb

GAMMA_CONC = cg.PESO_ESPECIFICO["concreto_armado"]      # 25 kN/m3

# --- geometria (NBR 9050/9077 fora do acervo -> A CONFIRMAR) ---------------
BLONDEL_ALVO = 0.63          # m : 2e + p, centro da faixa usual [0,62 ; 0,65]
ESPELHO_MAX = 0.18           # m
PISO_MIN, PISO_MAX = 0.25, 0.32
DESNIVEL_MAX_SEM_PATAMAR = 3.20     # m (mesmo criterio de escada.py)

# vinculacoes suportadas -> (coef. M+, coef. M-) de laje_concreto.COEF_1D
VINCULACOES = ("apoiada", "engastada_apoiada", "biengastada")


def geometria(desnivel, espelho_max=ESPELHO_MAX, blondel=BLONDEL_ALVO):
    """Numero de degraus, espelho e piso a partir do desnivel.

    O espelho e obtido dividindo o desnivel pelo MENOR numero de degraus que mantem
    e <= espelho_max (degraus iguais, como exige a pratica); o piso sai de Blondel,
    p = blondel - 2e. Gate: piso fora de [0,25 ; 0,32] m reprova em vez de seguir com
    uma escada impraticavel."""
    if desnivel <= 0:
        raise ValueError("desnivel deve ser > 0")
    n = max(2, math.ceil(desnivel / espelho_max - 1e-9))
    e = desnivel / n
    p = blondel - 2.0 * e
    ok = PISO_MIN - 1e-9 <= p <= PISO_MAX + 1e-9
    # a projecao horizontal do LANCE tem n-1 pisos (o ultimo degrau chega ao patamar)
    projecao = (n - 1) * p
    alpha = math.atan2(e, p) if p > 0 else math.pi / 2
    return {"n_degraus": n, "espelho": round(e, 4), "piso": round(p, 4),
            "blondel": round(2 * e + p, 4), "projecao_m": round(projecao, 4),
            "alpha_rad": alpha, "alpha_graus": round(math.degrees(alpha), 2),
            "ok": bool(ok),
            "motivo": "" if ok else
                      ("piso de %.1f cm fora da faixa ergonomica [%.0f ; %.0f] cm "
                       "para espelho de %.1f cm (Blondel 2e+p = %.1f cm)"
                       % (p * 100, PISO_MIN * 100, PISO_MAX * 100, e * 100,
                          (2 * e + p) * 100))}


def carga_permanente(h_laje, espelho, piso, revestimento_kN_m2=1.0):
    """Carga permanente da escada, por m2 de PROJECAO HORIZONTAL (kN/m2).

    Tres parcelas, e a primeira e a que se erra:
      - LAJE INCLINADA: a laje tem comprimento L/cos(alpha) para uma projecao L, logo
        o peso por m2 de projecao e gamma*h/cos(alpha), nao gamma*h. Esquecer o
        1/cos(alpha) subestima o peso proprio em ~13% numa escada de 30 graus.
      - DEGRAUS: cada degrau e um prisma TRIANGULAR de catetos e (espelho) e p
        (piso). O volume por metro de projecao horizontal e (e*p/2)/p = e/2, logo o
        peso por m2 de projecao e gamma*e/2 - nao gamma*e nem gamma*e*p.
      - REVESTIMENTO: por m2 de superficie pisada (projecao).
    Devolve (g_total, detalhe)."""
    if piso <= 0 or espelho <= 0 or h_laje <= 0:
        raise ValueError("espelho, piso e espessura da laje devem ser > 0")
    cos_a = piso / math.hypot(espelho, piso)
    g_laje = GAMMA_CONC * h_laje / cos_a
    g_degraus = GAMMA_CONC * espelho / 2.0
    g_rev = revestimento_kN_m2
    total = g_laje + g_degraus + g_rev
    return total, {"laje_inclinada": round(g_laje, 4), "degraus": round(g_degraus, 4),
                   "revestimento": round(g_rev, 4), "cos_alpha": round(cos_a, 5),
                   "total": round(total, 4)}


def verifica(cfg):
    """Verifica uma escada de concreto armado de UM lance.

    cfg: {
      'desnivel'   : altura a vencer pelo lance (m);
      'largura'    : largura util (m, so informativa para o quadro de ferros);
      'h_laje'     : espessura da laje da escada (m);
      'uso'        : chave da Tabela 10 da NBR 6120 (default
                     'escada_residencial_comum'); ou 'q' explicito (kN/m2);
      'vinculacao' : 'apoiada' (default) | 'engastada_apoiada' | 'biengastada';
      'revestimento_kN_m2' : default 1,0;
      'vao'        : (opc) vao horizontal de calculo (m). Sem ele, usa a projecao do
                     lance somada ao 'patamar' (m, opcional);
      'patamar'    : (opc) comprimento do patamar que entra no vao (m);
      'fck','fyk'  : resistencias (kN/m2); 'cobrimento' (m, default 0,025);
      'phi_mm'     : bitola presumida para a altura util (default 10 mm).
    }"""
    geo = geometria(cfg["desnivel"], cfg.get("espelho_max", ESPELHO_MAX))
    h = cfg["h_laje"]
    fck, fyk = cfg["fck"], cfg["fyk"]
    cob = cfg.get("cobrimento", 0.025)
    phi = cfg.get("phi_mm", 10.0) / 1000.0
    d = h - cob - phi / 2.0
    vinc = cfg.get("vinculacao", "apoiada")
    if vinc not in VINCULACOES:
        raise ValueError("vinculacao deve ser uma de %s (recebido %r)"
                         % (list(VINCULACOES), vinc))

    avisos = []
    # --- vao de calculo ---------------------------------------------------
    patamar = cfg.get("patamar", 0.0)
    L = cfg.get("vao", geo["projecao_m"] + patamar)
    if L <= 0:
        raise ValueError("vao de calculo deve ser > 0")

    # --- cargas -----------------------------------------------------------
    g, det_g = carga_permanente(h, geo["espelho"], geo["piso"],
                                cfg.get("revestimento_kN_m2", 1.0))
    if "q" in cfg:
        q = float(cfg["q"])
        uso = "informado explicitamente"
    else:
        uso = cfg.get("uso", "escada_residencial_comum")
        q = cg.carga_uso(uso)["q"]
    w = g + q                                     # caracteristica (kN/m2 = kN/m/m)
    gf = cfg.get("gamma_f", 1.4)

    # --- esforcos numa faixa de 1 m --------------------------------------
    cM_pos, cM_neg = lj.COEF_1D[vinc]
    M_d_pos = gf * cM_pos * w * L ** 2
    M_d_neg = gf * cM_neg * w * L ** 2
    V_d = gf * w * L / 2.0

    # --- espessura minima (Tab.13.2) --------------------------------------
    h_min = lj.h_minima("piso")
    ok_h = h >= h_min - 1e-9
    if not ok_h:
        avisos.append("espessura de %.1f cm abaixo do minimo de %.1f cm para laje de "
                      "piso (NBR 6118 Tab.13.2)" % (h * 100, h_min * 100))

    # --- armaduras ---------------------------------------------------------
    # escada = laje armada em UMA direcao -> minimo de "positiva_1d" (Tab.19.1)
    pos = lj.dimensiona_seccao(M_d_pos, 1.0, d, h, fck, fyk, "positiva_1d")
    neg = None
    if cM_neg > 0:
        neg = lj.dimensiona_seccao(M_d_neg, 1.0, d, h, fck, fyk, "negativa")
    As_sec = lj.armadura_secundaria(pos["As_adotada"], fck, h)
    sec = lj.dimensiona_seccao(0.0, 1.0, d, h, fck, fyk, "secundaria")

    # --- cortante de laje (19.4.1) ----------------------------------------
    cort = lj.cortante_laje(V_d, 1.0, d, fck, pos["As_adotada"])

    # --- ELS: flecha (17.3.2, Branson + fluencia) numa faixa de 1 m -------
    continua = vinc != "apoiada"
    fl = vb._flecha_alvenaria(1.0, h, d, L, w, fck, pos["As_adotada"], continua)
    lim_mm = lj.limite_flecha("visual", L) * 1000.0
    els_ok = fl["d_total_mm"] <= lim_mm + 1e-9

    # --- patamar obrigatorio ----------------------------------------------
    precisa_patamar = cfg["desnivel"] > DESNIVEL_MAX_SEM_PATAMAR + 1e-9
    if precisa_patamar:
        avisos.append(
            "desnivel de %.2f m acima de %.2f m: o lance exige PATAMAR intermediario "
            "(criterio de escada.py; NBR 9050/9077 fora do acervo -> A CONFIRMAR). "
            "Divida o desnivel em lances e verifique cada um."
            % (cfg["desnivel"], DESNIVEL_MAX_SEM_PATAMAR))
    if patamar > 0:
        avisos.append(
            "MUDANCA DE INCLINACAO no encontro lance/patamar: a armadura tracionada "
            "nao pode ser simplesmente dobrada seguindo o eixo quando a concavidade "
            "tende a arrancar o cobrimento - deve ser interrompida e ancorada de cada "
            "lado da quebra (detalhe de projeto).")

    ok = (geo["ok"] and ok_h and not precisa_patamar
          and pos["secao_ok"] and pos["ok_dominio"] and pos["ok_As_max"]
          and (neg is None or (neg["secao_ok"] and neg["ok_dominio"]
                               and neg["ok_As_max"]))
          and cort["ok"] and els_ok
          and not pos["malha"]["saturou"])

    return {
        "OK": bool(ok), "geometria": geo, "vinculacao": vinc,
        "vao_calculo_m": round(L, 4), "patamar_m": patamar,
        "uso": uso, "g_kN_m2": round(g, 3), "q_kN_m2": round(q, 3),
        "detalhe_g": det_g,
        "h_laje": h, "h_min": h_min, "ok_h_minimo": bool(ok_h), "d": round(d, 4),
        "M_d_pos": round(M_d_pos, 3), "M_d_neg": round(M_d_neg, 3),
        "V_d": round(V_d, 3),
        "armadura_positiva": pos, "armadura_negativa": neg,
        "As_secundaria": As_sec, "malha_secundaria": sec["malha"],
        "cortante": cort,
        "els": {"d_total_mm": fl["d_total_mm"], "lim_mm": round(lim_mm, 2),
                "ok": bool(els_ok), "criterio": "visual L/250 (Tab.13.3)"},
        "avisos": avisos,
    }


def dimensiona(cfg, espessuras=(0.08, 0.09, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20)):
    """Adota a MENOR espessura da lista que atende. Se NENHUMA atender, devolve o
    ultimo resultado com OK=False e o aviso - nunca a ultima tentada dada como boa
    (o padrao de saturacao silenciosa que ja apareceu em 4 disciplinas)."""
    h0 = cfg.get("h_laje", 0.0)
    cand = [h for h in espessuras if h >= h0 - 1e-9] or [max(espessuras)]
    r = None
    for h in cand:
        r = verifica(dict(cfg, h_laje=h))
        if r["OK"]:
            return r
    r = dict(r)
    r["OK"] = False
    r["avisos"] = list(r["avisos"]) + [
        "SATUROU a lista de espessuras (%s cm): nenhuma atende. O resultado abaixo e o "
        "da maior espessura tentada e NAO deve ser adotado - revise vao, vinculacao "
        "ou carga." % ", ".join("%.0f" % (h * 100) for h in cand)]
    return r


def relatorio(r):
    """Memoria de calculo da escada de concreto."""
    g = r["geometria"]
    L = ["ESCADA DE CONCRETO ARMADO - ABNT NBR 6118:2014 (laje armada em uma direcao)",
         "  Geometria: %d degraus ; espelho %.1f cm ; piso %.1f cm ; "
         "Blondel 2e+p = %.1f cm ; inclinacao %.1f graus"
         % (g["n_degraus"], g["espelho"] * 100, g["piso"] * 100, g["blondel"] * 100,
            g["alpha_graus"]),
         "  Vao de calculo (projecao horizontal): %.2f m ; vinculacao: %s"
         % (r["vao_calculo_m"], r["vinculacao"]),
         "  Laje: h = %.1f cm (minimo Tab.13.2 = %.1f cm) ; d = %.1f cm"
         % (r["h_laje"] * 100, r["h_min"] * 100, r["d"] * 100),
         "",
         "  CARGAS (por m2 de PROJECAO HORIZONTAL):",
         "    laje inclinada (gamma*h/cos alpha, cos = %.3f) : %6.2f kN/m2"
         % (r["detalhe_g"]["cos_alpha"], r["detalhe_g"]["laje_inclinada"]),
         "    degraus (prisma triangular, gamma*e/2)          : %6.2f kN/m2"
         % r["detalhe_g"]["degraus"],
         "    revestimento                                    : %6.2f kN/m2"
         % r["detalhe_g"]["revestimento"],
         "    g total                                         : %6.2f kN/m2" % r["g_kN_m2"],
         "    q de uso (%s)" % r["uso"],
         "                                                    : %6.2f kN/m2" % r["q_kN_m2"],
         "",
         "  ESFORCOS (faixa de 1 m): M+d = %.2f kN.m/m ; M-d = %.2f kN.m/m ; "
         "Vd = %.2f kN/m" % (r["M_d_pos"], r["M_d_neg"], r["V_d"]),
         "  ARMADURA principal: phi %.1f mm c/ %.1f cm (As_ef = %.2f cm2/m)"
         % (r["armadura_positiva"]["malha"]["phi_mm"],
            r["armadura_positiva"]["malha"]["s"] * 100,
            r["armadura_positiva"]["malha"]["As_ef"] * 1e4),
         "  ARMADURA de distribuicao: %.2f cm2/m" % (r["As_secundaria"] * 1e4),
         "  CORTANTE (19.4.1): %s" % ("OK" if r["cortante"]["ok"] else "REPROVA"),
         "  ELS flecha: %.2f mm <= %.2f mm (%s) -> %s"
         % (r["els"]["d_total_mm"], r["els"]["lim_mm"], r["els"]["criterio"],
            "OK" if r["els"]["ok"] else "REPROVA")]
    if not g["ok"]:
        L.append("  GEOMETRIA REPROVA: %s" % g["motivo"])
    if r["avisos"]:
        L += ["", "  Avisos:"] + ["    ! " + a for a in r["avisos"]]
    L += ["", "  RESULTADO: %s" % ("ATENDE" if r["OK"] else "REPROVADO"),
          "  [A CONFIRMAR: geometria de degrau/patamar (NBR 9050/9077 fora do acervo)]"]
    return "\n".join(L)
