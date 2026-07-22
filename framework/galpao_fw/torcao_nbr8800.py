# ============================================================================
# torcao_nbr8800.py - TORCAO e efeitos combinados, NBR 8800:2008 item 5.5.2
# (o item 5.6 e "barras de secao variavel" -> Anexo J; a torcao esta no 5.5.2).
#
# SECAO FECHADA (tubular retangular/circular) - 5.5.2.1/5.5.2.2:
#   Trd fechado (fy, Wt, ga1); se Tsd <= 0,20 Trd a torcao pode ser desprezada;
#   senao interacao (5.5.2.2):  N/Nrd + M/Mrd + (V/Vrd + T/Trd)^2 <= 1,0.
#
# SECAO ABERTA (perfil I, U) - 5.5.2.3 "secoes quaisquer": a NBR NAO da Trd
#   fechado; exige verificacao por TENSOES (teoria da elasticidade):
#     a) tensao normal:      sigma_Sd <= fy/ga1
#     b) tensao cisalhamento: tau_Sd  <= 0,60 fy/ga1
#   A tensao de cisalhamento de Saint-Venant e tau_t = Tsd*t_max/J (torcao
#   uniforme). A tensao NORMAL de EMPENAMENTO (sigma_w) exige analise de flexo-
#   torcao (bimomento) que a NBR nao formula -> quando a torcao no perfil aberto
#   NAO for desprezivel, ESTE modulo sinaliza que a analise de empenamento e
#   necessaria (nao a fabrica). Valores/itens lidos do PDF via NotebookLM.
# ============================================================================
"""Torcao e efeitos combinados (NBR 8800 5.5.2)."""

from __future__ import annotations

import math

GA1 = 1.10                        # coeficiente de ponderacao da resistencia (aco)


# --- propriedades de torcao --------------------------------------------------
def J_perfil_I(bf, tf, d, tw):
    """Constante de torcao de Saint-Venant de um perfil I (paredes finas
    abertas): J = (1/3) * sum(b_i * t_i^3) = (2*bf*tf^3 + (d-2tf)*tw^3)/3.
    Unidades SI (m). Retorna J (m^4) e t_max (m)."""
    hw = max(d - 2.0 * tf, 0.0)
    J = (2.0 * bf * tf ** 3 + hw * tw ** 3) / 3.0
    return J, max(tf, tw)


def Wt_tubular_retangular(H, B, t):
    """Modulo de resistencia a torcao de tubo retangular (parede fina):
    Wt ~= 2 * (H - t) * (B - t) * t (analogia de Bredt). SI (m)."""
    return 2.0 * (H - t) * (B - t) * t


# --- secao fechada (5.5.2.1 / 5.5.2.2) ---------------------------------------
def Trd_tubular_retangular(H, B, t, fy, E=200e6):
    """Momento de torcao resistente de calculo de secao tubular RETANGULAR
    (5.5.2.1.3), 3 faixas de esbeltez da parede (h/t). h = maior lado plano.
    Retorna Trd (kN.m). fy, E em kN/m2 ; dimensoes em m."""
    Wt = Wt_tubular_retangular(H, B, t)
    h = max(H, B) - t                        # lado plano governante (~lado - t)
    lam = (h / t) * math.sqrt(fy / E)        # h/t * sqrt(fy/E) (adimensional)
    r = math.sqrt(E / fy)
    if (h / t) <= 2.45 * r:
        Trd = 0.60 * fy * Wt / GA1
    elif (h / t) <= 3.07 * r:
        Trd = 0.60 * fy * Wt / GA1 * (2.45 * r / (h / t))
    else:                                    # 3,07 < h/t <= 260 (parede esbelta)
        Trd = 0.458 * (math.pi ** 2) * E * Wt / ((h / t) ** 2) / GA1
    return Trd


def interacao_tubular(Nsd, Nrd, Msd, Mrd, Vsd, Vrd, Tsd, Trd):
    """Interacao 5.5.2.2 (secao tubular): N/Nrd + M/Mrd + (V/Vrd + T/Trd)^2 <= 1.
    Se Tsd <= 0,20 Trd a torcao pode ser desprezada (retorna desprezivel=True)."""
    desprezivel = abs(Tsd) <= 0.20 * Trd + 1e-12
    u = (abs(Nsd) / Nrd if Nrd else 0.0) + (abs(Msd) / Mrd if Mrd else 0.0) + \
        ((abs(Vsd) / Vrd if Vrd else 0.0) + (abs(Tsd) / Trd if Trd else 0.0)) ** 2
    return {"desprezivel": desprezivel, "u": u, "OK": u <= 1.0 + 1e-9,
            "Trd": Trd, "criterio_desprezar": 0.20 * Trd}


