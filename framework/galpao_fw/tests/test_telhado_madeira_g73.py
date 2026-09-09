"""G73: o no da tesoura em madeira-madeira, lendo a pagina (NBR 7190-1).

Toda transcricao abaixo foi lida RENDERIZANDO o F136 (a camada de texto
das fomas multilinha sai embaralhada, nao ausente):
- 7.2 e Rk = Fv,Rk.nsp.nef: p.56 do PDF (impressa 56);
- 7.2 a-f: pp.56-57 do PDF (Figs.19-21);
- Tab.18 (1 secao, Ia-III): pp.58-59 do PDF;
- Tab.19 (2 secoes, Ia-III): pp.59-60 do PDF;
- beta = fe2,k/fe1,k e Fax,Rk/4 (+ limites e "apos investigacao
  experimental"): p.60 do PDF;
- Tab.16 (pre-furacao): p.55 do PDF; 7.1.11 na p.54;
- 7.1.9 (dmin), My,k (7.1.4), nef (7.1.7), Rd (7.1.2): pp.49-51.

Cada teste e' relacao (nunca numero congelado) e o vermelho-por-injecao
mora dentro.
"""

import copy
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

GALPAO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GALPAO))

import madeira_nbr7190 as mad
import telhado_casa_madeira as tmad

TELHADO_MM = {
    "vao": 8.0, "inclinacao_graus": 25.0, "extensao": 10.4,
    "espacamento": 2.0, "n_paineis": 2, "forro_fragil": False,
    "telha": {"tipo": "ondulada", "peso": 0.55},
    "sobrecarga_kNm2": 0.25,
    "madeira": {"classe": "C24", "carregamento": "curta", "umidade": 2,
                "categoria": "serrada"},
    "secoes": {
        "banzo_sup": {"b": 0.08, "h": 0.16},
        "banzo_inf": {"b": 0.06, "h": 0.16},
        "diagonal": {"b": 0.06, "h": 0.12},
        "montante": {"b": 0.06, "h": 0.12},
        "terca": {"b": 0.06, "h": 0.16}},
    "apoio": "viga",
    "travamento_borda_comprimida_m": 2.0,
    "contraventamento_banzo_inf_m": 2.0,
    "apoio_comprimento_m": 0.2,
    "ligacao": {
        "sistema": "madeira_madeira",
        "tipo_pino": "parafuso", "d_mm": 12.0, "d0_mm": 12.5,
        "fu_MPa": 415.0, "n_pinos": 4, "n_cortes": 2,
        "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                         "a3c": 80, "a4t": 60, "a4c": 60},
        "he_mm": 90.0},
}


def _cfg_mm(**kw):
    fe = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    base = {"tipo_pino": "parafuso", "d_mm": 12.0, "d0_mm": 12.5,
            "fu_MPa": 415.0, "t1_mm": 160.0, "t2_mm": 160.0,
            "fe1_Nmm2": fe, "fe2_Nmm2": fe, "n_pinos": 4,
            "n_cortes": 2, "kmod1": 0.9, "kmod2": 0.9,
            "espacamentos": {"a1": 150, "a2": 80, "a3t": 150,
                             "a3c": 80, "a4t": 60, "a4c": 60},
            "alpha_graus": 0.0, "t_madeira_mm": 80.0,
            "penetracao_mm": 80.0}
    base.update(kw)
    return base


# --- beta: a razao dos embutimentos, nao um numero -----------------------------

def test_beta_e_a_razao_dos_embutimentos():
    fe1 = mad.embutimento_fek(12.0, 350.0, True, True, 0.0)["fe_k_Nmm2"]
    fe2 = mad.embutimento_fek(12.0, 530.0, False, True, 0.0)["fe_k_Nmm2"]
    My = mad.pino_Myk_Nmm(415.0, 12.0)
    m = mad._rk_madeira_madeira(1, fe1, fe2, 60.0, 60.0, 12.0, My)
    assert m["beta"] == pytest.approx(fe2 / fe1)
    # p.60 do PDF: beta = fe2,k / fe1,k (ordem importa: inverter troca Ib).
    assert m["beta"] == pytest.approx(1.0 / (fe1 / fe2))
    assert m["Ib_embutimento_t2"] == pytest.approx(fe2 * 60.0 * 12.0)


# --- Tab.18: corte simples, seis modos ------------------------------------------

