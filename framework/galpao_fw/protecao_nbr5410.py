# ============================================================================
# protecao_nbr5410.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Especifica o dispositivo de PROTECAO (disjuntor) de um circuito e indica DR/DPS,
# ABNT NBR 5410:2004, 4a etapa do projeto eletrico:
#   1) PROTECAO CONTRA SOBRECARGA (5.3.4.1): coordenacao condutor x disjuntor
#      a) IB <= IN <= IZ ; b) I2 <= 1,45*IZ. Para disjuntores I2 = 1,45*IN, logo se
#      IN <= IZ a condicao (b) e satisfeita automaticamente. Escolhe o menor IN da
#      serie comercial (NBR IEC 60898/60947-2) que atenda IB <= IN <= IZ.
#   2) CAPACIDADE DE INTERRUPCAO (5.3.5): Icu do disjuntor >= Icc presumida na barra.
#   3) DR (5.1.3.2.2): protecao complementar contra choque, In(dif) <= 30 mA em
#      circuitos de tomadas/areas molhadas.
#   4) DPS (6.3.5.2 / NBR 5419-4): classe I (onda 10/350 us) no ponto de entrada de
#      edificacao sujeita a descarga direta / rede aerea; classe II (8/20 us) nos
#      quadros; classe III junto a equipamentos sensiveis.
# Condicoes e valores LIDOS do PDF da NBR 5410 e de Creder/NBR 5419 via NotebookLM -
# NAO de memoria. Aferido contra o exercicio do chuveiro (IB=27,27 A, IZ=41 A ->
# disjuntor de 32 A).
# Unidades: correntes em A. Saidas em portugues.
# ============================================================================
"""Protecao de circuito BT (NBR 5410): coordenacao disjuntor x condutor
(IB<=IN<=IZ, I2<=1,45*IZ), capacidade de interrupcao, DR e classe de DPS."""

from __future__ import annotations

# serie comercial de correntes nominais de disjuntor (NBR IEC 60898 / 60947-2), A
IN_DISJUNTORES = [6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 70, 80, 100, 125, 160,
                  200, 250, 320, 400, 500, 630, 800, 1000, 1250, 1600, 2000]

# fator da corrente convencional de atuacao do disjuntor: I2 = 1,45*IN
FATOR_I2 = 1.45
LIMITE_I2_IZ = 1.45          # I2 <= 1,45*IZ (5.3.4.1 b)
IN_DR_MA = 30.0             # corrente diferencial-residual p/ protecao de pessoas (mA)


def dimensiona_disjuntor(IB, IZ, Icc=None):
    """Escolhe o menor disjuntor da serie com IB <= IN <= IZ e verifica as duas
    condicoes de 5.3.4.1. Icc (se dado) verifica a capacidade de interrupcao.
    Retorna dict com IN, verificacoes e OK."""
    candidatos = [i for i in IN_DISJUNTORES if IB <= i <= IZ]
    IN = candidatos[0] if candidatos else None
    cond_a = IN is not None and (IB <= IN <= IZ)
    I2 = FATOR_I2 * IN if IN is not None else None
    cond_b = IN is not None and (I2 <= LIMITE_I2_IZ * IZ)   # sempre True se IN<=IZ
    ok_interrupcao = True if Icc is None else (IN is not None)  # so informativo aqui
    return {"IB": IB, "IZ": IZ, "IN": IN, "I2": I2,
            "cond_IB_IN_IZ": cond_a, "cond_I2_145IZ": cond_b,
            "Icc_barra": Icc, "OK": bool(cond_a and cond_b)}


def verifica_capacidade_interrupcao(Icu_disjuntor, Icc_barra):
    """Capacidade de interrupcao (5.3.5): Icu do disjuntor >= Icc presumida."""
    return {"Icu": Icu_disjuntor, "Icc": Icc_barra, "OK": Icu_disjuntor >= Icc_barra}


