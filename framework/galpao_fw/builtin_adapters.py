"""Registro dos adaptadores nativos do Loop."""

import sys


def register_builtin_adapters() -> None:
    module = sys.modules.get("galpao_adapter")
    if module is None:
        import galpao_adapter
        module = galpao_adapter
    register_galpao_adapter = getattr(module, "register_galpao_adapter", None)
    if callable(register_galpao_adapter):
        register_galpao_adapter()
    from casa_residencial import register_casa_residencial_adapter
    from edificio_adapter import register_edificio_adapter
    from casa_residencial_sintetica import register_residential_adapter
    from residencial_eletrica import register_residential_electrical_adapter
    # Fixture de contrato, nao projeto para obra: e' o UNICO adaptador
    # registrado sem hooks, e por isso o unico que exerce o caminho
    # "entregavel pedido, hook ausente -> not_available" do nucleo.
    # Decisao G10 em REVISAO-G10-FIXTURE-SINTETICA.md; nao remover.
    register_residential_adapter()
    register_residential_electrical_adapter()
    register_casa_residencial_adapter()
    register_edificio_adapter()
