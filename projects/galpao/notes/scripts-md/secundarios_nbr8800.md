# Pecas secundarias (longarina U + escora I) - secundarios_nbr8800.py

Arquivo: `projects/galpao/calc/secundarios_nbr8800.py`
Gerado: 2026-07-05
Base: NBR 8800:2008 - Anexo G (flexao), 5.4.2 (eixo fraco), 5.5.1 (interacao
biaxial), 5.5.1.2 (flexo-compressao). Pendente revisao do eng. senior.

## Problema que resolve

O toolkit dimensionava portico, terca de cobertura, base e ligacao - mas as
pecas SECUNDARIAS ficavam como placeholder, sem verificacao:
- **Longarina de parede (girt, UPE100)** - flexao biaxial.
- **Escora de beiral / cumeeira (HEA160)** - flexo-compressao.

Este modulo fecha essa lacuna. Generico e parametrico: todas as cargas/geometrias
sao `cfg` que a skill pergunta ao usuario no gate (ver [[toolkit-inputs-are-gate-questions]]).

## Metodo

### Longarina (perfil U) - flexao biaxial
- **Eixo forte (x):** vento normal a parede (pressao/succao), vao = distancia
  entre porticos. Sob SUCCAO a mesa interna (livre) e comprimida -> travada por
  linha(s) de tirante de parede: `Lb = vao/(n_tirantes+1)`.
- **Eixo fraco (y):** peso do tapamento + peso proprio; vao reduzido pelos tirantes.
- **Mrd,x:** Anexo G completo (FLT+FLM+FLA). O FLT do U usa **J e Cw do CATALOGO**
  (nao formula de perfil I) - dado marcado "A CONFIRMAR"; o METODO (G.2) e o mesmo
  do check do portico. Sem J/Cw -> INCONCLUSIVO (nao inventa).
- **Mrd,y:** `min(Zy ; 1,5*Wy)*fy / ga1` (5.4.2, sem FLT no eixo fraco).
- **Interacao biaxial (5.5.1, N=0):** `Mx/Mrdx + My/Mrdy <= 1`.

### Escora / cumeeira (perfil I) - flexo-compressao
- Axial do contraventamento longitudinal (vento no oitao, **A CONFIRMAR** - o
  modulo `vento` ainda so faz o vento transversal) + flexao do peso proprio no vao.
- Reusa `check_nbr8800.verifica` (mesma verificacao do portico, perfil I).

## Integracao (rodar_galpao, Gate 7)
- Puxa a pior pressao liquida de parede do `vento` (|net| maximo * q).
- Roda as duas verificacoes, salva `gate7-secundarios.txt`, entra no consolidado.
- Params em `PARAMS_REF["secundarios"]` (perfis, trib, tapamento, n_tirantes, Nsd).

## Achados (referencia 20x10, BAY 5 m)
- **Longarina UPE100 NAO passa com 1 tirante (1,13)**; passa com **2 tirantes
  (0,99)**. -> O modelo (`build_galpao`) hoje tem **0 tirante de parede**: precisa
  adicionar 2 linhas, ou perfil maior. **Sinalizado para o modelo e para o eng.**
- **Escora HEA160: 0,11 OK** com Nsd=60 kN (axial longitudinal **A CONFIRMAR**);
  governada por esbeltez (chi=0,43 em Lb=5 m), nao pelo esforco.

## Pontos "A CONFIRMAR" (nao esconder)
- Props do UPE100 e do HEA160, e em especial **J e Cw do U** (catalogo).
- **Axial da escora**: exige o vento LONGITUDINAL (NBR 6123, alpha=0) - ainda nao
  no modulo `vento`. Por ora Nsd e um parametro estimado. Proximo passo do toolkit.

## Codigo completo

