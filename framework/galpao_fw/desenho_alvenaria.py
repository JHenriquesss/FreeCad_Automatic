# ============================================================================
# desenho_alvenaria.py - PRANCHAS DA ALVENARIA ESTRUTURAL (G62)
# Elevacao das paredes portantes + plantas de 1a/2a fiada + quadro de blocos.
#
# REUSO POR PRIMITIVA (G56): todo texto sai por desenho_svg_base.texto (que ja
# aplica esc()) e toda linha por desenho_svg_base.linha. NUNCA escapar antes de
# chamar texto(): a dupla escapa imprime "&lt;" literal - so o parse do SVG
# pega isso, substring nao. Nenhum `_esc(`/`_t(`/`_line(` local: esse e' o berco
# do bug de dupla-escapa do residencial.
#
# MODULO (NBR 16868-1 5.3.1, bloco 390x190 + junta 10 mm): passo horizontal
# 0,40 m, passo vertical 0,20 m. fiadas(pe) = (inteiras, resto): o resto sai
# como faixa de ajuste/respaldo HACHURADA e rotulada, nunca esticando a fiada.
# Fiadas pares comecam em bloco inteiro, impares em meio bloco (amarracao).
# Os vãos vêm DECLARADOS do resultado (estrutura_casa.validar_vaos_parede):
# o desenho nunca inventa porta/janela.
#
# CONFERENCIAS (drawing-vs-data, padrao que pegou a grade da planta de
# incendio): confere_elevacao/confere_fiadas devolvem contagens para o teste
# comparar contra o calculo - numero de paredes, fiadas, vãos e blocos.
# Unidades de entrada: m. Saida: SVG (string).
# ============================================================================
"""Pranchas de alvenaria estrutural: elevacao, fiadas e quadro de blocos."""

from __future__ import annotations

from desenho_svg_base import abre_svg, linha, texto

# modulo do bloco 390 x 190 com junta de 10 mm (m)
BLOCO_COMP = 0.39
BLOCO_ALT = 0.19
JUNTA = 0.01
PASSO_C = BLOCO_COMP + JUNTA       # 0,40 m
PASSO_A = BLOCO_ALT + JUNTA        # 0,20 m
MEIO_BLOCO = 0.19                  # meio bloco 190 mm (0,19 + junta)

ESC = 90.0                         # px por metro (constante entre paineis)
COR_PAREDE = "#f1f5f9"
COR_JUNTA = "#94a3b8"
COR_VAO = "#ffffff"
COR_VERGA = "#b91c1c"
COR_AJUSTE = "#fde68a"
COR_OK = "#15803d"
COR_REPROVA = "#b91c1c"


