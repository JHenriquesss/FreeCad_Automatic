# ============================================================================
# cargas_eletricas.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Previsao de cargas e DEMANDA de uma instalacao eletrica INDUSTRIAL (galpao),
# 1a etapa do projeto eletrico. Base: Joao Mamede Filho, "Instalacoes Eletricas
# Industriais", Cap.1 (fatores de projeto e determinacao de demanda) e ABNT NBR
# 5410 4.2.1 (previsao de potencia). Cobre:
#   1) FATORES DE PROJETO (1.8.1):
#      - fator de demanda Fd = Dmax/Pinst ; fator de utilizacao Fu = Pabs/Pnom ;
#        fator de simultaneidade Fs = Dmax,grupo/soma(Dindiv) ; fator de carga
#        Fc = Dmed/Dmax.
#   2) DEMANDA DE MOTORES (1.8.2): potencia no eixo Peixo = Pn(cv) x Fu ;
#      demanda ativa por motor Dm(kW) = Peixo x 0,736 / eta ;
#      demanda aparente Dm(kVA) = Dm(kW) / Fp ; grupo = Nm x Fs x Dm.
#   3) DEMANDA DE ILUMINACAO/TOMADAS: Fu unitario (Tab.1.3); 200 VA por tomada
#      industrial (1.4). Fator de demanda por ocupacao em faixas (Tab.1.8).
# Valores das Tabelas 1.2 (simultaneidade), 1.3 (utilizacao) e 1.8 (demanda por
# ocupacao) e das formulas 1.8/1.9 LIDOS do PDF de Mamede via NotebookLM - NAO de
# memoria. Solver aferido contra o Exemplo de aplicacao do Cap.1 (motor 75 cv ->
# 52,2 kW / 60,7 kVA ; motor 30 cv -> 25,5 cv no eixo).
# Unidades: potencia de motor em cv; demanda em kW e kVA; tomada em VA. Saidas em
# portugues.
# ============================================================================
"""Previsao de cargas e demanda de instalacao industrial (Mamede Cap.1 / NBR 5410
4.2.1): fatores de projeto, demanda de motores (kW/kVA) e de iluminacao/tomadas."""

from __future__ import annotations

import math

# 1 cv = 0,736 kW (Mamede Cap.1, formulas de demanda de motores)
CV_KW = 0.736
# potencia atribuida por tomada em ambiente industrial (Mamede 1.4 / NBR 5410)
POT_TOMADA_VA = 200.0

# --- Tabela 1.3: fator de utilizacao (Fu) por tipo de carga -----------------
FATOR_UTILIZACAO = {
    "forno_resistencia": 1.00,
    "secador_caldeira": 1.00,
    "forno_inducao": 1.00,
    "soldador": 1.00,
    "retificador": 1.00,
    "iluminacao": 1.00,          # iluminacao, ar-cond. e aquecimento -> 1,0
    "ar_condicionado": 1.00,
    "aquecimento": 1.00,
}
# fator de utilizacao de MOTOR por faixa de potencia (cv), Tabela 1.3
_FU_MOTOR = [(2.5, 0.70), (15.0, 0.83), (40.0, 0.85), (math.inf, 0.87)]

# --- Tabela 1.2: fator de simultaneidade (Fs), colunas por n de aparelhos ----
_FS_COLUNAS = [2, 4, 5, 8, 10, 15, 20, 50]
FATOR_SIMULTANEIDADE = {
    # faixa de motor (cv): valores por numero de aparelhos [2,4,5,8,10,15,20,50]
    "3/4-2,5": [0.85, 0.80, 0.75, 0.70, 0.60, 0.55, 0.50, 0.40],
    "3-15":    [0.85, 0.80, 0.75, 0.75, 0.70, 0.65, 0.55, 0.45],
    "20-40":   [0.80, 0.80, 0.80, 0.75, 0.65, 0.60, 0.60, 0.50],
    ">40":     [0.90, 0.80, 0.70, 0.70, 0.65, 0.65, 0.65, 0.60],
    "retificador": [0.90, 0.90, 0.85, 0.80, 0.75, 0.70, 0.70, 0.70],
    "soldador":    [0.45, 0.45, 0.45, 0.40, 0.40, 0.30, 0.30, 0.30],
    "forno":       [1.00, 1.00, None, None, None, None, None, None],
}

