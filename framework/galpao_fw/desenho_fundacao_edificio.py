# ============================================================================
# desenho_fundacao_edificio.py - O QUE ESTE SCRIPT DESENHA (G80)
# PE-CO-04 planta de locacao/formas de fundacao do predio: sapatas (ou blocos)
# na malha de pilares, com dimensoes, cota de apoio e carga de projeto por
# elemento; quadro com o tipo de fundacao escolhido e a tensao admissivel
# DECLARADA (derivada do SPT ou assumida no spec - nunca arbitrada aqui).
#
# Le o que fundacao_edificio.py ja calcula (dimensiona TODOS os pilares):
# geometria por pilar, N_dimensionamento por pilar, sigma + proveniencia,
# cota de apoio. A folha e' COUNT-DRIVEN (armadilha medida: incendio desenhou
# cols*rows != N uma vez): um elemento desenhado por pilar, dimensoes
# desenhadas == dimensionadas. Cada sapata carrega data-pilar/data-B/data-L
# para a contagem ser por PARSE, nunca substring (a escada).
# ============================================================================
"""Planta de locacao/formas da fundacao do edificio (PE-CO-04) em SVG
puro-Python, a partir de fundacao_edificio.dimensiona. STATELESS."""

from __future__ import annotations

import desenho_svg_base as sb


def _sufixo_edicao(edicao=None):
    """Sufixo de edicao da NBR 6118 no titulo (G123/G125, auditoria do G123).

    G128: a edicao declarada no projeto chega aqui (casa e predio leem a
    chave; ausente = comportamento de hoje, 2014 declarado). O sufixo vem
    da fonte unica (sem literal)."""
    from edicao_nbr6118_g123 import sufixo_folha_edicao
    return sufixo_folha_edicao(edicao)

COR_SAPATA = "#e8e4dc"
COR_SAPATA_DIVISA = "#fde9c8"
COR_VIGA_EQ = "#b91c1c"
COR_MALHA = "#c9d4e0"
COR_PILAR = "#333"


def _resolve_vaos(fundacao, estrutura):
    """Vaos (m) para posicionar a malha. Nunca inventados: sem vaos, recusa."""
    pav = None
    if isinstance(estrutura, dict):
        if isinstance(estrutura.get("pavimento"), dict):
            pav = estrutura["pavimento"]
        elif "vaos_x" in estrutura and "vaos_y" in estrutura:
            pav = estrutura
        elif isinstance(fundacao, dict) and isinstance(
                fundacao.get("_vaos"), dict):
            pav = fundacao["_vaos"]
    if not isinstance(pav, dict) or not pav.get("vaos_x") \
            or not pav.get("vaos_y"):
        raise ValueError(
            "planta_fundacao_svg: vaos_x/vaos_y nao declarados "
            "(passe a estrutura com 'pavimento' ou o pav direto)")
    return list(pav["vaos_x"]), list(pav["vaos_y"])


def _geometria_desenho(registro):
    """(B, L, h, subtipo, rotulo) do elemento a desenhar por pilar.

    Isolada/bloco/divisa: rect B x L. Estaca: bloco de coroamento (quando
    dimensionado) + n círculos; sem bloco dimensionado, marca o pilar com
    o motivo em vez de desenhar peca que ninguem calculou.
    """
    g = registro.get("geometria") or {}
    subtipo = g.get("subtipo", "isolada")
    if "n_estacas" in g:
        return None, None, None, subtipo, "estaca"
    B = g.get("B_m")
    L = g.get("L_m")
    h = g.get("h_m")
    if B is None or L is None:
        return None, None, None, subtipo, "sem-geometria"
    return float(B), float(L), float(h or 0.0), subtipo, "sapata"


