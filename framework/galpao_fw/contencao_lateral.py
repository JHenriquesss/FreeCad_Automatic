# ============================================================================
# contencao_lateral.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a PECA da mao-francesa (contencao de translacao NODAL) pela ABNT
# NBR 8800:2008, item 4.11.3.4 - resistencia E rigidez - mais a esbeltez
# (5.3.4.1) e a compressao resistente (5.3.2).
#
# POR QUE EXISTE: `mao_francesa.py` calcula so o ESPACAMENTO (inverte a interacao
# flexo-compressao para achar Lb_max -> stride -> quantos bracos). Ele decide
# ONDE por o braco e nunca O QUE por: nao computa Fbr,Sd nem Sbr,Sd e nao
# verifica secao nenhuma. O modelo desenhava barra redonda D16.
#
# ---------------------------------------------------------------------------
# TEXTO DA NORMA (conferido no PDF, nao de memoria):
#
# 4.11.3.4 "A forca resistente e a rigidez de calculo necessarias das contencoes
#           de translacao NODAIS sao dadas, respectivamente, por:"
#               Fbr,Sd = 0,02 . Msd . Cd / h0
#               Sbr,Sd = 10 . Msd . Cd . gamma_r / (Lbb . h0)
#
#   CUIDADO: o item VIZINHO 4.11.3.3 trata das contencoes RELATIVAS e usa
#   coeficientes DIFERENTES (0,008 e 4). A mao-francesa trava um PONTO da mesa
#   -> e NODAL -> 4.11.3.4. Trocar os itens subdimensiona por 2,5x.
#
# 4.11.3.3 (definicoes, valem para os dois):
#   gamma_r "e um coeficiente de ponderacao da rigidez, igual a 1,35"
#   Msd     "e o momento fletor solicitante de calculo"
#   h0      "e a distancia entre os centros geometricos das mesas"
#   Cd      "e um coeficiente igual a 1,00, exceto para a contencao situada nas
#            vizinhancas do ponto de inflexao, em barras sujeitas a flexao com
#            curvatura reversa, quando deve ser tomado igual a 2,00"
#   Lbb     "e a distancia entre contencoes (comprimento destravado)"
#
# 5.3.4.1 "O indice de esbeltez das barras comprimidas [...] nao deve ser
#          superior a 200."
#
# 5.3.2   Nc,Rd = chi . Q . Ag . fy / gamma_a1
#
# TRACAO **E** COMPRESSAO (Fakury, Cap. 5, Fig. 5.22): "a forca axial solicitante
# nas contencoes laterais [...] deve ser considerada na direcao perpendicular aos
# elementos travados e COMO DE TRACAO E DE COMPRESSAO, pois o movimento lateral
# desses elementos pode se dar para um lado ou para o lado oposto. Se uma
# contencao formar um angulo diferente de 90 graus com o elemento travado, sua
# forca solicitante precisa ser ajustada para o angulo de inclinacao."
# => por isso a peca NAO pode ser um tirante (barra redonda so traciona), e por
#    isso a forca do braco e Fbr/cos(ang) e a rigidez util e (EA/L).cos^2(ang).
# ---------------------------------------------------------------------------
# NAO IMPLEMENTADO (de proposito, para nao inventar):
#   - catalogo de CANTONEIRAS: nao ha tabela de perfis L com A/I/rmin nas fontes
#     do projeto. Passe a secao explicitamente (Ask-Do-Not-Invent).
#   - Q de cantoneira simples (Anexo F, Grupo 2: (b/t)lim = 0,45.raiz(E/fy)) e a
#     regra E.1.4 (usar Ix1, eixo paralelo a aba conectada, quando ligada por uma
#     unica aba). Para BARRA REDONDA MACICA Q = 1,0 (secao sem elementos de
#     chapa: o Anexo F trata de relacoes largura/espessura, que nao existem aqui).
# Calcula apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Verificacao da peca da mao-francesa (NBR 8800 4.11.3.4 + 5.3.2 + 5.3.4.1)."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck

E = ck.E                      # 200e6 kN/m2
GA1 = ck.GA1                  # 1,10
GAMMA_R = 1.35                # 4.11.3.3: coeficiente de ponderacao da rigidez
ESBELTEZ_MAX = 200.0          # 5.3.4.1 (barras COMPRIMIDAS)


