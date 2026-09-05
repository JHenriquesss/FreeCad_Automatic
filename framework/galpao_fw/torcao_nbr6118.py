# ============================================================================
# torcao_nbr6118.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Torcao de vigas de concreto pela ANALOGIA DA TRELICA ESPACIAL GENERALIZADA
# (NBR 6118:2014, item 17.5), secao retangular cheia -> secao vazada equivalente:
#   - geometria (17.5.1.4.1): espessura de parede he = A/u (>= 2 c1); Ae = area
#     dentro da linha media da parede; ue = perimetro de Ae;
#   - biela comprimida (17.5.1.5): TRd2 = 0,50 alpha_v2 fcd Ae he sen(2 theta);
#   - estribos (17.5.1.6a): A90/s = Tsd/(fywd 2 Ae cotg theta);
#   - armadura longitudinal (17.5.1.6b): Asl = Tsd ue tg(theta)/(fywd 2 Ae);
#   - torcao + cortante concomitantes (17.7.2.2): Vsd/VRd2 + Tsd/TRd2 <= 1.
# theta arbitrado em 30..45 graus; fywd <= 435 MPa. Valores lidos do PDF NBR 6118
# (NotebookLM), nao de memoria. Unidades: m, kN (fck/fywk em kN/m2 ; T em kN.m).
# ============================================================================
"""Torcao de vigas retangulares (NBR 6118 17.5): trelica espacial, biela TRd2,
armaduras transversal/longitudinal e interacao com o cortante (17.7.2.2)."""

from __future__ import annotations

import math

GAMMA_C = 1.4
GAMMA_S = 1.15
FYWD_MAX = 435e3               # limite do aco transversal (kN/m2)
THETA_MIN = 30.0               # 17.5: theta da trelica em 30..45 graus (G51)
THETA_MAX = 45.0


def secao_vazada_equivalente(b, h, c1):
    """Geometria da secao vazada equivalente (17.5.1.4.1). b,h,c1 em m.
    he = A/u (>= 2 c1, <= bw-2 c1) ; Ae = (b-he)(h-he) ; ue = 2((b-he)+(h-he))."""
    A = b * h
    u = 2.0 * (b + h)
    he = A / u
    he = max(he, 2.0 * c1)                       # nao menor que 2 c1
    he = min(he, b - 2.0 * c1, h - 2.0 * c1)     # cabe na secao
    Ae = (b - he) * (h - he)
    ue = 2.0 * ((b - he) + (h - he))
    return {"A": A, "u": u, "he": he, "Ae": Ae, "ue": ue}


def verifica_torcao(Td, b, h, c1, fck, fywk=500e3, theta_deg=45.0):
    """Verifica torcao pura (17.5). Td = momento de torcao de calculo (kN.m).
    theta_deg em 30..45 graus (17.5, G51): fora da faixa, RECUSA fail-closed
    (OK=False, motivo nomeado) em vez de devolver numero que parece bom.
    Retorna TRd2 (biela), armaduras A90/s (estribo) e Asl (longitudinal), e OK."""
    g = secao_vazada_equivalente(b, h, c1)
    he, Ae, ue = g["he"], g["Ae"], g["ue"]
    fcd = fck / GAMMA_C
    av2 = 1.0 - (fck / 1000.0) / 250.0
    theta_valido = (THETA_MIN <= theta_deg <= THETA_MAX)
    th = math.radians(theta_deg)
    TRd2 = 0.50 * av2 * fcd * Ae * he * math.sin(2.0 * th)
    fywd = min(fywk / GAMMA_S, FYWD_MAX)
    # theta=0 (fora da faixa) zera tan(): sem esta guarda a RECUSA fail-closed
    # morria em ZeroDivisionError antes de recusar (achado no sweep do G51).
    _tan = math.tan(th) if abs(math.tan(th)) > 1e-12 else None
    # estribos (17.5.1.6a): A90/s = Td/(fywd 2 Ae cotg theta)
    A90_s = (Td / (fywd * 2.0 * Ae / _tan) if (Ae > 0 and _tan is not None)
             else float("inf"))
    # longitudinal (17.5.1.6b): Asl = Td ue tg(theta)/(fywd 2 Ae)
    Asl = (Td * ue * _tan / (fywd * 2.0 * Ae) if (Ae > 0 and _tan is not None)
           else float("inf"))
    # G51-rev: biela_ok volta a significar A BIELA (Td<=TRd2) e nada mais.
    # Antes, o theta recusado sujava esta chave para que a recusa chegasse ao
    # chamador; funcionava, mas o relatorio passava a imprimir a desigualdade
    # que VALE e concluir "REPROVA (aumentar secao)" com o remedio errado - a
    # secao esta sobrando, o errado e' o theta. Quem decide agora e' OK, que
    # compoe as duas condicoes; viga_concreto le OK (nao biela_ok).
    biela_ok = bool(Td <= TRd2 + 1e-6)
    motivo = ("" if theta_valido else
              "theta_deg=%.1f fora da faixa 30..45 da 17.5 (G51)" % theta_deg)
    return {"he": round(he, 4), "Ae": round(Ae, 4), "ue": round(ue, 4),
            "TRd2": TRd2, "Td": Td, "theta_deg": theta_deg,
            "theta_valido": bool(theta_valido), "motivo": motivo,
            "A90_s_cm2_m": round(A90_s * 1e4, 2), "Asl_cm2": round(Asl * 1e4, 2),
            "biela_ok": biela_ok, "OK": bool(biela_ok and theta_valido)}


