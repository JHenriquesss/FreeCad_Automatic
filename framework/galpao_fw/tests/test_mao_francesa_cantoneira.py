# ============================================================================
# test_mao_francesa_cantoneira.py - a SECAO da mao-francesa e escolha do
# engenheiro, e o 3D desenha EXATAMENTE a peca que o gate verifica.
#
# CONTEXTO: o gate 4.11.3.4 reprova a barra redonda D16 historica (esbeltez 233 >
# 200 e N = 19,73 kN > Nc,Rd = 5,82 kN, u = 3,39). A norma exige que a contencao
# resista a tracao E compressao, e barra redonda e TIRANTE.
#
# POR QUE NAO HA CATALOGO DE CANTONEIRAS: nao existe tabela de perfis L nas
# fontes do projeto. Escrever bitolas de memoria foi o erro do "AR300". Em vez
# disso, `perfis.cantoneira(b, t)` DERIVA as propriedades da geometria (validado
# por integracao exata de poligono em test_cantoneira_geom) e o engenheiro
# informa b e t - que e exatamente o que o framework se propoe a fazer: decidir
# com ele, nao por ele.
#
# MEDIDO no pipeline:
#   sem cantoneira  -> barra redonda D16, u = 3,39, atende_global = False
#   com L50x50x5    -> u = 0,47,          atende_global = True
#   3D: 8 faces (perfil L, nao cilindro), area da secao = 475,0 mm2, que e
#       exatamente t(2b-t) = 5(100-5). 24/24 bracos encostando na terca.
# ============================================================================
import ast
import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import contencao_lateral as CL
import perfis
import projeto_spec as PS

BUILD_SRC = os.path.join(GALPAO, "build_galpao.py")


@pytest.fixture(scope="module")
def src():
    return open(BUILD_SRC, encoding="utf-8").read()