def planta_fundacao_svg(fundacao, estrutura, titulo=None, edicao=None):
    """Monta a planta de locacao/formas da fundacao.

    fundacao  : dict de fundacao_edificio.dimensiona (tipo, sigma_solo_adm,
                proveniencia_sigma, cota_apoio_m, por_pilar).
    estrutura : R do edificio (com 'pavimento') ou o pav direto
                ({vaos_x, vaos_y}).
    edicao    : (opc, G128) '2014' ou '2023+Em1' declarada no projeto;
                ausente = comportamento de hoje (2014) declarado no titulo.
    """
    if not isinstance(fundacao, dict) or not fundacao.get("por_pilar"):
        raise ValueError(
            "planta_fundacao_svg: fundacao nao dimensionada "
            "(sem 'por_pilar'; sem sondagem/tensao nao ha folha)")
    por_pilar = fundacao["por_pilar"]
    tipo = fundacao.get("tipo", "... nao declarado")
    sigma = fundacao.get("sigma_solo_adm")
    prov = fundacao.get("proveniencia_sigma") or "... nao declarado"
    cota = fundacao.get("cota_apoio_m")
    vaos_x, vaos_y = _resolve_vaos(fundacao, estrutura)

    W, H = 1420, 960
    MX, MY = 150, 190
    LARG_QUADRO = 430
    larg_util = W - MX - LARG_QUADRO - 160
    alt_util = H - MY - 140
    lx, ly = sum(vaos_x), sum(vaos_y)
    esc = min(larg_util / max(lx, 1e-9), alt_util / max(ly, 1e-9))

    xs = [MX]
    for v in vaos_x:
        xs.append(xs[-1] + float(v) * esc)
    ys = [MY]
    for v in vaos_y:
        ys.append(ys[-1] + float(v) * esc)
    y_top, y_bot = ys[0], ys[-1]
    ys_inv = [y_bot - (y - y_top) for y in ys]
    por_nome = dict(por_pilar)

    def _xy(i, j):
        return xs[int(i)], ys_inv[int(j)]

    tit = titulo or ("PE-CO-04 - LOCACAO E FORMAS DA FUNDACAO "
                     "(%s ; %d pilares)" % (tipo, len(por_pilar)))
    tit += _sufixo_edicao(edicao)
    P = sb.abre_svg(W, H, tit)
    sigma_txt = ("%.1f kN/m2 (%s)" % (float(sigma), prov)) \
        if sigma is not None else "... nao declarado (ver quadro)"
    cota_txt = ("%.2f m" % float(cota)) if cota is not None \
        else "... nao declarado"
    P.append(sb.texto(W / 2, 58,
                      "tipo %s ; sigma_adm %s ; cota de apoio %s"
                      % (tipo, sigma_txt, cota_txt),
                      12, color="#333"))

    # --- malha de eixos ----------------------------------------------------
    # bolhas fora da area das sapatas (sapata tem ate ~2,5 m; o numero no eixo
    # do pilar seria escrito em cima dela). Faixa y=70..90 livre: abaixo do
    # subtitulo (y=58) e acima do topo da planta.
    y_topo, y_base = ys_inv[-1], ys_inv[0]
    for i in range(len(vaos_x) + 1):
        P.append(sb.linha(xs[i], 84, xs[i], y_base + 10, 1.0, COR_MALHA))
        P.append(sb.texto(xs[i], 76, "%d" % (i + 1), 11, color="#666"))
    for j in range(len(vaos_y) + 1):
        P.append(sb.linha(88, ys_inv[j], xs[-1] + 10, ys_inv[j],
                          1.0, COR_MALHA))
        P.append(sb.texto(70, ys_inv[j] + 4, "%s" % chr(65 + j), 11,
                          color="#666"))
    # contorno do lote da malha
    P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
             'fill="none" stroke="#bbb" stroke-dasharray="4 3"/>'
             % (xs[0], y_topo, xs[-1] - xs[0], y_base - y_topo))

    # --- sapatas: UMA por pilar (count-driven) ------------------------------
    for nome in sorted(por_nome):
        reg = por_nome[nome]
        g = reg.get("geometria") or {}
        cx, cy = _xy(reg["i"], reg["j"])
        B, L, h, subtipo, _kind = _geometria_desenho(reg)
        n_dim = float(reg.get("N_dimensionamento_kN", 0.0))
        if B is None:
            # estaca ou sem geometria: marca o pilar, nunca some
            P.append('<circle cx="%.1f" cy="%.1f" r="7" fill="white" '
                     'stroke="#b91c1c" stroke-width="1.6" data-pilar="%s" '
                     'data-subtipo="%s"/>'
                     % (cx, cy, sb.esc(nome), sb.esc(str(subtipo))))
            P.append(sb.texto(cx, cy - 14, nome, 10, weight="bold",
                              color="#b91c1c"))
            motivo = "bloco nao dimensionado" if "n_estacas" in g \
                else "sem geometria"
            P.append(sb.texto(cx, cy + 22, motivo, 9, color="#b91c1c"))
            continue
        w_px, h_px = float(B) * esc, float(L) * esc
        fill = COR_SAPATA_DIVISA if subtipo in ("divisa", "divisa_estaca") \
            else COR_SAPATA
        P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                 'fill="%s" stroke="#333" stroke-width="1.5" '
                 'data-pilar="%s" data-B="%.3f" data-L="%.3f" '
                 'data-h="%.3f" data-Ndim="%.1f" data-subtipo="%s"/>'
                 % (cx - w_px / 2.0, cy - h_px / 2.0, w_px, h_px, fill,
                    sb.esc(nome), float(B), float(L), float(h), n_dim,
                    sb.esc(str(subtipo))))
        # pilar (cheio) sobre a sapata
        P.append('<rect x="%.1f" y="%.1f" width="14" height="14" '
                 'fill="%s"/>' % (cx - 7, cy - 7, COR_PILAR))
        # nome ao LADO (nunca acima: o numero do eixo mora acima e a sapata
        # alta empurraria o rotulo para dentro dele). Ultima coluna ancora a
        # direita para nao invadir o quadro (licao da planta de formas).
        nx = len(vaos_x)
        ultima = (int(reg["i"]) == nx)
        if ultima:
            P.append(sb.texto(cx - w_px / 2.0 - 8, cy - 8, nome, 10,
                              anchor="end", weight="bold"))
        else:
            P.append(sb.texto(cx + w_px / 2.0 + 8, cy - 8, nome, 10,
                              anchor="start", weight="bold"))
        P.append(sb.texto(cx, cy + max(h_px / 2.0 + 16, 24),
                          "%.2f x %.2f" % (float(B), float(L)), 10))
        P.append(sb.texto(cx, cy + max(h_px / 2.0 + 30, 38),
                          "Ndim %.0f kN" % n_dim, 9, color="#444"))
        # viga de equilibrio/alavanca da divisa: linha ate o vizinho
        viz = g.get("vizinho")
        if viz and viz in por_nome:
            viz_reg = por_nome[viz]
            vx, vy = _xy(viz_reg["i"], viz_reg["j"])
            P.append(sb.linha(cx, cy, vx, vy, 2.2, COR_VIGA_EQ, dash="7 4"))
            mx, my = (cx + vx) / 2.0, (cy + vy) / 2.0
            m_viga = (g.get("M_viga_kNm") or (g.get("viga") or {}).get(
                "M_max_kNm"))
            if m_viga is not None:
                # deslocado da linha (nunca em cima dela) e longe do Ndim do
                # pilar interno, com quem dividia a mesma caixa no estimador
                if str(g.get("direcao")) == "y":
                    P.append(sb.texto(mx + 16, my, "M %.0f" % float(m_viga),
                                      9, anchor="start", color=COR_VIGA_EQ,
                                      weight="bold"))
                else:
                    P.append(sb.texto(mx, my - 24, "M %.0f kNm"
                                      % float(m_viga), 9, color=COR_VIGA_EQ,
                                      weight="bold"))

    # --- cotas dos vaos ------------------------------------------------------
    y_cota = y_base + 34
    for i, v in enumerate(vaos_x):
        xm = (xs[i] + xs[i + 1]) / 2.0
        P.append(sb.linha(xs[i], y_cota, xs[i + 1], y_cota, 1.0, "#666"))
        P.append(sb.texto(xm, y_cota - 6, "%.2f" % float(v), 11,
                          color="#666"))
    x_cota = 108.0
    for j, v in enumerate(vaos_y):
        ym = (ys_inv[j] + ys_inv[j + 1]) / 2.0
        P.append(sb.linha(x_cota, ys_inv[j], x_cota, ys_inv[j + 1], 1.0,
                          "#666"))
        P.append(sb.texto(x_cota - 4, ym + 4, "%.2f" % float(v), 11,
                          anchor="end", color="#666"))

    # --- quadro --------------------------------------------------------------
    qx = W - LARG_QUADRO - 20
    qy = MY - 20
    qh = H - qy - 40
    P.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfcfd" '
             'stroke="#c9d4e0" stroke-width="1"/>' % (qx, qy, LARG_QUADRO, qh))
    P.append(sb.texto(qx + LARG_QUADRO / 2, qy + 24,
                      "QUADRO DE FUNDACAO", 12, weight="bold"))
    P.append(sb.linha(qx + 12, qy + 34, qx + LARG_QUADRO - 12, qy + 34,
                      1.0, "#c9d4e0"))
    yy = qy + 52
    P.append(sb.texto(qx + 14, yy, "tipo: %s" % tipo, 11, anchor="start"))
    yy += 18
    P.append(sb.texto(qx + 14, yy, "sigma_adm:", 11, anchor="start",
                      weight="bold"))
    yy += 16
    # proveniencia pode ser longa: quebra em duas linhas curtas
    prov_curta = str(prov)
    if len(prov_curta) > 52:
        prov_curta = prov_curta[:52] + "..."
    sig_lin = ("%.1f kN/m2" % float(sigma)) if sigma is not None \
        else "... nao declarado"
    P.append(sb.texto(qx + 14, yy, sig_lin, 11, anchor="start"))
    yy += 16
    P.append(sb.texto(qx + 14, yy, prov_curta, 10, anchor="start",
                      color="#555"))
    yy += 18
    P.append(sb.texto(qx + 14, yy, "cota de apoio: %s" % cota_txt, 11,
                      anchor="start"))
    yy += 24
    P.append(sb.texto(qx + 14, yy, "PILAR", 10, anchor="start",
                      weight="bold"))
    P.append(sb.texto(qx + 74, yy, "SAPATA (m)", 10, anchor="start",
                      weight="bold"))
    P.append(sb.texto(qx + LARG_QUADRO - 14, yy, "Ndim kN", 10,
                      anchor="end", weight="bold"))
    yy += 8
    for nome in sorted(por_nome):
        reg = por_nome[nome]
        g = reg.get("geometria") or {}
        yy += 19
        if yy > H - 96:
            P.append(sb.texto(qx + LARG_QUADRO / 2, yy,
                              "... (%d pilares no total)" % len(por_nome),
                              10, color="#777"))
            break
        if "n_estacas" in g:
            dim = ("%dest D%.0f L%.0f" % (int(g.get("n_estacas") or 0),
                                          float(g.get("D_m") or 0) * 100,
                                          float(g.get("L_m") or 0)))
        elif g.get("B_m") is not None:
            dim = ("%.2f x %.2f x %.2f%s" % (
                float(g["B_m"]), float(g["L_m"]),
                float(g.get("h_m") or 0),
                " DIV" if str(g.get("subtipo")) in (
                    "divisa", "divisa_estaca") else ""))
        else:
            dim = "sem geometria"
        P.append(sb.texto(qx + 14, yy, nome, 10, anchor="start"))
        P.append(sb.texto(qx + 74, yy, dim, 10, anchor="start",
                          color="#333"))
        P.append(sb.texto(qx + LARG_QUADRO - 14, yy,
                          "%.0f" % float(reg.get("N_dimensionamento_kN",
                                                 0.0)),
                          10, anchor="end"))
    P.append(sb.texto(MX, H - 46,
                      "um elemento por pilar ; dimensoes desenhadas == "
                      "dimensionadas ; divisa com viga de equilibrio (M da "
                      "viga cotado)",
                      11, anchor="start", color="#444"))
    P.append(sb.texto(MX, H - 28,
                      "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
                      11, anchor="start", weight="bold", color="#444"))
    P.append("</svg>")
    return "\n".join(P)