def test_corte_simples_tem_seis_modos_transcritos():
    fe, My = 20.0, mad.pino_Myk_Nmm(415.0, 12.0)
    t1, t2, d = 60.0, 80.0, 12.0
    beta, r = 1.0, t2 / t1
    m = mad._rk_madeira_madeira(1, fe, fe, t1, t2, d, My)
    ia = fe * t1 * d
    ib = fe * t2 * d * beta
    ic = (fe * t1 * d / (1 + beta)
          * (math.sqrt(beta + 2 * beta ** 2 * (1 + r + r ** 2)
                       + beta ** 3 * r ** 2) - beta * (1 + r)))
    iia = (1.05 * fe * t1 * d / (2 + beta)
           * (math.sqrt(2 * beta * (1 + beta)
                        + 4 * beta * (2 + beta) * My / (fe * d * t1 ** 2))
              - beta))
    iib = (1.05 * fe * t2 * d / (1 + 2 * beta)
           * (math.sqrt(2 * beta ** 2 * (1 + beta)
                        + 4 * beta * (1 + 2 * beta) * My / (fe * d * t2 ** 2))
              - beta))
    iii = 1.15 * math.sqrt(2 * beta / (1 + beta)) * math.sqrt(2 * My * fe * d)
    assert m["Ia_embutimento_t1"] == pytest.approx(ia)
    assert m["Ib_embutimento_t2"] == pytest.approx(ib)
    assert m["Ic_misto"] == pytest.approx(ic)
    assert m["IIa_misto_t1"] == pytest.approx(iia)
    assert m["IIb_misto_t2"] == pytest.approx(iib)
    assert m["III_pino"] == pytest.approx(iii)
    assert m["FvRk_N"] == pytest.approx(min(ia, ib, ic, iia, iib, iii))
    assert len([k for k in m if k not in ("FvRk_N", "beta")]) == 6


# --- Tab.19: corte duplo, quatro modos (o 0,5 nao e' decoracao) ------------------

def test_corte_duplo_tem_quatro_modos_e_o_meio_vale():
    fe, My = 20.0, mad.pino_Myk_Nmm(415.0, 12.0)
    t1, t2, d = 60.0, 100.0, 12.0
    beta = 1.0
    m = mad._rk_madeira_madeira(2, fe, fe, t1, t2, d, My)
    assert m["Ia_embutimento_lateral"] == pytest.approx(fe * t1 * d)
    # p.59 do PDF: Fv,RK2 = 0,5.fe1,k.t2.d.beta (POR PLANO). Sem o 0,5
    # o plano central valeria o dobro e o Rk do no sairia 2x.
    assert m["Ib_embutimento_central"] == pytest.approx(
        0.5 * fe * t2 * d * beta)
    simples = mad._rk_madeira_madeira(1, fe, fe, t1, t2, d, My)
    assert m["II_misto"] == pytest.approx(simples["IIa_misto_t1"])
    assert m["III_pino"] == pytest.approx(simples["III_pino"])
    assert len([k for k in m if k not in ("FvRk_N", "beta")]) == 4


def test_injecao_sem_o_meio_aprovaria_o_que_reprova():
    """Vermelho por injecao: sem o 0,5 da Tab.19 o Ib dobra e um no no
    limite passa. A demanda abaixo cabe no bug e nao cabe na norma."""
    fe, My = 20.0, mad.pino_Myk_Nmm(415.0, 12.0)
    m_ok = mad._rk_madeira_madeira(2, fe, fe, 60.0, 60.0, 12.0, My)
    ib_bug = 2.0 * m_ok["Ib_embutimento_central"]
    assert ib_bug == pytest.approx(
        mad._rk_madeira_madeira(1, fe, fe, 60.0, 60.0, 12.0, My
                               )["Ib_embutimento_t2"])
    # o III governa aqui, entao a injecao mira um caso onde o Ib governa:
    m_fino = mad._rk_madeira_madeira(2, fe, fe, 200.0, 20.0, 12.0, My)
    assert m_fino["Ib_embutimento_central"] == m_fino["FvRk_N"]
    assert 2.0 * m_fino["FvRk_N"] > m_fino["FvRk_N"]


# --- Fax,Rk = 0 sem ensaio, dito --------------------------------------------------

