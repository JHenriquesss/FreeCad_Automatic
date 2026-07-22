# ============================================================================
# diafragma.py - EFEITO DE DIAFRAGMA da cobertura (distribuicao da forca lateral
# entre os porticos). Torna EXPLICITA a hipotese que antes era implicita no 2D.
#
# CLASSIFICACAO (ABNT NBR 15421:2023, item 8.3.2 - "Deformabilidade dos
# diafragmas"): o diafragma e FLEXIVEL se a maxima deflexao horizontal no plano
# do diafragma for MAIOR que o DOBRO da media dos deslocamentos relativos (drift)
# dos porticos; caso contrario pode ser RIGIDO (o caso classico rigido e a laje
# de concreto com vao/profundidade < 3). Nem um nem outro -> SEMIRRIGIDO (modelar
# a rigidez).
#
# DISTRIBUICAO da forca lateral (Pfeil; Fakury; log de sismo do framework):
#   - FLEXIVEL: por AREA/LARGURA TRIBUTARIA de cada portico. Cobertura de TELHA
#     METALICA sem contraventamento rigido no plano atua como diafragma FLEXIVEL
#     -> a distribuicao tributaria (que o rodar_galpao ja usa) e a mais fiel.
#   - RIGIDO: por RIGIDEZ relativa dos porticos + torcao se ha excentricidade
#     (so vale quando ha contraventamento longitudinal de cobertura, que
#     "transforma a cobertura em diafragma", Fakury Fig.5.5).
#
# Este modulo NAO reduz secoes automaticamente: e ANALISE/relatorio. A economia
# (colunas mais leves) so se materializa se o eng. prover o diafragma rigido e
# adotar a redistribuicao - decisao dele, documentada. Modulo PURO (headless).
# ============================================================================
"""Efeito de diafragma da cobertura (NBR 15421 8.3.2 + distribuicao)."""

from __future__ import annotations


def classifica_diafragma(deflexao_plano, drift_medio, concreto_vao_prof=None):
    """Classifica o diafragma (NBR 15421 8.3.2). deflexao_plano = maxima deflexao
    horizontal NO PLANO do diafragma; drift_medio = media dos deslocamentos
    relativos (drift) dos porticos dos pontos extremos. concreto_vao_prof =
    relacao vao/profundidade se for laje de concreto (rigido se < 3,0)."""
    if drift_medio <= 0:
        return {"classe": "indefinido", "razao": None,
                "motivo": "drift medio <= 0 (sem carga lateral?)"}
    razao = deflexao_plano / drift_medio
    if razao > 2.0:
        classe = "flexivel"
        motivo = "deflexao no plano (%.2f) > 2x drift medio (%.2f) -> 8.3.2" % (
            deflexao_plano, 2.0 * drift_medio)
    elif concreto_vao_prof is not None and concreto_vao_prof < 3.0:
        classe = "rigido"
        motivo = "laje de concreto vao/prof=%.1f < 3,0 e nao-flexivel (8.3.2)" % concreto_vao_prof
    elif razao <= 2.0:
        classe = "rigido"
        motivo = "deflexao no plano (%.2f) <= 2x drift medio (%.2f) (8.3.2)" % (
            deflexao_plano, 2.0 * drift_medio)
    else:
        classe = "semirrigido"
        motivo = "nem rigido nem flexivel -> modelar a rigidez (8.3.2)"
    return {"classe": classe, "razao": razao, "motivo": motivo}


def distribui_flexivel(F_total, larguras_trib):
    """Diafragma FLEXIVEL: forca por portico proporcional a LARGURA TRIBUTARIA.
    larguras_trib = lista das larguras tributarias (m) de cada portico."""
    s = sum(larguras_trib)
    if s <= 0:
        return [0.0] * len(larguras_trib)
    return [F_total * w / s for w in larguras_trib]