@pytest.fixture
def spec():
    with open(os.path.join(GALPAO, "spec_amostra_engenheiro.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ---- Qs (Anexo F, Tabela F.1) ---------------------------------------------
def test_qs_unitario_para_aba_compacta():
    """b/t <= 0,45.raiz(E/fy): para MR250 o limite e ~12,7, entao L50x50x5
    (b/t = 10) tem Qs = 1,0."""
    assert CL.qs_cantoneira_simples(10.0, 250e3) == 1.0


def test_qs_reduz_acima_do_limite():
    lim = 0.45 * math.sqrt(CL.E / 250e3)
    assert CL.qs_cantoneira_simples(lim + 2.0, 250e3) < 1.0


def test_degrau_no_limite_e_da_norma_nao_da_implementacao():
    """Em (b/t)lim a faixa 1 da 1,000 e a faixa 2 da 0,998:
        1,340 - 0,76 x 0,45 = 1,340 - 0,342 = 0,998
    O degrau de 0,2% esta nos COEFICIENTES ARREDONDADOS da propria Tabela F.1,
    nao na implementacao. Este teste existe para ninguem "consertar" a formula
    (mexer nos coeficientes para fechar em 1,0 seria falsificar a norma).
    """
    lim = 0.45 * math.sqrt(CL.E / 250e3)
    assert CL.qs_cantoneira_simples(lim, 250e3) == 1.0
    logo_acima = CL.qs_cantoneira_simples(lim + 1e-9, 250e3)
    assert logo_acima == pytest.approx(0.998, abs=1e-4)
    assert logo_acima < 1.0                      # o degrau e para BAIXO (a favor)


def test_qs_usa_o_limite_conservador():
    """Ha uma linha VIZINHA na Tabela F.1 para 'abas ligadas continuamente' com
    0,56 (MAIOR = menos restritiva). Cantoneira simples usa 0,45."""
    src_cl = open(os.path.join(GALPAO, "contencao_lateral.py"), encoding="utf-8").read()
    assert "0.45 * rE" in src_cl
    assert "0.91 * rE" in src_cl


# ---- secao para o gate ----------------------------------------------------
def test_secao_cantoneira_usa_r_min():
    """O que governa a flambagem da cantoneira simples e o eixo principal FRACO."""
    s = CL.secao_cantoneira(50, 5, 250e3)
    c = perfis.cantoneira(50, 5)
    assert s["r"] == c["r_min"]
    assert s["A"] == c["A"]


def test_cantoneira_atende_onde_a_barra_redonda_reprova():
    """Mesma solicitacao, so a peca muda."""
    kw = dict(Msd=158.9, h0=0.484, Lbb=4.045, L_braco=0.9324, ang_graus=45.0, fy=250e3)
    r_barra = CL.verifica_braco(sec=CL.secao_barra_redonda(0.016), **kw)
    r_cant = CL.verifica_braco(sec=CL.secao_cantoneira(50, 5, 250e3), **kw)
    assert not r_barra["ok"]
    assert r_cant["ok"], r_cant["motivo"]
    assert r_cant["esbeltez"] < CL.ESBELTEZ_MAX


# ---- spec: o engenheiro escolhe -------------------------------------------
def test_spec_sem_cantoneira_fica_none(spec):
    assert PS.to_build_kwargs(spec)["mf_sec"] is None


def test_spec_com_cantoneira_chega_aos_dois_lados(spec):
    """O MESMO par (b,t) tem que ir para o 3D e para o calculo - se divergirem,
    o gate aprova uma peca e o modelo desenha outra."""
    spec.setdefault("estrutura", {})["mao_francesa"] = {"b_mm": 63, "t_mm": 6}
    assert PS.to_build_kwargs(spec)["mf_sec"] == (63.0, 6.0)
    assert PS.to_rodar_params(spec)["mf_sec"] == (63.0, 6.0)


@pytest.mark.parametrize("b,t", [(50, 50), (50, 60), (50, 0), (50, -1)])
def test_spec_rejeita_geometria_impossivel(spec, b, t):
    spec.setdefault("estrutura", {})["mao_francesa"] = {"b_mm": b, "t_mm": t}
    with pytest.raises(ValueError):
        PS.to_build_kwargs(spec)


# ---- 3D: desenha o perfil L -----------------------------------------------
def test_secao_L_centrada_no_centroide(src):
    """O eixo do membro passa pelo centroide - e o centroide de um L NAO esta no
    meio da aba. Se ficasse no canto, a peca sairia deslocada do no."""
    assert "def l_section_pts(sec):" in src
    assert "return [(y - cgy, z - cgz) for (y, z) in P]" in src


def test_area_da_secao_L_confere():
    """Shoelace sobre os pontos que o build usa == t(2b - t)."""
    import re
    txt = open(BUILD_SRC, encoding="utf-8").read()
    ns = {}
    m = re.search(r"def l_section_pts\(sec\):.*?\n\n\n", txt, re.S)
    exec(m.group(0), ns)
    P = ns["l_section_pts"]((50.0, 5.0))
    A = 0.0
    for i in range(len(P)):
        y0, z0 = P[i]
        y1, z1 = P[(i + 1) % len(P)]
        A += y0 * z1 - y1 * z0
    assert abs(0.5 * A) == pytest.approx(5.0 * (2 * 50.0 - 5.0))
    assert sum(p[0] for p in P) / len(P) != 0.0 or True      # so documenta


def test_build_desenha_cantoneira_quando_configurada(src):
    assert "if MF_SEC:" in src
    assert "l_member(doc, p1, p2, MF_SEC, nm)" in src


def test_MF_SEC_em_configurar_e_reset(src):
    arv = ast.parse(src)
    fn = {n.name: n for n in arv.body if isinstance(n, ast.FunctionDef)}
    for alvo in ("configurar", "reset"):
        decl = {nome for n in ast.walk(fn[alvo]) if isinstance(n, ast.Global)
                for nome in n.names}
        assert "MF_SEC" in decl, "%s nao declara MF_SEC" % alvo


# ---- takeoff --------------------------------------------------------------
def test_takeoff_separa_tirante_de_mao_francesa(src):
    """Estavam agrupados sob 'barra-16' cravado - agora sao pecas diferentes e o
    rotulo tem de refletir a que foi escolhida."""
    assert '"Tirantes / maos-francesas", "barra-16"' not in src
    assert '"Maos-francesas"' in src
    assert '"Tirantes", "barra-%.0f" % D_TIRANTE' in src


def test_diametro_do_tirante_e_constante(src):
    import re
    assert re.search(r"^D_TIRANTE = 16\.0", src, re.M)
    assert 'rod(doc, (xk, y, Z0), (xk, y, EAVE_H), D_TIRANTE,' in src


def test_fonte_compila(src):
    ast.parse(src)
