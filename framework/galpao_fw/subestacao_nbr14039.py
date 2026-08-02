# ============================================================================
# subestacao_nbr14039.py - O QUE ESTE SCRIPT FAZ / CALCULA
# ENTRADA DE ENERGIA e SUBESTACAO de consumidor em MEDIA TENSAO, 6a etapa do
# projeto eletrico. Base: Mamede Filho Cap.12 e ABNT NBR 14039:2021:
#   1) NECESSIDADE de MT: carga instalada/demanda > 75 kW obriga atendimento em
#      media tensao (subgrupo A4, 2,3..25 kV; 13,8 kV usual); > 2500 kW -> AT (>=69 kV).
#   2) TRANSFORMADOR: potencia nominal Sn = menor valor da serie padronizada ABNT
#      (classe 15 kV) >= demanda maxima (kVA). Impedancia z% tabelada por Sn.
#   3) CORRENTES nominais: Inp = Sn/(raiz(3)*Vnp) ; Ins = Sn/(raiz(3)*Vns).
#   4) PROTECAO GERAL de MT (NBR 14039 5.3.1): Sn <= 300 kVA -> chave seccionadora
#      + fusivel limitador HH (com disjuntor na BT) OU disjuntor MT c/ rele 50/51;
#      Sn > 300 kVA -> OBRIGATORIO disjuntor MT c/ reles secundarios 50/51 (F e N).
#      Fusivel HH: Inf ~ 1,5*Inp -> proximo padrao. Rele 51 (tape): (1,15..1,30)*Inp
#      (tipico 1,20*Inp).
# Serie de trafos, z%, limite de 75 kW, criterio de protecao 5.3.1 e o exemplo
# (D=210 kVA -> 225 kVA ; Inp=9,41 A @13,8 kV ; Ins=341,8 A @380 V) LIDOS do PDF de
# Mamede/NBR 14039 via NotebookLM - NAO de memoria.
# Unidades: Sn em kVA; V em kV; corrente em A. Saidas em portugues.
# ============================================================================
"""Subestacao de consumidor em MT (Mamede Cap.12 / NBR 14039): necessidade de MT,
transformador (serie ABNT), correntes nominais e protecao 50/51 ou fusivel HH."""

from __future__ import annotations

import math

LIMITE_BT_KW = 75.0        # acima disso -> media tensao (concessionaria)
LIMITE_MT_KW = 2500.0      # acima disso -> alta tensao (>= 69 kV)
V_PRIMARIA_USUAL_KV = 13.8

# serie padronizada ABNT de trafos trifasicos de distribuicao classe 15 kV (kVA)
SERIE_TRAFO_KVA = [15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000,
                   1500, 2000, 2500]
# impedancia percentual por potencia (Mamede Tab.12/9.x, classe 15 kV, 75C)
Z_TRAFO_PCT = {15: 3.5, 30: 3.5, 45: 3.5, 75: 3.5, 112.5: 3.5, 150: 3.5,
               225: 4.5, 300: 4.5, 500: 4.5, 750: 5.5, 1000: 5.5}
# serie de fusiveis limitadores HH (A)
FUSIVEL_HH_A = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200]

FATOR_FUSIVEL_HH = 1.5     # Inf ~ 1,5*Inp (Mamede Cap.9)
FATOR_RELE_51 = 1.20       # tape do 51: 1,20*Inp (faixa 1,15..1,30)
LIMITE_PROT_DISJUNTOR_KVA = 300.0   # NBR 14039 5.3.1


def exige_media_tensao(carga_kW):
    """Avalia a tensao de fornecimento pela carga instalada/demanda (kW)."""
    return {"carga_kW": carga_kW,
            "media_tensao": carga_kW > LIMITE_BT_KW,
            "alta_tensao": carga_kW > LIMITE_MT_KW,
            "nota": ("BT (<= 75 kW)" if carga_kW <= LIMITE_BT_KW else
                     "MT (13,8 kV usual)" if carga_kW <= LIMITE_MT_KW else
                     "AT (>= 69 kV)")}


def escolhe_transformador(D_kVA):
    """Menor Sn da serie ABNT >= demanda. Retorna (Sn, z%|None)."""
    for s in SERIE_TRAFO_KVA:
        if s >= D_kVA:
            return s, Z_TRAFO_PCT.get(s)
    return SERIE_TRAFO_KVA[-1], Z_TRAFO_PCT.get(SERIE_TRAFO_KVA[-1])


