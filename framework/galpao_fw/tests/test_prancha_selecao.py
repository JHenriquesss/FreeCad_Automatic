# ============================================================================
# test_prancha_selecao.py - GUARDA SISTEMICA de selecao de geometria por prancha.
#
# POR QUE ESTE ARQUIVO EXISTE: dois bugs da MESMA familia passaram por 371 testes
# e chegaram ao entregavel (PE04 portico transbordando a folha; PE07 "detalhe do
# joelho" desenhando terca/calha, sem coluna nem rafter). Os dois escaparam porque:
#   (a) os testes 'build' sao deselecionados sem o bridge do FreeCAD, e
#   (b) `_cobertura` so checa que cada tipo aparece em ALGUMA prancha - o portico
#       aparecia nas elevacoes, entao as duas pranchas erradas passavam.
# A selecao (`_pref`/`_faixa`/`_snap_portico`) e Python PURO com duck-typing, entao
# da para testa-la com objetos falsos, SEM FreeCAD. E o unico ponto onde este bug
# e detectavel no CI. Sessao 16.
# ============================================================================
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD

BAY = 5700.0


class _BB:
    def __init__(self, x0, x1, y0=0.0, y1=20000.0):
        self.XMin, self.XMax = x0, x1
        self.YMin, self.YMax = y0, y1

    def isNull(self):
        return False


class _Shape:
    def __init__(self, bb):
        self.BoundBox = bb

    def isNull(self):
        return False


class _Obj:
    """Mimica o minimo de um objeto do FreeCAD que a selecao usa."""

    def __init__(self, label, x0, x1, y0=0.0, y1=20000.0):
        self.Label = label
        self.Shape = _Shape(_BB(x0, x1, y0, y1))


def _modelo(n_vaos):
    """Galpao com n_vaos vaos => n_vaos+1 porticos transversais (finos em X) +
    pecas LONGITUDINAIS (terca/calha/tapamento) que atravessam todo o comprimento
    e portanto tem centro X no meio - foram exatamente elas que apareceram no PE07."""
    comp = n_vaos * BAY
    objs = [_Obj("PORTICO_%02d" % i, i * BAY - 100, i * BAY + 100)
            for i in range(n_vaos + 1)]
    objs += [_Obj("TERCA_01", 0, comp), _Obj("CALHA_01", 0, comp),
             _Obj("TAPAMENTO_01", 0, comp)]
    return objs, comp


def _meio(comp):
    return comp / 2.0


@pytest.mark.parametrize("n_vaos", [1, 2, 3, 4, 5, 6, 7, 8])
def test_faixa_do_portico_sempre_pega_um_portico(n_vaos):
    """PE04. Com nº IMPAR de vaos o meio caia ENTRE dois porticos e a faixa
    +-0,45*bay (< meio-vao) voltava VAZIA -> fallback 'predio inteiro'."""
    objs, comp = _modelo(n_vaos)
    meio = TD._snap_portico(objs, "x", _meio(comp))
    frame = TD._faixa(objs, "x", meio, BAY * 0.45)
    assert TD._pref(frame, ("PORTICO",)), (
        "faixa sem PORTICO com %d vaos" % n_vaos)


@pytest.mark.parametrize("n_vaos", [1, 2, 3, 4, 5, 6, 7, 8])
def test_recorte_do_joelho_contem_portico(n_vaos):
    """PE07. A caixa de recorte do joelho (KW=1500) e centrada em `meio`; sem o
    snap ela ficava no vazio entre porticos e pegava so peca longitudinal."""
    objs, comp = _modelo(n_vaos)
    meio = TD._snap_portico(objs, "x", _meio(comp))
    KW = 1500.0
    dentro = [o for o in objs
              if o.Shape.BoundBox.XMin <= meio + KW
              and o.Shape.BoundBox.XMax >= meio - KW]
    assert [o for o in dentro if o.Label.startswith("PORTICO")], (
        "recorte do joelho sem coluna/rafter com %d vaos" % n_vaos)


@pytest.mark.parametrize("n_vaos", [1, 3, 5, 7])
def test_sem_snap_o_bug_reaparece(n_vaos):
    """Trava a REGRESSAO: prova que o snap e o que corrige (e nao coincidencia do
    modelo de teste). O bug aparece com nº IMPAR de VAOS (= nº PAR de porticos):
    o meio do comprimento cai a meio-vao dos dois porticos centrais e a faixa de
    +-0,45*bay nao alcanca nenhum. A amostra tem 5 vaos / 6 porticos (meio=14250,
    porticos em 11400 e 17100, folga de 285 mm) - exatamente este caso.
    Com nº PAR de vaos o meio cai EM CIMA de um portico e o bug nao aparece."""
    objs, comp = _modelo(n_vaos)
    frame = TD._faixa(objs, "x", _meio(comp), BAY * 0.45)   # sem _snap_portico
    assert not TD._pref(frame, ("PORTICO",))
    assert TD._pref(frame, ("TERCA",))     # so sobrava peca longitudinal


def test_snap_escolhe_o_portico_mais_proximo():
    objs, comp = _modelo(4)              # porticos em 0, 5700, ..., 22800
    assert TD._snap_portico(objs, "x", 11400.0) == 11400.0
    assert TD._snap_portico(objs, "x", 12000.0) == 11400.0
    assert TD._snap_portico(objs, "x", 15000.0) == 17100.0


def test_snap_sem_portico_devolve_o_centro():
    """Modelo sem PORTICO (ex.: tesoura) nao pode quebrar: devolve o centro."""
    objs = [_Obj("TERCA_01", 0, 20000)]
    assert TD._snap_portico(objs, "x", 10000.0) == 10000.0


def test_aviso_prancha_registra_e_nao_levanta():
    """A guarda ACUSA mas nao derruba as outras 12 pranchas."""
    del TD.AVISOS_PRANCHA[:]
    TD._aviso_prancha("PE07_DET_JOELHO", "teste")
    assert TD.AVISOS_PRANCHA == [{"prancha": "PE07_DET_JOELHO", "aviso": "teste"}]
    del TD.AVISOS_PRANCHA[:]
