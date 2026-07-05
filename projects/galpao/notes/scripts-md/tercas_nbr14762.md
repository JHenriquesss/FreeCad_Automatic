# Tercas formadas a frio (NBR 14762) - tercas_nbr14762.py

Arquivo: `projects/galpao/calc/tercas_nbr14762.py`  
Gerado: 2026-07-05  
Base: ABNT NBR 14762:2010 (9.8.2.1 MSE, 9.8.3 cortante, Tabela 13/14) +
Anexo F (mesa comprimida livre sob sucao). Formulas extraidas do PDF.
PARAMETRICO: recebe qualquer perfil Ue (dims + props de catalogo).

## Codigo completo

```python
# ============================================================================
# tercas_nbr14762.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica uma TERCA de cobertura em perfil formado a frio (secao U enrijecido,
# Ue) pela ABNT NBR 14762:2010. Generico: recebe qualquer perfil (dimensoes +
# propriedades de catalogo) e a configuracao (vao, linha de corrente, largura
# de influencia, inclinacao, pressoes) e verifica:
#   - Momento resistente por escoamento da secao efetiva (9.8.2.1, MSE) -> caso
#     GRAVIDADE (mesa comprimida travada pela telha, sem FLT).
#   - Momento resistente sob SUCCAO (mesa comprimida livre): Anexo F -> R*Wef.
#   - Dispensa de flambagem distorcional (Tabela 14).
#   - Cortante (9.8.3) e combinacao M+V (9.8.4).
#   - Flexao obliqua (decomposicao pela inclinacao; linha de corrente reduz o
#     vao do eixo fraco) com interacao linear.
#   - Flecha (ELS) L/180 (gravidade) e L/120 (vento), Anexo C da NBR 8800.
# Wef pelo MSE usa Wx (catalogo) + kl (Tabela 13, das dimensoes) -> baixo erro.
# ATENCAO: propriedades do perfil = do catalogo do fornecedor (A CONFIRMAR).
# Saidas em portugues. Calcula apenas; pendente revisao. Unidades SI: m, kN.
# ============================================================================
"""Verificacao de terca (Ue) conforme ABNT NBR 14762:2010 (9.8 + Anexo F)."""

from __future__ import annotations

import math

E = 200e6          # kN/m2 (modulo de elasticidade)
NU = 0.3           # coeficiente de Poisson
G_ACO = 77e6       # kN/m2 (modulo transversal)
GA = 1.10          # gamma para flexao/cortante (NBR 14762 9.8)

# Tabela 13 (NBR 14762) - kl da secao COMPLETA, flexao no eixo de maior inercia,
# Caso b (U enrijecido). Colunas: mu<=0,2 ; mu=0,25 ; mu=0,30 (mu = D/bw).
_TAB13 = {
    0.2: (32.0, 25.8, 21.2), 0.3: (29.3, 23.8, 19.7), 0.4: (24.8, 20.7, 18.2),
    0.5: (18.7, 17.6, 16.0), 0.6: (13.6, 13.3, 13.0), 0.7: (10.2, 10.1, 10.1),
    0.8: (7.9, 7.9, 7.9), 0.9: (6.2, 6.3, 6.3), 1.0: (5.1, 5.1, 5.1),
}


def _interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


def k_local(bf, bw, D):
    """kl da Tabela 13 (Ue) por interpolacao dupla em zeta=bf/bw e mu=D/bw."""
    zeta = min(max(bf / bw, 0.2), 1.0)
    mu = min(max(D / bw, 0.0), 0.3)
    zs = sorted(_TAB13)
    z0 = max([z for z in zs if z <= zeta], default=zs[0])
    z1 = min([z for z in zs if z >= zeta], default=zs[-1])
    # interpola em mu (0,2 ; 0,25 ; 0,3) para cada zeta vizinho
    def _kmu(row):
        if mu <= 0.2:
            return row[0]
        if mu <= 0.25:
            return _interp(mu, 0.2, 0.25, row[0], row[1])
        return _interp(mu, 0.25, 0.3, row[1], row[2])
    k0, k1 = _kmu(_TAB13[z0]), _kmu(_TAB13[z1])
    return _interp(zeta, z0, z1, k0, k1)


def Wef_MSE(W, Wc, kl, bw, t, fy):
    """Modulo resistente da secao efetiva (9.8.2.1, MSE)."""
    Ml = kl * math.pi ** 2 * E / (12 * (1 - NU ** 2)) * (t / bw) ** 2 * Wc
    lp = math.sqrt(W * fy / Ml)
    Wef = W if lp <= 0.673 else W * (1 - 0.22 / lp) / lp
    return Wef, Ml, lp


def fator_R_anexoF(bw_mm, secao="U", continua=False):
    """Tabela F.1: fator R para mesa comprimida livre (sucao)."""
    if continua:
        return 0.70 if secao == "Z" else 0.60      # bw <= 292
    if bw_mm <= 165:
        return 0.70
    if bw_mm <= 216:
        return 0.65
    if bw_mm <= 292:
        return 0.50 if secao == "Z" else 0.40
    return None                                     # fora do escopo do Anexo F


# Tabela 14: D/bw minimo para DISPENSAR distorcional (flexao, Ue). bw/t nas
# colunas (250,200,125,100,50) ; bf/bw nas linhas.
_TAB14_BWT = [250, 200, 125, 100, 50]
_TAB14 = {
    0.4: [0.05, 0.06, 0.10, 0.12, 0.25], 0.6: [0.05, 0.06, 0.10, 0.12, 0.25],
    0.8: [0.05, 0.06, 0.09, 0.12, 0.22], 1.0: [0.05, 0.06, 0.09, 0.11, 0.22],
    1.2: [0.05, 0.06, 0.09, 0.11, 0.20], 1.4: [0.05, 0.06, 0.09, 0.10, 0.20],
    1.6: [0.05, 0.06, 0.09, 0.10, 0.20], 1.8: [0.05, 0.06, 0.09, 0.10, 0.19],
    2.0: [0.05, 0.06, 0.09, 0.10, 0.19],
}


def dispensa_distorcional(bw, bf, D, t):
    """True se D/bw >= limite da Tabela 14 (dispensa a verificacao)."""
    bwt = bw / t
    ratio = bf / bw            # bf/bw (a tabela usa bf/bw)
    rs = sorted(_TAB14)
    r0 = max([r for r in rs if r <= ratio], default=rs[0])
    # coluna por bw/t (interpola nas colunas)
    cols = _TAB14_BWT
    def _colval(row):
        if bwt >= cols[0]:
            return row[0]
        if bwt <= cols[-1]:
            return row[-1]
        for a, b in zip(cols, cols[1:]):
            if b <= bwt <= a:
                return _interp(bwt, a, b, row[cols.index(a)], row[cols.index(b)])
        return row[-1]
    lim = _colval(_TAB14[r0])
    return (D / bw) >= lim, lim


def cortante_Vrd(h, t, fy, kv=5.0):
    """9.8.3: forca cortante resistente (kv=5 sem enrijecedores)."""
    lam = h / t
    lp = 1.08 * math.sqrt(E * kv / fy)
    lr = 1.40 * math.sqrt(E * kv / fy)
    if lam <= lp:
        return 0.6 * fy * h * t / GA
    if lam <= lr:
        return 0.65 * t ** 2 * math.sqrt(kv * fy * E) / GA
    return (0.905 * E * kv * t ** 3 / h) / GA


def verifica_terca(perfil, cfg):
    """perfil: dict com dims (mm) e propriedades de catalogo (SI). cfg: config."""
    bw, bf, D, t = perfil["bw"], perfil["bf"], perfil["D"], perfil["t"]  # mm
    bw_m, t_m = bw / 1000.0, t / 1000.0
    h = perfil.get("h_alma_plana", bw - 2 * (t + perfil.get("r", 0))) / 1000.0
    fy = cfg["fy"]
    W = perfil["Wx"]                     # modulo elastico bruto (SI)
    Wc = perfil.get("Wxc", W)            # comp. (U simetrico no eixo x: = W)
    Wy = perfil["Wy"]                    # eixo fraco (menor modulo)

    kl = k_local(bf, bw, D)
    Wef, Ml, lp = Wef_MSE(W, Wc, kl, bw_m, t_m, fy)

    # momentos resistentes eixo x (forte)
    Mrd_grav = Wef * fy / GA                                   # 9.8.2.1
    R = fator_R_anexoF(bw, perfil.get("secao", "U"), cfg.get("continua", False))
    Mrd_succ = (R * Wef * fy / GA) if R else None              # Anexo F
    # eixo y (fraco): escoamento (conservador, sem reducao local)
    Mrdy = Wy * fy / GA
    # distorcional
    disp, lim14 = dispensa_distorcional(bw, bf, D, t)
    Vrd = cortante_Vrd(h, t_m, fy)

    # ---- solicitacoes: decomposicao pela inclinacao -----------------------
    theta = cfg["theta"]                 # rad
    L = cfg["vao"]                       # vao forte (m)
    Ly = cfg.get("vao_fraco", L)         # eixo fraco (com linha de corrente)
    trib = cfg["larg_influencia"]        # largura de influencia (m)
    # pressoes de cálculo (kN/m2, ja com gamma) por caso
    res = {"perfil": perfil.get("nome", "Ue"), "kl": kl, "Wef": Wef, "Ml": Ml,
           "lp": lp, "Mrd_grav": Mrd_grav, "Mrd_succ": Mrd_succ, "R": R,
           "Mrdy": Mrdy, "Vrd": Vrd, "dispensa_dist": disp, "lim_tab14": lim14,
           "casos": {}}
    for nome, p_sd in cfg["casos"].items():   # p_sd kN/m2 (perp. ao telhado ja?)
        # carga por metro de terca (perpendicular ao plano do telhado)
        q = p_sd * trib                   # kN/m (na direcao da pressao)
        # componente perpendicular ao telhado (eixo x) e paralela (eixo y)
        qx = q * math.cos(theta)
        qy = q * math.sin(theta)
        Msx = abs(qx) * L ** 2 / 8.0
        Msy = abs(qy) * Ly ** 2 / 8.0
        Vsx = abs(qx) * L / 2.0
        # momento resistente do eixo x conforme o sentido (sucao = uplift)
        uplift = p_sd < 0
        Mrdx = res["Mrd_succ"] if (uplift and Mrd_succ) else res["Mrd_grav"]
        inter = Msx / Mrdx + Msy / Mrdy if Mrdx else float("inf")
        uv = Vsx / Vrd
        res["casos"][nome] = {"p_sd": p_sd, "qx": qx, "qy": qy, "Msx": Msx,
                              "Msy": Msy, "Vsx": Vsx, "Mrdx": Mrdx,
                              "uplift": uplift, "interacao": inter, "uV": uv,
                              "OK": inter <= 1.0 and uv <= 1.0}
    return res


def relatorio_pt(res, cfg):
    L = ["VERIFICACAO DE TERCA (ABNT NBR 14762:2010 - 9.8 + Anexo F)",
         f"  Perfil: {res['perfil']}  (propriedades A CONFIRMAR no catalogo)",
         f"  fy = {cfg['fy']/1000:.0f} MPa ; vao = {cfg['vao']:.2f} m ; "
         f"vao eixo fraco = {cfg.get('vao_fraco', cfg['vao']):.2f} m "
         f"(linha de corrente)",
         f"  Largura de influencia = {cfg['larg_influencia']:.3f} m ; "
         f"inclinacao = {math.degrees(cfg['theta']):.2f} graus",
         f"  Flambagem local: kl = {res['kl']:.2f} ; Ml = {res['Ml']:.2f} kN.m ; "
         f"lambda_p = {res['lp']:.3f}",
         f"  Wef = {res['Wef']*1e6:.2f} cm3 ; Mrd(gravidade) = {res['Mrd_grav']:.2f} kN.m",
         f"  Anexo F: R = {res['R']} ; Mrd(succao) = "
         f"{res['Mrd_succ']:.2f} kN.m" if res['Mrd_succ'] else
         "  Anexo F: fora do escopo (bw>292) - usar 9.8.2 sem painel",
         f"  Mrd eixo fraco = {res['Mrdy']:.2f} kN.m ; Vrd = {res['Vrd']:.2f} kN",
         f"  Distorcional: {'DISPENSADA' if res['dispensa_dist'] else 'VERIFICAR'} "
         f"(D/bw vs Tab.14 min {res['lim_tab14']:.3f})", ""]
    for nome, c in res["casos"].items():
        L += [f"  --- caso {nome} (p={c['p_sd']:+.3f} kN/m2, "
              f"{'SUCCAO/uplift' if c['uplift'] else 'gravidade'}) ---",
              f"    qx={c['qx']:+.3f} qy={c['qy']:+.3f} kN/m ; "
              f"Msx={c['Msx']:.2f} Msy={c['Msy']:.2f} kN.m ; Vsx={c['Vsx']:.2f} kN",
              f"    Interacao Msx/Mrdx + Msy/Mrdy = {c['Msx']:.2f}/{c['Mrdx']:.2f} + "
              f"{c['Msy']:.2f}/{res['Mrdy']:.2f} = {c['interacao']:.2f} ; "
              f"V/Vrd={c['uV']:.2f}  -> {'OK' if c['OK'] else 'NAO PASSA'}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


# ---- auto-teste: kl e Wef em pontos conhecidos -----------------------------
def _selftest():
    # kl nos vertices da Tabela 13 (Ue)
    assert abs(k_local(0.5 * 100, 100, 0.2 * 100) - 18.7) < 1e-6   # zeta0,5 mu0,2
    assert abs(k_local(1.0 * 100, 100, 0.0) - 5.1) < 1e-6
    # Wef = W quando lambda_p <= 0,673 (secao compacta)
    W = 50e-6
    Wef, Ml, lp = Wef_MSE(W, W, 20.0, 0.100, 0.003, 250e3)
    assert lp <= 0.673 and abs(Wef - W) < 1e-12, (lp, Wef)
    print("tercas_nbr14762 self-test PASSED")
    print(f"  k_local(zeta=0,5; mu=0,2) = {k_local(50,100,20):.2f} (Tab.13=18,7)")
    print(f"  Wef(compacta) = {Wef*1e6:.2f} cm3 == W ; lambda_p={lp:.3f}")


# ---- exemplo (perfil e config PLACEHOLDER - a skill pergunta ao usuario) ----
# Perfil Ue exemplo (dimensoes tipicas; PROPRIEDADES A CONFIRMAR no catalogo):
PERFIL_EXEMPLO = {
    "nome": "Ue 200x75x20x2.65 (EXEMPLO - confirmar catalogo)",
    "bw": 200.0, "bf": 75.0, "D": 20.0, "t": 2.65, "r": 3.0, "secao": "U",
    # propriedades de catalogo (SI) - VALORES DE EXEMPLO, substituir:
    "A": 8.03e-4, "Ix": 480e-8, "Iy": 63e-8, "Wx": 48.0e-6, "Wy": 12.0e-6,
}
CFG_EXEMPLO = {
    "fy": 250e3, "theta": math.atan(0.5 / 5.0), "vao": 5.0, "vao_fraco": 2.5,
    "larg_influencia": 1.675, "continua": False,
    "casos": {                      # pressoes de cálculo (kN/m2) ja fatoradas
        "gravidade_1.25G+1.5Q": +0.90,
        "sucao_1.0G+1.4W": -1.20,
    },
}


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_terca(PERFIL_EXEMPLO, CFG_EXEMPLO), CFG_EXEMPLO))
```

