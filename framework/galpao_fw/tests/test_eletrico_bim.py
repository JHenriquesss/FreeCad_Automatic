"""BIM/IFC do projeto eletrico (Fase 4): membros_bim (modelo neutro dos elementos
fisicos) + emissao IFC4 via ifc_emit (extensao retrocompativel). Camada pura de
contagem em CI; a emissao IFC roda so quando o ifcopenshell esta instalado."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_eletrico as ge
import ifc_emit


def _r():
    spec = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR", "temp_amb": 40.0},
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    return ge.rodar(spec)


# ------------------------------- camada PURA (CI) ----------------------------
def test_membros_bim_contagem():
    mb = ge.membros_bim(_r())
    tipos = {}
    for m in mb:
        tipos[m["tipo"]] = tipos.get(m["tipo"], 0) + 1
    # QGF + trafo + 1 eletrocalha + (4 anel + 4 hastes) aterramento + (4 captor + 8 descidas) SPDA
    assert tipos["Board"] == 1 and tipos["Transformer"] == 1
    assert tipos["CableCarrier"] == 1
    assert tipos["Earthing"] == 8              # 4 anel + 4 hastes
    assert tipos["Cable"] == 12                # 4 captor + 8 descidas (NP III)
    assert len(mb) == 23


def test_membros_bim_sem_geometria_vazio():
    r = _r()
    r.pop("geometria")
    assert ge.membros_bim(r) == []


def test_membros_bim_coords_mm_e_secao_m():
    mb = ge.membros_bim(_r())
    calha = next(m for m in mb if m["tipo"] == "CableCarrier")
    # coords em mm (comprimento 40 m -> 40000 mm), secao em m
    assert calha["p2"][0] == 40000.0 and calha["secao"]["bf"] == 0.10
    haste = next(m for m in mb if m["marca"].startswith("HASTE"))
    assert haste["p1"][2] == -500.0 and haste["p2"][2] == -3500.0    # 3 m enterrada


def test_pontos_perimetro_conta_e_fecha():
    pts = ge._pontos_perimetro(40000.0, 20000.0, 8)
    assert len(pts) == 8
    assert pts[0] == (0.0, 0.0)                # comeca no canto


# ------------------------- emissao IFC (gated no ifcopenshell) ---------------
@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emite_ifc4_tipos_eletricos(tmp_path):
    f = str(tmp_path / "eletrico.ifc")
    out = ge.emitir_bim(_r(), f)
    assert out and os.path.getsize(f) > 0
    import ifcopenshell
    m = ifcopenshell.open(f)
    assert m.schema == "IFC4"
    assert len(m.by_type("IfcElectricDistributionBoard")) == 1     # QGF
    assert len(m.by_type("IfcTransformer")) == 1                   # subestacao
    assert len(m.by_type("IfcCableCarrierSegment")) == 1           # eletrocalha
    assert len(m.by_type("IfcCableSegment")) == 20                 # aterramento + SPDA
    # materiais associados (Aco/Cobre)
    assert len(m.by_type("IfcMaterial")) >= 2


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_extensao_nao_quebra_bim_de_aco():
    # a extensao de _IFC_CLASS e aditiva: o BIM de aco segue identico
    ifc_emit._selftest()
