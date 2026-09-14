"""G132 - a edicao que se declara inteira trocando dois pontos.

Medido (G131, remedido no G132 nas 3 tipologias com `norma_6118_edicao`
"2023+Em1" injetada em memoria, 2026-09-13): as folhas PE-CO e o caderno
dizem 2023+Em1 enquanto o memorial da sapata (adapter-result.json) diz
2014 - e o memorial esta certo: nenhuma conta da casa troca com a chave.
Casa: 4 folhas + pacote + caderno em 2023, 61 pendencias de conflito em
2023, sapata em 2014. Predio: 4 folhas + pacote + caderno em 2023, 126
furo_previsto em 2023 (81 de laje 13.2.5.2 sem troca + 45 de viga
13.2.5.1 COM troca), sapata em 2014. Galpao: 2 folhas + pacote + caderno
em 2023, 688 conflito + 282 montagem em 2023. So 2 pontos leem a chave
(edicao_nbr6118_g123.MODULOS_COM_TROCA); todo o resto calcula pela 2014.

Entregue (tudo da fonte unica edicao_nbr6118_g123):
  1. PECA: edicao_da_peca (a edicao que a SUA conta usou; sem troca, 2014
     com qualquer chave) - folhas de desenho, quadro de aco e pendencias
     sem troca declaram por ela; os 10 memoriais ja declaravam (no-arg).
  2. PROJETO: carimbo_composicao (quais itens seguem a 2023+Em1, o resto
     pela 2014; sem a chave, o carimbo de hoje byte a byte) - pacote,
     caderno, memorial/relatorio do galpao e prancha techdraw.
  3. PORTAO: confronto_peca_conta (parte da conta, nao da chave) +
     contem_composicao (o projeto). Folha 2023 numa peca sem troca
     reprova nomeando os dois lados.
  4. COMPAT: edicao_6118 por pendencia (so furo transversal em viga
     segue a chave; laje/vertical/conflito/montagem declaram 2014).

Nao fazer do goal: migrar mais itens para a 2023; virar a chave em
projeto nenhum do repo (a injecao e em copia na memoria + tmp_path).
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


def test_01_fonte_peca_e_composicao_tabela_fechada():
    """Um assert so: edicao_da_peca x {ausente, 2014, 2023} x {troca ou
    nao}; composicao byte-identica sem a chave e composta com a chave
    (itens daqui, de MODULOS_COM_TROCA); confronto parte da conta."""
    quebras = []
    # Peca: sem a chave, 2014 nos dois casos; com a chave, so troca segue.
    for projeto, troca, esperado in (
            (None, False, "2014"), (None, True, "2014"),
            ("2014", False, "2014"), ("2014", True, "2014"),
            ("2023+Em1", False, "2014"), ("2023+Em1", True, "2023+Em1")):
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
    # Composicao: sem a chave (ou 2014), o carimbo de hoje byte a byte.
    if fonte.carimbo_composicao(None) != fonte.carimbo_edicao(None):
        quebras.append("composicao sem chave mudou o carimbo")
    if fonte.carimbo_composicao("2014") != fonte.carimbo_edicao("2014"):
        quebras.append("composicao 2014 mudou o carimbo")
    comp = fonte.carimbo_composicao("2023+Em1")
    for pedaco in (fonte.DECLARACAO_2014, fonte.DECLARACAO_2023_EM1,
                   "12.3.3 (premoldado_nbr9062)",
                   "13.2.5.1 (compatibilizacao)",
                   "edicao declarada no projeto: 2023+Em1"):
        if pedaco not in comp:
            quebras.append("composicao 2023 sem %r: %r" % (pedaco, comp))
    # A lista de itens vem de MODULOS_COM_TROCA (uma fonte so).
    if tuple(fonte.MODULOS_COM_TROCA) != (("premoldado_nbr9062", "12.3.3"),
                                         ("compatibilizacao", "13.2.5.1")):
        quebras.append("MODULOS_COM_TROCA mudou: %r" % (fonte.MODULOS_COM_TROCA,))
    # Confronto: parte da conta, nao da chave.
    boa_2014 = fonte.carimbo_edicao("2014")
    boa_2023 = fonte.carimbo_edicao("2023+Em1")
    if not fonte.confronto_peca_conta(boa_2014, "2023+Em1", False)["OK"]:
        quebras.append("peca 2014 sem troca com chave 2023 devia passar")
    r = fonte.confronto_peca_conta(boa_2023, "2023+Em1", False)
    if r["OK"]:
        quebras.append("folha 2023 em peca sem troca devia reprovar")
    elif "2023+Em1" not in r["motivo"] or "2014" not in r["motivo"]:
        quebras.append("motivo nao nomeia os dois lados: %r" % (r["motivo"],))
    if not fonte.confronto_peca_conta(boa_2023, "2023+Em1", True)["OK"]:
        quebras.append("peca 2023 com troca devia passar")
    if fonte.confronto_peca_conta("concreto sem norma", "2023+Em1",
                                  False)["OK"]:
        quebras.append("peca sem declaracao devia reprovar")
    if not fonte.contem_composicao(comp, "2023+Em1")["tem"]:
        quebras.append("composicao intacta devia passar no projeto")
    if fonte.contem_composicao(boa_2014, "2023+Em1")["tem"]:
        quebras.append("projeto 2023 sem composicao devia reprovar")
    assert not quebras, "G132 fonte:\n" + "\n".join(quebras)


def test_02_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: 2023 colada numa peca sem troca acusa; a
    intacta passa; composicao adulterada acusa; invalida levanta."""
    quebras = []
    # Folha real de desenho (funcao real) com a chave: declara 2014.
    import desenho_pavimento as dp
    folha = ("PLANTA TESTE G132" + dp._sufixo_edicao("2023+Em1"))
    if not fonte.confronto_peca_conta(folha, "2023+Em1", False)["OK"]:
        quebras.append("folha real sem troca devia declarar 2014")
    # Adulterada para 2023: o confronto acusa nomeando.
    adulterada = folha.replace(fonte.DECLARACAO_2014,
                               fonte.DECLARACAO_2023_EM1)
    (tmp_path / "folha-adulterada.svg").write_text(adulterada,
                                                   encoding="utf-8")
    r = fonte.confronto_peca_conta(
        (tmp_path / "folha-adulterada.svg").read_text(encoding="utf-8"),
        "2023+Em1", False)
    if r["OK"]:
        quebras.append("folha 2023 em peca sem troca devia reprovar")
    # Composicao adulterada (saiu o trecho dos itens): o projeto acusa.
    comp = fonte.carimbo_composicao("2023+Em1")
    sem_itens = comp.replace("12.3.3 (premoldado_nbr9062) e ", "")
    if fonte.contem_composicao(sem_itens, "2023+Em1")["tem"]:
        quebras.append("composicao sem os itens devia reprovar")
    if not fonte.contem_composicao(comp, "2023+Em1")["tem"]:
        quebras.append("composicao intacta devia passar")
    # Invalida levanta nas tres portas novas.
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


