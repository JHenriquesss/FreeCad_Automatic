# ============================================================================
# test_alcancabilidade.py - A BARRA VERDE COBRE O CALCULO, NAO A ALCANCABILIDADE.
# Um modulo pode ter 100% dos testes passando e mesmo assim NAO EXISTIR do ponto
# de vista de quem usa o framework, porque ninguem o importa a partir de uma
# entrada real (o Loop, um adaptador, a CLI). Foi assim que orcamento, cronograma,
# caderno de encargos e pacote legal ficaram verdes e inalcancaveis.
# Este teste faz o fecho transitivo dos imports a partir das ENTRADAS e exige
# que sobre APENAS o que esta declarado aqui:
#   - CARREGADOS_COMO_FONTE: modulos enviados ao FreeCAD como TEXTO-FONTE (o
#     import nunca aparece na AST de quem os usa). A declaracao e conferida: o
#     caminho tem que ser realmente montado por um modulo alcancavel, senao a
#     "ponte por string" morreu e o modulo virou ilha de verdade.
#   - SCRIPTS_AVULSOS: ferramentas rodadas a mao. A declaracao e conferida no
#     cabecalho do proprio arquivo (marca "SCRIPT AVULSO").
# Qualquer outro modulo que apareca aqui e uma ILHA: ou vira entregavel declarado
# do adaptador (com artefato e hash no manifesto), ou e apagado.
# ============================================================================
"""Alcancabilidade transitiva dos modulos a partir das entradas do framework."""

import ast
import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))


# Portas de entrada do framework: tudo o que um usuario pode chamar.
ENTRADAS = ["project_loop", "project_loop_cli", "builtin_adapters", "galpao_turnkey",
            "rodar_projeto", "rodar_galpao", "galpao_adapter", "casa_residencial",
            "edificio_adapter", "residencial_eletrica", "wizard", "framework"]

# {modulo: (modulo_que_o_envia, trecho que monta o caminho)}
CARREGADOS_COMO_FONTE = {
    "build_concreto": ("galpao_concreto", '"build_concreto.py"'),
    "build_eletrico": ("galpao_eletrico", '"build_eletrico.py"'),
    "build_federado": ("galpao_turnkey", '"build_federado.py"'),
}

SCRIPTS_AVULSOS = ["build_final", "demo_engenheiro", "tools_probe_pe13",
                   "validacao", "verificar_amostra", "validacao_sistema_g15",
                   "varredura_nao_verificados", "varredura_descoberta"]


def _modulos():
    return {p.stem: p for p in GALPAO.glob("*.py")}


def _imports(caminho, modulos):
    arvore = ast.parse(caminho.read_text(encoding="utf-8", errors="replace"))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module.split(".")[0])
    return {m for m in nomes if m in modulos}


def _alcancaveis(sementes=None):
    """Fecho transitivo dos imports a partir de `sementes` (default: ENTRADAS)."""
    modulos = _modulos()
    vistos, fila = set(), list(ENTRADAS if sementes is None else sementes)
    while fila:
        nome = fila.pop()
        if nome in vistos or nome not in modulos:
            continue
        vistos.add(nome)
        fila.extend(_imports(modulos[nome], modulos) - vistos)
    return modulos, vistos


def test_toda_entrada_existe():
    modulos = _modulos()
    faltando = [nome for nome in ENTRADAS if nome not in modulos]
    assert not faltando, "entradas declaradas que nao existem mais: %r" % faltando


def test_nenhuma_ilha_fora_do_declarado():
    # G37: um avulso DECLARADO e' ponto de partida legitimo, entao o que ELE
    # importa nao e' ilha. Sem semear os avulsos, uma biblioteca de consumidor
    # declarado era acusada de inalcancavel (fontes_externas_protocolo, usada
    # por validacao_sistema_g15 e por tools/extrai_fonte_externa.py) - e
    # declara-la avulsa seria mentira: avulso e' script que NINGUEM importa,
    # e essa e' importada por sete arquivos (o proprio guarda abaixo recusou).
    # O fecho estrito (so ENTRADAS) continua valendo para os demais testes.
    modulos, vistos = _alcancaveis(ENTRADAS + SCRIPTS_AVULSOS)
    ilhas = sorted(set(modulos) - vistos
                   - set(CARREGADOS_COMO_FONTE) - set(SCRIPTS_AVULSOS))
    assert not ilhas, (
        "modulos inalcancaveis a partir das entradas: %r. Cada um tem que virar "
        "entregavel declarado de um adaptador (deliverables + hook, com artefato "
        "no manifesto), ser declarado script avulso, ou ser apagado." % (ilhas,))


def test_ponte_por_string_dos_builds_continua_viva():
    # Filtro de nome morto: se o arquivo for renomeado, a montagem do caminho
    # continua compilando e o build vira ilha em silencio.
    modulos, vistos = _alcancaveis()
    for alvo, (remetente, trecho) in CARREGADOS_COMO_FONTE.items():
        assert (GALPAO / (alvo + ".py")).is_file(), \
            "%s declarado como carregado-por-fonte mas o arquivo sumiu" % alvo
        assert remetente in vistos, \
            "%s envia %s, mas o proprio %s ficou inalcancavel" % (
                remetente, alvo, remetente)
        fonte = (GALPAO / (remetente + ".py")).read_text(encoding="utf-8")
        assert trecho in fonte, \
            "%s nao monta mais o caminho %s: a ponte por string morreu" % (
                remetente, trecho)


def test_scripts_avulsos_se_declaram_no_cabecalho():
    for nome in SCRIPTS_AVULSOS:
        caminho = GALPAO / (nome + ".py")
        assert caminho.is_file(), "script avulso declarado que nao existe: %s" % nome
        cabecalho = caminho.read_text(encoding="utf-8")[:1200]
        assert "SCRIPT AVULSO" in cabecalho, (
            "%s esta na lista de scripts avulsos mas nao se declara como tal no "
            "cabecalho" % nome)


def test_scripts_avulsos_nao_sao_importados_por_ninguem():
    modulos = _modulos()
    for nome in SCRIPTS_AVULSOS:
        importadores = [outro for outro, caminho in modulos.items()
                        if outro != nome and nome in _imports(caminho, modulos)]
        assert not importadores, (
            "%s se declara script avulso mas e importado por %r - ou deixa de ser "
            "avulso, ou o import sai" % (nome, importadores))
