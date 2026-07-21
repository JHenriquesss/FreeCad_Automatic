# ============================================================================
# test_ship_cache_modulo.py - o bootstrap enviado ao FreeCAD tem que DESCARTAR
# os modulos irmaos do cache.
#
# O BUG (achado 2026-07-21): o processo do freecad.exe da ponte PERSISTE entre
# execucoes. `build_galpao.py` vai como FONTE, mas seus imports de modulos irmaos
# (hoje `mao_francesa_geom`) resolvem por `sys.modules` - e um modulo ja importado
# numa execucao anterior fica LA. O build continuava rodando a versao ANTIGA ate
# alguem reiniciar o FreeCAD.
#
# POR QUE E GRAVE: falha SILENCIOSA e mascara trabalho JA MERGEADO. O fix das
# pontas da mao-francesa (PR #41) ficou fora do modelo por isso - o codigo e os
# testes diziam 24/24 bracos tocando a terca, e o 3D entregue tinha 20/24. So
# apareceu porque uma constante NOVA (DIAM_BRACO) explodiu com AttributeError:
# "module 'mao_francesa_geom' has no attribute 'DIAM_BRACO'". Se eu tivesse so
# ALTERADO codigo existente, em vez de adicionar um nome, teria passado batido.
#
# Depois do fix: 24/24 bracos a 0,00 mm da terca (medido no modelo).
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import rodar_projeto as RP

BUILD = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture(scope="module")
def boot():
    return RP._ship_build_src(BUILD)


def test_bootstrap_limpa_o_cache_de_modulos(boot):
    assert "del sys.modules[_m]" in boot


def test_limpeza_vem_antes_do_codigo_do_build(boot):
    """Descartar DEPOIS do build ja ter importado nao adianta nada."""
    assert boot.index("del sys.modules[_m]") < boot.index("def build(")


def test_cobre_os_irmaos_de_verdade(boot):
    """A lista sai do diretorio, nao e uma lista fixa que envelhece."""
    for m in ("mao_francesa_geom", "contencao_lateral", "check_nbr8800"):
        assert repr(m) in boot, "modulo irmao %s fora da limpeza" % m


def test_nao_descarta_modulo_alheio(boot):
    """So os irmaos do galpao_fw - derrubar 'os'/'math'/'FreeCAD' do cache
    quebraria o proprio FreeCAD."""
    for m in ("'os'", "'sys'", "'math'", "'FreeCAD'", "'Part'"):
        assert m not in boot.split("def ")[0], "limpeza ampla demais: %s" % m


def test_sys_path_continua_prependado(boot):
    """A funcao original existe para isso (PR #15) - nao pode ter se perdido."""
    assert "sys.path.insert(0," in boot


def test_diametro_do_braco_e_compartilhado():
    """O caso que denunciou o bug: constante nova no modulo irmao. Se o build e o
    gate lerem valores diferentes, o calculo verifica uma peca que nao e a
    desenhada."""
    import mao_francesa_geom as mfg
    src = open(BUILD, encoding="utf-8").read()
    assert "mfg.DIAM_BRACO" in src
    assert mfg.DIAM_BRACO == 16.0
