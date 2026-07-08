# ============================================================================
# junta_dilatacao.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica a NECESSIDADE de JUNTA DE DILATACAO no galpao (efeito de temperatura)
# e o MOVIMENTO TERMICO longitudinal. Fecha a lacuna da acao de temperatura em
# edificio longo (a estrutura dilata/contrai; sem junta os esforcos de coacao e o
# deslocamento crescem com o comprimento).
#
#   - Movimento termico:  delta = alpha * dT * L   (alongamento/encurtamento).
#   - Comprimento maximo entre juntas: guia do "FEDERAL CONSTRUCTION COUNCIL
#     TECHNICAL REPORT No.65 - Expansion Joints in Building" (via AISC 2005 /
#     Bellei, "Edificios de Multiplos Andares em Aco", 4.5), para dT > 20 C
#     (condicao normal no Brasil):
#       base 120 m (edificio de ACO RETANGULAR, varios porticos rigidez simetrica);
#       base  60 m (qualquer material, forma NAO retangular tipo L,T,U);
#     modificada pela SOMA ALGEBRICA dos fatores:
#       - sem aquecimento interno:                        -33%
#       - ar-condicionado + aquecimento + controle:       +15%
#       - bases FIXAS (engastadas):                       -15%
#       - maior rigidez lateral em um dos planos:         -25%
#     (aquecido + base rotulada = usa o maximo, sem reducao.)
#
# alpha=12e-6/C e dT (variacao) = dado (Bellei: media Brasil +-15 C = 30 C); a
# skill confirma. Saidas em portugues. Unidades: m, C. CONCEITUAL - o eng. revisa.
# ============================================================================
"""Junta de dilatacao: necessidade (comprimento max) + movimento termico."""

from __future__ import annotations

import math
import re

ALPHA_ACO = 12e-6          # coef. de dilatacao termica do aco (/C) - NBR 8800/Bellei
DT_BRASIL = 30.0           # variacao media de temperatura (+-15 C) - Bellei 4.5


def movimento_termico(L, dT=DT_BRASIL, alpha=ALPHA_ACO):
    """Alongamento/encurtamento termico total: delta = alpha * dT * L (m).
    O movimento por lado (a partir do ponto fixo) e ~metade se simetrico."""
    return alpha * dT * L


def comprimento_max_junta(retangular=True, aquecido=False, ar_condicionado=False,
                          base_fixa=True, rigidez_assimetrica=False):
    """Comprimento maximo recomendado entre juntas de dilatacao (m), guia do
    Federal Construction Council Report No.65 (via Bellei 4.5). Retorna (L_max,
    fator_total)."""
    base = 120.0 if retangular else 60.0
    f = 0.0
    if not aquecido:
        f -= 0.33                              # sem aquecimento interno
    if ar_condicionado and aquecido:
        f += 0.15                              # AC + aquecimento + controle continuo
    if base_fixa:
        f -= 0.15                              # bases fixas (engastadas)
    if rigidez_assimetrica:
        # maior rigidez lateral em um plano: contraventamento vertical (X)
        # concentrado em UMA fachada/plano (nao distribuido) -> a estrutura se
        # dilata contra o ponto rigido, ampliando a coacao termica.
        f -= 0.25
    return base * (1.0 + f), f


def verifica_junta(L_total, dT=DT_BRASIL, retangular=True, aquecido=False,
                   ar_condicionado=False, base_fixa=True,
                   rigidez_assimetrica=False, alpha=ALPHA_ACO):
    """Necessidade de junta + movimento termico. Divide o comprimento total em
    segmentos <= L_max (n_juntas = ceil(L_total/L_max) - 1) e calcula o movimento
    do maior segmento. Retorna dict."""
    Lmax, fator = comprimento_max_junta(retangular, aquecido, ar_condicionado,
                                        base_fixa, rigidez_assimetrica)
    if Lmax <= 0:
        Lmax = 1e-9
    precisa = L_total > Lmax + 1e-9
    n_juntas = max(0, math.ceil(L_total / Lmax) - 1)
    n_seg = n_juntas + 1
    L_seg = L_total / n_seg
    delta_seg = movimento_termico(L_seg, dT, alpha)
    delta_total = movimento_termico(L_total, dT, alpha)
    return {"L_total": L_total, "L_max_junta": Lmax, "fator_total": fator,
            "precisa_junta": precisa, "n_juntas": n_juntas, "n_segmentos": n_seg,
            "L_segmento": L_seg, "dT": dT,
            "delta_segmento_mm": delta_seg * 1000.0,
            "delta_total_mm": delta_total * 1000.0,
            "OK": not precisa}          # OK = nao precisa de junta (cabe num trecho)


