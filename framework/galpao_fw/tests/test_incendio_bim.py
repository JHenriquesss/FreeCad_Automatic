"""BIM/IFC da SEGURANCA CONTRA INCENDIO: membros_bim (modelo neutro dos equipamentos)
+ emissao IFC4 via ifc_emit (extensao retrocompativel). COUNT-DRIVEN: o BIM usa as
mesmas contagens do resumo/pranchas. Camada pura de contagem em CI; a emissao IFC roda
so quando o ifcopenshell esta instalado."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_seguranca_incendio as gsi
import ifc_emit


def _r():
    return gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                      "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                      "deteccao": {"viga_m": 0.0},
                      "sprinklers": {"altura_estoque_m": 3.0},
                      "hidrantes": {"ocupacao": "industrial_I2"}})


def _conta(mb):
    t = {}
    for m in mb:
        t[m["tipo"]] = t.get(m["tipo"], 0) + 1
    return t


# ------------------------------- camada PURA (CI) ----------------------------
def test_membros_bim_count_driven_bate_com_resumo():
    r = _r()
    g = r["gates"]
    t = _conta(gsi.membros_bim(r))
    # cada equipamento usa EXATAMENTE a contagem do resumo (drawing/BIM == data)
    assert t["Sprinkler"] == g["sprinklers"]["N_chuveiros"]        # 67
    assert t["SmokeSensor"] == g["deteccao_alarme"]["N_detectores"]  # 10 (pontual)
    assert t["ManualCall"] == g["deteccao_alarme"]["N_acionadores"]  # 1
    assert t["Sign"] == g["sinalizacao"]["N_placas"]              # 11
    assert t["Hydrant"] == g["hidrantes"]["N_hidrantes"]          # 4
    # luminarias = aclaramento (teto) + balizamento (perimetro)
    assert t["EmergencyLight"] == (g["iluminacao_emergencia"]["N_aclaramento"]
                                   + g["iluminacao_emergencia"]["N_balizamento"])
    assert t["Extinguisher"] == 4                                 # 4 cantos
    assert t["WaterTank"] == 1                                    # reserva de incendio


def test_membros_bim_sem_geometria_vazio():
    assert gsi.membros_bim({"spec": {"C": 40.0}, "gates": {}}) == []


def test_membros_bim_coords_mm_e_teto():
    r = _r()
    mb = gsi.membros_bim(r)
    H = r["spec"]["H"] * 1000.0
    spk = next(m for m in mb if m["tipo"] == "Sprinkler")
    assert abs(spk["centro"][2] - (H - 200.0)) < 1e-9            # chuveiro no teto (mm)
    acn = next(m for m in mb if m["tipo"] == "ManualCall")
    assert acn["centro"][2] == 1200.0                            # 0,90-1,35 m (NBR 17240)


def test_mangotinho_tipo1_vira_hosereel():
    # ocupacao residencial_A -> tipo 1 (mangotinho) -> classe HoseReel, nao Hydrant
    r = gsi.rodar({"geometria": {"L": 20.0, "W": 15.0, "H": 5.0},
                   "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                   "hidrantes": {"ocupacao": "residencial_A"}})
    t = _conta(gsi.membros_bim(r))
    assert t.get("HoseReel", 0) >= 1 and "Hydrant" not in t


def test_tanque_dimensionado_pela_maior_reserva():
    r = _r()
    tanque = next(m for m in gsi.membros_bim(r) if m["tipo"] == "WaterTank")
    g = r["gates"]
    V = max(g["hidrantes"]["reserva_m3"], g["sprinklers"]["reserva_m3"])
    # altura do tanque contem o volume (base 3x3 m -> V/9 m de altura, minimo 1 m)
    assert abs(tanque["dims"][2] - max(1000.0, V / 9.0 * 1000.0)) < 1e-6
    assert tanque["centro"][0] < 0                               # fora da planta do galpao


# ------------------------- emissao IFC (gated no ifcopenshell) ---------------
@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emite_ifc4_classes_de_incendio(tmp_path):
    r = _r()
    f = str(tmp_path / "incendio.ifc")
    out = gsi.emitir_bim(r, f)
    assert out and os.path.getsize(f) > 0
    import ifcopenshell
    m = ifcopenshell.open(f)
    assert m.schema == "IFC4"
    g = r["gates"]
    # chuveiros + hidrantes sao IfcFireSuppressionTerminal (PredefinedType distinto)
    fst = m.by_type("IfcFireSuppressionTerminal")
    pdt = [e.PredefinedType for e in fst]
    assert pdt.count("SPRINKLER") == g["sprinklers"]["N_chuveiros"]
    assert pdt.count("FIREHYDRANT") == g["hidrantes"]["N_hidrantes"]
    assert len(m.by_type("IfcSensor")) == g["deteccao_alarme"]["N_detectores"]
    assert len(m.by_type("IfcAlarm")) == g["deteccao_alarme"]["N_acionadores"]
    assert len(m.by_type("IfcLightFixture")) == (g["iluminacao_emergencia"]["N_aclaramento"]
                                                 + g["iluminacao_emergencia"]["N_balizamento"])
    assert len(m.by_type("IfcTank")) == 1
    # placas + extintores -> IfcBuildingElementProxy
    assert len(m.by_type("IfcBuildingElementProxy")) == g["sinalizacao"]["N_placas"] + 4


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_extensao_nao_quebra_bim_existente():
    # a extensao de _IFC_CLASS e aditiva: aco/concreto/eletrico seguem identicos
    ifc_emit._selftest()
