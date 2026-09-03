"""G34 - Fechar o que a varredura achar, comecando pelas vigas.

Toda viga, todo tramo: As de flexao M+/M-, cortante, ancoragem, ELS de flecha.
Atencao ao M- de apoio interno (w.L2/10 do tramo < w.L2/8 do apoio).

Feito de verdade quando:
  - armadura_viga sai de sem_quantidade e entra com peso;
  - o executivo ganha prancha de armacao de viga;
  - um teste trava a transicao (nao volta para a lista de buracos em silencio).
"""

import copy
import json
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import desenho_pavimento as dp
import edificio_multipavimento as em
import gestao_edificio as ge
import varredura_nao_verificados as var
import viga_concreto as vgc


def _spec_mini():
    return {
        "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                      "pe_direito": 2.90},
        "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                       + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"}
                          for i in range(2, 0, -1)]),
        "laje": {"h": 0.10}, "viga": {"b": 0.20, "h": 0.50},
        "materiais": {"fck": 30e3, "fyk": 500e3},
    }


@pytest.fixture(scope="module")
def rodado():
    return em.rodar(_spec_mini())


# ---------------- toda viga, todo tramo ----------------
def test_toda_viga_todo_tramo_verificado(rodado):
    vv = rodado.get("vigas_verificacao")
    assert isinstance(vv, dict) and vv["por_linha"]
    assert vv["n_tramos"] == sum(len(l["tramos"]) for l in vv["por_linha"])
    # malha 3x2 vaos: 3 linhas X x 3 tramos + 4 linhas Y x 2 tramos = 17
    assert vv["n_tramos"] == 17
    assert vv["OK"], vv["reprovados"]
    assert rodado["gates"]["vigas"]["OK"]
    assert rodado["gates"]["vigas"]["n_tramos"] == 17


