# ============================================================================
# alma_variavel.py - PERFIL I DE ALMA VARIAVEL (tapered)
# Premissa: secao I duplamente SIMETRICA (mesas superior e inferior iguais).
# Gera secoes ao longo do comprimento (ALTURA VARIANDO LINEARMENTE).
# Para usar com frame2d: dividir em NSEG segmentos (recomendado >= 8),
# cada um com sua propria secao (A, Av, I) correspondente ao ponto medio.
# ============================================================================
"""Perfil I alma variavel (duplamente simetrico). Unidades: m, kN."""

from __future__ import annotations
import math


def props_I(h, bf, tw, tf):
    """Propriedades COMPLETAS de um perfil I duplamente simetrico de altura h (m).
    Retorna dict no formato consumido por check_nbr8800 (verifica/momento_resistente/
    cortante/compressao): A, Ix, Iy, Wx, Zx, Wy, Zy, rx, ry, d, bf, tf, tw, Av.
    Eixo forte = x (flexao no plano da alma)."""
    if h <= 2.0 * tf:
        raise ValueError(f"Altura {h}m menor que 2*tf={2*tf}m (inconsistente)")
    hw = h - 2.0 * tf                                  # altura livre da alma
    A = 2.0 * bf * tf + hw * tw
    Ix = (bf * h ** 3 - (bf - tw) * hw ** 3) / 12.0
    Iy = (2.0 * tf * bf ** 3) / 12.0 + (hw * tw ** 3) / 12.0
    Wx = 2.0 * Ix / h
    Zx = bf * tf * (h - tf) + tw * hw ** 2 / 4.0       # modulo plastico eixo forte
    Wy = 2.0 * Iy / bf
    Zy = tf * bf ** 2 / 2.0 + hw * tw ** 2 / 4.0       # modulo plastico eixo fraco
    return {"A": A, "Ix": Ix, "Iy": Iy, "Wx": Wx, "Zx": Zx, "Wy": Wy, "Zy": Zy,
            "rx": math.sqrt(Ix / A), "ry": math.sqrt(Iy / A), "d": h,
            "bf": bf, "tf": tf, "tw": tw, "Av": hw * tw}


def secao_tapered(h1, h2, bf, tw, tf, nseg=8):
    """Gera nseg secoes ao longo de uma viga de alma variavel.
    h1 = altura na extremidade 1 (m), h2 = altura na extremidade 2 (m).
    bf = largura da mesa (m), tw = espessura da alma (m),
    tf = espessura da mesa (m).
    Retorna lista de dicts com h, A, Av, I, Wx + as props COMPLETAS (props_I) de
    cada segmento (ponto medio). Premissa: I duplamente simetrico (2 mesas iguais)."""
    for h_ in (h1, h2):
        if h_ <= 2.0 * tf:
            raise ValueError(f"Altura {h_}m menor que 2*tf={2*tf}m (inconsistente)")
    secoes = []
    for i in range(nseg):
        t = (i + 0.5) / nseg
        h = h1 + (h2 - h1) * t
        p = props_I(h, bf, tw, tf)
        secoes.append({"h_m": round(h, 4), "A_m2": round(p["A"], 6),
                       "Av_m2": round(p["Av"], 6), "I_m4": round(p["Ix"], 8),
                       "Wx_m3": round(p["Wx"], 6), "segmento": i, "props": p})
    return secoes


def peso_tapered(h1, h2, bf, tw, tf, L, rho=77.0):
    """Peso linear medio de uma viga de alma variavel (kN/m)."""
    h_med = (h1 + h2) / 2.0
    A_med = 2.0 * bf * tf + (h_med - 2.0 * tf) * tw
    return A_med * rho


def _selftest():
    sec = secao_tapered(0.60, 0.30, 0.20, 0.008, 0.0125, nseg=8)
    assert len(sec) == 8
    assert sec[0]["h_m"] > sec[-1]["h_m"]
    assert sec[0]["I_m4"] > sec[-1]["I_m4"]
    assert sec[0]["Av_m2"] > 0                         # area de cisalhamento
    assert abs(secao_tapered(0.50, 0.50, 0.20, 0.008, 0.0125, 1)[0]["h_m"] - 0.50) < 0.001
    print("alma_variavel self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sec = secao_tapered(0.60, 0.30, 0.20, 0.008, 0.0125)
        for s in sec:
            print(f"  seg{s['segmento']}: h={s['h_m']*1000:.0f}mm A={s['A_m2']*1e4:.1f}cm2 I={s['I_m4']*1e8:.0f}cm4")
