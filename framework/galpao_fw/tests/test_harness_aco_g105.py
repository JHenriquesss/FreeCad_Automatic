# ============================================================================
# test_harness_aco_g105.py - G105: o harness de medicao por prancha existe,
# cobre o fonte e reprova prancha mais lenta que o orcamento.
# Nao roda freecad.exe: confere registro x fonte (AST + assinaturas),
# baseline nos dois sentidos e vermelho por injecao em tmp_path (convenção
# 2: o repo vivo nunca e mutado). Os orcamentos aqui sao FIXTURE sintetica
# em tmp_path, nao medicao: os tempos reais ficam not_available em
# TEMPOS_G105 ate a primeira rodada manual com modelo FCStd.
# ============================================================================
"""Portao G105: harness por prancha do executivo de aco."""

import inspect
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import techdraw_exec as TD
import tools_harness_aco_por_prancha as H


def test_01_portao_registro_cobre_fonte():
    """Cada entrada do registro existe no fonte com a assinatura certa; cada
    construtor de prancha do fonte tem entrada aqui. Um assert so (G97)."""
    lados = []
    for p in H.PRANCHAS:
        fn = getattr(TD, p["construtor"], None)
        if fn is None:
            lados.append("construtor sumiu do fonte: %s" % p["construtor"])
            continue
        n_params = len(inspect.signature(fn).parameters)
        if n_params != p["nargs"]:
            lados.append("%s: fonte tem %d params, registro diz %d"
                         % (p["chave"], n_params, p["nargs"]))
        if "prefixo_ligacao" in p:
            pref = TD.LIGACOES[p["indice_ligacao"]][0]
            if pref != p["prefixo_ligacao"]:
                lados.append("%s: LIGACOES[%d]=%s, registro diz %s"
                             % (p["chave"], p["indice_ligacao"], pref,
                                p["prefixo_ligacao"]))
    construtores_fonte = {n for n, o in vars(TD).items()
                          if n.startswith("_pr_") and callable(o)}
    construtores_reg = {p["construtor"] for p in H.PRANCHAS}
    for nome in sorted(construtores_fonte - construtores_reg):
        lados.append("construtor do fonte sem registro: %s" % nome)
    chaves_lig = [p["chave"] for p in H.PRANCHAS
                  if p["construtor"] == "_pr_ligacoes"]
    if len(chaves_lig) != len(TD.LIGACOES):
        lados.append("detalhes %d != LIGACOES %d"
                     % (len(chaves_lig), len(TD.LIGACOES)))
    if "PE14_DET_CONSOLE" not in {p["chave"] for p in H.PRANCHAS} or \
            "PE14_CROQUIS" not in {p["chave"] for p in H.PRANCHAS}:
        lados.append("colisao PE14 sem as duas chaves pelo nome completo")
    assert not lados, "registro G105 fora do fonte:\n" + "\n".join(lados)


def test_02_baseline_g105_nos_dois_sentidos():
    """Sem baseline congelado nos dois sentidos o harness e relatorio, nao
    portao: pagina nova cairia no meio do conhecido com a suite verde."""
    agora = {p["chave"]: p["classe"] for p in H.PRANCHAS}
    lados = []
    if set(agora) != set(H.BASELINE_G105):
        lados.append("chave nova/sumida sem triagem G105: %r"
                     % sorted(set(agora) ^ set(H.BASELINE_G105)))
    for nome in sorted(set(agora) | set(H.BASELINE_G105)):
        if agora.get(nome) != H.BASELINE_G105.get(nome):
            lados.append("G105 mudou em %r: conhecido %r, agora %r"
                         % (nome, H.BASELINE_G105.get(nome),
                            agora.get(nome)))
    if set(H.TEMPOS_G105) != set(H.BASELINE_G105):
        lados.append("TEMPOS_G105 fora do registro: %r"
                     % sorted(set(H.TEMPOS_G105) ^ set(H.BASELINE_G105)))
    assert not lados, "baseline G105 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_estouro_de_orcamento(tmp_path):
    """Prancha mais lenta que o orcamento reprova; o caso bom passa."""
    orc = {p["chave"]: 100.0 for p in H.PRANCHAS}
    bom = {p["chave"]: {"t_build": 10.0, "t_hlr": 40.0,
                        "t_cotas": 5.0, "t_export": 5.0}
           for p in H.PRANCHAS}
    bom["PE09_QUADROS"] = {"t_build": 5.0, "t_hlr": 0.0,
                           "t_cotas": 0.0, "t_export": 5.0}
    (tmp_path / "orc.json").write_text(json.dumps(orc), encoding="utf-8")
    (tmp_path / "bom.json").write_text(json.dumps(bom), encoding="utf-8")
    orc_lido = json.loads((tmp_path / "orc.json").read_text(encoding="utf-8"))
    bom_lido = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))
    assert H.conferir_orcamento(bom_lido, orc_lido)["OK"] is True
    lento = dict(bom_lido)
    lento["PE04_PORTICO"] = {"t_build": 10.0, "t_hlr": 400.0,
                             "t_cotas": 5.0, "t_export": 5.0}
    (tmp_path / "lento.json").write_text(json.dumps(lento), encoding="utf-8")
    lento_lido = json.loads(
        (tmp_path / "lento.json").read_text(encoding="utf-8"))
    r = H.conferir_orcamento(lento_lido, orc_lido)
    assert r["OK"] is False and len(r["estouros"]) == 1


def test_04_vermelho_por_injecao_prancha_faltando(tmp_path):
    """Medido sem uma prancha do registro acusa faltando (nao some)."""
    (tmp_path / "vazio.json").write_text(json.dumps({}), encoding="utf-8")
    med = json.loads((tmp_path / "vazio.json").read_text(encoding="utf-8"))
    r = H.conferir_orcamento(med, {})
    assert r["OK"] is False and set(r["faltando"]) == set(H.BASELINE_G105)


def test_05_vermelho_por_injecao_boot_sem_despacho(tmp_path):
    """O boot de uma prancha referencia o construtor dela e so ele; boot
    com o despacho trocado nao fecha contra o registro."""
    boot = H.montar_boot_por_prancha({"fcstd": "x", "out": "y"},
                                     "LIGACOES = [(1,2,3,4,5,6,7,8)]\n",
                                     "PE13_DET_CLIPE_GIRT",
                                     str(tmp_path / "t.json"))
    assert "_detalhe_ligacao" in boot and "CLIPE_GIRT" in boot
    assert "_pr_portico" not in boot
    ruim = boot.replace("_detalhe_ligacao", "_pr_portico")
    assert "_detalhe_ligacao" not in ruim


def test_06_esquema_do_medido_recusa_tempo_negativo(tmp_path):
    """Tempo negativo ou nao numerico e problema de esquema, nao numero."""
    res = {"prancha": "PE09_QUADROS", "t_build": -1.0, "t_hlr": 0.0,
           "t_cotas": 0.0, "t_export": "rapido"}
    (tmp_path / "tempo_PE09_QUADROS.json").write_text(
        json.dumps(res), encoding="utf-8")
    _, problemas = H.conferir_medido(
        str(tmp_path / "tempo_PE09_QUADROS.json"))
    assert len(problemas) == 2