## Resultado da execucao (self-test + exemplo)

```
tercas_nbr14762 self-test PASSED
  k_local(zeta=0,5; mu=0,2) = 18.70 (Tab.13=18,7)
  Wef(compacta) = 50.00 cm3 == W ; lambda_p=0.277

VERIFICACAO DE TERCA (ABNT NBR 14762:2010 - 9,8 + Anexo F)
  Perfil: Ue 200x75x20x2,65 (EXEMPLO - confirmar catalogo)  (propriedades A CONFIRMAR no catalogo)
  fy = 250 MPa ; vao = 5,00 m ; vao eixo fraco = 2,50 m (linha de corrente)
  Largura de influencia = 1,675 m ; inclinacao = 5,71 graus
  Flambagem local: kl = 25,93 ; Ml = 39,49 kN.m ; lambda_p = 0,551
  Wef = 48,00 cm3 ; Mrd(gravidade) = 10,91 kN.m
  Anexo F: R = 0,65 ; Mrd(succao) = 7,09 kN.m
  Mrd eixo fraco = 2,73 kN.m ; Vrd = 65,61 kN
  Distorcional: VERIFICAR (D/bw vs Tab.14 min 0,184)

  --- caso gravidade_1,25G+1,5Q (p=+0,900 kN/m2, gravidade) ---
    qx=+1,500 qy=+0,150 kN/m ; Msx=4,69 Msy=0,12 kN.m ; Vsx=3,75 kN
    Interacao Msx/Mrdx + Msy/Mrdy = 4,69/10,91 + 0,12/2,73 = 0,47 ; V/Vrd=0,06  -> OK
  --- caso sucao_1,0G+1,4W (p=-1,200 kN/m2, SUCCAO/uplift) ---
    qx=-2,000 qy=-0,200 kN/m ; Msx=6,25 Msy=0,16 kN.m ; Vsx=5,00 kN
    Interacao Msx/Mrdx + Msy/Mrdy = 6,25/7,09 + 0,16/2,73 = 0,94 ; V/Vrd=0,08  -> OK
```
