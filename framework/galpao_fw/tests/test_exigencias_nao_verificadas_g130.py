"""G130 - as 39 dividas que o cliente nao ve.

Medido (G125): ORFAS_TRIADAS tem 39 DIVIDAS com clausula - exigencias de
norma escritas e nao verificadas; zero mencoes (nome, clausula ou "nao
verificado") nos documentos entregues de rodada real de casa e predio.
Nao medido: o galpao; quais se aplicam a cada tipologia.

Entregue:
  1. FONTE UNICA (exigencias_nao_verificadas_g130.py, producao): a
     aplicabilidade por tipologia (casa/predio/galpao), com o motivo
     escrito onde nao se aplica. A clausula/motivo NAO sao copiados:
     sao lidos de ORFAS_TRIADAS ao vivo (divida nova sem triagem vira
     sem_triagem, nunca some em silencio).
  2. PACOTE: gerar_pacote ganha `tipologia` (ausente = a uniao; invalida
     levanta) e o markdown ganha a secao obrigatoria G130, sempre, com
     nome + clausula da fonte unica e a marca "não verificada pelo
     framework". Os 3 emissores passam a tipologia (casa/predio/galpao).
  3. PORTAO (test_01/02/03): rodada real das 3 tipologias (spec persistido,
     inalterado, em tmp_path): toda divida aplicavel esta no
     pacote-legal.md.
  4. INJECAO (test_04, tmp_path, nunca o repo): divida nova em ORFAS que
     nao chega ao pacote reprova; documento sem uma divida reprova
     nomeando; tipologia invalida levanta.
  5. BASELINE (test_05, nos dois sentidos): 39 dividas, 18/24/30 por
     tipologia, uniao 39; sem_triagem/mortas/sem_motivo/invalida vazios.
  6. USO (test_06): so pacote_legal importa a fonte (baseline nos dois
     sentidos); o pacote publica da fonte (sem literal copiado).

O que este goal NAO faz: implementar as verificacoes (cada uma e um goal
proprio) nem ligar constante em conta para tira-la da lista (Nao fazer do
goal). A producao so PUBLICA a divida.
"""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

import exigencias_nao_verificadas_g130 as lente


def _pacote_md(nome, tmp_path, opcoes=None):
    """Roda a tipologia de verdade (spec persistido, inalterado) e le o pacote.

    Devolve o texto do pacote-legal.md. O spec do repo nunca e mutado: a
    rodada escreve so em tmp_path."""
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    spec = g102._spec(nome)
    destino = str(tmp_path / ("run-g130-" + nome))
    opc = dict(opcoes) if opcoes is not None else dict(g102._OPCOES[nome])
    run_project(spec, destino, opc)
    caminho = os.path.join(destino, "documentos", "pacote-legal.md")
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def test_01_rodada_casa_toda_divida_aplicavel_no_pacote(tmp_path):
    """Casa real: as 18 aplicaveis estao no pacote-legal.md."""
    quebras = []
    try:
        texto = _pacote_md("casa", tmp_path)
    except Exception as exc:  # noqa: BLE001
        quebras.append("rodada casa falhou: %s: %s"
                       % (type(exc).__name__, exc))
        texto = ""
    if texto:
        conf = lente.confere_documento(texto, "casa")
        if not conf["OK"]:
            quebras.append("casa faltando=%r sem_triagem=%r"
                           % (conf["faltando"], conf["sem_triagem"]))
        if lente.MARCA_SECAO not in texto:
            quebras.append("casa sem a secao G130 no markdown")
        if lente.MARCA_ITEM not in texto:
            quebras.append("casa sem a marca 'nao verificada pelo framework'")
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G130 casa:\n" + "\n".join(quebras)


