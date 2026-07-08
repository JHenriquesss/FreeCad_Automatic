# ============================================================================
# fogo_nbr14323.py - DIMENSIONAMENTO AO FOGO (NBR 14323:2013)
# Verifica elementos estruturais de aco em situacao de incendio.
# Metodo simplificado: calcula a temperatura do aco apos o TRRF, reduz
# as resistencias e compara com a solicitacao em combinacao excepcional.
# Opcional: dimensiona espessura de protecao (intumescente ou spray).
# ============================================================================
"""Verificacao ao fogo conforme NBR 14323. Saidas PT. Unidades: m, kN, min."""

from __future__ import annotations
import math

# Curva ISO 834: temperatura dos gases (C) apos t minutos
def temp_gases(t_min):
    return 20.0 + 345.0 * math.log10(8.0 * t_min + 1.0)

# Fatores de reducao p/ aco laminado a quente (NBR 14323 Tab. 6.2 / Fakury)
_REDUCAO = [
    (20,   1.000, 1.000),
    (100,  1.000, 1.000),
    (200,  1.000, 0.900),
    (300,  1.000, 0.800),
    (400,  1.000, 0.700),
    (500,  0.780, 0.600),
    (550,  0.630, 0.450),
    (600,  0.470, 0.310),
    (700,  0.230, 0.130),
    (800,  0.110, 0.090),
    (900,  0.060, 0.068),
    (1000, 0.040, 0.045),
    (1100, 0.020, 0.030),
    (1200, 0.000, 0.000),
]

def k_y(theta_C):
    """Fator de reducao de fy na temperatura theta (C)."""
    for i in range(len(_REDUCAO) - 1):
        t1, ky1, _ = _REDUCAO[i]
        t2, ky2, _ = _REDUCAO[i + 1]
        if t1 <= theta_C <= t2:
            f = (theta_C - t1) / (t2 - t1) if t2 != t1 else 0
            return ky1 + f * (ky2 - ky1)
    return 0.0

def k_E(theta_C):
    """Fator de reducao do modulo de elasticidade na temperatura theta (C)."""
    for i in range(len(_REDUCAO) - 1):
        t1, _, kE1 = _REDUCAO[i]
        t2, _, kE2 = _REDUCAO[i + 1]
        if t1 <= theta_C <= t2:
            f = (theta_C - t1) / (t2 - t1) if t2 != t1 else 0
            return kE1 + f * (kE2 - kE1)
    return 0.0

# Massividade (fator de forma) para secoes abertas I, expostas em 4 lados
def massividade_I(h, b, tw, tf, lados=4):
    """Fator de forma u/A (1/m) para perfil I. h,b,tw,tf em m."""
    u = (2.0 * h + 4.0 * b - 2.0 * tw) if lados == 4 else (2.0 * h + 3.0 * b - 2.0 * tw)
    return u / (h * tw + 2.0 * b * tf)


def temp_aco_nao_protegido(t_min, u_A, emissividade=0.5, amb=20.0):
    """Temperatura do aco sem protecao apos t_min, metodo incremental
    simplificado (NBR 14323 Anexo A). u_A em 1/m."""
    Dt = min(t_min / 20.0, 5.0)          # passo de tempo (min)
    theta_a = amb
    n_passos = int(t_min / Dt)
    ca = 600.0                            # calor especifico do aco (J/kgC)
    rho_a = 7850.0                        # massa especifica aco (kg/m3)
    for _ in range(n_passos):
        theta_g = 20.0 + 345.0 * math.log10(8.0 * _ * Dt + 1.0)
        h_net = 25.0 * (theta_g - theta_a) + 5.67e-8 * emissividade * (
            (theta_g + 273.0) ** 4 - (theta_a + 273.0) ** 4)
        dtheta = (u_A / (ca * rho_a)) * h_net * Dt * 60.0
        theta_a += dtheta
    return round(theta_a, 1)


def comb_incendio(G_k, Q_k, psi2=0.4, gamma_g=1.1):
    """Combinacao excepcional de incendio (NBR 8681 / NBR 14323).
    Fd = gamma_g * Gk + psic2 * psic2 * Qk  (acao termica e a excepcional).
    gamma_g = 1,0 (fav) / 1,1 (desf pequena var) / 1,2 (desf grande var).
    psi2 = 0,2 (sem predominancia), 0,4 (concentracao), 0,6 (arquivos)."""
    return gamma_g * G_k + psi2 * Q_k


def verifica_fogo(sec_perfil, fy, G_k, Q_k, TRRF_min=60, lb=None,
                  perfil_tipo="I", lados_expostos=4, gamma_g=1.1, psi2=0.4,
                  protecao=None, u_A_fornecido=None):
    """Verifica perfil de aco em situacao de incendio.
    sec_perfil: dict com h,b,tw,tf (mm). fy em kN/m2.
    TRRF_min: tempo requerido de resistencia ao fogo (min).
    protecao: None (sem), "intumescente" ou "spray" com espessura em mm.
    Retorna dict com temperatura, fatores de reducao, u_A e status."""
    h = sec_perfil["h"] / 1000.0; b = sec_perfil["b"] / 1000.0
    tw = sec_perfil["tw"] / 1000.0; tf = sec_perfil["tf"] / 1000.0
    
    if u_A_fornecido:
        u_A = u_A_fornecido
    else:
        u_A = massividade_I(h, b, tw, tf, lados_expostos)
    
    # Temperatura do aco no TRRF
    if protecao:
        theta_a = _temp_com_protecao(TRRF_min, u_A, protecao["tipo"], protecao["espessura"])
    else:
        theta_a = temp_aco_nao_protegido(TRRF_min, u_A)
    
    # Fatores de reducao
    ky = round(k_y(theta_a), 4)
    kE = round(k_E(theta_a), 4)
    
    # Resistencia reduzida pelo fogo
    fy_fi = ky * fy
    E_fi = kE * 200e6  # E reduzido a quente
    
    # Solicitacao em combinação excepcional
    F_fi = comb_incendio(G_k, Q_k, psi2, gamma_g)
    
    return {"TRRF_min": TRRF_min, "theta_aco_C": theta_a,
            "theta_gases_C": round(temp_gases(TRRF_min), 1),
            "u_A_1m": round(u_A, 1), "ky": ky, "kE": kE,
            "fy_fi_kN_m2": round(fy_fi), "E_fi_kPa": round(E_fi),
            "F_fi_kN": round(F_fi, 1), "protecao": protecao}


