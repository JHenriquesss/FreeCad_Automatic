"""Testes da escada de concreto armado (NBR 6118:2014, laje armada em uma direcao).

O foco esta nas duas parcelas de carga que mais se erram numa escada - o peso da
laje INCLINADA lancado sobre a projecao horizontal (1/cos alpha) e o peso dos
DEGRAUS (prisma triangular, e/2) - e nos gates que reprovam em vez de saturar.
"""

import math

import pytest

import cargas_nbr6120 as cg
import escada_concreto as ec


def _cfg(**kw):
    base = {"desnivel": 1.45, "largura": 1.20, "h_laje": 0.16,
            "uso": "escada_residencial_comum", "patamar": 1.20,
            "fck": 25e3, "fyk": 500e3}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# geometria (Blondel)
# ---------------------------------------------------------------------------
def test_geometria_respeita_blondel_e_o_espelho_maximo():
    g = ec.geometria(1.45)
    assert g["ok"]
    assert g["espelho"] <= ec.ESPELHO_MAX + 1e-9
    assert g["blondel"] == pytest.approx(ec.BLONDEL_ALVO, abs=1e-6)
    assert ec.PISO_MIN <= g["piso"] <= ec.PISO_MAX


def test_degraus_sao_todos_iguais():
    """O espelho sai da divisao exata do desnivel: n*e tem de reproduzir o desnivel."""
    for desnivel in (1.20, 1.45, 1.60, 2.80, 3.00):
        g = ec.geometria(desnivel)
        assert g["n_degraus"] * g["espelho"] == pytest.approx(desnivel, rel=1e-3)


def test_piso_fora_da_faixa_ergonomica_reprova():
    """Espelho muito pequeno -> piso de Blondel acima de 32 cm: escada impraticavel.
    Reprova em vez de seguir com a geometria."""
    g = ec.geometria(0.30, espelho_max=0.10)
    assert g["ok"] is False
    assert "fora da faixa ergonomica" in g["motivo"]


def test_desnivel_nulo_levanta():
    with pytest.raises(ValueError, match="desnivel"):
        ec.geometria(0.0)


def test_inclinacao_bate_com_espelho_e_piso():
    g = ec.geometria(1.45)
    assert math.tan(g["alpha_rad"]) == pytest.approx(g["espelho"] / g["piso"],
                                                     rel=1e-3)


# ---------------------------------------------------------------------------
# carga permanente - as duas parcelas que se erram
# ---------------------------------------------------------------------------
def test_laje_inclinada_pesa_mais_que_a_laje_plana():
    """gamma*h/cos(alpha), nao gamma*h. Numa escada de ~28 graus a diferenca e ~13%,
    e o erro nao apareceria como excecao nenhuma - so como estrutura mais leve."""
    g = ec.geometria(1.45)
    _t, det = ec.carga_permanente(0.16, g["espelho"], g["piso"])
    plana = ec.GAMMA_CONC * 0.16
    assert det["laje_inclinada"] > plana
    assert det["laje_inclinada"] == pytest.approx(plana / det["cos_alpha"], rel=1e-3)


def test_degraus_pesam_gamma_vezes_meio_espelho():
    """O degrau e um prisma TRIANGULAR: volume por metro de projecao = e/2. Usar e
    (bloco macico) dobraria essa parcela; usar e*p mudaria ate a dimensao."""
    g = ec.geometria(1.45)
    _t, det = ec.carga_permanente(0.16, g["espelho"], g["piso"])
    assert det["degraus"] == pytest.approx(ec.GAMMA_CONC * g["espelho"] / 2.0,
                                           rel=1e-3)


def test_carga_total_e_a_soma_das_tres_parcelas():
    g = ec.geometria(1.45)
    total, det = ec.carga_permanente(0.16, g["espelho"], g["piso"], 1.0)
    assert total == pytest.approx(det["laje_inclinada"] + det["degraus"]
                                  + det["revestimento"], rel=1e-3)


def test_escada_mais_ingreme_pesa_mais_por_m2_de_projecao():
    g_suave = ec.geometria(1.20)
    g_ingreme = ec.geometria(1.80)
    t_s, _ = ec.carga_permanente(0.16, g_suave["espelho"], g_suave["piso"])
    t_i, _ = ec.carga_permanente(0.16, g_ingreme["espelho"], g_ingreme["piso"])
    assert g_ingreme["alpha_graus"] > g_suave["alpha_graus"]
    assert t_i > t_s


def test_geometria_degenerada_levanta():
    with pytest.raises(ValueError, match="> 0"):
        ec.carga_permanente(0.0, 0.16, 0.30)