def test_02_rodada_predio_toda_divida_aplicavel_no_pacote(tmp_path):
    """Predio real: as 24 aplicaveis estao no pacote-legal.md."""
    quebras = []
    try:
        texto = _pacote_md("predio", tmp_path)
    except Exception as exc:  # noqa: BLE001
        quebras.append("rodada predio falhou: %s: %s"
                       % (type(exc).__name__, exc))
        texto = ""
    if texto:
        conf = lente.confere_documento(texto, "predio")
        if not conf["OK"]:
            quebras.append("predio faltando=%r sem_triagem=%r"
                           % (conf["faltando"], conf["sem_triagem"]))
        if lente.MARCA_SECAO not in texto:
            quebras.append("predio sem a secao G130 no markdown")
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G130 predio:\n" + "\n".join(quebras)


def test_03_rodada_galpao_toda_divida_aplicavel_no_pacote(tmp_path):
    """Galpao real (sem 2D, o pacote independe dele): as 30 no pacote."""
    quebras = []
    try:
        texto = _pacote_md("galpao", tmp_path,
                           opcoes={"generate_ifc": False,
                                   "generate_2d": False})
    except Exception as exc:  # noqa: BLE001
        quebras.append("rodada galpao falhou: %s: %s"
                       % (type(exc).__name__, exc))
        texto = ""
    if texto:
        conf = lente.confere_documento(texto, "galpao")
        if not conf["OK"]:
            quebras.append("galpao faltando=%r sem_triagem=%r"
                           % (conf["faltando"], conf["sem_triagem"]))
        if lente.MARCA_SECAO not in texto:
            quebras.append("galpao sem a secao G130 no markdown")
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G130 galpao:\n" + "\n".join(quebras)


def test_04_vermelho_por_injecao_divida_nova_nao_chega(tmp_path):
    """tmp_path, nunca o repo: divida nova sem triagem reprova; sem citacao
    reprova nomeando; tipologia invalida levanta em toda porta."""
    quebras = []
    import pacote_legal as pl
    import varredura_constantes_orfas as vco

    # Divida nova em ORFAS (copia em memoria, o repo intacto): sem entrada
    # em APLICABILIDADE ela vira sem_triagem e nao chega a nenhum pacote.
    tri_nova = dict(vco.ORFAS_TRIADAS)
    tri_nova[("modulo_novo_g130.py", "CONSTANTE_NOVA_G130")] = (
        "DIVIDA", "motivo injetado", "NBR 9999 9.9.9")
    base = lente.confere_aplicabilidade(tri_nova)
    if ("modulo_novo_g130.py", "CONSTANTE_NOVA_G130") not in base["sem_triagem"]:
        quebras.append("divida nova devia virar sem_triagem")
    if base["OK"]:
        quebras.append("confere com divida nova devia reprovar")
    pac = pl.gerar_pacote(["concreto"], tipologia="casa")
    md = pl.markdown(pac)
    conf = lente.confere_documento(md, "casa", triadas=tri_nova)
    if conf["OK"]:
        quebras.append("documento sem a divida nova devia reprovar")
    if ("modulo_novo_g130.py", "CONSTANTE_NOVA_G130") not in conf["faltando"] \
            and ("modulo_novo_g130.py", "CONSTANTE_NOVA_G130") not in conf["sem_triagem"]:
        quebras.append("injecao nao nomeada: %r" % (conf,))
    # Documento com uma divida arrancada reprova nomeando a que falta.
    arrancado = md.replace("FVK_ARMADA_COEF", "DIVIDA_REMOVIDA_G130")
    conf_arr = lente.confere_documento(arrancado, "casa")
    if conf_arr["OK"]:
        quebras.append("documento sem FVK_ARMADA_COEF devia reprovar")
    elif ("alvenaria_estrutural.py", "FVK_ARMADA_COEF") not in conf_arr["faltando"]:
        quebras.append("faltando nao nomeia a divida: %r"
                       % (conf_arr["faltando"],))
    # Intacto passa (o instrumento acusa quando ha o que acusar).
    if not lente.confere_documento(md, "casa")["OK"]:
        quebras.append("documento intacto devia passar")
    # Tipologia invalida levanta em toda porta nova (nunca vira outra).
    for fn in (lambda: lente.normaliza_tipologia("sobrado"),
               lambda: lente.exigencias_para_tipologia("sobrado"),
               lambda: lente.nao_aplicaveis_para_tipologia("sobrado"),
               lambda: lente.confere_documento(md, "sobrado"),
               lambda: pl.gerar_pacote(["concreto"], tipologia="sobrado")):
        try:
            fn()
            quebras.append("tipologia invalida devia levantar: %r" % (fn,))
        except ValueError:
            pass
    # "edificio" e alias de "predio" (o nome vivo e "predio").
    if lente.normaliza_tipologia("edificio") != "predio":
        quebras.append("alias edificio devia canonizar para predio")
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G130 injecao:\n" + "\n".join(quebras)


