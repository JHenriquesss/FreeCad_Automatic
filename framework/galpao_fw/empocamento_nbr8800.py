# ============================================================================
# empocamento_nbr8800.py - EMPOCAMENTO PROGRESSIVO (ponding), NBR 8800 item 9.3
# A NBR 8800:2008 (9.3) NAO prescreve formula fechada: "Recomenda-se que a
# inclinacao de uma cobertura nao seja inferior a 3 %. Quando a inclinacao for
# inferior a 3 %, verificacoes adicionais devem ser feitas para assegurar que
# nao ocorrera colapso estrutural causado pelo peso proprio da agua acumulada em
# virtude das flechas (...), usando combinacoes ultimas de acoes." (+ Tabela C.1
# nota g: "evitar o empocamento, atencao especial a telhados de pequena declivi-
# dade"). Logo o GATE e geometrico: incl >= 3% dispensa; incl < 3% exige a
# analise incremental de flecha x agua (nao automatizada) -> NAO ATENDE ate que
# o engenheiro a faca (ou aumente a declividade). Valores lidos do PDF.
# ============================================================================
"""Empocamento progressivo em cobertura de baixa inclinacao (NBR 8800 9.3)."""

from __future__ import annotations

import math

INCL_MIN_PCT = 3.0            # 9.3: declividade minima recomendada (dispensa a analise)


def incl_pct_de_theta(theta_rad):
    """Inclinacao da agua em % (tan do angulo) a partir do angulo em radianos."""
    return math.tan(theta_rad) * 100.0


def verifica_empocamento(incl_pct):
    """Gate de empocamento (NBR 8800 9.3). incl_pct = declividade da agua (%).
      incl >= 3%  -> dispensado (OK): a norma so exige verificacao abaixo de 3%.
      incl < 3%   -> exige analise adicional (flecha x peso da agua acumulada,
                     combinacoes ultimas); nao automatizada -> ok=False +
                     recomendacao. Retorna dict."""
    dispensado = incl_pct >= INCL_MIN_PCT - 1e-9
    return {
        "incl_pct": incl_pct, "incl_min_pct": INCL_MIN_PCT,
        "dispensado": dispensado, "OK": dispensado,
        "flag": (
            "Empocamento (9.3): declividade %.2f%% >= %.0f%% -> DISPENSADO."
            % (incl_pct, INCL_MIN_PCT) if dispensado else
            "Empocamento (9.3): declividade %.2f%% < %.0f%% -> EXIGE verificacao "
            "adicional do peso da agua acumulada (flecha, combinacoes ultimas). "
            "NAO automatizada: aumentar a declividade (>=3%%) ou anexar a analise "
            "incremental de empocamento. Ate la, NAO ATENDE." % (incl_pct, INCL_MIN_PCT)),
    }


def relatorio_pt(r):
    return "\n".join([
        "=" * 60, "EMPOCAMENTO PROGRESSIVO (ABNT NBR 8800:2008, item 9.3)",
        "=" * 60,
        "  Declividade da agua: %.2f %% (minimo recomendado %.0f %%)"
        % (r["incl_pct"], r["incl_min_pct"]),
        "  " + r["flag"],
        "  RESULTADO: %s" % ("DISPENSADO/ATENDE" if r["OK"] else "NAO ATENDE"), ""])


def _selftest():
    # telhado 5% (tipico galpao) -> dispensado
    r5 = verifica_empocamento(5.0)
    assert r5["dispensado"] and r5["OK"]
    # exatamente 3% -> dispensado (limite inclusivo)
    assert verifica_empocamento(3.0)["OK"]
    # 2% (agua rasa / shed quase plano) -> exige analise, NAO ATENDE
    r2 = verifica_empocamento(2.0)
    assert not r2["dispensado"] and not r2["OK"] and "NAO ATENDE" in r2["flag"]
    # theta -> incl%: 10 graus ~ 17,6%
    assert abs(incl_pct_de_theta(math.radians(10.0)) - 17.63) < 0.1
    print("empocamento_nbr8800 _selftest PASSED")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_empocamento(2.0)))
