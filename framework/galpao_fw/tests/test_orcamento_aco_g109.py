# ============================================================================
# test_orcamento_aco_g109.py - G109: o numero por prancha do aco existe e o
# orcamento congelado reprova estouro. Os numeros viera da rodada manual
# 2026-09-11 (galpao-ufpe, FCStd 2,3 MB); os tetos sao manuais com folga e o
# teste VERIFICA a folga em vez de deriva-la (convencao 5). G118 (2026-09-12)
# mediu a PE05 que faltava (mesmo modelo/maquina): o portao agora declara so
# as duas condicionais sem numero. Vermelho por injecao em tmp_path; o repo
# vivo nunca e mutado.
# ============================================================================
"""Portao G109: orcamento por prancha do executivo de aco."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import tools_harness_aco_por_prancha as H


def _totais(medidos):
    return {c: round(sum(m.get(k) or 0.0 for k in H.TEMPO_KEYS), 1)
            for c, m in medidos.items()}


def test_01_medidos_g109_parseiam_sem_problema(tmp_path):
    """Cada prancha medida fecha no esquema do conferir_medido (parse real)."""
    for chave, med in H.MEDIDOS_G109.items():
        doc = {"prancha": chave, "ok": True, "motivo": ""}
        doc.update(med)
        p = tmp_path / ("tempo_%s.json" % chave)
        p.write_text(json.dumps(doc), encoding="utf-8")
        _, problemas = H.conferir_medido(str(p))
        assert problemas == [], "%s: %r" % (chave, problemas)


def test_02_orcamento_cobre_medidos_sem_faltando(tmp_path):
    """Teto manual acima do total medido em toda prancha com numero; o portao
    passa sem estouros nem faltando e declara so as duas condicionais sem
    numero (G118 mediu a PE05 que o G109 declarava em faltando)."""
    for chave, med in H.MEDIDOS_G109.items():
        teto = H.ORCAMENTO_G109.get(chave)
        if teto is None:
            continue
        total = sum(med.get(k) or 0.0 for k in H.TEMPO_KEYS)
        assert teto > total, "%s: teto %s sem folga sobre %.1f" % (
            chave, teto, total)
    r = H.conferir_orcamento(dict(H.MEDIDOS_G109), dict(H.ORCAMENTO_G109))
    assert r["estouros"] == []
    assert r["faltando"] == []
    assert sorted(r["sem_orcamento"]) == ["PE14_DET_CONSOLE",
                                          "PE15_DET_BLOCO"]
    assert r["OK"] is True


def test_03_vermelho_por_injecao_lentidao(tmp_path):
    """Prancha 10x mais lenta no HLR estoura o teto congelado."""
    medidos = {c: dict(m) for c, m in H.MEDIDOS_G109.items()}
    medidos["PE04_PORTICO"] = {"t_build": 0.2, "t_hlr": 430.0,
                               "t_cotas": 6.8, "t_export": 4.1}
    (tmp_path / "lento.json").write_text(json.dumps(medidos),
                                         encoding="utf-8")
    med = json.loads((tmp_path / "lento.json").read_text(encoding="utf-8"))
    r = H.conferir_orcamento(med, dict(H.ORCAMENTO_G109))
    assert r["OK"] is False
    assert len(r["estouros"]) == 1 and "PE04_PORTICO" in r["estouros"][0]


def test_04_vermelho_por_injecao_prancha_sumida(tmp_path):
    """Medido sem PE01 acusa faltando (nao some)."""
    medidos = {c: dict(m) for c, m in H.MEDIDOS_G109.items()
               if c != "PE01_COBERTURA"}
    (tmp_path / "sem_pe01.json").write_text(json.dumps(medidos),
                                            encoding="utf-8")
    med = json.loads(
        (tmp_path / "sem_pe01.json").read_text(encoding="utf-8"))
    r = H.conferir_orcamento(med, dict(H.ORCAMENTO_G109))
    assert r["OK"] is False
    assert sorted(r["faltando"]) == ["PE01_COBERTURA"]
