# ============================================================================
# test_estaca_ponta.py - a resistencia de PONTA da estaca (Aoki/Decourt/Teixeira)
# deve usar o N-SPT da camada NA PROFUNDIDADE DA PONTA (L), nao a ultima camada do
# perfil. Bug contra-seguranca (caca sessao 14): estaca curta com a ponta numa
# camada mole, mas o perfil descendo ate uma camada forte (areia densa), usava o N
# da camada FORTE (abaixo da estaca) -> R_ponta e P_adm SUPERESTIMADOS -> estaca
# subdimensionada CERTIFICADA. Todos os 3 metodos afetados.
# ============================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import estaca_profunda as EP

# 5 m de argila MOLE (N=3) sobre 10 m de areia DENSA (N=40).
_PERFIL = [{"tipo": "argila", "N": 3, "dz": 5.0},
           {"tipo": "areia", "N": 40, "dz": 10.0}]


def test_camada_na_ponta():
    assert EP._camada_na_ponta(_PERFIL, 3.0)["tipo"] == "argila"    # dentro da 1a
    assert EP._camada_na_ponta(_PERFIL, 5.0)["tipo"] == "argila"    # boundary -> cima
    assert EP._camada_na_ponta(_PERFIL, 10.0)["tipo"] == "areia"    # dentro da 2a
    assert EP._camada_na_ponta(_PERFIL, 99.0)["tipo"] == "areia"    # alem -> ultima


def test_aoki_ponta_na_camada_de_L():
    r5 = EP.capacidade_aoki_velloso(_PERFIL, 0.40, 5.0, "pre_moldada")
    r15 = EP.capacidade_aoki_velloso(_PERFIL, 0.40, 15.0, "pre_moldada")
    assert r5["N_ponta"] == 3, "ponta a 5 m esta na ARGILA (N=3), nao na areia N=40"
    assert r15["N_ponta"] == 40
    # a estaca curta (ponta mole) NAO pode ter R_ponta ~ da estaca longa (ponta na areia)
    assert r5["R_ponta_kN"] < 0.1 * r15["R_ponta_kN"]


def test_decourt_e_teixeira_ponta_na_camada_de_L():
    for f in (EP.capacidade_decourt_quaresma, EP.capacidade_teixeira):
        r5 = f(_PERFIL, 0.40, 5.0)
        r15 = f(_PERFIL, 0.40, 15.0)
        # ponta curta (argila) muito menor que ponta longa (areia densa)
        assert r5["R_ponta_kN"] < 0.2 * r15["R_ponta_kN"], f.__name__


def test_N_ponta_override_respeitado():
    # se o eng. informa N_ponta, ele prevalece (dado da sondagem no nivel da ponta)
    r = EP.capacidade_aoki_velloso(_PERFIL, 0.40, 5.0, "pre_moldada", N_ponta=8)
    assert r["N_ponta"] == 8


def test_perfil_ate_L_sem_regressao():
    # perfil de camada unica com L = profundidade: ponta = essa camada (inalterado)
    p = [{"tipo": "areia", "N": 20, "dz": 12.0}]
    r = EP.capacidade_aoki_velloso(p, 0.30, 12.0, "pre_moldada")
    assert r["N_ponta"] == 20
