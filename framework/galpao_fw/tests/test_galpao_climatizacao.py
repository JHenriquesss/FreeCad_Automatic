"""Vertical de CLIMATIZACAO (HVAC) do galpao: rodar (capacidade + rota de dutos) +
membros_bim (tronco/ramais/UTA) + integracao no turnkey (5a disciplina) e no clash
federado (dutos x estrutura = conflitos REAIS a revisar). Puro/CI; IFC gated no ifcopenshell."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_climatizacao as gcl
import galpao_turnkey as tk
import ifc_emit


def test_selftest():
    gcl._selftest()


def test_rodar_capacidade_e_duto():
    r = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "tipo": "galpao"})
    assert abs(r["gates"]["capacidade"]["TR"] - 33.33) < 0.1     # 800 m2 estimativa
    assert r["duto"]["largura_m"] > 0 and r["duto"]["altura_m"] > 0
    assert r["V_insuflamento_m3h"] > 0 and r["ATENDE"] is True


def test_rodar_geometria_invalida():
    with pytest.raises(ValueError):
        gcl.rodar({"geometria": {"L": 0, "W": 20, "H": 6}})
    with pytest.raises(ValueError):
        gcl.rodar({"tipo": "galpao"})                            # sem geometria


def test_membros_bim_tronco_ramais_uta():
    r = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "n_ramais": 4})
    mb = gcl.membros_bim(r)
    dutos = [m for m in mb if m["tipo"] == "Duct"]
    assert len(dutos) == 5 and sum(1 for m in mb if m["tipo"] == "AirHandler") == 1
    tronco = next(m for m in mb if m["marca"] == "DUTO-T")
    assert tronco["p1"][0] == 0.0 and tronco["p2"][0] == 40000.0  # corre no comprimento
    assert tronco["secao"]["bf"] == r["duto"]["largura_m"]        # secao em metros
    # tronco no forro (abaixo do topo) -> cruza a estrutura
    assert 0 < tronco["p1"][2] < 6000.0


def test_membros_bim_sem_geometria_vazio():
    assert gcl.membros_bim({"duto": {"largura_m": 1, "altura_m": 1}}) == []


# ------------------------------ integracao no turnkey ------------------------
def _spec_5():
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
                     "s1": 1.0, "s3": 1.0, "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
                     "fyk": 500e3, "sigma_solo_adm": 250.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0}},
        "climatizacao": {"tipo": "galpao"},
    }


def test_turnkey_despacha_climatizacao():
    R = tk.rodar(_spec_5())
    assert "climatizacao" in R["executadas"]
    assert R["disciplinas"]["climatizacao"]["rodou"] is True
    assert "climatizacao" in tk.DISCIPLINAS and "climatizacao" in tk._ADAPTADORES


def test_clash_federado_pega_duto_x_estrutura():
    # o ganho: dutos cruzam vigas/eletrocalha/detectores -> conflitos REAIS a revisar
    # (nao so SPDA/aterramento esperado). Duct nao e' aterramento -> vai p/ REVISAR.
    R = tk.rodar(_spec_5())
    rep = tk.checa_interferencia_federada(R, _spec_5())
    assert rep["n_revisar"] >= 1                                 # antes do HVAC era 0
    tipos_rev = {c["tipos"] for c in rep["revisar"]}
    assert any("Duct" in t for t in tipos_rev)                  # duto aparece no REVISAR
    assert any("BeamxDuct" in t or "DuctxBeam" in t for t in tipos_rev)  # duto x viga
    # e o duto x estrutura NAO e' classificado como esperado (so aterramento/SPDA e')
    assert not tk._clash_esperado("Beam", "Duct")


def test_membros_federados_inclui_climatizacao():
    R = tk.rodar(_spec_5())
    membros, disc = tk._membros_federados(R, _spec_5())
    assert "climatizacao" in disc
    assert any(m["marca"].startswith("H-") for m in membros)     # prefixo HVAC


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emite_ifc_dutos(tmp_path):
    r = gcl.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "n_ramais": 4})
    f = str(tmp_path / "hvac.ifc")
    assert gcl.emitir_bim(r, f) and os.path.getsize(f) > 0
    import ifcopenshell
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcDuctSegment")) == 5                 # tronco + 4 ramais
    assert len(m.by_type("IfcUnitaryEquipment")) == 1           # UTA
