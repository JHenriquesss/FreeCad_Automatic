# ============================================================================
# compatibilizacao.py - O QUE ESTE SCRIPT FAZ / PRODUZ
# Transforma o CLASH FEDERADO (galpao_turnkey.checa_interferencia_federada) num
# DOCUMENTO DE COORDENACAO com pendencias RASTREAVEIS - o passo que faltava: hoje o
# clash sai como lista/apendice de texto; aqui vira registro formal com ID estavel,
# severidade, status, acao sugerida e disciplina responsavel, exportavel em formato
# BCF-like (BIM Collaboration Format: um "topic" por conflito, com guid/titulo/
# status/prioridade/rotulos/responsavel). Assim a coordenacao vira um ciclo
# fechado (abrir -> analisar -> resolver -> aprovar), nao uma foto.
#   - gerar_pendencias(rep_clash): 1 pendencia por clash, ID CLH-NNN estavel, com
#     severidade (por volume + se e' montagem esperada), status inicial e acao.
#   - matriz_coordenacao(rep): matriz disciplina x disciplina (n de conflitos).
#   - bcf_topics(pendencias): estrutura BCF-like (topics) para intercambio.
# STATELESS: funcoes puras sobre o dict de clash; nenhuma dependencia pesada.
# ============================================================================
"""Relatorio formal de compatibilizacao: clash federado -> pendencias rastreaveis
(BCF-like) com ID/severidade/status/acao/responsavel + matriz de coordenacao."""

from __future__ import annotations

import hashlib

# disciplinas que sao ESTRUTURA (nao se movem; a instalacao e' que se compatibiliza)
_ESTRUTURA = {"concreto", "aco"}
# nome de exibicao
_NOME = {"concreto": "Estrutura de concreto", "aco": "Estrutura metalica",
         "eletrico": "Eletrica", "hidraulica": "Hidraulica",
         "incendio": "Incendio", "climatizacao": "Climatizacao (HVAC)"}

STATUS_ABERTO = "Aberto"
STATUS_APROVADO = "Aprovado"        # montagem intencional (clash esperado)


def _disciplinas_do_par(par):
    """'concretoxeletrico' -> ('concreto','eletrico'). Nomes nao contem 'x'."""
    ps = par.split("x")
    return (ps[0], ps[1]) if len(ps) == 2 else (par, "")


def _severidade(vol_mm3, esperado):
    """Severidade da pendencia. Esperado (montagem) -> Informativa. Senao por volume
    de interpenetracao: >5e6 mm3 (~5 L) Alta ; >5e5 Media ; senao Baixa."""
    if esperado:
        return "Informativa"
    if vol_mm3 > 5e6:
        return "Alta"
    if vol_mm3 > 5e5:
        return "Media"
    return "Baixa"


def _acao_e_responsavel(da, db, esperado):
    """Acao sugerida + disciplina responsavel pela adequacao. Regra de coordenacao:
    a INSTALACAO cede a ESTRUTURA (reposiciona/preve passagem); estrutura so muda em
    ultimo caso. Instalacao x instalacao -> coordenacao (remanejar tracado)."""
    if esperado:
        return ("Nenhuma - contato de montagem intencional (fixacao/aterramento); "
                "verificar apenas a fixacao.", "-")
    da_e = da in _ESTRUTURA; db_e = db in _ESTRUTURA
    if da_e and db_e:
        return ("Conflito estrutura x estrutura - revisar geometria/modelo (nao "
                "deveria ocorrer entre disciplinas).", "coordenacao")
    if da_e ^ db_e:                                 # uma e' estrutura, a outra instalacao
        inst = db if da_e else da
        return ("Reposicionar/remanejar o tracado da %s ou prever passagem "
                "(furacao/embutido) na estrutura, com verificacao estrutural." %
                _NOME.get(inst, inst), inst)
    # ambas instalacoes
    return ("Remanejar o tracado de uma das instalacoes (reservar prumadas/shafts); "
            "definir prioridade em reuniao de coordenacao.", "coordenacao")


