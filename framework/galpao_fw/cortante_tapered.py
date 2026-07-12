# ============================================================================
# cortante_tapered.py - Cortante da ALMA em barra de secao variavel (tapered).
# Numa barra de altura variavel, as mesas sao INCLINADAS em relacao ao eixo; a
# forca de mesa (binario que equilibra o momento) tem uma componente TRANSVERSAL
# que carrega parte da forca cortante aplicada. A alma, portanto, ve um cortante
# efetivo MENOR (quando a profundidade cresce no sentido de |M| crescente -
# caso haunch/joelho) ou MAIOR (geometria adversa).
#
# BASE: EQUILIBRIO (mecanica), NAO clausula da NBR 8800. O Anexo J (barras de
# secao variavel) tem apenas J.1 (aplicabilidade), J.2 (tracao), J.3 (compressao)
# e J.4 (momento/FLT) - NAO trata cortante. Por J.1.2, o que nao esta excetuado
# segue a Secao 5; logo o cortante segue 5.4.3 por secao (o verificador ja faz).
# Este modulo e um REFINO por equilibrio, nao uma citacao normativa.
#
# Derivacao (I duplo-simetrico, braco do binario ~ h_m):
#   forca de mesa  F = M / h_m
#   cada mesa inclina (dh/dx)/2 em relacao ao eixo; 2 mesas ->
#   componente transversal total = F * (dh/dx) = (M/h_m) * (dh/dx)
#   V_alma = V - (M/h_m)*(dh/dx)          (sinal pela geometria)
#
# POLITICA (calc assinado pelo senior; NBR silente):
#   - componente ADVERSA (aumenta o cortante da alma): SEMPRE contada (seguranca).
#   - componente FAVORAVEL (alivio): so creditada com opt-in explicito do
#     engenheiro (creditar=True); default = conservador (usa V cheio).
# Unidades SI: m, kN.
# ============================================================================
"""Cortante efetivo da alma em barra tapered (equilibrio). Unidades m, kN."""

from __future__ import annotations


def dh_dx(h1, h2, L_seg):
    """Gradiente de altura da alma ao longo do segmento (adimensional).
    h1, h2 = alturas nas extremidades (m); L_seg = comprimento do segmento (m)."""
    if L_seg <= 0.0:
        return 0.0
    return (h2 - h1) / L_seg


def _componente_mesa(M, h_m, dhdx):
    """Componente transversal das mesas inclinadas: (|M|/h_m)*|dh/dx| (kN)."""
    if h_m <= 0.0:
        return 0.0
    return (abs(M) / h_m) * abs(dhdx)


def v_alma_efetivo(M, V, h_m, dhdx, sentido=1):
    """Cortante efetivo da alma = V - sentido*(|M|/h_m)*|dh/dx|.
    sentido=+1: profundidade cresce onde |M| cresce -> ALIVIO (haunch/joelho).
    sentido=-1: geometria adversa -> ACRESCIMO. Retorna valor com o sinal de V."""
    comp = _componente_mesa(M, h_m, dhdx)
    s = 1 if sentido >= 0 else -1
    Vmag = abs(V) - s * comp
    return Vmag if V >= 0 else -Vmag


def cortante_efetivo_conservador(M, V, h_m, dhdx, sentido=1, creditar=False):
    """Cortante a USAR na verificacao 5.4.3, aplicando a politica de seguranca:
      - adverso (sentido<0): V_usar = max(|V|, |V_ef|) (sempre conta).
      - favoravel (sentido>=0): V_usar = |V_ef| se creditar, senao |V| (conservador).
    Retorna dict {V_usar, V_efetivo, alivio, acrescimo, creditado}."""
    Vef = v_alma_efetivo(M, V, h_m, dhdx, sentido)
    comp = _componente_mesa(M, h_m, dhdx)
    favoravel = sentido >= 0
    alivio = comp if favoravel else 0.0
    acrescimo = 0.0 if favoravel else comp
    if favoravel:
        V_usar = abs(Vef) if creditar else abs(V)
        creditado = bool(creditar and comp > 0.0)
    else:
        V_usar = max(abs(V), abs(Vef))
        creditado = False                          # adverso nao e "credito"
    return {"V_usar": V_usar, "V_efetivo": Vef, "alivio": alivio,
            "acrescimo": acrescimo, "creditado": creditado}


def sentido_haunch(segs):
    """Deriva o sentido (+1 haunch/alivio, -1 adverso) da GEOMETRIA do membro:
    +1 quando a secao de MAIOR |M| coincide com a de MAIOR altura (profundidade e
    momento co-crescem, caso joelho). Nao ha sinal fixo (mne-4). segs = lista de
    dicts com 'M' e 'h_m'."""
    valid = [s for s in segs if s.get("h_m")]
    if not valid:
        return 1
    s_maxM = max(valid, key=lambda s: abs(s.get("M", 0.0)))
    h_max = max(s["h_m"] for s in valid)
    return 1 if s_maxM["h_m"] >= 0.99 * h_max else -1


def _selftest():
    assert abs(dh_dx(0.60, 0.90, 3.0) - 0.10) < 1e-12
    # sentido: |M| maximo na secao mais funda -> +1 (haunch)
    assert sentido_haunch([{"M": 300.0, "h_m": 0.9}, {"M": 50.0, "h_m": 0.4}]) == 1
    assert sentido_haunch([{"M": 50.0, "h_m": 0.9}, {"M": 300.0, "h_m": 0.4}]) == -1
    assert dh_dx(0.50, 0.50, 3.0) == 0.0
    # haunch alivia
    assert abs(v_alma_efetivo(300.0, 200.0, 0.9, 0.10, +1)) < 200.0
    # prismatico e M=0 nao mudam
    assert v_alma_efetivo(300.0, 200.0, 0.9, 0.0, +1) == 200.0
    assert v_alma_efetivo(0.0, 200.0, 0.9, 0.10, +1) == 200.0
    # adverso aumenta
    assert abs(v_alma_efetivo(300.0, 200.0, 0.9, 0.10, -1)) > 200.0
    # politica conservadora
    rf = cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, +1, creditar=False)
    assert rf["V_usar"] == 200.0 and rf["alivio"] > 0.0 and not rf["creditado"]
    rc = cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, +1, creditar=True)
    assert rc["V_usar"] < 200.0 and rc["creditado"]
    ra = cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.10, -1, creditar=False)
    assert ra["V_usar"] > 200.0 and ra["acrescimo"] > 0.0
    rp = cortante_efetivo_conservador(300.0, 200.0, 0.9, 0.0, +1, creditar=True)
    assert rp["V_usar"] == 200.0 and rp["alivio"] == 0.0
    print("cortante_tapered self-test PASSED")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
