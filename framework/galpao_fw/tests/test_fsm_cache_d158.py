"""D158 - a curva assinatura do FSM memorizada e o mesmo numero.

Medido (D158): 3 checks do G15 chamavam `distorcional_fsm.curva_assinatura`
30 vezes com 5 argumentos distintos (83 % de repeticao), ~1,4 s cada.
A conta passou para `_curva_assinatura_calc` (memorizada); a publica devolve
copias dos arrays.

Por que nao e tautologia: a referencia e `__wrapped__`, a funcao crua sem
cache, rodada de novo a cada chamada; o teste de copia muta o que recebeu e
exige a proxima chamada intacta (o defeito que um cache ingenuo teria).
"""
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import distorcional_fsm as fsm

pytestmark = pytest.mark.skipif(not fsm._HAS_PYCUFSM,
                                reason="pycufsm indisponivel")

PERFIS = ((150.0, 60.0, 20.0, 2.0), (200.0, 75.0, 25.0, 2.65))


def _crua(bw, bf, D, t, fy=250.0, E=200000.0, nu=0.3, Lmin=20.0,
          Lmax=4000.0, n=80):
    return fsm._curva_assinatura_calc.__wrapped__(bw, bf, D, t, fy, E, nu,
                                                  Lmin, Lmax, n)


def test_01_cache_frio_e_quente_iguais_a_funcao_crua():
    """Um assert so: lengths e LF iguais elemento a elemento, My igual, na
    primeira chamada (cache frio) e na repetida (quente)."""
    fsm._curva_assinatura_calc.cache_clear()
    quebras = []
    for perfil in PERFIS:
        ref_L, ref_LF, ref_My = _crua(*perfil)
        for rotulo in ("frio", "quente"):
            L, LF, My = fsm.curva_assinatura(*perfil)
            if not (np.array_equal(L, ref_L) and np.array_equal(LF, ref_LF)
                    and My == ref_My):
                quebras.append("%s %r divergiu" % (rotulo, perfil))
    assert not quebras, "cache FSM D158:\n" + "\n".join(quebras)


def test_02_mexer_no_que_recebeu_nao_contamina_a_proxima():
    """Vermelho que um cache ingenuo teria: zerar o LF devolvido nao pode
    mudar a chamada seguinte (a publica entrega copia)."""
    perfil = PERFIS[0]
    _L, LF, _My = fsm.curva_assinatura(*perfil)
    esperado = LF.copy()
    LF[:] = 0.0
    _L2, LF2, _My2 = fsm.curva_assinatura(*perfil)
    assert np.array_equal(LF2, esperado)
    assert not np.array_equal(LF2, LF)


def test_03_mdist_igual_com_cache_frio_e_quente():
    """O que a terca usa (mdist) sai igual antes e depois de encher o cache."""
    fsm._curva_assinatura_calc.cache_clear()
    frio = fsm.mdist(*PERFIS[1], fy=250.0)
    quente = fsm.mdist(*PERFIS[1], fy=250.0)
    for chave in ("Mcrl_kNm", "Mdist_kNm", "Lcrl_mm", "Lcrd_mm", "My_kNm"):
        assert frio[chave] == quente[chave], chave
    assert np.array_equal(frio["LF"], quente["LF"])
