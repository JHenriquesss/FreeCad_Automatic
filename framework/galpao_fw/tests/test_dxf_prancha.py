# ============================================================================
# test_dxf_prancha.py - A PRANCHA DXF E' DERIVADA DO DESENHO DO MODELO E SAI
# EM ESCALA (plano de 2026-10-08, Fase 4). O SVG de entrada e' escrito aqui a
# mao, no formato que o ifcopenshell.draw produz (grupo raiz com ifc:matrix3,
# um grupo por elemento IFC, cota como <line> de classe DIMENSION): o teste
# nao depende de Blender nem de Bonsai.
# O que se cobra e' o que o engenheiro ve ao abrir o arquivo: geometria em
# tamanho real, cota que MEDE a geometria (nao texto copiado), viewport na
# escala escolhida, carimbo preenchido, camada por disciplina.
# ============================================================================
"""Prancha DXF (ezdxf) a partir do SVG de desenho do modelo IFC."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ezdxf = pytest.importorskip("ezdxf")

import dxf_prancha as DP

# 1:100 -> 10 mm de papel por metro; o (0, 0) do modelo cai em (30, 80) do papel
_SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:ifc="http://www.ifcopenshell.org/ns"
     width="%(larg)smm" height="%(alt)smm" viewBox="0 0 %(larg)s %(alt)s">
 <g ifc:name="Elevation T" class="section target-view-PLANVIEW scale-100"
    ifc:matrix3="[[10.0,0.0,30.0],[0.0,10.0,80.0],[0.0,0.0,1.0]]">
  <g id="product-1" class="IfcColumn material-AcoMR250 cut" ifc:name="C1" ifc:guid="g1">
   <path d="M30,80 L32,80 L32,78 L30,78 Z"/>
  </g>
  <g id="product-2" class="IfcBeam material-AcoMR250 projection" ifc:name="V1" ifc:guid="g2">
   <path d="M30,80 L130,80"/>
   <path d="M30,30 L130,30"/>
  </g>
  <g id="product-3" class="IfcFooting material-ConcretoC25 projection" ifc:name="BLO1" ifc:guid="g3">
   <path d="M20,90 L40,90"/>
  </g>
  <g id="product-4" class="IfcRailing material-null projection" ifc:name="GC1" ifc:guid="g4">
   <path d="M60,60 L70,60"/>
  </g>
  %(extra)s
 </g>
 <line class="GlobalId-x IfcAnnotation PredefinedType-DIMENSION" x1="30" y1="95" x2="130" y2="95"/>
 <line class="GlobalId-y IfcAnnotation PredefinedType-DIMENSION" x1="15" y1="80" x2="15" y2="30"/>
 %(eixos)s
</svg>
"""

_EIXO_1 = """<line class="GlobalId-e IfcAnnotation PredefinedType-GRID" x1="30" y1="100" x2="30" y2="10"/>
 <text class="GRID" x="30" y="100">1</text><text class="GRID" x="30" y="10">1</text>"""


def _svg(tmp_path, nome="PLANTA", larg=160, alt=110, extra="", eixos=""):
    p = tmp_path / (nome + ".svg")
    p.write_text(_SVG % {"larg": larg, "alt": alt, "extra": extra, "eixos": eixos},
                 encoding="utf-8")
    return str(p)


def _plano(pontos):
    """Lista de pontos -> lista plana de numeros (pytest.approx nao aninha)."""
    return [v for p in pontos for v in p]


def _dxf(tmp_path, desenhos, **carimbo):
    destino = str(tmp_path / "saida.dxf")
    resumo = DP.gerar_dxf(desenhos, destino, carimbo)
    return resumo, ezdxf.readfile(destino)


