# ============================================================================
# test_ifc_tanque.py - O IFC DO TANQUE-BASE TEM AS PECAS E AS MEDIDAS DO CALCULO.
# O envelope e' medido na geometria gerada pelo ifcopenshell, nao lido do spec.
# ============================================================================
"""Modelo IFC do tanque-base."""

import collections
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ifcopenshell = pytest.importorskip("ifcopenshell")
import ifcopenshell.geom  # noqa: E402
import ifcopenshell.util.element as ue  # noqa: E402
import ifcopenshell.util.shape as us  # noqa: E402

import ifc_tanque  # noqa: E402
import projeto_rev02 as P  # noqa: E402


@pytest.fixture(scope="module")
def modelo(tmp_path_factory):
    caminho = str(tmp_path_factory.mktemp("ifc") / "tanque.ifc")
    return ifc_tanque.emitir(caminho), ifcopenshell.open(caminho)


def _caixa(ifc, nomes):
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)
    mn, mx = [9e9] * 3, [-9e9] * 3
    for el in ifc.by_type("IfcElement"):
        if el.Name not in nomes:
            continue
        forma = ifcopenshell.geom.create_shape(st, el)
        v = us.get_vertices(forma.geometry)
        for i in range(3):
            mn[i], mx[i] = min(mn[i], v[:, i].min()), max(mx[i], v[:, i].max())
    return mn, mx


def test_pecas_do_modelo(modelo):
    _, ifc = modelo
    n = collections.Counter(e.Name for e in ifc.by_type("IfcElement"))
    assert n["M"] == 6 and n["APOIO"] == 6 and n["CT"] == 4 and n["CONE"] == 4
    assert n["SUCCAO"] == n["LAVAGEM"] == n["RESPIRO"] == n["BI"] == 1 and n["ENTRADA"] == 2
    assert n["L-INF"] == 4 and n["L-SUP"] == 4 and n["TE-INF"] == 2 and n["TE-SUP"] == 2
    assert n["TI"] == n["TS"] == P.geometria(P.SPEC_REV02)["n_travessas"] == 12
    assert n["CH-FUNDO"] == n["CH-TAMPA"] == 1 and n["CH-LATERAL"] == n["CH-TESTA"] == 2


def test_gaiola_ocupa_a_projecao_do_conteiner(modelo):
    _, ifc = modelo
    mn, mx = _caixa(ifc, {"M", "CT", "L-INF", "L-SUP", "TE-INF", "TE-SUP", "TI", "TS"})
    assert mn == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
    assert mx == pytest.approx([6.058, 2.438, 0.690], abs=1e-6)


def test_tanque_fica_dentro_da_gaiola_e_abaixo_do_plano_dos_cantos(modelo):
    _, ifc = modelo
    mn, mx = _caixa(ifc, {"CH-FUNDO", "CH-TAMPA", "CH-LATERAL", "CH-TESTA"})
    assert mn == pytest.approx([0.150, 0.150, 0.100], abs=1e-6)
    assert mx == pytest.approx([5.558, 2.288, 0.625], abs=1e-6)
    # travessas superiores: topo 15 mm abaixo dos 690 mm
    assert _caixa(ifc, {"TS"})[1][2] == pytest.approx(0.675, abs=1e-6)


def test_peso_do_modelo_perto_do_calculo(modelo):
    res, ifc = modelo
    pesos = [ue.get_psets(e)["Calc_Quantitativo"]["Peso_kg"]
             for e in ifc.by_type("IfcElement") if "Calc_Quantitativo" in ue.get_psets(e)]
    # cada peca grava o peso arredondado a 0,1 kg
    assert sum(pesos) == pytest.approx(res["peso_kg"], abs=3.0)
    # o calculo conta os tubos de eixo a eixo (sobrepoe os cantos): fica um pouco acima
    aco = P.massas(P.SPEC_REV02)["aco_kg"]
    assert 0.95 * aco < res["peso_kg"] <= aco


def test_chapa_de_topo_fica_no_plano_dos_cantos_e_o_resto_abaixo(modelo):
    _, ifc = modelo
    assert _caixa(ifc, {"CT"})[1][2] == pytest.approx(0.690, abs=1e-6)
    # fora a chapa de topo, nada da gaiola passa do topo (675 mm)
    assert _caixa(ifc, {"M", "L-SUP", "TE-SUP", "TS"})[1][2] <= 0.675 + 1e-6


