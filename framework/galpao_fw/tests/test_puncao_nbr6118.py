"""Puncao NBR 6118 item 19.5 (laje lisa) - o que este teste PODE e o que NAO pode
aferir.

NAO ha exemplo resolvido de puncao pela NBR 6118 no acervo do projeto (checado:
Carvalho cap.7 so trata laje sobre vigas; o Vol.4 do Araujo esta digitalizado ate
a p.168, antes da secao 7.5; Botelho declara que nao trata laje lisa;
Nilson/MacGregor resolvem pelo ACI 318, que e outro modelo). Entao aqui NAO se
finge afericao contra livro - a que existe em laje_concreto (Carvalho Ex.1) e na
sapata (Alonso) nao tem equivalente aqui, e isso esta declarado no cabecalho do
modulo. O que este arquivo garante:

  1. GEOMETRIA conferida contra a formula fechada da PROPRIA norma para o pilar
     interno (Wp = C1^2/2 + C1*C2 + 4*C2*d + 16*d^2 + 2*pi*d*C1) e contra o
     perimetro analitico u = 2(C1+C2) + 4*pi*d. Foi essa conferencia que pegou um
     erro real: a integral |e|dl pelo ponto MEDIO de cada trecho zerava os
     trechos que cruzam o eixo, e Wp saia 8% baixo.
  2. Cada expressao de resistencia recalculada independentemente no teste, a
     partir do texto da norma (19.5.3.1, 19.5.3.2, 19.5.3.3).
  3. Os GATES que nao aparecem como razao solicitante/resistente - 19.5.3.5
     (armadura obrigatoria) e 19.5.4 (colapso progressivo) -, que sao o caso
     tipico de saturacao silenciosa: sem gate proprio a ligacao sai OK=True.
  4. Cross-check com fundacao_sapata, que passou a consumir as mesmas primitivas.
"""

import math

import pytest

import fundacao_sapata as fs
import puncao_nbr6118 as pu

FCK, FYK = 30e3, 500e3


def _base(**over):
    cfg = dict(tipo="interno", c1=0.40, c2=0.40, d=0.16, fck=FCK, fyk=FYK,
               F_sd=400.0, As_x=12e-4, As_y=12e-4, As_ccp=15e-4)
    cfg.update(over)
    return cfg


# ---------------------------------------------------------------------------
# 1. Geometria dos contornos criticos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("c1,c2,d", [(0.40, 0.20, 0.15), (0.30, 0.30, 0.20),
                                     (0.20, 0.60, 0.12), (0.50, 0.25, 0.18)])
def test_perimetro_e_Wp_do_contorno_C_linha(c1, c2, d):
    """C' e o contorno a 2d: u = 2(C1+C2) + 4*pi*d (retangulo dilatado, cantos em
    arco de raio 2d) e Wp e o da formula fechada de 19.5.2.2."""
    pr = pu.propriedades(pu.contorno(c1, c2, 2 * d, "interno"))
    assert pr["u"] == pytest.approx(2 * (c1 + c2) + 4 * math.pi * d, rel=2e-3)
    assert pr["Wp_x"] == pytest.approx(pu.Wp_interno_formula(c1, c2, d), rel=2e-3)
    assert pr["Wp_y"] == pytest.approx(pu.Wp_interno_formula(c2, c1, d), rel=2e-3)
    assert pr["xc"] == pytest.approx(0.0, abs=1e-9)


def test_contorno_C_e_o_proprio_perimetro_do_pilar():
    pr = pu.propriedades(pu.contorno(0.40, 0.30, 0.0, "interno"))
    assert pr["u"] == pytest.approx(2 * (0.40 + 0.30))


def test_integral_de_e_nao_pode_usar_o_ponto_medio():
    """Regressao do erro que a conferencia pegou: num trecho que vai de -0,2 a
    +0,2 a integral de |e| vale 0,04 e nao zero."""
    assert pu._integral_abs(-0.2, 0.2, 0.4) == pytest.approx(0.04)
    assert pu._integral_abs(0.3, 0.5, 0.2) == pytest.approx(0.08)


