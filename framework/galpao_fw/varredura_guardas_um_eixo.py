# ============================================================================
# varredura_guardas_um_eixo.py - G83: AS GUARDAS QUE MEDEM UM EIXO SO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_guardas_um_eixo.py) e pelo teste-guarda
# tests/test_guardas_um_eixo_g83.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_descoberta.
#
# Motivacao (G83): o G77 achou uma guarda que media SO o X:
# test_desenho_concreto.py::test_tudo_cabe_no_canvas (regex sobre a fonte
# do SVG, 4 coletas de x/cx/x1/x2 e nenhuma de y). O defeito que ela
# deixou passar por anos: a cota de largura do pilar caia 3,5 px ABAIXO
# da folha, invisivel no entregue. Uma varredura rasa mostrou que o
# arquivo referencia Y so 2 vezes.
#
# Maquina: AST por funcao de teste (mesma familia do G48/G51/G75, sem
# vocabulario de faixa). Para cada `def test_*` (e helpers usados por
# teste) em tests/**/test_*.py, a lente mede tres sinais, todos
# sintaticos e ditos aqui:
#   - X_ONLY: menciona coordenada de X (x/cx/x1/x2/width/xmax) e nenhuma
#     de Y (y/cy/y1/y2/height/ymax).
#   - Y_ONLY: o espelho (rara; entra para o baseline fechar nos dois
#     sentidos, nao porque seja o defeito do G77).
#   - W_SEM_H: menciona width e nao height (o caso width-sem-height do
#     goal; H_SEM_W e o espelho).
#   - REGEX_COORD_SEM_PARSE: extrai coordenada de SVG por re.findall /
#     re.search com padrao que cita coordenada (x=/y=/cx/cy/width/height/
#     polygon/points) SEM nenhum parse no corpo (fromstring/parseString/
#     ET.parse/minidom.parse/confere_folha_svg/censo_de_folhas/.get("x")).
#     Regex sobre ROTULO (">([^<]+)</text>") nao e coordenada e nao entra:
#     checar texto nao e medir geometria.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - guardas legitimamente unidimensionais (ex.: checar que virgula
#     decimal nao aparece em coordenada: o eixo e irrelevante, a
#     propriedade vale por atributo). A lente ACUSA e a triagem no
#     teste-guarda declara o motivo medido pelo qual NAO e bug.
#   - substring pura sobre conteudo ("polygon" in s, ">8<" in s): checagem
#     de conteudo, nao de geometria. So vira achado se o padrao citar
#     coordenada; o resto e triado como conteudo, nao como medida.
#   - `"x"` como VALOR de dicionario (ex.: {"motivo": "x"} no teste do
#     fotovoltaico) casa o sinal X sem ser coordenada. Caso conhecido,
#     triado como falso-positivo no teste-guarda; refinar o sinal para
#     contexto de atributo custaria os `.get("x")` legitimos.
#   - arquivos fora de tests/: a lente mira a suite, nao a arvore.
# ============================================================================
"""Varredura G83: guardas geometricas de um eixo so ou por regex sem parse."""

from __future__ import annotations

import ast
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent
TESTS = GALPAO / "tests"

# Sinais de eixo como aparecem em fonte de teste. Propositalmente
# atributo-like (x=" / "x" / cx / x1 / width) para nao casar palavra
# comum ("existe", "texto", "geometry"). O `(?<![a-zA-Z])` impede que
# atributo COMPOSTO case como eixo (`stroke-dasharray="..."` nao e y).
_PAT_X = re.compile(r"""(?<![a-zA-Z])(?:x\s*=\s*["']|["']x["']|\bcx\b|\bx1\b|\bx2\b|\bwidth\b|\bxmax\b|viewBox)""")
_PAT_Y = re.compile(r"""(?<![a-zA-Z])(?:y\s*=\s*["']|["']y["']|\bcy\b|\by1\b|\by2\b|\bheight\b|\bymax\b|viewBox)""")
_PAT_W = re.compile(r"""\bwidth\b""")
_PAT_H = re.compile(r"""\bheight\b""")