def requer_dr(circ):
    """Indica DR de alta sensibilidade (<=30 mA) quando o circuito e de tomadas,
    area molhada/externa ou alimenta equipamento em local de risco (5.1.3.2.2)."""
    uso = circ.get("uso", "")
    local = circ.get("local", "")
    gatilho = (uso in ("tomadas", "forca") or
               local in ("molhado", "externo", "banheiro", "cozinha", "area_externa"))
    return {"requer_DR": bool(gatilho), "In_dif_mA": IN_DR_MA if gatilho else None}


def classe_dps(exposicao):
    """Classe de DPS recomendada por exposicao a descargas atmosfericas (NBR 5419-4):
      - 'direta'/'rede_aerea' -> Classe I (onda 10/350 us) no ponto de entrada;
      - 'indireta'/'quadro'   -> Classe II (8/20 us) nos quadros;
      - 'equipamento_sensivel'-> Classe III junto ao equipamento."""
    mapa = {
        "direta": ("I", "10/350 us", "ponto de entrada da edificacao"),
        "rede_aerea": ("I", "10/350 us", "ponto de entrada da edificacao"),
        "indireta": ("II", "8/20 us", "quadro de distribuicao"),
        "quadro": ("II", "8/20 us", "quadro de distribuicao"),
        "equipamento_sensivel": ("III", "1,2/50 - 8/20 us", "junto ao equipamento"),
    }
    if exposicao not in mapa:
        raise ValueError("[A CONFIRMAR] exposicao '%s' nao mapeada para DPS." % exposicao)
    cls, onda, local = mapa[exposicao]
    return {"classe": cls, "onda_ensaio": onda, "local": local}


def dimensiona_protecao(circ):
    """Protecao completa de um circuito. circ: {IB, IZ, Icc(opc), Icu(opc),
    uso, local, exposicao_dps(opc)}. Retorna disjuntor + DR + DPS."""
    dj = dimensiona_disjuntor(float(circ["IB"]), float(circ["IZ"]), circ.get("Icc"))
    if circ.get("Icc") is not None and circ.get("Icu") is not None:
        dj["interrupcao"] = verifica_capacidade_interrupcao(float(circ["Icu"]),
                                                            float(circ["Icc"]))
        dj["OK"] = dj["OK"] and dj["interrupcao"]["OK"]
    dr = requer_dr(circ)
    dps = classe_dps(circ["exposicao_dps"]) if circ.get("exposicao_dps") else None
    return {"disjuntor": dj, "dr": dr, "dps": dps, "OK": dj["OK"]}


def _selftest():
    """Afere contra o circuito do chuveiro (IB=27,27 A, IZ=41 A p/ 6mm2 B1)."""
    r = dimensiona_disjuntor(27.27, 41.0)
    assert r["IN"] == 32, r["IN"]                     # menor da serie com 27,27<=IN<=41
    assert r["cond_IB_IN_IZ"] and r["cond_I2_145IZ"]
    assert abs(r["I2"] - 1.45 * 32) < 1e-9
    assert r["OK"]
    # sem disjuntor possivel se IB > IZ (condutor subdimensionado)
    r2 = dimensiona_disjuntor(50.0, 41.0)
    assert r2["IN"] is None and not r2["OK"]
    # capacidade de interrupcao
    ci = verifica_capacidade_interrupcao(10000.0, 9116.0)
    assert ci["OK"]
    assert not verifica_capacidade_interrupcao(5000.0, 9116.0)["OK"]
    # DPS por exposicao
    assert classe_dps("direta")["classe"] == "I"
    assert classe_dps("quadro")["classe"] == "II"
    # DR em tomadas
    assert requer_dr({"uso": "tomadas"})["requer_DR"]
    assert requer_dr({"uso": "iluminacao", "local": "seco"})["requer_DR"] is False
    print("protecao_nbr5410 self-test PASSED (chuveiro -> disjuntor 32 A + DR/DPS)")


if __name__ == "__main__":
    _selftest()
