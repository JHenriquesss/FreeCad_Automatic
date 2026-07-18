# ============================================================================
# test_ship_build_src.py - build_galpao.py e ENVIADO como FONTE p/ dentro do
# FreeCAD (execute), nao importado. Se ele importa um modulo IRMAO (ex.
# mao_francesa_geom) e o dir do galpao_fw NAO esta no sys.path do FreeCAD ->
# ModuleNotFoundError e o build 3D QUEBRA. A regressao (caca sessao 14, fix da
# mao-francesa PR #15) passou batido pq os testes 'build' sao deselecionados sem
# bridge. Esta guarda (sem bridge) impede a recorrencia silenciosa.
# ============================================================================
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import rodar_projeto as RP

BUILD = os.path.join(GALPAO, "build_galpao.py")


def _irmaos_importados():
    """Nomes de modulos IRMAOS (existe <nome>.py no galpao_fw) importados por
    build_galpao.py - top-level e dentro de funcoes."""
    src = open(BUILD, encoding="utf-8").read()
    tree = ast.parse(src)
    nomes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                nomes.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            nomes.add(node.module.split(".")[0])
    return {n for n in nomes if os.path.exists(os.path.join(GALPAO, n + ".py"))}


def test_boot_prepende_o_dir_do_galpao():
    src = RP._ship_build_src(BUILD)
    linhas = src.splitlines()[:3]
    assert any("sys.path.insert" in l for l in linhas), \
        "shipped source NAO prepende sys.path -> import de irmao quebra no FreeCAD"
    gdir = GALPAO.replace("\\", "/")
    assert any(gdir in l for l in linhas), "sys.path nao aponta p/ o dir do galpao_fw"


def test_todos_os_irmaos_de_build_existem_no_dir_shipado():
    # cada modulo irmao importado por build_galpao DEVE existir no dir prependado
    # ao sys.path (senao ModuleNotFoundError no FreeCAD).
    irmaos = _irmaos_importados()
    for nome in irmaos:
        assert os.path.exists(os.path.join(GALPAO, nome + ".py")), nome
    # sanity: a mao_francesa_geom (a que quebrou) esta entre os irmaos rastreados
    assert "mao_francesa_geom" in irmaos, \
        "build_galpao deveria importar mao_francesa_geom (a geometria da mao-francesa)"


def test_run_removido_da_fonte_shipada():
    # o disparo '_result_ = run()' e reescrito pelo chamador (com configurar()),
    # nao deve vir na fonte base.
    src = RP._ship_build_src(BUILD)
    assert "_result_ = run()" not in src