# --- secao aberta (5.5.2.3, por tensoes) -------------------------------------
def verifica_torcao_aberta(Tsd, J, t_max, fy, sigma_normal_Sd=0.0):
    """Verificacao por TENSOES (5.5.2.3) de perfil ABERTO (I/U) sob torcao.
      tau_t = Tsd * t_max / J      (Saint-Venant, torcao uniforme)   [kN/m2]
      a) sigma_Sd <= fy/ga1   b) tau_Sd <= 0,60 fy/ga1
    Tsd em kN.m ; J em m^4 ; t_max em m ; fy em kN/m2. sigma_normal_Sd = tensao
    normal concomitante (flexao/axial) no ponto verificado, se informada.
    A torcao e DESPREZIVEL se tau_t <= 0,20*(0,60 fy/ga1). Caso contrario, a
    tensao de EMPENAMENTO (sigma_w) do perfil aberto NAO e coberta pela NBR
    (teoria da elasticidade/flexo-torcao) -> exige_analise_empenamento=True."""
    tau_t = abs(Tsd) * t_max / J if J else float("inf")   # kN/m2
    tau_rd = 0.60 * fy / GA1
    sig_rd = fy / GA1
    desprezivel = tau_t <= 0.20 * tau_rd + 1e-9
    u_tau = tau_t / tau_rd if tau_rd else float("inf")
    u_sig = abs(sigma_normal_Sd) / sig_rd if sig_rd else 0.0
    return {
        "tau_t": tau_t, "tau_rd": tau_rd, "u_tau": u_tau,
        "sigma_Sd": abs(sigma_normal_Sd), "sigma_rd": sig_rd, "u_sigma": u_sig,
        "desprezivel": desprezivel,
        "exige_analise_empenamento": (not desprezivel),
        "OK": (u_tau <= 1.0 + 1e-9 and u_sig <= 1.0 + 1e-9 and desprezivel),
        "flag": (
            "Torcao (5.5.2.3, perfil aberto): tau_t=%.1f MPa <= %.1f -> DESPREZIVEL "
            "(<=20%% do limite); torcao de empenamento nao governa." %
            (tau_t / 1000.0, tau_rd / 1000.0) if desprezivel else
            "Torcao (5.5.2.3, perfil aberto): tau_t=%.1f MPa (u=%.2f) NAO desprezivel "
            "-> exige analise de FLEXO-TORCAO (empenamento/bimomento, teoria da "
            "elasticidade; a NBR nao formula) OU eliminar a excentricidade. NAO ATENDE "
            "ate a analise." % (tau_t / 1000.0, u_tau)),
    }


def torque_carga_excentrica(carga_kN_m, excentricidade_m):
    """Torque distribuido (kN.m/m) de uma carga vertical (kN/m) aplicada a uma
    excentricidade (m) do centro de torcao - ex.: fachada pesada presa na mesa
    externa da coluna. Multiplicar pelo comprimento p/ o torque total, ou usar
    o momento de torcao maximo = torque_distribuido * L / 2 (barra biapoiada a
    torcao) conforme o modelo. Aqui retorna so o torque distribuido."""
    return abs(carga_kN_m) * abs(excentricidade_m)


def _selftest():
    # --- perfil aberto: torcao desprezivel (carga no plano da alma) -----------
    J, tmax = J_perfil_I(bf=0.20, tf=0.012, d=0.20, tw=0.008)
    assert J > 0 and abs(tmax - 0.012) < 1e-9
    r0 = verifica_torcao_aberta(Tsd=0.0, J=J, t_max=tmax, fy=250e3)
    assert r0["desprezivel"] and r0["OK"] and not r0["exige_analise_empenamento"]
    # torcao significativa em perfil aberto -> exige analise de empenamento
    r1 = verifica_torcao_aberta(Tsd=5.0, J=J, t_max=tmax, fy=250e3)
    assert not r1["desprezivel"] and r1["exige_analise_empenamento"] and not r1["OK"]
    assert "FLEXO-TORCAO" in r1["flag"]
    # tau_t = Tsd*t/J confere
    assert abs(r1["tau_t"] - 5.0 * tmax / J) < 1e-6
    # --- secao fechada (tubular): Trd e interacao -----------------------------
    Trd = Trd_tubular_retangular(H=0.20, B=0.20, t=0.008, fy=250e3)
    assert Trd > 0
    # torcao pequena -> desprezivel (<=0,20 Trd) e interacao passa
    it = interacao_tubular(Nsd=100.0, Nrd=800.0, Msd=20.0, Mrd=90.0,
                           Vsd=30.0, Vrd=300.0, Tsd=0.10 * Trd, Trd=Trd)
    assert it["desprezivel"] and it["OK"]
    # torcao grande -> nao desprezivel; termo quadratico cresce
    it2 = interacao_tubular(Nsd=100.0, Nrd=800.0, Msd=20.0, Mrd=90.0,
                            Vsd=200.0, Vrd=300.0, Tsd=0.8 * Trd, Trd=Trd)
    assert not it2["desprezivel"] and it2["u"] > it["u"]
    # tubo de parede fina (h/t alto) -> Trd cai vs parede espessa
    Trd_fina = Trd_tubular_retangular(H=0.30, B=0.30, t=0.004, fy=250e3)
    Trd_grossa = Trd_tubular_retangular(H=0.30, B=0.30, t=0.012, fy=250e3)
    assert Trd_grossa > Trd_fina
    # torque de carga excentrica
    assert abs(torque_carga_excentrica(10.0, 0.15) - 1.5) < 1e-9
    print("torcao_nbr8800 _selftest PASSED")


if __name__ == "__main__":
    _selftest()