def test_05_baseline_nos_dois_sentidos():
    """39 dividas, 18/24/30 por tipologia, uniao 39; triagem sem buraco."""
    quebras = []
    import varredura_constantes_orfas as vco

    if len(vco.ORFAS_TRIADAS) != 39:
        quebras.append("triadas=%d, esperado 39" % len(vco.ORFAS_TRIADAS))
    cont = {tip: len(lente.exigencias_para_tipologia(tip))
            for tip in lente.TIPOLOGIAS}
    if cont != {"casa": 18, "predio": 24, "galpao": 30}:
        quebras.append("contagem por tipologia=%r, esperado casa=18 "
                       "predio=24 galpao=30" % (cont,))
    if len(lente.exigencias_para_tipologia(None)) != 39:
        quebras.append("uniao sem tipologia devia ter 39")
    base = lente.confere_aplicabilidade()
    if not base["OK"]:
        quebras.append("aplicabilidade com buraco: %r" % (base,))
    # A que nao se aplica diz por que, no codigo: nenhum motivo vazio.
    for tip in lente.TIPOLOGIAS:
        for item in lente.nao_aplicaveis_para_tipologia(tip):
            if not (item["por_que_nao_aplica"] or "").strip():
                quebras.append("sem motivo: %s::%s fora de %s"
                               % (item["arquivo"], item["nome"], tip))
    assert not quebras, "G130 baseline:\n" + "\n".join(quebras)


def test_06_fonte_unica_uso_e_publicacao():
    """Um assert so: o pacote publica da fonte (sem literal); so ele importa."""
    quebras = []
    import pacote_legal as pl

    uso = lente.confere_uso_exigencias()
    if not uso["OK"]:
        quebras.append("uso fora do baseline: %r" % (uso,))
    # O pacote publica da fonte: sem tipologia = a uniao; com tipologia = o
    # recorte; a linha carrega nome + endereco da fonte unica.
    pac_u = pl.gerar_pacote(["concreto"])
    if len(pac_u.get("exigencias_nao_verificadas") or []) != 39:
        quebras.append("pacote sem tipologia devia trazer a uniao (39): %r"
                       % (len(pac_u.get("exigencias_nao_verificadas") or []),))
    for tip, n in (("casa", 18), ("predio", 24), ("galpao", 30)):
        pac = pl.gerar_pacote(["concreto"], tipologia=tip)
        if len(pac.get("exigencias_nao_verificadas") or []) != n:
            quebras.append("pacote %s=%d, esperado %d"
                           % (tip, len(pac.get("exigencias_nao_verificadas") or []), n))
        md = pl.markdown(pac)
        if lente.MARCA_SECAO not in md or lente.MARCA_ITEM not in md:
            quebras.append("pacote %s sem secao/marca G130" % tip)
        for it in pac["exigencias_nao_verificadas"]:
            if it["nome"] not in md or it["endereco"] not in md:
                quebras.append("pacote %s sem %s::%s no markdown"
                               % (tip, it["arquivo"], it["nome"]))
                break
    assert not quebras, "G130 fonte unica:\n" + "\n".join(quebras)
