"""Vertical de HIDRAULICA PREDIAL (coordenacao) do galpao: rodar (rede roteada, SEM
dimensionamento - NBR 5626/8160/10844 indisponiveis) + membros_bim (tubos pluvial/esgoto/
agua) + integracao no turnkey (6a disciplina) e no clash (tubo x estrutura/duto/cabo).
Regra AR300: os diametros vem do spec ou de default FLAGADO, nunca de norma inventada."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_hidraulica as ghi
import galpao_turnkey as tk
import ifc_emit


def test_selftest():
    ghi._selftest()


def test_dimensionamento_e_flagado_nao_inventado():
    # sem diametros no spec -> defaults COMERCIAIS explicitamente A CONFIRMAR (norma
    # indisponivel); NUNCA um valor de norma "calculado" de memoria.
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    assert "A CONFIRMAR" in r["dimensionamento"]
    assert r["redes"]["pluvial"]["default"] and r["redes"]["esgoto"]["default"]
    # com diametros informados no spec -> sem flag de default
    r2 = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                    "hidraulica": {"D_pluvial_mm": 150.0, "D_esgoto_mm": 100.0,
                                   "D_agua_mm": 60.0}})
    assert not r2["redes"]["pluvial"]["default"]
    assert "informados no spec" in r2["dimensionamento"]


def test_rodar_geometria_invalida():
    with pytest.raises(ValueError):
        ghi.rodar({"geometria": {"L": 0, "W": 20, "H": 6}})
    with pytest.raises(ValueError):
        ghi.rodar({})


def test_membros_bim_tubos():
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"n_condutores": 4}})
    mb = ghi.membros_bim(r)
    tubos = [m for m in mb if m["tipo"] == "Pipe"]
    assert len(tubos) == 4 + 2                            # condutores pluviais + esgoto + agua
    pluv = next(m for m in mb if m["marca"] == "PLUV1")
    assert pluv["p1"][2] == 6000.0 and pluv["p2"][2] == 0.0   # desce do beiral ao solo
    assert pluv["secao"]["forma"] == "ROUND"
    esg = next(m for m in mb if m["marca"] == "ESG-C")
    assert esg["p1"][2] == -300.0                         # coletor sob o piso


def test_membros_bim_sem_geometria_vazio():
    assert ghi.membros_bim({"redes": {}}) == []


# ------------------------------ integracao no turnkey ------------------------
def _spec_6():
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
        "hidraulica": {},
    }


def test_turnkey_despacha_hidraulica():
    R = tk.rodar(_spec_6())
    assert "hidraulica" in R["executadas"] and "hidraulica" in tk.DISCIPLINAS
    # o sub-spec vazio no topo (turnkey) usa os defaults flagados
    assert "A CONFIRMAR" in R["disciplinas"]["hidraulica"]["raw"]["dimensionamento"]


def test_clash_pega_tubo_x_estrutura_e_duto():
    R = tk.rodar(_spec_6())
    rep = tk.checa_interferencia_federada(R, _spec_6())
    tipos_rev = {c["tipos"] for c in rep["revisar"]}
    assert any("Pipe" in t for t in tipos_rev)                  # tubo aparece no REVISAR
    assert any("Pipe" in t and "Beam" in t for t in tipos_rev)  # tubo x viga
    # tubo x estrutura NAO e' esperado (so aterramento/SPDA e')
    assert not tk._clash_esperado("Beam", "Pipe")


def test_membros_federados_inclui_hidraulica():
    membros, disc = tk._membros_federados(tk.rodar(_spec_6()), _spec_6())
    assert "hidraulica" in disc
    assert any(m["marca"].startswith("P-") for m in membros)


@pytest.mark.skipif(not ifc_emit.disponivel(), reason="ifcopenshell ausente")
def test_emite_ifc_tubos(tmp_path):
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}, "hidraulica": {"n_condutores": 4}})
    f = str(tmp_path / "hid.ifc")
    assert ghi.emitir_bim(r, f) and os.path.getsize(f) > 0
    import ifcopenshell
    m = ifcopenshell.open(f)
    assert len(m.by_type("IfcPipeSegment")) == 6                # 4 pluvial + esgoto + agua
