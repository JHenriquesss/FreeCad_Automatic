# ============================================================================
# arquitetura_residencial.py - O QUE ESTE MODULO CALCULA
# PROGRAMA DE AMBIENTES de uma casa (modulo de calculo stateless, CI) e a
# PREVISAO DE CARGA da ABNT NBR 5410:2004 Sec.9.5.2, lida LITERALMENTE do PDF no
# NotebookLM (notebook 78cd2efd, fonte d213019d - regra AR300, nunca de memoria):
#
#   9.5.2.1.1 "Em cada comodo ou dependencia deve ser previsto pelo menos um ponto
#             de luz fixo no teto, comandado por interruptor."
#   9.5.2.1.2 "a) em comodos ou dependencias com area igual ou inferior a 6 m2,
#             deve ser prevista uma carga minima de 100 VA; b) em comodo ou
#             dependencias com area superior a 6 m2, deve ser prevista uma carga
#             minima de 100 VA para os primeiros 6 m2, acrescida de 60 VA para
#             cada aumento de 4 m2 INTEIROS."
#   9.5.2.2.1 numero minimo de pontos de tomada, por alinea:
#             a) banheiros: >= 1 ponto proximo ao lavatorio (restricoes de 9.1);
#             b) cozinhas/copas/copas-cozinhas/areas de servico/cozinha-area de
#                servico/lavanderias e analogos: >= 1 ponto por 3,5 m OU FRACAO de
#                perimetro; acima da bancada da pia, >= 2 tomadas;
#             c) varandas: >= 1 ponto;
#             d) salas e dormitorios: >= 1 ponto por 5 m OU FRACAO de perimetro;
#             e) demais comodos: 1 ponto se area <= 2,25 m2; 1 ponto se
#                2,25 < area <= 6 m2; 1 ponto por 5 m ou fracao se area > 6 m2.
#   9.5.2.2.2 potencias minimas: a) nos ambientes molhados da alinea (a)+(b),
#             600 VA por ponto ATE TRES PONTOS e 100 VA por ponto excedente,
#             CADA AMBIENTE SEPARADAMENTE; quando o conjunto desses ambientes
#             passa de seis pontos, ADMITE-SE 600 VA ate DOIS pontos;
#             b) nos demais comodos, 100 VA por ponto.
#
# A alternativa dos dois pontos e' uma PERMISSAO, nao o criterio padrao: aqui ela
# e' calculada num campo separado e sinalizada; o valor adotado continua sendo o
# dos tres pontos (nunca rebaixar a carga em silencio).
#
# ROTULO x GEOMETRIA: um comodo com area A tem perimetro minimo 4*raiz(A) (o
# quadrado, desigualdade isoperimetrica). Perimetro declarado abaixo disso e'
# geometricamente impossivel e REPROVA - sem isso o numero de tomadas sairia de
# uma planta que nao existe.
#
# ESCOPO: quantitativos + previsao de carga. Codigo de obras municipal, NBR 15575
# (desempenho) e aprovacao legal NAO sao avaliados e nao sao reivindicados.
# ============================================================================
"""Programa de ambientes residenciais e previsao de carga NBR 5410:2004 9.5.2.
Modulo de calculo stateless (CI), aferido no _selftest."""

from __future__ import annotations

import copy
import math
from numbers import Real

# --- 9.5.2.1.2 (carga de iluminacao) ---------------------------------------
AREA_BASE_ILUM_M2 = 6.0       # "primeiros 6 m2"
VA_BASE_ILUM = 100.0          # "carga minima de 100 VA"
PASSO_ILUM_M2 = 4.0           # "cada aumento de 4 m2 inteiros"
VA_PASSO_ILUM = 60.0          # "acrescida de 60 VA"

# --- 9.5.2.2.1 (numero de pontos de tomada) --------------------------------
PERIM_MOLHADO_M = 3.5         # alinea b)
PERIM_SECO_M = 5.0            # alineas d) e e)
AREA_MIN_ALINEA_E_M2 = 2.25   # alinea e), primeiro degrau

# --- 9.5.2.2.2 (potencias atribuiveis) -------------------------------------
VA_TOMADA_MOLHADA = 600.0
VA_TOMADA_EXCEDENTE = 100.0
VA_TOMADA_SECA = 100.0
N_PONTOS_600VA = 3            # criterio padrao, alinea a)
N_PONTOS_600VA_ALT = 2        # permissao quando o conjunto passa de 6 pontos
LIMITE_CONJUNTO_MOLHADO = 6   # "superior a seis pontos"

