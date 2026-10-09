# ============================================================================
# test_planta_eletrica_dxf.py - O ELETRICO SOBRE A PLANTA RECEBIDA (plano de
# 2026-10-08, Fase 5, quarto passo). A planta e' escrita aqui com o ezdxf e o
# arquivo de saida e' RELIDO: cobra-se que o original nao mude, que cada ponto
# da divisao vire um simbolo no ambiente certo (luz no centro, tomada encostada
# na parede pelo lado de dentro, nos dois eixos), que o rotulo ao lado seja o
# do circuito que alimenta o ponto, que a tabela traga uma linha por circuito e
# que ambiente sem posicao defensavel reprove em vez de ganhar ponto inventado.
# ============================================================================
"""Planta DXF + divisao -> DXF com as camadas do eletrico."""

import copy
import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ezdxf = pytest.importorskip("ezdxf")

import ambientes_dxf as AD
import circuitos_planta as CP
import planta_eletrica_dxf as PE

# planta fora da origem e com lados diferentes, para os dois eixos contarem
_X0, _Y0 = 10.0, 20.0
_COMODOS = [(0.0, 0.0, 4.0, 3.0, "quarto; quarto"),
            (4.0, 0.0, 3.0, 3.0, "cozinha; cozinha"),
            (0.0, 3.0, 2.0, 1.5, "banho; banheiro"),
            (2.0, 3.0, 5.0, 1.5, "servico; area de servico")]
_CRITERIOS = {"tensao_v": 127.0, "n_fases": 2,
              "limite_va": {"iluminacao": 1000.0, "tomadas": 1500.0,
                            "tomadas_exclusivas": 2000.0},
              "equipamentos": [{"nome": "chuveiro", "ambiente": "banho", "potencia_va": 5500.0,
                                "tensao_v": 220.0, "n_fases": 2}],
              "instalacao": {"isolacao": "PVC", "metodo_referencia": "B1",
                             "temperatura_ambiente_c": 30.0, "circuitos_agrupados": 3,
                             "queda_tensao_max_pct": 4.0, "exposicao_dps": "quadro",
                             "fator_potencia": {"iluminacao": 1.0, "tomadas": 0.8,
                                                "tomadas_exclusivas": 0.8,
                                                "equipamento": 1.0}},
              "tracado": {"fator": 1.2, "acrescimo_vertical_m": 2.5}}


def _planta(tmp_path, fator=1000.0, insunits=4, comodos=_COMODOS, quadro=(2.0, 3.0),
            poligonos=(), nome="planta.dxf"):
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    f = lambda x, y: ((_X0 + x) * fator, (_Y0 + y) * fator)
    for x0, y0, w, h, texto in comodos:
        msp.add_lwpolyline([f(x0, y0), f(x0 + w, y0), f(x0 + w, y0 + h), f(x0, y0 + h)],
                           close=True, dxfattribs={"layer": "AMBIENTES"})
        msp.add_text(texto, dxfattribs={"layer": "AMBIENTES",
                                        "insert": f(x0 + w / 2.0, y0 + h / 2.0)})
    for pts, texto, onde in poligonos:
        msp.add_lwpolyline([f(*p) for p in pts], close=True, dxfattribs={"layer": "AMBIENTES"})
        msp.add_text(texto, dxfattribs={"layer": "AMBIENTES", "insert": f(*onde)})
    msp.add_line(f(0, 0), f(7, 0), dxfattribs={"layer": "PAREDES"})
    if quadro is not None:
        msp.add_point(f(*quadro), dxfattribs={"layer": "QUADRO"})
    caminho = str(tmp_path / nome)
    doc.saveas(caminho)
    return caminho


def _tudo(tmp_path, dimensionar=True, **planta):
    origem = _planta(tmp_path, **planta)
    prev = AD.previsao_de_cargas(origem)
    div = CP.dividir(prev, _CRITERIOS)
    dim = CP.dimensionar_da_planta(div, prev["leitura_dxf"], _CRITERIOS) if dimensionar else None
    destino = str(tmp_path / "eletrica.dxf")
    res = PE.desenhar(origem, destino, prev["leitura_dxf"], div, dim)
    return origem, prev, div, dim, res


