# Ponte rolante + viga de rolamento - ponte_rolante.py

Arquivo: `projects/galpao/calc/ponte_rolante.py`
Gerado: 2026-07-05
Base: NBR 8800:2008 (acao de ponte, ELS, fadiga Anexo K) + NBR 8400 (classes).
Metodo do livro "Dimensionamento de elementos estruturais de aco e mistos"
(cap. 4, pesquisa/aco).
Status: **APROVADO E HOMOLOGADO** pelo eng. senior (2026-07-05) apos 2 correcoes
criticas. Diretrizes do senior para a integracao no portico (pendente):
1. Aplicar M_excentrico (39,9 kN.m) como momento concentrado no NO DO CONSOLE
   (ou barra rigida do console) - gera momento grande no pilar inferior, que
   costuma GOVERNAR o dimensionamento da coluna.
2. Ponte = acao variavel autonoma. Alem do psi0=0,7 quando o vento e principal,
   rodar uma combinacao com a PONTE como acao principal:
   G + 1,5*Ponte + 1,4*0,6*Vento (governa a flambagem dos pilares da via).

Correcoes aplicadas nesta versao:
- FLECHA VERTICAL com 2 rodas (era 1 roda no meio -> subestimava ~13%):
  `delta = Pk*(L-d)/(48EI)*(2L^2+2Ld-d^2)`.
- Mrd,y (surto lateral) SO da MESA SUPERIOR (o surto age no topo do trilho;
  NBR 8800 / Fakury 4.4.2): props ~metade do perfil. Antes superestimava ~100%.
- Nota 3.2 registrada: frenagem age nas rodas motoras (frac_long ajustavel).

## Problema que resolve
Lacuna detectada no ensaio (Gate 0, ponte pesada): o toolkit descrevia a
geometria da ponte mas NAO calculava os esforcos. Este modulo fecha: cargas nas
tres direcoes, viga de rolamento e a reacao empacotada para o portico.

## Metodo (fundamentado, nao de memoria)
Tres direcoes de forca (livro cap. 4 / NBR 8800):
- **Vertical**: (ponte + trole + carga icada) MAJORADO pelo coef. de impacto phi.
- **Transversal (surto)**: percentual de (icada + trole), dividido nas rodas;
  resistido SO pela mesa superior da viga de rolamento.
- **Longitudinal (frenagem)**: percentual das cargas de roda (rodas motoras).

phi, frac_lateral e frac_long sao **dado do fabricante ou NBR 8400** (o proprio
livro diz que "sao muitas vezes fornecidas pelos fabricantes") -> FLAGADOS
"A CONFIRMAR". O METODO (combinacao, momento por carga movel, ELS, fadiga) e norma.

- **Cargas de roda**: ponte encostada, trole na aproximacao minima -> Rmax/Rmin.
- **Viga de rolamento**: momento maximo ABSOLUTO de 2 rodas (mecanica exata:
  `Mmax=(2P/L)*(L/2-d/4)^2`), flexao lateral do surto (SO mesa superior),
  verificacao NBR 8800 (Anexo G + biaxial), flecha (2 rodas, sem impacto) e FADIGA.
- **ELS (NBR 8800, do livro)**: flecha vertical L/600 (<200 kN) / L/800 (>=200) /
  L/1000 (siderurgica); horizontal L/400 (L/600 sider.); coluna <= Hvr/400.
- **Reacao no portico**: R_vertical + M_excentrico + H_transversal + H_longitudinal.

## Pendente (integracao)
A reacao empacotada AINDA precisa ser injetada no galpao_portico como caso de
carga da ponte (+ combinacao psi0=0,7). Passo separado (mexe no portico aprovado).
A referencia 20x10 e SEM ponte -> este modulo roda sob cfg proprio.

## Codigo completo

