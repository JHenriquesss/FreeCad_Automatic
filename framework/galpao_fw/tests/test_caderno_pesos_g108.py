"""G108: o prazo do caderno reserva tempo de FreeCAD para quem leva menos de 1 s.

Medido (G106): `_STAGE_WEIGHTS` dava hidraulica 1,25 / incendio 1,0 /
climatizacao 1,0 e o mezanino caia no default 1,0; quando o aco reservava,
os pendentes somavam 12,75 e ele recebia 7/12,75 = 54,9 % do restante.

Entregue (`caderno_turnkey._STAGE_WEIGHTS`): os quatro pesos vem de
medicao (D125 para as tres de esquema; dispatch do mezanino medido em
2026-09-11: 0,0003 s, sem prancha), com a origem escrita ao lado de cada
peso. A fracao do aco sobe para 7/8,54 = 82,0 %.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos
(verde no caso bom, vermelho com os pesos antigos injetados via
monkeypatch, nunca mutando o repo), conta com os pesos vivos (o valor
travado e constante escrita a mao; o que o teste mede e o dict vivo) e
fonte independente (DISCIPLINAS do turnkey + _STAGE_WEIGHTS do caderno).
"""
import sys
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)
sys.path.insert(0, HERE)

# Conta travada, escrita a mao (G108):
# pendentes quando o aco reserva = [aco, eletrico, incendio, climatizacao,
# hidraulica, mezanino] (concreto + coordenacao_* ja consumidos, na ordem de
# DISCIPLINAS) = 7,0 + 1,5 + 0,01 + 0,01 + 0,01 + 0,01 = 8,54.
# Fracao do aco = 7,0/8,54 = 0,81967 (~82,0 %; era 7/12,75 = 0,54902).
FRACAO_ACO_ESPERADA = 0.8197
FRACAO_ACO_ANTIGA = 0.5490


def _fracao_aco(pesos, disciplinas):
    """Replica `reserve_stage` no instante em que o aco reserva: peso do aco
    sobre a soma dos pesos ainda pendentes (do aco em diante, na ordem de
    DISCIPLINAS), com o mesmo default 1,0 do caderno vivo."""
    pendentes = list(disciplinas[disciplinas.index("aco"):])
    total = sum(pesos.get(etapa, 1.0) for etapa in pendentes)
    return pesos.get("aco", 1.0) / total, pendentes


def test_01_fracao_do_aco_com_pesos_vivos():
    """Lado bom: com os pesos vivos a fracao do aco e a travada (~82 %),
    acima da antiga (~55 %)."""
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    fracao, pendentes = _fracao_aco(ct._STAGE_WEIGHTS, list(tk.DISCIPLINAS))
    gaps = []
    if pendentes != ["aco", "eletrico", "incendio", "climatizacao",
                     "hidraulica", "mezanino"]:
        gaps.append("ordem de reserva mudou: %r" % (pendentes,))
    if fracao != pytest.approx(FRACAO_ACO_ESPERADA, abs=1e-4):
        gaps.append("fracao do aco %.4f != travada %.4f (pesos vivos: %r)"
                    % (fracao, FRACAO_ACO_ESPERADA,
                       {k: ct._STAGE_WEIGHTS.get(k) for k in pendentes}))
    if not fracao > FRACAO_ACO_ANTIGA + 0.20:
        gaps.append("fracao do aco nao subiu: %.4f (antiga %.4f)"
                    % (fracao, FRACAO_ACO_ANTIGA))
    assert not gaps, ("G108 lado bom:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_02_injecao_pesos_antigos_volta_a_fracao_antiga(tmp_path, monkeypatch):
    """Lado vermelho (sem mutar o repo): com os pesos pre-G108 injetados a
    fracao volta a ~55 % e fica abaixo da barra — o teste 01 reprovaria."""
    import caderno_turnkey as ct
    import galpao_turnkey as tk

    antigos = dict(ct._STAGE_WEIGHTS)
    antigos.update({"hidraulica": 1.25, "incendio": 1.0, "climatizacao": 1.0})
    antigos.pop("mezanino", None)          # pre-G108: default 1,0
    monkeypatch.setattr(ct, "_STAGE_WEIGHTS", antigos)

    fracao, _pend = _fracao_aco(ct._STAGE_WEIGHTS, list(tk.DISCIPLINAS))
    gaps = []
    if fracao != pytest.approx(FRACAO_ACO_ANTIGA, abs=1e-4):
        gaps.append("injecao nao reproduz o regime antigo: %.4f" % fracao)
    if not fracao < FRACAO_ACO_ESPERADA - 0.20:
        gaps.append("com pesos antigos a barra nao iria ao vermelho: %.4f"
                    % fracao)
    assert not gaps, ("G108 lado vermelho:\n%s"
                      % "\n".join("  - " + g for g in gaps))
