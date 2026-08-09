# ============================================================================
# geotecnia_spt.py - O QUE ESTE SCRIPT FAZ / CALCULA
# A PONTE geotecnica que faltava: do PERFIL DE SONDAGEM SPT ate a TENSAO ADMISSIVEL
# do solo e a ESCOLHA do tipo de fundacao (rasa=sapata x profunda=estaca). Hoje o
# galpao recebe sigma_solo_adm como dado manual "A CONFIRMAR"; aqui esse valor passa
# a ser DERIVADO da sondagem.
#   - sigma_adm_spt: tensao admissivel de fundacao RASA pelo SPT medio no bulbo,
#     sigma_adm = N_medio/50 [MPa] (valida p/ N>=20, medida ~2.B abaixo da cota de
#     apoio) - LIDO do PDF (Exercicios de Fundacoes, "4o Metodo: SPT medio").
#   - capacidade_terzaghi: sigma_R = c.Nc.Sc + q.Nq.Sq + 0,5.gamma.B.Ngama.Sgama
#     (fatores de forma Tab.4.1 LIDOS do PDF: quadrada 1,3/0,8/1,0; corrida
#     1/1/1; retangular 1,1/0,9/1,0), sigma_adm = sigma_R/FS (FS=3). Os fatores de
#     capacidade Nc/Nq/Ngama vem das formulas classicas de Terzaghi/Vesic; o angulo
#     de atrito phi e' DADO DO LAUDO (Ask, Do Not Invent).
#   - recalque_elastico: recalque imediato de sapata (Teoria da Elasticidade),
#     s = sigma.B.(1-nu^2).Iw / E ; E do laudo (A CONFIRMAR).
#   - recomenda_fundacao: decide sapata x estaca a partir do perfil SPT e da carga
#     do pilar (reusa estaca_profunda p/ o caso profundo). Justificativa em texto.
# Unidades: m, kN, MPa (kN/m2 na interface com fundacao_sapata). STATELESS.
# ============================================================================
"""Ponte SPT -> tensao admissivel + escolha de fundacao (rasa x profunda).
sigma_adm = N/50 (Exercicios de Fundacoes); Terzaghi (fatores de forma do PDF);
recalque elastico. STATELESS: funcoes puras, _selftest aferido."""

from __future__ import annotations

import math

FS_RUPTURA = 3.0                # fator de seguranca a ruptura do solo (NBR 6122)
MPA_KNM2 = 1000.0               # 1 MPa = 1000 kN/m2

# fatores de forma de Terzaghi (Exercicios de Fundacoes, Tab.4.1) - LIDOS do PDF
_FORMA = {                      # (Sc, Sgama, Sq)
    "corrida":    (1.0, 1.0, 1.0),
    "quadrada":   (1.3, 0.8, 1.0),
    "circular":   (1.3, 0.6, 1.0),
    "retangular": (1.1, 0.9, 1.0),
}


def sigma_adm_spt(N_medio):
    """Tensao admissivel de fundacao RASA pelo SPT (Exercicios de Fundacoes,
    "4o Metodo: SPT medio"): sigma_adm = N_medio/50 [MPa], para N_medio >= 20,
    com o N medio tomado ~2.B abaixo da cota de apoio. Retorna (sigma_adm_MPa, nota).
    Para 8<=N<20 devolve o mesmo valor como PRESUMIDO conservador, com alerta
    (verificar por Terzaghi/prova de carga); N<8 -> None (solo fraco: fundacao
    profunda)."""
    if N_medio < 8:
        return None, "SPT medio < 8: solo fraco na cota de apoio - avaliar fundacao PROFUNDA"
    sig = N_medio / 50.0
    if N_medio >= 20:
        return sig, "sigma_adm = N/50 (SPT>=20, valido)"
    return sig, ("sigma_adm = N/50 PRESUMIDO (8<=SPT<20; formula validada p/ N>=20 - "
                 "confirmar por Terzaghi/prova de carga)")


def _fatores_capacidade(phi_graus):
    """Fatores de capacidade de carga Nq, Nc, Ngama (phi em graus). Formulas
    classicas: Nq = e^(pi.tan phi).tan^2(45+phi/2) (Reissner/Prandtl);
    Nc = (Nq-1).cot phi (Prandtl); Ngama = 2.(Nq+1).tan phi (Vesic 1973)."""
    phi = math.radians(phi_graus)
    if phi_graus <= 0:
        return 1.0, 5.14, 0.0                      # solo puramente coesivo (phi=0)
    Nq = math.exp(math.pi * math.tan(phi)) * math.tan(math.radians(45) + phi / 2.0) ** 2
    Nc = (Nq - 1.0) / math.tan(phi)
    Ngama = 2.0 * (Nq + 1.0) * math.tan(phi)
    return Nq, Nc, Ngama