# Parse: qualquer leitura de SVG como XML ou pela guarda generica.
_PARSE_MARCAS = ("fromstring", "parseString", "confere_folha_svg",
                 "censo_de_folhas", "ET.parse", "minidom.parse",
                 '.get("x"', ".get('x'", '.get("y"', ".get('y'",
                 '.get("width"', ".get('width'", '.get("height"',
                 ".get('height'", 'getAttribute')

# Regex com padrao que cita coordenada (o que e geometria, nao rotulo).
_COORD_NO_PADRAO = re.compile(
    r"""x\s*=|y\s*=|cx|cy|x1|x2|y1|y2|width|height|polygon|points|viewBox""",
    re.IGNORECASE)


def _regex_coord_sem_parse(func_no, texto_completo, seg):
    """True se ha re.findall/search com padrao-coordenada e sem parse."""
    tem_re = False
    padrao_coord = False
    for no in ast.walk(func_no):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) \
                and no.func.attr in ("findall", "search"):
            tem_re = True
            if no.args:
                try:
                    pat = ast.get_source_segment(texto_completo, no.args[0]) or ""
                except Exception:
                    pat = ""
                if _COORD_NO_PADRAO.search(pat):
                    padrao_coord = True
    if not (tem_re and padrao_coord):
        return False
    return not any(m in seg for m in _PARSE_MARCAS)


def _classes_de_funcao(func_no, src_texto):
    try:
        seg = ast.get_source_segment(src_texto, func_no) or ""
    except Exception:
        seg = ""
    if "svg" not in seg.lower() and "polygon" not in seg.lower():
        return []
    tem_x = bool(_PAT_X.search(seg))
    tem_y = bool(_PAT_Y.search(seg))
    tem_w = bool(_PAT_W.search(seg))
    tem_h = bool(_PAT_H.search(seg))
    classes = []
    if tem_x and not tem_y:
        classes.append("X_ONLY")
    if tem_y and not tem_x:
        classes.append("Y_ONLY")
    if tem_w and not tem_h:
        classes.append("W_SEM_H")
    if tem_h and not tem_w:
        classes.append("H_SEM_W")
    if _regex_coord_sem_parse(func_no, src_texto, seg):
        classes.append("REGEX_COORD_SEM_PARSE")
    return classes


def sitios_do_arquivo(caminho):
    """Achados de um arquivo de teste: {arquivo, funcao, linha, classes}."""
    caminho = pathlib.Path(caminho)
    try:
        texto = caminho.read_text(encoding="utf-8-sig", errors="replace")
        arvore = ast.parse(texto, filename=str(caminho))
    except (SyntaxError, UnicodeDecodeError):
        return []
    try:
        rel = caminho.relative_to(TESTS).as_posix()
    except ValueError:
        rel = caminho.name
    achados = []
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        classes = _classes_de_funcao(no, texto)
        if classes:
            achados.append({"arquivo": rel,
                            "funcao": no.name,
                            "linha": int(getattr(no, "lineno", 0) or 0),
                            "classes": sorted(classes)})
    return achados


def varredura(raiz=None):
    """Um item por (funcao, classe): {arquivo, funcao, linha, classe}."""
    base = pathlib.Path(raiz) if raiz is not None else TESTS
    achados = []
    for arq in sorted(base.rglob("test_*.py")):
        for sitio in sitios_do_arquivo(arq):
            for classe in sitio["classes"]:
                achados.append({"arquivo": sitio["arquivo"],
                                "funcao": sitio["funcao"],
                                "linha": sitio["linha"],
                                "classe": classe})
    return achados


def _selftest():
    linhas = varredura()
    assert isinstance(linhas, list) and linhas, "lente cega"
    assert all(set(d) == {"arquivo", "funcao", "linha", "classe"}
               for d in linhas)
    return {"n_sitios": len(linhas)}


if __name__ == "__main__":
    for item in varredura():
        print("%s::%s:%s [%s]" % (item["arquivo"], item["funcao"],
                                  item["linha"], item["classe"]))
