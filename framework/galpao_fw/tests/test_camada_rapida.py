# ============================================================================
# test_camada_rapida.py - A FRONTEIRA ENTRE A CAMADA RAPIDA E A LENTA DA SUITE
# (plano de 2026-10-08, Fase 1). A fronteira e' medida em
# `tests/camada_lenta.py`; aqui se cobra que a lista nao apodreca:
#   - arquivo declarado lento que nao existe mais reprova (isencao morta);
#   - todo arquivo que sobe o FreeCAD esta na camada lenta, pela fonte unica
#     do censo (nunca uma copia da lista);
#   - o guarda do motor sem FreeCAD roda na camada rapida;
#   - o medidor do runner (`tools/suite_rapida.confere`) acusa o orcamento
#     estourado e o arquivo que passou do corte (defeito injetado).
# ============================================================================
"""Camada rapida x lenta: lista medida, sem isencao morta, runner que acusa."""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)


def _por_caminho(nome, *partes):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(GALPAO, *partes))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CL = _por_caminho("_camada_lenta_teste", "tests", "camada_lenta.py")
CF = _por_caminho("_censo_freecad_teste", "tests", "censo_freecad.py")
SR = _por_caminho("_suite_rapida_teste", "tools", "suite_rapida.py")


def test_todo_arquivo_declarado_lento_existe():
    mortos = sorted(a for a in CL.LENTOS_MEDIDOS
                    if not os.path.isfile(os.path.join(GALPAO, a)))
    assert not mortos, "declarado lento e nao existe mais (tirar da lista): %r" % mortos


def test_todo_medido_esta_no_corte_ou_acima():
    abaixo = {a: t for a, t in CL.LENTOS_MEDIDOS.items() if t < CL.CORTE_S}
    assert not abaixo, "abaixo do corte de %.1f s nao e' lento: %r" % (CL.CORTE_S, abaixo)


def test_quem_sobe_o_freecad_esta_na_camada_lenta():
    lentos = CL.arquivos_lentos(CF.GRUPO_FREECAD)
    assert set(CF.GRUPO_FREECAD) <= lentos
    assert set(CL.LENTOS_MEDIDOS) <= lentos


def test_os_guardas_da_fase_1_ficam_na_camada_rapida():
    lentos = CL.arquivos_lentos(CF.GRUPO_FREECAD)
    for guarda in ("tests/test_motor_sem_freecad.py", "tests/test_camada_rapida.py"):
        assert guarda not in lentos, guarda


def test_o_runner_fica_verde_dentro_do_orcamento_e_do_corte():
    # 19,9 s: acima do corte e abaixo de FOLGA x corte (ruido de carga, nao acusa)
    assert SR.FOLGA == 2.0
    assert SR.confere({"tests/a.py": 3.0, "tests/b.py": 19.9}, parede_s=120.0,
                      corte_s=10.0, orcamento_s=600.0) == []


def test_o_runner_acusa_o_orcamento_estourado():
    q = SR.confere({"tests/a.py": 3.0}, parede_s=601.0, corte_s=10.0, orcamento_s=600.0)
    assert len(q) == 1 and "601 s de parede" in q[0]


def test_o_runner_acusa_o_arquivo_que_dobrou_o_corte():
    q = SR.confere({"tests/a.py": 3.0, "tests/pesado.py": 20.0}, parede_s=100.0,
                   corte_s=10.0, orcamento_s=600.0)
    assert len(q) == 1 and "tests/pesado.py somou 20.0 s" in q[0]