def test_efeito_corda_zero_sem_ensaio_e_dito():
    r = mad.verifica_ligacao_madeira_madeira(5.0, _cfg_mm())
    assert r["efeito_corda"] == "FaxRk=0 sem ensaio (conservador, p.60)"
    # Rk fecha contra a propria conta (nsp.nef.FvRk), nao contra si mesma:
    # a origem independente e' a recomposicao abaixo.
    assert r["Rk_N"] == pytest.approx(
        2 * r["nef"] * r["FvRk_por_plano_N"])
    assert r["Rd_kN"] == pytest.approx(
        min(0.9, 1.0) * 0.9 * r["Rk_N"] / 1.4 / 1000.0)


# --- Tab.16: a pre-furacao e' portao proprio ---------------------------------------

def test_tab16_prego_conifera_e_folhosa_tem_alvo_proprio():
    assert mad.verifica_prefuracao_tab16("prego", 5.0, 4.25, True)["OK"]
    assert mad.verifica_prefuracao_tab16("prego", 5.0, 4.90, False)["OK"]
    # cruzado reprova: 4,90 numa conifera nao e' 0,85.d.
    ruim = mad.verifica_prefuracao_tab16("prego", 5.0, 4.90, True)
    assert ruim["OK"] is False and "Tab.16" in ruim["motivo"]
    com = mad.verifica_prefuracao_tab16("parafuso", 12.0, 12.5)
    assert com["OK"] and com["faixa_mm"] == (12.0, 13.0)
    fora = mad.verifica_prefuracao_tab16("parafuso", 12.0, 13.5)
    assert fora["OK"] is False
    rosa = mad.verifica_prefuracao_tab16(
        "parafuso_rosca_soberba", 10.0, 7.0)
    assert rosa["OK"]
    assert not mad.verifica_prefuracao_tab16(
        "parafuso_rosca_soberba", 10.0, 8.0)["OK"]
    with pytest.raises(mad.EntradaMadeira, match="d0_mm"):
        mad.verifica_prefuracao_tab16("parafuso", 12.0, None)
    with pytest.raises(mad.EntradaMadeira, match="conifera"):
        mad.verifica_prefuracao_tab16("prego", 5.0, 4.25, None)


def test_pre_furo_errado_reprova_a_ligacao_72_nomeando():
    r = mad.verifica_ligacao_madeira_madeira(0.5, _cfg_mm(d0_mm=14.0))
    assert r["OK"] is False
    assert any("Tab.16" in m for m in r["falhas_geometria"])
    assert mad.verifica_ligacao_madeira_madeira(0.5, _cfg_mm())["OK"]


# --- o cuidado nomeado: a2 de prego continua 9d ------------------------------------

def test_a2_de_prego_continua_9d_na_tab14():
    d = 5.0
    assert mad.espacamentos_minimos("prego", d, 90.0)["a2"] == pytest.approx(
        9 * d)
    assert mad.espacamentos_minimos("prego", d, 0.0)["a2"] == pytest.approx(
        3 * d)


# --- portoes 7.2 a-f valem igual -----------------------------------------------------

def test_geometria_72_reprova_nomeando_o_artigo():
    fina = _cfg_mm(t_madeira_mm=20.0)
    r = mad.verifica_ligacao_madeira_madeira(1.0, fina)
    assert r["OK"] is False and any("7.2-a" in m
                                    for m in r["falhas_geometria"])
    prego = _cfg_mm(tipo_pino="prego", d_mm=8.0, d0_mm=0.85 * 8.0,
                    conifera=True, t_madeira_mm=30.0)
    r2 = mad.verifica_ligacao_madeira_madeira(0.5, prego)
    assert r2["OK"] is False and any("7.2-b" in m
                                     for m in r2["falhas_geometria"])
    curta = _cfg_mm(penetracao_mm=10.0)
    r3 = mad.verifica_ligacao_madeira_madeira(0.5, curta)
    assert r3["OK"] is False and any("7.2-f" in m
                                     for m in r3["falhas_geometria"])


def test_n_cortes_invalido_recusa_com_endereco():
    with pytest.raises(mad.EntradaMadeira, match="n_cortes"):
        mad.verifica_ligacao_madeira_madeira(1.0, _cfg_mm(n_cortes=3))
    with pytest.raises(mad.EntradaMadeira, match="n_pinos|1 pino"):
        mad.verifica_ligacao_madeira_madeira(1.0, _cfg_mm(n_pinos=1))


# --- o no da tesoura por declaracao ---------------------------------------------------