def test_le_o_desenho_em_milimetros_reais_com_y_para_cima(tmp_path):
    des = DP.ler_desenho(_svg(tmp_path))
    assert des["nome"] == "PLANTA" and des["escala_origem"] == 100
    # papel 160 x 110 mm a 1:100 = 16 x 11 m; origem do modelo em (30, 80) do papel
    assert des["quadro"] == pytest.approx((-3000.0, -3000.0, 13000.0, 8000.0))
    por_marca = {e["marca"]: e for e in des["elementos"]}
    v1 = por_marca["V1"]["polilinhas"]
    assert len(v1) == 2
    assert _plano(v1[0]) == pytest.approx([0.0, 0.0, 10000.0, 0.0])
    assert _plano(v1[1]) == pytest.approx([0.0, 5000.0, 10000.0, 5000.0])   # y do SVG desce
    col = por_marca["C1"]
    assert col["corte"] and col["material"] == "AcoMR250" and col["classe"] == "IfcColumn"
    assert col["polilinhas"][0][0] == pytest.approx(col["polilinhas"][0][-1])  # Z fecha
    assert por_marca["GC1"]["material"] is None
    assert len(des["cotas"]) == 2
    assert _plano(des["cotas"][0]) == pytest.approx([0.0, -1500.0, 10000.0, -1500.0])
    assert _plano(des["cotas"][1]) == pytest.approx([-1500.0, 0.0, -1500.0, 5000.0])


def test_curva_no_caminho_reprova_em_vez_de_sumir(tmp_path):
    arco = ('<g id="p9" class="IfcMember material-null projection" ifc:name="A" '
            'ifc:guid="g9"><path d="M0,0 A5,5 0 0 1 10,10"/></g>')
    with pytest.raises(ValueError, match="comando de caminho SVG nao tratado"):
        DP.ler_desenho(_svg(tmp_path, extra=arco))


def test_svg_sem_a_matriz_do_desenho_reprova(tmp_path):
    p = tmp_path / "solto.svg"
    p.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm">'
                 '<g class="x"/></svg>', encoding="utf-8")
    with pytest.raises(ValueError, match="sem ifc:matrix3"):
        DP.ler_desenho(str(p))


@pytest.mark.parametrize("larg_m, alt_m, esperado", [
    (16.0, 11.0, (50, "A3")),      # 320 x 220 mm a 1:50 cabe na area util do A3
    (20.0, 11.0, (50, "A2")),      # 400 mm de largura ja nao cabe no A3 (util 385)
    (27.0, 18.0, (50, "A2")),      # 540 x 360 a 1:50: exatamente a area util do A2
    (27.0, 19.0, (50, "A1")),      # 380 mm de altura ja passa do A2 (util 360)
    (51.0, 31.5, (75, "A1")),      # 1020 mm a 1:50 passa do A1 -> 1:75
    (75.0, 40.0, (100, "A1")),     # 1000 mm a 1:75 passa -> 1:100
])
def test_escolhe_a_maior_escala_na_menor_folha(larg_m, alt_m, esperado):
    esc, formato, _w, _h, de_escape = DP.escolher_folha(larg_m * 1000, alt_m * 1000)
    assert (esc, formato) == esperado and de_escape is False


def test_vista_maior_que_a1_a_1_100_cai_em_escala_de_escape_e_diz():
    esc, formato, _w, _h, de_escape = DP.escolher_folha(120000.0, 40000.0)
    assert (esc, formato, de_escape) == (150, "A1", True)
    with pytest.raises(ValueError, match="nao cabe em A1"):
        DP.escolher_folha(1.0e6, 1.0e6)


def test_geometria_vai_ao_modelo_em_tamanho_real_e_por_camada(tmp_path):
    resumo, doc = _dxf(tmp_path, [DP.ler_desenho(_svg(tmp_path))])
    assert not doc.audit().errors
    msp = doc.modelspace()
    viga = [e for e in msp.query("LINE") if e.dxf.layer == "EST-VIGA"]
    assert sorted(round(e.dxf.start.distance(e.dxf.end)) for e in viga) == [10000, 10000]
    pilar = msp.query('LWPOLYLINE[layer=="EST-PILAR-CORTE"]')
    assert len(pilar) == 1
    camadas = {l.dxf.name: l for l in doc.layers}
    assert camadas["EST-PILAR-CORTE"].dxf.lineweight == DP.ESPESSURA_CORTE
    assert camadas["EST-VIGA"].dxf.lineweight == 25
    assert "FUN-BLOCO" in camadas
    assert "GERAL-RAILING" in camadas          # classe fora do mapa nao some
    assert resumo["folhas"][0]["entidades"] == {
        "EST-PILAR-CORTE": 1, "EST-VIGA": 2, "FUN-BLOCO": 1, "GERAL-RAILING": 1}