def requisitos_nodal(Msd, h0, Lbb, Cd=1.0):
    """NBR 8800 4.11.3.4 - contencao de translacao NODAL.

    Msd (kN.m), h0 (m), Lbb (m) -> (Fbr_Sd kN, Sbr_Sd kN/m).
    Cd=1,0; use 2,0 nas vizinhancas do ponto de inflexao (curvatura reversa).
    """
    if h0 <= 0 or Lbb <= 0:
        raise ValueError("h0 e Lbb devem ser positivos")
    Fbr = 0.02 * Msd * Cd / h0
    Sbr = 10.0 * Msd * Cd * GAMMA_R / (Lbb * h0)
    return Fbr, Sbr


def requisitos_relativa(Msd, h0, Lbb, Cd=1.0):
    """NBR 8800 4.11.3.3 - contencao RELATIVA. NAO e o caso da mao-francesa;
    existe aqui so para deixar explicito que os coeficientes sao outros."""
    return (0.008 * Msd * Cd / h0,
            4.0 * Msd * Cd * GAMMA_R / (Lbb * h0))


def secao_barra_redonda(d):
    """Barra redonda MACICA de diametro d (m). r = d/4 (I=pi.d^4/64, A=pi.d^2/4).
    Q = 1,0: nao ha elemento de chapa (relacao b/t) a que o Anexo F se aplique."""
    A = math.pi * d ** 2 / 4.0
    return {"A": A, "r": d / 4.0, "Q": 1.0, "nome": "barra redonda D%.0f" % (d * 1000)}


def qs_cantoneira_simples(b_t, fy):
    """Anexo F / Tabela F.1 - ABA DE CANTONEIRA SIMPLES (elemento AL):
        (b/t)lim = 0,45.raiz(E/fy) ; (b/t)sup = 0,91.raiz(E/fy)
        Qs = 1,0                                   se b/t <= lim
        Qs = 1,340 - 0,76 (b/t) raiz(fy/E)         se lim < b/t <= sup
        Qs = 0,53 E / ((b/t)^2 fy)                 se b/t > sup

    GRUPO - CUIDADO COM AS DUAS NUMERACOES (me confundiu uma vez):
      NBR 8800 Tabela F.1, GRUPO 3 (texto literal): "Abas de cantoneiras simples
      ou multiplas providas de chapas de travejamento" -> 0,45.raiz(E/fy).
      O livro do Fakury chama o MESMO caso de "Grupo 2 da Tabela 7.3". Numeracoes
      diferentes, mesmo valor.

    A linha VIZINHA (NBR Tabela F.1 GRUPO 4) - "Abas de cantoneiras ligadas
    CONTINUAMENTE ou projetadas de secoes I, H, T ou U" - usa 0,56.raiz(E/fy),
    MAIOR/menos restritiva. Nao e o caso: a mao-francesa e cantoneira SIMPLES.
    """
    rE = math.sqrt(E / fy)
    lim, sup = 0.45 * rE, 0.91 * rE
    if b_t <= lim:
        return 1.0
    if b_t <= sup:
        return 1.340 - 0.76 * b_t * math.sqrt(fy / E)
    return 0.53 * E / (b_t ** 2 * fy)


def secao_cantoneira(b_mm, t_mm, fy):
    """Cantoneira de abas iguais para a mao-francesa. Propriedades DERIVADAS da
    geometria (perfis.cantoneira) - nao ha tabela de perfis L nas fontes, e
    inventar bitola de catalogo de memoria e o erro que se quer evitar.

    r = r_min (eixo principal fraco, o que governa a flambagem da cantoneira
    simples). ATENCAO: a NBR 8800 E.1.4 permite usar Ix1 (eixo paralelo a aba
    conectada) quando a cantoneira e ligada por UMA aba, soldada ou com >= 2
    parafusos e sem acoes transversais intermediarias - isso e MENOS conservador
    e NAO esta implementado aqui. Ficamos no r_min.
    """
    import perfis
    c = perfis.cantoneira(b_mm, t_mm)
    return {"A": c["A"], "r": c["r_min"], "Q": qs_cantoneira_simples(c["b_t"], fy),
            "b_t": c["b_t"], "nome": c["nome"]}


def compressao_resistente(sec, fy, L, K=1.0):
    """NBR 8800 5.3.2: Nc,Rd = chi.Q.Ag.fy/gamma_a1, com chi de 5.3.3."""
    A, r, Q = sec["A"], sec["r"], sec.get("Q", 1.0)
    esb = K * L / r
    Ne = math.pi ** 2 * E * (A * r ** 2) / (K * L) ** 2      # I = A.r^2
    lambda0 = math.sqrt(Q * A * fy / Ne)
    chi = ck.chi_compressao(lambda0)
    return {"esbeltez": esb, "Ne": Ne, "lambda0": lambda0, "chi": chi,
            "Nc_Rd": chi * Q * A * fy / GA1}


