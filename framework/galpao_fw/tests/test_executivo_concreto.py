"""Executivo do galpao de concreto - executivo_concreto.py.

Quadro de aco (lista de dobramento) + resumo de consumo + memorial. Reusa a
ancoragem/peso da fundacao e os relatorios dos modulos de calculo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import galpao_concreto as gc
import executivo_concreto as ex


def _r(vao=10.0):
    return gc.rodar({"vao": vao, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                     "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30,
                     "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0})


def test_quadro_cobre_pilar_viga_e_sapata():
    q = ex.quadro_de_aco(_r())
    elementos = {x["elemento"] for x in q}
    assert {"Pilar", "Viga cob.", "Sapata"} <= elementos
    # toda posicao tem quantidade e peso positivos
    assert all(x["n"] > 0 and x["peso_kg"] > 0 and x["comprimento_m"] > 0 for x in q)


def test_quantidades_escalam_com_n_porticos():
    q = ex.quadro_de_aco(_r())
    long_pilar = next(x for x in q if x["pos"].startswith("N1"))
    # 7 porticos x 2 pilares = 14 pilares ; n_barras por pilar = n_total/14 inteiro
    assert long_pilar["n"] % 14 == 0


def test_pilar_longitudinal_inclui_ancoragem():
    # o comprimento da barra do pilar > pe-direito (H) por causa da ancoragem/arranque
    r = _r()
    q = ex.quadro_de_aco(r)
    n1 = next(x for x in q if x["pos"].startswith("N1"))
    assert n1["comprimento_m"] > r["spec"]["H"]


def test_resumo_taxas_em_ordem_de_grandeza():
    r = _r()
    res = ex.resumo_aco(r)
    assert res["peso_total_kg"] > 0
    assert res["volume_concreto_m3"] > 0
    # consumo de aco de galpao de concreto: ordem de grandeza plausivel
    assert 20.0 < res["consumo_kg_m3"] < 300.0
    assert res["taxa_kg_m2"] > 0


def test_peso_bate_com_formula():
    # peso = n*L*0,00617*phi^2 (kg) - a formula de quadro_dobramento
    q = ex.quadro_de_aco(_r())
    x = q[0]
    esperado = x["n"] * x["comprimento_m"] * 0.00617 * x["phi_mm"] ** 2
    # tolerancia relativa: o peso interno usa o comprimento cheio; o registro
    # arredonda comprimento_m a 2 casas (x n barras -> alguns kg de diferenca).
    assert abs(x["peso_kg"] - esperado) / esperado < 0.005


def test_memorial_compoe_todas_as_disciplinas():
    txt = ex.memorial(_r())
    for marca in ("MEMORIAL DE CALCULO", "VENTO", "VIGA DE COBERTURA", "PILAR",
                  "QUADRO DE ACO"):
        assert marca in txt, marca


def test_g47_quadro_mostra_ramos_e_st_do_fuste():
    # G47: o s_t adotado tem de aparecer no quadro de aco do executivo,
    # nao so no dict do dimensionamento; grampos entram no comprimento/peso.
    import pilar_concreto as pc
    r = pc.dimensiona_pilar({"b": 0.40, "h": 0.40, "Nk": 900.0, "le": 3.0,
                             "fck": 30e3, "fyk": 500e3, "Vd": 700.0})
    assert r["n_ramos_estribo"] == 4
    base = _r()
    base["pilar"] = dict(base["pilar"], **{k: r[k] for k in
        ("phi_estribo_mm", "s_estribo", "s_estribo_max", "n_ramos_estribo",
         "s_t", "hx", "hy")})
    q = ex.quadro_de_aco(base)
    n2 = next(x for x in q if x["pos"].startswith("N2"))
    assert "4R" in n2["pos"] and "s_t=" in n2["pos"]
    assert n2["n_ramos"] == 4 and n2["s_t_m"] > 0
    # com 1 grampo o comprimento por espacamento supera o fechado simples
    assert n2["comprimento_m"] > ex._estribo_comprimento(0.40, 0.40, 0.03, 10.0)
    txt = ex.relatorio_quadro_pt(base)
    assert "s_t=" in txt


def test_selftest_roda():
    ex._selftest()
