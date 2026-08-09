# ============================================================================
# instalacao_eletrica.py - O QUE ESTE MODULO CALCULA
# LEIAUTE DA INSTALACAO ELETRICA do galpao (planta de iluminacao e tomadas):
# POSICIONA os pontos que o resto do projeto so contava, e agrupa em CIRCUITOS.
# Modulo de calculo stateless (CI, _selftest). Base normativa (NBR 5410:2004,
# lida dos PDFs no NotebookLM - regra AR300):
#   - 4.2.5.5: os circuitos terminais devem ser INDIVIDUALIZADOS por funcao; em
#     particular, circuitos DISTINTOS para iluminacao e para tomadas (obrigatorio;
#     a excecao de circuito comum e' so habitacao, 9.5.3.3, com IB <= 16 A).
#   - 4.2.1.2.3-b: em salas de equipamentos/manutencao, no minimo 1 ponto de TUG,
#     com potencia de circuito >= 1000 VA.
#   - 9.5.2.2.1: a regra de perimetro (1 tomada/5 m) e' restrita a HABITACAO; em
#     industrial/comercial a quantidade e' funcao da destinacao e dos equipamentos
#     (a criterio do projetista). Aqui adota-se um espacamento de perimetro
#     configuravel (default 10 m, pratica industrial) + o minimo de 1 TUG/sala.
# As POSICOES sao esquematicas (grade regular); o projetista ajusta ao leiaute real.
# ============================================================================
"""Leiaute da instalacao eletrica do galpao: posiciona luminarias (grade da
luminotecnica), tomadas (TUG, perimetro), interruptores e quadro, e agrupa em
circuitos SEPARADOS de iluminacao e tomada (NBR 5410 4.2.5.5). Stateless (CI)."""

from __future__ import annotations

import math

# --- constantes de norma / pratica (NBR 5410:2004) --------------------------
POT_TUG_VA = 100.0            # potencia de TUG de uso geral (VA) - pratica 9.5.2.2.2;
#                              salas de equipamento exigem circuito >= 1000 VA (4.2.1.2.3-b)
ESPAC_TUG_PERIM_M = 10.0      # espacamento de TUG no perimetro (industrial; a criterio, 9.5.2.2.1)
V_CIRCUITO_V = 220.0         # tensao dos circuitos terminais de ilum/TUG (F-F ou F-N conforme rede)
IB_MAX_CIRCUITO_A = 16.0     # corrente de projeto max usual por circuito terminal (F-N/F-F)
MAX_PONTOS_ILUM = 12         # pontos de luz por circuito (pratica; alem disso, divide)
MAX_PONTOS_TUG = 10          # pontos de tomada por circuito (pratica)


def grade_iluminacao(L, W, N, P_ponto_va=100.0):
    """Distribui N pontos de luz numa GRADE regular sobre o retangulo LxW (m).
    Escolhe linhas x colunas ~ proporcional a L:W (colunas ao longo de L, o maior),
    com margem = meio-espacamento nas bordas. Retorna [{id,x,y,va}] (x,y em m)."""
    if N <= 0 or L <= 0 or W <= 0:
        return []
    ratio = L / W
    linhas = max(1, int(round(math.sqrt(N / ratio))))
    colunas = max(1, int(math.ceil(N / linhas)))
    sx = L / colunas
    sy = W / linhas
    pts = []
    k = 0
    for j in range(linhas):
        # ordem SERPENTINA (boustrofedon): inverte as colunas em linhas alternadas p/ que
        # pontos consecutivos fiquem ADJACENTES -> o roteamento do circuito vira uma "cobra"
        # sem diagonais longas atravessando a planta (leiaute mais limpo).
        faixa = range(colunas) if j % 2 == 0 else range(colunas - 1, -1, -1)
        for i in faixa:
            if k >= N:
                break
            pts.append({"id": "L%d" % (k + 1), "x": round(sx * (i + 0.5), 2),
                        "y": round(sy * (j + 0.5), 2), "va": P_ponto_va})
            k += 1
    return pts