def verifica_braco(Msd, h0, Lbb, L_braco, ang_graus, sec, fy, Cd=1.0, K=1.0):
    """Verifica a peca da mao-francesa. Angulo = entre o EIXO DO BRACO e a
    direcao da forca de contencao (perpendicular ao elemento travado).

    O braco tipico liga a mesa inferior a uma terca com deslocamento
    LONGITUDINAL igual ao desnivel -> 45 graus.
    """
    Fbr, Sbr = requisitos_nodal(Msd, h0, Lbb, Cd)
    ca = math.cos(math.radians(ang_graus))
    if ca <= 1e-6:
        raise ValueError("braco perpendicular a forca de contencao: nao contem nada")
    N_braco = Fbr / ca                       # forca AXIAL no braco (tracao e compressao)
    S_braco = (E * sec["A"] / L_braco) * ca ** 2   # rigidez util na direcao da forca
    c = compressao_resistente(sec, fy, L_braco, K)
    r = {"Fbr_Sd": Fbr, "Sbr_Sd": Sbr, "N_braco": N_braco, "S_braco": S_braco,
         "ang": ang_graus, "L_braco": L_braco, "Cd": Cd, "secao": sec.get("nome", ""),
         **c}
    r["ok_esbeltez"] = c["esbeltez"] <= ESBELTEZ_MAX
    r["ok_resistencia"] = N_braco <= c["Nc_Rd"]
    r["ok_rigidez"] = S_braco >= Sbr
    r["ok"] = bool(r["ok_esbeltez"] and r["ok_resistencia"] and r["ok_rigidez"])
    faltas = []
    if not r["ok_esbeltez"]:
        faltas.append("esbeltez %.0f > %.0f (5.3.4.1)" % (c["esbeltez"], ESBELTEZ_MAX))
    if not r["ok_resistencia"]:
        faltas.append("N=%.2f kN > Nc,Rd=%.2f kN (5.3.2)" % (N_braco, c["Nc_Rd"]))
    if not r["ok_rigidez"]:
        faltas.append("S=%.0f < Sbr,Sd=%.0f kN/m (4.11.3.4)" % (S_braco, Sbr))
    r["motivo"] = "; ".join(faltas)
    if not r["ok"]:
        r["minimo"] = secao_minima(Msd, h0, Lbb, L_braco, ang_graus, fy, Cd, K,
                                   sec.get("Q", 1.0))
    return r


def secao_minima(Msd, h0, Lbb, L_braco, ang_graus, fy, Cd=1.0, K=1.0, Q=1.0):
    """O que a peca precisa TER para atender - para o gate GUIAR, nao so reprovar.

    r_min: direto de 5.3.4.1 (KL/r <= 200).
    A_min: no limite de esbeltez, lambda0 = (KL/r).raiz(Q.fy/(pi^2.E)) NAO depende
           de A, entao chi fica fixo e A_min = N.gamma_a1/(chi.Q.fy).
    A_rig: da rigidez (4.11.3.4): (E.A/L).cos^2 >= Sbr,Sd.
    """
    Fbr, Sbr = requisitos_nodal(Msd, h0, Lbb, Cd)
    ca = math.cos(math.radians(ang_graus))
    N = Fbr / ca
    r_min = K * L_braco / ESBELTEZ_MAX
    lambda0 = ESBELTEZ_MAX * math.sqrt(Q * fy / (math.pi ** 2 * E))
    chi = ck.chi_compressao(lambda0)
    A_res = N * GA1 / (chi * Q * fy)
    A_rig = Sbr * L_braco / (E * ca ** 2)
    return {"r_min": r_min, "A_min": max(A_res, A_rig), "A_resistencia": A_res,
            "A_rigidez": A_rig, "chi_no_limite": chi, "N_exigido": N}