# ---------------------------------------------------------------------------
# carga de uso vem da Tabela 10 da NBR 6120
# ---------------------------------------------------------------------------
def test_carga_de_uso_vem_da_tabela10():
    r = ec.verifica(_cfg(uso="escada_residencial_comum"))
    assert r["q_kN_m2"] == cg.carga_uso("escada_residencial_comum")["q"] == 3.0
    r2 = ec.verifica(_cfg(uso="escada_residencial_privativa"))
    assert r2["q_kN_m2"] == 2.5


def test_uso_inexistente_levanta():
    with pytest.raises(KeyError, match="nao consta na Tabela 10"):
        ec.verifica(_cfg(uso="escada_de_servico"))


def test_q_explicito_sobrepoe_a_tabela():
    r = ec.verifica(_cfg(q=4.0))
    assert r["q_kN_m2"] == 4.0 and "explicit" in r["uso"]


# ---------------------------------------------------------------------------
# esforcos e dimensionamento
# ---------------------------------------------------------------------------
def test_momento_de_faixa_bate_com_wL2_sobre_8():
    r = ec.verifica(_cfg(vinculacao="apoiada"))
    w = r["g_kN_m2"] + r["q_kN_m2"]
    # tolerancia de 1e-3: as saidas do modulo sao arredondadas para o relatorio
    assert r["M_d_pos"] == pytest.approx(1.4 * w * r["vao_calculo_m"] ** 2 / 8.0,
                                         rel=1e-3)
    assert r["M_d_neg"] == 0.0


def test_engastamento_reduz_o_momento_positivo_e_cria_o_negativo():
    ap = ec.verifica(_cfg(vinculacao="apoiada"))
    en = ec.verifica(_cfg(vinculacao="biengastada"))
    assert en["M_d_pos"] < ap["M_d_pos"]
    assert en["M_d_neg"] > 0.0
    assert en["armadura_negativa"] is not None


def test_vinculacao_invalida_levanta():
    with pytest.raises(ValueError, match="vinculacao"):
        ec.verifica(_cfg(vinculacao="engastada"))


def test_patamar_alonga_o_vao_de_calculo():
    sem = ec.verifica(_cfg(patamar=0.0))
    com = ec.verifica(_cfg(patamar=1.20))
    assert com["vao_calculo_m"] == pytest.approx(sem["vao_calculo_m"] + 1.20, rel=1e-9)
    assert com["M_d_pos"] > sem["M_d_pos"]


def test_armadura_de_distribuicao_e_menor_que_a_principal():
    r = ec.verifica(_cfg())
    assert 0 < r["As_secundaria"] < r["armadura_positiva"]["As_adotada"]


def test_escada_tipica_atende():
    r = ec.dimensiona(_cfg(h_laje=0.08))
    assert r["OK"] is True
    assert r["cortante"]["ok"] and r["els"]["ok"]


# ---------------------------------------------------------------------------
# gates: reprovar em vez de saturar
# ---------------------------------------------------------------------------
def test_lista_de_espessuras_esgotada_reprova_com_aviso():
    """SATURACAO SILENCIOSA: com um vao absurdo nenhuma espessura da lista atende. O
    resultado NAO pode sair como a ultima tentada dada por boa."""
    r = ec.dimensiona(_cfg(vao=12.0, patamar=0.0))
    assert r["OK"] is False
    assert any("SATUROU a lista de espessuras" in a for a in r["avisos"])


def test_desnivel_acima_de_320_exige_patamar_e_reprova_o_lance_unico():
    r = ec.verifica(_cfg(desnivel=3.60))
    assert r["OK"] is False
    assert any("PATAMAR intermediario" in a for a in r["avisos"])


def test_espessura_abaixo_do_minimo_da_tabela132_reprova():
    r = ec.verifica(_cfg(h_laje=0.06))
    assert r["ok_h_minimo"] is False
    assert r["OK"] is False
    assert any("Tab.13.2" in a for a in r["avisos"])


def test_mudanca_de_inclinacao_e_sinalizada():
    """A quebra do eixo no encontro lance/patamar exige detalhe de ancoragem - dobrar
    a armadura seguindo o eixo pode arrancar o cobrimento."""
    r = ec.verifica(_cfg(patamar=1.20))
    assert any("MUDANCA DE INCLINACAO" in a for a in r["avisos"])


def test_relatorio_declara_a_limitacao_de_fonte():
    r = ec.dimensiona(_cfg(h_laje=0.08))
    txt = ec.relatorio(r)
    assert "ESCADA DE CONCRETO ARMADO" in txt
    assert "A CONFIRMAR" in txt and "9050" in txt
    assert "laje inclinada" in txt and "degraus" in txt