def test_03_conta_por_pendencia_so_furo_em_viga_segue_a_chave():
    """Um assert so (funcoes reais): com a chave, so o furo transversal em
    viga declara 2023+Em1; laje, vertical, conflito e montagem declaram
    2014; sem a chave, tudo 2014; invalida levanta."""
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
    casos = [
        ("furo viga", cp.gerar_pendencias(
            rep_viga, cruzamentos=hints_viga, edicao="2023+Em1")[0],
         "2023+Em1"),
        ("furo laje", cp.gerar_pendencias(
            rep_laje, cruzamentos=hints_laje, edicao="2023+Em1")[0],
         "2014"),
        ("furo vertical", cp.gerar_pendencias(
            rep_viga, cruzamentos=hints_vert, edicao="2023+Em1")[0],
         "2014"),
        ("conflito", cp.gerar_pendencias(rep_viga, edicao="2023+Em1")[0],
         "2014"),
        ("montagem", cp.gerar_pendencias(rep_mont, edicao="2023+Em1")[0],
         "2014"),
    ]
    for nome, pend, esperado in casos:
        if pend["edicao_6118"] != esperado:
            quebras.append("%s com chave=%r, esperado %r"
                           % (nome, pend["edicao_6118"], esperado))
    # Sem a chave, tudo 2014 (o comportamento de hoje).
    for nome, rep, hints in (("viga", rep_viga, hints_viga),
                             ("laje", rep_laje, hints_laje)):
        p = cp.gerar_pendencias(rep, cruzamentos=hints)[0]
        if p["edicao_6118"] != "2014":
            quebras.append("%s sem chave=%r, esperado 2014"
                           % (nome, p["edicao_6118"]))
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


