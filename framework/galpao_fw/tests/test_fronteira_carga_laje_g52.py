"""A carga que chega a `dimensiona_laje` nao pode contar o peso proprio duas vezes.

FRONTEIRA (G52-rev). `pavimento_tipo` publica `g_kN_m2` = GAMMA_CONC*h + revestimento;
`laje_concreto.dimensiona_laje` documenta `g` como "permanente ALEM do peso proprio"
e soma 25*h por dentro. Passar `pav["g_kN_m2"]` como `g` dimensionava a laje para uma
carga que ninguem aplica - a laje engrossava sozinha enquanto vigas, pilares e
fundacao seguiam com a carga certa. Nenhum gate reprovava: cada modulo estava certo,
a JUNTA e' que estava errada. E' o mesmo formato do G3 (viga deitada), do G8 (laje que
engrossa sem realimentar) e do G13 (viga analisada e nunca verificada).

Por que um teste NOVO, com o G21_A3 ja no repo: aquele recria a aritmetica do defeito
em variaveis locais (`h_na_carga_bug = h_declarada`) e nunca chama `rodar`. Ele prova
a CONTA, nao o MODULO - fica verde com o defeito de volta. Estes aqui foram provados
VERMELHOS reinjetando `"g": pav["g_kN_m2"]` nas duas linhas.

A asserção e' a RELACAO, nao um numero congelado: numero congelado cristaliza o erro
se ele existir (licao do "AR300"), e a relacao vale para qualquer spec.
"""

import copy
import sys
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import edificio_multipavimento as em          # noqa: E402
import estrutura_casa as ec                   # noqa: E402
import pavimento_tipo as pt                   # noqa: E402

# revestimento DIFERENTE do default 1,0: se a chave morrer no caminho e o modulo
# cair no default, a relacao quebra e o teste acusa (filtro de nome morto).
REVEST = 1.6

PAREDE = {"tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14,
          "altura": 2.7, "revestimento_cm": 2.0}

EDIFICIO = {
    "geometria": {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5],
                  "pe_direito": 2.90},
    "pavimentos": ([{"nome": "Cobertura", "uso": "cobertura_manutencao"}]
                   + [{"nome": "Tipo %d" % i, "uso": "residencial_dormitorio"}
                      for i in range(4, 0, -1)]),
    "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
    "viga": {"b": 0.20, "h": 0.50},
    "materiais": {"fck": 30e3, "fyk": 500e3},
}

CASA = {
    "geometria": {"vaos_x": [3.5, 3.5, 3.4], "vaos_y": [4.0, 4.0],
                  "pe_direito": 2.7},
    "pavimentos": [{"nome": "Cobertura", "uso": "cobertura_manutencao"}],
    "laje": {"h": 0.10, "revestimento_kN_m2": REVEST},
    "viga": {"b": 0.20, "h": 0.45},
    "materiais": {"fck": 25e3, "fyk": 500e3},
    "parede_sobre_vigas": dict(PAREDE),
    "baldrame": {"b": 0.15, "h": 0.40, "parede": dict(PAREDE)},
}


def _confere(r, quem):
    laje, pav = r["laje"], r["pavimento"]
    h = laje["h"]
    pp = pt.GAMMA_CONC * h        # peso proprio, que CADA lado soma por dentro
    # 1) a junta: `dimensiona_laje` devolve o permanente TOTAL (25*h + o `g` que
    #    recebeu). Ele tem de ser o MESMO permanente que o pavimento distribui as
    #    vigas. Com `g` = pav["g_kN_m2"], a laje e' dimensionada para 25*h a mais
    #    do que qualquer outro elemento recebe.
    assert laje["g"] == pytest.approx(pav["g_kN_m2"], abs=2e-3), (
        "%s: a laje foi dimensionada para g = %.3f kN/m2 e o pavimento distribui "
        "%.3f - a fronteira conta o peso proprio (%.3f) duas vezes" % (
            quem, laje["g"], pav["g_kN_m2"], pp))
    # 2) e nao e' coincidencia de dois numeros errados: a decomposicao bate, com o
    #    revestimento DECLARADO (se a chave morrer no caminho, cai no default 1,0
    #    e esta linha acusa - filtro de nome morto).
    assert pav["g_kN_m2"] == pytest.approx(pp + REVEST, abs=2e-3), (
        "%s: g do pavimento %.3f != peso proprio %.3f + revestimento declarado "
        "%.2f" % (quem, pav["g_kN_m2"], pp, REVEST))
    # 3) a espessura da carga e a ADOTADA (G8: a laje nao engrossa em silencio)
    assert r["h_laje_adotada"] == pytest.approx(h, abs=1e-9), quem


def test_edificio_nao_conta_o_peso_proprio_da_laje_duas_vezes():
    _confere(em.rodar(copy.deepcopy(EDIFICIO)), "edificio")


def test_casa_nao_conta_o_peso_proprio_da_laje_duas_vezes():
    _confere(ec.rodar(copy.deepcopy(CASA)), "casa")
