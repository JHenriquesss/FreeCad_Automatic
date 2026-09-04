"""Pilar de concreto em flexao composta (NBR 6118:2014) - pilar_concreto.py.

Afericao contra 3 exemplos RESOLVIDOS de Bastos (UNESP, 'Pilares de Concreto
Armado', C30/CA-50), lidos do PDF - nao de memoria:
  - Ex.1: intermediario 20x50, Nk=1000, le=280 -> Md,tot,y=5320 kN.cm, As=10,84 cm2
  - Ex.2: idem, le=480 -> Md,tot,y=9940 kN.cm, As=31,03 cm2
  - Ex.5: extremidade 15x40, Nk=500, M1d,A,x=3500 M1d,B,x=2000 -> alpha_b=0,83, gamma_n=1,20
O solver de resistencia usa o diagrama parabola-retangulo (referencia dos abacos
de pilar); tolerancia de leitura de abaco ~+-5%.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pilar_concreto as pc


# ------------------------------------------------------------------ Ex.1
def test_ex1_intermediario_esbeltez_e_2a_ordem():
    r = pc.dimensiona_pilar({"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 2.80,
                             "le_y": 2.80, "fck": 30e3, "fyk": 500e3, "dl": 0.04})
    dy = r["dir"]["y"]
    assert abs(dy["lambda"] - 48.4) < 0.3          # lambda_y = raiz(12)*280/20
    assert dy["lambda1"] == 35.0                   # e1=0 -> piso 35
    assert not r["dir"]["x"]["considera_2a"]       # lambda_x=19,4 < 35
    assert dy["considera_2a"]                       # lambda_y=48,4 > 35
    assert abs(r["nu"] - 0.65) < 0.01
    assert abs(dy["e2_cm"] - 1.70) < 0.05          # excentricidade de 2a ordem
    assert abs(dy["M2d"] - 23.8) < 0.3             # M2d,y = 2380 kN.cm


def test_ex1_momento_total_e_armadura():
    r = pc.dimensiona_pilar({"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 2.80,
                             "le_y": 2.80, "fck": 30e3, "fyk": 500e3, "dl": 0.04})
    assert abs(r["Md_gov"] - 53.2) < 0.3           # 2940 + 2380 = 5320 kN.cm
    assert abs(r["As_cm2"] - 10.84) < 0.6          # abaco A-4: omega=0,22


# ------------------------------------------------------------------ Ex.2
def test_ex2_pilar_mais_alto_le480():
    r = pc.dimensiona_pilar({"b": 0.20, "h": 0.50, "Nk": 1000.0, "le_x": 4.80,
                             "le_y": 4.80, "fck": 30e3, "fyk": 500e3, "dl": 0.04})
    assert abs(r["dir"]["y"]["lambda"] - 83.0) < 0.3
    assert abs(r["dir"]["y"]["e2_cm"] - 5.00) < 0.1
    assert abs(r["Md_gov"] - 99.4) < 0.5           # 2940 + 7000 = 9940 kN.cm
    assert abs(r["As_cm2"] - 31.03) < 2.0          # abaco: omega=0,63


# ------------------------------------------------------------------ Ex.5
def test_ex5_extremidade_alpha_b_e_gamma_n():
    r = pc.dimensiona_pilar({"b": 0.40, "h": 0.15, "Nk": 500.0, "le_x": 2.80,
                             "le_y": 2.80, "fck": 30e3, "fyk": 500e3, "dl": 0.03,
                             "M1d_x": {"tipo": "biapoiado", "Ma": 35.0, "Mb": 20.0}})
    assert abs(r["Nd"] - 840.0) < 1.0              # gamma_n*gamma_f*Nk = 1,2*1,4*500
    assert abs(r["gamma_n"] - 1.20) < 1e-6         # b=15 cm -> 1,95-0,05*15
    dx = r["dir"]["x"]
    assert abs(dx["alpha_b"] - 0.83) < 0.01        # 0,6+0,4*(2000/3500)
    assert abs(dx["e1_cm"] - 4.17) < 0.05          # 3500/840
    assert abs(dx["Md_tot"] - 48.0) < 0.6          # ~4805 kN.cm


# ------------------------------------------------------------------ formulas isoladas
def test_gamma_n_tabela_13_1():
    assert pc.gamma_n(19.0) == 1.0
    assert abs(pc.gamma_n(14.0) - 1.25) < 1e-9     # 1,95-0,05*14
    assert abs(pc.gamma_n(15.0) - 1.20) < 1e-9


def test_gamma_n_abaixo_de_14_erro():
    import pytest
    with pytest.raises(ValueError):
        pc.gamma_n(13.0)


def test_lambda1_faixa_35_90():
    # e1=0 -> (25)/1 = 25 -> piso 35 ; e1 grande -> teto 90
    assert pc.lambda_1(0.0, 0.20, 1.0) == 35.0
    assert pc.lambda_1(2.0, 0.20, 0.4) == 90.0


def test_alpha_b_balanco_piso_085():
    # pilar em balanco (galpao pre-moldado): 0,80+0,20*Mc/Ma, piso 0,85
    ab = pc.alpha_b({"tipo": "balanco", "Ma": 100.0, "Mc": 0.0})
    assert abs(ab - 0.85) < 1e-9                    # 0,80 -> piso 0,85
    assert pc.alpha_b({"tipo": "balanco", "Ma": 0.0}) == 1.0   # sem M1 -> 1,0


def test_curvatura_limitada():
    # 1/r = 0,005/[h(nu+0,5)] <= 0,005/h
    inv_r = pc.curvatura(0.20, 0.65)
    assert abs(inv_r - 0.005 / (0.20 * 1.15)) < 1e-9
    # nu muito baixo -> limitado por 0,005/h
    assert abs(pc.curvatura(0.20, 0.0) - 0.005 / 0.20) < 1e-9


def test_resistencia_pura_compressao_e_flexao_bracket():
    # M=0: NRd ~ 0,85 fcd Ac + As fyd (compressao centrada), bracket do solver
    b, h, dl, fck, fyk = 0.30, 0.30, 0.04, 30e3, 500e3
    As = 12e-4
    MRd0 = pc.MRd_para_Nd(0.0, As, b, h, dl, fck, fyk)
    assert MRd0 > 0                                 # so N=0: ha capacidade de M
    # aumentar As aumenta MRd para o mesmo Nd (monotonia usada na bisseccao)
    Nd = 800.0
    m_lo = pc.MRd_para_Nd(Nd, 4e-4, b, h, dl, fck, fyk)
    m_hi = pc.MRd_para_Nd(Nd, 30e-4, b, h, dl, fck, fyk)
    assert m_hi > m_lo


def test_secao_insuficiente_reprova():
    # secao minima sob N e M altos: nem As_max resiste -> resiste=False
    r = pc.dimensiona_pilar({"b": 0.14, "h": 0.14, "Nk": 1500.0, "le_x": 3.0,
                             "le_y": 3.0, "fck": 25e3, "fyk": 500e3, "dl": 0.03})
    assert r["OK"] is False


def test_g44_asw_dimensionado_quando_minimo_nao_basta():
    # G44: biela OK mas VRd3,min insuficiente -> o fuste DIMENSIONA o estribo
    # (Asw/s) em vez de reprovar sem saida (G39 verificava e reprovava).
    r = pc.dimensiona_pilar({"b": 0.25, "h": 0.50, "Nk": 800.0, "le_x": 4.0,
                             "le_y": 4.0, "fck": 30e3, "fyk": 500e3, "dl": 0.04,
                             "Vd": 250.0,
                             "M1d_x": {"tipo": "balanco", "Ma": 80.0}})
    assert r["ok_biela"] is True and r["ok_min"] is False   # minimo nao basta
    assert r["cort_ok"] is True and r["OK"] is True         # mas o Asw resolve
    assert r["VRd3"] >= r["Vd"] - 1e-6
    assert r["Asw_s_cm2_m"] >= r["Asw_s_min_cm2_m"] + 1.0   # acima do minimo
    assert abs(r["Asw_s_cm2_m"] - 8.34) < 0.15              # (Vd-Vc)/(0,9*d*fywd)
    assert r["Asw_prov_cm2_m"] >= r["Asw_s_cm2_m"] - 1e-9   # phi c/s entrega
    assert r["s_estribo"] <= r["s_estribo_max"] + 1e-9


def test_g44_biela_esmagada_continua_reprovando():
    # G44 nao salva biela: Vd > VRd2 -> so aumenta a secao (fail-closed).
    r = pc.dimensiona_pilar({"b": 0.25, "h": 0.50, "Nk": 800.0, "le_x": 4.0,
                             "le_y": 4.0, "fck": 30e3, "fyk": 500e3, "dl": 0.04,
                             "Vd": 700.0,
                             "M1d_x": {"tipo": "balanco", "Ma": 80.0}})
    assert r["u_biela"] > 1.0
    assert r["cort_ok"] is False and r["OK"] is False


def test_g44b_asw_acima_do_detalhavel_reprova_em_vez_de_saturar():
    # G44b (achado na revisao do G44): a tabela de estribo do fuste tem TETO -
    # 2 ramos, phi 10 c/5 cm = 31,4 cm2/m - e ha secao CORRENTE cujo Asw
    # necessario passa disso ANTES de a biela esmagar. O fallback devolvia o
    # teto e `cort_ok` olhava so a biela: estribo 23% abaixo do necessario,
    # com OK=True e o phi 10 c/5 indo para o quadro de aco. Pior, o caso
    # REPROVAVA antes do G44 (cort_ok = ok_biela and ok_min): a saturacao
    # silenciosa transformou um vermelho em verde.
    r = pc.dimensiona_pilar({"b": 0.40, "h": 0.40, "Nk": 900.0, "le": 3.0,
                             "fck": 30e3, "fyk": 500e3, "Vd": 700.0})
    assert r["u_biela"] < 1.0 and r["ok_biela"] is True   # biela AGUENTA
    assert r["Asw_s_cm2_m"] > r["Asw_prov_cm2_m"]         # detalhamento nao cobre
    assert r["Asw_atendido"] is False
    assert r["cort_ok"] is False and r["OK"] is False     # fail-closed
    assert "excede" in pc.relatorio_pt(r)


def test_g44b_prov_nunca_menor_que_req_sem_reprovar():
    # A guarda generica: varrer secoes/fck e exigir que NENHUM caso saia com
    # Asw_prov < Asw_req e cort_ok=True. E' a forma de o teto da tabela nunca
    # mais virar "OK" em silencio quando a lista de bitolas mudar.
    for fck in (20e3, 25e3, 30e3, 40e3):
        for (b, h) in ((0.20, 0.40), (0.25, 0.50), (0.30, 0.60), (0.40, 0.40),
                       (0.50, 0.50)):
            VRd2 = pc.verifica_cortante_pilar(0.0, b, max(h - 0.04, 0.5 * h),
                                              fck, 500e3)["VRd2"]
            for frac in (0.3, 0.6, 0.8, 0.95, 0.999):
                r = pc.dimensiona_pilar({"b": b, "h": h, "Nk": 500.0, "le": 3.0,
                                         "fck": fck, "fyk": 500e3,
                                         "Vd": frac * VRd2})
                if r["Asw_prov_cm2_m"] < r["Asw_s_cm2_m"] - 1e-9:
                    assert r["cort_ok"] is False, (
                        "%.0fx%.0f fck%.0f Vd=%.0f%% VRd2: prov %.2f < req %.2f "
                        "e cort_ok=True (saturacao silenciosa)"
                        % (b * 100, h * 100, fck / 1000, frac * 100,
                           r["Asw_prov_cm2_m"], r["Asw_s_cm2_m"]))


def test_selftest_roda():
    pc._selftest()