def _dist_ao_contorno(ponto, pts):
    x, y = ponto
    melhor = None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy)))
        d = ((x - x0 - t * dx) ** 2 + (y - y0 - t * dy) ** 2) ** 0.5
        melhor = d if melhor is None else min(melhor, d)
    return melhor


def _insercoes(doc, camada, esc):
    return [(e.dxf.name, (e.dxf.insert.x * esc, e.dxf.insert.y * esc))
            for e in doc.modelspace().query('INSERT[layer=="%s"]' % camada)]


def test_o_arquivo_recebido_nao_muda_e_o_original_segue_no_destino(tmp_path):
    origem = _planta(tmp_path)
    antes = hashlib.sha256(open(origem, "rb").read()).hexdigest()
    prev = AD.previsao_de_cargas(origem)
    div = CP.dividir(prev, _CRITERIOS)
    res = PE.desenhar(origem, str(tmp_path / "e.dxf"), prev["leitura_dxf"], div)
    assert hashlib.sha256(open(origem, "rb").read()).hexdigest() == antes
    assert res["ATENDE"] is True and res["erros"] == []
    saida = ezdxf.readfile(res["arquivo"]).modelspace()
    original = ezdxf.readfile(origem).modelspace()
    for camada in ("AMBIENTES", "PAREDES", "QUADRO"):
        assert len(saida.query('*[layer=="%s"]' % camada)) \
            == len(original.query('*[layer=="%s"]' % camada)) > 0
    assert len(original.query("INSERT")) == 0 and len(saida.query("INSERT")) > 0


def test_cada_ponto_vira_um_simbolo_no_ambiente_certo(tmp_path):
    _origem, prev, div, _dim, res = _tudo(tmp_path)
    assert res["ATENDE"] is True and res["pontos_sem_posicao"] == []
    assert res["pontos_desenhados"] == len(div["pontos"]) == 4 + 12 + 1
    doc = ezdxf.readfile(res["arquivo"])
    geo = {n: [tuple(v) for v in pts] for n, pts in prev["leitura_dxf"]["geometria"].items()}
    luzes = _insercoes(doc, "ELE-ILUMINACAO", 0.001)
    tomadas = _insercoes(doc, "ELE-TOMADA", 0.001)
    equipamentos = _insercoes(doc, "ELE-EQUIPAMENTO", 0.001)
    assert {n for n, _p in luzes} == {"ELE_LUZ"} and {n for n, _p in tomadas} == {"ELE_TOMADA"}
    assert (len(luzes), len(tomadas), len(equipamentos)) == (4, 12, 1)
    # luz no centro de cada ambiente, nos dois eixos
    centros = sorted((round(x, 3), round(y, 3)) for _n, (x, y) in luzes)
    assert centros == sorted([(12.0, 21.5), (15.5, 21.5), (11.0, 23.75), (14.5, 23.75)])
    # tomada: dentro de UM ambiente, encostada na parede dele; a conta por ambiente fecha
    por_ambiente = {n: 0 for n in geo}
    for _n, pos in tomadas:
        donos = [n for n, pts in geo.items() if PE._dentro(pos, pts)]
        assert len(donos) == 1, pos
        assert _dist_ao_contorno(pos, geo[donos[0]]) == pytest.approx(PE.AFASTADA_M, abs=1e-6)
        por_ambiente[donos[0]] += 1
    esperado = {a["nome"]: a["n_tomadas_min"] for a in prev["ambientes"]}
    assert por_ambiente == esperado == {"quarto": 3, "cozinha": 4, "banho": 1, "servico": 4}
    # equipamento ao lado da luz do banho; quadro onde o cliente marcou
    assert PE._dentro(equipamentos[0][1], geo["banho"])
    assert _insercoes(doc, "ELE-QUADRO", 0.001) == [("ELE_QUADRO", (12.0, 23.0))]


