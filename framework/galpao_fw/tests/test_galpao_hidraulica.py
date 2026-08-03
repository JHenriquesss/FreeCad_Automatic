"""Vertical de HIDRAULICA PREDIAL do galpao: rodar (DIMENSIONA pela NBR 5626:2020/8160/
10844 via hidraulica_predial + roteia) + membros_bim (tubos pluvial/esgoto/agua) +
integracao no turnkey (6a disciplina) e no clash (tubo x estrutura/duto/cabo).
Regra AR300: os valores de norma vem dos PDFs; sem aparelhos, agua/esgoto caem em
default comercial FLAGADO [A CONFIRMAR], nunca norma inventada."""
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


def test_pluvial_dimensionado_por_ponto_de_drenagem():
    # cada condutor drena area/n_condutores (nao o telhado inteiro): 800/4 = 200 m2/ponto
    # -> Q=500 L/min -> Tab.4 1%: DN125. i local (dado de sitio) fica flagado.
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    assert r["redes"]["pluvial"]["fonte"] == "NBR 10844"
    assert r["redes"]["pluvial"]["D_mm"] == 125.0
    assert r["redes"]["pluvial"]["area_por_ponto_m2"] == 200.0
    assert r["redes"]["pluvial"]["saturado"] is False
    assert r["redes"]["pluvial"]["i_default"] is True
    assert "[A CONFIRMAR i local]" in r["dimensionamento"]


def test_pluvial_saturacao_e_sinalizada():
    # telhado enorme com 1 unico condutor -> a vazao excede a maior secao tabelada:
    # o dimensionamento NAO pode saturar em silencio, tem de FLAGAR.
    r = ghi.rodar({"geometria": {"L": 200.0, "W": 60.0, "H": 8.0},
                   "hidraulica": {"n_condutores": 1, "i_pluvial_mm_h": 150.0}})
    assert r["gates"]["rede"]["pluvial_saturado"] is True
    assert "SATURADO" in r["dimensionamento"]


def test_pressao_valvula_descarga_exige_15kPa():
    # conjunto com valvula de descarga -> o ponto mais exigente governa 15 kPa (nao 10)
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_agua": {"bacia_valvula": 1, "lavatorio": 2}}})
    assert r["redes"]["agua_fria"]["pressao"]["p_min_kPa"] == 15.0
    # sem valvula -> 10 kPa (geral)
    r2 = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                    "hidraulica": {"aparelhos_agua": {"bacia_caixa": 1, "lavatorio": 2}}})
    assert r2["redes"]["agua_fria"]["pressao"]["p_min_kPa"] == 10.0


def test_agua_esgoto_default_flagado_sem_aparelhos():
    # sem aparelhos, agua/esgoto caem em default comercial explicitamente A CONFIRMAR
    # (NUNCA norma inventada); dimensionamento fica INCOMPLETO.
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0}})
    assert r["redes"]["agua_fria"]["default"] and r["redes"]["esgoto"]["default"]
    assert r["dimensionamento_completo"] is False
    assert "A CONFIRMAR - informe aparelhos" in r["dimensionamento"]


def test_agua_esgoto_calculados_com_aparelhos():
    # com aparelhos informados, agua (NBR 5626:2020) e esgoto (NBR 8160) sao CALCULADOS
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_agua": {"bacia_caixa": 1, "lavatorio": 1,
                                                     "chuveiro": 1},
                                  "aparelhos_esgoto": {"bacia": 1, "lavatorio": 1,
                                                       "chuveiro": 1}}})
    assert r["redes"]["agua_fria"]["fonte"] == "NBR 5626:2020 (soma)"   # default = soma
    assert r["redes"]["agua_fria"]["D_mm"] == 25.0        # Q=1,31 L/s, v<=3 -> DN25
    assert r["redes"]["esgoto"]["fonte"] == "NBR 8160"    # UHC=9 -> coletor DN100 (min)
    assert r["dimensionamento_completo"] is True


