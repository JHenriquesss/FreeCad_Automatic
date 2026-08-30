# ============================================================================
# cronograma.py - O QUE ESTE SCRIPT FAZ / CALCULA
# CRONOGRAMA FISICO-FINANCEIRO (a dimensao 4D + a curva de desembolso). Amarra as
# atividades da obra (fundacao, estrutura, cobertura, instalacoes, acabamento,
# montagem) a um CALENDARIO e a um CUSTO, produzindo:
#   - REDE CPM (Critical Path Method): forward pass (early start/finish) a partir das
#     precedencias; duracao total e CAMINHO CRITICO (folga zero via backward pass).
#   - CURVA S fisico-financeira: avanco fisico ACUMULADO (%) e desembolso ACUMULADO
#     (R$) ao longo do tempo, distribuindo cada atividade LINEARMENTE no seu periodo.
#     O peso fisico de cada atividade e' o seu CUSTO (avanco medido por valor - a
#     convencao de curva S de obra).
# E' algoritmo puro (grafo/CPM). Duracoes e custos das atividades vem do
# planejamento/orcamento (o custo pode sair do modulo orcamento). STATELESS.
# Unidades: dias, R$. As atividades default sao um ESQUELETO de galpao (ajustavel).
# ============================================================================
"""Cronograma fisico-financeiro 4D: rede CPM (caminho critico) + curva S
(avanco fisico e desembolso acumulados). STATELESS."""

from __future__ import annotations

# WBS-esqueleto tipico de um galpao (peso = fracao do custo; duracao em dias).
# Serve de default; o usuario passa a lista real (com custos do orcamento).
_WBS_GALPAO = [
    {"id": "serv", "nome": "Servicos preliminares/canteiro", "dur": 10, "pred": []},
    {"id": "terra", "nome": "Terraplenagem", "dur": 8, "pred": ["serv"]},
    {"id": "fund", "nome": "Fundacoes", "dur": 15, "pred": ["terra"]},
    {"id": "estr", "nome": "Estrutura (montagem)", "dur": 25, "pred": ["fund"]},
    {"id": "cob", "nome": "Cobertura/fechamento", "dur": 15, "pred": ["estr"]},
    {"id": "piso", "nome": "Piso industrial", "dur": 12, "pred": ["estr"]},
    {"id": "inst", "nome": "Instalacoes (elet/hidr/incendio)", "dur": 20, "pred": ["cob"]},
    {"id": "acab", "nome": "Acabamento/limpeza", "dur": 10, "pred": ["inst", "piso"]},
]


def _topo_ordem(atividades):
    """Ordem topologica (Kahn) das atividades por precedencia. Levanta em ciclo."""
    ids = [a["id"] for a in atividades]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de atividade duplicados")
    idset = set(ids)
    for a in atividades:
        for p in a.get("pred", []):
            if p not in idset:
                raise ValueError("precedencia inexistente: %r em %r" % (p, a["id"]))
    grau = {a["id"]: len(a.get("pred", [])) for a in atividades}
    sucessores = {i: [] for i in ids}
    for a in atividades:
        for p in a.get("pred", []):
            sucessores[p].append(a["id"])
    fila = [i for i in ids if grau[i] == 0]
    ordem = []
    while fila:
        i = fila.pop(0)
        ordem.append(i)
        for s in sucessores[i]:
            grau[s] -= 1
            if grau[s] == 0:
                fila.append(s)
    if len(ordem) != len(ids):
        raise ValueError("ciclo de precedencia no cronograma")
    return ordem, sucessores