# --- Tabela 1.8: fator de demanda de iluminacao/tomadas por ocupacao ---------
# cada ocupacao: lista de faixas (limite_superior_kW, fator) aplicadas em degraus;
# ultima faixa com limite math.inf. Ex.: escritorio = 100% ate 20 kW, 70% acima.
FATOR_DEMANDA_OCUPACAO = {
    "auditorio":  [(math.inf, 1.00)],
    "banco_loja": [(math.inf, 1.00)],
    "clube":      [(math.inf, 1.00)],
    "garagem":    [(math.inf, 1.00)],
    "igreja":     [(math.inf, 1.00)],
    "restaurante":[(math.inf, 1.00)],
    "escola":     [(12.0, 1.00), (math.inf, 0.50)],
    "escritorio": [(20.0, 1.00), (math.inf, 0.70)],
    "hospital":   [(50.0, 0.40), (math.inf, 0.20)],
    "hotel":      [(20.0, 0.50), (100.0, 0.40), (math.inf, 0.30)],
    "residencia": [(10.0, 1.00), (120.0, 0.35), (math.inf, 0.25)],
    "industrial": [(math.inf, 1.00)],   # galpao: iluminacao/tomadas por Fu, sem degrau
}


def _faixa_motor(cv):
    """Faixa da Tabela 1.2/1.3 para a potencia do motor (cv)."""
    if cv <= 2.5:
        return "3/4-2,5"
    if cv <= 15.0:
        return "3-15"
    if cv <= 40.0:
        return "20-40"
    return ">40"


def fator_utilizacao_motor(cv):
    """Fu de motor por faixa de potencia (cv), Tabela 1.3."""
    for lim, fu in _FU_MOTOR:
        if cv <= lim:
            return fu
    return _FU_MOTOR[-1][1]


def fator_utilizacao(tipo):
    """Fu por tipo de carga nao-motriz (Tabela 1.3). tipo desconhecido -> erro
    (nao inventar; exigir dado)."""
    try:
        return FATOR_UTILIZACAO[tipo]
    except KeyError:
        raise ValueError(
            "[A CONFIRMAR] fator de utilizacao nao tabelado para '%s' "
            "(informar Fu explicito)." % tipo)


def fator_simultaneidade(n, cv=None, categoria=None):
    """Fs (Tabela 1.2) para um grupo de n aparelhos. Informe cv (motor) OU
    categoria ('retificador'/'soldador'/'forno'). Interpola por degrau: usa a
    coluna com o maior n tabelado <= n. n<=1 -> 1,0 (aparelho isolado)."""
    if n <= 1:
        return 1.0
    chave = categoria if categoria is not None else _faixa_motor(cv)
    linha = FATOR_SIMULTANEIDADE[chave]
    fs = None
    for col, val in zip(_FS_COLUNAS, linha):
        if val is None:
            break
        if col <= n:
            fs = val
        else:
            break
    if fs is None:                       # n entre 1 e a primeira coluna (2)
        fs = next(v for v in linha if v is not None)
    return fs


