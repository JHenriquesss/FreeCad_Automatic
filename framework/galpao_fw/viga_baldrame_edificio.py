# ============================================================================
# viga_baldrame_edificio.py - VIGA BALDRAME / AMARRACAO DO EDIFICIO
#
# Fronteira entre a fundacao do edificio e `viga_baldrame.py` (G18).
# O G3/G9 dimensionavam sapata/bloco/estaca mas deixavam a viga que as amarra
# como not_available - num edificio o fechamento do terreo desce pelo baldrame,
# nao pelo pilar. Este modulo LIGA os dois lados; nao inventa metodo novo.
#
#     vaos do grid (vaos_x/vaos_y) + carga da parede
#          -> viga_baldrame.verifica_baldrame / dimensiona_baldrame
#          -> reacoes por linha (viga continua) -> por pilar (soma)
#          -> gate
#
# ASK, DO NOT INVENT. A parede que o baldrame carrega e' ENTRADA DECLARADA
# (parede {tipo, espessura_cm, altura} da Tabela 2 da NBR 6120 ou q_parede
# declarado em kN/m). Sem ela nao ha baldrame - o modulo devolve not_declared
# e o escopo continua not_available. Carga de parede arbitrada e' o erro que
# este framework trata como bug, nao como default.
#
# UMA SECAO PARA A OBRA, UMA GEOMETRIA POR LINHA. A secao (b x h) e' a declarada
# (ou a ADOTADA quando dimensiona_baldrame sobe h para atender flecha Tab 13.3).
# A verificacao usa o MAIOR vao da malha (dimensionamento conservador) e as
# reacoes sao repartidas pilar a pilar via viga continua (nao por metade de vao).
#
# ACAO HORIZONTAL - o que entra e o que NAO entra (G23):
#   ENTRA  N_amarracao = max|V| da fundacao (reacao horizontal da base do
#          envelope ELU, por pilar, repartida em V por prumada). E' a tracao
#          que o baldrame tem de levar (As = Nd/fyd). O valor vem das
#          combinacoes da fundacao (G23: V heterogeneo por pilar quando ha
#          portico heterogeneo, senao uniforme).
#   NAO ENTRA  M (momento fletor na base): ele vai para a sapata/estaca (Parte A
#          ou grupo) e para o travamento da divisa, nao para a flexao do baldrame.
#          O baldrame flexiona sob q_parede, nao sob M_portico.
#
# Unidades: m, kN (fck/fyk em kN/m2). STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Viga baldrame do edificio: fronteira para viga_baldrame.py (G18)."""

from __future__ import annotations

import copy
import math

import viga_baldrame as vb

GAMMA_C_CONC = 25.0

LINHAS_VALIDAS = ("contorno", "todas")


class EntradaBaldrame(ValueError):
    """A entrada declarada nao permite dimensionar o baldrame."""


def declarada(spec_fundacao) -> bool:
    """True se ha o minimo para dimensionar baldrame.

    A pergunta tem UMA resposta aqui, para que o escopo publicado pelo adaptador
    e o calculo nao usem criterios diferentes.
    """
    if not isinstance(spec_fundacao, dict):
        return False
    vb_spec = spec_fundacao.get("viga_baldrame")
    if not isinstance(vb_spec, dict):
        return False
    # precisa pelo menos secao ou parede/q_parede para nao ser placeholder vazio
    return bool(vb_spec)


