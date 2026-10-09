# ============================================================================
# test_motor_sem_freecad.py - O MOTOR DE CALCULO NAO DEPENDE DO FREECAD.
# Plano de 2026-10-08 (decisoes-arquitetura-projetos.md, Fase 1): "nenhum
# modulo de calculo pode importar FreeCAD; o motor recebe dados e devolve
# dados". O FreeCAD e' SAIDA (modelo 3D e pranchas TechDraw), e so os modulos
# de saida declarados aqui podem cita-lo.
# Duas medidas, porque uma so nao fecha:
#   - ESTATICA (AST): quem cita FreeCAD em qualquer ponto do arquivo, inclusive
#     import tardio dentro de funcao, tem que estar em SAIDA_FREECAD. Pega o
#     modulo de calculo que ganha um `import FreeCAD` escondido.
#   - VIVA (subprocesso com o FreeCAD BLOQUEADO no sys.meta_path): todo modulo
#     importa de verdade, menos os de IMPORTA_NO_TOPO. Pega o import dinamico
#     (importlib) e o import em cadeia, que a AST nao ve. Bloquear, em vez de
#     confiar que o FreeCAD nao esta instalado, deixa a medida igual em
#     qualquer maquina.
# As duas listas sao cobradas nos DOIS sentidos (declarado que deixou de
# citar reprova: isencao morta), e cada medidor e' exercitado com o defeito
# injetado (os dois ultimos testes).
# ============================================================================
"""O motor importa e roda sem FreeCAD; so a saida declarada pode cita-lo."""

import ast
import json
import os
import pathlib
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))

# Modulos de topo que so existem dentro do FreeCAD.
NOMES_FREECAD = ("FreeCAD", "FreeCADGui", "Part", "Draft", "Arch", "TechDraw",
                 "Mesh", "Sketcher", "Import", "importDXF", "PySide", "PySide2",
                 "PySide6")

# {modulo: o que ele entrega pelo FreeCAD}. So estes podem citar o FreeCAD.
SAIDA_FREECAD = {
    "build_galpao": "modelo 3D do galpao de aco",
    "build_concreto": "modelo 3D da estrutura de concreto",
    "build_eletrico": "modelo 3D das instalacoes eletricas",
    "build_federado": "modelo 3D federado das disciplinas",
    "techdraw_exec": "pranchas executivas de aco (TechDraw)",
    "techdraw_concreto": "pranchas de concreto (TechDraw)",
    "techdraw_eletrico": "pranchas de eletrica (TechDraw)",
    "techdraw_hidraulica": "pranchas de hidraulica (TechDraw)",
    "techdraw_incendio": "pranchas de incendio (TechDraw)",
    "techdraw_climatizacao": "pranchas de climatizacao (TechDraw)",
    "techdraw_coordenacao": "pranchas de coordenacao (TechDraw)",
    "techdraw_mezanino": "pranchas do mezanino (TechDraw)",
}

# Dos de cima, os que importam o FreeCAD ao carregar (os demais importam
# dentro da funcao e carregam sem ele). So roda dentro do FreeCAD.
IMPORTA_NO_TOPO = {
    "build_galpao": "enviado ao FreeCAD como script; `import FreeCAD as App` "
                    "no topo",
}

# Script rodado a mao executa ao ser importado (tools_probe_pe13 sobe um
# freecad.exe): a medida viva nao o importa. A estatica cobre todos.
MARCA_AVULSO = "SCRIPT AVULSO"


def _modulos(pasta=GALPAO):
    return {p.stem: p for p in pathlib.Path(pasta).glob("*.py")}


def cita_freecad(caminho):
    """Nomes do FreeCAD importados em qualquer ponto do arquivo (AST)."""
    arvore = ast.parse(pathlib.Path(caminho).read_text(encoding="utf-8",
                                                       errors="replace"))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module.split(".")[0])
    return sorted(nomes & set(NOMES_FREECAD))


def _avulsos(modulos):
    return sorted(m for m, p in modulos.items()
                  if MARCA_AVULSO in p.read_text(encoding="utf-8",
                                                 errors="replace")[:4000])


_SONDA = textwrap.dedent('''
    import importlib, importlib.abc, json, os, sys
    pasta, nomes_fc, alvos = sys.argv[1], set(sys.argv[2].split(",")), sys.argv[3].split(",")

    class Bloqueio(importlib.abc.MetaPathFinder):
        def find_spec(self, nome, path=None, target=None):
            if nome.split(".")[0] in nomes_fc:
                raise ImportError("FREECAD_BLOQUEADO " + nome)

    sys.meta_path.insert(0, Bloqueio())
    sys.path.insert(0, pasta)
    os.chdir(pasta)
    saida_real, sys.stdout = sys.stdout, open(os.devnull, "w")
    bloqueados, pendentes = {}, []
    for nome in alvos:
        try:
            importlib.import_module(nome)
        except BaseException as exc:
            if "FREECAD_BLOQUEADO" in str(exc):
                bloqueados[nome] = str(exc)
            else:
                pendentes.append(nome)
    # import circular so fecha depois de carregar quem o registra: uma
    # segunda volta, com os outros ja em sys.modules.
    outras = {}
    for nome in pendentes:
        sys.modules.pop(nome, None)
        try:
            importlib.import_module(nome)
        except BaseException as exc:
            outras[nome] = "%s: %s" % (type(exc).__name__, str(exc)[:200])
    json.dump({"bloqueados": bloqueados, "outras": outras,
               "carregados_do_freecad": sorted(set(sys.modules) & nomes_fc),
               "importados": len(alvos) - len(bloqueados) - len(outras)},
              saida_real)
''')


