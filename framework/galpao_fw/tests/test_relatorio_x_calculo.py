# ============================================================================
# test_relatorio_x_calculo.py - o RELATORIO e a API tem que contar a mesma
# historia que os gates.
#
# Varredura "memorial x modelo x calculo". A massa de aco do relatorio ja vem do
# modelo (nao pode divergir), mas duas coisas divergiam:
#
# 1) QUADRO INCOMPLETO: o gate 7b (peca da mao-francesa) aparecia SO na linha de
#    resumo "ELEMENTOS QUE NAO ATENDEM". O QUADRO DE VERIFICACOES - a tabela que
#    o engenheiro le item a item - OMITIA justamente o elemento que reprovava.
#    Causa: `calcular()` monta `estrutura.resultados` (fonte do quadro) numa
#    lista SEPARADA da lista de `checks` do rodar_galpao. Duas listas, uma so
#    atualizada.
#
# 2) API MENTIA: `rodar_tudo` devolvia "atende" = res["atende"], que e o veredito
#    do PORTICO, enquanto o RELATORIO imprimia o veredito GLOBAL. Resultado
#    medido: relatorio "NAO ATENDE ... Mao-francesa=3.39" e a chamada devolvendo
#    atende=True. Quem consome por script (CI, outro programa) aprovaria o
#    projeto sem ver a falha - contra-seguranca silenciosa.
#
# Depois: quadro traz "Mao-francesa (peca) u=3.39 NAO ATENDE" e a API devolve
# atende=False com atende_portico=True (os dois vereditos, nomeados).
# ============================================================================
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

SRC = os.path.join(GALPAO, "rodar_projeto.py")


@pytest.fixture(scope="module")
def src():
    return open(SRC, encoding="utf-8").read()


def test_quadro_inclui_a_peca_da_mao_francesa(src):
    assert '"Mao-francesa (peca)": res.get("mf_peca_u")' in src


def test_api_devolve_o_veredito_global(src):
    """"atende" tem que ser o MESMO que o relatorio imprime."""
    assert 'res.get("atende_global")' in src
    codigo = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    assert not [l for l in codigo
                if re.search(r'"atende":\s*bool\(res\.get\("atende"\)\)', l)], (
        "voltou a devolver o veredito do portico como se fosse o global")


def test_api_expoe_os_dois_vereditos(src):
    """O do portico continua util (redimensionamento), mas NOMEADO."""
    assert '"atende_portico"' in src
    assert '"falhas"' in src


def test_relatorio_e_api_usam_a_mesma_fonte(src):
    """Ambos partem de atende_global com fallback para o do portico - se as duas
    rotas divergirem, volta a haver relatorio e API discordando."""
    arv = ast.parse(src)
    fns = {n.name: n for n in ast.walk(arv) if isinstance(n, ast.FunctionDef)}
    for alvo in ("relatorio_consolidado", "rodar_tudo"):
        txt = ast.get_source_segment(src, fns[alvo])
        assert "atende_global" in txt, "%s nao consulta o veredito global" % alvo


def test_quadro_sai_de_estrutura_resultados(src):
    """Guarda a ligacao: o quadro le `estrutura.resultados`, entao gate novo TEM
    de ser gravado la - nao basta entrar na lista de checks do rodar_galpao."""
    assert 'est.get("resultados", {})' in src
    assert 'spec.setdefault("estrutura", {})["resultados"] = resultados' in src


def test_massa_de_aco_do_relatorio_vem_do_modelo(src):
    """Nunca redigitada: sai do resultado do build (que a calcula do Volume)."""
    assert "rm.get('massa_aco_kg', '?')" in src


def test_fonte_compila(src):
    ast.parse(src)