def test_respiro_sai_acima_do_nivel_alto_alto(modelo):
    _, ifc = modelo
    g = P.geometria(P.SPEC_REV02)
    hh = (g["z_fundo"] + P.SPEC_REV02["chapas"]["fundo"]
          + P.capacidade(P.SPEC_REV02)["niveis"]["alarme_alto_alto"]["lamina_mm"]) / 1000
    assert _caixa(ifc, {"RESPIRO"})[0][2] > hh
    assert _caixa(ifc, {"RESPIRO"})[1][2] > 0.690 + ifc_tanque.ALTURA_CONTEINER_1CC


def test_tubos_da_tampa_passam_entre_as_travessas_superiores(modelo):
    _, ifc = modelo
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)

    def faixas_x(nome):
        saida = []
        for el in ifc.by_type("IfcElement"):
            if el.Name == nome:
                forma = ifcopenshell.geom.create_shape(st, el)
                v = us.get_vertices(forma.geometry)
                saida.append((v[:, 0].min(), v[:, 0].max()))
        return saida

    travessas = faixas_x("TS")
    tubos = faixas_x("RESPIRO") + faixas_x("ENTRADA")
    assert len(tubos) == 3
    for a, b in tubos:
        # folga minima de 50 mm para a travessa mais proxima
        assert all(b + 0.05 <= ta or a - 0.05 >= tb for ta, tb in travessas)


def test_poco_do_pescador_fica_entre_o_fundo_e_o_terreno(modelo):
    _, ifc = modelo
    mn, mx = _caixa(ifc, {"POCO"})
    assert mx[2] == pytest.approx(0.100, abs=1e-6)        # encosta por baixo no fundo
    assert mn[2] >= 0.010                                  # nao toca o terreno
    # o pescador desce dentro do poco, sem encostar no fundo dele
    pmn, pmx = _caixa(ifc, {"PESCADOR"})
    assert mn[0] < pmn[0] and pmx[0] < mx[0] and mn[1] < pmn[1] and pmx[1] < mx[1]
    assert pmn[2] > mn[2] + 0.006
    # e o poco nao bate em travessa inferior
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)
    for el in ifc.by_type("IfcElement"):
        if el.Name == "TI":
            forma = ifcopenshell.geom.create_shape(st, el)
            v = us.get_vertices(forma.geometry)
            assert v[:, 0].max() <= mn[0] or v[:, 0].min() >= mx[0]


def test_degraus_seguem_a_nbr_9050(modelo):
    _, ifc = modelo
    ac = P.acesso(P.SPEC_REV02)
    assert ac["ok"] and 160 <= ac["espelho_mm"] <= 180 and 280 <= ac["piso_mm"] <= 320
    degraus = [e for e in ifc.by_type("IfcElement") if e.Name == "DEGRAU"]
    assert len(degraus) == ac["espelhos"] - 1


def test_aberturas_recortam_as_chapas(modelo):
    _, ifc = modelo
    furos = collections.Counter(
        rel.RelatingBuildingElement.Name for rel in ifc.by_type("IfcRelVoidsElement"))
    # tampa: respiro + 2 entradas ; fundo: poco ; testa: succao, lavagem, boca e 2 de nivel
    assert furos["CH-TAMPA"] == 3 and furos["CH-FUNDO"] == 1 and furos["CH-TESTA"] == 5
    assert furos["OLHAL"] == 4


def test_olhais_e_calcos(modelo):
    _, ifc = modelo
    n = collections.Counter(e.Name for e in ifc.by_type("IfcElement"))
    assert n["OLHAL"] == 4 and n["CALCO"] == 6 and n["CORRIMAO"] == 8 and n["BANZO"] == 2
    mn, mx = _caixa(ifc, {"OLHAL"})
    # saem 70 mm do comprimento, nao da largura, e ficam abaixo do plano dos cantos
    assert mn[0] == pytest.approx(-0.070, abs=1e-6) and mx[0] == pytest.approx(6.128, abs=1e-6)
    assert mn[1] >= 0.0 and mx[1] <= 2.438 and mx[2] < 0.690
    assert _caixa(ifc, {"CALCO"})[1][2] == pytest.approx(0.0, abs=1e-6)


def test_lista_do_tanque_sem_aberturas(modelo, tmp_path):
    import pranchas_tanque
    res, _ = modelo
    lista = pranchas_tanque.lista_do_tanque(res["caminho"])
    pecas = {ln["peca"] for ln in lista["linhas"]}
    assert "OpeningElement" not in pecas and "BuildingElementProxy" not in pecas
    assert "Acessorio" in pecas
    chapas = {ln["marca"]: ln["perfil"] for ln in lista["linhas"] if ln["peca"] == "Chapa"}
    assert chapas["CH-FUNDO"] == "CH 6,35 - 5408 x 2138"
    assert chapas["CH-LATERAL"] == "CH 4,75 - 5408 x 514"