def test_04_casa_real_com_a_chave_sem_contradicao(tmp_path):
    """A contradicao medida no G131, refeita: com a chave, folhas e
    memorial da sapata declaram 2014 (conta), pacote e caderno trazem a
    composicao (projeto), pendencias de conflito declaram 2014."""
    import casa_residencial as adaptador

    quebras = []
    _man, destino = _rodada_casa(tmp_path, edicao="2023+Em1")
    # Folhas PE-CO: peca sem troca declara 2014 (portao da conta).
    for codigo, arquivo in sorted(dict(
            adaptador._PRANCHA_ARQUIVO_CASA).items()):
        if not codigo.startswith("PE-CO-"):
            continue
        caminho = os.path.join(destino, "drawings", arquivo)
        if not os.path.isfile(caminho):
            quebras.append("%s nao saiu" % arquivo)
            continue
        with open(caminho, encoding="utf-8") as fh:
            r = fonte.confronto_peca_conta(fh.read(), "2023+Em1", False)
        if not r["OK"]:
            quebras.append("%s: %s" % (arquivo, r["motivo"]))
    # Memorial da sapata no adapter-result: 2014 (estava certo, continua).
    caminho = os.path.join(destino, "reports", "adapter-result.json")
    with open(caminho, encoding="utf-8") as fh:
        resultado = fh.read()
    if "SAPATA - PARTE B (CONCRETO ARMADO) - NBR 6118:2014" not in resultado:
        quebras.append("memorial da sapata sem o cabecalho em 2014")
    if "NBR 6118:2023" in resultado:
        quebras.append("memorial da sapata com 2023 (nenhuma conta troca)")
    # Pacote e caderno: a composicao do projeto (contem as duas, de
    # proposito: o confronto por peca nao vale aqui).
    for doc in ("pacote-legal.md", "caderno-encargos.md"):
        caminho = os.path.join(destino, "documentos", doc)
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read()
        if not fonte.contem_composicao(texto, "2023+Em1")["tem"]:
            quebras.append("%s sem a composicao 2023" % doc)
        if fonte.confronto_peca_conta(texto, "2023+Em1", False)["OK"]:
            quebras.append("%s passa no confronto de peca "
                           "(composicao nao e peca)" % doc)
    # Pendencias: a casa real so tem conflito (sem conta que troca).
    caminho = os.path.join(destino, "coordination", "pendencias.json")
    with open(caminho, encoding="utf-8") as fh:
        pends = json.load(fh)
    if not pends:
        quebras.append("casa real sem pendencias (mudou o clash?)")
    for p in pends:
        if p.get("categoria") != "conflito":
            quebras.append("%s categoria %r (medido: so conflito)"
                           % (p.get("id"), p.get("categoria")))
        if p.get("edicao_6118") != "2014":
            quebras.append("%s declara %r (conflito nao troca)"
                           % (p.get("id"), p.get("edicao_6118")))
    assert not quebras, "G132 casa:\n" + "\n".join(quebras)


def test_05_sem_chave_saida_de_hoje_byte_identica(tmp_path):
    """Sem a chave: composicao == carimbo de hoje byte a byte; peca ==
    2014; a casa real declara 2014 em toda peca e nao cita 2023."""
    quebras = []
    if fonte.carimbo_composicao(None) != fonte.carimbo_edicao(None):
        quebras.append("composicao sem chave != carimbo de hoje")
    if fonte.edicao_da_peca(None, True) != "2014" \
            or fonte.edicao_da_peca(None, False) != "2014":
        quebras.append("peca sem chave != 2014")
    # Os literais de hoje, escritos a mao aqui (contra assercao
    # tautologica): a fonte sem a chave rende cada um byte a byte.
    import desenho_pavimento as dp
    import desenho_fundacao_edificio as dfe
    import desenho_concreto as dc
    import pacote_legal as pl
    import caderno_encargos as ce
    if dp._sufixo_edicao() != " (NBR 6118:2014)":
        quebras.append("sufixo pavimento mudou: %r" % (dp._sufixo_edicao(),))
    if dfe._sufixo_edicao() != " (NBR 6118:2014)":
        quebras.append("sufixo fundacao mudou: %r" % (dfe._sufixo_edicao(),))
    if dp._subtitulo_pilares() != dp._SUBTITULO_PILARES:
        quebras.append("subtitulo default mudou")
    r0 = {"spec": {}}
    if dc._carimbo_edicao(r0) != " (NBR 6118:2014)":
        quebras.append("carimbo desenho_concreto mudou: %r"
                       % (dc._carimbo_edicao(r0),))
    pac0 = pl.gerar_pacote(["concreto"], spec={})
    if pac0["carimbo_edicao_6118"] != fonte.carimbo_edicao(None):
        quebras.append("pacote sem chave mudou o carimbo")
    cad0 = ce.gerar_caderno(["concreto"])
    if cad0["linha_edicao_6118"] != fonte.carimbo_edicao(None):
        quebras.append("caderno sem chave mudou a linha")
    # Integracao: a casa real sem a chave declara 2014 em toda peca.
    import casa_residencial as adaptador
    _man, destino = _rodada_casa(tmp_path)
    pecas = {}
    for _codigo, arquivo in sorted(dict(
            adaptador._PRANCHA_ARQUIVO_CASA).items()):
        if not _codigo.startswith("PE-CO-"):
            continue
        with open(os.path.join(destino, "drawings", arquivo),
                  encoding="utf-8") as fh:
            pecas[arquivo] = fh.read()
    for doc in ("pacote-legal.md", "caderno-encargos.md"):
        with open(os.path.join(destino, "documentos", doc),
                  encoding="utf-8") as fh:
            pecas[doc] = fh.read()
    for arquivo, texto in sorted(pecas.items()):
        c = fonte.contem_declaracao(texto)
        if not c["tem"] or c["edicao"] != "2014":
            quebras.append("%s declara %r (esperado 2014)"
                           % (arquivo, c["edicao"]))
        if "2023" in texto:
            quebras.append("%s sem chave citando 2023" % (arquivo,))
    assert not quebras, "G132 byte-identico:\n" + "\n".join(quebras)
