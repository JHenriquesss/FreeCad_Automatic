"""Registro dos adaptadores nativos do Loop."""

import sys


def register_builtin_adapters() -> None:
    module = sys.modules.get("galpao_adapter")
    if module is None:
        import galpao_adapter
        from casa_residencial_sintetica import register_residential_adapter
        from residencial_eletrica import register_residential_electrical_adapter
        register_residential_adapter()
        register_residential_electrical_adapter()
        return
    register_galpao_adapter = getattr(module, "register_galpao_adapter", None)
    if register_galpao_adapter is None:
        return

    register_galpao_adapter()
    from casa_residencial_sintetica import register_residential_adapter
    from residencial_eletrica import register_residential_electrical_adapter
    register_residential_adapter()
    register_residential_electrical_adapter()
