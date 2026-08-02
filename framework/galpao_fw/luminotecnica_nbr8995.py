# ============================================================================
# luminotecnica_nbr8995.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Projeto LUMINOTECNICO de interiores (galpao) pelo METODO DOS LUMENS, definindo o
# numero de luminarias e a POTENCIA DE ILUMINACAO instalada (que alimenta a previsao
# de cargas). Base: ABNT NBR ISO/CIE 8995-1 (niveis de iluminancia) / NBR 5413 e
# Mamede Cap.2 / Creder Cap.13:
#   1) FLUXO LUMINOSO TOTAL (2.6): phi_total = E*A/(Fu*Fdl) [lm].
#   2) NUMERO DE LUMINARIAS: N = phi_total/(n_lampadas*phi_lampada) =
#      E*A/(phi_lampada*n_lampadas*Fu*Fdl).
#   3) INDICE DO RECINTO: K = (C*L)/(Hlp*(C+L)), Hlp = altura da luminaria ao plano
#      de trabalho (plano em 0,85 m do piso na ausencia de def.).
#   4) FATOR DE MANUTENCAO/DEPRECIACAO Fdl: limpo 0,80 / medio 0,70 / sujo 0,60.
#   5) FATOR DE UTILIZACAO Fu: do CATALOGO da luminaria (funcao de K + refletancias
#      teto/parede/piso). Aqui e ENTRADA (A CONFIRMAR pelo catalogo); default 0,60.
# Formula, niveis de iluminancia, refletancias e fatores LIDOS do PDF (NotebookLM) -
# NAO de memoria. Fluxos de luminaria LED lidos das tabelas dos livros; high-bay pela
# faixa de eficiencia documentada (100-150 lm/W).
# Unidades: E em lux; A em m2; fluxo em lm; P em W. Saidas em portugues.
# ============================================================================
"""Projeto luminotecnico de galpao pelo metodo dos lumens (NBR 8995-1 / Mamede
Cap.2 / Creder Cap.13): iluminancia, indice do recinto, numero de luminarias e
potencia de iluminacao instalada."""

from __future__ import annotations

import math

# Niveis de iluminancia mantida E (lux) por atividade (NBR ISO/CIE 8995-1 / 5413)
ILUMINANCIA = {
    "circulacao": 100,          # areas de circulacao/corredores industriais
    "armazem_geral": 100,       # locais de armazenamento - geral
    "deposito": 150,            # deposito/estoque
    "armazem_volumes": 200,     # armazenamento de grandes volumes
    "producao_bruta": 300,      # trabalho industrial bruto
    "usinagem_grosseira": 500,  # usinagem grosseira / maquinaria
    "producao": 500,            # galpao de producao / montagem media
    "montagem_media": 500,      # montagem media (ex.: quadros)
    "montagem_fina": 750,       # montagem fina
    "montagem_precisao": 1000,  # montagem de precisao / inspecao
    "escritorio": 500,          # escritorio administrativo
}

# Refletancias medias (fracao) por tonalidade (Mamede 2.6.7.1.2)
REFLETANCIA_TETO = {"branco": 0.70, "claro": 0.50, "escuro": 0.30}
REFLETANCIA_PAREDE = {"clara": 0.50, "escura": 0.30}
REFLETANCIA_PISO = {"claro": 0.30, "medio": 0.20, "escuro": 0.10}

# Fator de manutencao/depreciacao Fdl por ambiente (Creder Tab.13.9 / Negrisoli 2.22)
FATOR_MANUTENCAO = {"limpo": 0.80, "medio": 0.70, "sujo": 0.60}

# Catalogo de luminarias/lampadas (fluxo por LAMPADA em lm). LED tubular: Mamede
# Tab.2.15 (26W->3900lm, 18W->1850lm). High-bay LED: fluxo pela faixa de eficiencia
# documentada (100-150 lm/W) - A CONFIRMAR no catalogo do fabricante.
LUMINARIAS = {
    "led_tubular_18W": {"P_W": 18, "fluxo_lm": 1850, "n_lampadas": 1},
    "led_tubular_26W": {"P_W": 26, "fluxo_lm": 3900, "n_lampadas": 1},
    "high_bay_led_100W": {"P_W": 100, "fluxo_lm": 13000, "n_lampadas": 1},   # ~130 lm/W
    "high_bay_led_150W": {"P_W": 150, "fluxo_lm": 21000, "n_lampadas": 1},   # ~140 lm/W
}

FU_DEFAULT = 0.60           # fator de utilizacao default (direto industrial), A CONFIRMAR
# tabela-exemplo de Fu (Philips TMS, teto70/parede50/piso10) por K - so p/ K tabelado
_FU_TMS = {0.60: 0.32, 0.80: 0.39, 1.00: 0.45}


def iluminancia_recomendada(atividade):
    """Iluminancia mantida E (lux) para a atividade (NBR 8995-1). Desconhecida ->
    erro (nao inventar; informar E explicito)."""
    try:
        return ILUMINANCIA[atividade]
    except KeyError:
        raise ValueError("[A CONFIRMAR] atividade '%s' sem iluminancia tabelada "
                         "(informar E em lux)." % atividade)


def indice_recinto(C, L, Hlp):
    """Indice do recinto K = (C*L)/(Hlp*(C+L)). C,L,Hlp em m."""
    return (C * L) / (Hlp * (C + L))


def fator_manutencao(ambiente):
    """Fdl por ambiente (limpo/medio/sujo)."""
    try:
        return FATOR_MANUTENCAO[ambiente]
    except KeyError:
        raise ValueError("[A CONFIRMAR] ambiente '%s' sem fator de manutencao." % ambiente)


