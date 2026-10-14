"""G132 - a peca declara a edicao que a SUA conta usou (regra revista no D236).

Historia: no G132 so dois pontos liam a chave e a regra era "peca sem conta
que troca declara 2014 com qualquer chave", com o carimbo do projeto dizendo
a composicao ("2014, exceto X pela 2023"). O D236 migrou a NBR 6118 inteira
para a 2023 + Emenda 1 (decisao do usuario em 2026-10-14): os pontos que
mudam leem a chave (MODULOS_COM_TROCA) e o resto foi relido na 2023 e e'
igual. Regra de agora: TODA peca declara a edicao do projeto - a declarada,
ou o padrao (2023 + Em1) quando ausente; a 2014 so' quando declarada. O
portao continua partindo da peca: folha que diz uma edicao num projeto em
outra reprova nomeando os dois lados.

Nao fazer: virar a chave em projeto do repo (a injecao e em copia na
memoria + tmp_path).
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

import edicao_nbr6118_g123 as fonte

D14 = "NBR 6118:2014"
D23 = "NBR 6118:2023 + Emenda 1:2026"


def test_01_fonte_peca_e_composicao_tabela_fechada():
    """Um assert so: edicao_da_peca x {ausente, 2014, 2023} x {troca ou nao};
    composicao = carimbo da edicao; confronto parte da peca."""
    quebras = []
    for projeto, troca, esperado in (
            (None, False, "2023+Em1"), (None, True, "2023+Em1"),
            ("2014", False, "2014"), ("2014", True, "2014"),
            ("2023+Em1", False, "2023+Em1"), ("2023+Em1", True, "2023+Em1")):
        if fonte.edicao_da_peca(projeto, troca) != esperado:
            quebras.append("peca(%r, %r)=%r, esperado %r"
                           % (projeto, troca,
                              fonte.edicao_da_peca(projeto, troca), esperado))
    for invalida in ("2015", "2023", "nbr-2023", ""):
        try:
            fonte.edicao_da_peca(invalida, True)
            quebras.append("peca(%r) devia levantar" % (invalida,))
        except ValueError:
            pass
    for ed in (None, "2014", "2023+Em1"):
        if fonte.carimbo_composicao(ed) != fonte.carimbo_edicao(ed):
            quebras.append("composicao %r != carimbo da edicao" % (ed,))
    if D23 not in fonte.carimbo_composicao("2023+Em1") or \
            D14 in fonte.carimbo_composicao("2023+Em1"):
        quebras.append("composicao 2023: %r" % (fonte.carimbo_composicao("2023+Em1"),))
    if tuple(fonte.MODULOS_COM_TROCA) != (("premoldado_nbr9062", "12.3.3"),
                                         ("compatibilizacao", "13.2.5.1"),
                                         ("pilar_concreto", "15.8.2"),
                                         ("pilar_concreto", "8.2.10.1"),
                                         ("fctm_nbr6118_g127", "8.2.5"),
                                         ("fundacao_sapata", "17.2.2"),
                                         ("laje_concreto", "19.4.1"),
                                         ("viga_protendida", "9.6.1.2")):
        quebras.append("MODULOS_COM_TROCA mudou: %r" % (fonte.MODULOS_COM_TROCA,))
    boa_2014 = fonte.carimbo_edicao("2014")
    boa_2023 = fonte.carimbo_edicao("2023+Em1")
    if not fonte.confronto_peca_conta(boa_2014, "2014", False)["OK"]:
        quebras.append("peca 2014 em projeto 2014 devia passar")
    if not fonte.confronto_peca_conta(boa_2023, None, False)["OK"]:
        quebras.append("peca 2023 sem chave (padrao) devia passar")
    r = fonte.confronto_peca_conta(boa_2023, "2014", False)
    if r["OK"]:
        quebras.append("folha 2023 em projeto 2014 devia reprovar")
    elif "2023+Em1" not in r["motivo"] or "2014" not in r["motivo"]:
        quebras.append("motivo nao nomeia os dois lados: %r" % (r["motivo"],))
    if fonte.confronto_peca_conta("concreto sem norma", "2023+Em1",
                                  False)["OK"]:
        quebras.append("peca sem declaracao devia reprovar")
    comp = fonte.carimbo_composicao("2023+Em1")
    if not fonte.contem_composicao(comp, "2023+Em1")["tem"]:
        quebras.append("composicao intacta devia passar no projeto")
    if fonte.contem_composicao(boa_2014, "2023+Em1")["tem"]:
        quebras.append("projeto 2023 com carimbo 2014 devia reprovar")
    assert not quebras, "G132 fonte:\n" + "\n".join(quebras)


def test_02_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: folha de projeto 2014 adulterada para 2023
    acusa; a intacta passa; carimbo do projeto adulterado acusa; invalida
    levanta."""
    quebras = []
    import desenho_pavimento as dp
    folha = ("PLANTA TESTE G132" + dp._sufixo_edicao("2014"))
    if not fonte.confronto_peca_conta(folha, "2014", False)["OK"]:
        quebras.append("folha real de projeto 2014 devia declarar 2014")
    adulterada = folha.replace(D14, D23)
    (tmp_path / "folha-adulterada.svg").write_text(adulterada, encoding="utf-8")
    r = fonte.confronto_peca_conta(
        (tmp_path / "folha-adulterada.svg").read_text(encoding="utf-8"),
        "2014", False)
    if r["OK"]:
        quebras.append("folha 2023 em projeto 2014 devia reprovar")
    comp = fonte.carimbo_composicao("2023+Em1")
    if fonte.contem_composicao(comp.replace(D23, D14), "2023+Em1")["tem"]:
        quebras.append("carimbo do projeto adulterado devia reprovar")
    if not fonte.contem_composicao(comp, "2023+Em1")["tem"]:
        quebras.append("composicao intacta devia passar")
    for fn in (lambda: fonte.edicao_da_peca("2015", True),
               lambda: fonte.carimbo_composicao("2015"),
               lambda: fonte.confronto_peca_conta(folha, "2015", True)):
        try:
            fn()
            quebras.append("edicao invalida devia levantar: %r" % (fn,))
        except ValueError:
            pass
    if not tmp_path.is_dir():
        quebras.append("tmp_path sumiu")
    assert not quebras, "G132 injecao:\n" + "\n".join(quebras)


