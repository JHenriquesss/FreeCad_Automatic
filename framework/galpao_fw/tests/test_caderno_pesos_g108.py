"""G108: o prazo do caderno reserva tempo de FreeCAD para quem leva menos de 1 s.

Medido (G106): `_STAGE_WEIGHTS` dava hidraulica 1,25 / incendio 1,0 /
climatizacao 1,0 e o mezanino caia no default 1,0; quando o aco reservava,
os pendentes somavam 12,75 e ele recebia 7/12,75 = 54,9 % do restante.

Entregue (`caderno_turnkey._STAGE_WEIGHTS`): os quatro pesos vem de
medicao (D125 para as tres de esquema; dispatch do mezanino medido em
2026-09-11: 0,0003 s, sem prancha), com a origem escrita ao lado de cada
peso. A fracao do aco sobe para 7/8,54 = 82,0 % (G137: 9,54/11,08 = 86,1 %).

G114: ancora 900 s (estimativa T13) -> 578 s medidos (D133/G109); pesos
continuam no piso 0,01, fracao inalterada. O teste passa a chamar a
reserva real (`_fracao_reserva` + `_stage_timeout`), nunca replica a soma
com formula propria (regra anti-tautologia do lote, nota G113/D135).

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

# Conta travada, escrita a mao (G108; G137 atualiza o aco 7,0 -> 9,5396):
# pendentes quando o aco reserva = [aco, eletrico, incendio, climatizacao,
# hidraulica, mezanino] (concreto + coordenacao_* ja consumidos, na ordem de
# DISCIPLINAS) = 9,5396 + 1,5 + 0,01 + 0,01 + 0,01 + 0,01 = 11,0796.
# Fracao do aco = 9,5396/11,0796 = 0,8610 (~86,1 %; era 7/8,54 = 0,8197;
# antes 7/12,75 = 0,5490). G137: t_medido 578 -> 787,7 s (PE05 medida).
FRACAO_ACO_ESPERADA = 0.8610
FRACAO_ACO_ANTIGA = 0.6239


def _pendentes_do_aco():
    """Ordem viva: do aco em diante, na ordem de DISCIPLINAS (fonte: turnkey)."""
    import galpao_turnkey as tk

    disciplinas = list(tk.DISCIPLINAS)
    return list(disciplinas[disciplinas.index("aco"):])


def _fracao_via_reserva_real():
    """Fracao do aco pela reserva REAL (G114, anti-tautologia).

    Chama `caderno_turnkey._fracao_reserva` (que soma via `_total_peso`) e
    confere contra `_stage_timeout` com prazo congelado: fracao ==
    share/remaining. Nada aqui recalcula peso/total com formula propria.
    """
    import caderno_turnkey as ct

    pendentes = _pendentes_do_aco()
    fracao = ct._fracao_reserva("aco", pendentes)
    # Segundo caminho real: a reserva de prazo com restante conhecido.
    agora = ct._monotonic()
    deadline = agora + 100.0
    total = ct._total_peso(pendentes)
    share = ct._stage_timeout(
        deadline, 1e9, len(pendentes),
        weight=ct._STAGE_WEIGHTS.get("aco", 1.0),
        total_weight=total)
    fracao_via_timeout = float(share) / 100.0
    return fracao, fracao_via_timeout, pendentes


def test_01_fracao_do_aco_com_pesos_vivos():
    """Lado bom: com os pesos vivos a fracao do aco e a travada (~82 %),
    acima da antiga (~55 %)."""
    import caderno_turnkey as ct

    fracao, fracao_via_timeout, pendentes = _fracao_via_reserva_real()
    gaps = []
    if pendentes != ["aco", "eletrico", "incendio", "climatizacao",
                     "hidraulica", "mezanino"]:
        gaps.append("ordem de reserva mudou: %r" % (pendentes,))
    if fracao != pytest.approx(FRACAO_ACO_ESPERADA, abs=1e-4):
        gaps.append("fracao do aco %.4f != travada %.4f (pesos vivos: %r)"
                    % (fracao, FRACAO_ACO_ESPERADA,
                       {k: ct._STAGE_WEIGHTS.get(k) for k in pendentes}))
    if fracao_via_timeout != pytest.approx(fracao, abs=1e-9):
        gaps.append("reserva real diverge: fracao %.6f != via _stage_timeout "
                    "%.6f" % (fracao, fracao_via_timeout))
    if not fracao > FRACAO_ACO_ANTIGA + 0.20:
        gaps.append("fracao do aco nao subiu: %.4f (antiga %.4f)"
                    % (fracao, FRACAO_ACO_ANTIGA))
    assert not gaps, ("G108 lado bom:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_02_injecao_pesos_antigos_volta_a_fracao_antiga(tmp_path, monkeypatch):
    """Lado vermelho (sem mutar o repo): com os pesos pre-G108 injetados a
    fracao volta a ~55 % e fica abaixo da barra — o teste 01 reprovaria."""
    import caderno_turnkey as ct

    antigos = dict(ct._STAGE_WEIGHTS)
    antigos.update({"hidraulica": 1.25, "incendio": 1.0, "climatizacao": 1.0})
    antigos.pop("mezanino", None)          # pre-G108: default 1,0
    monkeypatch.setattr(ct, "_STAGE_WEIGHTS", antigos)

    fracao, fracao_via_timeout, _pend = _fracao_via_reserva_real()
    gaps = []
    if fracao != pytest.approx(FRACAO_ACO_ANTIGA, abs=1e-4):
        gaps.append("injecao nao reproduz o regime antigo: %.4f" % fracao)
    if fracao_via_timeout != pytest.approx(fracao, abs=1e-9):
        gaps.append("reserva real diverge com pesos antigos: %.6f != %.6f"
                    % (fracao, fracao_via_timeout))
    if not fracao < FRACAO_ACO_ESPERADA - 0.20:
        gaps.append("com pesos antigos a barra nao iria ao vermelho: %.4f"
                    % fracao)
    assert not gaps, ("G108 lado vermelho:\n%s"
                      % "\n".join("  - " + g for g in gaps))


def test_03_ancora_medida_d133(tmp_path):
    """G114: a ancora e o numero medido (~578 s, D133/G109), nao 900 s (T13)."""
    import caderno_turnkey as ct

    gaps = []
    ancora = getattr(ct, "_ANCORA_ACO_SEG", None)
    if ancora != pytest.approx(578.0, abs=1.0):
        gaps.append("ancora devia ser ~578 s medidos (D133/G109): %r" % (ancora,))
    # G119: a ancora tem de SUSTENTAR os pesos, nao so descreve-los. Antes ela
    # era escrita e lida por ninguem (os pesos eram literais), e este teste
    # conferia o literal contra ele mesmo - tautologia. Agora: (a) a funcao
    # real deriva o peso e (b) mexer na ancora move o peso derivado.
    if ct.peso_medido(ancora) != pytest.approx(7.0):
        gaps.append("peso_medido(ancora) devia ser 7,0: %r"
                    % ct.peso_medido(ancora))
    if ct._STAGE_WEIGHTS["aco"] != pytest.approx(ct.peso_medido(
            ct._T_MEDIDO_SEG["aco"])):
        gaps.append("peso do aco nao vem da regra: %r"
                    % ct._STAGE_WEIGHTS["aco"])
    original = ct._ANCORA_ACO_SEG
    try:                                   # ancora pela metade -> peso dobra
        ct._ANCORA_ACO_SEG = original / 2.0
        if ct.peso_medido(original) != pytest.approx(14.0):
            gaps.append("ancora nao sustenta o peso: metade da ancora devia "
                        "dobrar o peso, deu %r" % ct.peso_medido(original))
    finally:
        ct._ANCORA_ACO_SEG = original
    # o piso continua valendo para as disciplinas de segundos
    if ct.peso_medido(ct._T_MEDIDO_SEG["hidraulica"]) != pytest.approx(0.01):
        gaps.append("piso 0,01 perdido: %r"
                    % ct.peso_medido(ct._T_MEDIDO_SEG["hidraulica"]))
    # disciplina sem cronometro NAO ganha t_medido inventado
    for sem in ("concreto", "eletrico"):
        if sem in ct._T_MEDIDO_SEG:
            gaps.append("%s entrou em _T_MEDIDO_SEG sem medicao escrita" % sem)
    src = open(os.path.join(GALPAO, "caderno_turnkey.py"),
               encoding="utf-8").read()
    if "900 s" in src and "T13" in src and "ancora" in src.lower():
        # A estimativa antiga pode ficar como registro historico, mas nao
        # como ancora ativa da regra de pesos.
        if "7,0 x t_medido / 900" in src or "7 x 0,56/900" in src:
            gaps.append("regra de pesos ainda ancorada nos 900 s do T13")
    assert not gaps, ("G114 ancora:\n%s"
                      % "\n".join("  - " + g for g in gaps))
