# ============================================================================
# test_frame2d_hardening.py - o solver NUNCA deve devolver LIXO SILENCIOSO
# (NaN/inf) como se fosse resultado valido: a jusante viraria esforco/reacao
# "certificado" (contra-seguranca). Casos degenerados devem FALHAR ALTO
# (excecao clara) para o caller tratar. Achados no fuzz interno (sessao 16).
# Tambem trava o fix do _eidx (dois membros com dict IDENTICO colidiam ->
# UDL do 2o membro perdido).
# ============================================================================
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import frame2d as f2d

E = 200e6


def test_carga_nan_falha_alto():
    """Carga NaN antes retornava deslocamento NaN sem erro (lixo silencioso)."""
    f = f2d.Frame2D()
    a = f.add_node(0, 0); b = f.add_node(3, 0)
    f.add_element(a, b, E, 1e-2, 1e-4)
    f.add_support(a, True, True, True)
    f.add_nodal_load(b, Fy=float("nan"))
    with pytest.raises(ValueError):
        f.solve()


def test_no_coincidente_falha_alto():
    """No de comprimento zero (nos coincidentes) -> erro, nao NaN silencioso."""
    f = f2d.Frame2D()
    a = f.add_node(0, 0); b = f.add_node(0, 0)
    f.add_element(a, b, E, 1e-2, 1e-4)
    f.add_support(a, True, True, True)
    f.add_nodal_load(b, Fy=-10)
    with pytest.raises((ZeroDivisionError, ValueError)):
        f.solve()


def test_mecanismo_falha_alto():
    """Apoio insuficiente (mecanismo) -> matriz singular, erro explicito."""
    f = f2d.Frame2D()
    a = f.add_node(0, 0); b = f.add_node(3, 0)
    f.add_element(a, b, E, 1e-2, 1e-4)
    f.add_support(a, u=True)          # so trava 1 GDL
    f.add_nodal_load(b, Fy=-10)
    with pytest.raises((np.linalg.LinAlgError, ValueError)):
        f.solve()


def test_eidx_membros_identicos_nao_colide():
    """Dois membros com (i,j,E,A,I) IDENTICOS: _eidx antes devolvia o indice do
    PRIMEIRO para ambos (dict-equal) -> UDL do 2o membro era perdida. Agora
    compara por identidade (is) e da indices distintos."""
    f = f2d.Frame2D()
    a = f.add_node(0, 0); b = f.add_node(3, 0)
    f.add_element(a, b, E, 1e-2, 1e-4)
    f.add_element(a, b, E, 1e-2, 1e-4)     # dict identico ao anterior
    assert f._eidx(f.elements[0]) == 0
    assert f._eidx(f.elements[1]) == 1     # nao colide


def test_udl_no_membro_certo_com_dicts_identicos():
    """A UDL aplicada so no 2o de dois membros identicos deve gerar esforco
    (antes ia para o indice 0 / era perdida -> deslocamento nulo)."""
    f = f2d.Frame2D()
    a = f.add_node(0, 0); b = f.add_node(3, 0)
    f.add_element(a, b, E, 1e-2, 1e-4)
    e1 = f.add_element(a, b, E, 1e-2, 1e-4)
    f.add_support(a, True, True, True)
    f.add_support(b, False, True, False)
    f.add_member_udl(e1, wy=-5.0)
    d, mf = f.solve()
    assert np.all(np.isfinite(d))
    assert np.max(np.abs(d)) > 0.0        # a UDL produziu deformacao


def test_caso_valido_intacto():
    """Cantilever classico continua exato (o hardening nao muda resultado bom)."""
    L, I, A, P = 3.0, 1e-4, 1e-2, 10.0
    f = f2d.Frame2D()
    n0 = f.add_node(0, 0); n1 = f.add_node(L, 0)
    f.add_element(n0, n1, E, A, I)
    f.add_support(n0, True, True, True)
    f.add_nodal_load(n1, Fy=-P)
    d, mf = f.solve()
    exato = -P * L ** 3 / (3 * E * I)
    assert abs(d[3 * n1 + 1] - exato) / abs(exato) < 1e-6