def fator_utilizacao_tms(K):
    """Fu de exemplo (Philips TMS, teto70/parede50/piso10) p/ K tabelado; senao
    FU_DEFAULT. Serve de default; o real vem do catalogo da luminaria adotada."""
    chaves = sorted(_FU_TMS)
    prox = min(chaves, key=lambda k: abs(k - K))
    return _FU_TMS[prox] if abs(prox - K) < 0.11 else FU_DEFAULT


def fluxo_total(E, A, Fu, Fdl):
    """Fluxo luminoso total necessario: phi = E*A/(Fu*Fdl) [lm]."""
    return E * A / (Fu * Fdl)


def numero_luminarias(E, A, fluxo_luminaria, Fu, Fdl):
    """Numero de luminarias (arredondado p/ cima): N = E*A/(fluxo_lum*Fu*Fdl).
    fluxo_luminaria = n_lampadas * fluxo_por_lampada (lm)."""
    return math.ceil(fluxo_total(E, A, Fu, Fdl) / fluxo_luminaria)


def projeto_luminotecnico(caso):
    """Projeto luminotecnico de um recinto pelo metodo dos lumens.
    caso: {C, L, (Hlp | pe_direito), (atividade | E), luminaria(nome ou dict),
           ambiente(=medio p/ Fdl), Fu(opc; senao TMS/default), h_plano(=0,85)}.
    Retorna E, A, K, Fu, Fdl, fluxo_total, N_luminarias, P_total_kW, densidade_W_m2."""
    C = float(caso["C"]); L = float(caso["L"])
    A = C * L
    if A <= 0:
        raise ValueError("[A CONFIRMAR] area do recinto invalida: C=%g x L=%g (deve ser > 0)." % (C, L))
    h_plano = float(caso.get("h_plano", 0.85))
    if "Hlp" in caso:
        Hlp = float(caso["Hlp"])
    else:
        Hlp = float(caso["pe_direito"]) - h_plano       # luminaria no teto
    K = indice_recinto(C, L, Hlp)
    E = float(caso["E"]) if caso.get("E") is not None else iluminancia_recomendada(caso["atividade"])
    Fdl = fator_manutencao(caso.get("ambiente", "medio"))
    Fu = float(caso["Fu"]) if caso.get("Fu") is not None else fator_utilizacao_tms(K)
    if Fu <= 0 or Fdl <= 0:
        raise ValueError("[A CONFIRMAR] fatores invalidos: Fu=%g, Fdl=%g (devem ser > 0)." % (Fu, Fdl))

    lum = caso.get("luminaria", "high_bay_led_100W")
    lum = LUMINARIAS[lum] if isinstance(lum, str) else lum
    fluxo_lum = lum["fluxo_lm"] * lum.get("n_lampadas", 1)
    N = numero_luminarias(E, A, fluxo_lum, Fu, Fdl)
    P_total_kW = N * lum["P_W"] * lum.get("n_lampadas", 1) / 1000.0
    return {"E_lux": E, "A_m2": A, "K": K, "Fu": Fu, "Fdl": Fdl,
            "fluxo_total_lm": fluxo_total(E, A, Fu, Fdl),
            "fluxo_luminaria_lm": fluxo_lum, "N_luminarias": N,
            "P_luminaria_W": lum["P_W"] * lum.get("n_lampadas", 1),
            "P_total_kW": P_total_kW, "densidade_W_m2": P_total_kW * 1000.0 / A,
            "OK": N > 0}


def _selftest():
    """Afere a formula do metodo dos lumens + as tabelas (valores do PDF)."""
    # niveis NBR (lidos da fonte)
    assert iluminancia_recomendada("montagem_media") == 500
    assert iluminancia_recomendada("armazem_volumes") == 200
    assert iluminancia_recomendada("circulacao") == 100
    # indice do recinto: galpao 40x20, Hlp=5 -> K = 800/(5*60) = 2,667
    assert abs(indice_recinto(40.0, 20.0, 5.0) - 2.6667) < 0.001
    # fatores
    assert fator_manutencao("limpo") == 0.80 and fator_manutencao("sujo") == 0.60
    # metodo dos lumens (deterministico): E=500, A=800, Fu=0,6, Fdl=0,7,
    # luminaria 13000 lm -> phi=952381 lm -> N=74
    assert abs(fluxo_total(500, 800, 0.6, 0.7) - 952380.95) < 1.0
    assert numero_luminarias(500, 800, 13000, 0.6, 0.7) == 74
    # projeto completo do galpao (armazem de grandes volumes, high-bay 100W)
    p = projeto_luminotecnico({"C": 40.0, "L": 20.0, "pe_direito": 6.0,
                               "atividade": "armazem_volumes", "ambiente": "medio",
                               "Fu": 0.60, "luminaria": "high_bay_led_100W"})
    assert p["E_lux"] == 200 and p["A_m2"] == 800.0
    assert p["Fdl"] == 0.70 and p["Fu"] == 0.60
    # N = 200*800/(13000*0,6*0,7) = 160000/5460 = 29,3 -> 30
    assert p["N_luminarias"] == 30, p["N_luminarias"]
    assert abs(p["P_total_kW"] - 3.0) < 1e-9              # 30 x 100 W
    print("luminotecnica_nbr8995 self-test PASSED (metodo dos lumens + NBR 8995)")


if __name__ == "__main__":
    _selftest()