def fiadas(pe_direito):
    """(n_inteiras, resto_m): fiadas de 0,20 m que cabem no pe-direito."""
    pe = float(pe_direito)
    n = int(pe // PASSO_A)
    return n, round(pe - n * PASSO_A, 4)


def _juntas_do_curso(L, impar):
    """Posicoes x (m) das juntas verticais de um curso (amarracao)."""
    juntas = []
    inicio = MEIO_BLOCO + JUNTA if impar else PASSO_C
    x = inicio
    while x < L - 1e-9:
        juntas.append(round(x, 4))
        x += PASSO_C
    return juntas


def blocos_do_curso(L, impar, vaos=(), pe_curso0=0.0):
    """(inteiros, meios): blocos de um curso, descontando os vãos que o
    atravessam em altura. Contagem exata sobre as juntas da fiada."""
    L = float(L)
    if impar:
        segs, pos = [], MEIO_BLOCO + JUNTA
        segs.append((0.0, MEIO_BLOCO))          # meio bloco de arranque
        while pos < L - 1e-9:
            fim = min(pos + BLOCO_COMP, L)
            segs.append((pos, fim))
            pos += PASSO_C
    else:
        segs, pos = [], 0.0
        while pos < L - 1e-9:
            fim = min(pos + BLOCO_COMP, L)
            segs.append((pos, fim))
            pos += PASSO_C
    inteiros = meios = 0
    for (a, b) in segs:
        meio = b - a
        atravessa = any(not (b <= v["pos_m"] or a >= v["pos_m"] + v["larg_m"])
                        and v["peitoril_m"] <= pe_curso0 + 1e-9
                        and pe_curso0 < v["peitoril_m"] + v["alt_m"] - 1e-9
                        for v in vaos)
        if atravessa:
            continue
        if meio >= BLOCO_COMP - 1e-9:
            inteiros += 1
        elif meio > 1e-9:
            meios += 1
    base_meios = 1 if impar else 0
    return inteiros, meios, base_meios


def quadro_parede(L, pe_direito, vaos=()):
    """Quadro de blocos da parede cheia menos os vãos (por comprimento)."""
    n, resto = fiadas(pe_direito)
    inteiros = meios = 0
    for k in range(n):
        i, m, _ = blocos_do_curso(L, impar=bool(k % 2), vaos=vaos,
                                  pe_curso0=k * PASSO_A)
        inteiros += i
        meios += m
    area_bruta = L * pe_direito
    area_vaos = sum(v["larg_m"] * v["alt_m"] for v in vaos)
    return {"inteiros": inteiros, "meios": meios,
            "n_fiadas": n, "ajuste_m": resto,
            "area_bruta_m2": round(area_bruta, 2),
            "area_vaos_m2": round(area_vaos, 2),
            "area_liquida_m2": round(area_bruta - area_vaos, 2)}


def _painel_elevacao(partes, reg, pe_direito, te, y0):
    """Um painel de elevação; devolve (altura_px, contagens)."""
    L = float(reg["comprimento_m"])
    vaos = reg.get("vaos") or []
    n, resto = fiadas(pe_direito)
    W = L * ESC
    x0 = 70.0
    h_px = pe_direito * ESC
    y_base = y0 + 46.0 + h_px            # cota zero da parede (base)
    y_topo = y_base - h_px

    ver = (reg.get("verificacao") or {})
    cor = COR_OK if reg.get("OK") else COR_REPROVA
    estado = "ATENDE" if reg.get("OK") else "REPROVA"
    partes.append(texto(x0, y0 + 22,
                           "PAREDE %s - L=%.2f m e=%.0f cm - %s"
                           % (reg["nome"], L, te * 100, estado),
                           14, anchor="start", weight="bold", color=cor))
    partes.append(texto(x0, y0 + 40,
                           "Nd=%.1f kN NRd=%s kN/m %.2f - %d fiadas + ajuste %.0f cm"
                           % (reg.get("N_wall_d_kN", 0.0),
                              ("%.1f" % ver.get("NRd_kN"))
                              if ver.get("NRd_kN") is not None else "-",
                              (ver.get("NRd_kN_m")
                               if ver.get("NRd_kN_m") is not None else 0.0),
                              n, resto * 100),
                           11, anchor="start", color="#555"))
    # corpo da parede
    partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                  'fill="%s" stroke="#111" stroke-width="1.6" data-parede="%s"/>'
                  % (x0, y_topo, W, h_px, COR_PAREDE, reg["nome"]))
    # fiadas + juntas alternadas
    for k in range(n):
        y = y_base - k * PASSO_A * ESC
        partes.append(linha(x0, y, x0 + W, y, 0.8, COR_JUNTA))
        for jx in _juntas_do_curso(L, impar=bool(k % 2)):
            partes.append(linha(x0 + jx * ESC, y - PASSO_A * ESC,
                                   x0 + jx * ESC, y, 0.6, COR_JUNTA))
        partes.append(texto(x0 + W + 8, y - 4, "F%d" % (k + 1), 9,
                               anchor="start", color="#777"))
    if resto > 1e-9:
        partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                      'fill="%s" stroke="#92400e" stroke-width="1" '
                      'stroke-dasharray="6 3" data-ajuste="%s"/>'
                      % (x0, y_topo - resto * ESC, W, resto * ESC,
                         COR_AJUSTE, reg["nome"]))
        partes.append(texto(x0 + W + 8, y_topo - resto * ESC / 2,
                               "ajuste %.0f cm" % (resto * 100), 9,
                               anchor="start", color="#92400e"))
    # vãos + vergas/contravergas
    for iv, v in enumerate(vaos):
        vx = x0 + v["pos_m"] * ESC
        vw = v["larg_m"] * ESC
        vy_topo = y_base - (v["peitoril_m"] + v["alt_m"]) * ESC
        vh = v["alt_m"] * ESC
        partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                      'fill="%s" stroke="#111" stroke-width="1.4" data-vao="%s-%d"/>'
                      % (vx, vy_topo, vw, vh, COR_VAO, reg["nome"], iv))
        partes.append(texto(vx + vw / 2, vy_topo - 6,
                               "%s %.0fx%.0f" % (v["tipo"], v["larg_m"] * 100,
                                                 v["alt_m"] * 100),
                               10, weight="bold"))
        # verga: larg + 0,40 de apoio, acima do vão
        partes.append(linha(vx - 0.20 * ESC, vy_topo - 4,
                               vx + vw + 0.20 * ESC, vy_topo - 4,
                               2.2, COR_VERGA, dash="8 3"))
        partes.append(texto(vx + vw + 0.20 * ESC + 4, vy_topo - 1,
                               "verga", 9, anchor="start", color=COR_VERGA))
        if v["peitoril_m"] > 1e-9:      # janela: contraverga sob o peitoril
            y_peit = y_base - v["peitoril_m"] * ESC
            partes.append(linha(vx - 0.20 * ESC, y_peit + 10,
                                   vx + vw + 0.20 * ESC, y_peit + 10,
                                   2.2, COR_VERGA, dash="8 3"))
            partes.append(texto(vx + vw + 0.20 * ESC + 4, y_peit + 13,
                                   "contraverga", 9, anchor="start",
                                   color=COR_VERGA))
    altura = 46.0 + h_px + 34.0
    return altura, {"paredes": 1, "fiadas": n, "vaos": len(vaos),
                    "ajuste": 1 if resto > 1e-9 else 0}