def test_cota_e_entidade_que_mede_a_geometria(tmp_path):
    _resumo, doc = _dxf(tmp_path, [DP.ler_desenho(_svg(tmp_path))])
    dims = doc.modelspace().query("DIMENSION")
    assert sorted(round(d.get_measurement(), 6) for d in dims) == [5000.0, 10000.0]
    assert {d.dxf.layer for d in dims} == {DP.CAMADA_COTA}
    assert {d.dxf.dimstyle for d in dims} == {"COTA-1-50"}
    estilo = doc.dimstyles.get("COTA-1-50")
    assert estilo.dxf.dimscale == 50.0 and estilo.dxf.dimtxt == DP.ALTURA_TEXTO


def test_folha_tem_viewport_na_escala_e_carimbo_preenchido(tmp_path):
    resumo, doc = _dxf(tmp_path, [DP.ler_desenho(_svg(tmp_path))], PROJETO="Galpao X",
                       RESPONSAVEL="Eng. Y")
    info = resumo["folhas"][0]
    assert (info["escala"], info["formato"]) == (50, "A3")
    assert "Layout1" not in doc.layouts
    folha = doc.layouts.get(info["folha"])
    assert (folha.dxf.paper_width, folha.dxf.paper_height) == (420.0, 297.0)
    vp = [v for v in folha.query("VIEWPORT") if v.dxf.layer == DP.CAMADA_VIEWPORT][0]
    assert vp.dxf.view_height / vp.dxf.height == pytest.approx(50.0)
    assert (vp.dxf.width, vp.dxf.height) == pytest.approx((320.0, 220.0))
    # a viewport inteira fica dentro do quadro, acima do carimbo
    assert vp.dxf.center.y - vp.dxf.height / 2 >= DP.MARGEM + DP.CARIMBO_H - 1e-6
    assert vp.dxf.center.x - vp.dxf.width / 2 >= DP.MARGEM_ESQ - 1e-6
    assert doc.layers.get(DP.CAMADA_VIEWPORT).dxf.plot == 0
    carimbo = {a.dxf.tag: a.dxf.text for a in folha.query("INSERT")[0].attribs}
    assert carimbo["PROJETO"] == "Galpao X" and carimbo["RESPONSAVEL"] == "Eng. Y"
    assert carimbo["TITULO"] == "PLANTA" and carimbo["ESCALA"] == "1:50"
    assert carimbo["FOLHA"] == "01/01  A3" and carimbo["DATA"]
    assert set(carimbo) == set(DP.CAMPOS_CARIMBO)


def test_duas_vistas_nao_se_sobrepoem_no_modelo(tmp_path):
    a = DP.ler_desenho(_svg(tmp_path, "A-PLANTA"))
    b = DP.ler_desenho(_svg(tmp_path, "B-CORTE", larg=510, alt=315))
    resumo, doc = _dxf(tmp_path, [a, b])
    assert [(f["escala"], f["formato"]) for f in resumo["folhas"]] == [(50, "A3"), (75, "A1")]
    ret = {}
    for f in resumo["folhas"]:
        v = [vp for vp in doc.layouts.get(f["folha"]).query("VIEWPORT")
             if vp.dxf.layer == DP.CAMADA_VIEWPORT][0]
        centro = v.dxf.view_center_point
        meia_l, meia_a = f["largura_real_mm"] / 2.0, f["altura_real_mm"] / 2.0
        ret[f["desenho"]] = (centro.x - meia_l, centro.y - meia_a,
                             centro.x + meia_l, centro.y + meia_a)
    a_x0, a_y0, a_x1, a_y1 = ret["A-PLANTA"]
    b_x0, b_y0, b_x1, b_y1 = ret["B-CORTE"]
    separadas = a_x1 < b_x0 or b_x1 < a_x0 or a_y1 < b_y0 or b_y1 < a_y0
    assert separadas, ret
    assert (a_y0, b_y0) == pytest.approx((0.0, 0.0))       # mesma linha de base
    assert {"COTA-1-50", "COTA-1-75"} <= {d.dxf.name for d in doc.dimstyles}