# ambientes da alinea (b) de 9.5.2.2.1 - os mesmos da alinea (a) de 9.5.2.2.2,
# somados aos banheiros (que sao alinea (a) de 9.5.2.2.1 mas tambem 600 VA).
TIPOS_MOLHADOS_PERIMETRO = frozenset({
    "cozinha", "copa", "copa_cozinha", "cozinha_area_servico",
    "area_servico", "lavanderia",
})
TIPOS_BANHEIRO = frozenset({"banheiro", "lavabo"})
TIPOS_VARANDA = frozenset({"varanda", "sacada", "terraco"})
TIPOS_SALA_DORMITORIO = frozenset({
    "sala", "sala_estar", "sala_jantar", "sala_estar_jantar", "dormitorio",
    "quarto", "suite",
})
# os tipos acima sao os NOMEADOS pela norma; qualquer outro cai na alinea (e),
# com aviso explicito (nunca um enquadramento silencioso).
TIPOS_CONHECIDOS = (TIPOS_MOLHADOS_PERIMETRO | TIPOS_BANHEIRO | TIPOS_VARANDA
                    | TIPOS_SALA_DORMITORIO | frozenset({
                        "circulacao", "corredor", "hall", "closet", "deposito",
                        "despensa", "escritorio", "garagem", "escada",
                    }))
TOL_GEOM = 1e-9


def _finito_positivo(valor):
    return (isinstance(valor, Real) and not isinstance(valor, bool)
            and math.isfinite(float(valor)) and float(valor) > 0.0)


def carga_iluminacao_va(area_m2):
    """Carga minima de iluminacao (NBR 5410 9.5.2.1.2), em VA.

    area <= 6 m2 -> 100 VA; acima disso, 100 VA + 60 VA por bloco de 4 m2
    INTEIROS excedentes (a norma diz "cada aumento de 4 m2 inteiros": 13,9 m2
    tem 7,9 m2 excedentes = 1 bloco, nao 2)."""
    if not _finito_positivo(area_m2):
        raise ValueError("area do ambiente deve ser finita e maior que zero.")
    area = float(area_m2)
    if area <= AREA_BASE_ILUM_M2:
        return VA_BASE_ILUM
    blocos = math.floor((area - AREA_BASE_ILUM_M2) / PASSO_ILUM_M2 + TOL_GEOM)
    return VA_BASE_ILUM + VA_PASSO_ILUM * blocos


def _pontos_por_perimetro(perimetro_m, passo_m):
    """1 ponto por 'passo' metros OU FRACAO de perimetro (minimo 1)."""
    return max(1, int(math.ceil(perimetro_m / passo_m - TOL_GEOM)))


def criterio_tomadas(tipo, area_m2, perimetro_m):
    """(criterio, n_pontos, molhado, notas) da NBR 5410 9.5.2.2.1/9.5.2.2.2."""
    notas = []
    if tipo in TIPOS_BANHEIRO:
        notas.append("9.5.2.2.1-a: ponto proximo ao lavatorio, atendidas as "
                     "restricoes de 9.1 (volumes do banheiro).")
        return "9.5.2.2.1-a", 1, True, notas
    if tipo in TIPOS_MOLHADOS_PERIMETRO:
        n = _pontos_por_perimetro(perimetro_m, PERIM_MOLHADO_M)
        notas.append("9.5.2.2.1-b: acima da bancada da pia devem ser previstas "
                     "no minimo duas tomadas de corrente.")
        notas.append("9.5.3.2: estes pontos exigem circuito exclusivo de tomadas.")
        return "9.5.2.2.1-b", n, True, notas
    if tipo in TIPOS_VARANDA:
        notas.append("9.5.2.2.1-c: admite-se o ponto proximo ao acesso quando a "
                     "varanda tem area < 2 m2 ou profundidade < 0,80 m.")
        return "9.5.2.2.1-c", 1, False, notas
    if tipo in TIPOS_SALA_DORMITORIO:
        return ("9.5.2.2.1-d",
                _pontos_por_perimetro(perimetro_m, PERIM_SECO_M), False, notas)
    if area_m2 <= AREA_MIN_ALINEA_E_M2:
        notas.append("9.5.2.2.1-e: admite-se o ponto externo ao comodo, a ate "
                     "0,80 m da porta de acesso.")
        return "9.5.2.2.1-e-1", 1, False, notas
    if area_m2 <= AREA_BASE_ILUM_M2:
        return "9.5.2.2.1-e-2", 1, False, notas
    return ("9.5.2.2.1-e-3",
            _pontos_por_perimetro(perimetro_m, PERIM_SECO_M), False, notas)