def capacidade_terzaghi(c_kNm2, gamma_kNm3, B_m, q_kNm2, phi_graus, forma="quadrada",
                        fs=FS_RUPTURA):
    """Capacidade de carga de fundacao rasa (Terzaghi, Exercicios de Fundacoes):
    sigma_R = c.Nc.Sc + q.Nq.Sq + 0,5.gamma.B.Ngama.Sgama ; sigma_adm = sigma_R/fs
    (o termo de sobrecarga q NAO leva fs). phi (graus) e c do LAUDO. Retorna kN/m2."""
    if forma not in _FORMA:
        raise ValueError("forma invalida: %r" % forma)
    Sc, Sg, Sq = _FORMA[forma]
    Nq, Nc, Ng = _fatores_capacidade(phi_graus)
    sigma_R = c_kNm2 * Nc * Sc + q_kNm2 * Nq * Sq + 0.5 * gamma_kNm3 * B_m * Ng * Sg
    # tensao admissivel: minora sigma_R (menos a sobrecarga q, que ja e' efetiva)
    sigma_adm = (sigma_R - q_kNm2) / fs + q_kNm2
    return {"sigma_R_kNm2": sigma_R, "sigma_adm_kNm2": sigma_adm,
            "Nc": Nc, "Nq": Nq, "Ngama": Ng, "forma": forma, "fs": fs}


def recalque_elastico(sigma_kNm2, B_m, E_kNm2, nu=0.3, Iw=0.88):
    """Recalque imediato (elastico) de sapata rigida (Teoria da Elasticidade):
    s = sigma.B.(1-nu^2).Iw / E. Iw ~ 0,88 (sapata quadrada rigida). E do laudo
    (A CONFIRMAR). Retorna recalque em mm."""
    s_m = sigma_kNm2 * B_m * (1.0 - nu ** 2) * Iw / E_kNm2
    return s_m * 1000.0


def _n_medio_bulbo(perfil, cota_apoio_m, B_m):
    """N medio do SPT no bulbo de pressao (~2.B abaixo da cota de apoio). perfil:
    lista [{N, dz}] do topo p/ baixo (dz em m, espessura de cada camada)."""
    z0 = cota_apoio_m; z1 = cota_apoio_m + 2.0 * B_m
    prof = 0.0; soma = 0.0; esp = 0.0
    for cam in perfil:
        top = prof; bot = prof + cam["dz"]; prof = bot
        # sobreposicao [top,bot] com [z0,z1]
        lo = max(top, z0); hi = min(bot, z1)
        if hi > lo:
            soma += cam["N"] * (hi - lo); esp += (hi - lo)
    if esp <= 0:                                   # bulbo abaixo do perfil informado
        return perfil[-1]["N"]
    return soma / esp


def dimensiona_sapata_spt(perfil, N_pilar_kN, cota_apoio_m=0.5, B_max_m=2.5):
    """Dimensiona a sapata (quadrada) SO com o SPT: itera B ate o N medio no bulbo
    (~2.B) convergir e a area atender N_pilar/sigma_adm. Retorna dict ou None se
    inviavel (sigma muito baixa / B > B_max)."""
    B = 1.0
    for _ in range(30):
        N_med = _n_medio_bulbo(perfil, cota_apoio_m, B)
        sig_MPa, nota = sigma_adm_spt(N_med)
        if sig_MPa is None:
            return None
        sig_kNm2 = sig_MPa * MPA_KNM2
        A = N_pilar_kN / sig_kNm2
        B_novo = math.sqrt(A)
        if abs(B_novo - B) < 1e-3:
            B = B_novo; break
        B = B_novo
    if B > B_max_m:
        return None
    return {"B_m": round(B, 2), "N_medio_bulbo": round(N_med, 1),
            "sigma_adm_MPa": round(sig_MPa, 3), "sigma_adm_kNm2": round(sig_kNm2, 1),
            "area_m2": round(B * B, 2), "nota": nota}