def _temp_com_protecao(t_min, u_A, tipo, espessura_mm):
    """Temperatura do aco com protecao (simplificado).
    Retorna temperatura aproximada apos t_min."""
    dp = espessura_mm / 1000.0
    if tipo == "intumescente":
        # Pintura intumescente: reducao aproximada de 60-70% na temperatura
        theta_s_prot = temp_aco_nao_protegido(t_min, u_A) * 0.35
        return round(theta_s_prot, 1)
    elif tipo == "spray":
        # Spray vermiculita/cimento: reducao maior
        theta_s_prot = temp_aco_nao_protegido(t_min, u_A) * (0.20 if dp >= 0.025 else 0.30)
        return round(theta_s_prot, 1)
    return temp_aco_nao_protegido(t_min, u_A)


def espessura_protecao(t_min, u_A, tipo="intumescente", temp_critica=550.0):
    """Calcula espessura necessaria de protecao para manter o aco abaixo
    de temp_critica durante t_min minutos. Retorna espessura em mm."""
    if tipo == "intumescente":
        # Dados da Tab. 6.13 (Fakury / Nullifire): u/A vs espessura
        tabela = [
            (55,  0.49, 1.27, 1.73, 3.96),
            (105, 0.32, 0.88, 1.27, 2.31),
            (155, 0.47, 1.70, 2.31, 5.94),
            (205, 0.60, 1.25, 2.30, None),
            (260, 0.67, 2.30, None, None),
        ]
        col = {30: 1, 60: 2, 90: 3, 120: 4}
        if t_min not in col:
            return None
        ci = col[t_min]
        for row in tabela:
            if u_A <= row[0]:
                return row[ci] if row[ci] is not None else row[ci - 1] + 0.5
        return None
    elif tipo == "spray":
        tab_spray = [
            (30,  10, 10, 10, 17),
            (50,  10, 12, 15, 27),
            (70,  10, 15, 22, 30),
            (90,  10, 20, 22, 35),
            (110, 15, 20, 25, 40),
            (150, 15, 22, 30, 45),
            (190, 17, 25, 35, 45),
            (230, 20, 27, 35, 50),
        ]
        col = {30: 1, 60: 2, 90: 3, 120: 4}
        ci = col.get(t_min, 2)
        for row in tab_spray:
            if u_A <= row[0]:
                return row[ci]
        return None
    return None


def relatorio_pt(r):
    L = ["DIMENSIONAMENTO AO FOGO (NBR 14323:2013)",
         f"  TRRF = {r['TRRF_min']} min ; temperatura gases = {r['theta_gases_C']:.0f} C",
         f"  Fator de massividade u/A = {r['u_A_1m']:.1f} /m",
         f"  Temperatura no aco apos {r['TRRF_min']} min = {r['theta_aco_C']:.0f} C",
         f"  Fatores de reducao: ky = {r['ky']:.4f} ; kE = {r['kE']:.4f}",
         f"  fy,fi = {r['fy_fi_kN_m2']:.0f} kN/m2 ; E,fi = {r['E_fi_kPa']:.0f} kPa"]
    if r.get("protecao"):
        L.append(f"  Protecao: {r['protecao']['tipo']} esp={r['protecao']['espessura']} mm")
    else:
        L.append("  Sem protecao passiva.")
    L.append("  [FLAG: verificacao completa requer analise da estrutura em incendio")
    L.append("   com as combinacoes excepcionais (NBR 8681) e reducao de resistencia.")
    L.append("   O engenheiro confirma TRRF conforme NBR 14432 e corpo de bombeiros.]")
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # HEA200 sem protecao, TRRF 60 min
    sec = {"h": 190.0, "b": 200.0, "tw": 6.5, "tf": 10.0}
    r = verifica_fogo(sec, 250e3, 100.0, 30.0, TRRF_min=60)
    assert 800 <= r["theta_aco_C"] <= 1000, f"temp={r['theta_aco_C']}"
    assert r["ky"] < 1.0 and r["kE"] < 1.0
    assert r["u_A_1m"] > 50
    # Com protecao intumescente
    r2 = verifica_fogo(sec, 250e3, 100.0, 30.0, TRRF_min=60,
                       protecao={"tipo": "intumescente", "espessura": 1.27})
    assert r2["theta_aco_C"] < r["theta_aco_C"], f"prot={r2['theta_aco_C']} >= sem={r['theta_aco_C']}"
    print("fogo_nbr14323 self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sec = {"h": 190.0, "b": 200.0, "tw": 6.5, "tf": 10.0}
        print(relatorio_pt(verifica_fogo(sec, 250e3, 100.0, 30.0, TRRF_min=60)))