def _furo_viga_hint():
    return {"direcao": "transversal", "d_furo_mm": 125.0,
            "h_viga_mm": 600.0, "dist_apoio_mm": 1300.0,
            "zona_tracao": True, "dist_face_mm": 60.0,
            "cobrimento_mm": 25.0, "furo_unico": True,
            "armadura_seccionada": False, "forma_furo": "circular"}


def test_03_toda_pendencia_declara_a_edicao_do_projeto():
    """Um assert so (funcoes reais): com 2014 declarada, toda categoria
    declara e cita 2014; com 2023 ou sem a chave, 2023 + Em1."""
    import compatibilizacao as cp

    quebras = []
    rep_viga = {"clashes": [{"a": "V1", "b": "T1",
                             "disciplinas": "concretoxhidraulica",
                             "tipos": "BeamxPipe", "vol_mm3": 1e5,
                             "esperado": False}]}
    hints_viga = {("V1", "T1", "BeamxPipe"): _furo_viga_hint()}
    rep_laje = {"clashes": [{"a": "L1", "b": "T1",
                             "disciplinas": "concretoxhidraulica",
                             "tipos": "SlabxPipe", "vol_mm3": 1e5,
                             "esperado": False}]}
    hints_laje = {("L1", "T1", "SlabxPipe"):
                  dict(_furo_viga_hint(), dim_abertura_mm=100.0,
                       vao_menor_mm=4000.0, laje_lisa=False)}
    hints_vert = {("V1", "T1", "BeamxPipe"):
                  {"vertical": True, "d_furo_mm": 50.0, "b_viga_mm": 300.0,
                   "dist_face_mm": 60.0, "cobrimento_mm": 25.0}}
    rep_mont = {"clashes": [{"a": "V1", "b": "T1",
                             "disciplinas": "concretoxhidraulica",
                             "tipos": "BeamxPipe", "vol_mm3": 1e5,
                             "esperado": True}]}
    for ed, esperado in (("2014", "2014"), ("2023+Em1", "2023+Em1"),
                         (None, "2023+Em1")):
        rot = fonte.rotulo_edicao(esperado)
        kw = {} if ed is None else {"edicao": ed}
        casos = [
            ("furo viga", cp.gerar_pendencias(rep_viga, cruzamentos=hints_viga, **kw)[0]),
            ("furo laje", cp.gerar_pendencias(rep_laje, cruzamentos=hints_laje, **kw)[0]),
            ("furo vertical", cp.gerar_pendencias(rep_viga, cruzamentos=hints_vert, **kw)[0]),
            ("conflito", cp.gerar_pendencias(rep_viga, **kw)[0]),
            ("montagem", cp.gerar_pendencias(rep_mont, **kw)[0]),
        ]
        for nome, pend in casos:
            if pend["edicao_6118"] != esperado:
                quebras.append("%s com %r=%r, esperado %r"
                               % (nome, ed, pend["edicao_6118"], esperado))
            fora = [c for c in pend["clausulas"] if "6118" in c and not c.startswith(rot)]
            if fora:
                quebras.append("%s com %r cita outra edicao: %r" % (nome, ed, fora))
    try:
        cp.gerar_pendencias(rep_viga, cruzamentos=hints_viga, edicao="2015")
        quebras.append("pendencia com edicao invalida devia levantar")
    except ValueError:
        pass
    assert not quebras, "G132 pendencias:\n" + "\n".join(quebras)