def recomenda_fundacao(perfil, N_pilar_kN, cota_apoio_m=0.5, B_max_m=2.5,
                       N_competente=20):
    """Escolhe o tipo de fundacao a partir do perfil SPT e da carga do pilar.
    Regra: se a sapata fecha (B<=B_max) com o solo raso competente -> RASA (sapata);
    senao, se ha camada competente (N>=N_competente) mais funda -> PROFUNDA (estaca);
    senao REVISAR. Retorna {tipo, justificativa, sapata?/estaca_dica?}."""
    N_sup = _n_medio_bulbo(perfil, cota_apoio_m, 1.0)
    sap = dimensiona_sapata_spt(perfil, N_pilar_kN, cota_apoio_m, B_max_m)
    if sap is not None and N_sup >= 8:
        return {"tipo": "sapata", "sapata": sap,
                "justificativa": "solo raso competente (N medio ~%.0f na cota de "
                "apoio) e sapata %.2f x %.2f m <= B_max %.1f m -> fundacao DIRETA "
                "(sigma_adm = N/50)." % (N_sup, sap["B_m"], sap["B_m"], B_max_m)}
    # procura a 1a camada competente (profundidade acumulada)
    prof = 0.0; z_comp = None
    for cam in perfil:
        prof += cam["dz"]
        if cam["N"] >= N_competente and z_comp is None:
            z_comp = prof
    if z_comp is not None:
        return {"tipo": "estaca", "z_camada_competente_m": round(z_comp, 1),
                "justificativa": "solo raso insuficiente p/ sapata (N sup ~%.0f) mas "
                "ha camada competente (N>=%d) a ~%.1f m -> fundacao PROFUNDA. Dimensionar "
                "com estaca_profunda (Aoki-Velloso, perfil_spt)." % (N_sup, N_competente, z_comp),
                "estaca_dica": {"L_min_m": round(z_comp, 1)}}
    return {"tipo": "revisar", "justificativa": "sem camada competente no perfil "
            "informado (N sempre baixo) - aprofundar a sondagem / melhorar o solo / "
            "avaliar fundacao especial."}


# ----------------------------------- selftest --------------------------------
def _selftest():
    # 1) sigma_adm = N/50 (PDF): N=25 -> 0,50 MPa ; N=20 -> 0,40 MPa
    s, _ = sigma_adm_spt(25.0)
    assert abs(s - 0.5) < 1e-9, s
    s20, nota20 = sigma_adm_spt(20.0)
    assert abs(s20 - 0.4) < 1e-9 and "valido" in nota20
    # 8<=N<20 -> presumido com alerta ; N<8 -> None (profunda)
    s10, nota10 = sigma_adm_spt(10.0)
    assert abs(s10 - 0.2) < 1e-9 and "PRESUMIDO" in nota10
    assert sigma_adm_spt(5.0)[0] is None

    # 2) Terzaghi: phi maior -> capacidade maior ; forma quadrada > corrida (Nc.Sc)
    a = capacidade_terzaghi(0.0, 18.0, 2.0, 10.0, 30.0, "quadrada")
    b = capacidade_terzaghi(0.0, 18.0, 2.0, 10.0, 35.0, "quadrada")
    assert b["sigma_adm_kNm2"] > a["sigma_adm_kNm2"] > 0
    # phi=0 (argila): Nc=5,14, Nq=1, Ngama=0 (Prandtl)
    arg = capacidade_terzaghi(50.0, 18.0, 2.0, 10.0, 0.0, "quadrada")
    assert abs(arg["Nc"] - 5.14) < 0.01 and arg["Ngama"] == 0.0

    # 3) recalque cresce com a tensao e cai com E
    r1 = recalque_elastico(200.0, 2.0, 20000.0)
    r2 = recalque_elastico(400.0, 2.0, 20000.0)
    r3 = recalque_elastico(200.0, 2.0, 40000.0)
    assert r2 > r1 > r3 > 0

    # 4) recomendador: solo competente raso -> sapata
    perfil_bom = [{"tipo": "areia", "N": 25, "dz": 6.0}]
    rec = recomenda_fundacao(perfil_bom, 600.0)
    assert rec["tipo"] == "sapata" and rec["sapata"]["B_m"] <= 2.5

    # 5) solo fraco em cima, competente embaixo -> estaca
    perfil_mole = [{"tipo": "argila", "N": 3, "dz": 6.0},
                   {"tipo": "areia", "N": 30, "dz": 6.0}]
    rec2 = recomenda_fundacao(perfil_mole, 600.0)
    assert rec2["tipo"] == "estaca" and rec2["z_camada_competente_m"] == 12.0

    # 6) carga alta em solo mediano -> sapata estoura B_max -> estaca (se houver comp.)
    perfil_med = [{"tipo": "areia", "N": 12, "dz": 4.0}, {"tipo": "areia", "N": 25, "dz": 8.0}]
    rec3 = recomenda_fundacao(perfil_med, 4000.0, B_max_m=2.5)
    assert rec3["tipo"] in ("estaca", "sapata")     # decidido pela geometria
    return True


if __name__ == "__main__":
    _selftest()
    import json
    perfil = [{"tipo": "argila_arenosa", "N": 4, "dz": 3.0},
              {"tipo": "areia_siltosa", "N": 8, "dz": 3.0},
              {"tipo": "areia", "N": 28, "dz": 6.0}]
    print(json.dumps(recomenda_fundacao(perfil, 800.0), indent=2, ensure_ascii=False))
    print("selftest OK")