def relatorio_pt(r):
    L = ["=" * 70, "JUNTA DE DILATACAO / MOVIMENTO TERMICO (temperatura)",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
         f"Comprimento do galpao: {r['L_total']:.1f} m ; dT = {r['dT']:.0f} C "
         f"(alpha=12e-6/C) [Bellei 4.5 / FCC Report 65]",
         f"Comprimento maximo entre juntas: {r['L_max_junta']:.1f} m "
         f"(fator {r['fator_total']*100:+.0f}%)",
         ""]
    if r["precisa_junta"]:
        meia = r['delta_segmento_mm'] / 2.0
        L += [f">> PRECISA de junta: {r['n_juntas']} junta(s) -> {r['n_segmentos']} "
              f"trechos de ~{r['L_segmento']:.1f} m (cada <= L_max).",
              f"   Movimento termico do trecho: delta={r['delta_segmento_mm']:.1f} mm "
              f"-> ~{meia:.1f} mm por lado da junta.",
              f"   DETALHE (executivo, confirmar): furos oblongos/apoio deslizante que",
              f"   absorvam ~{meia:.1f} mm por lado, OU dimensionar os pilares de",
              f"   extremidade para o momento do deslocamento imposto no topo."]
    else:
        meia = r['delta_total_mm'] / 2.0
        L += [f">> NAO precisa de junta ({r['L_total']:.1f} m <= {r['L_max_junta']:.1f} m).",
              f"   Movimento termico total: delta={r['delta_total_mm']:.1f} mm "
              f"(~{meia:.1f} mm por lado).",
              f"   Sem junta: os apoios/pilares de extremidade absorvem esse "
              f"deslocamento (furo oblongo) ou sao dimensionados para a coacao termica."]
    L += ["", "[FLAG] dT e as condicoes (aquecimento, AC, base, rigidez) sao dados",
          "       do projeto/sitio - a skill confirma. Detalhe da junta (linha dupla",
          "       de pilares, apoio deslizante) = projeto executivo."]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # 1) movimento termico: delta = alpha*dT*L
    assert abs(movimento_termico(100.0, 30.0) - 12e-6 * 30.0 * 100.0) < 1e-12
    # 2) comprimento max: retangular base 120 ; galpao tipico (sem aquec + base fixa)
    Lmax, f = comprimento_max_junta(retangular=True, aquecido=False, base_fixa=True)
    assert abs(f - (-0.33 - 0.15)) < 1e-12
    assert abs(Lmax - 120.0 * (1 - 0.48)) < 1e-9          # 62,4 m
    # nao-retangular base 60 ; aquecido + rotulado = usa o maximo (sem reducao)
    Lmax2, f2 = comprimento_max_junta(retangular=False, aquecido=True, base_fixa=False)
    assert abs(Lmax2 - 60.0) < 1e-9 and abs(f2) < 1e-12
    # 3) verifica: galpao 100 m tipico (Lmax 62,4) -> precisa 1 junta (2 trechos 50 m)
    r = verifica_junta(100.0)
    assert r["precisa_junta"] and r["n_juntas"] == 1 and r["n_segmentos"] == 2
    assert abs(r["L_segmento"] - 50.0) < 1e-9
    assert abs(r["delta_segmento_mm"] - 12e-6 * 30.0 * 50.0 * 1000.0) < 1e-9
    # galpao curto 40 m -> nao precisa
    r2 = verifica_junta(40.0)
    assert not r2["precisa_junta"] and r2["n_juntas"] == 0 and r2["OK"]
    print("junta_dilatacao self-test PASSED")
    print(f"  galpao tipico: L_max={Lmax:.1f} m ; 100 m -> {r['n_juntas']} junta(s), "
          f"trecho {r['L_segmento']:.1f} m, delta={r['delta_segmento_mm']:.1f} mm")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_junta(100.0)))
