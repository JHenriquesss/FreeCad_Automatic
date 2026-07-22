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
