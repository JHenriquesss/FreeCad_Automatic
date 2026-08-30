"""Testes do pavimento-tipo: malha -> laje -> viga continua -> pilar.

A peca central e o FECHAMENTO DE CARGA: a soma das reacoes que chegam aos pilares
tem de reproduzir a carga total do pavimento. E uma conferencia independente de
todo o encadeamento - se um painel deixar de descarregar numa viga, ou se uma
reacao for contada duas vezes, o total nao fecha, e nenhum gate de flexao ou
cortante acusaria isso.
"""

import pytest

import cargas_nbr6120 as cg
import pavimento_tipo as pt


def _cfg(**kw):
    base = {"vaos_x": [5.0, 4.0, 5.0], "vaos_y": [4.5, 4.5], "h_laje": 0.10,
            "uso": "residencial_dormitorio", "revestimento_kN_m2": 1.0,
            "b_viga": 0.20, "h_viga": 0.50, "fck": 30e3, "fyk": 500e3,
            "pe_direito": 2.90}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# vinculacao deduzida da malha
# ---------------------------------------------------------------------------
def test_painel_unico_e_totalmente_apoiado():
    p = pt.monta_paineis([5.0], [4.0])[0]
    assert p.caso == 1                       # nenhuma borda engastada
    assert not any(p.engastes.values())


def test_painel_interno_e_engastado_nas_quatro_bordas():
    paineis = {(p.i, p.j): p for p in pt.monta_paineis([4.0, 4.0, 4.0],
                                                       [4.0, 4.0, 4.0])}
    assert paineis[(1, 1)].caso == 9
    assert all(paineis[(1, 1)].engastes.values())


def test_painel_de_canto_tem_duas_bordas_continuas():
    paineis = {(p.i, p.j): p for p in pt.monta_paineis([4.0, 4.0], [4.0, 4.0])}
    c = paineis[(0, 0)]
    assert c.engastes == {"esq": False, "dir": True, "inf": False, "sup": True}
    assert c.caso == 4                       # uma longa + uma curta engastadas


def test_mapa_de_casos_cobre_as_nove_combinacoes():
    vistos = {pt.caso_por_bordas(a, b) for a in (0, 1, 2) for b in (0, 1, 2)}
    assert vistos == set(range(1, 10))


def test_contagem_invalida_de_bordas_levanta():
    with pytest.raises(ValueError):
        pt.caso_por_bordas(3, 0)


def test_orientacao_do_painel_segue_o_menor_vao():
    """A laje_concreto trabalha com lx = MENOR vao; as bordas perpendiculares a ele
    sao as LONGAS. Trocar isso troca o caso de vinculacao e, com ele, os momentos e
    as reacoes - e o erro nao apareceria como excecao, so como numero errado."""
    largo = pt.Painel(0, 0, 6.0, 3.0, {"esq": True, "dir": False,
                                       "inf": False, "sup": False})
    alto = pt.Painel(0, 0, 3.0, 6.0, {"esq": True, "dir": False,
                                      "inf": False, "sup": False})
    assert largo.lx == 3.0 and largo.ly == 6.0
    assert alto.lx == 3.0 and alto.ly == 6.0
    # no painel LARGO (6 x 3) a borda 'esq' tem 3 m -> e CURTA -> caso 2
    assert largo.caso == 2
    # no painel ALTO (3 x 6) a borda 'esq' tem 6 m -> e LONGA -> caso 3
    assert alto.caso == 3


def test_reacoes_unitarias_fecham_a_area_do_painel():
    """A soma das reacoes x comprimento de cada borda tem de dar a carga do painel
    (14.7.6.1: os quinhoes cobrem o painel inteiro)."""
    p = pt.Painel(0, 0, 5.0, 4.0, {"esq": True, "dir": True, "inf": False,
                                   "sup": True})
    ru = p.reacoes_unitarias()
    total = (ru["esq"] + ru["dir"]) * p.ly_global + (ru["inf"] + ru["sup"]) * p.lx_global
    assert total == pytest.approx(p.area, rel=2e-3)


# ---------------------------------------------------------------------------
# fechamento de carga (a conferencia independente)
# ---------------------------------------------------------------------------
def test_carga_fecha_nos_pilares():
    r = pt.monta(_cfg())
    f = pt.verifica_fechamento(r)
    assert f["ok"], f
    assert f["erro_rel"] < 1e-3


@pytest.mark.parametrize("vx,vy", [([5.0], [4.0]), ([4.0, 4.0], [4.0]),
                                   ([6.0, 3.0, 5.0], [4.5, 3.0, 5.5]),
                                   ([4.0] * 4, [4.0] * 4)])
def test_carga_fecha_em_varias_malhas(vx, vy):
    r = pt.monta(_cfg(vaos_x=vx, vaos_y=vy))
    assert pt.verifica_fechamento(r)["ok"]