def elevacao_paredes_svg(alvenaria, pe_direito, te, titulo=None):
    """Todas as elevações empilhadas + quadro de blocos (UMA folha)."""
    regs = alvenaria.get("por_linha") or []
    tit = titulo or "ELEVACAO DAS PAREDES PORTANTES - NBR 16868-1 5.3.1"
    W = 1100.0
    partes = abre_svg(W, 100, tit)
    y = 60.0
    tot = {"paredes": 0, "fiadas": 0, "vaos": 0, "ajuste": 0,
           "inteiros": 0, "meios": 0,
           "area_bruta_m2": 0.0, "area_vaos_m2": 0.0}
    for reg in regs:
        L = float(reg["comprimento_m"])
        Wnec = 70.0 + L * ESC + 120.0
        if Wnec > W:                      # painel mais largo que a folha
            W = Wnec
        alt, cont = _painel_elevacao(partes, reg, pe_direito, te, y)
        q = quadro_parede(L, pe_direito, reg.get("vaos") or [])
        partes.append(texto(70.0, y + alt - 8,
                               "blocos: %d int + %d meios - area %.2f - vaos %.2f = liq %.2f m2"
                               % (q["inteiros"], q["meios"], q["area_bruta_m2"],
                                  q["area_vaos_m2"], q["area_liquida_m2"]),
                               11, anchor="start"))
        y += alt + 18.0
        for k in tot:
            if k in cont:
                tot[k] += cont[k]
        tot["inteiros"] += q["inteiros"]
        tot["meios"] += q["meios"]
        tot["area_bruta_m2"] += q["area_bruta_m2"]
        tot["area_vaos_m2"] += q["area_vaos_m2"]
    partes.append(texto(70.0, y + 6,
                           "TOTAL: %d paredes - %d int + %d meios - bruta %.2f - vaos %.2f m2"
                           % (tot["paredes"], tot["inteiros"], tot["meios"],
                              round(tot["area_bruta_m2"], 2),
                              round(tot["area_vaos_m2"], 2)),
                           12, anchor="start", weight="bold"))
    svg = "\n".join(partes) + "\n</svg>"
    svg = svg.replace('width="100"',
                      'width="%.0f"' % W, 1)
    svg = svg.replace('viewBox="0 0 100 ',
                      'viewBox="0 0 %.0f ' % W, 1)
    svg = svg.replace('height="100"',
                      'height="%.0f"' % (y + 30.0), 1)
    return svg


def confere_elevacao(svg, alvenaria, pe_direito):
    """Paredes, fiadas, vãos e ajustes DESENHADOS x CALCULADOS."""
    import xml.etree.ElementTree as _ET

    root = _ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    rects = list(root.iter(ns + "rect")) + list(root.iter("rect"))
    regs = alvenaria.get("por_linha") or []
    n_paredes = sum(1 for r in rects if r.get("data-parede"))
    n_vaos = sum(1 for r in rects if r.get("data-vao") is not None)
    n_ajustes = sum(1 for r in rects if r.get("data-ajuste"))
    n_fiadas_esp, resto = fiadas(pe_direito)
    return {
        "paredes_desenhadas": n_paredes,
        "paredes_calculadas": len(regs),
        "vaos_desenhados": n_vaos,
        "vaos_declarados": sum(len(r.get("vaos") or []) for r in regs),
        "fiadas_por_parede": n_fiadas_esp,
        "ajustes_desenhados": n_ajustes,
        "ajustes_esperados": (len(regs) if resto > 1e-9 else 0),
        "ok": (n_paredes == len(regs)
               and n_vaos == sum(len(r.get("vaos") or []) for r in regs)
               and n_ajustes == (len(regs) if resto > 1e-9 else 0)),
    }