def test_rotulo_ao_lado_do_ponto_e_o_circuito_que_o_alimenta(tmp_path):
    _origem, prev, div, _dim, res = _tudo(tmp_path)
    doc = ezdxf.readfile(res["arquivo"])
    posicoes, _erros = PE.posicoes_sugeridas(div, prev["leitura_dxf"]["geometria"])
    circuito_de = {pid: c["id"] for c in div["circuitos"] for pid in c["point_ids"]}
    h = PE.ALTURA_TEXTO_M
    rotulos = {(round(t.dxf.insert.x * 0.001 - 1.3 * h, 3), round(t.dxf.insert.y * 0.001 - 0.6 * h, 3)):
               t.dxf.text for t in doc.modelspace().query('TEXT[layer=="ELE-TEXTO"]')}
    assert len(rotulos) == len(div["pontos"])
    for p in div["pontos"]:
        x, y = posicoes[p["id"]]
        texto = rotulos[(round(x, 3), round(y, 3))]
        esperado = circuito_de[p["id"]] + (" chuveiro" if p["kind"] == "tue" else "")
        assert texto == esperado, p["id"]
    # as tomadas da cozinha e do servico nao levam o rotulo das tomadas gerais
    assert sorted(set(rotulos.values())) == ["EQ1 chuveiro", "IL1", "TE1", "TE2", "TG1"]


def test_tabela_tem_uma_linha_por_circuito_com_e_sem_dimensionamento(tmp_path):
    _o, _p, div, dim, res = _tudo(tmp_path)
    textos = [t.dxf.text for t in ezdxf.readfile(res["arquivo"]).modelspace().query(
        'TEXT[layer=="ELE-TABELA"]')]
    assert "QUADRO DE CARGAS" in textos and PE.NOTA in textos and "LEGENDA" in textos
    assert [t for t in textos if t in ("mm2", "DJ (A)", "DR", "L (m)")] \
        == ["L (m)", "mm2", "DJ (A)", "DR"]
    for c in div["circuitos"]:
        assert textos.count(c["id"]) == 1
    eq = [r for r in dim["resumo"] if r["id"] == "EQ1"][0]
    i = textos.index("EQ1")
    assert textos[i:i + 11] == ["EQ1", "equipamento", "1", "5500", "220", "25.00", "AB",
                                "%.1f" % eq["comprimento_m"], "%g" % eq["secao_mm2"],
                                "%d" % eq["disjuntor_a"], "sim"]
    # chuveiro 2750 + 2750; TE1 em A, TE2 em B (4650 cada); TG1 900 em A; IL1 460 em B
    assert "CARGA INSTALADA 10660 VA; POR FASE A=5550, B=5110" in textos
    for _bloco, _camada, descricao in PE.LEGENDA:
        assert descricao in textos
    # sem dimensionamento a tabela nao promete condutor nem protecao
    pasta = tmp_path / "sem"
    pasta.mkdir()
    _o, _p, _d, _dim, sem = _tudo(pasta, dimensionar=False)
    textos = [t.dxf.text for t in ezdxf.readfile(sem["arquivo"]).modelspace().query(
        'TEXT[layer=="ELE-TABELA"]')]
    assert "mm2" not in textos and "DJ (A)" not in textos and "EQ1" in textos
    assert sem["ATENDE"] is True


def test_circuito_recusado_pelo_calculo_fica_escrito_e_o_veredito_cai(tmp_path):
    origem = _planta(tmp_path)
    prev = AD.previsao_de_cargas(origem)
    div = CP.dividir(prev, _CRITERIOS)
    criterios = copy.deepcopy(_CRITERIOS)
    criterios["comprimentos_m"] = {"TE1": 5000.0}
    dim = CP.dimensionar_da_planta(div, prev["leitura_dxf"], criterios)
    assert dim["ATENDE"] is False
    res = PE.desenhar(origem, str(tmp_path / "e.dxf"), prev["leitura_dxf"], div, dim)
    assert res["ATENDE"] is False
    textos = [t.dxf.text for t in ezdxf.readfile(res["arquivo"]).modelspace().query(
        'TEXT[layer=="ELE-TABELA"]')]
    i = textos.index("TE1")
    assert textos[i + 7] == "NAO DIMENSIONADO"
    assert textos[textos.index("TE2") + 7] != "NAO DIMENSIONADO"