def _positivo(valor) -> bool:
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _valida(spec_fundacao):
    vb_spec = spec_fundacao.get("viga_baldrame")
    if not isinstance(vb_spec, dict):
        raise EntradaBaldrame("fundacao.viga_baldrame deve ser um objeto")
    erros = []
    for chave in ("b", "h"):
        val = vb_spec.get(chave)
        if val is not None and not _positivo(val):
            erros.append("viga_baldrame.%s deve ser > 0" % chave)
    q = vb_spec.get("q_parede")
    parede = vb_spec.get("parede")
    if q is not None and not isinstance(q, (int, float)):
        erros.append("viga_baldrame.q_parede deve ser numerico (kN/m)")
    elif q is not None and q < 0:
        erros.append("viga_baldrame.q_parede nao pode ser < 0")
    if parede is not None and not isinstance(parede, dict):
        erros.append("viga_baldrame.parede deve ser um objeto")
    if parede is not None:
        for req in ("tipo", "espessura_cm", "altura"):
            if req not in parede:
                erros.append("viga_baldrame.parede precisa de '%s'" % req)
    if q is None and parede is None:
        erros.append("viga_baldrame precisa de 'q_parede' (kN/m) ou 'parede' "
                     "(tipo/espessura_cm/altura, Tabela 2 da NBR 6120)")
    linhas = vb_spec.get("linhas")
    if linhas is not None and linhas not in LINHAS_VALIDAS:
        erros.append("viga_baldrame.linhas invalido: %r (use %s)" % (linhas, ", ".join(LINHAS_VALIDAS)))
    cont = vb_spec.get("continuidade")
    if cont is not None and cont not in ("simples", "continua"):
        erros.append("viga_baldrame.continuidade deve ser 'simples' ou 'continua'")
    if erros:
        raise EntradaBaldrame("; ".join(erros))


def _q_parede(spec_vb) -> tuple[float, str]:
    """Carga linear da parede (kN/m) e proveniencia."""
    if spec_vb.get("q_parede") is not None:
        return float(spec_vb["q_parede"]), "declarada em viga_baldrame.q_parede"
    parede = spec_vb.get("parede") or {}
    import cargas_nbr6120 as cg
    try:
        q = cg.carga_linear_parede(
            parede["tipo"], parede["espessura_cm"], parede["altura"],
            parede.get("revestimento_cm", 1.0))
    except Exception as exc:  # noqa: BLE001
        raise EntradaBaldrame("viga_baldrame.parede invalida: %s" % exc) from exc
    return float(q), ("Tabela 2 da NBR 6120: %s e=%s cm, h=%.2f m"
                      % (parede["tipo"], parede["espessura_cm"], float(parede["altura"])))


def linhas_de_baldrame(vaos_x, vaos_y, modo):
    """Linhas da malha que recebem baldrame."""
    if modo not in LINHAS_VALIDAS:
        raise EntradaBaldrame("viga_baldrame.linhas invalido: %r" % modo)
    nx, ny = len(vaos_x), len(vaos_y)
    linhas = []
    for j in range(ny + 1):
        if modo == "todas" or j in (0, ny):
            linhas.append(("BX-%d" % j, "x", j, list(vaos_x)))
    for i in range(nx + 1):
        if modo == "todas" or i in (0, nx):
            linhas.append(("BY-%d" % i, "y", i, list(vaos_y)))
    return linhas


def _n_amarracao_max(fundacao) -> float:
    """Maior |V| entre as combinacoes de todos os pilares (tracao de amarracao)."""
    if not isinstance(fundacao, dict):
        return 0.0
    por_pilar = fundacao.get("por_pilar") or {}
    vmax = 0.0
    for reg in por_pilar.values():
        for comb in reg.get("combinacoes") or []:
            v = abs(float(comb.get("V_kN") or 0.0))
            if v > vmax:
                vmax = v
    return vmax