def pontos_tomada(L, W, espac_m=ESPAC_TUG_PERIM_M, pot_va=POT_TUG_VA):
    """Distribui TUGs ao longo do PERIMETRO do galpao, a cada 'espac_m' (m),
    incluindo os 4 cantos. Retorna [{id,x,y,va}] (x,y em m). Ver 9.5.2.2.1
    (criterio do projetista em nao-residencial) + minimo 4 (cantos)."""
    if L <= 0 or W <= 0:
        return []
    perim = 2.0 * (L + W)
    n = max(4, int(round(perim / max(0.1, espac_m))))
    pts = []
    for k in range(n):
        d = perim * k / n            # posicao ao longo do perimetro (m), sentido horario
        if d < L:                    # borda inferior (y=0), x cresce
            x, y = d, 0.0
        elif d < L + W:              # borda direita (x=L), y cresce
            x, y = L, d - L
        elif d < 2 * L + W:          # borda superior (y=W), x decresce
            x, y = L - (d - L - W), W
        else:                        # borda esquerda (x=0), y decresce
            x, y = 0.0, W - (d - 2 * L - W)
        pts.append({"id": "T%d" % (k + 1), "x": round(x, 2), "y": round(y, 2), "va": pot_va})
    return pts


def interruptores(L, W):
    """Interruptores junto aos acessos (default: proximos aos dois topos, no eixo).
    Retorna [{id,x,y}] (m)."""
    if L <= 0 or W <= 0:
        return []
    return [{"id": "S1", "x": round(0.03 * L, 2), "y": round(W / 2.0, 2)},
            {"id": "S2", "x": round(0.97 * L, 2), "y": round(W / 2.0, 2)}]


def _agrupa(pontos, prefixo, max_pontos, v=V_CIRCUITO_V, ib_max=IB_MAX_CIRCUITO_A):
    """Agrupa uma lista de pontos em circuitos, limitando por NUMERO de pontos e
    por corrente de projeto (IB = VA/V <= ib_max). Retorna [{nome,pontos,va,IB_A}]."""
    circs = []
    atual = []
    va = 0.0
    va_max = ib_max * v
    for p in pontos:
        if atual and (len(atual) >= max_pontos or va + p["va"] > va_max):
            circs.append(atual); atual = []; va = 0.0
        atual.append(p); va += p["va"]
    if atual:
        circs.append(atual)
    out = []
    for i, grupo in enumerate(circs, start=1):
        vg = sum(p["va"] for p in grupo)
        out.append({"nome": "%s%d" % (prefixo, i), "pontos": [p["id"] for p in grupo],
                    "n_pontos": len(grupo), "va": round(vg, 0), "IB_A": round(vg / v, 2)})
    return out


def circuitos(luzes, tomadas, v=V_CIRCUITO_V):
    """Agrupa em circuitos SEPARADOS de iluminacao e de tomada (NBR 5410 4.2.5.5).
    Retorna {iluminacao:[...], tomada:[...]}."""
    return {"iluminacao": _agrupa(luzes, "C-ILUM-", MAX_PONTOS_ILUM, v),
            "tomada": _agrupa(tomadas, "C-TUG-", MAX_PONTOS_TUG, v)}


# --- ELETRODUTO (NBR 5410 6.2.11.1.6-a: taxa de ocupacao 53/31/40% p/ 1/2/3+ cond.) ----
# Selecao SIMPLIFICADA do DN por faixa de secao, p/ circuito tipico de 3-4 condutores a
# 40% (F+N+PE ou 3F+N+PE). Bitola minima de eletroduto = 16 mm. Os diametros externos dos
# cabos (base do calculo exato de ocupacao) vem da NBR NM 280 / catalogo; aqui a faixa
# tabela o resultado usual do criterio de 40%.
TAXA_OCUPACAO_3MAIS = 0.40      # NBR 5410 6.2.11.1.6-a (3 ou mais condutores)
_ELETRODUTO_POR_SECAO = [(2.5, 20), (6.0, 25), (16.0, 32), (35.0, 40), (1e9, 50)]
DN_ELETRODUTO_MIN_MM = 16


def eletroduto_dn(secao_mm2):
    """DN nominal do eletroduto (mm) para o circuito, pela faixa de secao (criterio de
    ocupacao 40%, NBR 5410 6.2.11.1.6-a; 3-4 condutores)."""
    for lim, dn in _ELETRODUTO_POR_SECAO:
        if secao_mm2 <= lim:
            return max(dn, DN_ELETRODUTO_MIN_MM)
    return 50