@pytest.mark.parametrize("insunits, fator", [(4, 1000.0), (5, 100.0), (6, 1.0)])
def test_a_unidade_do_desenho_recebido_e_respeitada(tmp_path, insunits, fator):
    _o, _p, _div, _dim, res = _tudo(tmp_path, fator=fator, insunits=insunits)
    doc = ezdxf.readfile(res["arquivo"])
    luzes = sorted((round(e.dxf.insert.x / fator, 3), round(e.dxf.insert.y / fator, 3))
                   for e in doc.modelspace().query('INSERT[layer=="ELE-ILUMINACAO"]'))
    assert luzes == sorted([(12.0, 21.5), (15.5, 21.5), (11.0, 23.75), (14.5, 23.75)])
    alturas = {round(t.dxf.height / fator, 6)
               for t in doc.modelspace().query('TEXT[layer=="ELE-TEXTO"]')}
    assert alturas == {round(0.8 * PE.ALTURA_TEXTO_M, 6)}
    # o simbolo tem o tamanho do texto, tambem na unidade do desenho
    raio = [e.dxf.radius for e in doc.blocks["ELE_LUZ"] if e.dxftype() == "CIRCLE"]
    assert raio == [pytest.approx(PE.ALTURA_TEXTO_M * fator)]


def test_ambiente_em_u_nao_ganha_ponto_inventado(tmp_path):
    # o centro de area do U cai no vao, fora do ambiente
    u = [(8, 0), (14, 0), (14, 4), (13, 4), (13, 1), (9, 1), (9, 4), (8, 4)]
    _o, prev, div, _dim, res = _tudo(tmp_path, poligonos=[(u, "varanda; varanda", (11, 0.5))])
    assert prev["ATENDE"] is True and "varanda" in prev["leitura_dxf"]["geometria"]
    assert [e["code"] for e in res["erros"]] == ["centro_fora_do_ambiente"]
    assert res["erros"][0]["ambiente"] == "varanda" and res["ATENDE"] is False
    da_varanda = [p["id"] for p in div["pontos"] if p["room"] == "varanda"]
    assert res["pontos_sem_posicao"] == da_varanda and len(da_varanda) == 2
    assert res["pontos_desenhados"] == len(div["pontos"]) - 2
    # os outros ambientes saem desenhados
    doc = ezdxf.readfile(res["arquivo"])
    assert len(doc.modelspace().query('INSERT[layer=="ELE-ILUMINACAO"]')) == 4


def test_sem_divisao_nao_ha_desenho_e_sem_quadro_marcado_nao_ha_simbolo_de_quadro(tmp_path):
    origem = _planta(tmp_path, quadro=None)
    prev = AD.previsao_de_cargas(origem)
    sem_criterio = CP.dividir(prev, {"tensao_v": 127.0})
    destino = str(tmp_path / "e.dxf")
    res = PE.desenhar(origem, destino, prev["leitura_dxf"], sem_criterio)
    assert res["arquivo"] is None and res["ATENDE"] is False and not os.path.exists(destino)
    div = CP.dividir(prev, _CRITERIOS)
    ok = PE.desenhar(origem, destino, prev["leitura_dxf"], div)
    doc = ezdxf.readfile(ok["arquivo"])
    assert len(doc.modelspace().query('INSERT[layer=="ELE-QUADRO"]')) == 0
    # a legenda fica na camada da tabela: contar pontos por camada nao a conta
    assert len(doc.modelspace().query('INSERT[layer=="ELE-TABELA"]')) == len(PE.LEGENDA)
    assert [t.dxf.text for t in doc.modelspace().query('TEXT[layer=="ELE-QUADRO"]')] == []
    assert ok["ATENDE"] is True


def test_tomada_nao_cai_no_canto_nem_fora(tmp_path):
    # sala 7 x 4 com 5 tomadas: a terceira cairia exatamente no canto (7; 4)
    sala = [(0.0, 0.0), (7.0, 0.0), (7.0, 4.0), (0.0, 4.0)]
    pontos = PE._no_perimetro(sala, 5)
    a = PE.AFASTADA_M
    assert [(round(x, 4), round(y, 4)) for x, y in pontos] == [
        (2.2, round(a, 4)), (6.6, round(a, 4)), (round(7.0 - a, 4), round(4.0 - a, 4)),
        (2.6, round(4.0 - a, 4)), (round(a, 4), 2.2)]
    for p in pontos:
        assert PE._dentro(p, sala)