def distribui_rigido(F_total, rigidezes, posicoes=None, exc=0.0):
    """Diafragma RIGIDO: forca por portico proporcional a RIGIDEZ relativa; se ha
    excentricidade `exc` (m) da resultante em relacao ao centro de rigidez, soma
    a parcela de TORCAO (F_i inclui K_i*d_i*(F*exc)/Sum(K_j*d_j^2)).
    rigidezes = rigidez lateral de cada portico ; posicoes = coordenada de cada
    portico ao longo do comprimento (m), p/ a torcao (default: igualmente espacados)."""
    n = len(rigidezes)
    K = sum(rigidezes)
    if K <= 0:
        return [0.0] * n
    if posicoes is None:
        posicoes = list(range(n))
    # centro de rigidez
    xr = sum(k * x for k, x in zip(rigidezes, posicoes)) / K
    d = [x - xr for x in posicoes]
    Jt = sum(k * di * di for k, di in zip(rigidezes, d))     # rigidez torcional
    Mt = F_total * exc                                        # momento de torcao
    F = []
    for k, di in zip(rigidezes, d):
        direto = F_total * k / K
        torc = (k * di * Mt / Jt) if Jt > 0 and Mt else 0.0
        F.append(direto + torc)
    return F


def relatorio_pt(classe_info, forcas=None, metodo=None):
    L = ["=" * 66, "EFEITO DE DIAFRAGMA DA COBERTURA (NBR 15421 8.3.2)", "=" * 66,
         "  Classe: %s" % classe_info["classe"].upper(),
         "  %s" % classe_info["motivo"]]
    if forcas is not None:
        L.append("  Distribuicao (%s): %s kN" % (
            metodo or "-", ", ".join("%.1f" % f for f in forcas)))
    L += ["  [Telha metalica sem contravento rigido no plano = FLEXIVEL ->",
          "   distribuicao TRIBUTARIA (a que o portico ja usa) e a fiel. A acao",
          "   de diafragma rigido exige contraventamento longitudinal de cobertura.]", ""]
    return "\n".join(L)


def _selftest():
    # 8.3.2: flexivel se deflexao no plano > 2x drift medio
    assert classifica_diafragma(30.0, 10.0)["classe"] == "flexivel"    # 30 > 20
    assert classifica_diafragma(15.0, 10.0)["classe"] == "rigido"      # 15 <= 20
    # laje de concreto vao/prof<3 -> rigido
    assert classifica_diafragma(15.0, 10.0, concreto_vao_prof=2.0)["classe"] == "rigido"
    assert classifica_diafragma(0.0, 0.0)["classe"] == "indefinido"
    # FLEXIVEL: tributaria. 3 porticos, larguras 5/5/5 -> 1/3 cada de 90 kN
    ff = distribui_flexivel(90.0, [5.0, 5.0, 5.0])
    assert all(abs(f - 30.0) < 1e-9 for f in ff)
    # borda com meia largura tributaria recebe menos
    fb = distribui_flexivel(100.0, [2.5, 5.0, 2.5])
    assert abs(fb[0] - 25.0) < 1e-9 and abs(fb[1] - 50.0) < 1e-9
    # RIGIDO sem excentricidade + rigidezes iguais -> igual ao flexivel uniforme
    fr = distribui_rigido(90.0, [1.0, 1.0, 1.0])
    assert all(abs(f - 30.0) < 1e-9 for f in fr)
    # RIGIDO com excentricidade -> torcao: portico da ponta mais afastado recebe mais
    fe = distribui_rigido(90.0, [1.0, 1.0, 1.0], posicoes=[0.0, 5.0, 10.0], exc=2.0)
    assert fe[2] > fe[1] > fe[0]                        # torcao carrega a ponta
    assert abs(sum(fe) - 90.0) < 1e-6                   # equilibrio (soma = F_total)
    # rigidez maior -> puxa mais forca (rigido)
    fk = distribui_rigido(100.0, [3.0, 1.0])
    assert abs(fk[0] - 75.0) < 1e-9 and abs(fk[1] - 25.0) < 1e-9
    print("diafragma _selftest PASSED")


if __name__ == "__main__":
    _selftest()