def carga_tomadas_va(n_pontos, molhado, n_pontos_600va=N_PONTOS_600VA):
    """Potencia minima do conjunto de tomadas do ambiente (9.5.2.2.2), em VA."""
    if not molhado:
        return VA_TOMADA_SECA * n_pontos
    plenos = min(n_pontos, n_pontos_600va)
    return VA_TOMADA_MOLHADA * plenos + VA_TOMADA_EXCEDENTE * (n_pontos - plenos)


def _geometria_do_ambiente(amb, indice):
    """(area, perimetro, erros): area e perimetro conferidos entre si.

    Aceita largura/comprimento (retangulo) e/ou area/perimetro declarados. Nao
    inventa nenhum dos dois: sem geometria suficiente, devolve (None, None)."""
    erros = []
    nome = amb.get("nome") or "ambiente[%d]" % indice
    largura = amb.get("largura_m")
    comprimento = amb.get("comprimento_m")
    area = amb.get("area_m2")
    perimetro = amb.get("perimetro_m")

    for campo, valor in (("largura_m", largura), ("comprimento_m", comprimento),
                         ("area_m2", area), ("perimetro_m", perimetro)):
        if valor is not None and not _finito_positivo(valor):
            erros.append({"code": "geometria_invalida", "ambiente": nome,
                          "campo": campo,
                          "detail": "%s deve ser finito e maior que zero" % campo})

    if erros:
        return None, None, erros

    area_geo = perim_geo = None
    if largura is not None and comprimento is not None:
        area_geo = float(largura) * float(comprimento)
        perim_geo = 2.0 * (float(largura) + float(comprimento))

    if area is not None and area_geo is not None and not math.isclose(
            float(area), area_geo, rel_tol=1e-3):
        erros.append({
            "code": "area_declarada_diverge_da_geometria", "ambiente": nome,
            "area_declarada_m2": float(area), "area_geometrica_m2": area_geo,
            "detail": "area_m2 declarada nao confere com largura x comprimento"})
    if perimetro is not None and perim_geo is not None and not math.isclose(
            float(perimetro), perim_geo, rel_tol=1e-3):
        erros.append({
            "code": "perimetro_declarado_diverge_da_geometria", "ambiente": nome,
            "perimetro_declarado_m": float(perimetro),
            "perimetro_geometrico_m": perim_geo,
            "detail": "perimetro_m declarado nao confere com 2*(L+C)"})

    if erros:
        # geometria CONTESTADA (o rotulo diverge da medida): nao publicar numero
        # derivado de uma planta em disputa - o ambiente fica sem previsao ate a
        # divergencia ser resolvida.
        return None, None, erros

    area_final = float(area) if area is not None else area_geo
    perim_final = float(perimetro) if perimetro is not None else perim_geo
    if area_final is None or perim_final is None:
        erros.append({
            "code": "geometria_ausente", "ambiente": nome,
            "detail": "informe largura_m + comprimento_m ou area_m2 + perimetro_m"})
        return None, None, erros

    # ROTULO x GEOMETRIA: desigualdade isoperimetrica - nenhuma figura plana de
    # area A tem perimetro menor que o do circulo (2*raiz(pi*A)); para um comodo
    # ortogonal o piso e' 4*raiz(A) (o quadrado). Abaixo disso a planta nao existe.
    perim_min = 4.0 * math.sqrt(area_final)
    if perim_final < perim_min * (1.0 - 1e-6):
        erros.append({
            "code": "perimetro_incompativel_com_area", "ambiente": nome,
            "perimetro_m": perim_final, "perimetro_minimo_m": perim_min,
            "area_m2": area_final,
            "detail": "perimetro menor que o do quadrado de mesma area "
                      "(4*raiz(A)): geometria impossivel"})
        return None, None, erros
    return area_final, perim_final, erros


