# ============================================================================
# orcamento.py - O QUE ESTE SCRIPT FAZ / CALCULA
# A camada 5D: transforma os QUANTITATIVOS do projeto (aco em kg, concreto em m3,
# piso em m2, ...) numa PLANILHA ORCAMENTARIA e na CURVA ABC. E' a ponte
# "projeto -> obra" que faltava: ja tinhamos as quantidades, faltava o custo.
#   - planilha(itens, bdi_pct): custo = quantidade x preco_unitario por item; soma
#     o custo direto e aplica o BDI (Beneficios e Despesas Indiretas) -> preco de
#     venda. BDI e' um PERCENTUAL de projeto (varia por obra/regime) - A CONFIRMAR.
#   - curva_abc(planilha): ordena por custo decrescente, custo acumulado (%), e
#     classifica A / B / C (classe A = itens ate 50% do valor; B = 50-80%; C =
#     80-100%) - a convencao classica de engenharia de custos.
#   - compor_orcamento(quantitativos, precos): mapeia um dict de quantitativos nos
#     itens usando a tabela de precos de REFERENCIA.
# IMPORTANTE (AR300): os PRECOS UNITARIOS sao DADO DE SITIO (SINAPI/tabela oficial,
# por UF, data-base e regime de desoneracao) - a tabela embutida aqui e' de
# REFERENCIA e esta marcada A CONFIRMAR; o usuario substitui pela SINAPI vigente.
# Unidades: R$ ; quantidades nas unidades naturais de cada insumo. STATELESS.
# ============================================================================
"""Orcamento 5D: quantitativos -> planilha orcamentaria + curva ABC + BDI.
Precos de REFERENCIA (A CONFIRMAR - substituir pela SINAPI vigente). STATELESS."""

from __future__ import annotations

BDI_PADRAO_PCT = 25.0           # BDI tipico de obra industrial (A CONFIRMAR)

# Tabela de precos de REFERENCIA (ordem de grandeza, R$ - A CONFIRMAR SINAPI/UF/data).
# NAO e' cotacao: e' so p/ o motor rodar sem entrada. O usuario passa 'precos'.
_PRECOS_REF = {
    # codigo : (descricao, unidade, preco_unitario_R$)
    "aco_estrutural":   ("Aco estrutural fabricado e montado", "kg", 18.00),
    "concreto_estrut":  ("Concreto estrutural fck>=25 MPa lancado", "m3", 620.00),
    "forma":            ("Forma de madeira (chapa) e desforma", "m2", 90.00),
    "armadura":         ("Armadura aco CA-50 cortada/dobrada/montada", "kg", 14.00),
    "piso_industrial":  ("Piso industrial de concreto (placa+junta+acab.)", "m2", 145.00),
    "telha_cobertura":  ("Telha metalica termoacustica + montagem", "m2", 110.00),
    "fechamento_lateral":("Fechamento lateral (telha/alvenaria)", "m2", 130.00),
    "eletrica_ponto":   ("Ponto eletrico (luminaria/tomada + circuito)", "un", 260.00),
    "hidraulica_ponto": ("Ponto hidraulico (agua/esgoto)", "un", 240.00),
    "fundacao_concreto":("Fundacao (concreto+forma+armadura+escavacao)", "m3", 780.00),
    "estaca":           ("Estaca (execucao, por metro)", "m", 210.00),
}


def preco_ref():
    """Copia da tabela de precos de referencia (para inspecao/override parcial)."""
    return {k: v for k, v in _PRECOS_REF.items()}


