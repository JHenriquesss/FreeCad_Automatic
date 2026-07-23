"""Emissor IFC4 puro-Python (ifcopenshell), SEM FreeCAD - item 2 do roteiro.

Se o ifcopenshell nao estiver instalado, o modulo inteiro e pulado (o export via
FreeCAD, build_galpao._export_ifc, cobre o caso sem a lib).
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("ifcopenshell")   # pula tudo se a lib nao estiver instalada

import ifcopenshell
import modelo_neutro as MN
import ifc_emit as EM

_SEC = {"col": {"nome": "HEA200", "d": 0.190, "bf": 0.200, "tw": 0.0065, "tf": 0.010},
        "raf": {"nome": "HEA180", "d": 0.171, "bf": 0.180, "tw": 0.006, "tf": 0.0095}}
_GEO = {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0}


@pytest.fixture(scope="module")
def ifc_model(tmp_path_factory):
    membros = MN.frame_primario(_GEO, _SEC)            # 18 col + 18 beam
    f = str(tmp_path_factory.mktemp("ifc") / "g.ifc")
    EM.emitir_ifc(membros, f, nome="Amostra")
    return ifcopenshell.open(f)


def test_disponivel():
    assert EM.disponivel() is True


def test_schema_ifc4(ifc_model):
    assert ifc_model.schema == "IFC4"


def test_contagem_tipada(ifc_model):
    assert len(ifc_model.by_type("IfcColumn")) == 18
    assert len(ifc_model.by_type("IfcBeam")) == 18


def test_predefined_types(ifc_model):
    assert ifc_model.by_type("IfcColumn")[0].PredefinedType == "COLUMN"
    assert ifc_model.by_type("IfcBeam")[0].PredefinedType == "BEAM"


def test_marcas_preservadas(ifc_model):
    assert {e.Name for e in ifc_model.by_type("IfcColumn")} == {"C1"}
    assert {e.Name for e in ifc_model.by_type("IfcBeam")} == {"V1"}


def test_perfil_I_reusado(ifc_model):
    profs = ifc_model.by_type("IfcIShapeProfileDef")
    assert len(profs) == 2                             # col + raf, cacheados
    nomes = {p.ProfileName for p in profs}
    assert nomes == {"HEA200", "HEA180"}
    # dims em mm (catalogo em m * 1000)
    hea200 = [p for p in profs if p.ProfileName == "HEA200"][0]
    assert abs(hea200.OverallWidth - 200.0) < 1e-6
    assert abs(hea200.OverallDepth - 190.0) < 1e-6


def test_hierarquia_espacial(ifc_model):
    assert len(ifc_model.by_type("IfcProject")) == 1
    assert len(ifc_model.by_type("IfcBuildingStorey")) == 1
    # todo elemento contido em um storey
    assert len(ifc_model.by_type("IfcRelContainedInSpatialStructure")) >= 1


def test_escala_real_mm_nao_1000x(ifc_model):
    # GUARDA de escala: o modelo IFC usa unidade MILIMETRO; os helpers do ifcopenshell
    # esperam METROS e reconvertem. Sem converter, um pilar de 6 m saía com 6.000.000 mm
    # (1000x) e o modelo abria gigante/inconsistente no Revit. Aqui: pilar de eave=6 m
    # -> extrusao 6000 mm e beiral em z=6000 mm (nao 6e6).
    col = ifc_model.by_type("IfcColumn")[0]
    depth = col.Representation.Representations[0].Items[0].Depth
    assert abs(depth - 6000.0) < 1.0, depth               # 6 m = 6000 mm (nao 6e6)
    import ifcopenshell.util.placement as up
    beam = ifc_model.by_type("IfcBeam")[0]
    zo = up.get_local_placement(beam.ObjectPlacement)[2, 3]
    assert abs(zo - 6000.0) < 1.0, zo                     # beiral em 6000 mm


def test_placa_base_como_ifcplate(tmp_path):
    # placa de base (chapa B x L x t por coluna) -> IfcPlate, espessura real em mm
    spec = {"slug": "pb", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180",
                          "base_adotada": {"B": 0.6, "L": 0.8, "t": 0.1, "db": 0.032, "n": 6}}}
    f = str(tmp_path / "pb.ifc")
    EM.emitir_ifc_do_spec(spec, f)
    m = ifcopenshell.open(f)
    pl = m.by_type("IfcPlate")
    assert all(p.PredefinedType == "SHEET" for p in pl)
    # placas de base = perfil retangular (box); 1 por base: 9 porticos x 2 = 18
    box = [p for p in pl if p.Representation.Representations[0].Items[0].SweptArea.is_a()
           == "IfcRectangleProfileDef"]
    assert len(box) == 18
    sld = box[0].Representation.Representations[0].Items[0]
    assert abs(sld.SweptArea.XDim - 600.0) < 1e-6 and abs(sld.SweptArea.YDim - 800.0) < 1e-6
    assert abs(sld.Depth - 100.0) < 1e-6                  # t = 100 mm (nao 100000)


def test_nervuras_base_como_ifcplate_poligonal(tmp_path):
    # nervura da base = chapa triangular (poligono) -> IfcPlate, perfil arbitrario
    spec = {"slug": "nb", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180",
                          "base_adotada": {"B": 0.6, "L": 0.8, "t": 0.1, "db": 0.032, "n": 6}}}
    f = str(tmp_path / "nb.ifc")
    EM.emitir_ifc_do_spec(spec, f)
    m = ifcopenshell.open(f)
    pl = m.by_type("IfcPlate")
    # 18 placas base (box) + 36 nervuras (2 x 18 bases) = 54
    assert len(pl) == 54
    poly = [p for p in pl
            if p.Representation.Representations[0].Items[0].SweptArea.is_a().startswith("IfcArbitrary")]
    assert len(poly) == 36                                # nervuras triangulares
    tri = poly[0].Representation.Representations[0].Items[0].SweptArea.OuterCurve
    assert len(tri.Points) == 4                           # 3 vertices + fechamento


def test_emitir_do_spec_frame_laminado(tmp_path):
    spec = {"slug": "amostra", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200",
                          "perfil_raf_adotado": "HEA180"}}
    f = str(tmp_path / "spec.ifc")
    out = EM.emitir_ifc_do_spec(spec, f)
    assert out == f and os.path.exists(f)
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcColumn")) == 18 and len(m.by_type("IfcBeam")) == 18


def test_emitir_do_spec_com_tercas(tmp_path):
    # terca_dims [h,bf,lip,t] mm + n_terca -> IfcMember (perfil C) alem do primario
    spec = {"slug": "amostra", "geometria": _GEO,
            "estrutura": {"perfil_col_adotado": "HEA200",
                          "perfil_raf_adotado": "HEA180",
                          "n_terca": 5, "terca_perfil": "Ue300",
                          "terca_dims": [300.0, 85.0, 25.0, 3.35],
                          "longarina_perfil": "UPE140",
                          "longarina_dims": [140.0, 65.0, 5.0, 9.0]}}
    f = str(tmp_path / "spec_t.ifc")
    EM.emitir_ifc_do_spec(spec, f)
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcColumn")) == 18 and len(m.by_type("IfcBeam")) == 18
    # 10 tercas + 4 girts + 0 tirantes (sem n_tirante) + 4 contrav (2 vaos extremos
    # x 2 diagonais; comprimento 40/bay 5 -> 9 porticos) = 18
    assert len(m.by_type("IfcMember")) == (2 * (5 - 1) + 2) + 4 + 4
    # perfil formado a frio -> IfcCShapeProfileDef ; girt U -> IfcUShapeProfileDef ;
    # contrav barra redonda -> IfcCircleProfileDef
    cs = m.by_type("IfcCShapeProfileDef")
    assert len(cs) == 1 and abs(cs[0].Depth - 300.0) < 1e-6 and abs(cs[0].Girth - 25.0) < 1e-6
    us = m.by_type("IfcUShapeProfileDef")
    assert len(us) == 1 and abs(us[0].Depth - 140.0) < 1e-6
    assert len(m.by_type("IfcCircleProfileDef")) == 1        # contrav 20 mm


def test_emitir_tapamento_como_cladding(tmp_path):
    # tapamento de parede -> IfcCovering CLADDING com perfil poligonal;
    # aberturas viram vazios (IfcArbitraryProfileDefWithVoids)
    membros = MN.tapamentos(
        _GEO, fechamento={"tipo": "alvenaria"},
        aberturas={"portao_frente": [4500.0, 2500.0],
                   "janelas_laterais": [3000.0, 1000.0]})
    f = str(tmp_path / "tap.ifc")
    EM.emitir_ifc(membros, f, nome="Amostra")
    m = ifcopenshell.open(f)
    cov = m.by_type("IfcCovering")
    assert len(cov) == 4 and all(c.PredefinedType == "CLADDING" for c in cov)
    # extrusao de perfil (chapa) -> IfcExtrudedAreaSolid, um por painel
    assert len(m.by_type("IfcExtrudedAreaSolid")) == 4
    # 3 paineis com abertura (janela E, janela D, portao FRENTE) -> perfil com vazio
    assert len(m.by_type("IfcArbitraryProfileDefWithVoids")) == 3
    # o 4o (oitao FUNDO, sem abertura) -> perfil fechado simples (sem vazio)
    somente_fechados = [p for p in m.by_type("IfcArbitraryClosedProfileDef")
                        if not p.is_a("IfcArbitraryProfileDefWithVoids")]
    assert len(somente_fechados) == 1


def test_emitir_tapered_do_spec(tmp_path):
    # pórtico de alma variável: emitir_ifc_do_spec NAO retorna None (antes retornava)
    # e os rafters viram IfcExtrudedAreaSolidTapered (loft joelho->cumeeira)
    spec = {"slug": "tap", "geometria": {"span": 30.0, "comprimento": 40.0, "eave": 7.0,
                                         "ridge": 9.0, "bay": 5.0},
            "estrutura": {"tipo_portico": "alma_variavel",
                          "tapered": {"h_joelho": 0.90, "h_cumeeira": 0.40, "bf": 0.25,
                                      "tw": 0.008, "tf": 0.0125, "h_col_base": 0.45}}}
    f = str(tmp_path / "tap.ifc")
    out = EM.emitir_ifc_do_spec(spec, f)
    assert out == f and os.path.exists(f)
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcColumn")) == 18 and len(m.by_type("IfcBeam")) == 18
    # 18 colunas (afinam) + 18 rafters (afinam) = 36 solidos tapered
    assert len(m.by_type("IfcExtrudedAreaSolidTapered")) == 36
    # rafter: funda no joelho (900) -> rasa na cumeeira (400)
    rep = m.by_type("IfcBeam")[0].Representation.Representations[0].Items[0]
    assert abs(rep.SweptArea.OverallDepth - 900.0) < 1e-6
    assert abs(rep.EndSweptArea.OverallDepth - 400.0) < 1e-6


def test_tapered_sem_h_col_base_coluna_prismatica(tmp_path):
    spec = {"slug": "tap2", "geometria": {"span": 30.0, "comprimento": 40.0, "eave": 7.0,
                                          "ridge": 9.0, "bay": 5.0},
            "estrutura": {"tipo_portico": "alma_variavel",
                          "tapered": {"h_joelho": 0.90, "h_cumeeira": 0.40, "bf": 0.25,
                                      "tw": 0.008, "tf": 0.0125}}}
    f = str(tmp_path / "tap2.ifc")
    EM.emitir_ifc_do_spec(spec, f)
    m = ifcopenshell.open(f)
    # só os 18 rafters afinam; colunas prismáticas (IfcExtrudedAreaSolid comum)
    assert len(m.by_type("IfcExtrudedAreaSolidTapered")) == 18
    col_solid = m.by_type("IfcColumn")[0].Representation.Representations[0].Items[0]
    assert col_solid.is_a() == "IfcExtrudedAreaSolid"


def test_tesoura_ainda_retorna_none(tmp_path):
    # treliça (tesoura) segue sem caminho puro -> None (via FreeCAD)
    spec = {"geometria": _GEO, "estrutura": {"tipo_portico": "tesoura",
                                             "perfil_col_adotado": None,
                                             "perfil_raf_adotado": None}}
    assert EM.emitir_ifc_do_spec(spec, str(tmp_path / "x.ifc")) is None


def test_emitir_ifc_analitico_structural(tmp_path):
    # modelo ANALITICO -> IFC4-Structural (nos + barras + apoios + conectividade)
    spec = {"slug": "a", "geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0,
                                       "ridge": 7.0, "bay": 5.0, "base_fixed": True},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180"}}
    f = str(tmp_path / "an.ifc")
    out = EM.emitir_ifc_analitico_do_spec(spec, f)
    assert out == f
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcStructuralAnalysisModel")) == 1
    assert len(m.by_type("IfcStructuralPointConnection")) == 5      # 2+2+1
    assert len(m.by_type("IfcStructuralCurveMember")) == 4          # 2 col + 2 raf
    # cada barra liga aos 2 nos (4*2 = 8 relacoes)
    assert len(m.by_type("IfcRelConnectsStructuralMember")) == 8
    # base_fixed -> 2 condicoes de contorno "engaste"
    bc = m.by_type("IfcBoundaryNodeCondition")
    assert len(bc) == 2 and all(b.Name == "engaste" for b in bc)
    # todos os nos e barras num unico grupo (o SAM)
    grp = m.by_type("IfcRelAssignsToGroup")[0]
    assert len(grp.RelatedObjects) == 5 + 4
    # cada barra carrega a secao (A, I, grupo) num Pset
    assert len(m.by_type("IfcPropertySet")) == 4
    ps = m.by_type("IfcPropertySet")[0]
    nomes = {p.Name for p in ps.HasProperties}
    assert {"Grupo", "Area_m2", "Inercia_m4"} <= nomes


def test_analitico_carrega_esforcos_no_pset(tmp_path):
    # esforcos de projeto (do calculo) no spec -> Nsd/Vsd/Msd/Combo no Pset da barra
    spec = {"slug": "a", "geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0,
                                       "ridge": 7.0, "bay": 5.0, "base_fixed": True},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180",
                          "esf_coluna": {"M_kNm": 120.0, "N_kN": 50.0, "V_kN": 20.0, "combo": "C1_gov"},
                          "esf_rafter": {"M_kNm": 90.0, "N_kN": 40.0, "V_kN": 35.0, "combo": "C2_gov"}}}
    f = str(tmp_path / "esf.ifc")
    EM.emitir_ifc_analitico_do_spec(spec, f)
    m = ifcopenshell.open(f)
    # acha o Pset de uma barra de coluna (Grupo=coluna) e confere os esforcos
    psets = m.by_type("IfcPropertySet")
    col_ps = [ps for ps in psets if any(p.Name == "Grupo" and p.NominalValue.wrappedValue == "coluna"
                                        for p in ps.HasProperties)][0]
    props = {p.Name: p.NominalValue.wrappedValue for p in col_ps.HasProperties}
    assert props["Msd_kNm"] == 120.0 and props["Nsd_kN"] == 50.0
    assert props["Combo_governante"] == "C1_gov"


def test_analitico_tapered_pset_secao_variavel(tmp_path):
    # alma variável: o IFC4-Structural agora sai (antes None) e o Pset da barra
    # traz Variavel + Altura_i/j + Inercia_i/j das seções de ponta
    spec = {"slug": "tapan", "geometria": {"span": 30.0, "comprimento": 40.0, "eave": 7.0,
                                           "ridge": 9.0, "bay": 5.0, "base_fixed": True},
            "estrutura": {"tipo_portico": "alma_variavel",
                          "tapered": {"h_joelho": 0.90, "h_cumeeira": 0.40, "bf": 0.25,
                                      "tw": 0.008, "tf": 0.0125, "h_col_base": 0.45}}}
    f = str(tmp_path / "tapan.ifc")
    out = EM.emitir_ifc_analitico_do_spec(spec, f)
    assert out == f
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcStructuralCurveMember")) == 4
    ps = m.by_type("IfcPropertySet")[0]
    props = {p.Name: p.NominalValue.wrappedValue for p in ps.HasProperties}
    assert props["Variavel"] is True
    assert {"Altura_i_m", "Altura_j_m", "Inercia_i_m4", "Inercia_j_m4"} <= set(props)
    # coluna: 450 -> 900 mm (0.45 -> 0.90 m)
    col_ps = [p for p in m.by_type("IfcPropertySet")
              if any(x.Name == "Grupo" and x.NominalValue.wrappedValue == "coluna"
                     for x in p.HasProperties)][0]
    cprops = {p.Name: p.NominalValue.wrappedValue for p in col_ps.HasProperties}
    assert abs(cprops["Altura_i_m"] - 0.45) < 1e-9 and abs(cprops["Altura_j_m"] - 0.90) < 1e-9


def test_analitico_structural_rotula(tmp_path):
    spec = {"geometria": {"span": 20.0, "comprimento": 40.0, "eave": 6.0, "ridge": 7.0,
                          "bay": 5.0, "base_fixed": False},
            "estrutura": {"perfil_col_adotado": "HEA200", "perfil_raf_adotado": "HEA180"}}
    f = str(tmp_path / "an2.ifc")
    EM.emitir_ifc_analitico_do_spec(spec, f)
    m = ifcopenshell.open(f)
    bc = m.by_type("IfcBoundaryNodeCondition")
    assert len(bc) == 2 and all(b.Name == "rotula" for b in bc)


def test_analitico_structural_tapered_none(tmp_path):
    spec = {"geometria": {"span": 20.0, "eave": 6.0, "ridge": 7.0, "bay": 5.0},
            "estrutura": {"perfil_col_adotado": None, "perfil_raf_adotado": None}}
    assert EM.emitir_ifc_analitico_do_spec(spec, str(tmp_path / "x.ifc")) is None


def test_emitir_do_spec_tapered_retorna_none(tmp_path):
    # portico tapered (sem perfil laminado) -> None (segue via FreeCAD)
    spec = {"geometria": _GEO, "estrutura": {"perfil_col_adotado": None,
                                             "perfil_raf_adotado": None}}
    assert EM.emitir_ifc_do_spec(spec, str(tmp_path / "x.ifc")) is None
