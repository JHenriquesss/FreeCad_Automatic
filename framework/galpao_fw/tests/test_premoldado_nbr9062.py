"""Concreto PRE-MOLDADO NBR 9062:2017 - premoldado_nbr9062.py.

Fecha o gap "pre-moldado": calice de fundacao (colarinho, 7.7), situacoes
transitorias (icamento/transporte/montagem, 5.3.2) e fckj (NBR 6118 12.3.3).
Coeficientes conferidos no PDF da NBR 9062 (NotebookLM), nao de memoria:
- Tabela 15 (embutimento): lisas/rugosas 1,5h->2,0h ; chaves 1,2h->1,6h ; min 40 cm.
- gamma_n = 1,2 (7.7.1.2) ; parede >= 15 cm, fundo >= 20 cm (7.7.5.1).
- Hsfd/Nbd: modelo Leonhardt+El Debs (7.7.3.1, Fig.26) ; compressao <= 0,4 fcd (7.7.3.6).
- beta_a (5.3.2.2): saque/manuseio/montagem 1,3 (1,4 desf.) ; transporte 1,3/0,8 ;
  icamento pilar 1,3 (sigma_s <= 0,5 fyk) ; dispositivo 3,0. gamma_f = 1,30 (5.3.2.1).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import premoldado_nbr9062 as pm


# --------------------------------------------------------- embutimento (Tab.15)
def test_embutimento_limites_tabela15():
    # r <= 0,15 -> 1,5h (lisa/rugosa) ; r >= 2 -> 2,0h
    assert abs(pm.embutimento(1000, 10, 0.40, "rugosa") - 1.5 * 0.40) < 1e-9
    assert abs(pm.embutimento(1000, 1000, 0.40, "rugosa") - 2.0 * 0.40) < 1e-9
    # chaves de cisalhamento: 1,2h -> 1,6h
    assert abs(pm.embutimento(1000, 10, 0.40, "chaves") - 1.2 * 0.40) < 1e-9
    assert abs(pm.embutimento(1000, 1000, 0.40, "chaves") - 1.6 * 0.40) < 1e-9


def test_embutimento_interpola_e_piso_40cm():
    # excentricidade intermediaria: interpolacao linear entre 0,15 e 2,0
    L = pm.embutimento(800, 200, 0.40, "rugosa")     # r = 0,625
    assert 1.5 * 0.40 < L < 2.0 * 0.40
    k = 1.5 + (2.0 - 1.5) * (0.625 - 0.15) / (2.0 - 0.15)
    assert abs(L - k * 0.40) < 1e-9
    # piso absoluto de 40 cm (7.7.2.4)
    assert abs(pm.embutimento(1000, 5, 0.20, "rugosa") - pm.LEMB_MIN) < 1e-9


def test_embutimento_tracao_veda_lisa():
    # pilar tracionado: 2,0h e interface nao pode ser lisa (7.7.2.2)
    assert abs(pm.embutimento(500, 100, 0.40, "rugosa", tracao=True) - 2.0 * 0.40) < 1e-9
    try:
        pm.embutimento(500, 100, 0.40, "lisa", tracao=True)
        assert False, "deveria vedar interface lisa na tracao"
    except ValueError:
        pass


# ------------------------------------------------ forcas do calice (El Debs)
def test_hsfd_positivo_e_nbd_alivio_por_atrito():
    Hsfd, Nbd = pm.forca_horizontal_calice(800, 200, 40, 0.40, 0.70, "rugosa")
    assert Hsfd > 0
    # Nbd = (Nd - mu*Vd)/(1+mu^2), mu=0,6 -> alivio real
    assert abs(Nbd - (800 - 0.6 * 40) / (1 + 0.6 ** 2)) < 1e-6


def test_interface_muda_hsfd_via_atrito():
    # lisa (mu=0,3) e rugosa (mu=0,6) dao resultados distintos; ambos positivos.
    Hl, Nl = pm.forca_horizontal_calice(800, 200, 40, 0.40, 0.70, "lisa")
    Hr, Nr = pm.forca_horizontal_calice(800, 200, 40, 0.40, 0.70, "rugosa")
    assert Hl > 0 and Hr > 0 and abs(Hl - Hr) > 1.0
    # mais atrito (rugosa) alivia mais a normal de fundo Nbd
    assert Nr < Nl


def test_dimensiona_calice_aplica_gamma_n_e_compressao():
    cal = pm.dimensiona_calice({"Nd": 800.0, "Md": 200.0, "Vd": 40.0, "h": 0.40,
                                "b": 0.40, "fck": 30e3, "fyk": 500e3, "interface": "rugosa"})
    assert cal["gamma_n"] == 1.20                     # 7.7.1.2
    assert cal["lim_comp"] == round(0.4 * 30e3 / 1.4, 1)   # 0,4 fcd (7.7.3.6)
    assert cal["compressao_ok"] is True
    assert cal["As_horizontal_cm2"] > 0 and cal["OK"]


def test_calice_chaves_usa_mbd_e_alivio_02Nd():
    cal = pm.dimensiona_calice({"Nd": 800.0, "Md": 200.0, "Vd": 40.0, "h": 0.40,
                                "b": 0.40, "fck": 30e3, "interface": "chaves"})
    # 7.7.4: Mbd = Md + Vd*Lemb (com gamma_n) ; N_base = 0,2 Nd (com gamma_n)
    assert abs(cal["N_base"] - 0.2 * 800 * 1.2) < 1e-6
    # Lemb reportado e arredondado a 3 casas -> tolerancia coerente
    assert abs(cal["Mbd"] - (200 * 1.2 + 40 * 1.2 * cal["Lemb"])) < 0.05


# --------------------------------------------- situacoes transitorias (5.3.2)
def test_beta_a_valores_norma():
    assert pm.beta_a("montagem") == 1.3
    assert pm.beta_a("montagem", desfavoravel=True) == 1.4
    assert pm.beta_a("transporte") == 1.3
    assert pm.beta_a("transporte", favoravel=True) == 0.8
    assert pm.beta_a("icamento_pilar") == 1.3
    assert pm.beta_a("dispositivo") == 3.0


def test_carga_equivalente_gamma_f_130():
    g, ba = pm.carga_equivalente(10.0, "montagem")
    assert abs(g - 1.30 * 1.3 * 10.0) < 1e-9 and ba == 1.3


def test_fckj_evolui_com_idade():
    assert abs(pm.fckj_idade(30e3, 28) - 30e3) < 1e-6      # 28 d -> fck
    assert pm.fckj_idade(30e3, 3, "CPV") < 30e3            # mais novo -> menor
    # CPV-ARI ganha resistencia mais rapido que CPIII na mesma idade
    assert pm.fckj_idade(30e3, 3, "CPV") > pm.fckj_idade(30e3, 3, "CPIII")


# ---------------------------------------------------- icamento do pilar
def test_icamento_pilar_limita_sigma_05fyk():
    ica = pm.verifica_icamento_pilar({"L": 8.0, "b": 0.40, "h": 0.40, "As": 12.0,
                                      "fck": 30e3, "fyk": 500e3, "t_dias": 3})
    # Mr usa 0,50 fyk (5.3.2.2) - NAO fyd
    d = 0.40 - 0.04
    assert abs(ica["Mr_0.5fyk_kN_m"] - 12e-4 * 0.5 * 500e3 * 0.9 * d) < 1e-6
    assert ica["OK"] and ica["beta_a"] == 1.3


def test_icamento_ponto_otimo_207L():
    ica = pm.verifica_icamento_pilar({"L": 10.0, "b": 0.30, "h": 0.60, "As": 10.0,
                                      "fck": 30e3, "t_dias": 5})
    assert abs(ica["a_otimo"] - 0.2071 * 10.0) < 0.01


def test_pilar_longo_esbelto_pode_reprovar_icamento():
    # pilar muito longo, secao fina e pouca armadura, icado nas pontas (a=0)
    ica = pm.verifica_icamento_pilar({"L": 14.0, "b": 0.20, "h": 0.30, "As": 2.0,
                                      "fck": 30e3, "t_dias": 2, "a_pega": 0.0})
    assert isinstance(ica["OK"], bool)
    assert ica["Md_kN_m"] > 0


def test_selftest_roda():
    pm._selftest()