def test_contorno_reduzido_de_borda_e_de_canto():
    """19.5.2.3/19.5.2.4: o contorno e interrompido perpendicularmente a borda
    livre; u* fica menor que o do pilar interno e o centroide sai do centro do
    pilar (e por isso que M_Sd1 = M_Sd - F_Sd*e*)."""
    c1, c2, d = 0.40, 0.40, 0.16
    interno = pu.propriedades(pu.contorno(c1, c2, 2 * d, "interno"))
    borda = pu.propriedades(pu.contorno(c1, c2, 2 * d, "borda", d=d))
    canto = pu.propriedades(pu.contorno(c1, c2, 2 * d, "canto", d=d))
    assert canto["u"] < borda["u"] < interno["u"]
    assert abs(borda["xc"]) > 1e-3 and abs(borda["yc"]) == pytest.approx(0.0, abs=1e-9)
    assert abs(canto["xc"]) > 1e-3 and abs(canto["yc"]) > 1e-3


def test_corte_do_contorno_e_o_menor_entre_1_5d_e_meio_C1():
    """Com C1 pequeno, quem manda e 0,5*C1; com C1 grande, 1,5d."""
    d = 0.20
    curto = pu.propriedades(pu.contorno(0.20, 0.40, 2 * d, "borda", d=d))["u"]
    longo = pu.propriedades(pu.contorno(1.20, 0.40, 2 * d, "borda", d=d))["u"]
    # o corte a 0,5*C1 = 0,10 m e mais severo que o corte a 1,5d = 0,30 m
    assert curto < longo


def test_abertura_a_menos_de_8d_desconta_trecho_do_contorno():
    """19.5.1: o trecho entre as retas que passam pelo centro do pilar e
    tangenciam a abertura nao entra em C'."""
    c1 = c2 = 0.40
    d = 0.16
    segs = pu.contorno(c1, c2, 2 * d, "interno")
    u0 = pu.propriedades(segs)["u"]
    perto, cortou = pu.remove_abertura(segs, (0.50, 0.80, -0.15, 0.15), d)
    assert cortou is True and pu.propriedades(perto)["u"] < u0
    longe, cortou2 = pu.remove_abertura(segs, (3.0, 3.4, -0.15, 0.15), d)
    assert cortou2 is False and pu.propriedades(longe)["u"] == pytest.approx(u0)


def test_geometria_invalida_levanta_erro():
    with pytest.raises(ValueError):
        pu.contorno(0.0, 0.40, 0.30)
    with pytest.raises(ValueError):
        pu.contorno(0.40, 0.40, 0.30, "flutuante")
    with pytest.raises(ValueError):
        pu.tau_rd1(0.0, 0.01, FCK)
    with pytest.raises(ValueError):
        pu.fywd_de_projeto(FYK, "arame")
    with pytest.raises(ValueError):
        pu.verifica_puncao(_base(F_sd=0.0))


# ---------------------------------------------------------------------------
# 2. Expressoes de resistencia (recalculadas a partir do texto da norma)
# ---------------------------------------------------------------------------

def test_tau_rd2_e_a_expressao_de_19_5_3_1():
    """tau_Rd2 = 0,27*(1 - fck/250)*fcd."""
    for fck in (20e3, 30e3, 50e3):
        assert pu.tau_rd2(fck) == pytest.approx(
            0.27 * (1 - fck / 1000.0 / 250.0) * fck / 1.4)


def test_tau_rd1_e_a_expressao_de_19_5_3_2():
    """tau_Rd1 = 0,13*(1+raiz(20/d[cm]))*(100*rho*fck[MPa])^(1/3) + 0,10*sigma_cp."""
    d, rho, fck, scp = 0.16, 0.0075, 30e3, 500.0
    esperado = (0.13 * (1 + math.sqrt(20.0 / 16.0)) * (100 * rho * 30) ** (1 / 3.0)
                * 1000.0 + 0.10 * scp)
    assert pu.tau_rd1(d, rho, fck, scp) == pytest.approx(esperado)


def test_tau_rd3_e_a_expressao_de_19_5_3_3():
    """tau_Rd3 = 0,10*(...) + 0,10*sigma_cp + 1,5*(d/sr)*Asw*fywd*sen(a)/(u*d)."""
    d, rho, fck = 0.16, 0.0075, 30e3
    Asw, fywd, sr, u = 6e-4, 300e3, 0.10, 3.6
    esperado = (0.10 * (1 + math.sqrt(20.0 / 16.0)) * (100 * rho * 30) ** (1 / 3.0)
                * 1000.0 + 1.5 * (d / sr) * Asw * fywd * 1.0 / (u * d))
    assert pu.tau_rd3(d, rho, fck, Asw, fywd, sr, u) == pytest.approx(esperado)
    # a parcela do concreto de tau_Rd3 (0,10) e MENOR que a de tau_Rd1 (0,13)
    assert pu.tau_rd3(d, rho, fck, 0.0, 0.0, 0.0, u) < pu.tau_rd1(d, rho, fck)


