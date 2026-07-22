"""Marcas de peca (piece marks) - modulo puro marcas_peca."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import marcas_peca as MP


def test_prefixo_por_categoria():
    assert MP.prefixo_marca("Colunas") == "C"
    assert MP.prefixo_marca("Vigas") == "V"
    assert MP.prefixo_marca("Tercas de parede") == "TP"
    assert MP.prefixo_marca("Tercas") == "T"          # nao casa com "Tercas de parede"
    assert MP.prefixo_marca("Vigas de baldrame") == "BD"   # antes de "Vigas"
    assert MP.prefixo_marca("Categoria inexistente") == "X"


def test_uma_marca_por_perfil_distinto():
    grupos = [("Colunas", "HEA200"), ("Colunas", "HEA240"), ("Vigas", "HEA180")]
    m = MP.mapa_marcas(grupos)
    assert {m[("Colunas", "HEA200")], m[("Colunas", "HEA240")]} == {"C1", "C2"}
    assert m[("Vigas", "HEA180")] == "V1"


def test_mesmo_grupo_mesma_marca():
    grupos = [("Tercas", "Ue200"), ("Escoras de beiral", "HEA160")]
    assert MP.mapa_marcas(grupos)[("Tercas", "Ue200")] == "T1"
    assert MP.mapa_marcas(grupos)[("Escoras de beiral", "HEA160")] == "E1"


def test_deterministico():
    grupos = [("Vigas", "A"), ("Colunas", "B"), ("Tercas", "C")]
    assert MP.mapa_marcas(grupos) == MP.mapa_marcas(list(reversed(grupos)))


def test_tercas_parede_nao_colide_com_tercas():
    grupos = [("Tercas", "Ue200"), ("Tercas de parede", "Ue150")]
    m = MP.mapa_marcas(grupos)
    assert m[("Tercas", "Ue200")] == "T1"
    assert m[("Tercas de parede", "Ue150")] == "TP1"


def test_todos_os_grupos_recebem_marca():
    grupos = [("Colunas", "x"), ("Vigas", "y"), ("Contraventamento", "b20"),
              ("Placas de base", "chapa-40"), ("Chumbadores", "barra-20")]
    m = MP.mapa_marcas(grupos)
    assert all(g in m and m[g] for g in grupos)