def relatorio_pt(r):
    L = ["=" * 68,
         "MAO-FRANCESA - VERIFICACAO DA PECA (NBR 8800 4.11.3.4)",
         "contencao de translacao NODAL (nao relativa: 4.11.3.3 usa 0,008 e 4)",
         "=" * 68,
         f"  Secao ....................... {r['secao']}",
         f"  Comprimento do braco ........ {r['L_braco']:.3f} m "
         f"(angulo {r['ang']:.0f} graus)",
         f"  Cd .......................... {r['Cd']:.2f}",
         "  --- solicitacao (4.11.3.4) ---",
         f"  Fbr,Sd = 0,02.Msd.Cd/h0 ..... {r['Fbr_Sd']:.2f} kN",
         f"  N no braco = Fbr/cos(ang) ... {r['N_braco']:.2f} kN (tracao E compressao)",
         f"  Sbr,Sd = 10.Msd.Cd.1,35/(Lbb.h0) {r['Sbr_Sd']:.0f} kN/m",
         "  --- resistencia da peca ---",
         f"  Esbeltez KL/r ............... {r['esbeltez']:.0f} "
         f"(limite {ESBELTEZ_MAX:.0f}) {'OK' if r['ok_esbeltez'] else 'NAO ATENDE'}",
         f"  lambda0 / chi ............... {r['lambda0']:.3f} / {r['chi']:.3f}",
         f"  Nc,Rd (5.3.2) ............... {r['Nc_Rd']:.2f} kN "
         f"{'OK' if r['ok_resistencia'] else 'NAO ATENDE'}",
         f"  Rigidez do braco ............ {r['S_braco']:.0f} kN/m "
         f"{'OK' if r['ok_rigidez'] else 'NAO ATENDE'}",
         "-" * 68]
    if r["ok"]:
        L.append("  >> ATENDE")
    else:
        L.append("  >> NAO ATENDE - REFORCO EXIGIDO: " + r["motivo"])
        m = r.get("minimo")
        if m:
            L += ["  MINIMO NORMATIVO calculado (o eng. escolhe no catalogo):",
                  f"    raio de giracao r >= {m['r_min']*1000:.1f} mm "
                  f"(5.3.4.1: KL/r <= {ESBELTEZ_MAX:.0f})",
                  f"    area bruta Ag >= {m['A_min']*1e4:.2f} cm2 "
                  f"(resistencia {m['A_resistencia']*1e4:.2f} ; "
                  f"rigidez {m['A_rigidez']*1e4:.2f})",
                  "  BOA PRATICA (Bellei/Fakury Fig. 8.16-8.17 e 5.22): usar",
                  "    CANTONEIRA. Atencao: uma barra redonda de diametro maior",
                  "    ATENDERIA a conta acima, mas a literatura reserva a barra",
                  "    redonda para TIRANTE (so tracao) e manda a contencao lateral",
                  "    resistir 'como de tracao E de compressao'. A conta nao",
                  "    captura isso - a escolha do perfil e do eng. responsavel."]
    L.append("=" * 68)
    return "\n".join(L)


def _selftest():
    # Barra redonda D16 (o que o modelo desenhava). L do EIXO = 0,9324 m a 45
    # graus, obtido de mao_francesa_geom.comprimento_braco (rafter 500x200, terca
    # Ue300x85, i=15%). ATENCAO: o bbox do cilindro no modelo mede 948,4 mm - ele
    # inclui d.sen(45)=11,3 mm de raio. Usar o bbox como comprimento de flambagem
    # superestima a esbeltez (237 em vez de 233); o correto e o EIXO.
    sec = secao_barra_redonda(0.016)
    r = verifica_braco(Msd=61.3, h0=0.1615, Lbb=3.35, L_braco=0.9324,
                       ang_graus=45.0, sec=sec, fy=250e3)
    print(relatorio_pt(r))
    assert not r["ok_esbeltez"], "D16 a 0,93 m tem KL/r=233 > 200: tem que reprovar"
    assert not r["ok"]
    # coerencia: 4.11.3.3 (relativa) da valores MENORES - nao confundir os itens
    fn, sn = requisitos_nodal(61.3, 0.1615, 3.35)
    fr, sr = requisitos_relativa(61.3, 0.1615, 3.35)
    assert fn > fr and sn > sr
    assert abs(fn / fr - 2.5) < 1e-9, "0,02/0,008 = 2,5"
    assert abs(sn / sr - 2.5) < 1e-9, "10/4 = 2,5"
    # Cd=2,0 dobra os dois requisitos
    f2, s2 = requisitos_nodal(61.3, 0.1615, 3.35, Cd=2.0)
    assert abs(f2 / fn - 2.0) < 1e-9 and abs(s2 / sn - 2.0) < 1e-9
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