```python
# ============================================================================
# ponte_rolante.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Acao de PONTE ROLANTE em galpao industrial pela ABNT NBR 8800:2008 (+ NBR 8400
# para as classes). Fornece as cargas e verifica a VIGA DE ROLAMENTO, e empacota
# a reacao para o PORTICO (console/pilar). Referencia do metodo: livro
# "Dimensionamento de elementos estruturais de aco e mistos" (cap. 4) + NBR 8800.
#
# Tres direcoes de forca (item 4 do livro / NBR 8800):
#   VERTICAL: peso da ponte + trole + carga icada, MAJORADO pelo coef. de impacto
#     phi (do fabricante ou NBR 8400 - parametro A CONFIRMAR; 1,10 leve .. 1,25
#     pesada/siderurgica).
#   TRANSVERSAL (surto): percentual de (carga icada + trole), acel./desalinhamento
#     do trole; dividido entre as rodas. frac_lateral A CONFIRMAR (~0,10).
#   LONGITUDINAL (frenagem): percentual das cargas de roda no trilho; frenagem da
#     ponte. frac_long A CONFIRMAR (~0,10).
#
# Cargas de roda (Rmax/Rmin): ponte encostada, trole na aproximacao minima 'a' de
# um trilho -> reacao maxima naquele trilho; por roda = R_trilho / n_rodas.
#
# Viga de rolamento (vao = distancia entre porticos): momento por CARGA MOVEL (2
# rodas, formula do momento maximo absoluto - mecanica exata), flexao lateral do
# surto (eixo fraco), verificacao NBR 8800 (Anexo G + biaxial), flecha e FADIGA.
# ELS (NBR 8800): flecha vertical L/600 (<200 kN) / L/800 (>=200) / L/1000
# (siderurgica); horizontal L/400 (L/600 siderurgica); NAO majorar por impacto.
# Coluna: deslocamento no nivel da viga de rolamento <= Hvr/400.
# FADIGA: pontes pesadas exigem verificacao (NBR 8800 Anexo K) - SINALIZA, nao
# fabrica categoria de detalhe sem dado.
#
# Generico e parametrico (dados da ponte = gate/fabricante). NAO inventa
# coeficientes normativos: phi, frac_lateral, frac_long entram flagados. Calcula
# apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Acao de ponte rolante + viga de rolamento - ABNT NBR 8800:2008 / NBR 8400."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck

GA1 = ck.GA1


def cargas_de_roda(Q, peso_ponte, peso_trole, vao_ponte, aprox_min, n_rodas_lado):
    """Reacao maxima/minima por roda (kN), ponte com trole na aproximacao minima.

    Q = capacidade icada ; pesos em kN ; vao_ponte = distancia entre trilhos (m) ;
    aprox_min = distancia minima do gancho ao trilho (m). O peso da ponte divide-se
    igualmente nos dois trilhos; a carga movel (Q+trole) vai por braco de alavanca.
    """
    S = vao_ponte
    movel = Q + peso_trole
    R_trilho_max = peso_ponte / 2.0 + movel * (S - aprox_min) / S
    R_trilho_min = peso_ponte / 2.0 + movel * aprox_min / S
    return (R_trilho_max / n_rodas_lado, R_trilho_min / n_rodas_lado,
            R_trilho_max, R_trilho_min)


def forcas_horizontais(Q, peso_trole, R_roda_max, n_rodas_lado, frac_lateral,
                       frac_long):
    """Forca transversal por roda (surto) e longitudinal por trilho (frenagem).
    NOTA (parecer 3.2): a frenagem age nas RODAS MOTORAS. Aqui frac_long incide
    sobre as cargas de roda do trilho; se so parte das rodas for motorizada, o
    eng. reduz frac_long por (n_motoras/n_rodas) na entrada (A CONFIRMAR)."""
    n_total = 2 * n_rodas_lado
    H_transv_roda = frac_lateral * (Q + peso_trole) / n_total
    H_long_trilho = frac_long * R_roda_max * n_rodas_lado
    return H_transv_roda, H_long_trilho


def _m_max_movel(P, d, L):
    """Momento maximo absoluto de 2 cargas iguais P espacadas d, vao L (biapoiada).
    Formula da mecanica (momento maximo absoluto): Mmax = (2P/L)*(L/2 - d/4)^2.
    Compara com uma roda so no meio (P*L/4) caso d seja grande."""
    if d < L:
        m2 = (2.0 * P / L) * (L / 2.0 - d / 4.0) ** 2
    else:
        m2 = 0.0
    return max(m2, P * L / 4.0)


def limite_flecha_vertical(cap_kN, siderurgica):
    """NBR 8800: L/600 (<200 kN) ; L/800 (>=200) ; L/1000 (siderurgica >=200)."""
    if siderurgica and cap_kN >= 200.0:
        return 1000.0
    if cap_kN >= 200.0:
        return 800.0
    return 600.0


def verifica_viga_rolamento(sec, fy, cfg):
    """Viga de rolamento (perfil I) sob carga movel + surto lateral - NBR 8800.

    cfg: vao (m, entre porticos), P_vertical (kN, carga de roda majorada por
    impacto), H_transv (kN, surto por roda), d_rodas (m, base entre rodas),
    E_Ix (opcional, para flecha), cap_kN, siderurgica, phi (impacto).
    """
    L = cfg["vao"]
    P = cfg["P_vertical"]; Ht = cfg["H_transv"]; d = cfg.get("d_rodas", 0.0)
    Msdx = _m_max_movel(P, d, L)                    # flexao vertical (movel)
    Msdy = _m_max_movel(Ht, d, L)                   # flexao lateral (surto)
    # resistencias (Anexo G eixo forte ; eixo fraco plastico)
    Mnx, gov, det = ck.momento_resistente(sec, fy, cfg.get("Lb", L), cfg.get("Cb", 1.0))
    Mrdx = Mnx / GA1
    # Flexao lateral do surto atua no TOPO DO TRILHO -> so a MESA SUPERIOR resiste
    # (NBR 8800 / Fakury 4.4.2), ~metade das props do perfil inteiro.
    Wy = sec.get("Wy", sec["Iy"] / (sec["bf"] / 2.0))
    Zy = sec.get("Zy", 1.5 * Wy)
    Wy_top, Zy_top = Wy / 2.0, Zy / 2.0
    Mrdy = min(Zy_top, 1.5 * Wy_top) * fy / GA1
    inter = Msdx / Mrdx + Msdy / Mrdy
    # flecha (carga movel SEM impacto, combinacao rara): P_carac = P/phi
    lim = limite_flecha_vertical(cfg["cap_kN"], cfg.get("siderurgica", False))
    flecha = None; flecha_ok = None
    if "E_Ix" in cfg and cfg["E_Ix"]:
        Pk = P / cfg.get("phi", 1.10)
        if 0.0 < d < L:                               # 2 rodas simetricas no vao
            flecha = Pk * (L - d) / (48.0 * cfg["E_Ix"]) * (2 * L ** 2 + 2 * L * d - d ** 2)
        else:                                         # 1 roda no meio
            flecha = Pk * L ** 3 / (48.0 * cfg["E_Ix"])
        flecha_ok = flecha <= L / lim
    return {"tipo": "viga_rolamento", "nome": cfg.get("nome", "Viga de rolamento"),
            "L": L, "Msdx": Msdx, "Msdy": Msdy, "Mrdx": Mrdx, "Mrdy": Mrdy,
            "M_gov": gov, "inter": inter, "u_x": Msdx / Mrdx, "u_y": Msdy / Mrdy,
            "flecha_mm": None if flecha is None else flecha * 1000.0,
            "flecha_lim": lim, "flecha_ok": flecha_ok,
            "OK": inter <= 1.0 and (flecha_ok in (None, True)),
            "fadiga_flag": "FADIGA (NBR 8800 Anexo K) a verificar para ciclos "
                           "elevados (ponte pesada/siderurgica) - dado do regime."}


def reacao_no_portico(R_roda_max, n_rodas_lado, H_transv_roda, H_long_trilho,
                      excentricidade):
    """Empacota a reacao da viga de rolamento para o PORTICO (console/pilar).
    R_vert = soma das rodas no trilho ; M_exc = R_vert * excentricidade (trilho
    fora do eixo do pilar) ; H_transv e H_long entram na analise/contraventamento."""
    R_vert = R_roda_max * n_rodas_lado
    return {"R_vertical_kN": R_vert, "M_excentrico_kNm": R_vert * excentricidade,
            "H_transversal_kN": H_transv_roda * n_rodas_lado,
            "H_longitudinal_kN": H_long_trilho}


def relatorio_pt(esf, viga, reac):
    L = ["=" * 70, "PONTE ROLANTE (ABNT NBR 8800:2008 / NBR 8400)", "=" * 70,
         "  CARGAS DE RODA (ponte encostada, trole na aproximacao minima):",
         f"    R_roda_max = {esf['R_roda_max']:.1f} kN ; R_roda_min = {esf['R_roda_min']:.1f} kN",
         f"    Coef. de impacto phi = {esf['phi']:.2f} (A CONFIRMAR: fabricante/NBR 8400)",
         f"    P_vertical (com impacto) = {esf['P_vertical']:.1f} kN/roda",
         f"    Surto transversal = {esf['H_transv']:.1f} kN/roda "
         f"(frac {esf['frac_lateral']:.2f} A CONFIRMAR)",
         f"    Frenagem longitudinal = {esf['H_long']:.1f} kN/trilho "
         f"(frac {esf['frac_long']:.2f} A CONFIRMAR)",
         "-" * 70, "  VIGA DE ROLAMENTO (carga movel + surto lateral):",
         f"    Vao = {viga['L']:.2f} m ; Msd,x = {viga['Msdx']:.1f} kN.m ; "
         f"Msd,y = {viga['Msdy']:.1f} kN.m",
         f"    Mrd,x ({viga['M_gov']}) = {viga['Mrdx']:.1f} ; Mrd,y = {viga['Mrdy']:.1f} kN.m",
         f"    Interacao Mx/Mrdx+My/Mrdy = {viga['u_x']:.2f}+{viga['u_y']:.2f}="
         f"{viga['inter']:.2f} -> {'OK' if viga['inter'] <= 1 else 'NAO PASSA'}"]
    if viga["flecha_mm"] is not None:
        L.append(f"    Flecha vertical (sem impacto) = {viga['flecha_mm']:.1f} mm "
                 f"(limite L/{viga['flecha_lim']:.0f}) -> "
                 f"{'OK' if viga['flecha_ok'] else 'NAO'}")
    L += [f"    >> {viga['fadiga_flag']}",
          "-" * 70, "  REACAO NO PORTICO (console/pilar):",
          f"    R_vertical = {reac['R_vertical_kN']:.1f} kN ; M_excentrico = "
          f"{reac['M_excentrico_kNm']:.1f} kN.m",
          f"    H_transversal = {reac['H_transversal_kN']:.1f} kN ; H_longitudinal = "
          f"{reac['H_longitudinal_kN']:.1f} kN",
          "    (entram na analise do portico e no contraventamento longitudinal)",
          "  ELS: deslocamento no nivel da viga de rolamento <= Hvr/400 "
          "(50 mm siderurgica); diferencial entre pilares <= 15 mm.", "=" * 70]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def analisa(cfg):
    """Roda a cadeia da ponte a partir de um cfg (dados do fabricante/gate)."""
    Rmx, Rmn, Rtmx, Rtmn = cargas_de_roda(
        cfg["Q"], cfg["peso_ponte"], cfg["peso_trole"], cfg["vao_ponte"],
        cfg["aprox_min"], cfg["n_rodas_lado"])
    phi = cfg["phi"]
    Ht, Hl = forcas_horizontais(cfg["Q"], cfg["peso_trole"], Rmx,
                                cfg["n_rodas_lado"], cfg["frac_lateral"],
                                cfg["frac_long"])
    P = phi * Rmx
    esf = {"R_roda_max": Rmx, "R_roda_min": Rmn, "phi": phi, "P_vertical": P,
           "H_transv": Ht, "H_long": Hl, "frac_lateral": cfg["frac_lateral"],
           "frac_long": cfg["frac_long"]}
    vcfg = {"vao": cfg["vao_viga"], "P_vertical": P, "H_transv": Ht,
            "d_rodas": cfg.get("d_rodas", 0.0), "cap_kN": cfg["Q"],
            "siderurgica": cfg.get("siderurgica", False), "phi": phi,
            "Lb": cfg.get("Lb", cfg["vao_viga"]), "E_Ix": cfg.get("E_Ix"),
            "nome": "Viga de rolamento"}
    viga = verifica_viga_rolamento(cfg["perfil_viga"], cfg["fy"], vcfg)
    reac = reacao_no_portico(Rmx, cfg["n_rodas_lado"], Ht, Hl,
                             cfg.get("excentricidade", 0.30))
    return esf, viga, reac


# --- perfil de viga de rolamento (exemplo; A CONFIRMAR no catalogo) ----------
VS500 = {"A": 98.0e-4, "Ix": 40000e-8, "Iy": 2000e-8, "ry": 0.045,
         "Zx": 1800e-6, "Wx": 1600e-6, "Zy": 300e-6, "Wy": 200e-6,
         "d": 0.500, "bf": 0.250, "tf": 0.016, "tw": 0.008,
         "_fonte": "A CONFIRMAR (perfil soldado VS ; props do catalogo)"}


def _selftest():
    # Ponte de 100 kN (10 tf), vao 10 m (entre trilhos ~ vao do galpao), viga de
    # rolamento no BAY de 5 m. Coeficientes tipicos (A CONFIRMAR fabricante/8400).
    cfg = {"Q": 100.0, "peso_ponte": 60.0, "peso_trole": 15.0, "vao_ponte": 9.5,
           "aprox_min": 1.0, "n_rodas_lado": 2, "phi": 1.10, "frac_lateral": 0.10,
           "frac_long": 0.10, "vao_viga": 5.0, "d_rodas": 3.0, "fy": 250e3,
           "perfil_viga": VS500, "siderurgica": False, "excentricidade": 0.30,
           "E_Ix": ck.E * VS500["Ix"]}
    esf, viga, reac = analisa(cfg)
    print(relatorio_pt(esf, viga, reac))
    assert esf["R_roda_max"] > esf["R_roda_min"]
    assert viga["Msdx"] > 0 and viga["inter"] > 0
    assert reac["R_vertical_kN"] > 0 and reac["M_excentrico_kNm"] > 0
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
```

