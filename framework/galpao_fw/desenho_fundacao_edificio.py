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
    da fonte unica (sem literal).
    G132: a folha declara a edicao que a SUA conta usou (sem troca: 2014
    com qualquer chave). Invalida continua levantando."""
    from edicao_nbr6118_g123 import edicao_da_peca, sufixo_folha_edicao
    return sufixo_folha_edicao(edicao_da_peca(edicao, False))

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


def planta_fundacao_svg(fundacao, estrutura, titulo=None, edicao=None,
                          ausencias=None, veredito=None):
    """Monta a planta de locacao/formas da fundacao.

    fundacao  : dict de fundacao_edificio.dimensiona (tipo, sigma_solo_adm,
                proveniencia_sigma, cota_apoio_m, por_pilar).
    estrutura : R do edificio (com 'pavimento') ou o pav direto
                ({vaos_x, vaos_y}).
    edicao    : (opc, G128) '2014' ou '2023+Em1' declarada no projeto;
                ausente = comportamento de hoje (2014) declarado no titulo.
    ausencias : (opc, G140) campos que o calculo do galpao nao produz,
                declarados em caixa vermelha na folha. None = caminho do
                predio/casa, byte-identico (nenhum pixel muda).
    veredito  : (G155) fonte do veredito (o proprio `fundacao` com
                gate.OK/reprovados). None/ATENDE = byte-identico; REPROVA
                declara a linha com os gates + STATUS, lidos da fonte unica
                veredito_folha_g152 (nunca decididos aqui).
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
    alt_aus = 0
    if ausencias:
        # G140: a caixa vermelha mora acima do rodape; a planta encolhe
        # o mesmo tanto (nunca desenhada embaixo da caixa).
        alt_aus = 40 + len(list(ausencias)) * 20
        H += alt_aus
    MX, MY = 150, 190
    LARG_QUADRO = 430
    larg_util = W - MX - LARG_QUADRO - 160
    alt_util = H - MY - 140 - alt_aus
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
            # estaca ou sem geometria: marca o pilar, nunca some. Com grupo
            # dimensionado (n_estacas) o circulo carrega n/D/L/Ndim para a
            # conferencia por PARSE (G143, mesma forma do rect da sapata).
            n_est = int(g.get("n_estacas") or 0)
            d_est = float(g.get("D_m") or 0.0)
            l_est = float(g.get("L_m") or 0.0)
            P.append('<circle cx="%.1f" cy="%.1f" r="7" fill="white" '
                     'stroke="#b91c1c" stroke-width="1.6" data-pilar="%s" '
                     'data-subtipo="%s" data-n="%d" data-D="%.3f" '
                     'data-L="%.3f" data-Ndim="%.1f"/>'
                     % (cx, cy, sb.esc(nome), sb.esc(str(subtipo)),
                        n_est, d_est, l_est, n_dim))
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
    # G140: com a caixa de ausencias no rodape, o quadro termina acima
    # dela (nunca desenhado embaixo). Sem ausencias, como antes.
    qh = H - qy - 40 - (alt_aus + 12 if ausencias else 0)
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
    # G143: a proveniencia dos parametros da fundacao, lida do resultado
    # (adaptar_galpao_para_locacao). Caminho do predio/casa nao tem a chave
    # e segue byte-identico (nenhum pixel muda).
    prov143 = (fundacao or {}).get("proveniencias_g143")
    if prov143:
        for _lin143 in str(prov143).split(" ; ")[:3]:
            P.append(sb.texto(qx + 14, yy, "G143: %s" % _lin143[:64], 10,
                              anchor="start", color="#555"))
            yy += 15
        yy += 9
    # G149: a proveniencia D_m/L_m/tipo/FS da estaca do predio, lida do
    # resultado (dimensiona). Caminho rasa/casa/sem proveniencia nao tem a
    # chave e segue byte-identico (nenhum pixel muda).
    prov149 = (fundacao or {}).get("proveniencias_g149")
    if prov149:
        for _lin149 in str(prov149).split(" ; ")[:3]:
            P.append(sb.texto(qx + 14, yy, "%s" % _lin149[:72], 10,
                              anchor="start", color="#555"))
            yy += 15
        yy += 9
    # G154: o material com a origem, lido do resultado (dimensiona, fonte
    # unica material_fundacao_g154). So carimba quando ha o que declarar
    # (modelo a confirmar); declarado puro segue sem linha nova.
    prov154 = (fundacao or {}).get("proveniencias_g154")
    if prov154:
        P.append(sb.texto(qx + 14, yy, "%s" % str(prov154)[:72], 10,
                          anchor="start", color="#555"))
        yy += 15
        yy += 9
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
        if yy > H - 96 - (alt_aus + 12 if ausencias else 0):
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
    if ausencias:
        # G140: o que o calculo do galpao nao produz, declarado na folha
        # (nunca default silencioso). Mesma forma do G138.
        ax, ay = (float(MX), float(H - 46 - 24 - alt_aus))
        P.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                 'fill="white" stroke="#b91c1c" stroke-width="1.5"/>'
                 % (ax, ay, W - MX - 170, alt_aus))
        P.append(sb.texto(ax + (W - MX - 170) / 2.0, ay + 24,
                          "DADOS NAO DECLARADOS PELO CALCULO "
                          "DO GALPAO (G140)",
                          12, weight="bold", color="#b91c1c"))
        for i, campo in enumerate(list(ausencias)):
            P.append(sb.texto(ax + 14, ay + 46 + i * 20,
                              "nao declarado: %s" % campo, 11,
                              anchor="start"))
    P.append(sb.texto(MX, H - 28,
                      "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
                      11, anchor="start", weight="bold", color="#444"))
    # G155: veredito lido do resultado pela fonte unica (nunca decidido aqui).
    if veredito is not None:
        from veredito_folha_g152 import veredito_para_folha_svg as _v152
        _lin155, _st155 = _v152(veredito)
        if _lin155 is not None:
            P.append(sb.texto(W / 2, 100, _lin155, 12, weight="bold",
                              color="#b91c1c"))
            if _st155 is not None:
                P.append(sb.texto(W / 2, H - 12, "STATUS: %s" % _st155, 11,
                                  weight="bold", color="#b91c1c"))
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
    # G143: a estaca sai como <circle data-pilar> (sem B/L, com n/D/L no
    # quadro) — conta como elemento desenhado do pilar, como o rect.
    rects += [el for el in (list(raiz.iter(ns + "circle"))
                            + list(raiz.iter("circle")))
              if el.get("data-pilar")]
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
            # G143: estaca desenhada == dimensionada (n/D/L por PARSE).
            for chave, attr in (("n_estacas", "data-n"), ("D_m", "data-D"),
                                ("L_m", "data-L")):
                try:
                    des = float(el.get(attr))
                except (TypeError, ValueError):
                    divergencias.append("%s: %s ausente no desenho"
                                        % (nome, attr))
                    continue
                if abs(des - float(g[chave])) > 1e-3:
                    divergencias.append(
                        "%s: %s desenhado %.3f != dimensionado %.3f"
                        % (nome, chave, des, float(g[chave])))
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
                          edicao=None, veredito=None):
    """Escreve a planta de fundacao (SVG) em `path`. Retorna o path."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_fundacao_svg(fundacao, estrutura, titulo,
                                    edicao=edicao,
                                    veredito=veredito))
    return path


# G140 (D169): o que o calculo do galpao NAO produz para a planta de
# locacao/formas — medido em 2026-09-14 contra `galpao_concreto.rodar`
# (sapata unica dimensionada + spec {vao, comprimento, n_porticos, s} +
# tipo_fundacao; sem `por_pilar`, sem `proveniencia_sigma`, sem
# `cota_apoio_m`) e o que `planta_fundacao_svg` le (shape do predio:
# fundacao.{tipo, sigma_solo_adm, proveniencia_sigma, cota_apoio_m,
# por_pilar[{i, j, N_dimensionamento_kN, geometria}]} +
# estrutura.{vaos_x, vaos_y}). Uma fonte so: esta lista mora na producao
# e a folha a declara, nunca inventa.
AUSENCIAS_GALPAO_LOCACAO = (
    "cota_apoio_m (cota de assentamento nao declarada no spec do galpao; "
    "o calculo usa h_reaterro=0,5 m)",
    "sigma_solo_adm sem sondagem SPT declarada "
    "(default 200 kN/m2; confirmar com sondagem)",
)


def adaptar_galpao_para_locacao(r, spec=None):
    """Adapta o resultado de `galpao_concreto.rodar` para o emissor de
    locacao/formas da fundacao (shape do predio), sem redimensionar nada.

    Devolve (fundacao, estrutura, ausentes): `fundacao`/`estrutura` no
    shape que `planta_fundacao_svg` le — um elemento por pilar (malha de
    2 x n_porticos, nomes P<j><E|D> como no `membros_bim`), cada um com a
    sapata (ou o grupo de estacas) DIMENSIONADA pelo calculo; `ausentes`
    e o subconjunto de `AUSENCIAS_GALPAO_LOCACAO` que o calculo nao
    produz nesta rodada. Ausencia se declara na folha, nunca vira
    default silencioso. Levanta ValueError quando a fundacao nao foi
    dimensionada (sem sapata/estaca aprovada nao ha folha honesta).
    """
    spec = dict(spec or {})
    rsp = ((r or {}).get("spec") or {}) if isinstance(r, dict) else {}
    try:
        vao = float(spec.get("vao", rsp.get("vao")))
        comp = float(spec.get("comprimento", rsp.get("comprimento")))
        n = int(spec.get("n_porticos", rsp.get("n_porticos")))
    except (TypeError, ValueError):
        raise ValueError(
            "adaptar_galpao_para_locacao: vao/comprimento/n_porticos nao "
            "declarados (sem malha de pilares nao ha locacao)")
    if not (vao > 0 and comp > 0 and n >= 2):
        raise ValueError(
            "adaptar_galpao_para_locacao: malha invalida (vao=%r, "
            "comprimento=%r, n_porticos=%r)" % (vao, comp, n))
    try:
        s = float(rsp.get("s") or (comp / (n - 1)))
    except (TypeError, ValueError, ZeroDivisionError):
        raise ValueError(
            "adaptar_galpao_para_locacao: espacamento entre porticos nao "
            "derivado (comprimento=%r, n_porticos=%r)" % (comp, n))
    tipo = ((r or {}).get("tipo_fundacao") or "sapata") \
        if isinstance(r, dict) else "sapata"
    por_pilar = {}
    sigma = None
    if tipo == "estaca":
        est = ((r or {}).get("estaca") or {}) if isinstance(r, dict) else {}
        grupo = (est.get("grupo") or {})
        cap = (est.get("capacidade") or {})
        n_est = grupo.get("n")
        if not n_est:
            raise ValueError(
                "adaptar_galpao_para_locacao: fundacao profunda sem grupo "
                "dimensionado (sem n de estacas nao ha folha PE-CO-04)")
        try:
            Ndim_e = float(est.get("N_pilar", 0.0) or 0.0)
        except (TypeError, ValueError):
            Ndim_e = 0.0
        for j in range(n):
            for lado, i in (("E", 0), ("D", 1)):
                nome = "P%d%s" % (j + 1, lado)
                por_pilar[nome] = {
                    "i": i, "j": j,
                    "N_dimensionamento_kN": Ndim_e,
                    "geometria": {"n_estacas": int(n_est),
                                  "D_m": float(cap.get("D", 0.0) or 0.0),
                                  "L_m": float(cap.get("L", 0.0) or 0.0),
                                  "subtipo": "estaca"},
                }
    else:
        sap = ((r or {}).get("sapata") or {}) if isinstance(r, dict) else {}
        aprovado = sap.get("aprovado")
        if not aprovado or len(aprovado) < 3:
            raise ValueError(
                "adaptar_galpao_para_locacao: sapata nao dimensionada "
                "nesta rodada (sem sapata aprovada nao ha folha PE-CO-04)")
        B, L, h = (float(aprovado[0]), float(aprovado[1]),
                   float(aprovado[2]))
        rA = (aprovado[3] or {}) if len(aprovado) > 3 else {}
        cA = (aprovado[4] or {}) if len(aprovado) > 4 else {}
        try:
            Ndim = float(cA.get("N", rA.get("N_ext_verificacao",
                                            rA.get("N_tot", 0.0))))
        except (TypeError, ValueError):
            Ndim = 0.0
        sigma = cA.get("sigma_solo_adm", rA.get("sigma_adm"))
        for j in range(n):
            for lado, i in (("E", 0), ("D", 1)):
                nome = "P%d%s" % (j + 1, lado)
                por_pilar[nome] = {
                    "i": i, "j": j,
                    "N_dimensionamento_kN": Ndim,
                    "geometria": {"B_m": B, "L_m": L, "h_m": h,
                                  "subtipo": "isolada"},
                }
    # proveniencia: explicita no spec > derivada da sondagem > default
    # sem sondagem (ausencia declarada, nunca "assumida" calada).
    ausentes = []
    tem_spt = bool(spec.get("perfil_spt"))
    tem_geo = isinstance((r or {}).get("geotecnia"), dict)
    sigma_default = False
    if spec.get("sigma_solo_adm") is not None:
        prov = "declarada no spec (sigma_solo_adm)"
    elif tem_spt or tem_geo:
        prov = "derivada da sondagem SPT (geotecnia_spt)"
    else:
        prov = ("default 200 kN/m2 sem sondagem declarada "
                "(confirmar com sondagem)")
        sigma_default = True
    cota = spec.get("cota_apoio")
    if cota is None:
        ausentes.append(AUSENCIAS_GALPAO_LOCACAO[0])
    else:
        try:
            cota = float(cota)
        except (TypeError, ValueError):
            raise ValueError(
                "adaptar_galpao_para_locacao: cota_apoio nao numerica (%r)"
                % (cota,))
    if sigma_default:
        ausentes.append(AUSENCIAS_GALPAO_LOCACAO[1])
    fundacao = {"tipo": tipo, "sigma_solo_adm": sigma,
                "proveniencia_sigma": prov, "cota_apoio_m": cota,
                "por_pilar": por_pilar}
    # G143: a proveniencia dos parametros da fundacao (D/L/tipo da estaca,
    # cota/B_max/mu/sigma) viaja na folha — lida do resultado (fonte unica),
    # nunca inventada aqui. Ausente no resultado antigo -> sem linha (a
    # folha segue como antes).
    try:
        from estaca_parametros_g143 import linha_folha as _lin_folha_g143
        _prov143 = _lin_folha_g143((r or {}).get("fundacao_parametros"))
    except Exception:
        _prov143 = None
    if _prov143:
        fundacao["proveniencias_g143"] = _prov143
    estrutura = {"vaos_x": [vao], "vaos_y": [s] * (n - 1)}
    return fundacao, estrutura, ausentes


def gerar_locacao_galpao(r, path, titulo=None, spec=None):
    """Escreve a locacao/formas da fundacao do GALPAO (PE-CO-04) em `path`.

    G140: adapta o resultado de `galpao_concreto.rodar` (uma fonte so,
    sem redimensionar fundacao) e declara na folha os campos que o
    calculo nao produz. Devolve (path, ausentes)."""
    fundacao, estrutura, ausentes = adaptar_galpao_para_locacao(r, spec)
    n = len(fundacao["por_pilar"])
    rot = "estaca" if fundacao.get("tipo") == "estaca" else "sapata"
    with open(path, "w", encoding="utf-8") as f:
        f.write(planta_fundacao_svg(
            fundacao, estrutura,
            titulo=titulo or ("PE-CO-04 - LOCACAO E FORMAS DA FUNDACAO "
                              "DO GALPAO (%s ; %d pilares)" % (rot, n)),
            ausencias=ausentes or None))
    return path, ausentes