def test_cada_tramo_tem_as_mm_cortante_ancoragem_els(rodado):
    for linha in rodado["vigas_verificacao"]["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["OK"], (linha["nome"], tramo)
            # flexao M+ e M-
            assert tramo["As_inf_cm2"] > 0
            assert tramo["As_sup_cm2"] > 0
            assert tramo["M_d_kNm"] > 0
            assert tramo["M_d_neg_envoltoria_kNm"] > 0
            # cortante
            assert tramo["V_d_kN"] > 0 and tramo["cort_ok"]
            # ELS flecha + fissuracao
            ver = tramo["verificacao"]
            assert ver["els_ok"] and ver["fissu_ok"]
            # ancoragem
            assert ver["ancoragem"]["lb_nec_mm"] > 0


def test_momento_negativo_da_envoltoria_coberto_e_maior_que_tabela(rodado):
    """O G13 achou: viga_concreto sozinha usa w.L2/10; no apoio interno de dois
    vaos o real e' w.L2/8. O repasse tem que cobrir -- e tem que fazer diferenca."""
    achou_continua = False
    for linha in rodado["vigas_verificacao"]["por_linha"]:
        for tramo in linha["tramos"]:
            assert tramo["momento_negativo_coberto"], (linha["nome"], tramo)
            if tramo["M_d_neg_envoltoria_kNm"] > 0:
                achou_continua = True
                assert tramo["M_d_neg_dimensionado_kNm"] == pytest.approx(
                    tramo["M_d_neg_envoltoria_kNm"], abs=0.01)
    assert achou_continua
    # prova de que o repasse muda a armadura: sem M_d_neg sai outro numero
    base = {"vao": 4.0, "b": 0.20, "h": 0.45, "fck": 25e3, "fyk": 500e3,
            "q": 20.0, "continuidade": "continua"}
    tabela = vgc.verifica_viga(dict(base))
    envoltoria = vgc.verifica_viga(dict(base, M_d_neg=2.0 * tabela["M_d_neg"]))
    assert envoltoria["As_sup_cm2"] > tabela["As_sup_cm2"]


def test_viga_esbelta_reprova_nomeando_tramo():
    spec = _spec_mini()
    spec["viga"] = {"b": 0.12, "h": 0.30}
    r = em.rodar(spec)
    assert not r["gates"]["vigas"]["OK"]
    assert r["vigas_verificacao"]["reprovados"]
    assert all("tramo" in m for m in r["vigas_verificacao"]["reprovados"])
    assert "vigas" in r["reprovados"]


# ---------------- orcamento: sai de sem_quantidade ----------------
def test_armadura_viga_tem_peso_e_sai_de_sem_quantidade(rodado):
    dados = ge.derivacao({"estrutura": rodado, "instalacoes": {}})
    q = dados["quantitativos"]
    assert q["armadura_viga"] > 0
    motivos = {i["item"]: i["motivo"] for i in dados["nao_derivados"]}
    assert "armadura_viga" not in motivos
    # plausivel de viga de edificio
    taxa = q["armadura_viga"] / dados["composicao"]["viga_m3"]
    assert 20.0 <= taxa <= 200.0, taxa


def test_orcamento_do_loop_nao_lista_mais_armadura_viga_sem_peso():
    import copy as _cp
    import tempfile
    import project_loop
    from builtin_adapters import register_builtin_adapters
    register_builtin_adapters()
    repo = os.path.dirname(os.path.dirname(GALPAO))
    spec_path = os.path.join(repo, "projects", "edificio-multipavimento",
                             "project-spec.json")
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    destino = tempfile.mkdtemp(prefix="g34-")
    man = project_loop.run_project(_cp.deepcopy(spec), destino,
                                   {"generate_ifc": False, "generate_2d": True})
    orc = man["deliverables"]["orcamento"]
    assert "armadura_viga" in orc["codigos"]
    assert "armadura_viga" not in orc["sem_quantidade"]


# ---------------- executivo: prancha de armacao ----------------
def test_prancha_de_armacao_de_viga_existe_e_confere(rodado, tmp_path):
    vv = rodado["vigas_verificacao"]
    svg = dp.prancha_armacao_vigas_svg(vv)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "ARMACAO DE VIGAS" in svg
    conf = dp.confere_armacao_vigas(vv, svg)
    assert conf["ok"], conf["faltando"]
    assert conf["n_tramos"] == vv["n_tramos"] == 17
    # tem As, estribo, ancoragem e flecha por tramo
    assert "As_inf" in svg or "As" in svg
    assert "ESTRIBO" in svg and "LB" in svg and "FLECHA" in svg
    caminho = dp.gerar_prancha_armacao_vigas(vv, str(tmp_path / "vigas.svg"))
    assert os.path.exists(caminho)


def test_hook_de_desenhos_emite_a_prancha(tmp_path):
    import copy as _cp
    import project_loop
    from builtin_adapters import register_builtin_adapters
    register_builtin_adapters()
    repo = os.path.dirname(os.path.dirname(GALPAO))
    spec_path = os.path.join(repo, "projects", "edificio-multipavimento",
                             "project-spec.json")
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    man = project_loop.run_project(_cp.deepcopy(spec), str(tmp_path),
                                   {"generate_ifc": False, "generate_2d": True})
    arts = man["deliverables"]["drawings"]["artifacts"]
    assert "drawings/armacao-vigas-pavimento-tipo.svg" in arts
    assert len(arts) == 3


# ---------------- trava da transicao ----------------
def test_viga_nao_pode_voltar_para_a_lista_de_buracos_em_silencio():
    """Uma vez fechado, ninguem devolve para NAO_VERIFICADOS sem o teste gritar.

    Trava em 3 pontos (lista, scan e numero): se qualquer um voltar, este teste
    -- e o test_lista_confere -- ficam vermelhos.
    """
    for chave in (("edificio", "viga", "M_positivo"),
                  ("edificio", "viga", "M_apoios"),
                  ("edificio", "viga", "V_max")):
        assert chave not in var.chaves_declaradas(), (
            "G34 fechou a viga; %r voltou para NAO_VERIFICADOS" % (chave,))
        assert chave not in var.chaves_varridas(), (
            "a varredura voltou a achar %r sem cheque -- o repasse caiu" % (chave,))
    # o numero tambem trava: sem peso, o buraco voltou
    r = em.rodar(_spec_mini())
    dados = ge.derivacao({"estrutura": r, "instalacoes": {}})
    assert dados["quantitativos"].get("armadura_viga", 0) > 0, (
        "armadura_viga voltou a vazia: o fechamento foi desfeito")