def corrente_nominal(Sn_kVA, V_kV):
    """Corrente nominal de linha: In = Sn/(raiz(3)*V). Sn kVA, V kV -> A."""
    return Sn_kVA / (math.sqrt(3.0) * V_kV)


def _proximo_fusivel_hh(Inf_calc):
    """Menor fusivel HH padrao >= valor calculado."""
    for f in FUSIVEL_HH_A:
        if f >= Inf_calc:
            return f
    return FUSIVEL_HH_A[-1]


def protecao_mt(Sn_kVA, Inp):
    """Define a protecao geral de MT (NBR 14039 5.3.1) por capacidade instalada."""
    if Sn_kVA > LIMITE_PROT_DISJUNTOR_KVA:
        return {"tipo": "disjuntor_rele", "funcoes": ["50", "51", "50N", "51N"],
                "rele_51_pickup_A": FATOR_RELE_51 * Inp,
                "obrigatorio_disjuntor": True}
    Inf = _proximo_fusivel_hh(FATOR_FUSIVEL_HH * Inp)
    return {"tipo": "chave_fusivel_HH", "fusivel_HH_A": Inf,
            "fusivel_HH_calc_A": FATOR_FUSIVEL_HH * Inp,
            "alt_disjuntor_rele": ["50", "51"], "obrigatorio_disjuntor": False,
            "nota": "disjuntor obrigatorio na BT quando se usa fusivel HH na MT"}


def dimensiona_subestacao(caso):
    """Projeta a entrada/subestacao de MT.
    caso: {D_kVA, carga_inst_kW(opc), V_primaria_kV(=13,8), V_secundaria_V(=380)}.
    Retorna trafo, correntes primaria/secundaria e protecao de MT."""
    D_kVA = float(caso["D_kVA"])
    carga_kW = float(caso.get("carga_inst_kW", D_kVA * 0.92))   # ~ P a fp 0,92
    Vp = float(caso.get("V_primaria_kV", V_PRIMARIA_USUAL_KV))
    Vs = float(caso.get("V_secundaria_V", 380.0))
    necess = exige_media_tensao(carga_kW)
    Sn, z = escolhe_transformador(D_kVA)
    Inp = corrente_nominal(Sn, Vp)
    Ins = corrente_nominal(Sn, Vs / 1000.0)
    prot = protecao_mt(Sn, Inp)
    return {"necessidade": necess, "Sn_kVA": Sn, "z_pct": z,
            "V_primaria_kV": Vp, "V_secundaria_V": Vs,
            "Inp_A": Inp, "Ins_A": Ins, "protecao": prot,
            "OK": necess["media_tensao"] and not necess["alta_tensao"]}


def _selftest():
    """Afere contra o exemplo de Mamede: D=210 kVA, 13,8/0,38 kV -> trafo 225 kVA,
    Inp=9,41 A, Ins=341,8 A; protecao por chave + fusivel HH (Sn<=300)."""
    assert exige_media_tensao(60.0)["media_tensao"] is False
    assert exige_media_tensao(200.0)["media_tensao"] is True
    assert exige_media_tensao(3000.0)["alta_tensao"] is True
    Sn, z = escolhe_transformador(210.0)
    assert Sn == 225 and z == 4.5
    r = dimensiona_subestacao({"D_kVA": 210.0, "V_primaria_kV": 13.8,
                               "V_secundaria_V": 380.0})
    assert r["Sn_kVA"] == 225
    assert abs(r["Inp_A"] - 9.41) < 0.02, r["Inp_A"]
    assert abs(r["Ins_A"] - 341.8) < 0.2, r["Ins_A"]
    assert r["protecao"]["tipo"] == "chave_fusivel_HH"
    assert r["protecao"]["fusivel_HH_A"] == 16          # 1,5*9,41=14,1 -> 16 A
    # Sn > 300 -> disjuntor obrigatorio com rele 50/51
    r2 = dimensiona_subestacao({"D_kVA": 450.0})
    assert r2["Sn_kVA"] == 500 and r2["protecao"]["tipo"] == "disjuntor_rele"
    assert "51" in r2["protecao"]["funcoes"]
    assert abs(r2["protecao"]["rele_51_pickup_A"] - 1.20 * r2["Inp_A"]) < 1e-9
    print("subestacao_nbr14039 self-test PASSED (Mamede D=210kVA -> 225kVA, Inp=9,41A)")


if __name__ == "__main__":
    _selftest()
