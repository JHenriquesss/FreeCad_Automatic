# ============================================================================
# test_ambientes_dxf.py - AMBIENTES LIDOS DA PLANTA DXF E PREVISAO DE CARGA
# (plano de 2026-10-08, Fase 5, primeiro passo). A planta e' escrita aqui com
# o ezdxf (polilinhas fechadas + textos na camada AMBIENTES); o que se cobra e'
# que area e perimetro saiam do DESENHO na unidade certa, que cada texto case
# com a sua polilinha, que a previsao seja a do motor para os mesmos numeros
# digitados a mao, e que planta mal marcada reprove com o motivo nomeado.
# ============================================================================
"""Ambientes de um DXF -> previsao de carga pelo motor."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ezdxf = pytest.importorskip("ezdxf")

import ambientes_dxf as AD
import arquitetura_residencial as AR


def _planta(tmp_path, comodos, insunits=4, extras=None, nome="planta.dxf"):
    """comodos: [(x0, y0, largura, altura, texto)] nas unidades do desenho."""
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    for x0, y0, w, h, texto in comodos:
        msp.add_lwpolyline([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
                           close=True, dxfattribs={"layer": "AMBIENTES"})
        if texto is not None:
            msp.add_text(texto, dxfattribs={"layer": "AMBIENTES",
                                            "insert": (x0 + w / 2.0, y0 + h / 2.0)})
    if extras:
        extras(msp)
    caminho = str(tmp_path / nome)
    doc.saveas(caminho)
    return caminho


_CASA_MM = [(0, 0, 4000, 3000, "quarto"),                       # 12 m2, perimetro 14 m
            (4000, 0, 3000, 3000, "Cozinha"),                   # 9 m2, 12 m
            (0, 3000, 2000, 1500, "Banho social; banheiro"),    # 3 m2, 7 m
            (2000, 3000, 5000, 1500, "Área de Serviço")]   # 7,5 m2, 13 m


def test_le_area_e_perimetro_do_desenho_em_metros(tmp_path):
    lido = AD.ler_ambientes(_planta(tmp_path, _CASA_MM))
    assert lido["erros"] == [] and lido["metros_por_unidade"] == 0.001
    por_nome = {a["nome"]: a for a in lido["ambientes"]}
    assert set(por_nome) == {"quarto 1", "cozinha 1", "Banho social", "area_servico 1"}
    assert (por_nome["quarto 1"]["area_m2"], por_nome["quarto 1"]["perimetro_m"]) == (12.0, 14.0)
    assert (por_nome["cozinha 1"]["tipo"], por_nome["cozinha 1"]["area_m2"]) == ("cozinha", 9.0)
    banho = por_nome["Banho social"]
    assert (banho["tipo"], banho["area_m2"], banho["perimetro_m"]) == ("banheiro", 3.0, 7.0)
    # tipo com acento e preposicao vira o tipo do motor
    assert por_nome["area_servico 1"]["tipo"] == "area_servico"
    assert por_nome["area_servico 1"]["tipo"] in AR.TIPOS_CONHECIDOS


@pytest.mark.parametrize("insunits, fator", [(4, 1000.0), (5, 100.0), (6, 1.0)])
def test_a_unidade_do_cabecalho_decide_a_escala(tmp_path, insunits, fator):
    caminho = _planta(tmp_path, [(0, 0, 4 * fator, 3 * fator, "quarto")], insunits=insunits)
    amb = AD.ler_ambientes(caminho)["ambientes"][0]
    assert (amb["area_m2"], amb["perimetro_m"]) == (12.0, 14.0)


def test_desenho_sem_unidade_declarada_e_recusado_ate_ser_informada(tmp_path):
    caminho = _planta(tmp_path, [(0, 0, 4000, 3000, "quarto")], insunits=0)
    with pytest.raises(ValueError, match="unidade do desenho nao declarada"):
        AD.ler_ambientes(caminho)
    amb = AD.ler_ambientes(caminho, unidade="mm")["ambientes"][0]
    assert (amb["area_m2"], amb["perimetro_m"]) == (12.0, 14.0)
    # a mesma planta lida como metros da um numero absurdo: por isso nao se adivinha
    assert AD.ler_ambientes(caminho, unidade="m")["ambientes"][0]["area_m2"] == 12.0e6


def test_previsao_e_a_do_motor_para_os_mesmos_ambientes(tmp_path):
    res = AD.previsao_de_cargas(_planta(tmp_path, _CASA_MM))
    a_mao = AR.rodar({"ambientes": [
        {"nome": "quarto 1", "tipo": "quarto", "area_m2": 12.0, "perimetro_m": 14.0},
        {"nome": "cozinha 1", "tipo": "cozinha", "area_m2": 9.0, "perimetro_m": 12.0},
        {"nome": "Banho social", "tipo": "banheiro", "area_m2": 3.0, "perimetro_m": 7.0},
        {"nome": "area_servico 1", "tipo": "area_servico", "area_m2": 7.5, "perimetro_m": 13.0}]})
    assert res["ATENDE"] is a_mao["ATENDE"] is True
    assert res["totais"] == a_mao["totais"]
    assert res["totais"]["n_ambientes"] == 4 and res["totais"]["area_util_m2"] == 31.5
    assert res["leitura_dxf"]["erros"] == []
    def _linha(r, nome):
        return [a for a in r["ambientes"] if a["nome"] == nome][0]
    for nome in ("quarto 1", "cozinha 1", "Banho social", "area_servico 1"):
        assert _linha(res, nome) == _linha(a_mao, nome)


def test_planta_mal_marcada_reprova_com_o_motivo(tmp_path):
    def _extras(msp):
        msp.add_text("varanda", dxfattribs={"layer": "AMBIENTES", "insert": (50000, 50000)})
        msp.add_lwpolyline([(20000, 0), (23000, 0), (23000, 3000)],
                           dxfattribs={"layer": "AMBIENTES"})              # aberta
        arco = msp.add_lwpolyline([(30000, 0), (33000, 0), (33000, 3000), (30000, 3000)],
                                  close=True, dxfattribs={"layer": "AMBIENTES"})
        arco.set_points([(30000, 0, 0, 0, 0.5), (33000, 0), (33000, 3000), (30000, 3000)],
                        format="xyseb")
        msp.add_text("sala", dxfattribs={"layer": "AMBIENTES", "insert": (11000, 1000)})

    comodos = [(0, 0, 4000, 3000, "quarto"),
               (5000, 0, 4000, 3000, None),                     # sem texto
               (10000, 0, 4000, 3000, "cozinha")]               # ganha um segundo texto
    res = AD.previsao_de_cargas(_planta(tmp_path, comodos, extras=_extras))
    codigos = sorted(e["code"] for e in res["leitura_dxf"]["erros"])
    assert codigos == ["ambiente_com_varios_textos", "ambiente_sem_texto", "polilinha_aberta",
                       "polilinha_com_arco", "texto_fora_de_ambiente"]
    # so o ambiente bem marcado entra na previsao, e o veredito cai
    assert [a["nome"] for a in res["ambientes"]] == ["quarto 1"]
    assert res["ATENDE"] is False


def test_outra_camada_nao_entra(tmp_path):
    def _extras(msp):
        msp.add_lwpolyline([(9000, 0), (12000, 0), (12000, 3000), (9000, 3000)], close=True,
                           dxfattribs={"layer": "PAREDES"})
        msp.add_text("sala", dxfattribs={"layer": "PAREDES", "insert": (10000, 1000)})

    lido = AD.ler_ambientes(_planta(tmp_path, [(0, 0, 4000, 3000, "quarto")], extras=_extras))
    assert [a["nome"] for a in lido["ambientes"]] == ["quarto 1"] and lido["erros"] == []
    outra = AD.ler_ambientes(_planta(tmp_path, [(0, 0, 4000, 3000, "quarto")], extras=_extras,
                                     nome="p2.dxf"), camada="PAREDES")
    assert [(a["tipo"], a["area_m2"]) for a in outra["ambientes"]] == [("sala", 9.0)]


@pytest.mark.parametrize("texto, esperado", [
    ("Cozinha", "cozinha"), ("Área de Serviço", "area_servico"),
    ("Sala de Estar", "sala_estar"), ("copa e cozinha", "copa_cozinha"),
    ("  SUÍTE ", "suite"), ("sala-jantar", "sala_jantar")])
def test_normaliza_tipo(texto, esperado):
    assert AD.normaliza_tipo(texto) == esperado


@pytest.mark.parametrize("insunits, fator", [(4, 1000.0), (5, 100.0), (6, 1.0)])
def test_geometria_e_quadro_saem_em_metros_nos_dois_eixos(tmp_path, insunits, fator):
    def _extras(msp):
        msp.add_circle((1.5 * fator, 2.5 * fator), 0.1 * fator, dxfattribs={"layer": "QUADRO"})

    lido = AD.ler_ambientes(_planta(tmp_path, [(1 * fator, 2 * fator, 4 * fator, 3 * fator,
                                                "quarto")], insunits=insunits, extras=_extras))
    assert lido["erros"] == []
    assert lido["geometria"] == {"quarto 1": [[1.0, 2.0], [5.0, 2.0], [5.0, 5.0], [1.0, 5.0]]}
    assert lido["quadro_m"] == [1.5, 2.5]


def test_quadro_em_outra_camada_e_tipos_de_entidade(tmp_path):
    def _extras(msp):
        msp.add_text("QD", dxfattribs={"layer": "QD-GERAL", "insert": (500, 700)})
        msp.add_point((9000, 9000), dxfattribs={"layer": "OUTRA"})

    caminho = _planta(tmp_path, [(0, 0, 4000, 3000, "quarto")], extras=_extras)
    assert AD.ler_ambientes(caminho)["quadro_m"] is None
    assert AD.ler_ambientes(caminho, camada_quadro="QD-GERAL")["quadro_m"] == [0.5, 0.7]
    assert AD.ler_ambientes(caminho, camada_quadro="OUTRA")["quadro_m"] == [9.0, 9.0]
