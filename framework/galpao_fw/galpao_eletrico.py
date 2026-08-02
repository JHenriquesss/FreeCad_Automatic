# ============================================================================
# galpao_eletrico.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Orquestra o PROJETO ELETRICO de baixa tensao de um galpao industrial (nucleo BT),
# reaproveitando os modulos de calculo agnosticos ja implementados:
#   - cargas_eletricas      (Mamede Cap.1 / NBR 5410 4.2.1): quadro de cargas e demanda;
#   - condutores_nbr5410    (NBR 5410): alimentador e circuitos pelos 3 criterios;
#   - curto_circuito        (Mamede Cap.5): Icc presumida na barra do QGF;
#   - protecao_nbr5410      (NBR 5410): disjuntor geral (IB<=IN<=IZ) + DR/DPS;
#   - fator_potencia        (Mamede Cap.4): banco de capacitores p/ FP>=0,92;
#   - subestacao_nbr14039   (NBR 14039): entrada/subestacao em MT (se > 75 kW);
#   - aterramento_nbr15749  (NBR 15749): resistividade/resistencia do aterramento;
#   - spda_nbr5419          (NBR 5419): gerenciamento de risco e projeto do SPDA.
# STATELESS por design: rodar(spec) recebe um dict explicito (sem estado global -
# evita a classe de bug _CFG). Dados de concessionaria/trafo (Sn, z%, demanda
# contratada) e comprimentos de alimentador marcados A CONFIRMAR - nunca inventados.
# Unidades: potencia em kW/kVA; tensao em V; corrente em A; comprimento em km.
# Saidas em portugues. gates -> ATENDE/REPROVA como nos verticais de aco/concreto.
# ============================================================================
"""Projeto eletrico BT de galpao industrial (NBR 5410 / Mamede). Orquestrador
STATELESS: rodar(spec) -> gates ATENDE/REPROVA."""

from __future__ import annotations

import math

import cargas_eletricas as ce
import condutores_nbr5410 as cd
import curto_circuito as cc
import protecao_nbr5410 as pr
import fator_potencia as fp
import aterramento_nbr15749 as at
import spda_nbr5419 as spda
import subestacao_nbr14039 as se

# serie comercial de transformadores de distribuicao ABNT (kVA)
TRAFOS_KVA = [45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 2000]
FP_ALVO = fp.FP_MINIMO             # 0,92


def _corrente_trifasica(S_kVA, V):
    """Corrente de linha de uma potencia aparente trifasica: I = S/(raiz(3)*V)."""
    return S_kVA * 1000.0 / (math.sqrt(3.0) * V)


def _escolhe_trafo(D_kVA):
    """Menor trafo padrao ABNT com Sn >= demanda aparente (informativo)."""
    for s in TRAFOS_KVA:
        if s >= D_kVA:
            return s
    return TRAFOS_KVA[-1]