def planilha(itens, bdi_pct=BDI_PADRAO_PCT):
    """Monta a planilha orcamentaria. itens: lista de dicts
    {codigo, descricao, unidade, quantidade, preco_unitario}. Devolve linhas com
    custo = quantidade x preco_unitario, o custo direto total, o BDI e o preco de
    venda (custo direto x (1+BDI))."""
    linhas = []
    for it in itens:
        q = float(it["quantidade"]); pu = float(it["preco_unitario"])
        if q < 0 or pu < 0:
            raise ValueError("quantidade/preco negativo em %r" % it.get("codigo"))
        custo = q * pu
        linhas.append({"codigo": it.get("codigo", ""),
                       "descricao": it.get("descricao", ""),
                       "unidade": it.get("unidade", ""),
                       "quantidade": round(q, 3), "preco_unitario": round(pu, 2),
                       "custo": round(custo, 2)})
    custo_direto = sum(l["custo"] for l in linhas)
    bdi = custo_direto * bdi_pct / 100.0
    return {"linhas": linhas, "custo_direto": round(custo_direto, 2),
            "bdi_pct": bdi_pct, "bdi_valor": round(bdi, 2),
            "preco_venda": round(custo_direto + bdi, 2),
            "n_itens": len(linhas),
            "nota": "PRECOS A CONFIRMAR (SINAPI/UF/data-base/desoneracao); "
                    "BDI de projeto (varia por obra)."}


def curva_abc(plan, corte_a=50.0, corte_b=80.0):
    """Curva ABC a partir de planilha(): ordena por custo decrescente, custo
    acumulado (%) e classe (A ate corte_a%, B ate corte_b%, C o resto). Retorna
    a lista classificada + o resumo por classe."""
    linhas = sorted(plan["linhas"], key=lambda l: l["custo"], reverse=True)
    total = plan["custo_direto"] or 1.0
    acum = 0.0
    out = []
    resumo = {"A": {"n": 0, "custo": 0.0}, "B": {"n": 0, "custo": 0.0},
              "C": {"n": 0, "custo": 0.0}}
    for l in linhas:
        # classe pelo acumulado ANTES do item (o item lidera a classe ate o corte):
        # assim o 1o item e' sempre A, mesmo que sozinho passe do corte (evita o
        # furo de um item dominante cair em C).
        pct_antes = 100.0 * acum / total
        acum += l["custo"]
        pct_acum = 100.0 * acum / total
        classe = "A" if pct_antes < corte_a else ("B" if pct_antes < corte_b else "C")
        item = dict(l, pct_individual=round(100.0 * l["custo"] / total, 2),
                    pct_acumulado=round(pct_acum, 2), classe=classe)
        out.append(item)
        resumo[classe]["n"] += 1
        resumo[classe]["custo"] = round(resumo[classe]["custo"] + l["custo"], 2)
    return {"itens": out, "resumo": resumo, "corte_a": corte_a, "corte_b": corte_b}


def compor_orcamento(quantitativos, precos=None, bdi_pct=BDI_PADRAO_PCT):
    """Mapeia um dict de quantitativos {codigo: quantidade} nos itens da planilha,
    usando a tabela de precos (default: referencia). Ignora quantidade 0/None e
    codigos sem preco (registrando em 'sem_preco'). Retorna planilha + curva ABC."""
    tab = dict(_PRECOS_REF)
    if precos:
        tab.update(precos)              # override do usuario (SINAPI real)
    itens = []; sem_preco = []
    for cod, q in quantitativos.items():
        if not q:
            continue
        if cod not in tab:
            sem_preco.append(cod); continue
        desc, un, pu = tab[cod]
        itens.append({"codigo": cod, "descricao": desc, "unidade": un,
                      "quantidade": q, "preco_unitario": pu})
    plan = planilha(itens, bdi_pct)
    abc = curva_abc(plan)
    # COBERTURA: um orcamento com uma linha so PARECE um orcamento fechado. Os
    # codigos da tabela que ficaram SEM quantitativo sao declarados - quem le sabe
    # que o preco de venda nao cobre a obra inteira (custo omitido != custo zero).
    orcados = {it["codigo"] for it in itens}
    sem_quantidade = sorted(c for c in tab if c not in orcados)
    return {"planilha": plan, "abc": abc, "sem_preco": sem_preco,
            "sem_quantidade": sem_quantidade,
            "cobertura_pct": round(100.0 * len(orcados) / (len(tab) or 1), 1)}