def cronograma(atividades=None):
    """Rede CPM. atividades: lista {id, nome, dur, custo?, pred:[ids]}. Forward pass
    (ES/EF) + backward pass (LS/LF) -> folga e caminho critico. Retorna dict com
    a linha do tempo por atividade, duracao total e o caminho critico."""
    ats = atividades if atividades is not None else _WBS_GALPAO
    ordem, sucessores = _topo_ordem(ats)
    A = {a["id"]: dict(a) for a in ats}
    # forward pass
    ES = {}; EF = {}
    for i in ordem:
        preds = A[i].get("pred", [])
        ES[i] = max([EF[p] for p in preds], default=0)
        EF[i] = ES[i] + A[i]["dur"]
    dur_total = max(EF.values()) if EF else 0
    # backward pass
    LF = {}; LS = {}
    for i in reversed(ordem):
        sucs = sucessores[i]
        LF[i] = min([LS[s] for s in sucs], default=dur_total)
        LS[i] = LF[i] - A[i]["dur"]
    linha = []
    critico = []
    for a in ats:
        i = a["id"]
        folga = LS[i] - ES[i]
        eh_crit = folga == 0
        if eh_crit:
            critico.append(i)
        linha.append({"id": i, "nome": a["nome"], "dur": a["dur"],
                      "custo": a.get("custo", 0.0),
                      "inicio": ES[i], "fim": EF[i], "folga": folga,
                      "critico": eh_crit})
    linha.sort(key=lambda x: (x["inicio"], x["fim"]))
    return {"atividades": linha, "duracao_total_dias": dur_total,
            "caminho_critico": critico,
            "custo_total": round(sum(x["custo"] for x in linha), 2)}


def curva_s(crono, n_periodos=None):
    """Curva S fisico-financeira. Divide a duracao total em periodos (default:
    semanas) e acumula o AVANCO FISICO (ponderado pelo custo) e o DESEMBOLSO,
    distribuindo cada atividade LINEARMENTE entre inicio e fim. Retorna a serie."""
    dur = crono["duracao_total_dias"]
    if dur <= 0:
        return {"periodos": [], "passo_dias": 0}
    passo = 7 if n_periodos is None else max(1, dur / n_periodos)
    custo_total = crono["custo_total"] or 1.0
    # marcos de tempo (fim de cada periodo)
    marcos = []
    t = passo
    while t < dur:
        marcos.append(t); t += passo
    marcos.append(dur)

    def _fracao_realizada(at, t):
        """Fracao [0,1] de uma atividade concluida ate o instante t (linear)."""
        if t <= at["inicio"]:
            return 0.0
        if t >= at["fim"] or at["dur"] == 0:
            return 1.0
        return (t - at["inicio"]) / at["dur"]

    periodos = []
    for t in marcos:
        custo_acum = 0.0
        for at in crono["atividades"]:
            custo_acum += at["custo"] * _fracao_realizada(at, t)
        avanco_fisico = 100.0 * custo_acum / custo_total
        periodos.append({"dia": round(t, 1),
                         "avanco_fisico_pct": round(avanco_fisico, 1),
                         "desembolso_acum": round(custo_acum, 2),
                         "desembolso_pct": round(100.0 * custo_acum / custo_total, 1)})
    return {"periodos": periodos, "passo_dias": passo,
            "custo_total": crono["custo_total"]}


def aplica_custos(atividades, custos_por_id):
    """Anexa custos (R$) as atividades por id (do orcamento). Ids sem custo ficam 0."""
    out = []
    for a in atividades:
        b = dict(a); b["custo"] = float(custos_por_id.get(a["id"], a.get("custo", 0.0)))
        out.append(b)
    return out


def aviso_custeio(crono):
    """Aviso quando so PARTE das atividades tem custo. A curva S pesa o avanco
    fisico pelo CUSTO: com custo em poucas atividades ela chega a 100% antes do
    fim da obra. Verdade sobre o dinheiro conhecido, MENTIRA sobre o fisico - e
    tem que sair no ARTEFATO que a pessoa le, nao so no manifesto. '' se nao ha."""
    ats = crono.get("atividades", [])
    com = sum(1 for a in ats if a.get("custo"))
    if not ats or com == 0 or com == len(ats):
        return ""
    fim = max((a["fim"] for a in ats if a.get("custo")), default=0)
    return ("ATENCAO - curva S custeada em %d de %d atividades: o avanco e "
            "ponderado pelo custo, entao ela satura em 100%% no dia %d, antes do "
            "fim da obra (dia %d). As atividades sem custo no orcamento nao "
            "aparecem no avanco." % (com, len(ats), fim,
                                     crono.get("duracao_total_dias", 0)))