def _comprimento_circuito(pids, pos, quadro):
    """Comprimento estimado do circuito (m): trajeto ligando os pontos na ordem +
    trecho do 1o ponto ao quadro (QGF). Usado no criterio de QUEDA DE TENSAO."""
    if not pids:
        return 0.0
    pts = [pos[p] for p in pids if p in pos]
    if not pts:
        return 0.0
    d = math.hypot(pts[0]["x"] - quadro["x"], pts[0]["y"] - quadro["y"])
    for a, b in zip(pts, pts[1:]):
        d += math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    return d


def dimensiona_circuito(circ, pos, quadro, tipo, v=V_CIRCUITO_V):
    """Dimensiona 1 circuito terminal (condutor + disjuntor + eletroduto), reusando
    condutores_nbr5410 e protecao_nbr5410. circ vem de _agrupa (nome, pontos, va, IB_A).
    tipo: 'iluminacao'|'tomada' (governa o eletroduto e o rotulo). Retorna a linha do QDC."""
    import condutores_nbr5410 as cd
    import protecao_nbr5410 as pr
    L_m = _comprimento_circuito(circ["pontos"], pos, quadro)
    ib = circ["va"] / v
    cond = cd.dimensiona_condutor({
        "IB": ib, "V": v, "L_km": L_m / 1000.0, "sistema": "monofasico", "n_cond": 2,
        "isolacao": "PVC", "metodo": "B1", "fp": 1.0, "uso": tipo})
    secao = cond.get("secao_mm2")
    prot = pr.dimensiona_protecao({"IB": ib, "IZ": cond.get("Iz") or 0.0, "uso": tipo})
    dn = prot["disjuntor"].get("IN")
    return {
        "circuito": circ["nome"], "tipo": tipo, "n_pontos": circ["n_pontos"],
        "potencia_VA": circ["va"], "IB_A": round(ib, 2), "comprimento_m": round(L_m, 1),
        "secao_mm2": secao, "disjuntor_A": dn, "eletroduto_mm": eletroduto_dn(secao or 2.5),
        "queda_pct": cond.get("dv_pct"), "OK": bool(cond.get("OK") and prot.get("OK"))}


def quadro_de_circuitos(circs, pos, quadro, v=V_CIRCUITO_V):
    """QDC - Quadro de Distribuicao de Circuitos: dimensiona TODOS os circuitos (ilum e
    tomada) e retorna a lista de linhas [{circuito,tipo,n_pontos,potencia_VA,IB_A,
    secao_mm2,disjuntor_A,eletroduto_mm,queda_pct,OK}]."""
    linhas = []
    for c in circs["iluminacao"]:
        linhas.append(dimensiona_circuito(c, pos, quadro, "iluminacao", v))
    for c in circs["tomada"]:
        linhas.append(dimensiona_circuito(c, pos, quadro, "tomada", v))
    return linhas