def test_pasta_sem_svg_reprova(tmp_path):
    with pytest.raises(ValueError, match="nenhum .svg"):
        DP.gerar_de_pasta(str(tmp_path), str(tmp_path / "x.dxf"))


def test_eixo_da_grade_vai_ao_dxf_com_linha_bolha_e_rotulo(tmp_path):
    des = DP.ler_desenho(_svg(tmp_path, eixos=_EIXO_1))
    assert len(des["eixos"]) == 1
    p1, p2, rotulo = des["eixos"][0]
    assert rotulo == "1"
    assert _plano([p1, p2]) == pytest.approx([0.0, -2000.0, 0.0, 7000.0])
    resumo, doc = _dxf(tmp_path, [des])
    assert resumo["folhas"][0]["eixos"] == 1
    msp = doc.modelspace()
    linhas = msp.query('LINE[layer=="%s"]' % DP.CAMADA_EIXO)
    assert len(linhas) == 1 and round(linhas[0].dxf.start.distance(linhas[0].dxf.end)) == 9000
    bolhas = msp.query('CIRCLE[layer=="%s"]' % DP.CAMADA_EIXO)
    textos = msp.query('TEXT[layer=="%s"]' % DP.CAMADA_EIXO)
    assert len(bolhas) == 2 and [t.dxf.text for t in textos] == ["1", "1"]
    # uma bolha em cada ponta do eixo, nas duas coordenadas (a vista comeca em
    # x = 3000 e y = 3000 no modelo: o quadro do desenho vai de -3000 a ...)
    centros = sorted((round(c.dxf.center.x), round(c.dxf.center.y)) for c in bolhas)
    assert centros == [(3000, 1000), (3000, 10000)]
    assert sorted((round(t.dxf.align_point.x), round(t.dxf.align_point.y))
                  for t in textos) == centros
    # bolha e rotulo no tamanho de papel vezes a escala da folha (1:50 aqui),
    # sem deformar a letra (fator de largura 1)
    assert {c.dxf.radius for c in bolhas} == {DP.RAIO_BOLHA * 50}
    assert {t.dxf.height for t in textos} == {DP.ALTURA_ROTULO_EIXO * 50}
    assert {t.dxf.get("width", 1.0) for t in textos} == {1.0}
    assert doc.layers.get(DP.CAMADA_EIXO).dxf.linetype == "CENTER"
    assert not doc.audit().errors


def test_desenho_sem_grade_segue_sem_eixo(tmp_path):
    des = DP.ler_desenho(_svg(tmp_path))
    assert des["eixos"] == []
    resumo, doc = _dxf(tmp_path, [des])
    assert resumo["folhas"][0]["eixos"] == 0
    assert len(doc.modelspace().query('*[layer=="%s"]' % DP.CAMADA_EIXO)) == 0


def test_eixo_sem_rotulo_na_ponta_reprova(tmp_path):
    solto = ('<line class="GlobalId-e IfcAnnotation PredefinedType-GRID" '
             'x1="30" y1="100" x2="30" y2="10"/>')
    with pytest.raises(ValueError, match="eixo da grade com 0 rotulos"):
        DP.ler_desenho(_svg(tmp_path, eixos=solto))


def _ifc_com_romaneio(tmp_path):
    ifcopenshell = pytest.importorskip("ifcopenshell")
    import ifc_emit
    spec = {"slug": "lm", "geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0,
                                        "ridge": 7.0, "bay": 5.0},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180",
                          "sapata_adotada": {"B": 2.0, "L": 2.5, "h": 0.6},
                          "romaneio": [{"marca": "C1", "comprimento_m": 6.0, "peso_unit_kg": 253.8},
                                       {"marca": "V1", "comprimento_m": 10.05,
                                        "peso_unit_kg": 356.8}]}}
    return ifc_emit.emitir_ifc_do_spec(spec, str(tmp_path / "lm.ifc"))