def test_parede_sobre_vigas_de_contorno_entra_no_total():
    sem = pt.monta(_cfg())
    com = pt.monta(_cfg(parede_sobre_vigas={
        "tipo": "bloco_ceramico_furo_horizontal", "espessura_cm": 14.0,
        "revestimento_cm": 1.0}))
    assert com["N_total_k"] > sem["N_total_k"]
    assert pt.verifica_fechamento(com)["ok"]
    # a carga linear tem de bater com a Tabela 2 x altura livre
    alt = 2.90 - 0.50
    esperado = cg.carga_linear_parede("bloco_ceramico_furo_horizontal", 14.0, alt, 1.0)
    assert com["g_parede_kN_m"] == pytest.approx(esperado, rel=1e-6)


# ---------------------------------------------------------------------------
# coerencia fisica das reacoes
# ---------------------------------------------------------------------------
def test_pilar_interno_recebe_mais_que_o_de_canto():
    r = pt.monta(_cfg(vaos_x=[4.0, 4.0, 4.0], vaos_y=[4.0, 4.0, 4.0]))
    por_nome = {p["nome"]: p for p in r["pilares"]}
    internos = [p["N_k"] for p in r["pilares"] if p["posicao"] == "interno"]
    cantos = [p["N_k"] for p in r["pilares"] if p["posicao"] == "canto"]
    extrem = [p["N_k"] for p in r["pilares"] if p["posicao"] == "extremidade"]
    assert min(internos) > max(extrem) > max(cantos)
    assert len(cantos) == 4
    assert por_nome["P22"]["posicao"] == "interno"


def test_malha_simetrica_da_reacoes_simetricas():
    r = pt.monta(_cfg(vaos_x=[4.0, 4.0], vaos_y=[4.0, 4.0]))
    por = {(p["i"], p["j"]): p["N_k"] for p in r["pilares"]}
    assert por[(0, 0)] == pytest.approx(por[(2, 2)], rel=1e-6)
    assert por[(0, 2)] == pytest.approx(por[(2, 0)], rel=1e-6)
    assert por[(1, 0)] == pytest.approx(por[(0, 1)], rel=1e-6)


def test_carga_de_uso_maior_aumenta_a_reacao():
    leve = pt.monta(_cfg(uso="residencial_dormitorio"))     # 1,5 kN/m2
    pesado = pt.monta(_cfg(uso="loja_deposito"))            # 5,0 kN/m2
    assert pesado["N_total_k"] > leve["N_total_k"]
    assert pesado["q_kN_m2"] == 5.0


# ---------------------------------------------------------------------------
# integracao com as regras da NBR 6120
# ---------------------------------------------------------------------------
def test_uso_inexistente_propaga_o_erro_da_tabela10():
    with pytest.raises(KeyError, match="nao consta na Tabela 10"):
        pt.monta(_cfg(uso="quarto_de_hospedes"))


def test_parede_sem_posicao_definida_soma_a_carga_variavel():
    base = pt.monta(_cfg())
    com = pt.monta(_cfg(parede_sem_posicao_pp=1.8))         # faixa 0,75 kN/m2
    assert com["q_kN_m2"] == pytest.approx(base["q_kN_m2"] + 0.75)
    assert com["tab11"]["adicional_kN_m2"] == 0.75


def test_parede_pesada_sem_posicao_definida_reprova_o_pavimento():
    """A Tabela 11 marca NAO PERMITIDO acima de 3,0 kN/m: a parede tem de entrar como
    carga linear permanente na posicao de projeto. O pavimento nao pode simplesmente
    somar 1,0 kN/m2 e seguir."""
    with pytest.raises(ValueError, match="NAO PERMITIDO"):
        pt.monta(_cfg(parede_sem_posicao_pp=3.5))


def test_alternancia_de_cargas_e_avaliada_nas_vigas():
    """As vigas recebem g e q separados justamente para que 14.6.6.3 possa ser
    avaliado. Com uso leve a alternancia e dispensada; com deposito (5 kN/m2), nao."""
    leve = pt.monta(_cfg(uso="residencial_dormitorio"))
    assert all(v["alternancia_dispensada"] for v in leve["vigas_x"])
    pesado = pt.monta(_cfg(uso="praca_alimentacao_cozinha"))    # 7,5 kN/m2 > 5
    assert not any(v["alternancia_dispensada"] for v in pesado["vigas_x"])
    assert all(v["alternancia_aplicada"] for v in pesado["vigas_x"])
    assert all(v["OK"] for v in pesado["vigas_x"])


# ---------------------------------------------------------------------------
# robustez
# ---------------------------------------------------------------------------
def test_malha_vazia_levanta():
    with pytest.raises(ValueError, match="pelo menos um vao"):
        pt.monta_paineis([], [4.0])


def test_vao_nulo_levanta():
    with pytest.raises(ValueError, match="> 0"):
        pt.monta_paineis([4.0, 0.0], [4.0])


def test_parede_mais_alta_que_o_pe_direito_levanta():
    with pytest.raises(ValueError, match="altura livre"):
        pt.monta(_cfg(h_viga=3.0, pe_direito=2.90,
                      parede_sobre_vigas={"tipo": "bloco_ceramico_furo_horizontal",
                                          "espessura_cm": 14.0}))


def test_relatorio_traz_o_fechamento():
    txt = pt.relatorio(pt.monta(_cfg()))
    assert "PAVIMENTO-TIPO" in txt
    assert "Fechamento de carga: OK" in txt
    assert "P11" in txt