def dimensiona(spec_fundacao, contexto):
    """Dimensiona o baldrame do edificio.

    spec_fundacao: secao `estrutura.fundacao` do spec (contem viga_baldrame).
    contexto: {vaos_x, vaos_y, eixos_x, eixos_y, pilares, fundacao,
               materiais {fck, fyk}, estabilidade, momentos_base} - fundacao traz
               as combinacoes com V para N_amarracao (G23).

    Retorna dict com gate, por_linha, por_pilar, verificacao, etc.
    Levanta EntradaBaldrame quando a entrada declarada nao permite dimensionar.
    """
    _valida(spec_fundacao)
    vb_spec = spec_fundacao["viga_baldrame"]
    vaos_x = contexto.get("vaos_x") or contexto.get("geometria", {}).get("vaos_x")
    vaos_y = contexto.get("vaos_y") or contexto.get("geometria", {}).get("vaos_y")
    if vaos_x is None or vaos_y is None:
        # tenta extrair de vaos nos pilares/eixos
        raise EntradaBaldrame("contexto sem vaos_x/vaos_y para o baldrame")
    # fallback: usa eixos para derivar vaos se nao vier direto
    if not isinstance(vaos_x, list) or not isinstance(vaos_y, list):
        raise EntradaBaldrame("vaos_x/vaos_y devem ser listas de vaos")

    b = float(vb_spec.get("b", 0.20))
    h0 = float(vb_spec.get("h", 0.40))
    modo = vb_spec.get("linhas", "contorno")
    linhas = linhas_de_baldrame(vaos_x, vaos_y, modo)

    q_parede, proveniencia = _q_parede(vb_spec)

    vao_critico = max(max(l[3]) for l in linhas) if linhas else 0.0
    n_max = max(len(l[3]) for l in linhas) if linhas else 1
    continuidade = vb_spec.get("continuidade", "continua" if n_max > 1 else "simples")

    materiais = contexto.get("materiais") or {}
    fck = float(vb_spec.get("fck", materiais.get("fck", 25e3)))
    fyk = float(vb_spec.get("fyk", materiais.get("fyk", 500e3)))

    # N_amarracao: declarado vence o derivado da fundacao (tracao de amarracao)
    if vb_spec.get("N_amarracao") is not None:
        N_amar = float(vb_spec["N_amarracao"])
        prov_N = "declarado em viga_baldrame.N_amarracao"
    else:
        N_amar = _n_amarracao_max(contexto.get("fundacao"))
        prov_N = ("max|V| das combinacoes da fundacao (G23: V heterogeneo por pilar "
                  "quando ha portico heterogeneo, senao uniforme)" if N_amar > 1e-9 else "sem acao horizontal: V=0")

    # Verificacao no maior vao (dimensiona adotando altura se houver parede)
    cfg = {"vao": vao_critico, "b": b, "h": h0, "fck": fck, "fyk": fyk,
           "q_parede": q_parede, "N_amarracao": N_amar,
           "continuidade": continuidade,
           "cobrimento": vb_spec.get("cobrimento", 0.05),
           "phi_estribo_mm": vb_spec.get("phi_estribo_mm", 5.0)}
    # se ha parede, adota altura que atende flecha (Tab 13.3)
    if q_parede > 0:
        r_verif = vb.dimensiona_baldrame(cfg)
    else:
        r_verif = vb.verifica_baldrame(cfg)
    h = float(r_verif["h"])
    w = q_parede + GAMMA_C_CONC * b * h

    # Reacoes por linha (viga continua) e por pilar (soma das duas direcoes)
    import viga_continua as vc

    por_pilar: dict[str, float] = {}
    por_linha = []
    for nome, eixo, indice, vaos in linhas:
        analise = vc.analisa({
            "tramos": [{"L": L, "b": b, "h": h} for L in vaos],
            "g": [w] * len(vaos), "q": [0.0] * len(vaos), "fck": fck})
        reacoes = analise["reacoes"]
        for k, reacao in enumerate(reacoes):
            # mapeia indice da linha para pilar: BX-j varia em x (i=k), BY-i varia em y (j=k)
            if eixo == "x":
                i, j = k, indice
            else:
                i, j = indice, k
            chave = "P%d%d" % (i + 1, j + 1)
            # Alguns grids usam nomes P11, P21... ja no fundacao; mas esse mapeamento
            # e' geometrico (i,j). Mantemos o mesmo para conferir.
            por_pilar[chave] = round(por_pilar.get(chave, 0.0) + float(reacao), 3)
        por_linha.append({"nome": nome, "eixo": eixo, "indice": indice,
                          "vaos": list(vaos),
                          "reacoes_kN": [round(float(v), 3) for v in reacoes],
                          "M_positivo": list(analise["M_positivo"]),
                          "M_apoios": list(analise["M_apoios"])})

    comprimento = sum(sum(l[3]) for l in linhas)
    esperado = w * comprimento
    somado = sum(por_pilar.values())
    erro_rel = abs(somado - esperado) / esperado if esperado > 1e-9 else 0.0
    fechamento_ok = erro_rel <= 0.02

    gate = {"OK": bool(r_verif["OK"]) and fechamento_ok,
            "fechamento_ok": fechamento_ok,
            "erro_rel": round(erro_rel, 5),
            "n_linhas": len(linhas),
            "n_pilares_com_reacao": len(por_pilar)}

    avisos = []
    if r_verif.get("els") is not None and r_verif.get("els_ok") is False:
        avisos.append({"code": "baldrame_flecha_reprova",
                        "detail": "a flecha pos-parede (%.1f mm) excede min(L/500;10)=%.1f mm - aumentar h" % (
                            r_verif["els"]["d_pos_parede_mm"], r_verif["els"]["lim_mm"])})
    if h > h0 + 1e-9:
        avisos.append({"code": "baldrame_altura_adotada",
                        "detail": "altura adotada %.2f m > declarada %.2f m para atender ELS (Tab 13.3)" % (h, h0)})
    if N_amar > 1e-9:
        avisos.append({"code": "baldrame_N_amarracao_derivado",
                        "detail": "N_amarracao = %.1f kN (%s)" % (N_amar, prov_N)})
    # G23: momento nao alimenta a flexao do baldrame - declarado explicitamente
    avisos.append({"code": "baldrame_momento_nao_alimenta_flexao",
                    "detail": "M_portico (momento fletor na base por pilar, G23) NAO alimenta a flexao do baldrame: ele flexiona sob q_parede, nao sob M; M vai para a sapata/estaca e para o travamento da divisa"})

    return {
        "secao": {"b_m": b, "h_m": h, "h_declarada_m": h0, "b_cm": round(b*100), "h_cm": round(h*100)},
        "adotou_altura_maior": h > h0 + 1e-9,
        "continuidade": continuidade,
        "vao_critico_m": round(vao_critico, 3),
        "q_parede_kN_m": round(q_parede, 3),
        "proveniencia_parede": proveniencia,
        "w_kN_m": round(w, 3),
        "linhas": modo,
        "por_linha": por_linha,
        "por_pilar": por_pilar,
        "fechamento": {"ok": fechamento_ok, "N_pilares_kN": round(somado, 2),
                       "carga_esperada_kN": round(esperado, 2), "erro_rel": round(erro_rel, 5),
                       "comprimento_m": round(comprimento, 3)},
        "verificacao": r_verif,
        "N_amarracao_kN": round(N_amar, 2),
        "proveniencia_N_amarracao": prov_N,
        "gate": gate,
        "escopo": _escopo(True),
        "avisos": avisos,
    }


