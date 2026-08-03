"""Prancha de COORDENACAO do modelo federado: desenho_coordenacao (SVG planta+elevacao
coloridas por disciplina + clash) e techdraw_coordenacao (cfg da prancha A1 + bootstrap).
Partes CI (fora do FreeCAD); a geracao da prancha em si (freecad.exe) e' build-gated."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import desenho_coordenacao as dc
import techdraw_coordenacao as tc
import galpao_turnkey as tk


def _spec():
    return {
        "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
        "eletrico": {"tensao_V": 380.0,
                     "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92,
                                "ocupacao": "industrial"},
                     "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
        "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                     "deteccao": {"viga_m": 0.0}},
        "climatizacao": {"tipo": "galpao"},
        "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                       "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}},
    }


def test_selftest():
    dc._selftest()


def test_svg_tem_planta_elevacao_e_disciplinas():
    R = tk.rodar(_spec())
    membros, disc = tk._membros_federados(R, _spec())
    clash = tk.checa_interferencia_federada(R, _spec())
    svg = dc.coordenacao_svg(membros, clash)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for termo in ("PLANTA", "ELEVACAO", "DISCIPLINAS", "RESUMO DE CLASH"):
        assert termo in svg
    # so as disciplinas presentes entram na legenda (nao ha aco sem spec enriquecido)
    assert "Hidraulica" in svg and "Eletrico" in svg
    assert "Aco" not in svg


def test_svg_sem_geometria_nao_quebra():
    assert "sem geometria federada" in dc.coordenacao_svg([], None)


def test_disc_do_membro_prefixo():
    assert dc._disc_do_membro({"marca": "P-PLUV1"}) == "P"
    assert dc._disc_do_membro({"marca": "C-COL1"}) == "C"
    assert dc._disc_do_membro({"marca": "SEMPREFIXO"}) is None


def test_config_de_spec_monta_cfg():
    R = tk.rodar(_spec())
    clash = tk.checa_interferencia_federada(R, _spec())
    cfg = tc.config_de_spec(R, "/tmp/x", spec=_spec(), clash=clash)
    assert cfg["coord_svg"].startswith("<svg")
    assert cfg["clash_hdr"] == ["ITEM A", "ITEM B", "DISCIPLINAS", "SITUACAO"]
    assert len(cfg["clash_rows"]) >= 1
    # carimbo de coordenacao nao vaza material/norma de aco
    assert cfg["carimbo_material"] == "COORDENACAO"
    # as notas citam o frame comum e a triagem esperado x revisar
    txt = "\n".join(cfg["notas"])
    assert "X=comprimento" in txt and "A REVISAR" in txt and "NBR 5419" in txt


def test_config_de_spec_computa_clash_se_none():
    R = tk.rodar(_spec())
    cfg = tc.config_de_spec(R, "/tmp/x", spec=_spec(), clash=None)   # sem clash -> computa
    assert cfg["coord_svg"].startswith("<svg") and cfg["clash_rows"]


def test_bootstrap_injeta_entry():
    R = tk.rodar(_spec())
    cfg = tc.config_de_spec(R, "/tmp/x", spec=_spec())
    boot = tc.script_bootstrap(cfg)
    assert "_entry_coordenacao" in boot and "QTimer" in boot
    assert "coord_svg" in boot                          # cfg embutido


def test_montar_prancha_coordenacao_sem_freecad_erro_limpo():
    # sem freecad.exe: retorna {erro} sem levantar (nao quebra o caderno)
    R = tk.rodar(_spec())
    res = tk.montar_prancha_coordenacao(R, "/tmp/x", spec=_spec(),
                                        freecad_exe="/nao/existe/freecad.exe")
    assert "erro" in res


def test_montar_prancha_coordenacao_exige_2_disciplinas():
    # so 1 disciplina -> erro claro (coordenacao nao faz sentido)
    spec1 = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
             "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                          "deteccao": {"viga_m": 0.0}}}
    R = tk.rodar(spec1)
    # usa um exe existente qualquer p/ passar da checagem de exe e cair na de disciplinas
    res = tk.montar_prancha_coordenacao(R, "/tmp/x", spec=spec1, freecad_exe=sys.executable)
    assert "erro" in res and "disciplinas" in res["erro"]