def interacao_torcao_cortante(Vsd, VRd2, Td, TRd2):
    """Esmagamento das bielas sob cortante + torcao concomitantes (17.7.2.2):
    Vsd/VRd2 + Td/TRd2 <= 1. Retorna a razao e OK."""
    razao = Vsd / VRd2 + Td / TRd2
    return {"razao": round(razao, 3), "OK": razao <= 1.0 + 1e-6}


def relatorio_pt(r, inter=None):
    L = ["TORCAO (NBR 6118 17.5, trelica espacial generalizada)",
         f"  Secao vazada equiv.: he={r['he']*100:.1f} cm ; Ae={r['Ae']*1e4:.0f} cm2 ; "
         f"ue={r['ue']*100:.0f} cm ; theta={r['theta_deg']:.0f} graus",
         f"  Biela: Td={r['Td']:.1f} <= TRd2={r['TRd2']:.1f} kN.m "
         f"-> {'OK' if r['biela_ok'] else 'REPROVA (aumentar secao)'}",
         f"  Armaduras: estribo A90/s={r['A90_s_cm2_m']:.2f} cm2/m ; "
         f"longitudinal Asl={r['Asl_cm2']:.2f} cm2"]
    if not r.get("theta_valido", True):
        # G51-rev: as armaduras acima foram calculadas COM o theta recusado
        # (fora de 30..45 elas sub-dimensionam: theta=20 da 63% do estribo de
        # 30). O dicionario segue devolvendo os numeros - quem os le tem OK
        # False -, mas o relatorio, que e' feito para ser lido, os marca.
        L.append("  ^ armaduras calculadas com o theta RECUSADO: nao usar")
        L.append(f"  THETA RECUSADO (17.5, G51): {r.get('motivo', '')}")
        L.append("  RESULTADO: REPROVA por theta (a biela nao e' o problema)")
    if inter:
        L.append(f"  Torcao+Cortante (17.7.2.2): Vsd/VRd2+Td/TRd2 = {inter['razao']:.2f} "
                 f"<= 1 -> {'OK' if inter['OK'] else 'REPROVA'}")
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # viga 20x50, C30, c1=4 cm, Td=20 kN.m
    r = verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3)
    assert r["he"] > 0 and r["Ae"] > 0
    # he = A/u = 0,1/1,4 = 0,0714 m (> 2 c1 = 0,08? nao -> he=0,08)
    g = secao_vazada_equivalente(0.20, 0.50, 0.04)
    assert abs(g["he"] - max(0.10 / 1.4, 0.08)) < 1e-9
    assert r["TRd2"] > 0 and r["A90_s_cm2_m"] > 0 and r["Asl_cm2"] > 0
    assert r["biela_ok"]
    # torcao alta esmaga a biela
    r_alto = verifica_torcao(300.0, 0.20, 0.50, 0.04, 30e3)
    assert not r_alto["biela_ok"]
    # theta menor (30) da TRd2 menor que theta 45 (sen2theta menor)
    r30 = verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=30.0)
    r45 = verifica_torcao(20.0, 0.20, 0.50, 0.04, 30e3, theta_deg=45.0)
    assert r45["TRd2"] > r30["TRd2"]
    # interacao V+T
    it = interacao_torcao_cortante(100.0, 400.0, 15.0, 60.0)   # 0,25+0,25=0,5
    assert abs(it["razao"] - 0.5) < 1e-9 and it["OK"]
    assert not interacao_torcao_cortante(400.0, 400.0, 60.0, 60.0)["OK"]
    print("torcao_nbr6118 self-test PASSED")
    print(relatorio_pt(r, interacao_torcao_cortante(100.0, 400.0, r["Td"], r["TRd2"])))


if __name__ == "__main__":
    _selftest()