def relatorio_pt(crono, cs=None):
    """Relatorio-texto do cronograma + curva S."""
    L = ["CRONOGRAMA FISICO-FINANCEIRO (4D)", "=" * 34,
         "Duracao total: %d dias | Caminho critico: %s" %
         (crono["duracao_total_dias"], " -> ".join(crono["caminho_critico"])),
         "-" * 60,
         "%-32s %5s %5s %5s %6s" % ("ATIVIDADE", "INI", "FIM", "FOLGA", "CRIT")]
    for a in crono["atividades"]:
        L.append("%-32.32s %5d %5d %5d %6s" %
                 (a["nome"], a["inicio"], a["fim"], a["folga"],
                  "SIM" if a["critico"] else ""))
    if cs and cs["periodos"]:
        L.append("-" * 60)
        L.append("CURVA S (avanco fisico acumulado):")
        for p in cs["periodos"]:
            barra = "#" * int(p["avanco_fisico_pct"] / 5)
            L.append("  dia %4.0f: %5.1f%% %s" % (p["dia"], p["avanco_fisico_pct"], barra))
        aviso = aviso_custeio(crono)
        if aviso:
            L.append(aviso)
    return "\n".join(L)


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def curva_s_svg(crono, cs=None):
    """Grafico do cronograma: barras de Gantt das atividades (criticas em vermelho)
    + curva S de avanco fisico acumulado. SVG puro, XML-valido (parse)."""
    cs = cs or curva_s(crono)
    W, H = 1000, 620
    dur = crono["duracao_total_dias"] or 1
    ax0, ay0, aw = 340, 90, 600
    ats = crono["atividades"]
    rowh = 30
    gh = rowh * len(ats)

    def _t(x, y, s, size=12, anchor="middle", weight="normal", color="#111"):
        return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}"'
                f' text-anchor="{anchor}" font-weight="{weight}" fill="{color}">'
                f'{_esc(s)}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           _t(W / 2, 40, "CRONOGRAMA FISICO-FINANCEIRO (4D)", 20, weight="bold"),
           _t(W / 2, 64, "Duracao %d dias | caminho critico em vermelho" %
              crono["duracao_total_dias"], 12, color="#555")]
    # Gantt
    for k, a in enumerate(ats):
        y = ay0 + k * rowh
        out.append(_t(ax0 - 12, y + rowh / 2 + 4, a["nome"][:34], 11, anchor="end",
                      color="#333"))
        x = ax0 + aw * a["inicio"] / dur
        w = max(2, aw * a["dur"] / dur)
        cor = "#c0392b" if a["critico"] else "#3498db"
        out.append(f'<rect x="{x:.0f}" y="{y+5:.0f}" width="{w:.0f}" height="{rowh-12}" '
                   f'fill="{cor}" rx="3"/>')
        out.append(_t(x + w + 6, y + rowh / 2 + 4, "%dd" % a["dur"], 10,
                      anchor="start", color="#666"))
    # eixo de tempo
    yaxis = ay0 + gh + 8
    out.append(f'<line x1="{ax0}" y1="{yaxis}" x2="{ax0+aw}" y2="{yaxis}" '
               f'stroke="#111" stroke-width="1"/>')
    # curva S sobre uma faixa abaixo do Gantt
    cy0 = yaxis + 40; ch = H - cy0 - 70
    out.append(f'<rect x="{ax0}" y="{cy0}" width="{aw}" height="{ch}" fill="#fafafa" '
               f'stroke="#ddd"/>')
    out.append(_t(ax0 - 12, cy0 + ch / 2, "avanco", 11, anchor="end", color="#333"))
    pts = []
    for p in cs["periodos"]:
        px = ax0 + aw * p["dia"] / dur
        py = cy0 + ch * (1.0 - p["avanco_fisico_pct"] / 100.0)
        pts.append("%.0f,%.0f" % (px, py))
    if pts:
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#27ae60" '
                   f'stroke-width="2.5"/>')
        for p, xy in zip(cs["periodos"], pts):
            x, y = xy.split(",")
            out.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#27ae60"/>')
    out.append(_t(ax0, cy0 - 8, "CURVA S - avanco fisico acumulado (%)", 12,
                  anchor="start", weight="bold", color="#27ae60"))
    for pc in (0, 50, 100):
        yy = cy0 + ch * (1.0 - pc / 100.0)
        out.append(_t(ax0 + aw + 8, yy + 4, "%d%%" % pc, 10, anchor="start", color="#999"))
    out.append(_t(W / 2, H - 24, "Custo total: R$ %s | passo %.0f dias" %
                  (f"{crono['custo_total']:,.0f}", cs["passo_dias"]), 11, color="#666"))
    aviso = aviso_custeio(crono)
    if aviso:
        out.append(_t(W / 2, H - 8, aviso[:150], 10, color="#c0392b"))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------- selftest --------------------------------
