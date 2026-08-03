# -*- coding: utf-8 -*-
"""Trava a caca de SATURACAO SILENCIOSA (S40): tabela satura no maior valor +
gate que NAO reprova + OK=True. Ja corrigido antes em hidraulica (pluvial) e
eletrico (curto). Aqui: aco (terca) e incendio (placa de sinalizacao).

Padrao do bug: uma escada/tabela satura no ULTIMO item quando nada passa; o
consumidor entrega o item saturado como se atendesse. Contra-seguranca."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# ACO: o veredito global (rodar_galpao._consolidar) usava so terca_inter (ELU).
# A iteracao de tercas satura no perfil MAIS PESADO (menor interacao) quando
# nenhum passa; se ele falha por FLECHA (ELS)/distorcional, terca_inter <= 1
# e a falha escapava. Agora a linha "Terca (ELS/dist.)" reprova via terca_ok.
# ---------------------------------------------------------------------------
def test_terca_saturada_por_flecha_reprova_verdito_global(tmp_path):
    import rodar_galpao as rg
    save = lambda nome, texto: None                      # noqa: E731 (no-op)
    g = {"comprimento": 40.0, "span": 20.0}

    # terca saturada: ELU interacao PASSA (0,5 <= 1) mas ELS/distorcional reprova
    res = {"terca_inter": 0.5, "terca_ok": False}
    rg._consolidar(str(tmp_path), save, g, {}, res=res)
    assert res["atende_global"] is False, "terca reprovada por flecha deve derrubar o global"
    nomes = [n for n, _ in res["falhas_verificacao"]]
    assert any(n.startswith("Terca (ELS") for n in nomes), nomes

    # controle: terca OK nao gera falha por esta linha (nem por interacao)
    res_ok = {"terca_inter": 0.5, "terca_ok": True}
    rg._consolidar(str(tmp_path), save, g, {}, res=res_ok)
    assert res_ok["atende_global"] is True
    assert not res_ok["falhas_verificacao"]


# ---------------------------------------------------------------------------
# INCENDIO: placa_minima satura em 600 mm (maior lado padronizado) quando
# NENHUM cobre L_vis; dimensiona_sinalizacao dava OK=True so exigindo lado>=100
# -> placa subdimensionada numa rota longa de galpao grande (contra-seguranca).
# ---------------------------------------------------------------------------
def test_placa_sinalizacao_satura_reprova():
    import sinalizacao_nbr16820 as sn
    # galpao normal 40x20: L_vis ~22,4 m < 24 m (dist. da placa 600) -> ATENDE
    r = sn.dimensiona_sinalizacao({"C": 40.0, "L": 20.0})
    assert r["placa_lado_mm"] == 600 and r["OK"] and not r["placa_satura"]
    # galpao grande 100x60: L_vis ~58,3 m > 24 m -> satura e REPROVA (nao OK mudo)
    rg = sn.dimensiona_sinalizacao({"C": 100.0, "L": 60.0})
    assert rg["placa_satura"] and not rg["OK"]