def rodar(spec):
    """Calcula o programa de ambientes e a previsao de carga NBR 5410 9.5.2.

    spec: {ambientes: [{nome, tipo, largura_m, comprimento_m | area_m2,
           perimetro_m}], pe_direito_m (opcional)}.
    Retorna {ambientes, totais, gates, reprovados, erros, avisos, escopo, ATENDE}."""
    if not isinstance(spec, dict):
        raise TypeError("spec de arquitetura residencial deve ser um dicionario")
    ambientes_spec = spec.get("ambientes")
    erros = []
    avisos = []
    if not isinstance(ambientes_spec, list):
        raise TypeError("spec['ambientes'] deve ser uma lista")
    if not ambientes_spec:
        erros.append({"code": "programa_vazio",
                      "detail": "informe ao menos um ambiente"})

    ambientes = []
    nomes = set()
    for indice, bruto in enumerate(ambientes_spec):
        if not isinstance(bruto, dict):
            erros.append({"code": "ambiente_invalido", "indice": indice,
                          "detail": "cada ambiente deve ser um objeto"})
            continue
        nome = bruto.get("nome") or "ambiente[%d]" % indice
        if nome in nomes:
            erros.append({"code": "ambiente_duplicado", "ambiente": nome,
                          "detail": "nome de ambiente repetido"})
        nomes.add(nome)
        tipo = str(bruto.get("tipo") or "").strip().lower()
        if tipo not in TIPOS_CONHECIDOS:
            avisos.append({
                "code": "tipo_ambiente_nao_mapeado", "ambiente": nome,
                "tipo": tipo,
                "detail": "tipo nao nomeado pela NBR 5410 9.5.2.2.1; enquadrado "
                          "na alinea (e) - confirme a destinacao do local"})
        area, perimetro, erros_geo = _geometria_do_ambiente(bruto, indice)
        erros.extend(erros_geo)
        if area is None or perimetro is None:
            ambientes.append({
                "nome": nome, "tipo": tipo, "area_m2": None, "perimetro_m": None,
                "criterio_tomadas": None, "n_tomadas_min": None,
                "n_pontos_luz_min": None, "carga_iluminacao_va": None,
                "carga_tomadas_va": None, "carga_tomadas_va_alternativa": None,
                "molhado": None, "notas": [], "geometria_ok": False})
            continue
        criterio, n_tomadas, molhado, notas = criterio_tomadas(tipo, area, perimetro)
        ambientes.append({
            "nome": nome, "tipo": tipo,
            "area_m2": round(area, 4), "perimetro_m": round(perimetro, 4),
            "criterio_tomadas": criterio, "n_tomadas_min": n_tomadas,
            # 9.5.2.1.1: pelo menos um ponto de luz fixo no teto por comodo
            "n_pontos_luz_min": 1,
            "carga_iluminacao_va": carga_iluminacao_va(area),
            "carga_tomadas_va": carga_tomadas_va(n_tomadas, molhado),
            "carga_tomadas_va_alternativa": carga_tomadas_va(
                n_tomadas, molhado, N_PONTOS_600VA_ALT),
            "molhado": molhado, "notas": notas, "geometria_ok": True})

    validos = [a for a in ambientes if a["geometria_ok"]]
    pontos_molhados = sum(a["n_tomadas_min"] for a in validos if a["molhado"])
    alternativa = pontos_molhados > LIMITE_CONJUNTO_MOLHADO
    totais = {
        "n_ambientes": len(ambientes),
        "area_util_m2": round(sum(a["area_m2"] for a in validos), 4),
        "carga_iluminacao_va": sum(a["carga_iluminacao_va"] for a in validos),
        "carga_tomadas_va": sum(a["carga_tomadas_va"] for a in validos),
        "carga_tomadas_va_alternativa": sum(
            a["carga_tomadas_va_alternativa"] for a in validos),
        "n_pontos_luz_min": sum(a["n_pontos_luz_min"] for a in validos),
        "n_tomadas_min": sum(a["n_tomadas_min"] for a in validos),
        "pontos_molhados": pontos_molhados,
        # a permissao dos dois pontos so vale se o CONJUNTO passa de seis pontos;
        # mesmo disponivel, o valor adotado continua sendo o dos tres pontos.
        "alternativa_9_5_2_2_2_disponivel": alternativa,
        "alternativa_adotada": False,
    }
    if alternativa:
        avisos.append({
            "code": "alternativa_9_5_2_2_2_disponivel",
            "pontos_molhados": pontos_molhados,
            "detail": "o conjunto de ambientes molhados passa de seis pontos; a "
                      "norma ADMITE 600 VA ate dois pontos. Nao adotado: decisao "
                      "do projetista"})
    if len(validos) < len(ambientes):
        avisos.append({
            "code": "ambientes_sem_previsao_de_carga",
            "n": len(ambientes) - len(validos),
            "detail": "ambientes com geometria invalida ficaram fora dos totais"})

    gates = {
        "geometria": {"OK": not erros, "n_ambientes_validos": len(validos),
                      "n_ambientes": len(ambientes)},
        "previsao_carga": {
            "OK": bool(validos) and all(
                a["n_tomadas_min"] >= 1 and a["n_pontos_luz_min"] >= 1
                for a in validos),
            "carga_iluminacao_va": totais["carga_iluminacao_va"],
            "carga_tomadas_va": totais["carga_tomadas_va"],
            "n_tomadas_min": totais["n_tomadas_min"]},
    }
    escopo = {
        "quantitativos": "implemented",
        "previsao_carga_nbr5410": "implemented",
        "codigo_de_obras": "not_evaluated",
        "desempenho_nbr15575": "not_evaluated",
        "acessibilidade_nbr9050": "not_evaluated",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }
    resultado = {
        "schema": "freecad-automatic/residential-architecture",
        "schema_version": 1,
        "ambientes": ambientes,
        "totais": totais,
        "pe_direito_m": spec.get("pe_direito_m"),
        "gates": gates,
        "erros": erros,
        "avisos": avisos,
        "escopo": escopo,
    }
    resultado["reprovados"] = [k for k, g in gates.items() if not g["OK"]]
    resultado["ATENDE"] = not resultado["reprovados"] and not erros
    return resultado


