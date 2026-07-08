# ============================================================================
# calhas.py - DIMENSIONAMENTO DE CALHAS E CONDUTORES (Bellei §2.4 / NBR 10844)
# Calcula area de contribuicao, vazao, secao da calha (Manning-Strickler),
# diametro dos condutores e carga de agua. Inclui borda livre (75%) e regra
# pratica de Bellei (1 cm2 de secao / m2 de telhado).
# ============================================================================
"""Dimensionamento de calhas e condutores. Saidas PT. Unidades: m, L/min."""

from __future__ import annotations
import math


def area_contribuicao(comp_telhado, larg_agua, h_elevacao=0.0):
    return comp_telhado * (larg_agua + h_elevacao / 2.0)


def vazao_projeto(A_contrib, I_mm_h=150.0):
    return I_mm_h * A_contrib / 60.0


def secao_calha(Q_req, B_base=0.10, i=0.005, n=0.011, H_max=0.08):
    """Retorna a altura d'agua necessaria, com borda livre de 25%.
    H_max = altura total da calha (m). A lamina d'agua maxima e 0.75*H_max.
    Se não couber com borda livre, retorna ok=False."""
    h_limite = 0.75 * H_max
    for h_agua in [a / 1000.0 for a in range(5, int(h_limite * 1000) + 1)]:
        As = B_base * h_agua
        Pm = B_base + 2.0 * h_agua
        Rh = As / Pm if Pm > 0 else 0.0
        Q_calc = 60000.0 * As * (Rh ** (2.0 / 3.0)) * (i ** 0.5) / n
        if Q_calc >= Q_req:
            return {"h_agua_m": round(h_agua, 3), "As_cm2": round(As * 10000, 1),
                    "Q_calc_Lmin": round(Q_calc, 1), "Q_req_Lmin": round(Q_req, 1),
                    "B_base_m": B_base, "H_max_m": H_max, "i": i,
                    "borda_livre_pct": round(100 * (1 - h_agua / H_max), 0),
                    "ok": True, "ok_borda_livre": h_agua <= h_limite}
    return {"ok": False, "Q_req_Lmin": round(Q_req, 1), "h_max_m": H_max}


def diametro_condutor(Q_Lmin, n_condutores=1):
    Q_por = Q_Lmin / max(n_condutores, 1)
    if Q_por <= 90:   return 75
    elif Q_por <= 180: return 100
    elif Q_por <= 320: return 125
    elif Q_por <= 500: return 150
    else:              return 200


def dimensiona(comp_telhado, larg_agua, h_elevacao=0.0, I_mm_h=150.0,
               inclinacao=0.005, n_condutores=2, B_base=0.10, H_calha=0.08):
    A = area_contribuicao(comp_telhado, larg_agua, h_elevacao)
    Q = vazao_projeto(A, I_mm_h)
    secao = secao_calha(Q, B_base, inclinacao, H_max=H_calha)
    if not secao.get("ok"):
        return {"area_contrib_m2": round(A, 1), "vazao_Lmin": round(Q, 1),
                "secao": secao, "ok": False}
    d_cond = diametro_condutor(Q, n_condutores)
    ok_bellei = (secao["B_base_m"] * secao["H_max_m"]) * 10000 >= A  # 1 cm2/m2 (Bellei, secao total)
    Vol = (secao["As_cm2"] / 10000) * comp_telhado
    peso_agua = Vol * 10.0
    return {
        "area_contrib_m2": round(A, 1), "vazao_Lmin": round(Q, 1),
        "secao": {**secao, "ok_bellei": ok_bellei,
                  "ok": secao["ok"] and ok_bellei and secao.get("ok_borda_livre", True)},
        "condutor_diam_mm": d_cond, "n_condutores": n_condutores,
        "peso_agua_kN": round(peso_agua, 2), "inclinacao": inclinacao,
        "ok": secao["ok"] and ok_bellei and secao.get("ok_borda_livre", True)}


def relatorio_pt(r):
    s = r.get("secao", {})
    L = ["CALHAS E CONDUTORES (Bellei §2.4 / NBR 10844)",
         f"  Area de contribuicao = {r['area_contrib_m2']:.1f} m2",
         f"  Vazao de projeto Q = {r['vazao_Lmin']:.0f} L/min"]
    if s.get("ok"):
        L += [f"  CALHA: B={s['B_base_m']*1000:.0f} mm ; H={s['H_max_m']*1000:.0f} mm",
              f"    Lamina d'agua req = {s['h_agua_m']*1000:.0f} mm ; As={s['As_cm2']:.1f} cm2",
              f"    Q calc = {s['Q_calc_Lmin']:.0f} >= {s['Q_req_Lmin']:.0f} L/min",
              f"    Borda livre = {s.get('borda_livre_pct',0):.0f}% (>= 25% OK)",
              f"    Bellei As>=A_contrib: {s['As_cm2']:.0f} >= {r['area_contrib_m2']:.0f} cm2"
              + (" OK" if s.get('ok_bellei') else " NAO (usar H maior)")]
        L.append(f"  Condutores: {r['n_condutores']} x d{r['condutor_diam_mm']} mm")
        L.append(f"  Peso da agua = {r['peso_agua_kN']:.1f} kN")
    else:
        L.append(f"  Nao foi possivel dimensionar com H_max={s.get('h_max_m',0.08)*1000:.0f} mm")
    L += ["  [A CONFIRMAR: I pluviometrica local; geometria; condutores]"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    r = dimensiona(10.0, 5.0, 0.5, B_base=0.20, H_calha=0.08)
    assert r.get("ok"), f"calha reprovada: {r.get('secao',{})}"
    print(f"calhas self-test PASSED: {r['secao']['As_cm2']:.0f} cm2, "
          f"h={r['secao']['h_agua_m']*1000:.0f}mm, "
          f"borda={r['secao'].get('borda_livre_pct',0):.0f}%")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(dimensiona(10.0, 5.0, 0.5, B_base=0.15, H_calha=0.08)))