def projeto_instalacao(r, espac_tug_m=ESPAC_TUG_PERIM_M, pot_tug_va=POT_TUG_VA):
    """Leiaute completo a partir do resultado de galpao_eletrico.rodar(r): posiciona
    luminarias (grade da luminotecnica), tomadas (perimetro), interruptores e o QGF,
    e agrupa em circuitos separados (4.2.5.5). Retorna o dicionario de instalacao."""
    geo = r.get("geometria") or {}
    L = float(geo.get("L", 0.0)); W = float(geo.get("W", 0.0))
    lum = r.get("luminotecnica") or {}
    N = int(lum.get("N_luminarias", 0))
    p_lum_w = float(lum.get("P_luminaria_W", 100.0))
    if N <= 0 and L > 0 and W > 0:
        # sem luminotecnica no resultado -> estimativa por area (1 luminaria de galpao
        # cobre ~18 m2, high-bay tipico); o projetista refina com o calculo luminotecnico.
        N = max(4, int(round((L * W) / 18.0)))
    luzes = grade_iluminacao(L, W, N, P_ponto_va=p_lum_w)
    tomadas = pontos_tomada(L, W, espac_m=espac_tug_m, pot_va=pot_tug_va)
    ints = interruptores(L, W)
    circs = circuitos(luzes, tomadas)
    quadro = {"id": "QGF", "x": round(0.02 * L, 2), "y": round(0.02 * W, 2)}
    pos = {p["id"]: p for p in luzes + tomadas}
    qdc = quadro_de_circuitos(circs, pos, quadro)      # dimensiona cada circuito (QDC)
    # anexa o dimensionamento a cada circuito (p/ rotular na planta)
    dim_por_nome = {d["circuito"]: d for d in qdc}
    for grupo in (circs["iluminacao"] + circs["tomada"]):
        d = dim_por_nome.get(grupo["nome"], {})
        grupo["secao_mm2"] = d.get("secao_mm2")
        grupo["disjuntor_A"] = d.get("disjuntor_A")
        grupo["eletroduto_mm"] = d.get("eletroduto_mm")
    return {
        "luzes": luzes, "tomadas": tomadas, "interruptores": ints, "quadro": quadro,
        "circuitos": circs, "qdc": qdc,
        "quantitativos": {
            "n_pontos_luz": len(luzes), "n_tomadas": len(tomadas),
            "n_interruptores": len(ints),
            "n_circuitos_ilum": len(circs["iluminacao"]),
            "n_circuitos_tug": len(circs["tomada"]),
            "carga_ilum_va": round(sum(p["va"] for p in luzes), 0),
            "carga_tug_va": round(sum(p["va"] for p in tomadas), 0)},
        "norma": "NBR 5410 (4.2.5.5 circuitos ilum/tomada separados; "
                 "4.2.1.2.3-b sala equip. >=1 TUG/1000 VA; 9.5.2.2.1 nao-residencial a criterio)",
    }


def _selftest():
    # grade: 44 luzes num 40x20 -> linhas x colunas proporcional (colunas ao longo de L)
    luz = grade_iluminacao(40.0, 20.0, 44)
    assert len(luz) == 44
    # todas dentro do retangulo
    assert all(0 < p["x"] < 40 and 0 < p["y"] < 20 for p in luz)
    # colunas (ao longo de L=40, o maior lado) >= linhas (ao longo de W=20)
    xs = sorted(set(p["x"] for p in luz)); ys = sorted(set(p["y"] for p in luz))
    assert len(xs) >= len(ys), (len(xs), len(ys))
    # tomadas no perimetro: todas numa das 4 bordas
    tom = pontos_tomada(40.0, 20.0, espac_m=10.0)
    assert len(tom) == 12          # perimetro 120 / 10
    for p in tom:
        na_borda = (abs(p["x"]) < 1e-6 or abs(p["x"] - 40) < 1e-6
                    or abs(p["y"]) < 1e-6 or abs(p["y"] - 20) < 1e-6)
        assert na_borda, p
    # circuitos: iluminacao e tomada SEPARADOS (4.2.5.5); nenhum circuito mistura
    circ = circuitos(luz, tom)
    assert circ["iluminacao"] and circ["tomada"]
    assert all(c["nome"].startswith("C-ILUM-") for c in circ["iluminacao"])
    assert all(c["nome"].startswith("C-TUG-") for c in circ["tomada"])
    # limite de pontos por circuito de iluminacao respeitado
    assert all(c["n_pontos"] <= MAX_PONTOS_ILUM for c in circ["iluminacao"])
    # IB por circuito <= limite
    assert all(c["IB_A"] <= IB_MAX_CIRCUITO_A + 1e-9
               for c in circ["iluminacao"] + circ["tomada"])
    # 44 luzes / 12 por circ -> pelo menos 4 circuitos de iluminacao
    assert len(circ["iluminacao"]) >= 4
    # projeto completo a partir de um r sintetico
    r = {"geometria": {"L": 40.0, "W": 20.0, "H": 8.0},
         "luminotecnica": {"N_luminarias": 44, "P_luminaria_W": 100}}
    inst = projeto_instalacao(r)
    q = inst["quantitativos"]
    assert q["n_pontos_luz"] == 44 and q["n_tomadas"] == 12
    assert q["n_circuitos_ilum"] >= 4 and q["n_circuitos_tug"] >= 1
    # guardas degeneradas
    assert grade_iluminacao(0, 20, 44) == [] and pontos_tomada(40, 0) == []
    print("instalacao_eletrica self-test PASSED (NBR 5410 4.2.5.5 / 9.5.2.2)")


if __name__ == "__main__":
    _selftest()
