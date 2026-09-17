# ============================================================================
# desenho_escada_edificio.py - O QUE ESTE SCRIPT DESENHA (G81)
# PE-IN-03 escada de emergencia do predio (planta + corte): degraus por lance,
# patamar, espelho/piso com a verificacao de Blondel visivel, largura exigida
# (NBR 9077 Tab.10 + NBR 9050 6.8.3) x adotada (declaracao unica
# estrutura.escada.largura) e tipo exigido x declarado (Tab.11).
#
# Le o que ja e' calculado, nao recalcula nada:
#   - escada_concreto.dimensiona (via edificio_multipavimento R["escada"]):
#     geometria (n, espelho, piso, Blondel, projecao), patamar declarado,
#     largura declarada, armadura principal, vinculacao, vao;
#   - incendio_edificio.dimensiona (I["gates"]): escada_largura (exigida,
#     governa), escada_geometria (faixa 9050 6.8.2), escada_tipo.
#
# TRIAGEM DO PATAMAR (G81): o comprimento do patamar era "A CONFIRMAR" quando
# a NBR 9050/9077 nao constava da base (escada.py igualava a largura do lance
# por pratica). As duas ENTRARAM no acervo depois (F078 NBR 9050:2020, F076
# NBR 9077:2025): 6.8.8 fixa o MINIMO longitudinal em 1,20 m e 6.8.7 exige um
# patamar a cada 3,20 m de desnivel. O spec do predio DECLARA patamar = 1,2 m
# (minimo atendido) e desnivel/lance = 1,45 m (lance unico, sem patamar
# intermediario). A folha desenha o valor DECLARADO e cita o minimo — o que
# passa do minimo continua decisao de projeto, nunca numero fechado aqui.
#
# A folha e' COUNT-DRIVEN (armadilha medida: incendio desenhou cols*rows != N
# uma vez): um rect data-degrau por degrau; degraus desenhados == n_degraus
# dimensionados; espelho/piso/patamar/largura desenhados == dimensionados.
# A contagem e' por PARSE, nunca substring (a escada).
#
# Contrato G86(a): escada REPROVADA entra na folha carimbada REPROVADA, nunca
# some. Sem escada dimensionada nao ha folha: recusa com endereco (o hook
# nomeia a pulada).
# ============================================================================
"""Folha PE-IN-03 (escada de emergencia: planta + corte) em SVG puro-Python,
a partir de escada_concreto + gates de incendio_edificio. STATELESS."""

from __future__ import annotations

import desenho_svg_base as sb

COR_DEGRAU = "#e8e4dc"
COR_PATAMAR = "#cfe3cf"
COR_LAJE = "#b91c1c"
COR_COTA = "#666"
COR_OK = "#166534"
COR_REPROVA = "#b91c1c"