def planta_fiadas_svg(alvenaria, vaos_x, vaos_y, te, titulo=None):
    """Plantas de 1a e 2a fiada lado a lado, com amarracao e vãos."""
    regs = {r["nome"]: r for r in (alvenaria.get("por_linha") or [])}
    tit = titulo or "PLANTAS DE 1a E 2a FIADAS - AMARRACAO"
    LX, LY = sum(vaos_x), sum(vaos_y)
    esc = min(380.0 / LX, 300.0 / LY)
    W, H = 1000.0, 560.0
    partes = abre_svg(W, H, tit)
    for col, (fiada, impar) in enumerate((("1a FIADA", False), ("2a FIADA", True))):
        ox = 70.0 + col * 500.0
        oy = 120.0
        partes.append(texto(ox + LX * esc / 2, oy - 30, fiada, 14,
                               weight="bold"))
        # faixa das paredes (linhas de contorno/todas como calculado)
        for reg in alvenaria.get("por_linha") or []:
            L = float(reg["comprimento_m"])
            vaos = reg.get("vaos") or []
            if reg["eixo"] == "x":
                # posicao y pela ordem da linha na malha
                y = oy + _y_da_linha_x(reg, vaos_y, esc, LY)
                x = ox
                partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                              'fill="none" stroke="#111" stroke-width="1.6" '
                              'data-fiadas-parede="%s-%d"/>'
                              % (x, y - te * esc / 2, L * esc, te * esc,
                                 reg["nome"], 1 + col))
                for jx in _juntas_do_curso(L, impar):
                    partes.append(linha(x + jx * esc, y - te * esc / 2,
                                           x + jx * esc, y + te * esc / 2,
                                           0.7, COR_JUNTA))
                for v in vaos:
                    partes.append('<rect x="%.1f" y="%.1f" width="%.1f" '
                                  'height="%.1f" fill="white" stroke="#111" '
                                  'stroke-width="1.2" data-fiadas-vao="%s-%d"/>'
                                  % (x + v["pos_m"] * esc, y - te * esc / 2,
                                     v["larg_m"] * esc, te * esc,
                                     reg["nome"], 1 + col))
            else:
                x = ox + _x_da_linha_y(reg, vaos_x, esc)
                y = oy
                partes.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                              'fill="none" stroke="#111" stroke-width="1.6" '
                              'data-fiadas-parede="%s-%d"/>'
                              % (x - te * esc / 2, y, te * esc, L * esc,
                                 reg["nome"], 1 + col))
                for jx in _juntas_do_curso(L, impar):
                    partes.append(linha(x - te * esc / 2, y + jx * esc,
                                           x + te * esc / 2, y + jx * esc,
                                           0.7, COR_JUNTA))
                for v in vaos:
                    partes.append('<rect x="%.1f" y="%.1f" width="%.1f" '
                                  'height="%.1f" fill="white" stroke="#111" '
                                  'stroke-width="1.2" data-fiadas-vao="%s-%d"/>'
                                  % (x - te * esc / 2, y + v["pos_m"] * esc,
                                     te * esc, v["larg_m"] * esc,
                                     reg["nome"], 1 + col))
        partes.append(texto(ox, oy + LY * esc + 40,
                               "amarracao: impar inicia em meio bloco" if impar
                               else "amarracao: pares iniciam em bloco inteiro",
                               11, anchor="start", color="#555"))
    partes.append("</svg>")
    return "\n".join(partes)


def _y_da_linha_x(reg, vaos_y, esc, LY):
    """Posicao y (px, origem no topo do desenho) da linha X pelo indice."""
    ys = [0.0]
    for v in vaos_y:
        ys.append(ys[-1] + float(v))
    y_m = ys[int(reg["indice"])]
    return (LY - y_m) * esc


def _x_da_linha_y(reg, vaos_x, esc):
    """Posicao x (px) da linha Y pelo indice."""
    xs = [0.0]
    for v in vaos_x:
        xs.append(xs[-1] + float(v))
    return xs[int(reg["indice"])] * esc