```python
# ============================================================================
# secundarios_nbr8800.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica as PECAS SECUNDARIAS de perfil laminado pela ABNT NBR 8800:2008 que
# o resto do toolkit ainda nao cobria:
#   (1) LONGARINA DE PAREDE (girt, perfil U laminado) - flexao BIAXIAL:
#       - eixo forte (x): vento normal a parede (pressao/succao), vao = distancia
#         entre porticos; mesa comprimida sob SUCCAO travada por linha(s) de
#         tirante de parede -> Lb = vao/(n_tirantes+1).
#       - eixo fraco (y): peso do tapamento + peso proprio; vao = idem eixo forte
#         reduzido pelos tirantes.
#       - interacao de flexao biaxial (5.5.1, N=0): Mx/Mrdx + My/Mrdy <= 1.
#       - Mrdx: Anexo G completo (FLT+FLM+FLA). O FLT do U usa J e Cw do U vindos
#         do CATALOGO (nao de formula de I) - dado marcado "A CONFIRMAR"; o METODO
#         (G.2) e o mesmo do check. Sem J/Cw no dict -> INCONCLUSIVO (nao inventa).
#       - Mrdy = min(Zy, 1,5*Wy)*fy / ga1 (5.4.2, sem FLT no eixo fraco).
#   (2) ESCORA DE BEIRAL / CUMEEIRA (perfil I laminado) - FLEXO-COMPRESSAO:
#       axial do contraventamento longitudinal (vento no oitao) + flexao do peso
#       proprio no vao entre porticos. Reusa check_nbr8800.verifica (perfil I).
#
# Generico e parametrico: TODAS as cargas/geometrias sao parametros (cfg) que a
# skill pergunta ao usuario no gate (peso do tapamento, n de tirantes, pressao de
# vento, axial da escora, etc.). Defaults = galpao 20x10 de referencia, cada um
# marcado "A CONFIRMAR". NAO calcula esforcos globais nem inventa dados de
# catalogo. Calcula apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Verificacao de pecas secundarias (longarina U, escora I) - NBR 8800:2008."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck

E = ck.E          # 200e6 kN/m2
GA1 = ck.GA1      # 1,10

# --- Propriedades de catalogo (SI). A CONFIRMAR no catalogo do fornecedor -----
# Perfil U laminado (UPE, abas paralelas). Inclui eixo fraco (Iy, Wy, Zy) para a
# flexao biaxial. Valores nominais europeus - CONFERIR (Gerdau/ArcelorMittal).
UPE100 = {"nome": "UPE100", "A": 12.53e-4,
          "Ix": 207e-8, "Wx": 41.4e-6, "Zx": 48.8e-6, "rx": 0.0407,
          "Iy": 38.3e-8, "Wy": 12.9e-6, "Zy": 23.5e-6, "ry": 0.0175,
          "d": 0.100, "bf": 0.055, "tf": 0.0075, "tw": 0.0045,
          # Torcao/empenamento do U (para o FLT, Anexo G): CATALOGO, nao formula.
          "J": 2.01e-8, "Cw": 7.9e-10,
          "_fonte": "A CONFIRMAR no catalogo (props, J e Cw)"}

# Perfil I/H para escora/cumeeira (formato aceito por check_nbr8800.verifica).
HEA160 = {"A": 38.77e-4, "Ix": 1673e-8, "Iy": 615.6e-8, "ry": 0.0398,
          "Zx": 245.1e-6, "Wx": 220.1e-6, "d": 0.152, "bf": 0.160,
          "tf": 0.009, "tw": 0.006, "_fonte": "A CONFIRMAR no catalogo"}


def _mrd_eixo_forte_U(sec, fy, Lb, Cb=1.0):
    """Mrd,x do perfil U (kN.m) pelo Anexo G (FLT, FLM, FLA). Mesmas formulas de
    check_nbr8800.momento_resistente, mas J e Cw vem do CATALOGO do U (nao de
    formula de I). Se faltarem J/Cw no dict -> INCONCLUSIVO (nao inventa)."""
    if "Cw" not in sec or "J" not in sec:
        return None, "INCONCLUSIVO: faltam J/Cw do U (catalogo) para o FLT.", {
            "Lp": None, "compacto": None}
    Zx, Wx, Iy = sec["Zx"], sec["Wx"], sec["Iy"]
    bf, tf, d, tw, ry = sec["bf"], sec["tf"], sec["d"], sec["tw"], sec["ry"]
    Cw, J = sec["Cw"], sec["J"]
    rE = math.sqrt(E / fy)
    h = d - 2 * tf
    Mpl = Zx * fy
    sr = 0.3 * fy
    # FLM (mesa, elemento AL): b/t da aba do U
    lam_m = bf / tf; lamp_m = 0.38 * rE; lamr_m = 0.83 * math.sqrt(E / (fy - sr))
    Mcr_m = 0.69 * E * Wx / lam_m ** 2
    Mn_flm = ck._interp_M(lam_m, lamp_m, lamr_m, Mpl, (fy - sr) * Wx, Mcr_m)
    # FLA (alma): h/tw
    lam_a = h / tw; lamp_a = 3.76 * rE; lamr_a = 5.70 * rE
    Mn_fla = ck._interp_M(lam_a, lamp_a, lamr_a, Mpl, fy * Wx, Mpl)
    # FLT (Anexo G, com J e Cw do catalogo)
    lam = Lb / ry; lamp = 1.76 * rE
    Mr = (fy - sr) * Wx
    b1 = Mr / (E * J)
    lamr = (1.38 * math.sqrt(Iy * J)) / (ry * J * b1) * \
        math.sqrt(1 + math.sqrt(1 + 27 * Cw * b1 ** 2 / Iy))
    Mcr = (Cb * math.pi ** 2 * E * Iy / Lb ** 2) * \
        math.sqrt(Cw / Iy + 0.039 * J * Lb ** 2 / Iy)
    Mn_flt = ck._interp_M(lam, lamp, lamr, Mpl, Mr, Mcr, Cb)
    Mn = min(Mn_flt, Mn_flm, Mn_fla)
    gov = ["FLT", "FLM", "FLA"][[Mn_flt, Mn_flm, Mn_fla].index(Mn)]
    return Mn / GA1, gov, {"Lp": lamp * ry, "Lr": lamr * ry,
                           "compacto": lam_m <= lamp_m and lam_a <= lamp_a,
                           "Mn_flt": Mn_flt, "Mn_flm": Mn_flm, "Mn_fla": Mn_fla}


def _mrd_eixo_fraco(sec, fy):
    """Mrd,y = min(Zy ; 1,5*Wy)*fy / ga1 (5.4.2, sem FLT no eixo fraco)."""
    return min(sec["Zy"], 1.5 * sec["Wy"]) * fy / GA1


def verifica_longarina(sec, fy, cfg):
    """Longarina de parede (girt, perfil U) - flexao biaxial NBR 8800.

    cfg (do gate): vao (m, = distancia entre porticos), q_vento (kN/m2, pressao
    liquida na parede, do modulo vento), trib (m, altura de influencia da
    longarina), g_tapamento (kN/m2, peso do fechamento), n_tirantes (linhas de
    tirante de parede), continua (bool), gamma (dict opcional).
    """
    vao = cfg["vao"]; g = cfg.get("gamma", {})
    gW = g.get("W", 1.40); gG = g.get("G", 1.25)   # ELU (Tabela 1)
    n_t = cfg.get("n_tirantes", 1)
    Lb = vao / (n_t + 1)                            # destravamento (eixo forte, succao)
    Ly = vao / (n_t + 1)                            # vao do eixo fraco (peso) c/ tirante
    # linhas de carga caracteristicas (kN/m)
    qx = cfg["q_vento"] * cfg["trib"]              # vento normal -> eixo forte
    qy = (cfg["g_tapamento"] + cfg.get("peso_proprio", 0.10)) * cfg["trib"]  # peso -> fraco
    # coeficientes estaticos (biapoiada ou continua)
    cM = 1.0 / 10.0 if cfg.get("continua") else 1.0 / 8.0
    # momentos solicitantes ELU
    Msdx = gW * qx * vao ** 2 * cM
    Msdy = gG * qy * Ly ** 2 * cM
    # resistencias
    Mrdx, modo_x, detx = _mrd_eixo_forte_U(sec, fy, Lb)
    Mrdy = _mrd_eixo_fraco(sec, fy)
    r = {"tipo": "longarina", "nome": sec.get("nome", "U"), "vao": vao, "Lb": Lb,
         "Ly": Ly, "qx": qx, "qy": qy, "Msdx": Msdx, "Msdy": Msdy,
         "Mrdx": Mrdx, "modo_x": modo_x, "Mrdy": Mrdy, "Lp": detx["Lp"],
         "compacto": detx["compacto"]}
    if Mrdx is None:
        r.update(inter=None, OK=False)
        return r
    inter = Msdx / Mrdx + Msdy / Mrdy               # 5.5.1 biaxial (N=0)
    r.update(inter=inter, u_x=Msdx / Mrdx, u_y=Msdy / Mrdy, OK=inter <= 1.0)
    return r


def verifica_escora(sec, fy, cfg):
    """Escora de beiral / cumeeira (perfil I) - flexo-compressao NBR 8800.

    cfg (do gate): vao (m), Nsd (kN, axial de compressao do contraventamento
    longitudinal), peso_proprio (kN/m), Lb (m, travamento lateral), Cb.
    Reusa check_nbr8800.verifica (mesma verificacao do portico).
    """
    vao = cfg["vao"]
    qz = cfg.get("peso_proprio", 0.31)             # kN/m (peso proprio HEA160 ~0,30)
    gG = cfg.get("gamma_G", 1.25)
    Msd = gG * qz * vao ** 2 / 8.0                  # flexao do peso proprio no vao
    Vsd = gG * qz * vao / 2.0
    Nsd = cfg["Nsd"]                               # axial (A CONFIRMAR: vento long.)
    Lb = cfg.get("Lb", vao)
    res = ck.verifica(sec, fy, L=vao, Nsd=Nsd, Msd=Msd, Vsd=Vsd,
                      Kx=1.0, Ky=1.0, Lb=Lb, Cb=cfg.get("Cb", 1.0),
                      nome=cfg.get("nome", "Escora/cumeeira (HEA160)"))
    res["tipo"] = "escora"
    return res
```
(As funcoes `relatorio_pt` e `_selftest` seguem no arquivo-fonte.)