def test_agua_metodo_pesos_selecionavel():
    # metodo dos pesos (NBR 5626:1998) selecionavel via spec -> vazao simultanea menor
    base = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2,
                                              "chuveiro": 2}}}
    r_soma = ghi.rodar(base)                                  # default = soma
    base_p = {"geometria": base["geometria"],
              "hidraulica": dict(base["hidraulica"], metodo_agua="pesos")}
    r_pesos = ghi.rodar(base_p)
    assert r_soma["redes"]["agua_fria"]["metodo"] == "soma"
    ap = r_pesos["redes"]["agua_fria"]
    assert ap["metodo"] == "pesos" and ap["fonte"] == "NBR 5626:1998 (pesos)"
    assert ap["soma_P"] == 2.0
    assert ap["Q_Ls"] < r_soma["redes"]["agua_fria"]["Q_Ls"]   # simultaneo < soma
    assert "metodo dos pesos" in r_pesos["dimensionamento"]


def test_agua_quente_spafaq():
    # NBR 5626:2020 unificou fria+quente (SPAFAQ): a rede quente reusa as ferramentas da
    # fria (vazao, velocidade <=3 m/s, pressao Fair-Whipple-Hsiao) nos pontos quentes.
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_agua": {"lavatorio": 3, "chuveiro": 2},
                                  "aparelhos_agua_quente": {"lavatorio": 3, "chuveiro": 2},
                                  "p_alim_kPa": 300.0}})
    aq = r["redes"]["agua_quente"]
    assert aq["fonte"] == "NBR 5626:2020 (quente)" and aq["D_mm"] > 0
    assert aq["v_real_ms"] <= 3.0                          # limite de velocidade aplicado
    assert "pressao" in aq and r["gates"]["pressao_agua_quente"]["p_min_kPa"] == 10.0
    assert "agua quente" in r["dimensionamento"]
    mb = ghi.membros_bim(r)
    aqm = next(m for m in mb if m["marca"] == "AGUA-Q")
    assert aqm["material"] == "CPVC" and aqm["secao"]["forma"] == "ROUND"


def test_sem_agua_quente_nao_cria_rede():
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_agua": {"lavatorio": 2}}})
    assert "agua_quente" not in r["redes"]
    assert not any(m["marca"] == "AGUA-Q" for m in ghi.membros_bim(r))


def test_override_diametro_no_spec_vence():
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"D_pluvial_mm": 150.0, "D_esgoto_mm": 100.0,
                                  "D_agua_mm": 60.0}})
    assert r["redes"]["pluvial"]["fonte"] == "spec" and r["redes"]["pluvial"]["D_mm"] == 150.0
    assert r["redes"]["agua_fria"]["fonte"] == "spec"


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
    # condutores pluviais + esgoto + agua + calha (sem aparelhos_esgoto -> sem ventilacao)
    assert len(tubos) == 4 + 3
    assert any(m["marca"] == "CALHA" for m in mb)         # calha no beiral (NBR 10844 Tab.3)
    pluv = next(m for m in mb if m["marca"] == "PLUV1")
    assert pluv["p1"][2] == 6000.0 and pluv["p2"][2] == 0.0   # desce do beiral ao solo
    assert pluv["secao"]["forma"] == "ROUND"
    esg = next(m for m in mb if m["marca"] == "ESG-C")
    assert esg["p1"][2] == -300.0                         # coletor sob o piso


def test_ventilacao_e_calha_dimensionadas():
    # com aparelhos_esgoto (com bacia) -> ventilacao (NBR 8160 Tab.8/D.1) + coluna no 3D;
    # pluvial sempre tem calha (NBR 10844 Tab.3).
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})
    esg = r["redes"]["esgoto"]
    assert esg["uhc"] == 14                              # bacia 6*2 + lavatorio 1*2
    assert esg["ventilacao_ramal_mm"] == 50              # com bacia, ate 17 UHC -> DN50 (Tab.8)
    assert esg["ventilacao_coluna_mm"] == 50             # Tab.D.1: esgoto DN100 -> vent DN50
    assert r["redes"]["pluvial"]["calha_mm"] in (100, 125, 150)
    assert "ventilacao" in r["dimensionamento"] and "calha" in r["dimensionamento"]
    mb = ghi.membros_bim(r)
    vent = next(m for m in mb if m["marca"] == "VENT-C")
    assert vent["p2"][2] > r["geometria"]["H"] * 1000.0  # sobe acima do telhado


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
    assert len(m.by_type("IfcPipeSegment")) == 7                # 4 pluvial + esgoto + agua + calha