def relatorio_pt(res, titulo="ORCAMENTO (5D) - PLANILHA + CURVA ABC"):
    """Relatorio-texto da planilha e da curva ABC."""
    plan = res["planilha"]; abc = res["abc"]
    L = [titulo, "=" * len(titulo)]
    L.append("%-38s %-6s %10s %12s %10s" % ("DESCRICAO", "UN", "QUANT", "P.UNIT", "CUSTO"))
    for it in abc["itens"]:
        L.append("%-38.38s %-6s %10.2f %12.2f %10.2f [%s]" %
                 (it["descricao"], it["unidade"], it["quantidade"],
                  it["preco_unitario"], it["custo"], it["classe"]))
    L.append("-" * 78)
    L.append("Custo direto: R$ %s" % f"{plan['custo_direto']:,.2f}")
    L.append("BDI (%.1f%%): R$ %s" % (plan["bdi_pct"], f"{plan['bdi_valor']:,.2f}"))
    L.append("PRECO DE VENDA: R$ %s" % f"{plan['preco_venda']:,.2f}")
    r = abc["resumo"]
    L.append("Curva ABC: A=%d itens (R$ %.2f) | B=%d | C=%d"
             % (r["A"]["n"], r["A"]["custo"], r["B"]["n"], r["C"]["n"]))
    L.append("[%s]" % plan["nota"])
    faltando = res.get("sem_quantidade") or []
    if faltando:
        L.append("ORCAMENTO PARCIAL - %d insumo(s) da tabela SEM quantitativo nesta "
                 "rodada (NAO entram no preco de venda): %s"
                 % (len(faltando), ", ".join(faltando)))
    if res.get("sem_preco"):
        L.append("SEM PRECO NA TABELA (ha quantidade, falta custo): %s"
                 % ", ".join(res["sem_preco"]))
    return "\n".join(L)


def _vol_membros_concreto(membros):
    """Volume de concreto (m3) de uma lista membros_bim (barras RECT + caixas)."""
    import math
    vol = 0.0
    for m in membros:
        if "dims" in m:                            # caixa (dims em MM, como o emissor)
            B, L, h = m["dims"]; vol += B * L * h / 1e9
        elif "secao" in m and "p1" in m:           # barra RECT
            bf = m["secao"].get("bf", 0.0); d = m["secao"].get("d", 0.0)
            p1, p2 = m["p1"], m["p2"]
            comp = math.dist(p1, p2) / 1000.0      # mm -> m
            vol += bf * d * comp
    return vol


def quantitativos_de_turnkey(R):
    """Best-effort: extrai os quantitativos CLARAMENTE disponiveis no resultado de
    galpao_turnkey.rodar(R). O que nao esta pronto o usuario completa (e o que
    faltou aparece em ``sem_quantidade`` na saida de compor_orcamento, para o
    orcamento parcial nao se passar por fechado). Guardado: nunca quebra.
    Retorna {codigo: quantidade}."""
    q = {}
    d = R.get("disciplinas", {})
    conc = d.get("concreto", {})
    if conc.get("rodou"):
        raw = conc.get("raw", {})
        piso = raw.get("piso")
        if piso and piso.get("OK") and piso.get("area_m2"):
            q["piso_industrial"] = piso["area_m2"]
        try:
            import galpao_concreto as gc
            membros = gc.membros_bim(raw)
            # SUPERESTRUTURA e FUNDACAO tem composicao (e preco) diferentes: a
            # sapata leva escavacao/lastro/forma de fundacao. Somar tudo em
            # 'concreto_estrut' e o rotulo errado sobre a mesma geometria.
            sup = [m for m in membros if m.get("tipo") != "Footing"]
            fund = [m for m in membros if m.get("tipo") == "Footing"]
            v_sup = _vol_membros_concreto(sup)
            v_fund = _vol_membros_concreto(fund)
            if v_sup > 0:
                q["concreto_estrut"] = round(v_sup, 1)
            if v_fund > 0:
                q["fundacao_concreto"] = round(v_fund, 1)
        except Exception:
            pass
    aco = d.get("aco", {})
    if aco.get("rodou"):
        # Peso das pecas PRIMARIAS (colunas + rafters) do romaneio do proprio
        # vertical - o insumo que domina a curva ABC de um galpao metalico e que
        # ficava de fora do orcamento inteiro. Secundarias (tercas, longarinas,
        # contraventamento, ligacoes) NAO estao neste peso: ver 'a_confirmar'.
        kg = (aco.get("raw") or {}).get("romaneio_peso_primario_kg")
        try:
            kg = float(kg)
        except (TypeError, ValueError):
            kg = 0.0
        if kg > 0:
            q["aco_estrutural"] = round(kg, 1)
    elet = d.get("eletrico", {})
    if elet.get("rodou"):
        try:
            import instalacao_eletrica as ie
            inst = ie.projeto_instalacao(elet["raw"])
            qi = inst.get("quantitativos", {})
            n = (qi.get("n_pontos_luz", 0) or 0) + (qi.get("n_tomadas", 0) or 0)
            if n:
                q["eletrica_ponto"] = n
        except Exception:
            pass
    return q