def demanda_motor(caso):
    """Demanda de um tipo de motor (ou grupo de Nm iguais), Mamede 1.8.2.
    caso: {P_cv, eta, Fp, n(=1), Fu(opcional->tabela), Fs(opcional->tabela)}.
    Retorna dict com potencia no eixo, demanda ativa (kW) e aparente (kVA)."""
    cv = float(caso["P_cv"])
    n = int(caso.get("n", 1))
    eta = float(caso["eta"])
    Fp = float(caso["Fp"])
    Fu = float(caso["Fu"]) if caso.get("Fu") is not None else fator_utilizacao_motor(cv)
    Fs = float(caso["Fs"]) if caso.get("Fs") is not None else fator_simultaneidade(n, cv=cv)
    p_eixo_cv = cv * Fu                       # potencia no eixo de 1 motor (cv)
    d_kW_1 = p_eixo_cv * CV_KW / eta          # demanda de 1 motor (kW)
    d_kW = d_kW_1 * n * Fs                     # demanda do grupo (kW)
    d_kVA = d_kW / Fp                          # demanda do grupo (kVA)
    return {"n": n, "P_cv": cv, "Fu": Fu, "Fs": Fs, "eta": eta, "Fp": Fp,
            "p_eixo_cv": p_eixo_cv, "D_kW_unit": d_kW_1, "D_kW": d_kW, "D_kVA": d_kVA}


def demanda_grupo_motores(motores):
    """Soma a demanda de varios tipos de motor. motores: lista de casos de
    demanda_motor. Retorna {D_kW, D_kVA, itens}."""
    itens = [demanda_motor(m) for m in motores]
    d_kW = sum(i["D_kW"] for i in itens)
    d_kVA = sum(i["D_kVA"] for i in itens)
    return {"D_kW": d_kW, "D_kVA": d_kVA, "itens": itens}


def potencia_tomadas_VA(n_tomadas, pot_va=POT_TOMADA_VA):
    """Potencia instalada de tomadas industriais: n x 200 VA (Mamede 1.4)."""
    return n_tomadas * pot_va


def fator_demanda_ocupacao(P_kW, ocupacao):
    """Aplica o fator de demanda por ocupacao em degraus (Tabela 1.8) sobre a
    potencia P_kW de iluminacao/tomadas. Retorna a demanda resultante (kW)."""
    faixas = FATOR_DEMANDA_OCUPACAO.get(ocupacao)
    if faixas is None:
        raise ValueError("[A CONFIRMAR] ocupacao '%s' nao tabelada." % ocupacao)
    demanda = 0.0
    restante = P_kW
    piso = 0.0
    for limite, fator in faixas:
        largura = limite - piso
        parcela = min(restante, largura)
        if parcela <= 0:
            break
        demanda += parcela * fator
        restante -= parcela
        piso = limite
    return demanda


def demanda_iluminacao(P_inst_kW, fp=0.92, ocupacao="industrial"):
    """Demanda de iluminacao/tomadas: aplica o fator de demanda de ocupacao
    (industrial=1,0) e converte a kVA pelo fator de potencia das luminarias."""
    d_kW = fator_demanda_ocupacao(P_inst_kW, ocupacao)
    d_kVA = d_kW / fp
    return {"D_kW": d_kW, "D_kVA": d_kVA, "P_inst_kW": P_inst_kW, "fp": fp}


