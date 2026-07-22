# ============================================================================
# modelo_neutro.py - MODELO NEUTRO (puro, SEM FreeCAD) do portico primario do
# galpao: a "receita" da estrutura como DADOS (barras com perfil + extremidades +
# secao), nao como chamadas de API do FreeCAD. E a camada de intercambio entre o
# CALCULO e os EMISSORES (FreeCAD, IFC, ...). Item 2 do roteiro de
# interoperabilidade: com o modelo neutro, o FreeCAD deixa de ser obrigatorio para
# o entregavel BIM (ver ifc_emit.py, emissor IFC puro-Python).
#
# Escopo desta 1a versao: estrutura PRIMARIA (colunas + rafters/meias-aguas). Os
# secundarios, chapas e ligacoes seguem no modelo do FreeCAD (build_galpao) ate
# serem migrados. Coordenadas em MILIMETROS (padrao do IFC de galpao). O eixo do
# galpao: X = comprimento (linha de porticos), Y = vao(s) transversal(is), Z =
# altura. As secoes (d, bf, tw, tf) chegam em METROS (catalogo perfis) e o membro
# guarda-as como estao; o emissor converte p/ mm.
# ============================================================================
"""Modelo neutro (puro) do portico primario: barras com perfil + extremidades."""

from __future__ import annotations

MM = 1000.0


def _n_porticos(comprimento, bay):
    return int(round(comprimento / bay)) + 1 if bay > 0 else 1