def confere_fiadas(svg, alvenaria):
    """Paredes e vãos por fiada DESENHADOS x CALCULADOS (duas fiadas)."""
    import xml.etree.ElementTree as _ET

    root = _ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    rects = list(root.iter(ns + "rect")) + list(root.iter("rect"))
    regs = alvenaria.get("por_linha") or []
    n_par = sum(1 for r in rects if r.get("data-fiadas-parede"))
    n_vao = sum(1 for r in rects if r.get("data-fiadas-vao") is not None)
    n_vaos = sum(len(r.get("vaos") or []) for r in regs)
    return {
        "paredes_por_fiada": n_par // 2 if n_par else 0,
        "paredes_calculadas": len(regs),
        "vaos_por_fiada": n_vao // 2 if n_vao else 0,
        "vaos_declarados": n_vaos,
        "ok": (n_par == 2 * len(regs) and n_vao == 2 * n_vaos),
    }


def gerar_pranchas_alvenaria(estrutura, out_dir):
    """Escreve elevacao-paredes.svg + planta-fiadas.svg em out_dir.

    Retorna {"files", "skipped"} com motivo nomeado por folha ausente.
    """
    from pathlib import Path

    destino = Path(out_dir)
    destino.mkdir(parents=True, exist_ok=True)
    gerados, ignorados = [], {}
    alv = (estrutura or {}).get("alvenaria")
    if not isinstance(alv, dict) or not alv.get("por_linha"):
        ignorados["elevacao-paredes.svg"] = "parede_portante_nao_calculada"
        ignorados["planta-fiadas.svg"] = "parede_portante_nao_calculada"
        return {"files": gerados, "skipped": ignorados}
    n_pav = int(estrutura.get("n_pavimentos") or 1)
    pe = float(estrutura.get("H_total_m", 0.0)) / max(n_pav, 1)
    te = float(alv.get("te_m") or 0.14)
    try:
        (destino / "elevacao-paredes.svg").write_text(
            elevacao_paredes_svg(alv, pe, te), encoding="utf-8")
        gerados.append("elevacao-paredes.svg")
    except Exception as exc:                            # noqa: BLE001
        ignorados["elevacao-paredes.svg"] = "falha_no_desenho: %s" % exc
    try:
        pav = estrutura.get("pavimento") or {}
        (destino / "planta-fiadas.svg").write_text(
            planta_fiadas_svg(alv, pav.get("vaos_x"), pav.get("vaos_y"), te),
            encoding="utf-8")
        gerados.append("planta-fiadas.svg")
    except Exception as exc:                            # noqa: BLE001
        ignorados["planta-fiadas.svg"] = "falha_no_desenho: %s" % exc
    return {"files": gerados, "skipped": ignorados}


def _selftest():
    import xml.etree.ElementTree as ET

    alv = {"por_linha": [
        {"nome": "BX-0", "eixo": "x", "indice": 0, "comprimento_m": 4.0,
         "N_wall_d_kN": 50.0, "OK": True,
         "verificacao": {"NRd_kN": 80.0, "NRd_kN_m": 20.0},
         "vaos": [{"pos_m": 1.0, "larg_m": 0.8, "alt_m": 2.1,
                   "peitoril_m": 0.0, "tipo": "porta"}]},
        {"nome": "BY-0", "eixo": "y", "indice": 0, "comprimento_m": 3.0,
         "N_wall_d_kN": 40.0, "OK": True,
         "verificacao": {"NRd_kN": 60.0, "NRd_kN_m": 20.0}, "vaos": []}],
        "te_m": 0.14}
    svg = elevacao_paredes_svg(alv, 2.7, 0.14)
    ET.fromstring(svg)                                  # XML valido, '<' escapado
    c = confere_elevacao(svg, alv, 2.7)
    assert c["ok"], c
    assert c["paredes_desenhadas"] == 2 and c["vaos_desenhados"] == 1
    svg2 = planta_fiadas_svg(alv, [4.0], [3.0], 0.14)
    ET.fromstring(svg2)
    c2 = confere_fiadas(svg2, alv)
    assert c2["ok"], c2
    q = quadro_parede(4.0, 2.7, alv["por_linha"][0]["vaos"])
    assert q["n_fiadas"] == 13 and q["area_vaos_m2"] == round(0.8 * 2.1, 2)
    # amarracao: impar comeca em meio bloco
    assert _juntas_do_curso(4.0, False)[0] == PASSO_C
    assert _juntas_do_curso(4.0, True)[0] == MEIO_BLOCO + JUNTA
    print("desenho_alvenaria self-test PASSED (2 folhas XML-validas)")
    return True


if __name__ == "__main__":
    _selftest()