def quadro_de_cargas(spec):
    """Monta o quadro de cargas e a demanda TOTAL da instalacao industrial.
    spec['cargas'] = {
        'motores': [ {P_cv, n, eta, Fp, Fu?, Fs?}, ... ],
        'iluminacao_kW': float, 'ilum_fp': float(=0,92), 'ocupacao': str,
        'outras': [ {nome, P_kW, D_kW, D_kVA} ... ]   # cargas ja em demanda
    }
    Retorna {P_inst_kW, D_kW, D_kVA, fp_resultante, por_grupo, OK, linhas}."""
    cargas = spec.get("cargas", {})
    por_grupo = {}
    linhas = []

    mot = demanda_grupo_motores(cargas.get("motores", []))
    if cargas.get("motores"):
        por_grupo["motores"] = {"D_kW": mot["D_kW"], "D_kVA": mot["D_kVA"]}
        for it in mot["itens"]:
            linhas.append((("%dx motor %.0f cv" % (it["n"], it["P_cv"])),
                           it["D_kW"], it["D_kVA"]))

    ilum_kW = float(cargas.get("iluminacao_kW", 0.0))
    if ilum_kW > 0:
        il = demanda_iluminacao(ilum_kW, fp=float(cargas.get("ilum_fp", 0.92)),
                                ocupacao=cargas.get("ocupacao", "industrial"))
        por_grupo["iluminacao"] = {"D_kW": il["D_kW"], "D_kVA": il["D_kVA"]}
        linhas.append(("iluminacao/tomadas", il["D_kW"], il["D_kVA"]))

    for o in cargas.get("outras", []):
        por_grupo[o["nome"]] = {"D_kW": o["D_kW"], "D_kVA": o["D_kVA"]}
        linhas.append((o["nome"], o["D_kW"], o["D_kVA"]))

    # potencia instalada (nominal): motores em kW nominais + iluminacao + outras
    p_inst_mot = sum(m["P_cv"] * CV_KW * int(m.get("n", 1)) for m in cargas.get("motores", []))
    p_inst = p_inst_mot + ilum_kW + sum(o.get("P_kW", o["D_kW"]) for o in cargas.get("outras", []))

    D_kW = sum(g["D_kW"] for g in por_grupo.values())
    D_kVA = sum(g["D_kVA"] for g in por_grupo.values())
    fp_result = (D_kW / D_kVA) if D_kVA > 0 else 0.0
    tem_carga = D_kVA > 0
    return {"P_inst_kW": p_inst, "D_kW": D_kW, "D_kVA": D_kVA,
            "fp_resultante": fp_result, "por_grupo": por_grupo,
            "linhas": linhas, "OK": tem_carga}


def _selftest():
    """Afere contra o Exemplo de aplicacao do Cap.1 de Mamede (planta industrial)."""
    # Motor tipo (1): 75 cv, Fu=0,87, eta=0,92, Fp=0,86 -> 52,2 kW ; 60,7 kVA
    m1 = demanda_motor({"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 1})
    assert abs(m1["Fu"] - 0.87) < 1e-9, m1["Fu"]           # Fu de >40 cv (Tab.1.3)
    assert abs(m1["p_eixo_cv"] - 65.25) < 1e-6, m1["p_eixo_cv"]
    assert abs(m1["D_kW"] - 52.2) < 0.1, m1["D_kW"]
    assert abs(m1["D_kVA"] - 60.7) < 0.1, m1["D_kVA"]
    # Motor tipo (2): 30 cv, Fu=0,85 -> potencia no eixo 25,5 cv
    m2 = demanda_motor({"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 1})
    assert abs(m2["Fu"] - 0.85) < 1e-9, m2["Fu"]           # Fu de 20-40 cv
    assert abs(m2["p_eixo_cv"] - 25.5) < 1e-6, m2["p_eixo_cv"]
    # Tabela 1.2 (fator de simultaneidade), faixa 3-15 cv
    assert fator_simultaneidade(8, cv=10.0) == 0.75
    assert fator_simultaneidade(10, cv=10.0) == 0.70
    assert fator_simultaneidade(1, cv=10.0) == 1.0
    assert fator_simultaneidade(3, cv=10.0) == 0.85       # degrau: usa coluna 2
    assert fator_simultaneidade(5, categoria="soldador") == 0.45
    # Tabela 1.8 (fator de demanda por ocupacao) em degraus
    assert abs(fator_demanda_ocupacao(30.0, "escritorio") - 27.0) < 1e-9   # 20*1 + 10*0,7
    assert abs(fator_demanda_ocupacao(30.0, "industrial") - 30.0) < 1e-9
    print("cargas_eletricas self-test PASSED (Mamede Cap.1 Ex. + Tab.1.2/1.3/1.8)")


if __name__ == "__main__":
    _selftest()
