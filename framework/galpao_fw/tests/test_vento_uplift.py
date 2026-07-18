# ============================================================================
# test_vento_uplift.py - vento de 1 vao tem de gerar SUCCAO no telhado (uplift),
# como a NBR 6123 Tabela 5 e o modelo de multi-vao. O modelo antigo aplicava o
# telhado p/ BAIXO sem Cpe -> anulava o arrancamento (subdimensionava tracao de
# fundacao). Ver wiki 07 §2A / memory bug-sinal-reacao-fundacao.
# ============================================================================
import os
import sys
import math

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_portico as gp
import vento_nbr6123 as v


def _setup(span=20, eave=6, ridge=7, bay=6):
    gp.configurar(span=span, eave=eave, ridge=ridge, bay=bay, base_fixed=False)
    gp.W_WALL_COL = 0.0
    v.configurar(v0=45, cat="II", s3=0.95, z=ridge, theta=math.degrees(gp.THETA))


def test_vento_1vao_succao_no_telhado():
    _setup()
    apply, _ = gp._wind("portao_barlavento")
    fr, ix = gp._frame(); apply(fr, ix)
    # a componente vertical da UDL do telhado tem de ser p/ CIMA (wy>0 = uplift)
    wy = fr.member_udl.get(ix["rafL"][0], (0, 0))[1]
    assert wy > 0, "telhado a barlavento deve SUGAR (uplift), nao empurrar p/ baixo"


def test_vento_1vao_uplift_liquido_e_para_cima():
    _setup()
    apply, _ = gp._wind("portao_barlavento")
    fr, ix = gp._frame(); apply(fr, ix); fr.solve(); R = fr.reactions()
    # resultante vertical aplicada e p/ CIMA (uplift) -> reacao de base negativa
    av = sum(fy for _, (fx, fy, m) in fr.nodal_loads.items())
    for e, (wx, wy) in fr.member_udl.items():
        xi, yi = fr.nodes[fr.elements[e]["i"]]; xj, yj = fr.nodes[fr.elements[e]["j"]]
        av += wy * math.hypot(xj - xi, yj - yi)
    rv = sum(R[3 * b + 1] for b in ix["nBases"])
    assert av > 0, "vento deve levantar (resultante vertical p/ cima)"
    assert abs(av + rv) < 1e-6, "equilibrio vertical"


def test_abertura_dominante_muda_cpi():
    # a escolha do usuario (wizard) passa a valer: vedada usa Cpi menor que portao.
    cp = v.cpi_por_abertura("portao_oitao")
    cv = v.cpi_por_abertura("vedada")
    assert cp["portao_barlavento"] == 0.80 and cv["portao_barlavento"] == 0.20
    # menos pressao interna -> menos succao/uplift no telhado
    _setup()
    gp.configurar(abertura_dominante="vedada")
    apply, _ = gp._wind("portao_barlavento")
    fr, ix = gp._frame(); apply(fr, ix)
    wy_vedada = fr.member_udl.get(ix["rafL"][0], (0, 0))[1]
    gp.configurar(abertura_dominante="portao_oitao")
    apply, _ = gp._wind("portao_barlavento")
    fr, ix = gp._frame(); apply(fr, ix)
    wy_portao = fr.member_udl.get(ix["rafL"][0], (0, 0))[1]
    assert wy_portao > wy_vedada > 0    # ambos uplift, mas portao suga mais
    gp.configurar(abertura_dominante="portao_oitao")   # restaura default


def test_referencia_detecta_uplift_na_base():
    # com o vento correto, o galpao leve de referencia ARRANCA (N de base negativo
    # em alguma combinacao) -> a tracao de chumbador/fundacao passa a ser projetada.
    import rodar_galpao as R
    orig = R._casos_base_envelope
    cap = {}
    def spy(*a, **k):
        o = orig(*a, **k); cap.setdefault("v", o); return o
    R._casos_base_envelope = spy
    try:
        import tempfile
        R.rodar(R.PARAMS_REF, tempfile.mkdtemp())
        Ns = [N for _, N, _, _ in cap["v"]]
        assert min(Ns) < 0, "alguma combinacao deve dar uplift (N<0) no galpao leve"
    finally:
        R._casos_base_envelope = orig