def _selftest():
    # 1) rede simples em serie: A(5)->B(3)->C(2) -> total 10, todos criticos
    ats = [{"id": "A", "nome": "A", "dur": 5, "pred": []},
           {"id": "B", "nome": "B", "dur": 3, "pred": ["A"]},
           {"id": "C", "nome": "C", "dur": 2, "pred": ["B"]}]
    cr = cronograma(ats)
    assert cr["duracao_total_dias"] == 10
    assert cr["caminho_critico"] == ["A", "B", "C"]
    fim = {a["id"]: a["fim"] for a in cr["atividades"]}
    assert fim["A"] == 5 and fim["B"] == 8 and fim["C"] == 10

    # 2) paralelo: A(5); B(2) ambos -> C. Caminho critico A->C; B tem folga 3
    ats2 = [{"id": "A", "nome": "A", "dur": 5, "pred": []},
            {"id": "B", "nome": "B", "dur": 2, "pred": []},
            {"id": "C", "nome": "C", "dur": 4, "pred": ["A", "B"]}]
    cr2 = cronograma(ats2)
    assert cr2["duracao_total_dias"] == 9
    folgas = {a["id"]: a["folga"] for a in cr2["atividades"]}
    assert folgas["A"] == 0 and folgas["C"] == 0 and folgas["B"] == 3

    # 3) ciclo levanta
    try:
        cronograma([{"id": "X", "nome": "X", "dur": 1, "pred": ["Y"]},
                    {"id": "Y", "nome": "Y", "dur": 1, "pred": ["X"]}]); assert False
    except ValueError:
        pass
    # precedencia inexistente levanta
    try:
        cronograma([{"id": "A", "nome": "A", "dur": 1, "pred": ["Z"]}]); assert False
    except ValueError:
        pass

    # 4) curva S: monotona crescente, termina em 100%
    ats3 = aplica_custos(ats, {"A": 500.0, "B": 300.0, "C": 200.0})
    cr3 = cronograma(ats3)
    assert cr3["custo_total"] == 1000.0
    cs = curva_s(cr3)
    pcts = [p["avanco_fisico_pct"] for p in cs["periodos"]]
    assert pcts == sorted(pcts)                      # nao decresce
    assert abs(pcts[-1] - 100.0) < 1e-6              # termina em 100%
    assert abs(cs["periodos"][-1]["desembolso_acum"] - 1000.0) < 1e-6

    # 5) WBS default do galpao roda e tem caminho critico
    crg = cronograma()
    assert crg["duracao_total_dias"] > 0 and crg["caminho_critico"]

    # 6) curva S SVG e' XML valido (parse)
    from xml.dom.minidom import parseString
    svg = curva_s_svg(cr3)
    assert svg.startswith("<svg") and "CURVA S" in svg
    parseString(svg.encode("utf-8"))
    return True


if __name__ == "__main__":
    _selftest()
    custos = {"serv": 30000, "terra": 45000, "fund": 90000, "estr": 400000,
              "cob": 180000, "piso": 116000, "inst": 150000, "acab": 40000}
    cr = cronograma(aplica_custos(_WBS_GALPAO, custos))
    print(relatorio_pt(cr, curva_s(cr)))
    print("selftest OK")