def previsao_por_ambiente(resultado):
    """Mapa {nome_do_ambiente: registro} para a conferencia ponto x minimo."""
    return {a["nome"]: copy.deepcopy(a) for a in resultado["ambientes"]}


def relatorio_pt(resultado):
    """Resumo textual da previsao de carga (uma linha por ambiente)."""
    linhas = ["Previsao de carga NBR 5410:2004 9.5.2 (%d ambientes, %.2f m2)"
              % (resultado["totais"]["n_ambientes"],
                 resultado["totais"]["area_util_m2"])]
    for a in resultado["ambientes"]:
        if not a["geometria_ok"]:
            linhas.append("  %-18s GEOMETRIA INVALIDA" % a["nome"])
            continue
        linhas.append(
            "  %-18s %5.2f m2  perim %5.2f m  ilum %4.0f VA  %d tomada(s) "
            "%5.0f VA  [%s]"
            % (a["nome"], a["area_m2"], a["perimetro_m"], a["carga_iluminacao_va"],
               a["n_tomadas_min"], a["carga_tomadas_va"], a["criterio_tomadas"]))
    t = resultado["totais"]
    linhas.append("  TOTAL: iluminacao %.0f VA + tomadas %.0f VA (%d pontos)"
                  % (t["carga_iluminacao_va"], t["carga_tomadas_va"],
                     t["n_tomadas_min"]))
    return "\n".join(linhas)


def _selftest():
    # 9.5.2.1.2 conferido nos degraus da norma
    assert carga_iluminacao_va(6.0) == 100.0
    assert carga_iluminacao_va(10.0) == 160.0
    assert carga_iluminacao_va(13.9) == 160.0
    assert carga_iluminacao_va(14.0) == 220.0
    # 9.5.2.2.1-b: cozinha 2,5 x 3,6 -> perimetro 12,2 m -> ceil(12,2/3,5) = 4
    r = rodar({"ambientes": [
        {"nome": "Cozinha", "tipo": "cozinha", "largura_m": 2.5,
         "comprimento_m": 3.6}]})
    cozinha = r["ambientes"][0]
    assert cozinha["n_tomadas_min"] == 4
    assert cozinha["carga_tomadas_va"] == 3 * 600.0 + 100.0
    # rotulo x geometria: 12 m2 com 10 m de perimetro e' impossivel
    ruim = rodar({"ambientes": [
        {"nome": "X", "tipo": "sala", "area_m2": 12.0, "perimetro_m": 10.0}]})
    assert ruim["ATENDE"] is False
    print("arquitetura_residencial self-test PASSED (NBR 5410 9.5.2)")


if __name__ == "__main__":
    _selftest()