def test_lista_de_material_e_contada_no_modelo(tmp_path):
    lista = DP.lista_do_ifc(_ifc_com_romaneio(tmp_path))
    por_marca = {l["marca"]: l for l in lista["linhas"]}
    # 9 porticos x 2 = 18 pilares de 6 m e 18 vigas; comprimento da extrusao
    c, v = por_marca["C1"], por_marca["V1"]
    assert (c["peca"], c["perfil"], c["comprimento_m"], c["qtd"]) == ("Pilar", "HEA200", 6.0, 18)
    assert (c["peso_unit_kg"], c["peso_total_kg"]) == (253.8, 4568.4)
    assert (v["qtd"], v["peso_total_kg"]) == (18, round(356.8 * 18, 1))
    # fundacao entra contada e SEM peso (o calculo nao a pesa): celula vazia
    sap = [l for l in lista["linhas"] if l["peca"] == "Fundacao"]
    assert sap and sum(l["qtd"] for l in sap) == 18
    assert all(l["peso_total_kg"] is None for l in sap)
    # a altura do bloco nao entra na coluna de comprimento
    assert all(l["comprimento_m"] is None for l in sap)
    assert lista["peso_total_kg"] == round(4568.4 + 356.8 * 18, 1)
    assert lista["linhas_sem_peso"] == len(lista["linhas"]) - 2
    # a primeira linha e' pilar: ordem por tipo de peca
    assert lista["linhas"][0]["peca"] == "Pilar"


def test_lista_de_material_vira_folha_do_dxf_e_avisa_do_peso_parcial(tmp_path):
    lista = DP.lista_do_ifc(_ifc_com_romaneio(tmp_path))
    resumo, doc = _dxf(tmp_path, [DP.ler_desenho(_svg(tmp_path))], PROJETO="Galpao X")
    assert "lista" not in resumo
    destino = str(tmp_path / "com_lista.dxf")
    resumo = DP.gerar_dxf([DP.ler_desenho(_svg(tmp_path))], destino, {"PROJETO": "Galpao X"},
                          lista=lista)
    doc = ezdxf.readfile(destino)
    assert not doc.audit().errors
    assert resumo["lista"]["folha"] == "02-LISTA-DE-MATERIAL"
    assert resumo["lista"]["linhas"] == len(lista["linhas"])
    folha = doc.layouts.get("02-LISTA-DE-MATERIAL")
    textos = [t.dxf.text for t in folha.query("TEXT")]
    assert "C1" in textos and "HEA200" in textos and "4568,4" in textos
    assert "TOTAL PESADO" in textos
    assert any("sem peso" in t and "NAO e' o peso da obra" in t for t in textos)
    carimbo = {a.dxf.tag: a.dxf.text for a in folha.query("INSERT")[0].attribs}
    assert carimbo["TITULO"] == "LISTA DE MATERIAL" and carimbo["FOLHA"] == "02/02  A3"
    # a folha da vista passa a contar a lista no total de folhas
    vista = doc.layouts.get(resumo["folhas"][0]["folha"])
    assert {a.dxf.tag: a.dxf.text for a in vista.query("INSERT")[0].attribs}["FOLHA"] \
        == "01/02  A3"


def test_lista_que_nao_cabe_na_folha_reprova(tmp_path):
    lista = {"linhas": [{"marca": "M%d" % i, "peca": "Barra", "perfil": "L50", "comprimento_m": 1.0,
                         "qtd": 1, "peso_unit_kg": None, "peso_total_kg": None}
                        for i in range(60)],
             "peso_total_kg": None, "linhas_sem_peso": 60}
    with pytest.raises(ValueError, match="nao cabe numa folha A3"):
        DP.gerar_dxf([DP.ler_desenho(_svg(tmp_path))], str(tmp_path / "x.dxf"), {}, lista=lista)
