"""D165 - o executivo de aco COMPLETO do galpao, portao de auditoria.

O G102 roda o galpao sem o executivo de aco (executivo_aco=False): com ele
o portao era sorteio de relogio (D164). O executivo completo mora aqui, com
prazo que cabe no tempo medido, e roda na AUDITORIA do lote (serial, com
GALPAO_AUDITORIA=1) - fora disso o teste sai pulado com o motivo escrito.

Medido (2026-09-13, spec projects/galpao-tp-g95 turnkey.aco, maquina de
8 GB, freecad.exe sozinho): rodar_tudo com 3D + executivo em 1038,9 s,
executivo ok=True, 15 PDFs em pranchas/. So 3 tem codigo no indice
(`galpao_adapter._PRANCHA_ARQUIVO_GALPAO`): PE01_COBERTURA, PE04_PORTICO,
PE07_DET_JOELHO. As outras 12 saem sem codigo - o G137 da codigo a cada uma
e esvazia SEM_CODIGO_ACO. Baseline nos dois sentidos: prancha nova sem
codigo reprova; entrada da baseline que ganhou codigo ou sumiu do disco
reprova (nome morto).
"""
import glob
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
REPO = os.path.dirname(os.path.dirname(GALPAO))

ENV_AUDITORIA = "GALPAO_AUDITORIA"
TIMEOUT_3D_SEG = 900
TIMEOUT_EXEC_SEG = 2400
CUSTO_MEDIDO_SEG = 1038.9
CUSTO_MEDIDO_EM = "2026-09-13"

# arquivo -> motivo (medido no D165; o G137 da codigo e remove daqui)
SEM_CODIGO_ACO = {
    "PE02_FUNDACOES.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE03_ELEVACOES.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE05_CONTRAVENTAMENTO.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE06_DET_BASE.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE08_FECHAMENTO.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE09_QUADROS.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE10_DET_CUMEEIRA.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE11_DET_GUSSET_COB.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE12_DET_GUSSET_PAR.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE13_DET_CLIPE_GIRT.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE14_CROQUIS.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
    "PE16_MONTAGEM.pdf": "emitida pelo techdraw_exec sem codigo no indice (G137)",
}


def conferir_pranchas_aco(pdfs, mapa_arquivos, sem_codigo):
    """[mensagens]: vazio = cada prancha emitida tem codigo ou triagem."""
    quebras = []
    emitidas = set(pdfs)
    for pdf in sorted(emitidas):
        if pdf not in mapa_arquivos and pdf not in sem_codigo:
            quebras.append("%s emitida sem codigo e sem triagem" % pdf)
    for pdf, motivo in sorted(sem_codigo.items()):
        if not (motivo or "").strip():
            quebras.append("%s na baseline sem motivo" % pdf)
        if pdf in mapa_arquivos:
            quebras.append("%s ganhou codigo e segue na baseline (nome morto)" % pdf)
        elif pdf not in emitidas:
            quebras.append("%s na baseline e nao emitida (nome morto)" % pdf)
    return quebras


def test_01_conferencia_vermelha_nos_dois_sentidos():
    mapa = {"A.pdf"}
    casos = [
        (["A.pdf", "B.pdf"], {"B.pdf": "triada"}, 0),
        (["A.pdf", "B.pdf", "C.pdf"], {"B.pdf": "triada"}, 1),   # nova sem codigo
        (["A.pdf"], {"B.pdf": "triada"}, 1),                     # sumiu do disco
        (["A.pdf", "B.pdf"], {"B.pdf": " "}, 1),                 # sem motivo
        (["A.pdf"], {"A.pdf": "triada"}, 1),                     # ganhou codigo
    ]
    obtido = [len(conferir_pranchas_aco(p, mapa, s)) for p, s, _n in casos]
    assert obtido == [n for _p, _s, n in casos], obtido


@pytest.mark.skipif(os.environ.get(ENV_AUDITORIA) != "1",
                    reason="executivo de aco completo (~17 min, freecad.exe): "
                           "portao da auditoria do lote - rode com "
                           "GALPAO_AUDITORIA=1, serial (D165)")
def test_02_executivo_aco_completo_emite_e_cada_prancha_tem_codigo(tmp_path):
    import time

    import galpao_adapter as ga
    import rodar_projeto as RP

    with open(os.path.join(REPO, "projects", "galpao-tp-g95",
                           "project-spec.json"), encoding="utf-8") as fh:
        spec = json.load(fh)
    inicio = time.perf_counter()
    r = RP.rodar_tudo(dict(spec["turnkey"]["aco"]), out_dir=str(tmp_path),
                      com_3d=True, com_executivo=True, gerar_pdf=False,
                      gerar_dossie=False, verbose=False,
                      timeout_3d=TIMEOUT_3D_SEG, timeout_exec=TIMEOUT_EXEC_SEG)
    segundos = time.perf_counter() - inicio
    print("CUSTO_D165 executivo_aco_completo=%.1fs" % segundos)
    ex = r.get("executivo") or {}
    quebras = []
    if ex.get("ok") is not True:
        quebras.append("executivo nao terminou: %r" % ({k: ex.get(k) for k in
                                                        ("ok", "erro")},))
    pdfs = sorted(os.path.basename(p) for p in
                  glob.glob(os.path.join(str(tmp_path), "pranchas", "*.pdf")))
    quebras.extend(conferir_pranchas_aco(
        pdfs, set(ga._PRANCHA_ARQUIVO_GALPAO.values()), SEM_CODIGO_ACO))
    assert not quebras, "D165 executivo de aco:\n" + "\n".join(quebras)
