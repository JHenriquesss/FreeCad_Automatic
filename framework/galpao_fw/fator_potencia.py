# ============================================================================
# fator_potencia.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Correcao do FATOR DE POTENCIA de uma instalacao industrial, 5a etapa do projeto
# eletrico. Base: Mamede Filho, Cap.4 (correcao de fator de potencia):
#   - potencia reativa capacitiva necessaria: Qc = P*(tan(phi1) - tan(phi2)) [kVAr]
#     com phi = arccos(FP); phi1 = fator atual, phi2 = fator desejado.
#   - limite regulamentar minimo: FP >= 0,92 (indutivo ou capacitivo), abaixo do
#     qual ha faturamento de reativo excedente.
# Formula e o limite 0,92 LIDOS do PDF de Mamede via NotebookLM - NAO de memoria.
# Aferido contra o exercicio de revisao (P=500 kW, FP 0,65 -> 0,90).
# Unidades: potencia ativa em kW; reativa em kVAr; FP adimensional.
# ============================================================================
"""Correcao de fator de potencia (Mamede Cap.4): banco de capacitores
Qc = P*(tan phi1 - tan phi2) e verificacao do limite FP >= 0,92."""

from __future__ import annotations

import math

FP_MINIMO = 0.92          # limite regulamentar (indutivo/capacitivo)


def _tan_de_fp(fp):
    """tan(phi) a partir do fator de potencia FP = cos(phi)."""
    return math.tan(math.acos(fp))


def potencia_reativa_capacitiva(P_kW, fp1, fp2=FP_MINIMO):
    """Qc = P*(tan phi1 - tan phi2) [kVAr] para elevar o FP de fp1 para fp2."""
    return P_kW * (_tan_de_fp(fp1) - _tan_de_fp(fp2))


def corrige_fator_potencia(P_kW, fp_atual, fp_alvo=FP_MINIMO):
    """Dimensiona o banco de capacitores. Retorna {Qc_kVAr, fp_atual, fp_alvo,
    precisa_corrigir, OK}. precisa_corrigir=True se fp_atual < 0,92."""
    precisa = fp_atual < FP_MINIMO
    Qc = potencia_reativa_capacitiva(P_kW, fp_atual, fp_alvo) if precisa else 0.0
    return {"P_kW": P_kW, "fp_atual": fp_atual, "fp_alvo": fp_alvo,
            "Qc_kVAr": Qc, "precisa_corrigir": precisa,
            "OK": fp_atual >= FP_MINIMO or Qc > 0.0}


def _selftest():
    """Afere a formula contra o exercicio de revisao de Mamede (P=500 kW,
    FP 0,65 atrasado -> 0,90)."""
    Qc = potencia_reativa_capacitiva(500.0, 0.65, 0.90)
    # tan(acos0,65)=1,1691 ; tan(acos0,90)=0,4843 ; 500*(1,1691-0,4843)=342,4
    assert abs(Qc - 342.4) < 1.0, Qc
    r = corrige_fator_potencia(500.0, 0.65, 0.90)
    assert r["precisa_corrigir"] and abs(r["Qc_kVAr"] - 342.4) < 1.0
    # ja acima de 0,92 -> nao corrige
    r2 = corrige_fator_potencia(500.0, 0.95)
    assert not r2["precisa_corrigir"] and r2["Qc_kVAr"] == 0.0 and r2["OK"]
    # elevar exatamente ao minimo 0,92
    Qc92 = potencia_reativa_capacitiva(100.0, 0.80)
    assert Qc92 > 0.0
    print("fator_potencia self-test PASSED (Mamede P=500kW 0,65->0,90 = 342 kVAr)")


if __name__ == "__main__":
    _selftest()
