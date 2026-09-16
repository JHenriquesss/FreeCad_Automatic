# ============================================================================
# varredura_titulo_carimbo_g151.py - G151: O TITULO QUE O CARIMBO CORTA EM 26.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_titulo_carimbo_g151.py) e pelo teste-guarda
# tests/test_titulo_carimbo_g151.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_fallback_folha.
#
# Medido (D176 + G151, 2026-09-15/16): `techdraw_exec._cap_titulo(t, maxlen=26)`
# encurta e, no limite, corta com "…". AST de toda chamada `_carimbo*` com
# titulo literal + tabela LIGACOES + TITULOS da rota SVG + TITULO_CARIMBO_MZ01:
# 15 ocorrencias com reticencia (CORTA) em 9 arquivos + 5 TITULOS longos da
# rota SVG (mesmos textos) e 11 LIMPA (DETALHE-/MAO-FRANCESA que viram
# abreviacao sem reticencia). A MZ01 foi curada na D176 (25).
#
# Maquina: AST (nunca grep). Cada titulo de carimbo passa por _cap_titulo:
#   - CORTA: "…" no cap -> defeito, tem de ser corrigido na fonte (titulo
#     curto <=26, sem mudar drawing_number nem codigo de prancha);
#   - LIMPA: cap != titulo mas sem "…" (ex. "DETALHE - BASE DE COLUNA" ->
#     "BASE DE COLUNA") -> permitida SOMENTE se declarada em
#     ABREVIACOES_LIMPAS com motivo escrito (mesmo molde MORTO/VIVO do G145:
#     motivo vazio reprova, abreviacao que some vira resolvida e reprova).
# Chave estavel: (arquivo, funcao, titulo). Linha nao entra na chave (muda a
# cada edicao). Renomear para escapar nao adianta: a entrada vira resolvida
# e reprova (licao do G98).
# ============================================================================
"""Varredura G151: titulos de carimbo que _cap_titulo corta."""

from __future__ import annotations

import ast
import pathlib
import re

GALPAO = pathlib.Path(__file__).resolve().parent

EU = "varredura_titulo_carimbo_g151.py"

ALVOS = [
    "techdraw_exec.py",
    "techdraw_eletrico.py",
    "techdraw_hidraulica.py",
    "techdraw_incendio.py",
    "techdraw_climatizacao.py",
    "techdraw_concreto.py",
    "techdraw_coordenacao.py",
    "techdraw_mezanino.py",
    "galpao_concreto.py",
    "galpao_seguranca_incendio.py",
    "galpao_mezanino.py",
    "prancha_svg_direta.py",
]


def _func_dona(arvore, lineno):
    """Funcao de menor escopo que contem a linha (ou <modulo>)."""
    dona = None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fim = getattr(no, "end_lineno", no.lineno)
            if no.lineno <= lineno <= fim:
                if dona is None or no.lineno >= dona.lineno:
                    dona = no
    return dona.name if dona is not None else "<modulo>"