def _guid(a, b, tipos):
    """GUID determinístico (estavel entre execucoes) a partir dos elementos."""
    h = hashlib.sha1(("%s|%s|%s" % (a, b, tipos)).encode("utf-8")).hexdigest()
    return "%s-%s-%s-%s-%s" % (h[:8], h[8:12], h[12:16], h[16:20], h[20:32])


def gerar_pendencias(rep_clash, prefixo="CLH"):
    """Uma pendencia rastreavel por clash. rep_clash = saida de
    checa_interferencia_federada. Ordena A REVISAR (por volume desc) antes dos
    esperados; ID CLH-NNN estavel pela ordem. Retorna lista de dicts."""
    clashes = rep_clash.get("clashes", [])
    # a revisar primeiro (por volume desc), depois esperados (por volume desc)
    ordenados = sorted(clashes, key=lambda c: (c.get("esperado", False),
                                               -c.get("vol_mm3", 0)))
    pend = []
    for i, c in enumerate(ordenados, start=1):
        da, db = _disciplinas_do_par(c.get("disciplinas", ""))
        esperado = bool(c.get("esperado"))
        acao, resp = _acao_e_responsavel(da, db, esperado)
        pend.append({
            "id": "%s-%03d" % (prefixo, i),
            "guid": _guid(c.get("a"), c.get("b"), c.get("tipos")),
            "titulo": "Interferencia %s x %s" % (_NOME.get(da, da), _NOME.get(db, db)),
            "disciplina_a": da, "disciplina_b": db,
            "elemento_a": c.get("a"), "elemento_b": c.get("b"),
            "tipos": c.get("tipos"), "volume_mm3": c.get("vol_mm3"),
            "severidade": _severidade(c.get("vol_mm3", 0), esperado),
            "status": STATUS_APROVADO if esperado else STATUS_ABERTO,
            "esperado": esperado,
            "acao_sugerida": acao, "responsavel": resp,
        })
    return pend


def resumo(pendencias):
    """Contagens por status, severidade e par de disciplinas."""
    por_status = {}; por_sev = {}; por_par = {}
    for p in pendencias:
        por_status[p["status"]] = por_status.get(p["status"], 0) + 1
        por_sev[p["severidade"]] = por_sev.get(p["severidade"], 0) + 1
        par = "x".join(sorted((p["disciplina_a"], p["disciplina_b"])))
        por_par[par] = por_par.get(par, 0) + 1
    abertas = sum(1 for p in pendencias if p["status"] == STATUS_ABERTO)
    return {"total": len(pendencias), "abertas": abertas,
            "por_status": por_status, "por_severidade": por_sev, "por_par": por_par}


def matriz_coordenacao(rep_clash):
    """Matriz disciplina x disciplina com o n de conflitos (por_par do clash).
    Retorna {disciplinas:[...ordenadas...], matriz:{da:{db:n}}}."""
    discs = set()
    m = {}
    for par, n in rep_clash.get("por_par", {}).items():
        da, db = _disciplinas_do_par(par)
        discs.add(da); discs.add(db)
        m.setdefault(da, {})[db] = n
        m.setdefault(db, {})[da] = n
    return {"disciplinas": sorted(discs), "matriz": m}


def bcf_topics(pendencias, autor="galpao_turnkey"):
    """Estrutura BCF-like (BIM Collaboration Format) - 1 topic por pendencia, com
    os campos do markup BCF (guid, title, topic_status, priority, labels,
    assigned_to). Serializavel em JSON para intercambio com plataformas BIM."""
    _PRIOR = {"Alta": "High", "Media": "Normal", "Baixa": "Low",
              "Informativa": "Low"}
    topics = []
    for p in pendencias:
        topics.append({
            "guid": p["guid"],
            "title": "%s: %s" % (p["id"], p["titulo"]),
            "topic_type": "Clash",
            "topic_status": "Closed" if p["esperado"] else "Open",
            "priority": _PRIOR.get(p["severidade"], "Normal"),
            "labels": [p["disciplina_a"], p["disciplina_b"], p["severidade"]],
            "assigned_to": p["responsavel"],
            "description": "%s | %s : %s mm3 | Acao: %s" % (
                p["tipos"], "%s x %s" % (p["elemento_a"], p["elemento_b"]),
                p["volume_mm3"], p["acao_sugerida"]),
            "author": autor,
        })
    return {"bcf_version": "2.1-like", "topics": topics, "n": len(topics)}