## Resultado da execucao (`python ponte_rolante.py`, ponte 100 kN, corrigido)

```
======================================================================
PONTE ROLANTE (ABNT NBR 8800:2008 / NBR 8400)
======================================================================
  CARGAS DE RODA (ponte encostada, trole na aproximacao minima):
    R_roda_max = 66,4 kN ; R_roda_min = 21,1 kN
    Coef. de impacto phi = 1,10 (A CONFIRMAR: fabricante/NBR 8400)
    P_vertical (com impacto) = 73,1 kN/roda
    Surto transversal = 2,9 kN/roda (frac 0,10 A CONFIRMAR)
    Frenagem longitudinal = 13,3 kN/trilho (frac 0,10 A CONFIRMAR)
----------------------------------------------------------------------
  VIGA DE ROLAMENTO (carga movel + surto lateral):
    Vao = 5,00 m ; Msd,x = 91,4 kN.m ; Msd,y = 3,6 kN.m
    Mrd,x (FLT) = 323,4 ; Mrd,y = 34,1 kN.m
    Interacao Mx/Mrdx+My/Mrdy = 0,28+0,11=0,39 -> OK
    Flecha vertical (sem impacto) = 2,5 mm (limite L/600) -> OK
    >> FADIGA (NBR 8800 Anexo K) a verificar para ciclos elevados (ponte pesada/siderurgica) - dado do regime.
----------------------------------------------------------------------
  REACAO NO PORTICO (console/pilar):
    R_vertical = 132,9 kN ; M_excentrico = 39,9 kN.m
    H_transversal = 5,8 kN ; H_longitudinal = 13,3 kN
    (entram na analise do portico e no contraventamento longitudinal)
  ELS: deslocamento no nivel da viga de rolamento <= Hvr/400 (50 mm siderurgica); diferencial entre pilares <= 15 mm.
======================================================================

[selftest] OK
```
