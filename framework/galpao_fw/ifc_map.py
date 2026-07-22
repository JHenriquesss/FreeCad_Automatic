# ============================================================================
# ifc_map.py - MAPA de NOME DA PECA -> TIPO IFC (BIM). Modulo PURO (sem FreeCAD),
# usado pelo build_galpao no export IFC4 (item 1 do roteiro de interoperabilidade:
# o galpao abre no Revit/Eberick com a CATEGORIA ESTRUTURAL correta, nao um solido
# generico). Separado para ser testavel sem FreeCAD. A convencao de nomes e a do
# build (PORTICO_NN_Cnn = coluna, _Vnn = rafter; TERCA/TIRANTE/CONTRAV = membro
# secundario; PLACA_BASE/GUSSET = chapa; SAPATA/BLOCO = fundacao; ESTACA = estaca;
# TELHA/TAPAMENTO = fechamento; CHUMBADOR/PORCA/ARRUELA = conector).
# ============================================================================
"""Mapa nome-da-peca -> tipo IFC para o export BIM (puro, sem FreeCAD)."""

from __future__ import annotations

import re

_PORTICO_COL = re.compile(r"PORTICO_\d+_C\d")
_PORTICO_RAF = re.compile(r"PORTICO_\d+_V\d")


def ifc_tipo(nome):
    """Nome da peca -> string IfcType aceita pelo exportIFC do FreeCAD
    (IfcColumn/Beam/Member/Plate/Footing/Pile/Covering/MechanicalFastener).
    None -> o exportador cai em IfcBuildingElementProxy (ainda visivel no viewer)."""
    n = (nome or "").upper()
    if _PORTICO_COL.match(n):
        return "Column"
    if _PORTICO_RAF.match(n):
        return "Beam"
    if n.startswith(("VIGA_ROLAMENTO", "CUMEEIRA", "ESCORA_BEIRAL")):
        return "Beam"
    if n.startswith(("TERCA", "TIRANTE", "CONTRAV", "MONTANTE", "MAO_FRANCESA",
                     "ESTICADOR", "VAO_")):
        return "Member"
    if n.startswith(("PLACA_BASE", "GUSSET", "CLIPE", "NERVURA", "CONSOLE_PONTE",
                     "ENRIJECEDOR", "DOUBLER", "CONEX", "CHAPA")):
        return "Plate"
    if n.startswith("ESTACA"):
        return "Pile"
    if n.startswith(("SAPATA", "BLOCO", "BALDRAME", "PEDESTAL")):
        return "Footing"
    if n.startswith(("TELHA", "TAPAMENTO", "PAINEL")):
        return "Covering"
    if n.startswith(("CHUMBADOR", "PARAFUSO", "PORCA", "ARRUELA")):
        return "MechanicalFastener"
    if n.startswith(("CALHA", "CONDUTOR", "BOCAL")):
        return "Member"                    # drenagem (linear, nao estrutural)
    return None


def _selftest():
    assert ifc_tipo("PORTICO_01_C00") == "Column"
    assert ifc_tipo("PORTICO_03_C02") == "Column"
    assert ifc_tipo("PORTICO_01_V00_E") == "Beam"
    assert ifc_tipo("VIGA_ROLAMENTO_E") == "Beam"
    assert ifc_tipo("CUMEEIRA_S00") == "Beam"
    assert ifc_tipo("TERCA_S00_03") == "Member"
    assert ifc_tipo("TIRANTE_PAREDE_E_01") == "Member"
    assert ifc_tipo("CONTRAV_COB_01") == "Member"
    assert ifc_tipo("MAO_FRANCESA_00") == "Member"
    assert ifc_tipo("PLACA_BASE_C00_01") == "Plate"
    assert ifc_tipo("GUSSET_COB_01") == "Plate"
    assert ifc_tipo("CONSOLE_PONTE_E") == "Plate"
    assert ifc_tipo("ESTACA_C00_01") == "Pile"
    assert ifc_tipo("SAPATA_C00_01") == "Footing"
    assert ifc_tipo("BLOCO_C00_01") == "Footing"
    assert ifc_tipo("BALDRAME_E") == "Footing"
    assert ifc_tipo("TELHA_S00_E") == "Covering"
    assert ifc_tipo("TAPAMENTO_OITAO_00") == "Covering"
    assert ifc_tipo("CHUMBADOR_C00_01") == "MechanicalFastener"
    assert ifc_tipo("ARRUELA_C00_01") == "MechanicalFastener"
    assert ifc_tipo("CALHA_E") == "Member"
    assert ifc_tipo("CONDUTOR_E_00") == "Member"
    # nao casa coluna com rafter e vice-versa
    assert ifc_tipo("PORTICO_01_C00") != ifc_tipo("PORTICO_01_V00_E")
    # desconhecido -> None (proxy)
    assert ifc_tipo("TERRENO_LOTE") is None
    assert ifc_tipo("") is None and ifc_tipo(None) is None
    print("ifc_map _selftest PASSED")


if __name__ == "__main__":
    _selftest()