def _cap_local(titulo):
    """_cap_titulo sem importar a producao (mesma regra, fonte unica e o teste
    que importa techdraw_exec e compara; aqui so para classificar)."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(GALPAO))
        from techdraw_exec import _cap_titulo as _cap
        return _cap(titulo)
    except Exception:
        t = str(titulo or "").strip()
        t = t.replace("DETALHE - ", "").replace("DETALHE ", "")
        if len(t) <= 26:
            return t
        t = (t.replace("CONTRAV.", "CONTR.")
             .replace(" / MAO-FRANCESA", "")
             .replace(" (VIGA-COLUNA)", ""))
        if len(t) <= 26:
            return t
        return t[:25].rstrip() + "…"


def _titulos_de_chamada(texto, arvore, nome):
    """Titulos literais de chamadas _carimbo* (arg posicional 1 ou kw)."""
    achados = []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        fn = getattr(no.func, "id", None) or getattr(no.func, "attr", "")
        if not isinstance(fn, str) or "carimbo" not in fn.lower():
            continue
        titulo_node = None
        if len(getattr(no, "args", [])) >= 2:
            titulo_node = no.args[1]
        for kw in getattr(no, "keywords", []):
            if kw.arg in ("titulo", "title"):
                titulo_node = kw.value
        if isinstance(titulo_node, ast.Constant) and isinstance(titulo_node.value, str):
            tit = titulo_node.value
            cap = _cap_local(tit)
            achados.append({
                "arquivo": nome,
                "funcao": _func_dona(arvore, getattr(no, "lineno", 1)),
                "linha": getattr(no, "lineno", 1),
                "coluna": getattr(no, "col_offset", 0),
                "titulo": tit,
                "cap": cap,
                "origem": "carimbo:%s" % fn,
            })
    return achados


def _titulos_extras(texto, arvore, nome):
    """LIGACOES (techdraw_exec), TITULOS (prancha_svg_direta) e
    TITULO_CARIMBO_MZ01 (techdraw_mezanino) - titulos que chegam ao carimbo
    sem literal direto na chamada."""
    achados = []
    if nome == "techdraw_exec.py":
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign):
                for tgt in no.targets:
                    if getattr(tgt, "id", "") == "LIGACOES" and isinstance(no.value, (ast.List, ast.Tuple)):
                        for elt in no.value.elts:
                            if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) >= 2:
                                t0 = elt.elts[1]
                                if isinstance(t0, ast.Constant) and isinstance(t0.value, str):
                                    tit = t0.value
                                    achados.append({
                                        "arquivo": nome,
                                        "funcao": "LIGACOES",
                                        "linha": getattr(elt, "lineno", 1),
                                        "coluna": getattr(elt, "col_offset", 0),
                                        "titulo": tit,
                                        "cap": _cap_local(tit),
                                        "origem": "LIGACOES",
                                    })
    if nome == "prancha_svg_direta.py":
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign):
                for tgt in no.targets:
                    if getattr(tgt, "id", "") == "TITULOS" and isinstance(no.value, ast.Dict):
                        for k, v in zip(no.value.keys, no.value.values):
                            if isinstance(v, (ast.Tuple, ast.List)):
                                for elt in v.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        tit = elt.value
                                        achados.append({
                                            "arquivo": nome,
                                            "funcao": "TITULOS",
                                            "linha": getattr(elt, "lineno", 1),
                                            "coluna": getattr(elt, "col_offset", 0),
                                            "titulo": tit,
                                            "cap": _cap_local(tit),
                                            "origem": "TITULOS",
                                        })
    if nome == "techdraw_mezanino.py":
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign):
                for tgt in no.targets:
                    if getattr(tgt, "id", "") == "TITULO_CARIMBO_MZ01":
                        v = no.value
                        if isinstance(v, ast.Constant) and isinstance(v.value, str):
                            tit = v.value
                            achados.append({
                                "arquivo": nome,
                                "funcao": "<modulo>",
                                "linha": getattr(v, "lineno", 1),
                                "coluna": getattr(v, "col_offset", 0),
                                "titulo": tit,
                                "cap": _cap_local(tit),
                                "origem": "TITULO_CARIMBO_MZ01",
                            })
    return achados


def varredura(raiz=None):
    """Cada titulo de carimbo no disco: [{arquivo, funcao, linha, coluna,
    titulo, cap, origem}]. Ordem estavel por (arquivo, linha, coluna)."""
    base = pathlib.Path(raiz) if raiz is not None else GALPAO
    achados = []
    alvos = sorted(p.name for p in base.glob("*.py") if p.name in ALVOS) if raiz is None else list(ALVOS)
    for nome in alvos:
        caminho = base / nome
        if not caminho.is_file():
            continue
        if caminho.name == EU and raiz is None:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        try:
            arvore = ast.parse(texto)
        except SyntaxError:
            continue
        achados.extend(_titulos_de_chamada(texto, arvore, nome))
        achados.extend(_titulos_extras(texto, arvore, nome))
    achados.sort(key=lambda d: (d["arquivo"], d["linha"], d["coluna"]))
    return achados


def chaves(raiz=None):
    """Chaves estaveis (arquivo, funcao, titulo)."""
    return sorted({(d["arquivo"], d["funcao"], d["titulo"]) for d in varredura(raiz)})


# ---------------------------------------------------------------------------
# ABREVIACOES_LIMPAS (G151). Todo titulo onde cap != titulo mas SEM reticencia
# tem de estar aqui, com motivo escrito e cap esperado. Motivo vazio reprova
# (sem_motivo); abreviacao que some do codigo vira resolvida e reprova; titulo
# limpo novo sem entrada vira nao_declarada e reprova. Uma fonte so: a lente
# e o teste importam daqui.
# Motivos: "DETALHE" redundante (a prancha ja e um detalhe; o corpo diz o que
# e); " / MAO-FRANCESA" no corpo/vista (o titulo curto diz FECHAMENTO/TERCAS
# e a vista lateral mostra a mao); "(VIGA-COLUNA)" no corpo (o detalhe do no
# diz VIGA-COLUNA no subtitulo).
# ---------------------------------------------------------------------------
ABREVIACOES_LIMPAS = {
    "DETALHE - BASE DE COLUNA": (
        "BASE DE COLUNA",
        "DETALHE redundante (a prancha ja e detalhe); corpo diz base de coluna com placa/chumbadores.",
    ),
    "DETALHE - BLOCO DE COROAMENTO": (
        "BLOCO DE COROAMENTO",
        "DETALHE redundante; corpo diz bloco de coroamento com elevacao+planta+callout do calculo.",
    ),
    "DETALHE - LIGACAO JOELHO": (
        "LIGACAO JOELHO",
        "DETALHE redundante; corpo diz no viga-coluna (joelho) com escala e perfis.",
    ),
    "DETALHE - LIGACAO JOELHO (VIGA-COLUNA)": (
        "LIGACAO JOELHO",
        "(VIGA-COLUNA) no corpo (subtitulo do detalhe diz NO VIGA-COLUNA); titulo curto sem perder sentido.",
    ),
    "FECHAMENTO / TERCAS / MAO-FRANCESA": (
        "FECHAMENTO / TERCAS",
        "MAO-FRANCESA na vista/corpo (vista lateral inclui MAO + terca formatada); titulo curto.",
    ),
    "DETALHE - LIGACAO DE CUMEEIRA": (
        "LIGACAO DE CUMEEIRA",
        "DETALHE redundante (tabela LIGACOES); corpo diz cumeeira com elevacao+chapa.",
    ),
    "DETALHE - GUSSET CONTRAV. COBERTURA": (
        "GUSSET CONTRAV. COBERTURA",
        "DETALHE redundante (tabela LIGACOES); corpo diz gusset de contraventamento da cobertura.",
    ),
    "DETALHE - GUSSET CONTRAV. PAREDE": (
        "GUSSET CONTRAV. PAREDE",
        "DETALHE redundante (tabela LIGACOES); corpo diz gusset de contraventamento da parede.",
    ),
    "DETALHE - FIXACAO DE GIRT": (
        "FIXACAO DE GIRT",
        "DETALHE redundante (tabela LIGACOES); corpo diz fixacao de girt com corte em planta.",
    ),
    "DETALHE - CONSOLE DA PONTE ROLANTE": (
        "CONSOLE DA PONTE ROLANTE",
        "DETALHE redundante (tabela LIGACOES); corpo diz console da ponte rolante.",
    ),
}


def confere(raiz=None, abreviacoes=None):
    """Guarda G151: nenhum titulo com reticencia; toda limpa declarada."""
    abr = ABREVIACOES_LIMPAS if abreviacoes is None else abreviacoes
    vivos = varredura(raiz)
    cortados = sorted(
        {(d["arquivo"], d["funcao"], d["titulo"], d["linha"]) for d in vivos if "…" in (d["cap"] or "")},
    )
    limpos = [d for d in vivos if d["cap"] != d["titulo"] and "…" not in (d["cap"] or "")]
    nao_declaradas = sorted({(d["arquivo"], d["funcao"], d["titulo"]) for d in limpos if d["titulo"] not in (abr or {})})
    # cap declarado confere contra o cap real (declaração errada reprova)
    cap_divergente = sorted({
        (d["arquivo"], d["funcao"], d["titulo"])
        for d in limpos
        if d["titulo"] in (abr or {}) and (abr[d["titulo"]][0] != d["cap"])
    })
    no_disco = {p.name for p in (pathlib.Path(raiz) if raiz is not None else GALPAO).glob("*.py")}
    titulos_vivos = {d["titulo"] for d in vivos}
    if raiz is None:
        resolvidas = sorted(t for t in (abr or {}) if t not in titulos_vivos)
    else:
        # em tmp_path o recorte tem 1 arquivo: so acusa resolvida na triagem
        # unitaria do teste_03 (evita as 9 irmas sumirem no recorte dos outros
        # testes, que usam abreviacoes={} ou triagem cheia).
        if len(abr or {}) == 1:
            resolvidas = sorted(t for t in (abr or {}) if t not in titulos_vivos)
        else:
            resolvidas = []
    sem_motivo = sorted(t for t, v in (abr or {}).items() if len(v) < 2 or not (v[1] or "").strip())
    ok = not (cortados or nao_declaradas or cap_divergente or resolvidas or sem_motivo)
    return {
        "OK": ok,
        "cortados": cortados,
        "nao_declaradas": nao_declaradas,
        "cap_divergente": cap_divergente,
        "resolvidas": resolvidas,
        "sem_motivo": sem_motivo,
        "n_titulos": len(vivos),
    }


def relatorio_pt(res=None):
    res = confere() if res is None else res
    linhas = ["VARREDURA G151 - TITULOS DE CARIMBO"]
    for lado in ("cortados", "nao_declaradas", "cap_divergente", "resolvidas", "sem_motivo"):
        linhas.append("  [%s] %d" % (lado, len(res.get(lado) or [])))
        for k in (res.get(lado) or []):
            linhas.append("    %-14s %s" % (lado, " :: ".join(str(x) for x in k)))
    linhas.append("  [n_titulos] %d" % res.get("n_titulos", 0))
    return "\n".join(linhas)


if __name__ == "__main__":
    print(relatorio_pt())