def rodar(spec):
    """Dimensiona o nucleo BT do galpao industrial e devolve os gates.
    spec: {
      'tensao_V'   : tensao de linha (V), default 380 (trifasico).
      'sistema'    : 'trifasico' (default) | 'monofasico'.
      'cargas'     : ver cargas_eletricas.quadro_de_cargas (motores, iluminacao...).
      'alimentador': {L_km, metodo('B1'|'F'), isolacao('PVC'|'EPR'), temp_amb,
                      n_agrupados, fp} - trecho trafo/entrada -> QGF [L_km A CONFIRMAR].
      'transformador': {Sn_kVA, z_pct} (opc.) -> habilita a Icc na barra do QGF.
      'origem'     : 'rede_publica'(5%) | 'subestacao_propria'(7%) - limite de queda.
      'fp_desejado': default 0,92.
      'circuitos'  : lista opcional de circuitos terminais p/ dimensionar (cada um
                     no formato de condutores_nbr5410.dimensiona_condutor + protecao).
    }"""
    V = float(spec.get("tensao_V", 380.0))
    sistema = spec.get("sistema", "trifasico")
    origem = spec.get("origem", "rede_publica")

    # -------------------------------------------------- 1) CARGAS / DEMANDA
    qc = ce.quadro_de_cargas(spec)
    D_kW = qc["D_kW"]; D_kVA = qc["D_kVA"]; fp_result = qc["fp_resultante"]

    # -------------------------------------------------- 2) ALIMENTADOR (QGF)
    al = dict(spec.get("alimentador", {}))
    IB = _corrente_trifasica(D_kVA, V) if sistema == "trifasico" else (D_kVA * 1000.0 / V)
    circ_al = {"IB": IB, "V": V, "L_km": al.get("L_km", 0.0),
               "sistema": sistema, "n_cond": 3 if sistema == "trifasico" else 2,
               "isolacao": al.get("isolacao", "EPR"), "metodo": al.get("metodo", "F"),
               "fp": al.get("fp", fp_result if fp_result > 0 else 0.80),
               "temp_amb": al.get("temp_amb", 30.0),
               "n_agrupados": al.get("n_agrupados", 1), "uso": "forca",
               "origem": origem}
    alimentador = cd.dimensiona_condutor(circ_al)

    # ------------------------------------------- 2b) SUBESTACAO / ENTRADA MT
    # aciona quando a carga instalada/demanda supera 75 kW (NBR 14039 / concessionaria).
    subest = None
    if qc["P_inst_kW"] > se.LIMITE_BT_KW or D_kVA * 0.92 > se.LIMITE_BT_KW:
        subest = se.dimensiona_subestacao({
            "D_kVA": D_kVA, "carga_inst_kW": qc["P_inst_kW"],
            "V_primaria_kV": spec.get("V_primaria_kV", se.V_PRIMARIA_USUAL_KV),
            "V_secundaria_V": V})

    # -------------------------------------------------- 3) CURTO na barra QGF
    # usa o trafo explicito; se ausente, cai no trafo escolhido pela subestacao.
    trafo = spec.get("transformador")
    if trafo and trafo.get("Sn_kVA") and trafo.get("z_pct"):
        icc = cc.icc_simetrica(float(trafo["Sn_kVA"]), V / 1000.0, float(trafo["z_pct"]))
        Icc_barra = icc["Ik3"]
    elif subest and subest.get("z_pct"):
        icc = cc.icc_simetrica(subest["Sn_kVA"], V / 1000.0, subest["z_pct"])
        Icc_barra = icc["Ik3"]
    else:
        icc = None
        Icc_barra = None                      # depende do trafo/concessionaria (A CONFIRMAR)

    # -------------------------------------------------- 4) PROTECAO GERAL
    IZ = alimentador["Iz"] or 0.0
    prot = pr.dimensiona_protecao({"IB": IB, "IZ": IZ, "Icc": Icc_barra,
                                   "Icu": spec.get("Icu_geral"), "uso": "forca",
                                   "exposicao_dps": spec.get("exposicao_dps", "indireta")})

    # -------------------------------------------------- 5) FATOR DE POTENCIA
    fp_desejado = float(spec.get("fp_desejado", FP_ALVO))
    corr_fp = fp.corrige_fator_potencia(D_kW, fp_result if fp_result > 0 else 0.80,
                                        fp_desejado)

    # -------------------------------------------- CIRCUITOS TERMINAIS (opc.)
    circuitos = []
    for c in spec.get("circuitos", []):
        cond = cd.dimensiona_condutor(c)
        pcirc = pr.dimensiona_protecao({"IB": c["IB"], "IZ": cond["Iz"] or 0.0,
                                        "Icc": Icc_barra, "uso": c.get("uso", "forca"),
                                        "local": c.get("local", ""),
                                        "exposicao_dps": c.get("exposicao_dps")})
        circuitos.append({"nome": c.get("nome", "circuito"), "condutor": cond,
                          "protecao": pcirc, "OK": cond["OK"] and pcirc["OK"]})
    circuitos_ok = all(x["OK"] for x in circuitos) if circuitos else True

    # -------------------------------------------------- 6) ATERRAMENTO
    # exige resistividade do solo MEDIDA (Wenner, NBR 15749) - dado de sitio.
    at_spec = spec.get("aterramento")
    aterr = None
    if at_spec and at_spec.get("rho") is not None:
        aterr = at.dimensiona_aterramento(at_spec)

    # -------------------------------------------------- 7) SPDA (NBR 5419)
    # geometria do galpao: L=comprimento, W=vao (largura), H=pe-direito.
    geo = spec.get("geometria")
    spda_res = None
    if geo and all(k in geo for k in ("L", "W", "H")):
        spda_res = spda.dimensiona_spda({
            "L": geo["L"], "W": geo["W"], "H": geo["H"],
            "NP": spec.get("spda", {}).get("NP"),
            "Ng": spec.get("spda", {}).get("Ng"),
            "Cd": spec.get("spda", {}).get("Cd", 1.0),
            "R1": spec.get("spda", {}).get("R1")})

    # -------------------------------------------------- INFO: trafo sugerido
    trafo_sugerido = _escolhe_trafo(D_kVA)

    # --------------------------------------------------------------- GATES
    gates = {
        "cargas": {"P_inst_kW": round(qc["P_inst_kW"], 1), "D_kW": round(D_kW, 1),
                   "D_kVA": round(D_kVA, 1), "fp_resultante": round(fp_result, 3),
                   "trafo_sugerido_kVA": trafo_sugerido, "OK": qc["OK"]},
        "alimentador": {"secao_mm2": alimentador["secao_mm2"],
                        "IB": round(IB, 1), "Iz": alimentador["Iz"],
                        "governante": alimentador["governante"],
                        "dv_pct": round(alimentador["dv_pct"], 2) if alimentador["dv_pct"] else None,
                        "isolacao": alimentador["isolacao"], "metodo": alimentador["metodo"],
                        "OK": alimentador["OK"]},
        "curto": {"Icc_kA": round(Icc_barra / 1000.0, 2) if Icc_barra else None,
                  "nota": "" if Icc_barra else "A CONFIRMAR: exige Sn e z% do trafo",
                  "OK": True},
        "protecao": {"IN_geral_A": prot["disjuntor"]["IN"],
                     "dps_classe": prot["dps"]["classe"] if prot["dps"] else None,
                     "OK": prot["OK"]},
        "fator_potencia": {"fp_atual": round(fp_result, 3), "fp_alvo": fp_desejado,
                           "Qc_kVAr": round(corr_fp["Qc_kVAr"], 1),
                           "precisa_corrigir": corr_fp["precisa_corrigir"], "OK": True},
        "circuitos": {"n": len(circuitos), "OK": circuitos_ok},
        "aterramento": {"R_ohm": round(aterr["R_ohm"], 2) if aterr else None,
                        "limite_ohm": aterr["limite_ohm"] if aterr else at.R_MAX_SPDA,
                        "nota": "" if aterr else "A CONFIRMAR: exige rho medido (Wenner/NBR 15749)",
                        "OK": aterr["OK"] if aterr else True},
        "subestacao": {"necessaria": bool(subest), "Sn_kVA": subest["Sn_kVA"] if subest else None,
                       "Inp_A": round(subest["Inp_A"], 2) if subest else None,
                       "protecao": subest["protecao"]["tipo"] if subest else None,
                       "nota": "" if subest else "carga <= 75 kW: atendimento em BT",
                       "OK": subest["OK"] if subest else True},
        "spda": {"NP": spda_res["NP"] if spda_res else None,
                 "n_descidas": spda_res["n_descidas"] if spda_res else None,
                 "Nd_ano": round(spda_res["Nd_ano"], 5) if (spda_res and spda_res["Nd_ano"]) else None,
                 "nota": "" if spda_res else "A CONFIRMAR: exige geometria e estudo de risco (NBR 5419-2)",
                 "OK": spda_res["OK"] if spda_res else True},
    }
    res = {"spec": {"tensao_V": V, "sistema": sistema, "origem": origem},
           "geometria": geo, "cargas": qc, "alimentador": alimentador, "curto": icc,
           "protecao": prot, "fator_potencia": corr_fp, "circuitos": circuitos,
           "subestacao": subest, "aterramento": aterr, "spda": spda_res,
           "trafo_sugerido_kVA": trafo_sugerido, "gates": gates}
    reprovados = [k for k, g in gates.items() if not g["OK"]]
    res["reprovados"] = reprovados
    res["ATENDE"] = len(reprovados) == 0
    return res


