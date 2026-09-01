"""Primitiva GEOMETRICA do modelo neutro: caixa envolvente, interpenetracao e
quantitativo de uma lista de membros.

Ja havia tres leituras da mesma caixa espalhadas pelo framework (o clash do
galpao de concreto, o build FreeCAD e o emissor IFC), e foi justamente onde a
convencao de unidade divergiu sem ninguem notar. Toda tipologia nova le a caixa
por aqui.

Convencao (a mesma do `ifc_emit` e do `build_concreto`):
  coordenadas em MILIMETROS; `dims` de caixa em MILIMETROS; secao de barra
  (`bf`, `d`) em METROS; `bf` = largura transversal ao eixo, `d` = altura;
  `ancoragem` diz onde a linha p1->p2 cai na secao ('eixo', padrao, ou 'base').
  Contrato explicito em `fronteiras.F01_sapata_dims_mm` / F03 / F04 / F05.
"""

from __future__ import annotations

import math

import fronteiras as _FR  # contrato explicito de unidade (F01/F03/F04/F05)

MM = 1000.0
# Re-exporta as unidades canonicas para quem importa deste modulo
UNIDADE_DIMS = _FR.UNIDADE_DIMS_MM  # mm
UNIDADE_SECAO = _FR.UNIDADE_SECAO_M  # m
ANCORAGEM_PADRAO = _FR.UNIDADE_ANCORAGEM_ENUM[0]  # "eixo"

# tolerancia geometrica (mm). Abaixo disso e' arredondamento de ponto flutuante;
# acima, peca dentro de peca.
TOL_MM = 1.0


def aabb(membro):
    """Caixa envolvente do membro em mm: (x0, x1, y0, y1, z0, z1)."""
    if "dims" in membro:
        dx, dy, dz = membro["dims"]
        cx, cy, cz = membro["centro"]
        return (cx - dx / 2, cx + dx / 2, cy - dy / 2, cy + dy / 2,
                cz - dz / 2, cz + dz / 2)
    p1, p2 = membro["p1"], membro["p2"]
    secao = membro["secao"]
    if str(secao.get("forma", "")).upper() == "ROUND":
        # barra circular: a envolvente e' D nas DUAS direcoes transversais
        bf = d = float(secao["D"]) * MM
    else:
        bf, d = secao["bf"] * MM, secao["d"] * MM
    x0, x1 = sorted((p1[0], p2[0]))
    y0, y1 = sorted((p1[1], p2[1]))
    z0, z1 = sorted((p1[2], p2[2]))
    if abs(z1 - z0) > max(abs(x1 - x0), abs(y1 - y0)):    # barra VERTICAL (pilar)
        return (x0 - bf / 2, x1 + bf / 2, y0 - d / 2, y1 + d / 2, z0, z1)
    base = membro.get("ancoragem") == "base"
    zi = z0 if base else z0 - d / 2                       # onde comeca a altura
    if abs(x1 - x0) >= abs(y1 - y0):                      # barra que corre em X
        return (x0, x1, y0 - bf / 2, y1 + bf / 2, zi, zi + d)
    return (x0 - bf / 2, x1 + bf / 2, y0, y1, zi, zi + d)  # barra que corre em Y


def volume_comum(a, b, folga=TOL_MM):
    """Volume (mm3) da intersecao de duas caixas. Peca que compartilha FACE tem
    volume comum zero - o toque nao conta como interpenetracao."""
    dx = min(a[1], b[1]) - max(a[0], b[0]) - folga
    dy = min(a[3], b[3]) - max(a[2], b[2]) - folga
    dz = min(a[5], b[5]) - max(a[4], b[4]) - folga
    return dx * dy * dz if (dx > 0 and dy > 0 and dz > 0) else 0.0


def interpenetracoes(membros):
    """Pares de membros que ocupam o MESMO volume (caixa envolvente).

    E' a varredura que o build FreeCAD faz sobre solidos reais, feita aqui sem
    FreeCAD para que ela rode no CI. Retorna {'OK', 'conflitos', 'n_membros'}.
    """
    caixas = [(m, aabb(m)) for m in membros]
    conflitos = []
    for i in range(len(caixas)):
        ma, ca = caixas[i]
        for j in range(i + 1, len(caixas)):
            mb, cb = caixas[j]
            vol = volume_comum(ca, cb)
            if vol > TOL_MM ** 3:
                conflitos.append({"a": ma.get("marca"), "b": mb.get("marca"),
                                  "vol_mm3": round(vol, 1)})
    return {"OK": not conflitos, "conflitos": conflitos, "n_membros": len(membros)}


def volume(membro):
    """Volume da peca (m3). Barra de secao CIRCULAR (estaca, tirante) usa
    pi*D^2/4, nao o quadrado da envolvente - a diferenca e' 27 % e apareceria
    direto no quantitativo de concreto."""
    if "dims" not in membro and str(
            (membro.get("secao") or {}).get("forma", "")).upper() == "ROUND":
        p1, p2 = membro["p1"], membro["p2"]
        comprimento = math.dist(p1, p2)
        raio = float(membro["secao"]["D"]) * MM / 2.0
        return math.pi * raio ** 2 * comprimento / 1e9
    c = aabb(membro)
    return ((c[1] - c[0]) * (c[3] - c[2]) * (c[5] - c[4])) / 1e9


def quantitativo(membros):
    """Volume por tipo de peca (m3) direto do modelo neutro.

    O TOTAL sai da soma dos volumes CHEIOS, nao da soma dos ja arredondados -
    a mesma ordem de `build_concreto._takeoff`. Somar arredondados dava 1 mm3 de
    diferenca entre os dois caminhos, o bastante para o cross-check reprovar por
    motivo nenhum.
    """
    por = {}
    for membro in membros:
        vol = volume(membro)
        registro = por.setdefault(membro["tipo"], {"n": 0, "vol_m3": 0.0})
        registro["n"] += 1
        registro["vol_m3"] += vol
    total = sum(r["vol_m3"] for r in por.values())
    for registro in por.values():
        registro["vol_m3"] = round(registro["vol_m3"], 3)
    return {"por_tipo": por, "vol_concreto_m3": round(total, 3)}