def confere_desenho_fundacao(fundacao, svg, tol=1e-6):
    """Drawing-vs-data por PARSE: conta elementos e confere B/L/Ndim.

    Lado A (independente): o dict de fundacao_edificio.dimensiona.
    Lado B: os <rect data-pilar> do SVG. Tautologia seria derivar o esperado
    do proprio SVG; aqui o esperado vem do calculo.
    """
    import xml.etree.ElementTree as _ET

    esperado = fundacao.get("por_pilar") or {}
    try:
        raiz = _ET.fromstring(svg)
    except _ET.ParseError as exc:
        return {"ok": False, "motivo": "svg-malformado: %s" % exc,
                "n_esperado": len(esperado), "n_desenhado": 0,
                "faltando": sorted(esperado), "divergencias": []}
    ns = "{http://www.w3.org/2000/svg}"
    rects = list(raiz.iter(ns + "rect")) + list(raiz.iter("rect"))
    por_pilar_svg = {}
    for el in rects:
        nome = el.get("data-pilar")
        if nome:
            por_pilar_svg[nome] = el
    faltando = sorted(set(esperado) - set(por_pilar_svg))
    sobrando = sorted(set(por_pilar_svg) - set(esperado))
    divergencias = []
    for nome in sorted(set(esperado) & set(por_pilar_svg)):
        reg = esperado[nome]
        g = reg.get("geometria") or {}
        el = por_pilar_svg[nome]
        if "n_estacas" in g:
            continue
        for chave, attr in (("B_m", "data-B"), ("L_m", "data-L")):
            if g.get(chave) is None:
                continue
            try:
                des = float(el.get(attr))
            except (TypeError, ValueError):
                divergencias.append("%s: %s ausente no desenho" % (nome, attr))
                continue
            if abs(des - float(g[chave])) > 1e-3:
                divergencias.append(
                    "%s: %s desenhado %.3f != dimensionado %.3f"
                    % (nome, chave, des, float(g[chave])))
        try:
            ndes = float(el.get("data-Ndim"))
        except (TypeError, ValueError):
            divergencias.append("%s: data-Ndim ausente" % nome)
        else:
            if abs(ndes - float(reg.get("N_dimensionamento_kN", 0.0))) > 0.15:
                divergencias.append(
                    "%s: Ndim desenhado %.1f != dimensionado %.1f"
                    % (nome, ndes,
                       float(reg.get("N_dimensionamento_kN", 0.0))))
    # h mora no mesmo rect; confere em separado para a mensagem ser cirurgica
    for nome in sorted(set(esperado) & set(por_pilar_svg)):
        g = (esperado[nome].get("geometria") or {})
        if "n_estacas" in g or g.get("h_m") is None:
            continue
        try:
            hdes = float(por_pilar_svg[nome].get("data-h"))
        except (TypeError, ValueError):
            divergencias.append("%s: data-h ausente" % nome)
        else:
            if abs(hdes - float(g["h_m"])) > 1e-3:
                divergencias.append(
                    "%s: h desenhado %.3f != dimensionado %.3f"
                    % (nome, hdes, float(g["h_m"])))
    _ = tol
    ok = not faltando and not sobrando and not divergencias
    motivo = ""
    if not ok:
        partes = []
        if faltando:
            partes.append("faltando %s" % ",".join(faltando))
        if sobrando:
            partes.append("sobrando %s" % ",".join(sobrando))
        partes.extend(divergencias[:4])
        motivo = "; ".join(partes)
    return {"ok": ok, "motivo": motivo,
            "n_esperado": len(esperado), "n_desenhado": len(por_pilar_svg),
            "faltando": faltando, "sobrando": sobrando,
            "divergencias": divergencias}


def gerar_planta_fundacao(fundacao, estrutura, path, titulo=None,
                          edicao=None):
    """Escreve a planta de fundacao (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_fundacao_svg(fundacao, estrutura, titulo,
                                    edicao=edicao))
    return path
