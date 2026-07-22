"""Mapa nome-da-peca -> tipo IFC (export BIM). Item 1 do roteiro de interop.

Garante que cada familia de peca sai no IFC com a CATEGORIA ESTRUTURAL correta
(abre no Revit/Eberick como coluna/viga/chapa/fundacao, nao solido generico).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ifc_map as M


def test_coluna_vs_rafter_do_portico():
    assert M.ifc_tipo("PORTICO_01_C00") == "Column"
    assert M.ifc_tipo("PORTICO_10_C02") == "Column"
    assert M.ifc_tipo("PORTICO_01_V00_E") == "Beam"
    assert M.ifc_tipo("PORTICO_01_V01_D") == "Beam"
    # a mesma familia PORTICO_ NAO pode colapsar coluna e rafter no mesmo tipo
    assert M.ifc_tipo("PORTICO_01_C00") != M.ifc_tipo("PORTICO_01_V00_E")


def test_secundarios_sao_member():
    for nm in ("TERCA_S00_03", "TIRANTE_PAREDE_E_01", "CONTRAV_COB_01",
               "MAO_FRANCESA_00", "ESTICADOR_01", "MONTANTE_OITAO_01"):
        assert M.ifc_tipo(nm) == "Member", nm


def test_chapas_sao_plate():
    for nm in ("PLACA_BASE_C00_01", "GUSSET_COB_01", "CLIPE_GIRT_01",
               "NERVURA_BASE_01", "CONSOLE_PONTE_E", "ENRIJECEDOR_01"):
        assert M.ifc_tipo(nm) == "Plate", nm


def test_fundacao_footing_e_estaca_pile():
    for nm in ("SAPATA_C00_01", "BLOCO_C00_01", "BALDRAME_E", "PEDESTAL_C00_01"):
        assert M.ifc_tipo(nm) == "Footing", nm
    assert M.ifc_tipo("ESTACA_C00_01") == "Pile"


def test_fechamento_covering_e_conector_fastener():
    assert M.ifc_tipo("TELHA_S00_E") == "Covering"
    assert M.ifc_tipo("TAPAMENTO_OITAO_00") == "Covering"
    for nm in ("CHUMBADOR_C00_01", "PARAFUSO_01", "PORCA_01", "ARRUELA_C00_01"):
        assert M.ifc_tipo(nm) == "MechanicalFastener", nm


def test_viga_rolamento_e_cumeeira_beam():
    assert M.ifc_tipo("VIGA_ROLAMENTO_E") == "Beam"
    assert M.ifc_tipo("CUMEEIRA_S00") == "Beam"


def test_desconhecido_e_none():
    assert M.ifc_tipo("TERRENO_LOTE") is None
    assert M.ifc_tipo("") is None
    assert M.ifc_tipo(None) is None


def test_tipos_sao_valores_ifc_validos():
    # todos os tipos retornados existem no vocabulario aceito pelo exportIFC
    validos = {"Column", "Beam", "Member", "Plate", "Footing", "Pile",
               "Covering", "MechanicalFastener"}
    amostra = ["PORTICO_01_C00", "PORTICO_01_V00_E", "TERCA_S00", "PLACA_BASE_01",
               "SAPATA_01", "ESTACA_01", "TELHA_00", "CHUMBADOR_01", "CALHA_E"]
    for nm in amostra:
        t = M.ifc_tipo(nm)
        assert t is None or t in validos, (nm, t)


def test_selftest_modulo():
    M._selftest()
