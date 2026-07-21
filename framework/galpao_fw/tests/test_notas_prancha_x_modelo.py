# ============================================================================
# test_notas_prancha_x_modelo.py - as NOTAS TECNICAS da prancha vao para a OBRA,
# entao todo numero nelas tem que ser MEDIDO no modelo, nunca afirmado.
#
# Terceira varredura da serie (depois de interpenetracao e rotulo do takeoff):
# "cotas/textos das pranchas x modelo". Dois textos fixos estavam errados:
#
# 1) "2. RN +0,00 = topo do concreto (base das placas)." - FALSO NOS DOIS LADOS.
#    Medido: topo do concreto -100 mm, face inferior da placa -70 mm, face
#    superior +30 mm. Z=0 nao e nenhum dos tres. Esta nota define o DATUM de todo
#    o conjunto de pranchas: quem locasse niveis por ela erraria 100 mm.
#    (A cota do concreto mudou de -70 para -100 no PR #42, quando o gap de graute
#    passou a ser realizado - a nota ja estava errada antes e ficou mais.)
#
# 2) "7. Chumbadores ASTM A36 com gancho 180 mm." - o gancho do modelo tem 60 mm.
#
# Conferida e CORRETA, mas agora derivada: "8. barras d20" (medido 20,0 mm).
#
# O padrao das tres varreduras e o mesmo: onde ha DUAS descricoes da mesma coisa
# (texto e geometria), uma envelhece. A correcao nao e acertar o numero - e fazer
# o texto SAIR da geometria.
# ============================================================================
import ast
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import techdraw_exec as TD

SRC = os.path.join(GALPAO, "techdraw_exec.py")


@pytest.fixture(scope="module")
def src():
    return open(SRC, encoding="utf-8").read()


def _literais_das_notas(src):
    """Strings que entram DE FATO na lista `notas` de _pr_quadros.

    Filtrar por linha ('nao comeca com #') nao serve: as mesmas frases aparecem
    em COMENTARIO e em DOCSTRING, documentando o bug que se corrigiu. Ja me
    derrubou tres vezes. O AST olha o valor, nao o texto do arquivo.
    """
    arv = ast.parse(src)
    fn = next(n for n in ast.walk(arv)
              if isinstance(n, ast.FunctionDef) and n.name == "_pr_quadros")
    for no in ast.walk(fn):
        if (isinstance(no, ast.Assign)
                and any(getattr(t, "id", "") == "notas" for t in no.targets)):
            return [e.value for e in ast.walk(no)
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    raise AssertionError("lista `notas` nao encontrada em _pr_quadros")


def test_nota_do_datum_nao_e_mais_texto_fixo(src):
    lits = _literais_das_notas(src)
    assert not [s for s in lits if "topo do concreto (base das placas)" in s], (
        "voltou a afirmar um datum que o modelo nao honra")
    assert '_nm.get("niveis"' in src


def test_nota_do_chumbador_nao_e_mais_texto_fixo(src):
    assert not [s for s in _literais_das_notas(src) if "gancho 180" in s]
    assert '_nm.get("chumbador"' in src


def test_nota_do_contravento_deriva(src):
    assert not [s for s in _literais_das_notas(src) if "barras d20" in s]
    assert '_nm.get("contrav"' in src


def test_nenhuma_nota_fixa_carrega_medida_em_mm(src):
    """Guarda GERAL: nota tecnica com 'NNN mm' cravado e a forma do bug. As
    excecoes sao propriedades de MATERIAL (fub/fw/filete), nao geometria."""
    ok = ("Filete minimo", "fub", "fw ")
    for s in _literais_das_notas(src):
        if re.search(r"\d+\s*mm", s) and not any(k in s for k in ok):
            raise AssertionError("nota com medida cravada: %r" % s)


def test_fallback_nao_inventa_numero(src):
    """Sem a peca no modelo, a nota tem que ficar GENERICA - jamais cair num
    numero fixo, que e como o erro nasceu."""
    fn = _fonte_de(src, "_pr_quadros")
    for trecho in ('"2. Niveis conforme memorial de calculo."',
                   '"7. Chumbadores ASTM A36 conforme detalhe da base."',
                   '"8. Contraventamento pretensionado c/ esticador."'):
        assert trecho in fn, "fallback ausente ou com numero: %s" % trecho
    assert not re.search(r'"2\.[^"]*\d+\s*mm', fn)


def test_notas_do_modelo_nao_derruba_a_prancha(src):
    """A prancha nao pode falhar por causa de uma nota: erro ao medir devolve
    dict vazio e os fallbacks assumem."""
    fn = _fonte_de(src, "_notas_do_modelo")
    assert "except Exception:" in fn
    assert fn.rstrip().endswith("return out")


def test_niveis_usam_a_peca_de_concreto_disponivel(src):
    """Fundacao rasa (PEDESTAL/SAPATA) ou profunda (BLOCO) - a nota tem que
    funcionar nos dois casos."""
    fn = _fonte_de(src, "_notas_do_modelo")
    for p in ("PLACA_BASE", "PEDESTAL", "BLOCO", "SAPATA"):
        assert p in fn


def test_area_da_barra_vem_do_volume(src):
    """Diametro de barra redonda pelo bbox erraria em barra inclinada; area =
    Volume/comprimento do eixo e robusta a inclinacao."""
    fn = _fonte_de(src, "_area_barra")
    assert "o.Shape.Volume / L" in fn


def _fonte_de(src, nome):
    arv = ast.parse(src)
    for n in ast.walk(arv):
        if isinstance(n, ast.FunctionDef) and n.name == nome:
            return ast.get_source_segment(src, n)
    raise AssertionError("funcao %s nao encontrada" % nome)


def test_funcoes_existem():
    assert callable(TD._notas_do_modelo)
    assert callable(TD._area_barra)


def test_fonte_compila(src):
    ast.parse(src)