def relatorio_pt(r):
    """Relatorio textual do nucleo BT (decimais com virgula)."""
    g = r["gates"]
    L = ["PROJETO ELETRICO BT - GALPAO INDUSTRIAL (NBR 5410 / Mamede)",
         f"  Cargas: P inst = {g['cargas']['P_inst_kW']} kW ; "
         f"Demanda = {g['cargas']['D_kW']} kW / {g['cargas']['D_kVA']} kVA ; "
         f"FP = {g['cargas']['fp_resultante']} ; trafo sugerido "
         f"{g['cargas']['trafo_sugerido_kVA']} kVA [A CONFIRMAR demanda/concessionaria]",
         f"  Alimentador QGF: {g['alimentador']['secao_mm2']} mm2 "
         f"({g['alimentador']['isolacao']}, metodo {g['alimentador']['metodo']}) ; "
         f"IB = {g['alimentador']['IB']} A ; Iz = {g['alimentador']['Iz']} A ; "
         f"queda = {g['alimentador']['dv_pct']}% ; governa: {g['alimentador']['governante']}",
         f"  Curto no QGF: "
         + (f"Icc = {g['curto']['Icc_kA']} kA" if g['curto']['Icc_kA'] else g['curto']['nota']),
         f"  Protecao geral: disjuntor {g['protecao']['IN_geral_A']} A ; "
         f"DPS classe {g['protecao']['dps_classe']}",
         f"  Fator de potencia: {g['fator_potencia']['fp_atual']} -> "
         f"{g['fator_potencia']['fp_alvo']} ; banco = {g['fator_potencia']['Qc_kVAr']} kVAr "
         + ("(necessario)" if g['fator_potencia']['precisa_corrigir'] else "(dispensavel)"),
         f"  Subestacao: "
         + (f"trafo {g['subestacao']['Sn_kVA']} kVA ; Inp = {g['subestacao']['Inp_A']} A "
            f"(13,8 kV) ; protecao {g['subestacao']['protecao']}"
            if g['subestacao']['necessaria'] else g['subestacao']['nota']),
         f"  Aterramento: "
         + (f"R = {g['aterramento']['R_ohm']} ohm (limite {g['aterramento']['limite_ohm']})"
            if g['aterramento']['R_ohm'] is not None else g['aterramento']['nota']),
         f"  SPDA: "
         + (f"NP {g['spda']['NP']} ; {g['spda']['n_descidas']} descidas"
            if g['spda']['NP'] else g['spda']['nota']),
         f"  RESULTADO: {'ATENDE' if r['ATENDE'] else 'REPROVA - ' + ', '.join(r['reprovados'])}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _pontos_perimetro(L, W, n):
    """n pontos igualmente espacados ao longo do perimetro do retangulo LxW (mm),
    comecando no canto (0,0). Usado p/ posicionar as descidas do SPDA."""
    P = 2.0 * (L + W)
    passo = P / n
    pts = []
    for i in range(n):
        d = i * passo
        if d <= L:
            pts.append((d, 0.0))
        elif d <= L + W:
            pts.append((L, d - L))
        elif d <= 2 * L + W:
            pts.append((L - (d - L - W), W))
        else:
            pts.append((0.0, W - (d - 2 * L - W)))
    return pts


def membros_bim(r):
    """Modelo neutro dos elementos FISICOS do projeto eletrico para ifc_emit.
    Convencao (igual aos demais verticais): COORDENADAS em mm; secao de BARRA em m;
    dims de CAIXA em mm. Eixos: X = comprimento (L), Y = largura/vao (W), Z = altura.
    Requer r['geometria'] {L,W,H} (m). Emite: QGF e transformador (caixas), eletrocalha
    principal (bandeja), anel de aterramento + hastes de canto, captacao SPDA no
    perimetro do telhado + descidas. Mapeamento IFC via ifc_emit._IFC_CLASS
    (IfcCableCarrierSegment / IfcCableSegment / IfcDistributionBoard / IfcTransformer)."""
    geo = r.get("geometria")
    if not geo or not all(k in geo for k in ("L", "W", "H")):
        return []
    L = geo["L"] * 1000.0; W = geo["W"] * 1000.0; H = geo["H"] * 1000.0   # mm
    CU = "Cobre"; ACO = "Aco galvanizado"
    membros = []

    # QGF (quadro geral de forca): caixa no piso, junto a uma parede
    membros.append({"tipo": "Board", "perfil": "QGF", "marca": "QGF",
                    "dims": [800.0, 300.0, 2000.0], "centro": [1000.0, 300.0, 1000.0],
                    "material": "Aco"})
    # transformador da subestacao (se houver)
    if r.get("subestacao"):
        Sn = r["subestacao"]["Sn_kVA"]
        membros.append({"tipo": "Transformer", "perfil": "TRAFO %gkVA" % Sn,
                        "marca": "TR1", "dims": [1500.0, 1300.0, 1700.0],
                        "centro": [-1500.0, 700.0, 850.0], "material": "Aco"})
    # eletrocalha principal: corre no comprimento, sob o beiral (z = H - 500 mm)
    ze = H - 500.0
    membros.append({"tipo": "CableCarrier", "perfil": "Bandeja 100x50", "marca": "CALHA-P",
                    "secao": {"forma": "RECT", "bf": 0.10, "d": 0.05},
                    "p1": [0.0, W / 2.0, ze], "p2": [L, W / 2.0, ze], "material": "Aco"})

    # --- ATERRAMENTO: anel no perimetro, enterrado (z = -500 mm) + hastes de canto ---
    zg = -500.0
    anel = [([0.0, 0.0, zg], [L, 0.0, zg]), ([L, 0.0, zg], [L, W, zg]),
            ([L, W, zg], [0.0, W, zg]), ([0.0, W, zg], [0.0, 0.0, zg])]
    for i, (a, b) in enumerate(anel, 1):
        membros.append({"tipo": "Earthing", "perfil": "Cabo terra 50mm2",
                        "marca": "MALHA%d" % i, "secao": {"forma": "ROUND", "D": 0.008},
                        "p1": a, "p2": b, "material": CU})
    for i, (x, y) in enumerate([(0.0, 0.0), (L, 0.0), (L, W), (0.0, W)], 1):
        membros.append({"tipo": "Earthing", "perfil": "Haste 3m", "marca": "HASTE%d" % i,
                        "secao": {"forma": "ROUND", "D": 0.016},
                        "p1": [x, y, zg], "p2": [x, y, zg - 3000.0], "material": ACO})

    # --- SPDA: captacao no perimetro do telhado (z = H) + descidas nas colunas ---
    spda_res = r.get("spda")
    if spda_res and spda_res.get("n_descidas"):
        capt = [([0.0, 0.0, H], [L, 0.0, H]), ([L, 0.0, H], [L, W, H]),
                ([L, W, H], [0.0, W, H]), ([0.0, W, H], [0.0, 0.0, H])]
        for i, (a, b) in enumerate(capt, 1):
            membros.append({"tipo": "Cable", "perfil": "Captor 35mm2", "marca": "CAPT%d" % i,
                            "secao": {"forma": "ROUND", "D": 0.008},
                            "p1": a, "p2": b, "material": CU})
        for i, (x, y) in enumerate(_pontos_perimetro(L, W, spda_res["n_descidas"]), 1):
            membros.append({"tipo": "Cable", "perfil": "Descida 16mm2", "marca": "DESC%d" % i,
                            "secao": {"forma": "ROUND", "D": 0.016},
                            "p1": [x, y, H], "p2": [x, y, zg], "material": CU})
    return membros


def emitir_bim(r, path, nome="GalpaoEletrico"):
    """Emite o IFC4 dos elementos eletricos (via ifc_emit puro). None se sem geometria
    ou sem ifcopenshell."""
    import ifc_emit
    if not ifc_emit.disponivel():
        return None
    membros = membros_bim(r)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(membros, path, nome=nome, secao_em_metros=True)


def _selftest():
    """Roda um galpao industrial de exemplo (motores + iluminacao) e confere o
    encadeamento cargas -> alimentador -> protecao -> FP."""
    spec = {"tensao_V": 380.0, "sistema": "trifasico", "origem": "subestacao_propria",
            "cargas": {"motores": [{"P_cv": 75.0, "eta": 0.92, "Fp": 0.86, "n": 2},
                                   {"P_cv": 30.0, "eta": 0.90, "Fp": 0.86, "n": 3}],
                       "iluminacao_kW": 20.0, "ilum_fp": 0.92, "ocupacao": "industrial"},
            "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR",
                            "temp_amb": 40.0, "n_agrupados": 1},
            "transformador": {"Sn_kVA": 300.0, "z_pct": 4.5},
            "fp_desejado": 0.92,
            "geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "spda": {"NP": "III", "Ng": 5.0, "R1": 2e-5},
            "aterramento": {"tipo": "malha", "rho": 100.0, "A": 800.0, "L_cond": 400.0}}
    r = rodar(spec)
    g = r["gates"]
    assert g["cargas"]["D_kVA"] > 0 and g["cargas"]["OK"]
    assert g["cargas"]["trafo_sugerido_kVA"] in TRAFOS_KVA
    assert g["alimentador"]["secao_mm2"] is not None and g["alimentador"]["OK"]
    assert abs(g["curto"]["Icc_kA"] - 10.13) < 0.1        # trafo 300kVA/4,5% (Mamede)
    assert g["protecao"]["IN_geral_A"] is not None
    assert g["protecao"]["dps_classe"] == "II"            # exposicao default 'indireta'
    assert g["spda"]["NP"] == "III" and g["spda"]["n_descidas"] == 8
    assert g["aterramento"]["R_ohm"] is not None
    assert g["subestacao"]["necessaria"] and g["subestacao"]["Sn_kVA"] == 225
    assert isinstance(r["ATENDE"], bool)
    print(relatorio_pt(r))
    print("galpao_eletrico self-test PASSED")


if __name__ == "__main__":
    _selftest()
