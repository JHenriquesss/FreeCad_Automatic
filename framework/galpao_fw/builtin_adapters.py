"""Registro dos adaptadores nativos do Loop."""

import sys


def register_builtin_adapters() -> None:
    module = sys.modules.get("galpao_adapter")
    if module is None:
        import galpao_adapter
        return
    register_galpao_adapter = getattr(module, "register_galpao_adapter", None)
    if register_galpao_adapter is None:
        return

    register_galpao_adapter()