def test_no_madeira_madeira_atende_e_nomeia_o_sistema():
    r = tmad.rodar(copy.deepcopy(TELHADO_MM))
    assert r["ATENDE"] is True, r["reprovados"]
    assert r["ligacoes"]["sistema"] == "madeira_madeira"
    assert r["ligacoes"]["apoio"]["n_cortes"] == 2
    assert r["ligacoes"]["apoio"]["beta"] == pytest.approx(1.0)
    assert "madeira_madeira" in tmad.relatorio_pt(r)


def test_chapa_de_aco_continua_disponivel():
    import tests.test_telhado_madeira_g66 as g66

    r = tmad.rodar(copy.deepcopy(g66.TELHADO_VIGA))
    assert r["ATENDE"] is True
    assert r["ligacoes"]["sistema"] == "chapa_aco"


def test_corte_simples_no_limite_reprova_onde_o_duplo_passa():
    um = copy.deepcopy(TELHADO_MM)
    um["ligacao"]["n_cortes"] = 1
    r = tmad.rodar(um)
    assert r["ATENDE"] is False and "ligacoes" in r["reprovados"]
    assert r["ligacoes"]["no_critico"]["util"] > 1.0
    dois = tmad.rodar(copy.deepcopy(TELHADO_MM))
    assert dois["ATENDE"] is True
    # relacao, nao numero: o duplo carrega 2x o simples no mesmo pino.
    assert dois["ligacoes"]["no_critico"]["Rk_N"] == pytest.approx(
        2 * r["ligacoes"]["no_critico"]["Rk_N"])


def test_sistema_ambiguo_ou_omisso_recusa():
    amb = copy.deepcopy(TELHADO_MM)
    amb["ligacao"]["config_73"] = "chapa_central_dupla"
    amb["ligacao"]["t_chapa_mm"] = 6.3
    with pytest.raises(tmad.EntradaTelhado, match="7.2"):
        tmad.rodar(amb)
    sem = copy.deepcopy(TELHADO_MM)
    del sem["ligacao"]["d0_mm"]
    with pytest.raises(tmad.EntradaTelhado, match="d0_mm"):
        tmad.rodar(sem)
    tres = copy.deepcopy(TELHADO_MM)
    tres["ligacao"]["n_cortes"] = 3
    with pytest.raises(tmad.EntradaTelhado, match="n_cortes"):
        tmad.rodar(tres)


# --- escopo: a ausencia passa a ser presenca -------------------------------------------

def test_escopo_72_implementado_e_sem_motivo_de_ausencia():
    assert mad.escopo()["ligacao_madeira_madeira_7.2"] == "implemented"
    assert "ligacao_madeira_madeira_7.2" not in mad.motivos_escopo()
    assert tmad.escopo()["ligacao_madeira_madeira_7.2"] == "implemented"


# --- prancha: abrir a folha e olhar -----------------------------------------------------

def test_prancha_diz_o_sistema_e_a_situacao_de_cada_peca():
    import re

    import desenho_casa_residencial as dcr

    r = tmad.rodar(copy.deepcopy(TELHADO_MM))
    svg = dcr.telhado_tesoura_svg(r)
    ET.fromstring(svg)
    assert "ligacao madeira_madeira: ATENDE" in svg
    txt = re.findall(r">([^<]+)</text>", svg)
    i = txt.index("Peca")
    situacao = {}
    for k in range(i + 5, len(txt) - 4, 5):
        situacao[txt[k]] = txt[k + 4]
    assert situacao["banzo_sup"] == situacao["terca"] == "ATENDE"
    # e no defeito a folha diz ONDE: a peca reprovada nao contamina as
    # que passam, e a linha da ligacao acompanha o veredito.
    ruim = copy.deepcopy(TELHADO_MM)
    ruim["secoes"]["diagonal"] = {"b": 0.02, "h": 0.02}
    r2 = tmad.rodar(ruim)
    assert r2["ATENDE"] is False
    svg2 = dcr.telhado_tesoura_svg(r2)
    ET.fromstring(svg2)
    txt2 = re.findall(r">([^<]+)</text>", svg2)
    j = txt2.index("Peca")
    sit2 = {}
    for k in range(j + 5, len(txt2) - 4, 5):
        sit2[txt2[k]] = txt2[k + 4]
    assert sit2["diagonal"] == "REPROVA"
    assert sit2["banzo_sup"] == "ATENDE"