def relatorio_pt(pendencias, res=None):
    """Relatorio-texto do documento de compatibilizacao."""
    res = res or resumo(pendencias)
    L = ["RELATORIO DE COMPATIBILIZACAO - PENDENCIAS DE COORDENACAO",
         "=" * 58,
         "Total: %d pendencias (%d ABERTAS, %d aprovadas/montagem)" %
         (res["total"], res["abertas"], res["total"] - res["abertas"]),
         "Severidade: " + " ; ".join("%s=%d" % (k, v)
                                     for k, v in sorted(res["por_severidade"].items())),
         "-" * 58]
    for p in pendencias:
        L.append("%-8s [%-11s] %-9s %s" %
                 (p["id"], p["severidade"], p["status"], p["titulo"]))
        L.append("         %s x %s (%s)  vol=%s mm3" %
                 (p["elemento_a"], p["elemento_b"], p["tipos"], p["volume_mm3"]))
        L.append("         -> %s [resp: %s]" % (p["acao_sugerida"], p["responsavel"]))
    if not pendencias:
        L.append("Nenhum conflito no modelo federado.")
    return "\n".join(L)


def _esc(txt):
    return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def matriz_svg(rep_clash, pendencias=None):
    """Matriz de coordenacao disciplina x disciplina (heatmap do n de conflitos) +
    resumo de severidade. SVG puro-Python, XML-valido (parse)."""
    mat = matriz_coordenacao(rep_clash)
    discs = mat["disciplinas"]
    pend = pendencias if pendencias is not None else gerar_pendencias(rep_clash)
    res = resumo(pend)
    n = len(discs)
    cell = 74
    x0, y0 = 240, 130
    W = max(880, x0 + n * cell + 60)
    H = max(520, y0 + n * cell + 190)

    def _t(x, y, s, size=13, anchor="middle", weight="normal", color="#111"):
        return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="Arial" font-size="{size}"'
                f' text-anchor="{anchor}" font-weight="{weight}" fill="{color}">'
                f'{_esc(s)}</text>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Arial">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           _t(W / 2, 46, "MATRIZ DE COMPATIBILIZACAO - CONFLITOS ENTRE DISCIPLINAS",
              20, weight="bold")]
    if n == 0:
        out.append(_t(W / 2, H / 2, "Nenhum conflito no modelo federado.", 15,
                      color="#0a0"))
        out.append("</svg>")
        return "\n".join(out)

    vmax = max((v for row in mat["matriz"].values() for v in row.values()), default=1)
    for j, dj in enumerate(discs):                 # colunas (cabecalho girado)
        cx = x0 + j * cell + cell / 2
        out.append(_t(cx, y0 - 12, _NOME.get(dj, dj)[:12], 11, anchor="middle",
                      color="#333"))
    for i, di in enumerate(discs):                 # linhas
        cy = y0 + i * cell + cell / 2
        out.append(_t(x0 - 12, cy + 4, _NOME.get(di, di)[:16], 11, anchor="end",
                      color="#333"))
        for j, dj in enumerate(discs):
            x = x0 + j * cell; y = y0 + i * cell
            v = mat["matriz"].get(di, {}).get(dj, 0) if di != dj else None
            if v is None:
                fill = "#e8e8e8"                    # diagonal (mesma disciplina)
            elif v == 0:
                fill = "#f4faf4"
            else:
                t = v / vmax
                fill = "#%02x%02x%02x" % (int(220 - 120 * t), int(90 + 40 * (1 - t)),
                                          int(70 + 30 * (1 - t)))
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                       f'fill="{fill}" stroke="#fff" stroke-width="2"/>')
            if v:
                out.append(_t(x + cell / 2, y + cell / 2 + 6, str(v), 20,
                              weight="bold", color="#fff"))

    # resumo por severidade
    ry = y0 + n * cell + 46
    out.append(_t(x0, ry, "PENDENCIAS: %d total ; %d ABERTAS" %
                  (res["total"], res["abertas"]), 14, anchor="start", weight="bold"))
    sev = res["por_severidade"]
    out.append(_t(x0, ry + 28, "Severidade  ->  " + " ; ".join(
        "%s: %d" % (k, sev[k]) for k in ("Alta", "Media", "Baixa", "Informativa")
        if k in sev), 12, anchor="start", color="#333"))
    out.append(_t(x0, ry + 54, "Numero na celula = conflitos entre o par (a instalacao "
                  "cede a estrutura; ver acao por pendencia).", 11, anchor="start",
                  color="#666"))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------- selftest --------------------------------