def test_K_da_tabela_19_2():
    assert pu.K_puncao(0.5) == 0.45
    assert pu.K_puncao(1.0) == 0.60
    assert pu.K_puncao(2.0) == 0.70
    assert pu.K_puncao(3.0) == 0.80
    assert pu.K_puncao(1.5) == pytest.approx(0.65)     # interpolado
    assert pu.K_puncao(0.1) == 0.45 and pu.K_puncao(9.0) == 0.80   # limitado


def test_fywd_tem_teto_e_avisa_quando_satura():
    """19.5.3.3: 300 MPa (stud) e 250 MPa (estribo). CA-50 daria 435 MPa - deixar
    o corte calado seria contar com um aco que a norma nao deixa usar."""
    stud = pu.fywd_de_projeto(FYK, "stud")
    estribo = pu.fywd_de_projeto(FYK, "estribo")
    assert stud["fywd"] == 300e3 and stud["saturou"] is True
    assert estribo["fywd"] == 250e3 and estribo["saturou"] is True
    baixo = pu.fywd_de_projeto(250e3, "stud")
    assert baixo["fywd"] == pytest.approx(250e3 / 1.15) and baixo["saturou"] is False


def test_primitivas_sao_as_mesmas_da_sapata():
    """REUSO: fundacao_sapata passou a consumir este modulo - nao pode haver duas
    implementacoes da mesma tensao resistente."""
    assert fs._K_puncao(1.5) == pu.K_puncao(1.5)
    r = fs.puncao_sapata(500.0, 2.0, 2.0, 0.30, 0.30, 0.40, FCK, 20e-4, 20e-4)
    assert r["tau_rd1"] == pytest.approx(pu.tau_rd1(0.40, r["rho"], FCK))


# ---------------------------------------------------------------------------
# 3. Orquestrador: verificacoes e gates
# ---------------------------------------------------------------------------

def test_ligacao_folgada_atende():
    r = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=20e-4))
    assert r["dispensa_armadura"] is True and r["OK"] is True
    assert r["u_puncao"] < 1.0 and r["u_biela"] < 1.0


def test_carga_alta_exige_armadura_e_a_armadura_resolve():
    sem = pu.verifica_puncao(_base(F_sd=900.0, As_ccp=40e-4))
    assert sem["dispensa_armadura"] is False and sem["OK"] is False
    com = pu.verifica_puncao(_base(
        F_sd=900.0, As_ccp=40e-4,
        armadura={"Asw": 8e-4, "sr": 0.10, "s0": 0.07, "tipo": "stud",
                  "n_contornos": 5}))
    assert com["armadura"]["tau_rd3"] > com["tau_rd1"]
    assert com["OK"] is True


def test_biela_esgotada_nao_e_resolvida_por_armadura():
    """19.5.3.1: se tau_Sd > tau_Rd2 no contorno C, nao adianta armar."""
    r = pu.verifica_puncao(_base(
        F_sd=3000.0, As_ccp=200e-4,
        armadura={"Asw": 40e-4, "sr": 0.10, "s0": 0.07, "n_contornos": 8}))
    assert r["ok_biela"] is False and r["OK"] is False
    assert any("compressao diagonal" in a for a in r["avisos"])


def test_espacamento_radial_e_primeira_linha_reprovam():
    r = pu.verifica_puncao(_base(
        F_sd=700.0, As_ccp=40e-4,
        armadura={"Asw": 12e-4, "sr": 0.20, "s0": 0.15, "n_contornos": 4}))
    assert r["armadura"]["ok_sr"] is False and r["armadura"]["ok_s0"] is False
    assert r["OK"] is False


def test_contorno_C_duas_linhas_precisa_de_linhas_suficientes():
    """19.5.3.4: com poucas linhas de conectores, o C'' (2d alem da ultima)
    ainda tem tau_Sd > tau_Rd1 - e o gate tem de acusar."""
    poucas = pu.verifica_puncao(_base(
        F_sd=900.0, As_ccp=40e-4,
        armadura={"Asw": 12e-4, "sr": 0.10, "s0": 0.07, "n_contornos": 1}))
    muitas = pu.verifica_puncao(_base(
        F_sd=900.0, As_ccp=40e-4,
        armadura={"Asw": 12e-4, "sr": 0.10, "s0": 0.07, "n_contornos": 6}))
    assert poucas["armadura"]["ok_c2linha"] is False and poucas["OK"] is False
    assert muitas["armadura"]["ok_c2linha"] is True and muitas["OK"] is True