def _escopo(com_baldrame: bool) -> dict:
    return {
        "viga_baldrame": "implemented" if com_baldrame else "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def relatorio_pt(resultado) -> str:
    """Quadro do baldrame do edificio."""
    r = resultado["verificacao"]
    linhas = [
        "VIGA BALDRAME DO EDIFICIO MULTIPAVIMENTO (ABNT NBR 6118:2014)",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "  Secao: %d x %d cm (declarada %d cm) ; continuidade: %s" % (
            resultado["secao"]["b_cm"], resultado["secao"]["h_cm"],
            round(resultado["secao"]["h_declarada_m"]*100), resultado["continuidade"]),
        "  Vao critico: %.2f m ; q_parede = %.2f kN/m (%s)" % (
            resultado["vao_critico_m"], resultado["q_parede_kN_m"], resultado["proveniencia_parede"]),
        "  w (parede + p.p.) = %.3f kN/m ; N_amarracao = %.1f kN (%s)" % (
            resultado["w_kN_m"], resultado["N_amarracao_kN"], resultado["proveniencia_N_amarracao"]),
        "  Linhas: %s (%d linhas) ; fechamento: %.1f kN nos pilares vs %.1f kN esperados (erro %.3f%%) -> %s" % (
            resultado["linhas"], resultado["gate"]["n_linhas"],
            resultado["fechamento"]["N_pilares_kN"], resultado["fechamento"]["carga_esperada_kN"],
            100*resultado["fechamento"]["erro_rel"], "OK" if resultado["fechamento"]["ok"] else "NAO FECHA"),
        "",
        "  " + vb.relatorio_pt(r).replace("\n", "\n  "),
        "",
        "  POR PILAR (reacao do baldrame, kN): " + ", ".join(
            "%s=%.1f" % (k, v) for k, v in sorted(resultado["por_pilar"].items())),
        "",
        "  GATE: %s" % ("ATENDE" if resultado["gate"]["OK"] else "REPROVA"),
    ]
    for aviso in resultado.get("avisos") or []:
        linhas.append("  [%s] %s" % (aviso["code"], aviso["detail"]))
    return "\n".join(linhas)
