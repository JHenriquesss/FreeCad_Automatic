# ============================================================================
# test_secao_por_ligacao.py - o eixo do CORTE A-A e escolhido POR LIGACAO.
#
# HISTORIA: o corte saia perpendicular a elevacao para todos os detalhes. Para o
# CLIPE DE GIRT isso fatiava quase so ar. A conta de arestas (proxy do PR #33,
# LIMIAR_SEC=15) foi assim:
#     10  -> antes do fix de SectionOrigin (#33): corte vazio, sem hachura
#     22  -> apos o #33
#     14  -> apos o #38 (mover a girt mudou o que o plano atravessa) = REPROVA
#     15  -> normal x (transversal a girt): passava por UMA aresta
#     25  -> normal z (corte em PLANTA na altura do clipe): informativo
#
# O corte em planta e como esse detalhe e desenhado na pratica: mostra a secao do
# pilar, o clipe e a girt em planta.
#
# COMO FOI MEDIDO: `scratchpad/probe_pe13.py` gera SO este detalhe dentro do
# freecad.exe e conta as arestas. Isso importa porque NAO da para medir pelo
# bridge - `getEdgeByIndex` so popula com a cena grafica montada (retorna 0 ate
# para a vista base). Sem esse harness cada tentativa custava um executivo
# completo (12-20 min) e viravam chutes.
# ============================================================================
import ast
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD


def test_tabela_tem_o_eixo_do_corte():
    """Cada entrada de LIGACOES carrega o eixo da normal do corte."""
    for item in TD.LIGACOES:
        assert len(item) == 8, "entrada de LIGACOES sem o campo sec_normal: %r" % (item,)


def test_clipe_de_girt_corta_em_planta():
    """normal z = corte horizontal. Medido: 25 arestas contra 14 (normal y,
    historico) e 15 (normal x, transversal a girt)."""
    d = {it[0]: it[7] for it in TD.LIGACOES}
    assert d["CLIPE_GIRT"] == "z"


def test_demais_ligacoes_mantem_o_historico():
    """So o clipe de girt precisou de eixo proprio - cumeeira e gussets ja davam
    39/63/70 arestas. None = perpendicular a elevacao (comportamento antigo)."""
    d = {it[0]: it[7] for it in TD.LIGACOES}
    for k in ("CONEX_CUMEEIRA", "CONEX_GUSSET_COB", "CONEX_GUSSET_PAR",
              "CONEX_CONSOLE"):
        assert d[k] is None


def test_eixos_declarados_existem():
    for it in TD.LIGACOES:
        if it[7] is not None:
            assert it[7] in TD._AXES


def test_detalhe_ligacao_aceita_sec_normal():
    arv = ast.parse(open(os.path.join(GALPAO, "techdraw_exec.py"),
                         encoding="utf-8").read())
    fn = next(n for n in arv.body
              if isinstance(n, ast.FunctionDef) and n.name == "_detalhe_ligacao")
    nomes = [a.arg for a in fn.args.args] + [a.arg for a in fn.args.kwonlyargs]
    assert "sec_normal" in nomes


def test_origem_do_corte_nao_e_deslocada():
    """REGRESSAO: tentei deslocar a origem 25% para fora do plano medio da peca
    (hipotese de plano tangente a alma) e o TechDraw TRAVOU - o executivo estourou
    1200 s sem gerar prancha nenhuma. A origem tem que ser o centro do alvo."""
    txt = open(os.path.join(GALPAO, "techdraw_exec.py"), encoding="utf-8").read()
    assert "origem=c0)" in txt
    assert "c0.add(_off)" not in txt