# O que o peso do romaneio NAO cobre - dito junto com o numero, nao depois.
NOTA_ACO_PRIMARIO = ("aco_estrutural = pecas PRIMARIAS do romaneio (colunas + "
                     "rafters); tercas, longarinas, contraventamento, ligacoes e "
                     "chapas nao estao neste peso - completar com o romaneio do "
                     "modelo 3D antes de fechar preco")


# ----------------------------------- selftest --------------------------------
def _selftest():
    # planilha basica: custo = q x pu ; BDI aplicado
    itens = [{"codigo": "a", "descricao": "A", "unidade": "kg", "quantidade": 100,
              "preco_unitario": 10.0},
             {"codigo": "b", "descricao": "B", "unidade": "m3", "quantidade": 2,
              "preco_unitario": 500.0}]
    p = planilha(itens, bdi_pct=20.0)
    assert p["custo_direto"] == 2000.0                 # 1000 + 1000
    assert p["bdi_valor"] == 400.0 and p["preco_venda"] == 2400.0

    # curva ABC: item mais caro entra em A; acumulado chega a 100%
    abc = curva_abc(p)
    assert abc["itens"][0]["pct_acumulado"] <= 100.0
    assert abs(abc["itens"][-1]["pct_acumulado"] - 100.0) < 1e-6
    # com 2 itens iguais (50% cada): 1o A (50<=50), 2o B (100>50, <=80? nao, >80 -> C)
    assert abc["itens"][0]["classe"] == "A"

    # ABC classifica: 1 item domina -> A ; caudinha -> C
    itens2 = [{"codigo": "big", "descricao": "grande", "unidade": "un",
               "quantidade": 1, "preco_unitario": 900.0}]
    itens2 += [{"codigo": "s%d" % i, "descricao": "peq%d" % i, "unidade": "un",
                "quantidade": 1, "preco_unitario": 10.0} for i in range(10)]
    a2 = curva_abc(planilha(itens2))
    assert a2["itens"][0]["classe"] == "A" and a2["itens"][0]["codigo"] == "big"
    assert a2["resumo"]["C"]["n"] >= 1

    # compor_orcamento: usa tabela de referencia; codigo sem preco vai p/ sem_preco
    res = compor_orcamento({"aco_estrutural": 50000, "concreto_estrut": 200,
                            "piso_industrial": 800, "codigo_inexistente": 5})
    assert "codigo_inexistente" in res["sem_preco"]
    assert res["planilha"]["custo_direto"] > 0
    # aco 50 t x 18 = 900k domina -> classe A
    top = res["abc"]["itens"][0]
    assert top["codigo"] == "aco_estrutural" and top["classe"] == "A"

    # override de preco do usuario (SINAPI real) vence a referencia
    res2 = compor_orcamento({"aco_estrutural": 1000},
                            precos={"aco_estrutural": ("Aco", "kg", 25.0)})
    assert res2["planilha"]["linhas"][0]["preco_unitario"] == 25.0

    # guard: quantidade negativa levanta
    try:
        planilha([{"codigo": "x", "quantidade": -1, "preco_unitario": 1}])
        assert False
    except ValueError:
        pass
    return True


if __name__ == "__main__":
    _selftest()
    res = compor_orcamento({"aco_estrutural": 42000, "concreto_estrut": 180,
                            "fundacao_concreto": 60, "piso_industrial": 800,
                            "telha_cobertura": 850, "fechamento_lateral": 600,
                            "eletrica_ponto": 56, "hidraulica_ponto": 24})
    print(relatorio_pt(res))
    print("selftest OK")