## Resultado da execucao (`python secundarios_nbr8800.py`, caso que passa)

```
====================================================================
LONGARINA DE PAREDE (perfil U) - UPE100
NBR 8800 Anexo G + interacao biaxial (vento eixo forte, peso fraco)
====================================================================
  Vao (entre porticos) ........ 5,00 m
  Lb (mesa interna, succao) ... 1,67 m  (Lp=0,87 m ; compacto=True)
  qx (vento) .................. 2,204 kN/m -> Msdx=9,64 kN.m
  qy (peso) ................... 0,400 kN/m -> Msdy=0,17 kN.m
  Mrd,x (FLT) = 10,19 kN.m
  Mrd,y (min(Zy;1,5Wy)*fy) .... 4,40 kN.m
  Interacao Mx/Mrdx+My/Mrdy ... 0,95+0,04=0,99 -> OK
====================================================================

  --- Escora de beiral / cumeeira (HEA160) ---
  Compressao: Ne=486 kN ; lambda0=1,412 ; chi=0,434 ; Nc,Rd=382,4 kN
    Mn_FLT=49,8 ; ... governa FLT ; Mrd=45,3 kN.m
  Utilizacao: N/Nc=0,16 ; M/Mrd=0,03 ; V/Vrd=0,01
  Interacao (N/(2Nrd) + M/Mrd) = 0,11  -> OK

[selftest] OK
```