def _selftest():
    rep = {"por_par": {"concretoxeletrico": 2, "concretoxhidraulica": 1},
           "clashes": [
               {"a": "C-P1E", "b": "E-CALHA", "disciplinas": "concretoxeletrico",
                "tipos": "ColumnxCableCarrier", "vol_mm3": 8.0e6, "esperado": False},
               {"a": "C-V1", "b": "H-TUBO", "disciplinas": "concretoxhidraulica",
                "tipos": "BeamxPipe", "vol_mm3": 6.0e5, "esperado": False},
               {"a": "C-P2D", "b": "E-DESC", "disciplinas": "concretoxeletrico",
                "tipos": "ColumnxCable", "vol_mm3": 3.0e5, "esperado": True}]}
    pend = gerar_pendencias(rep)
    # 3 pendencias, IDs sequenciais estaveis; a revisar antes do esperado
    assert [p["id"] for p in pend] == ["CLH-001", "CLH-002", "CLH-003"]
    assert pend[0]["severidade"] == "Alta" and pend[0]["volume_mm3"] == 8.0e6
    assert pend[1]["severidade"] == "Media"
    # o esperado vem por ultimo, Informativa/Aprovado
    assert pend[2]["esperado"] and pend[2]["status"] == STATUS_APROVADO
    assert pend[2]["severidade"] == "Informativa"
    # responsavel: estrutura x eletrica -> eletrica se adequa
    assert pend[0]["responsavel"] == "eletrico"
    # guid estavel (mesmo input -> mesmo guid)
    assert gerar_pendencias(rep)[0]["guid"] == pend[0]["guid"]

    r = resumo(pend)
    assert r["total"] == 3 and r["abertas"] == 2
    assert r["por_status"][STATUS_ABERTO] == 2 and r["por_status"][STATUS_APROVADO] == 1

    mat = matriz_coordenacao(rep)
    assert mat["matriz"]["concreto"]["eletrico"] == 2
    assert mat["matriz"]["eletrico"]["concreto"] == 2

    bcf = bcf_topics(pend)
    assert bcf["n"] == 3
    assert bcf["topics"][0]["topic_status"] == "Open"
    assert bcf["topics"][0]["priority"] == "High"
    assert bcf["topics"][2]["topic_status"] == "Closed"      # esperado

    # sem conflitos -> lista vazia, relatorio informa
    assert gerar_pendencias({"clashes": []}) == []
    assert "Nenhum conflito" in relatorio_pt([])

    # matriz SVG e' XML valido (parse, nao substring)
    from xml.dom.minidom import parseString
    svg = matriz_svg(rep, pend)
    assert svg.startswith("<svg") and "MATRIZ DE COMPATIBILIZACAO" in svg
    parseString(svg.encode("utf-8"))
    parseString(matriz_svg({"por_par": {}, "clashes": []}).encode("utf-8"))  # vazio
    return True


if __name__ == "__main__":
    _selftest()
    print("selftest OK")
