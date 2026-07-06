# ============================================================================
# terreno.py - O QUE ESTE SCRIPT FAZ / CALCULA
# PASSO ZERO do projeto: viabilidade do TERRENO (vem ANTES da estrutura, pois
# LIMITA as dimensoes do galpao). Le o lote em KML (Google Earth) ou em
# coordenadas, calcula a AREA e aplica os parametros urbanisticos da lei de uso
# do solo / plano diretor (que sao dados de entrada do gate, nao inventados):
#   - TAXA DE OCUPACAO (TO): projecao horizontal maxima da edificacao / lote.
#   - TAXA DE PERMEABILIDADE (TP): area permeavel MINIMA / lote (drenagem -
#     "pontos de escoamento para o solo"); logo a area impermeavel <= (1-TP)*lote.
#   - COEFICIENTE DE APROVEITAMENTO (CA): area construida total (todos os
#     pavimentos) / lote.
#   - RECUOS (frente/lateral/fundos): afastamentos das divisas -> encolhem o
#     retangulo construivel.
# Saida: area do lote, limites (footprint max por TO, area construida max por CA,
# area permeavel minima por TP), o retangulo construivel (bbox - recuos) e a
# verificacao de um galpao proposto contra tudo isso.
#
# Projecao: equirretangular local (lat/lon -> metros com a latitude media), exata
# em escala de lote (erro < 0,1%). Para lotes grandes / levantamento de precisao,
# confirmar com UTM/geodesico. Calcula apenas; pendente revisao do responsavel.
# ============================================================================
"""Viabilidade do terreno (KML/coord) + parametros urbanisticos - passo zero."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

R_TERRA = 6378137.0     # raio equatorial WGS84 (m)


def parse_kml(kml_texto_ou_caminho):
    """Extrai o 1o poligono (outerBoundary) de um KML. Aceita texto ou caminho.
    Retorna lista de (lon, lat) em graus."""
    txt = kml_texto_ou_caminho
    if "<" not in txt:                       # e um caminho de arquivo
        with open(txt, encoding="utf-8") as f:
            txt = f.read()
    root = ET.fromstring(txt)
    blocos = [e.text for e in root.iter() if e.tag.split("}")[-1] == "coordinates"]
    if not blocos:
        raise ValueError("KML sem <coordinates>")
    pts = []
    for c in blocos[0].replace("\n", " ").split():
        lon, lat = (float(v) for v in c.split(",")[:2])
        pts.append((lon, lat))
    return pts


def projeta_metros(pts_lonlat):
    """Projecao equirretangular local (origem no 1o ponto, lat media)."""
    lon0, lat0 = pts_lonlat[0]
    latm = math.radians(sum(p[1] for p in pts_lonlat) / len(pts_lonlat))
    out = []
    for lon, lat in pts_lonlat:
        x = math.radians(lon - lon0) * math.cos(latm) * R_TERRA
        y = math.radians(lat - lat0) * R_TERRA
        out.append((x, y))
    return out


def area_poligono_m2(pts_xy):
    """Area por shoelace (m2). Fecha o poligono automaticamente."""
    p = list(pts_xy)
    if p[0] != p[-1]:
        p.append(p[0])
    s = sum(p[i][0] * p[i + 1][1] - p[i + 1][0] * p[i][1] for i in range(len(p) - 1))
    return abs(s) / 2.0


def _bbox(pts_xy):
    """Bounding box ALINHADO AOS EIXOS (N-S / L-O) - so informativo."""
    xs = [p[0] for p in pts_xy]; ys = [p[1] for p in pts_xy]
    return max(xs) - min(xs), max(ys) - min(ys)


def _convex_hull(pts):
    """Fecho convexo (monotone chain de Andrew). Retorna vertices CCW."""
    p = sorted(set(pts))
    if len(p) <= 2:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    upper = []
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]


def _obb(pts_xy):
    """Retangulo envolvente de AREA MINIMA (Oriented Bounding Box), medido pelos
    eixos do PROPRIO lote (nao Norte). Corrige a distorcao do AABB para lotes
    girados. Retorna (lado_maior, lado_menor, angulo_rad). Rotating calipers:
    o retangulo minimo tem um lado colinear a uma aresta do fecho convexo."""
    h = _convex_hull(pts_xy)
    if len(h) < 3:
        w, d = _bbox(pts_xy)
        return max(w, d), min(w, d), 0.0
    best = None
    n = len(h)
    for i in range(n):
        ax, ay = h[i]; bx, by = h[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        L = math.hypot(ex, ey)
        if L < 1e-12:
            continue
        ux, uy = ex / L, ey / L          # eixo ao longo da aresta
        vx, vy = -uy, ux                 # eixo perpendicular
        us = [px * ux + py * uy for px, py in h]
        vs = [px * vx + py * vy for px, py in h]
        w = max(us) - min(us); d = max(vs) - min(vs)
        area = w * d
        if best is None or area < best[0]:
            best = (area, max(w, d), min(w, d), math.atan2(uy, ux))
    return best[1], best[2], best[3]


def analisa_terreno(cfg):
    """Viabilidade do lote. cfg (do gate):
      kml / pts_lonlat / pts_xy (uma das formas de dar o lote) ;
      to_max, ca_max, tp_min (fracoes 0..1) ;
      recuo_frente, recuo_lateral, recuo_fundos (m) ; n_pav (opcional, p/ CA).
    """
    if "pts_xy" in cfg:
        xy = cfg["pts_xy"]
    else:
        pts = cfg["pts_lonlat"] if "pts_lonlat" in cfg else parse_kml(cfg["kml"])
        xy = projeta_metros(pts)
    A = area_poligono_m2(xy)
    W, D = _bbox(xy)                              # AABB (N-S/L-O) - informativo
    lado_maior, lado_menor, ang = _obb(xy)       # OBB (eixos do lote) - correto
    rf = cfg.get("recuo_frente", 0.0); rl = cfg.get("recuo_lateral", 0.0)
    rfu = cfg.get("recuo_fundos", 0.0)
    # Retangulo construivel medido pelos eixos do lote (OBB): lado MENOR = frente
    # (recuos frente+fundos) ; lado MAIOR = profundidade (recuos laterais). Ajuste
    # a orientacao no gate se a testada nao for o lado menor.
    Dc = max(0.0, lado_menor - rf - rfu)         # sentido da testada (frente)
    Wc = max(0.0, lado_maior - 2 * rl)           # sentido das laterais
    to, ca, tp = cfg["to_max"], cfg["ca_max"], cfg["tp_min"]
    return {"area_lote_m2": A, "bbox_m": (W, D), "obb_m": (lado_maior, lado_menor),
            "obb_angulo_graus": round(math.degrees(ang), 1),
            "retangulo_construivel_m": (Wc, Dc),
            "footprint_max_TO_m2": to * A, "area_construida_max_CA_m2": ca * A,
            "area_permeavel_min_TP_m2": tp * A, "area_impermeavel_max_m2": (1 - tp) * A,
            "to_max": to, "ca_max": ca, "tp_min": tp,
            "recuos_m": (rf, rl, rfu), "n_pav": cfg.get("n_pav", 1)}


def verifica_galpao(terr, comprimento, largura, n_pav=1, area_pavimentada=0.0):
    """Verifica um galpao (comprimento x largura, m) contra o terreno.
    area_pavimentada = piso externo impermeavel adicional (patio, manobra)."""
    footprint = comprimento * largura
    area_construida = footprint * n_pav
    impermeavel = footprint + area_pavimentada
    (Wc, Dc) = terr["retangulo_construivel_m"]
    cabe = ((comprimento <= Wc + 1e-6 and largura <= Dc + 1e-6) or
            (comprimento <= Dc + 1e-6 and largura <= Wc + 1e-6))
    checks = {
        "TO (footprint)": (footprint, terr["footprint_max_TO_m2"], footprint <= terr["footprint_max_TO_m2"]),
        "CA (area construida)": (area_construida, terr["area_construida_max_CA_m2"],
                                 area_construida <= terr["area_construida_max_CA_m2"]),
        "TP (impermeavel)": (impermeavel, terr["area_impermeavel_max_m2"],
                             impermeavel <= terr["area_impermeavel_max_m2"]),
        "Recuos (cabe no retangulo)": (footprint, Wc * Dc, cabe)}
    ok = all(v[2] for v in checks.values())
    return {"footprint_m2": footprint, "area_construida_m2": area_construida,
            "impermeavel_m2": impermeavel, "cabe_no_retangulo": cabe,
            "checks": checks, "OK": ok}


def relatorio_pt(terr, ver=None):
    L = ["=" * 70, "VIABILIDADE DO TERRENO (parametros urbanisticos - lei de uso do solo)",
         "=" * 70,
         f"  Area do lote ................ {terr['area_lote_m2']:.1f} m2",
         f"  AABB (N-S x L-O, informativo) {terr['bbox_m'][0]:.1f} x {terr['bbox_m'][1]:.1f} m",
         f"  OBB (eixos do lote) ......... {terr['obb_m'][0]:.1f} x {terr['obb_m'][1]:.1f} m "
         f"(girado {terr['obb_angulo_graus']} graus do Norte)",
         f"  Recuos (frente/lat/fundos) .. {terr['recuos_m']} m",
         f"  Retangulo construivel ....... {terr['retangulo_construivel_m'][0]:.1f} x "
         f"{terr['retangulo_construivel_m'][1]:.1f} m",
         f"  TO max ({terr['to_max']*100:.0f}%) footprint .... <= {terr['footprint_max_TO_m2']:.1f} m2",
         f"  CA max ({terr['ca_max']:.2f}) area constr. .. <= {terr['area_construida_max_CA_m2']:.1f} m2",
         f"  TP min ({terr['tp_min']*100:.0f}%) permeavel ..... >= {terr['area_permeavel_min_TP_m2']:.1f} m2 "
         f"(impermeavel <= {terr['area_impermeavel_max_m2']:.1f} m2)"]
    if ver is not None:
        L += ["-" * 70, "  GALPAO PROPOSTO:",
              f"    Footprint = {ver['footprint_m2']:.1f} m2 ; area construida = "
              f"{ver['area_construida_m2']:.1f} m2 ; impermeavel = {ver['impermeavel_m2']:.1f} m2"]
        for nome, (val, lim, okc) in ver["checks"].items():
            L.append(f"    {nome}: {val:.1f} / {lim:.1f} -> {'OK' if okc else 'NAO PASSA'}")
        L.append(f"  >> {'VIAVEL' if ver['OK'] else 'NAO VIAVEL (ver acima)'}")
    L.append("=" * 70)
    return "\n".join(L)


def _selftest():
    # Lote ~110 x 110 m (KML de teste); TO 60%, CA 1,0, TP 15%, recuos 5/1,5/3.
    kml = ('<kml xmlns="http://www.opengis.net/kml/2.2"><Placemark><Polygon>'
           '<outerBoundaryIs><LinearRing><coordinates>'
           '-46.6330,-23.5500,0 -46.6320,-23.5500,0 -46.6320,-23.5510,0 '
           '-46.6330,-23.5510,0 -46.6330,-23.5500,0'
           '</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></kml>')
    cfg = {"kml": kml, "to_max": 0.60, "ca_max": 1.0, "tp_min": 0.15,
           "recuo_frente": 5.0, "recuo_lateral": 1.5, "recuo_fundos": 3.0, "n_pav": 1}
    terr = analisa_terreno(cfg)
    # galpao 20 x 10 (footprint 200 m2)
    ver = verifica_galpao(terr, comprimento=20.0, largura=10.0, n_pav=1,
                          area_pavimentada=150.0)
    print(relatorio_pt(terr, ver))
    assert terr["area_lote_m2"] > 10000     # ~110x110 ~ 12000 m2
    assert ver["OK"]                        # galpao pequeno cabe folgado
    # galpao gigante (footprint > TO) -> nao viavel
    ver2 = verifica_galpao(terr, comprimento=120.0, largura=100.0)
    assert ver2["OK"] is False
    # --- OBB: lote retangular 50 x 20 m GIRADO 45 graus (X/Y em metros) --------
    import math as _m
    c, s = _m.cos(_m.radians(45)), _m.sin(_m.radians(45))
    ret = [(0, 0), (50, 0), (50, 20), (0, 20)]
    xy = [(x * c - y * s, x * s + y * c) for x, y in ret]     # gira 45 graus
    t2 = analisa_terreno({"pts_xy": xy, "to_max": 1.0, "ca_max": 2.0, "tp_min": 0.0,
                          "recuo_frente": 0.0, "recuo_lateral": 0.0, "recuo_fundos": 0.0})
    lado_maior, lado_menor = t2["obb_m"]
    # OBB recupera 50 x 20 (nao ~53 x 53 do AABB)
    assert abs(lado_maior - 50.0) < 0.5 and abs(lado_menor - 20.0) < 0.5, t2["obb_m"]
    # AABB distorce: lado real de 20 m aparece como ~49,5 (inflado) -> prova o erro
    assert t2["bbox_m"][1] > 40.0, t2["bbox_m"]
    print("\n[selftest] OK (inclui lote girado 45 graus: OBB recupera 50x20)")


if __name__ == "__main__":
    _selftest()
