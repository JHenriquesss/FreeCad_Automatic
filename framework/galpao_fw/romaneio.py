# ============================================================================
# romaneio.py - LISTA DE MATERIAIS / ROMANEIO com MARCAS DE PECA (piece marks)
# Entregavel de fabricacao PRELIMINAR derivado do CALCULO (perfis adotados +
# geometria). Agrupa pecas identicas sob uma marca (C1, V1, ...) com quantidade,
# comprimento, peso unitario e total. E PRELIMINAR: o romaneio DEFINITIVO (com
# recortes, furacao e marcas por posicao exata) sai do MODELO 3D/takeoff. Serve
# de estimativa de compra/orcamento e de esqueleto das marcas. SI (m, kg).
# ============================================================================
"""Romaneio preliminar com marcas de peca (a partir do calculo)."""

from __future__ import annotations

import math

RHO_ACO = 7850.0                 # densidade do aco (kg/m3)


def massa_por_metro(area_m2):
    """Massa linear (kg/m) de um perfil de area de secao A (m2)."""
    return area_m2 * RHO_ACO


def _n_porticos(comprimento, bay):
    """Numero de porticos transversais = trechos(comprimento/bay) + 1."""
    return int(round(comprimento / bay)) + 1 if bay > 0 else 1


def romaneio_primario(geometria, secoes):
    """Monta o romaneio das pecas PRIMARIAS (colunas + vigas/rafters) do galpao.
    geometria: {span|spans, comprimento, eave, ridge, bay}
    secoes: {col: {'nome','A'}, raf: {'nome','A'}}  (perfil adotado do calculo)
    Retorna dict {itens:[...], peso_total_kg, n_porticos}. Cada item:
      {marca, descricao, perfil, comprimento_m, qtd, peso_unit_kg, peso_total_kg}."""
    spans = geometria.get("spans") or [geometria["span"]]
    nvaos = len(spans)
    comp, bay = geometria["comprimento"], geometria["bay"]
    eave, ridge = geometria["eave"], geometria["ridge"]
    np_ = _n_porticos(comp, bay)
    itens = []

    # COLUNAS: (nvaos+1) por portico, comprimento ~ pe-direito (eave). Marca C1.
    col = secoes["col"]
    n_col = (nvaos + 1) * np_
    mpm_c = massa_por_metro(col["A"])
    pu_c = mpm_c * eave
    itens.append({"marca": "C1", "descricao": "Coluna", "perfil": col["nome"],
                  "comprimento_m": round(eave, 3), "qtd": n_col,
                  "peso_unit_kg": round(pu_c, 1),
                  "peso_total_kg": round(pu_c * n_col, 1)})

    # VIGAS/RAFTERS: 2 meias-aguas por vao por portico (E e D da cumeeira). O
    # comprimento da meia-agua = hypot(span/2, ridge-eave). Uma marca por largura
    # de vao distinta (V1, V2, ...) - vaos iguais compartilham a marca.
    raf = secoes["raf"]
    mpm_r = massa_por_metro(raf["A"])
    larguras = {}
    for s in spans:
        larguras.setdefault(round(s, 3), 0)
        larguras[round(s, 3)] += 1
    for k, (s, _cnt) in enumerate(sorted(larguras.items()), start=1):
        L_meia = math.hypot(s / 2.0, ridge - eave)
        n_raf = 2 * larguras[s] * np_          # 2 meias-aguas x (nº vaos dessa larg) x porticos
        pu_r = mpm_r * L_meia
        itens.append({"marca": "V%d" % k, "descricao": "Viga/rafter (meia-agua)",
                      "perfil": raf["nome"], "comprimento_m": round(L_meia, 3),
                      "qtd": n_raf, "peso_unit_kg": round(pu_r, 1),
                      "peso_total_kg": round(pu_r * n_raf, 1)})

    peso_total = round(sum(i["peso_total_kg"] for i in itens), 1)
    return {"itens": itens, "peso_total_kg": peso_total, "n_porticos": np_,
            "nvaos": nvaos}


def relatorio_pt(r, titulo="ROMANEIO PRELIMINAR (pecas primarias)"):
    L = ["=" * 78, titulo + " - do calculo; DEFINITIVO sai do modelo 3D", "=" * 78,
         "%-5s %-22s %-10s %8s %5s %10s %11s" %
         ("MARCA", "DESCRICAO", "PERFIL", "COMP(m)", "QTD", "P.UNIT(kg)", "P.TOTAL(kg)"),
         "-" * 78]
    for it in r["itens"]:
        L.append("%-5s %-22s %-10s %8.3f %5d %10.1f %11.1f" %
                 (it["marca"], it["descricao"], it["perfil"], it["comprimento_m"],
                  it["qtd"], it["peso_unit_kg"], it["peso_total_kg"]))
    L += ["-" * 78,
          "PORTICOS: %d  |  VAOS: %d  |  PESO PRIMARIO TOTAL: %.1f kg (%.2f t)"
          % (r["n_porticos"], r["nvaos"], r["peso_total_kg"], r["peso_total_kg"] / 1000.0),
          "[PRELIMINAR: secundarios, ligacoes, chapas e recortes -> takeoff do 3D.]", ""]
    return "\n".join(L)


def _selftest():
    geo = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}
    sec = {"col": {"nome": "HEA200", "A": 0.005383},
           "raf": {"nome": "HEA180", "A": 0.004525}}
    r = romaneio_primario(geo, sec)
    # 40/5 = 8 trechos -> 9 porticos ; 1 vao -> 2 colunas/portico = 18 colunas
    assert r["n_porticos"] == 9
    col = [i for i in r["itens"] if i["marca"] == "C1"][0]
    assert col["qtd"] == 2 * 9 and abs(col["comprimento_m"] - 6.0) < 1e-9
    # peso coluna = A*rho*L: 0,005383*7850*6
    assert abs(col["peso_unit_kg"] - 0.005383 * 7850 * 6.0) < 0.1
    # rafters: 1 vao -> V1 ; meia-agua = hypot(10, 1) ; qtd = 2*1*9 = 18
    v1 = [i for i in r["itens"] if i["marca"] == "V1"][0]
    assert v1["qtd"] == 18 and abs(v1["comprimento_m"] - math.hypot(10.0, 1.0)) < 1e-2
    assert r["peso_total_kg"] > 0
    # multi-vao heterogeneo: larguras distintas -> marcas V1/V2 separadas
    r2 = romaneio_primario({"spans": [10.0, 30.0], "comprimento": 30.0, "eave": 6.0,
                            "ridge": 7.5, "bay": 6.0}, sec)
    marcas = {i["marca"] for i in r2["itens"]}
    assert "V1" in marcas and "V2" in marcas          # 2 larguras -> 2 marcas
    assert r2["n_porticos"] == 6                       # 30/6=5 -> 6
    # colunas: 3 por portico (2 vaos) x 6 = 18
    assert [i for i in r2["itens"] if i["marca"] == "C1"][0]["qtd"] == 3 * 6
    print("romaneio _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(romaneio_primario(
        {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0},
        {"col": {"nome": "HEA200", "A": 0.005383},
         "raf": {"nome": "HEA180", "A": 0.004525}})))
