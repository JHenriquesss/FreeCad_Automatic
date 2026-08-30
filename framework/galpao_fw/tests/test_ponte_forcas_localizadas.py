# ============================================================================
# test_ponte_forcas_localizadas.py - A VIGA DE ROLAMENTO SOB A NBR 8800 5.7.
# forcas_localizadas.py estava 100% verde e NINGUEM o chamava: a viga de
# rolamento era verificada so a flexao biaxial, flecha e fadiga, sem o modo de
# ruina mais classico dela (esmagamento/enrugamento da alma sob a roda e sob a
# reacao no console). Estes testes travam o wire - e travam tambem a REGRA DE
# DADO AUSENTE: sem trilho/filete informados usa-se o piso conservador (ln=0,
# k=tf), nunca um valor inventado que faria o perfil passar de graca.
# ============================================================================
"""NBR 8800 5.7 na viga de rolamento (ponte_rolante.verifica_forcas_localizadas)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

import forcas_localizadas as fl
import ponte_rolante as pr


def _cfg(**over):
    base = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "vao_ponte": 9.5,
            "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10,
            "frac_lateral": 0.10, "frac_long": 0.10, "vao_viga": 5.0,
            "d_rodas": 3.0, "fy": 250e3, "perfil_viga": pr.VS500,
            "siderurgica": False, "excentricidade": 0.30}
    base.update(over)
    return base


def test_a_analise_da_ponte_verifica_as_forcas_localizadas():
    _, viga, _ = pr.analisa(_cfg())
    assert "forcas_localizadas" in viga, "5.7 nao entrou na viga de rolamento"
    resultado = viga["forcas_localizadas"]
    assert set(resultado["roda"]) >= {"F_sd", "F_Rd", "OK"}
    assert "atende" in resultado["apoio"]


def test_o_veredito_da_viga_engloba_o_5_7():
    # sem isto uma reprovacao de alma passaria silenciosa por tras de um
    # inter<=1 de flexao (a mesma classe de bug da saturacao silenciosa).
    _, viga, _ = pr.analisa(_cfg())
    resultado = viga["forcas_localizadas"]
    assert viga["OK"] == (viga["inter"] <= 1.0
                          and (viga["flecha_ok"] in (None, True))
                          and viga["fadiga"]["ok"] and resultado["OK"])


def test_sem_trilho_informado_usa_o_piso_conservador_e_declara():
    _, viga, _ = pr.analisa(_cfg())
    resultado = viga["forcas_localizadas"]
    assert resultado["ln_roda_m"] == 0.0 and resultado["ln_apoio_m"] == 0.0
    assert resultado["k_m"] == pr.VS500["tf"]
    assert any("piso conservador" in aviso for aviso in resultado["a_confirmar"])


def test_o_piso_conservador_e_de_fato_o_menor_F_Rd():
    # ln maior e k maior so aumentam F_Rd (5.7.3/5.7.4): o piso nunca aprova
    # o que o dado real reprovaria.
    sec, fy = pr.VS500, 250e3
    piso = fl.escoamento_local_alma(sec, fy, 0.0, sec["tf"], na_extremidade=True)
    real = fl.escoamento_local_alma(sec, fy, 0.15, sec["tf"] + 0.006,
                                    na_extremidade=True)
    assert piso["F_Rd"] < real["F_Rd"]


def test_apoio_que_nao_passa_ganha_enrijecedor_dimensionado():
    # 5.7.8: extremidade sem restricao a rotacao exige enrijecedor de apoio.
    # O modulo DIMENSIONA (5.7.9) em vez de so reprovar.
    _, viga, reac = pr.analisa(_cfg())
    resultado = viga["forcas_localizadas"]
    if resultado["apoio"]["atende"]:
        return                                  # nada a dimensionar neste caso
    enrijecedor = resultado["enrijecedor_apoio"]
    assert enrijecedor and enrijecedor["escolha"], "reprovou sem propor solucao"
    assert enrijecedor["N_Rd"] >= reac["R_vertical_kN"]
    assert enrijecedor["geometria"]["ok"], "chapa fora da geometria 5.7.9.5"


def test_trilho_declarado_substitui_o_piso():
    apoio = {"ln_roda_m": 0.15, "ln_apoio_m": 0.20, "k_m": 0.022}
    _, viga, _ = pr.analisa(_cfg(apoio=apoio))
    resultado = viga["forcas_localizadas"]
    assert resultado["ln_apoio_m"] == 0.20 and resultado["k_m"] == 0.022
    assert resultado["a_confirmar"] == []
    # com apoio real a resistencia sobe e o apoio passa direto
    assert resultado["apoio"]["atende"] is True


def test_o_relatorio_mostra_o_5_7_sem_estragar_o_item_da_norma():
    # o pos-processamento de virgula decimal do relatorio converteria "5.7" em
    # "5,7"; o item tem de sair legivel.
    esf, viga, reac = pr.analisa(_cfg())
    texto = pr.relatorio_pt(esf, viga, reac)
    assert "FORCAS LOCALIZADAS NA ALMA (NBR 8800 5.7.3/5.7.4)" in texto
    assert "5,7.3" not in texto