def _num(valor, default=None):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def planta_escada_svg(escada, incendio=None, titulo=None, veredito=None):
    """Monta a folha da escada (planta + corte + quadro).

    escada   : resultado de escada_concreto.dimensiona (com "geometria",
               "patamar_m", "largura_m", "armadura_positiva", "vinculacao").
    incendio : saida de incendio_edificio.dimensiona (usa ["gates"]) ou None.
               Sem ele, os campos 9077/9050 saem "... nao declarado".
    veredito : (G155) fonte do veredito (o `incendio` com ATENDE/reprovados;
               sem ele, a propria `escada` com OK). None = historico; ATENDE
               = byte-identico; REPROVA declara pela fonte unica
               veredito_folha_g152 (o carimbo REPROVADA do quadro continua).
    """
    if not isinstance(escada, dict) or not isinstance(
            escada.get("geometria"), dict):
        raise ValueError(
            "planta_escada_svg: escada nao dimensionada "
            "(sem 'geometria'; sem estrutura.escada nao ha folha)")
    geo = escada["geometria"]
    n = int(geo["n_degraus"])
    espelho = float(geo["espelho"])
    piso = float(geo["piso"])
    blondel = float(geo.get("blondel", piso + 2.0 * espelho))
    proj = float(geo.get("projecao_m", (n - 1) * piso))
    patamar = _num(escada.get("patamar_m"), 0.0) or 0.0
    largura = _num(escada.get("largura_m"))
    desnivel = n * espelho
    vao = _num(escada.get("vao_calculo_m"), proj + patamar)
    vinc = escada.get("vinculacao", "... nao declarado")
    ok_estrut = bool(escada.get("OK"))

    gates = (incendio or {}).get("gates") if isinstance(incendio, dict) else {}
    gates = gates if isinstance(gates, dict) else {}
    g_larg = gates.get("escada_largura") or {}
    g_geo = gates.get("escada_geometria")
    g_tipo = gates.get("escada_tipo") or {}
    exig = _num(g_larg.get("largura_exigida_m"))
    governa = g_larg.get("governa")
    tipo_ex = g_tipo.get("tipo_exigido")
    tipo_dec = g_tipo.get("tipo_declarado")

    arm = (escada.get("armadura_positiva") or {}).get("malha") or {}
    arm_txt = ("phi %.1f c/ %.0f cm" % (arm["phi_mm"], arm["s"] * 100)
               if arm.get("phi_mm") and arm.get("s") else "... nao declarado")

    carimbo = "ATENDE" if ok_estrut else "REPROVADA - VER QUADRO"
    tit = titulo or ("PE-IN-03 - ESCADA DE EMERGENCIA (PLANTA E CORTE) "
                     "(%d degraus ; %s)" % (n, carimbo))
    W, H = 1420, 980
    P = sb.abre_svg(W, H, tit)
    P[-1] = P[-1].replace('font-size="20"', 'font-size="19"')
    sub = ("lance unico" if desnivel <= 3.20 + 1e-9 else "MULTI-LANCE (ver nota)")
    P.append(sb.texto(W / 2, 58,
                       "desnivel %.2f m ; %s ; patamar declarado %.2f m "
                       "(minimo NBR 9050 6.8.8 = 1,20 m)" % (desnivel, sub, patamar),
                       12, color="#333"))

    # --- PLANTA (vista de cima): largura na horizontal, caminhamento na vertical
    px0, py0, pW, pH = 80, 110, 380, 560
    esc_p = min(pW / max(largura or 1.0, 1e-9),
                pH / max(proj + patamar, 1e-9))
    larg_px = (largura or 0.0) * esc_p
    P.append(sb.texto(px0 + pW / 2, py0 - 14, "PLANTA (lance + patamar)",
                      13, weight="bold"))
    y = py0 + pH
    # patamar no topo (chegada): e' o n-esimo degrau (o ultimo espelho chega
    # nele) e o rect do patamar e' contavel em separado. A projecao do lance
    # tem n-1 pisos (escada_concreto.geometria): desenhar n pisos somaria um
    # piso a mais que o dimensionado.
    pat_px = patamar * esc_p
    P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
             'fill="%s" stroke="#333" stroke-width="1.5" data-degrau="%d" '
             'data-patamar-rect="%.3f"/>'
             % (px0 + (pW - larg_px) / 2.0, y - pat_px, larg_px, pat_px,
                COR_PATAMAR, n, patamar))
    P.append(sb.texto(px0 + pW / 2, y - pat_px / 2 + 4, "PATAMAR %.2f m" % patamar,
                      11, weight="bold"))
    y -= pat_px
    for i in range(1, n):
        h_px = piso * esc_p
        P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                 'fill="%s" stroke="#333" stroke-width="1.2" '
                 'data-degrau="%d" data-piso="%.4f" data-espelho="%.4f"/>'
                 % (px0 + (pW - larg_px) / 2.0, y - h_px, larg_px, h_px,
                    COR_DEGRAU, i, piso, espelho))
        if h_px >= 16:
            P.append(sb.texto(px0 + pW / 2, y - h_px / 2 + 4, "%d" % i, 10))
        y -= h_px
    P.append(sb.texto(px0 + pW / 2, py0 + pH + 58,
                      "%d pisos + patamar de chegada = %d espelhos" % (n - 1, n),
                      10, color=COR_COTA))
    # cotas da planta
    x_sol = px0 + (pW - larg_px) / 2.0
    P.append(sb.linha(x_sol, py0 + pH + 18, x_sol + larg_px, py0 + pH + 18,
                      1.0, COR_COTA))
    if largura is not None:
        P.append(sb.texto(x_sol + larg_px / 2, py0 + pH + 34,
                          "larg %.2f m (adotada)" % largura, 11, color=COR_COTA))
    P.append(sb.linha(px0 - 22, py0 + pH - (proj + patamar) * esc_p,
                      px0 - 22, py0 + pH, 1.0, COR_COTA))
    P.append(sb.texto(px0 - 28, py0 + pH - (proj + patamar) * esc_p / 2,
                      "%.2f" % (proj + patamar), 11, anchor="end",
                      color=COR_COTA))

    # --- CORTE (perfil): um path em escada + laje; a CONTAGEM mora na planta
    cx0, cy0, cW, cH = 540, 110, 430, 560
    esc_c = min(cW / max(proj + patamar + 0.6, 1e-9),
                (cH - 120) / max(desnivel, 1e-9))
    P.append(sb.texto(cx0 + cW / 2, cy0 - 14, "CORTE (perfil do lance)",
                      13, weight="bold"))
    base_y = cy0 + cH - 90
    x = cx0 + 20
    # n espelhos de subida, (n-1) pisos de corrida + o patamar de chegada:
    # a projecao total e' (n-1)*piso + patamar == proj + patamar.
    d = ["M%.1f %.1f" % (x, base_y)]
    for i in range(n):
        d.append("v%.1f" % (-espelho * esc_c))
        d.append("h%.1f" % ((piso if i < n - 1 else patamar) * esc_c))
    P.append('<path d="%s" fill="none" stroke="#111" stroke-width="2.0" '
             'data-perfil="lance"/>' % " ".join(d))
    # laje sob o perfil (deslocada da espessura, so indicacao)
    P.append(sb.linha(x, base_y + 14, x + (proj + patamar) * esc_c,
                      base_y - desnivel * esc_c + 14, 2.4, COR_LAJE))
    P.append(sb.texto(x + (proj + patamar) * esc_c / 2, base_y + 32,
                      "laje h = %.0f cm (%s)" % (escada.get("h_laje", 0) * 100,
                                                 vinc),
                      11, color=COR_LAJE))
    # cotas do corte: desnivel + chamada do 1o espelho/piso
    P.append(sb.linha(x - 22, base_y - desnivel * esc_c, x - 22, base_y,
                      1.0, COR_COTA))
    P.append(sb.texto(x - 28, base_y - desnivel * esc_c / 2, "%.2f" % desnivel,
                      11, anchor="end", color=COR_COTA))
    P.append(sb.texto(x + piso * esc_c / 2, base_y + 48,
                      "piso %.1f cm" % (piso * 100), 10, color=COR_COTA))
    P.append(sb.texto(x + (proj + patamar) * esc_c + 8,
                      base_y - desnivel * esc_c, "patamar", 10,
                      anchor="start", color=COR_COTA))

    # --- QUADRO ------------------------------------------------------------
    qx, qW = 1020, 380
    qy, qh = 90, H - 90 - 60
    P.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfcfd" '
             'stroke="#c9d4e0" stroke-width="1"/>' % (qx, qy, qW, qh))
    P.append(sb.texto(qx + qW / 2, qy + 24, "QUADRO DA ESCADA", 12,
                      weight="bold"))
    P.append(sb.linha(qx + 12, qy + 34, qx + qW - 12, qy + 34, 1.0, "#c9d4e0"))
    yy = qy + 54

    def _lin(chave, valor, cor="#111", peso="normal", tam=11):
        nonlocal yy
        P.append(sb.texto(qx + 14, yy, chave, tam, anchor="start",
                          color="#555"))
        P.append(sb.texto(qx + qW - 14, yy, valor, tam, anchor="end",
                          weight=peso, color=cor))
        yy += 20

    _lin("degraus (1 lance)", "%d" % n)
    _lin("espelho", "%.1f cm" % (espelho * 100))
    _lin("piso", "%.1f cm" % (piso * 100))
    _lin("Blondel 2e+p", "%.1f cm [62;64]" % (blondel * 100),
         COR_OK if 62 - 1e-9 <= blondel * 100 <= 64 + 1e-9 else COR_REPROVA,
         "bold")
    if isinstance(g_geo, dict):
        ok9050 = bool(g_geo.get("OK"))
        _lin("geometria 9050 6.8.2", "OK" if ok9050 else "REPROVA",
             COR_OK if ok9050 else COR_REPROVA, "bold")
    else:
        _lin("geometria 9050 6.8.2", "... nao declarado")
    _lin("patamar (declarado)", "%.2f m" % patamar)
    _lin("patamar minimo 6.8.8", "1,20 m", COR_OK
         if patamar + 1e-9 >= 1.20 else COR_REPROVA, "bold")
    if exig is not None:
        ok_l = largura is not None and largura + 1e-9 >= exig
        _lin("largura exigida", "%.2f m (%s)" % (exig, governa or "?"))
        _lin("largura adotada", ("%.2f m" % largura) if largura is not None
             else "... nao declarado", COR_OK if ok_l else COR_REPROVA,
             "bold")
    else:
        _lin("largura exigida", "... nao declarado")
        _lin("largura adotada", ("%.2f m" % largura) if largura is not None
             else "... nao declarado")
    _lin("tipo exigido Tab.11", str(tipo_ex if tipo_ex else "... nao declarado"))
    _lin("tipo declarado", str(tipo_dec if tipo_dec else "... nao declarado"),
         COR_OK if (tipo_ex and tipo_dec and tipo_dec == tipo_ex)
         else ("#555" if not tipo_dec else COR_REPROVA), "bold"
         if tipo_ex and tipo_dec else "normal")
    _lin("armadura principal", arm_txt)
    _lin("vao de calculo", "%.2f m" % vao)
    yy += 6
    P.append(sb.texto(qx + 14, yy, "NOTA PATAMAR (G81):", 10, anchor="start",
                      weight="bold"))
    yy += 16
    for ln in ("comprimento desenhado = declarado (%.2f m) ;" % patamar,
               "minimo 9050 6.8.8 = 1,20 m. Acima do",
               "minimo e' decisao de projeto (A CONFIRMAR",
               "pelo RT), nunca numero fechado aqui."):
        P.append(sb.texto(qx + 14, yy, ln, 10, anchor="start",
                          color="#555"))
        yy += 15
    yy += 4
    for ln in (("lance unico: desnivel %.2f m <= 3,20 m" % desnivel)
               if desnivel <= 3.20 + 1e-9 else
               "desnivel > 3,20 m: EXIGE patamar intermediario (6.8.7)",
               "Blondel e faixa 9050 lidos dos gates, nao",
               "recalculados nesta folha."):
        P.append(sb.texto(qx + 14, yy, ln, 10, anchor="start",
                          color="#555"))
        yy += 15
    if not ok_estrut:
        P.append(sb.texto(qx + qW / 2, yy + 10, "ESCADA REPROVADA",
                          13, weight="bold", color=COR_REPROVA))
        motivo = escada.get("avisos") or []
        if motivo:
            P.append(sb.texto(qx + 14, yy + 28, str(motivo[0])[:52], 10,
                              anchor="start", color=COR_REPROVA))

    P.append(sb.texto(80, H - 30,
                      "degraus desenhados == dimensionados ; medidas desenhadas == "
                      "calculadas ; 9077/9050 verificados nos gates",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(W - 20, H - 30, "CONCEITUAL - PENDENTE REVISAO E ART",
                      11, anchor="end", weight="bold", color="#444"))
    # G155: veredito lido do resultado pela fonte unica (nunca decidido aqui).
    _fonte155 = veredito if veredito is not None else (
        incendio if incendio is not None else escada)
    if _fonte155 is not None:
        from veredito_folha_g152 import veredito_para_folha_svg as _v152
        _lin155, _st155 = _v152(_fonte155)
        if _lin155 is not None:
            P.append(sb.texto(W / 2, 76, _lin155, 12, weight="bold",
                              color="#b91c1c"))
            if _st155 is not None:
                P.append(sb.texto(W / 2, H - 12, "STATUS: %s" % _st155, 11,
                                  weight="bold", color="#b91c1c"))
    P.append("</svg>")
    svg = "\n".join(P)
    # carimbo legivel por parse (nao so por pixel)
    svg = svg.replace(
        "<svg ", '<svg data-n="%d" data-espelho="%.4f" data-piso="%.4f" '
        'data-blondel="%.4f" data-patamar="%.3f" '
        'data-largura-declarada="%s" data-largura-exigida="%s" data-ok="%s" '
        % (n, espelho, piso, blondel, patamar,
           ("%.3f" % largura) if largura is not None else "nao-declarada",
           ("%.3f" % exig) if exig is not None else "nao-declarada",
           "1" if ok_estrut else "0"), 1)
    return svg


def confere_desenho_escada(escada, svg, incendio=None, tol=1e-6):
    """Drawing-vs-data por PARSE: degraus contados e medidas conferidas.

    Lado A (independente): escada_concreto.dimensiona + gates do incendio.
    Lado B: rects data-degrau / data-patamar-rect + attrs data-* do SVG.
    Tautologia seria derivar o esperado do proprio SVG.
    """
    import xml.etree.ElementTree as _ET

    geo = (escada or {}).get("geometria") or {}
    n_esp = int(geo.get("n_degraus") or 0)
    try:
        raiz = _ET.fromstring(svg)
    except _ET.ParseError as exc:
        return {"ok": False, "motivo": "svg-malformado: %s" % exc,
                "n_esperado": n_esp, "n_desenhado": 0,
                "divergencias": []}
    ns = "{http://www.w3.org/2000/svg}"
    rects = list(raiz.iter(ns + "rect")) + list(raiz.iter("rect"))
    degraus = [el for el in rects if el.get("data-degrau")]
    nums = sorted(el.get("data-degrau") for el in degraus)
    divergencias = []
    if len(degraus) != n_esp:
        divergencias.append("degraus desenhados %d != dimensionados %d"
                            % (len(degraus), n_esp))
    if nums != [str(i) for i in range(1, n_esp + 1)]:
        divergencias.append("numeracao dos degraus quebrada: %s" % nums[:6])
    for chave, attr in (("espelho", "data-espelho"), ("piso", "data-piso"),
                        ("blondel", "data-blondel")):
        ref = float(geo.get(chave, 0.0)) if chave != "blondel" else float(
            geo.get("blondel", 0.0))
        try:
            des = float(raiz.get(attr))
        except (TypeError, ValueError):
            divergencias.append("%s ausente no desenho" % attr)
            continue
        if abs(des - ref) > 1e-3:
            divergencias.append("%s desenhado %.4f != dimensionado %.4f"
                                % (chave, des, ref))
    pat_ref = float(escada.get("patamar_m") or 0.0)
    try:
        pat_des = float(raiz.get("data-patamar"))
    except (TypeError, ValueError):
        divergencias.append("data-patamar ausente no desenho")
    else:
        if abs(pat_des - pat_ref) > 1e-3:
            divergencias.append("patamar desenhado %.3f != declarado %.3f"
                                % (pat_des, pat_ref))
    larg_ref = escada.get("largura_m")
    if larg_ref is not None:
        try:
            larg_des = float(raiz.get("data-largura-declarada"))
        except (TypeError, ValueError):
            divergencias.append("data-largura-declarada ausente")
        else:
            if abs(larg_des - float(larg_ref)) > 1e-3:
                divergencias.append("largura desenhada %.3f != declarada %.3f"
                                    % (larg_des, float(larg_ref)))
    gates = (incendio or {}).get("gates") if isinstance(incendio, dict) \
        else {}
    g_larg = (gates or {}).get("escada_largura") or {}
    if g_larg.get("largura_exigida_m") is not None:
        try:
            ex_des = float(raiz.get("data-largura-exigida"))
        except (TypeError, ValueError):
            divergencias.append("data-largura-exigida ausente")
        else:
            if abs(ex_des - float(g_larg["largura_exigida_m"])) > 1e-3:
                divergencias.append(
                    "largura exigida desenhada %.3f != gate %.3f"
                    % (ex_des, float(g_larg["largura_exigida_m"])))
    _ = tol
    ok = not divergencias
    return {"ok": ok, "motivo": "" if ok else "; ".join(divergencias[:6]),
            "n_esperado": n_esp, "n_desenhado": len(degraus),
            "divergencias": divergencias}


def gerar_planta_escada(escada, path, incendio=None, titulo=None, veredito=None):
    """Escreve a folha da escada (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_escada_svg(escada, incendio, titulo,
                                  veredito=veredito))
    return path