def frame_primario(geometria, secoes):
    """Monta o modelo neutro das barras PRIMARIAS (colunas + rafters).
    geometria: {span|spans, comprimento, eave, ridge, bay} em METROS.
    secoes: {"col": {nome, d, bf, tw, tf}, "raf": {nome, d, bf, tw, tf}} em METROS.
    Retorna lista de membros; cada um:
      {marca, perfil, tipo ("Column"/"Beam"), p1 (mm), p2 (mm), secao (m)}."""
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    bay = float(geometria["bay"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    np_ = _n_porticos(comp, bay)
    xs = [comp * i / (np_ - 1) for i in range(np_)] if np_ > 1 else [0.0]
    cols_y = [0.0]                                   # linhas de coluna em Y
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    col, raf = secoes["col"], secoes["raf"]
    membros = []
    for x in xs:
        # COLUNAS: uma por linha de vao, da base (Z=0) ao beiral (Z=eave)
        for y in cols_y:
            membros.append({"marca": "C1", "perfil": col["nome"], "tipo": "Column",
                            "p1": (x * MM, y * MM, 0.0),
                            "p2": (x * MM, y * MM, eave * MM), "secao": col})
        # RAFTERS: 2 meias-aguas por vao (do beiral a cumeeira, subindo)
        for j in range(len(spans)):
            yr = (cols_y[j] + cols_y[j + 1]) / 2.0
            for ya in (cols_y[j], cols_y[j + 1]):
                membros.append({"marca": "V%d" % (j + 1), "perfil": raf["nome"],
                                "tipo": "Beam",
                                "p1": (x * MM, ya * MM, eave * MM),
                                "p2": (x * MM, yr * MM, ridge * MM), "secao": raf})
    return membros


def tercas(geometria, n_terca, terca_sec):
    """Terças (purlins) LONGITUDINAIS do modelo neutro: barras X=0->comprimento na
    altura do rafter, `n_terca-1` posicoes INTERMEDIARIAS por agua (eave e cumeeira
    ficam com as tercas de beiral/cumeeira, fora deste conjunto), nas duas aguas de
    cada vao. Replica a convencao do build_galpao (loop das tercas, k=1..n_terca-1,
    yl interpolado eave->ridge; ver terca_ys la) - guardado por cross-check de
    contagem em test_modelo_neutro. terca_sec: {nome, h/d, bf, t, lip} (m), forma C.
    Assenta no TOPO do rafter (z = rafter + meia-alma do rafter + meia-alma da terca)."""
    if not n_terca or n_terca < 2 or not terca_sec:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    ridge = float(geometria.get("ridge", eave))
    raf_d = float(geometria.get("raf_d", 0.0))       # altura do rafter (m), p/ o assento
    t_h = float(terca_sec.get("d") or terca_sec.get("h") or 0.0)
    off = (raf_d / 2.0 + t_h / 2.0)                  # terca no topo do rafter
    cols_y = [0.0]
    for s in spans:
        cols_y.append(cols_y[-1] + s)
    nome = terca_sec.get("nome", "Terca")

    def _terca(yl, zl):
        ms.append({"marca": "T1", "perfil": nome, "tipo": "Member",
                   "p1": (0.0, yl * MM, zl * MM),
                   "p2": (comp * MM, yl * MM, zl * MM), "secao": terca_sec})

    ms = []
    for j in range(len(spans)):
        y0, y1 = cols_y[j], cols_y[j + 1]
        yr = (y0 + y1) / 2.0                          # cumeeira do vao
        for k in range(1, int(n_terca)):
            for (ya, yb) in ((y0, yr), (y1, yr)):     # agua E (sobe ate cumeeira) e D
                yl = ya + (yb - ya) * k / n_terca
                zl = eave + (ridge - eave) * (yl - ya) / (yb - ya) + off
                _terca(yl, zl)
    # tercas de BEIRAL: uma em cada lado externo do galpao (cols_y[0] e cols_y[-1]),
    # na cota do beiral (mesma convencao do build_galpao, TERCA_BEIRAL_E/D).
    _terca(cols_y[0], eave + off)
    _terca(cols_y[-1], eave + off)
    return ms


GIRT_Z_MM = (2000.0, 4000.0)                          # niveis dos girts (mm) - espelha o build


def girts(geometria, girt_sec, col_d=0.0):
    """Girts de parede (longarinas): U LONGITUDINAIS em 2 niveis (GIRT_Z_MM), nas 2
    paredes longitudinais (y = -GOFF e y = SPAN + GOFF, GOFF = col_d/2 + girt_d/2 =
    girt contra a mesa do pilar). Perfil U (UPE). Espelha o build_galpao
    (TERCA_PAREDE), caso comum sem porta lateral (que segmentaria a parede). Niveis
    acima do beiral sao descartados. col_d e a altura do pilar (m)."""
    if not girt_sec:
        return []
    spans = geometria.get("spans") or [geometria.get("span")]
    spans = [float(s) for s in spans if s]
    comp = float(geometria["comprimento"])
    eave = float(geometria["eave"])
    span_tot = sum(spans)
    girt_d = float(girt_sec.get("d") or girt_sec.get("h") or 0.0)
    goff = col_d / 2.0 + girt_d / 2.0
    nome = girt_sec.get("nome", "Girt")
    ms = []
    for z_mm in GIRT_Z_MM:
        if z_mm > eave * MM:                          # girt acima do beiral -> nao existe
            continue
        for y in (-goff, span_tot + goff):
            ms.append({"marca": "G1", "perfil": nome, "tipo": "Member",
                       "p1": (0.0, y * MM, z_mm), "p2": (comp * MM, y * MM, z_mm),
                       "secao": girt_sec})
    return ms


def frame_completo(geometria, secoes, n_terca=None, terca_sec=None,
                   girt_sec=None, col_d=None):
    """Modelo neutro fisico = primario (colunas + rafters) + terças (se n_terca +
    terca_sec) + girts de parede (se girt_sec). Tirantes/contraventamento/chapas e
    escopo das proximas iteracoes."""
    ms = frame_primario(geometria, secoes)
    if n_terca and terca_sec:
        geo = dict(geometria)                         # altura do rafter -> assento
        geo.setdefault("raf_d", (secoes.get("raf") or {}).get("d", 0.0))
        ms += tercas(geo, n_terca, terca_sec)
    if girt_sec:
        cd = col_d if col_d is not None else (secoes.get("col") or {}).get("d", 0.0)
        ms += girts(geometria, girt_sec, cd)
    return ms


def resumo(membros):
    """Contagem por tipo (p/ testes/relatorio)."""
    from collections import Counter
    return dict(Counter(m["tipo"] for m in membros))


def _selftest():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    sec = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
           "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}
    M = frame_primario(geo, sec)
    # 40/5=8 -> 9 porticos ; 1 vao -> 2 colunas/portico = 18 colunas ; 2 rafters/portico = 18
    r = resumo(M)
    assert r["Column"] == 18 and r["Beam"] == 18, r
    # coluna da base ao beiral, vertical (so Z varia)
    c = [m for m in M if m["tipo"] == "Column"][0]
    assert c["p1"][2] == 0.0 and abs(c["p2"][2] - 6000.0) < 1e-6
    assert c["p1"][0] == c["p2"][0] and c["p1"][1] == c["p2"][1]
    # rafter sobe do beiral (Z=6000) a cumeeira (Z=7000) e caminha em Y ate o meio
    v = [m for m in M if m["tipo"] == "Beam"][0]
    assert abs(v["p1"][2] - 6000.0) < 1e-6 and abs(v["p2"][2] - 7000.0) < 1e-6
    assert abs(v["p2"][1] - 10000.0) < 1e-6         # cumeeira no meio do vao 20 m
    # multi-vao: 2 vaos -> 3 colunas/portico + 4 rafters/portico
    M2 = frame_primario({"spans": [10.0, 12.0], "comprimento": 30.0, "eave": 6.0,
                         "ridge": 7.5, "bay": 6.0}, sec)
    r2 = resumo(M2)
    # 30/6=5 -> 6 porticos ; 3 colunas -> 18 ; 4 rafters -> 24
    assert r2["Column"] == 18 and r2["Beam"] == 24, r2
    # marcas V1 (1o vao) e V2 (2o vao) distintas
    marcas = {m["marca"] for m in M2 if m["tipo"] == "Beam"}
    assert marcas == {"V1", "V2"}, marcas
    print("modelo_neutro _selftest PASSED")


if __name__ == "__main__":
    _selftest()