def sonda(pasta, alvos):
    """Importa `alvos` de `pasta` num subprocesso com o FreeCAD bloqueado."""
    r = subprocess.run(
        [sys.executable, "-c", _SONDA, str(pasta), ",".join(NOMES_FREECAD),
         ",".join(alvos)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, env=dict(os.environ, PYTHONUTF8="1"))
    assert r.returncode == 0, "a sonda quebrou:\n%s" % r.stderr[-2000:]
    return json.loads(r.stdout)


def test_so_a_saida_declarada_cita_o_freecad():
    modulos = _modulos()
    citam = {m: cita_freecad(p) for m, p in modulos.items()}
    citam = {m: nomes for m, nomes in citam.items() if nomes}
    intrusos = {m: n for m, n in citam.items() if m not in SAIDA_FREECAD}
    assert not intrusos, (
        "modulo fora de SAIDA_FREECAD importando o FreeCAD: %r. Calculo recebe "
        "dados e devolve dados; a geometria vai para um modulo de saida."
        % intrusos)
    mortos = sorted(set(SAIDA_FREECAD) - set(citam))
    assert not mortos, (
        "declarado em SAIDA_FREECAD e nao cita mais o FreeCAD (isencao "
        "morta, tirar da lista): %r" % mortos)


def test_o_motor_inteiro_importa_com_o_freecad_bloqueado():
    modulos = _modulos()
    avulsos = set(_avulsos(modulos))
    alvos = sorted(set(modulos) - avulsos)
    assert len(alvos) > 150, "a sonda perdeu os alvos: %d" % len(alvos)
    r = sonda(GALPAO, alvos)
    assert not r["outras"], "modulo que nao importa (sem FreeCAD na causa): %r" \
        % r["outras"]
    assert sorted(r["bloqueados"]) == sorted(IMPORTA_NO_TOPO), (
        "so IMPORTA_NO_TOPO pode exigir o FreeCAD ao carregar; a sonda achou "
        "%r" % r["bloqueados"])
    assert r["carregados_do_freecad"] == []
    assert r["importados"] == len(alvos) - len(IMPORTA_NO_TOPO)


def test_importa_no_topo_e_subconjunto_da_saida():
    assert set(IMPORTA_NO_TOPO) <= set(SAIDA_FREECAD)
    assert not set(IMPORTA_NO_TOPO) & set(_avulsos(_modulos())), \
        "avulso nao passa pela sonda: nao pode constar como medido por ela"


def test_a_medida_estatica_acusa_o_import_tardio_injetado(tmp_path):
    limpo = tmp_path / "calculo_limpo.py"
    limpo.write_text("import math\n\ndef f():\n    return math.pi\n",
                     encoding="utf-8")
    sujo = tmp_path / "calculo_sujo.py"
    sujo.write_text("def f():\n    import FreeCAD as App\n    return App\n",
                    encoding="utf-8")
    de_part = tmp_path / "calculo_part.py"
    de_part.write_text("def f():\n    from Part import makeBox\n",
                       encoding="utf-8")
    assert cita_freecad(limpo) == []
    assert cita_freecad(sujo) == ["FreeCAD"]
    assert cita_freecad(de_part) == ["Part"]


def test_a_sonda_acusa_o_import_de_topo_e_o_dinamico_injetados(tmp_path):
    (tmp_path / "limpo.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "de_topo.py").write_text("import FreeCAD\n", encoding="utf-8")
    # a AST nao ve este: so a medida viva pega
    (tmp_path / "dinamico.py").write_text(
        "import importlib\nApp = importlib.import_module('Free' + 'CAD')\n",
        encoding="utf-8")
    (tmp_path / "em_cadeia.py").write_text("import de_topo\n", encoding="utf-8")
    (tmp_path / "quebrado.py").write_text("raise ValueError('outro motivo')\n",
                                          encoding="utf-8")
    assert cita_freecad(tmp_path / "dinamico.py") == []
    r = sonda(tmp_path, ["limpo", "de_topo", "dinamico", "em_cadeia",
                         "quebrado"])
    assert sorted(r["bloqueados"]) == ["de_topo", "dinamico", "em_cadeia"]
    assert list(r["outras"]) == ["quebrado"]
    assert r["importados"] == 1