def test_gate_19_5_3_5_armadura_obrigatoria_mesmo_passando_na_tensao():
    """SATURACAO SILENCIOSA: a ligacao passa folgada em tau_Sd <= tau_Rd1, mas se
    a estabilidade global depende da laje a armadura e OBRIGATORIA (>= 50% de
    F_Sd). Sem gate proprio isso sai OK=True, porque nao aparece em razao
    nenhuma de solicitante/resistente."""
    calado = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=20e-4))
    assert calado["OK"] is True and calado["dispensa_armadura"] is True

    exigente = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=20e-4,
                                        estabilidade_depende_laje=True))
    assert exigente["dispensa_armadura"] is True     # a tensao continua folgada
    assert exigente["ok_19_5_3_5"] is False and exigente["OK"] is False
    assert any("19.5.3.5" in a for a in exigente["avisos"])

    # 50% de 250 kN = 125 kN ; Asw*fywd = 5 cm2 * 300 MPa = 150 kN -> atende
    armado = pu.verifica_puncao(_base(
        F_sd=250.0, As_ccp=20e-4, estabilidade_depende_laje=True,
        armadura={"Asw": 5e-4, "sr": 0.10, "s0": 0.07, "n_contornos": 3}))
    assert armado["ok_19_5_3_5"] is True and armado["OK"] is True


def test_gate_19_5_4_colapso_progressivo():
    """SATURACAO SILENCIOSA: fyd*As,ccp >= 1,5*F_Sd tambem nao aparece como razao
    de tensao. Com a armadura inferior insuficiente, a ligacao NAO atende ainda
    que a puncao esteja folgada."""
    r = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=1e-4))
    assert r["dispensa_armadura"] is True
    assert r["ok_colapso"] is False and r["OK"] is False
    esperado = 1.5 * 250.0 / (FYK / 1.15)
    assert r["As_ccp_min"] == pytest.approx(esperado)
    # sem declarar nada tambem reprova (ausencia nao e conformidade)
    sem = pu.verifica_puncao({k: v for k, v in _base(F_sd=250.0).items()
                              if k != "As_ccp"})
    assert sem["ok_colapso"] is False


def test_19_5_4_admite_gamma_f_1_2():
    com = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=20e-4, usar_gf_1_2=True))
    sem = pu.verifica_puncao(_base(F_sd=250.0, As_ccp=20e-4))
    assert com["As_ccp_min"] == pytest.approx(sem["As_ccp_min"] * 1.2 / 1.4)


def test_momento_aumenta_a_tensao_e_borda_e_pior_que_interno():
    sem_M = pu.verifica_puncao(_base(F_sd=400.0))
    com_M = pu.verifica_puncao(_base(F_sd=400.0, M_sd_x=60.0))
    assert com_M["tau_sd"] > sem_M["tau_sd"]
    borda = pu.verifica_puncao(_base(F_sd=400.0, M_sd_x=60.0, tipo="borda"))
    assert borda["u"] < com_M["u"] and borda["tau_sd"] > com_M["tau_sd"]
    # no contorno reduzido o momento e aliviado por F_Sd*e* (19.5.2.3)
    assert borda["e_estrela"] > 0 and borda["M_sd1_efetivo"] < abs(borda["M_sd_x"])


def test_rho_zero_avisa_e_reprova():
    r = pu.verifica_puncao(_base(F_sd=400.0, As_x=0.0, As_y=0.0))
    assert r["tau_rd1"] == 0.0 and r["OK"] is False
    assert any("rho = 0" in a for a in r["avisos"])


def test_relatorio_pt_sai_completo():
    r = pu.verifica_puncao(_base(
        F_sd=900.0, As_ccp=40e-4,
        armadura={"Asw": 8e-4, "sr": 0.10, "s0": 0.07, "n_contornos": 5}))
    txt = pu.relatorio_pt(r)
    for pedaco in ("PUNCAO", "Contorno C", "Contorno C'", "tau_Rd3", "RESULTADO"):
        assert pedaco in txt