def _rodada_casa(tmp_path, edicao=None):
    """Casa de verdade (spec persistido) em tmp_path; a chave, quando dada,
    vai na copia em memoria, nunca no repo (molde G128 _rodada)."""
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    spec = g102._spec("casa")
    assert "norma_6118_edicao" not in spec, \
        "o repo nao declara a chave (Nao fazer do G132)"
    if edicao is not None:
        spec["norma_6118_edicao"] = edicao
    destino = str(tmp_path / ("run-g132-casa-%s" % (edicao or "ausente")))
    return run_project(spec, destino, dict(g102._OPCOES["casa"])), destino


def _pecas_casa(destino):
    import casa_residencial as adaptador
    pecas = {}
    for codigo, arquivo in sorted(dict(adaptador._PRANCHA_ARQUIVO_CASA).items()):
        if not codigo.startswith("PE-CO-"):
            continue
        with open(os.path.join(destino, "drawings", arquivo), encoding="utf-8") as fh:
            pecas[arquivo] = fh.read()
    for doc in ("pacote-legal.md", "caderno-encargos.md"):
        with open(os.path.join(destino, "documentos", doc), encoding="utf-8") as fh:
            pecas[doc] = fh.read()
    with open(os.path.join(destino, "reports", "adapter-result.json"),
              encoding="utf-8") as fh:
        pecas["adapter-result.json"] = fh.read()
    with open(os.path.join(destino, "coordination", "pendencias.json"),
              encoding="utf-8") as fh:
        pends = json.load(fh)
    return pecas, pends


def test_04_casa_real_com_2014_declarada_toda_peca_em_2014(tmp_path):
    """Casa de verdade com a 2014 DECLARADA: folhas, memorial da sapata,
    pacote, caderno e pendencias declaram 2014 e nao citam a 2023 (a chave
    chega a todas as contas pelo contexto das entradas)."""
    quebras = []
    _man, destino = _rodada_casa(tmp_path, edicao="2014")
    pecas, pends = _pecas_casa(destino)
    for arquivo, texto in sorted(pecas.items()):
        c = fonte.contem_declaracao(texto)
        if not c["tem"] or c["edicao"] != "2014":
            quebras.append("%s declara %r (esperado 2014)" % (arquivo, c["edicao"]))
    if "SAPATA - PARTE B (CONCRETO ARMADO) - " + D14 not in pecas["adapter-result.json"]:
        quebras.append("memorial da sapata sem o cabecalho em 2014")
    if not pends:
        quebras.append("casa real sem pendencias (mudou o clash?)")
    for p in pends:
        if p.get("edicao_6118") != "2014":
            quebras.append("%s declara %r (projeto 2014)" % (p.get("id"), p.get("edicao_6118")))
    assert not quebras, "G132 casa 2014:\n" + "\n".join(quebras)


def test_05_sem_chave_toda_peca_na_2023(tmp_path):
    """Sem a chave (D236): composicao == carimbo do padrao; peca == 2023 + Em1;
    a casa real declara 2023 + Em1 em toda peca e nao cita a 2014."""
    quebras = []
    if fonte.carimbo_composicao(None) != fonte.carimbo_edicao(None):
        quebras.append("composicao sem chave != carimbo do padrao")
    if fonte.edicao_da_peca(None, True) != "2023+Em1" \
            or fonte.edicao_da_peca(None, False) != "2023+Em1":
        quebras.append("peca sem chave != 2023+Em1")
    import desenho_pavimento as dp
    import desenho_fundacao_edificio as dfe
    import desenho_concreto as dc
    import pacote_legal as pl
    import caderno_encargos as ce
    s23 = " (" + D23 + ")"
    if dp._sufixo_edicao() != s23:
        quebras.append("sufixo pavimento: %r" % (dp._sufixo_edicao(),))
    if dfe._sufixo_edicao() != s23:
        quebras.append("sufixo fundacao: %r" % (dfe._sufixo_edicao(),))
    if dc._carimbo_edicao({"spec": {}}) != s23:
        quebras.append("carimbo desenho_concreto: %r" % (dc._carimbo_edicao({"spec": {}}),))
    if pl.gerar_pacote(["concreto"], spec={})["carimbo_edicao_6118"] != fonte.carimbo_edicao(None):
        quebras.append("pacote sem chave fora do carimbo do padrao")
    if ce.gerar_caderno(["concreto"])["linha_edicao_6118"] != fonte.carimbo_edicao(None):
        quebras.append("caderno sem chave fora do carimbo do padrao")
    _man, destino = _rodada_casa(tmp_path)
    pecas, pends = _pecas_casa(destino)
    for arquivo, texto in sorted(pecas.items()):
        c = fonte.contem_declaracao(texto)
        if not c["tem"] or c["edicao"] != "2023+Em1":
            quebras.append("%s declara %r (esperado 2023+Em1)" % (arquivo, c["edicao"]))
        if D14 in texto:
            quebras.append("%s sem chave citando 2014" % (arquivo,))
    for p in pends:
        if p.get("edicao_6118") != "2023+Em1":
            quebras.append("%s declara %r" % (p.get("id"), p.get("edicao_6118")))
    assert not quebras, "G132 sem chave:\n" + "\n".join(quebras)
