"""ELS (flecha) da viga de baldrame sob alvenaria - NBR 6118 17.3.2 + Tabela 13.3.

A verificacao antes so fazia resistencia (flexao/cortante/armadura). Um baldrame
esbelto passa no ELU mas a flecha diferida (fluencia) fissura a parede de alvenaria
apoiada nele. Achado na auditoria de fechamento. O deslocamento comparado ao limite
e o POS-construcao da parede (so a fluencia), NBR 6118 Tab 13.3.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import viga_baldrame as vb


def _cfg(vao, q_parede, h=0.40, **kw):
    base = {"vao": vao, "b": 0.20, "h": h, "fck": 25e3, "fyk": 500e3,
            "cobrimento": 0.05, "q_parede": q_parede, "N_amarracao": 30.0}
    base.update(kw)
    return base


def test_baldrame_tem_verificacao_de_flecha_sob_alvenaria():
    r = vb.verifica_baldrame(_cfg(5.0, 6.0))
    assert r["els"] is not None
    assert {"d_pos_parede_mm", "lim_mm", "fissura"} <= set(r["els"])
    # limite = min(L/500, 10 mm); para L=5 m, L/500=10 mm
    assert abs(r["els"]["lim_mm"] - 10.0) < 1e-6


def test_sem_alvenaria_nao_checa_flecha():
    # q_parede=0 (so telha): sem parede p/ fissurar -> ELS de alvenaria nao se aplica
    r = vb.verifica_baldrame(_cfg(5.0, 0.0))
    assert r["els"] is None and r["els_ok"] is True


def test_baldrame_esbelto_reprova_no_els_mesmo_com_elu_ok():
    # vao 5,7 m + parede pesada (12 kN/m) numa secao 20x40: ELU passa, ELS reprova
    # (a flecha de fluencia fissura a alvenaria). Sem o ELS, OK seria True (bug).
    r = vb.verifica_baldrame(_cfg(5.7, 12.0, h=0.40))
    assert r["ok_dominio"] and r["sec_ok"] and r["cort_ok"]   # ELU passa
    assert r["els_ok"] is False and r["OK"] is False          # ELS reprova
    assert r["els"]["d_pos_parede_mm"] > r["els"]["lim_mm"]
    assert r["els"]["fissura"] is True                        # estadio II


def test_dimensiona_baldrame_sobe_altura_ate_atender_els():
    # a escalada adota a MENOR altura que vence ELU + ELS
    rd = vb.dimensiona_baldrame(_cfg(5.7, 12.0, h=0.40))
    assert rd["OK"] is True and rd["els_ok"] is True
    assert rd["h"] > 0.40                                      # subiu do seed


def test_pos_construcao_e_so_a_fluencia():
    # o deslocamento comparado ao limite e o POS-parede (fluencia), nao o total:
    # d_pos = d_total - d_imediata (a imediata ocorre durante o levantamento).
    r = vb.verifica_baldrame(_cfg(5.0, 6.0))
    e = r["els"]
    assert abs(e["d_pos_parede_mm"] - (e["d_total_mm"] - e["d_imediata_mm"])) < 0.1
