"""Registro dos adaptadores nativos do Loop."""


def register_builtin_adapters() -> None:
    from galpao_adapter import register_galpao_adapter

    register_galpao_adapter()
