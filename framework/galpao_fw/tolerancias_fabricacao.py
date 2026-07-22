# ============================================================================
# tolerancias_fabricacao.py - QUADRO DE TOLERANCIAS de fabricacao e montagem.
# Valores LIDOS das fontes (nao de memoria), cada um com a referencia:
#   NBR 8800:2008 (itens 12.2/12.3 e Tabela 12) + Bellei Apendice C + Manual CBCA.
# Modulo PURO (sem FreeCAD) -> testavel headless; o techdraw_exec renderiza a
# tabela na prancha PE09. O desenho vai para a OBRA -> tolerancia errada e grave.
# ============================================================================
"""Tolerancias de fabricacao/montagem (NBR 8800 + Bellei) para a prancha."""

from __future__ import annotations

# (item, tolerancia, fonte)
TOLERANCIAS_FABRICACAO = [
    ("Comprimento de peca cortada", "+/-2 mm (laminado) ; +/-4 mm (soldado)", "Bellei Ap.C"),
    ("Retilineidade / empenamento", "L/1000 (barra compr., entre travamentos)", "NBR 8800 12.2.1.7.3"),
    ("Esquadro das extremidades", "+/-2 mm (d<=600 mm)", "Bellei Ap.C"),
    ("Posicao de furos (espacamento)", "+/-2 mm", "Bellei Ap.C"),
    ("Posicao de furos (acumulado)", "+/-2 (<=4m) ; +/-3 (4-9m) ; +/-4 (>9m)", "Bellei Ap.C"),
]

TOLERANCIAS_MONTAGEM = [
    ("Prumo de pilar (desaprumo)", "1:500 ; max H/500 ou 5 mm; teto 25 mm", "NBR 8800 12.3.3.1.1"),
    ("Desalinhamento de eixos", "+/-5 mm", "Bellei Ap.C (Tab.C-3)"),
    ("Elevacao do topo de pilar", "+5 mm / -8 mm", "NBR 8800 12.3.3.1.2 b"),
]


def folga_furo(db_mm):
    """Folga do FURO PADRAO em relacao ao diametro do parafuso db (NBR 8800
    Tabela 12): dh = db + 1,5 mm (db < 24 mm) ; db + 2,0 mm (db >= 24 mm)."""
    return db_mm + (1.5 if db_mm < 24.0 else 2.0)


def linhas_quadro(db_mm=None):
    """Linhas do QUADRO DE TOLERANCIAS: (grupo, item, tolerancia, fonte). Se db_mm
    for dado, acrescenta a folga do furo-padrao daquele parafuso (NBR 8800 Tab.12)."""
    linhas = [("FABRICACAO", it, tol, f) for (it, tol, f) in TOLERANCIAS_FABRICACAO]
    linhas += [("MONTAGEM", it, tol, f) for (it, tol, f) in TOLERANCIAS_MONTAGEM]
    dh = ("db+1,5 (db<24) ; db+2,0 (db>=24)" if db_mm is None
          else "db=%.0f -> furo %.1f mm" % (db_mm, folga_furo(db_mm)))
    linhas.append(("FURACAO", "Folga do furo-padrao", dh, "NBR 8800 Tab.12"))
    return linhas


def _selftest():
    assert abs(folga_furo(20.0) - 21.5) < 1e-9       # db<24 -> +1,5
    assert abs(folga_furo(24.0) - 26.0) < 1e-9       # db>=24 -> +2,0
    assert abs(folga_furo(22.0) - 23.5) < 1e-9
    ls = linhas_quadro(db_mm=24.0)
    assert ls[0][0] == "FABRICACAO" and any(g == "MONTAGEM" for g, *_ in ls)
    assert ls[-1][0] == "FURACAO" and "26.0" in ls[-1][2]
    assert all(len(t) == 4 and t[3] for t in ls)     # toda linha tem FONTE
    ls0 = linhas_quadro()
    assert "db+1,5" in ls0[-1][2]
    print("tolerancias_fabricacao _selftest PASSED")


if __name__ == "__main__":
    _selftest()
