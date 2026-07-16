# -*- coding: utf-8 -*-
# Shim de compatibilidade do pycufsm 0.2.0 com numpy >= 2.
#
# O pycufsm 0.2.0 foi escrito para numpy 1.x e quebra em numpy>=2 em DOIS pontos:
#
#   (A) pycufsm/pre/cutwp.py  (prop2 - propriedades da linha media): faz
#         x_diffs[i] = np.diff([coord[a, k], coord[b, k]])
#       np.diff de 2 elementos devolve array de tamanho 1; no numpy<2 era
#       auto-desempacotado ao atribuir a um escalar, no numpy>=2 vira ValueError.
#
#   (B) pycufsm/solve/analysis_c (Cython COMPILADO) e analysis_p.py (puro), na
#       montagem da matriz de rigidez global (k_kg_global): fazem
#         row = int((np.argwhere(props[:, 0] == mat_num)).reshape(1))
#       int() de um array 1-D de tamanho 1 vira TypeError no numpy>=2. Como o
#       .pyd compilado nao e patchavel, forcamos o caminho PURO (analysis_p) e o
#       corrigimos por proxy.
#
# ESTRATEGIA (sem editar/vendorizar a lib):
#   - Troca-se, APENAS nos namespaces de cutwp e analysis_p, a referencia `np`
#     por um proxy que delega tudo ao numpy real, exceto:
#       * diff(): desempacota resultado de tamanho 1 (compat numpy<2);
#       * argwhere(): devolve uma view _IntableArray cujo __int__ e seguro
#         (funciona mesmo apos .reshape(1) porque numpy preserva a subclasse).
#   - Forca-se o seletor pycufsm.solve.analysis a usar analysis_p (puro).
#
# Escopo restrito a esses 2 modulos (nao mexe no numpy global). Idempotente.
# No numpy<2 e um no-op (a lib ja funciona nativamente).
#
# Uso: `import pycufsm_compat` ANTES de importar prop2/pycufsm.fsm.

_applied = False
_IntableArray = None


def _make_proxy(np_mod):
    global _IntableArray
    if _IntableArray is None:
        class _IA(np_mod.ndarray):
            """ndarray cujo int()/index e seguro mesmo com tamanho 1 e ndim>0
            (o numpy>=2 proibiu a conversao implicita)."""
            def __int__(self):
                return int(self.reshape(-1)[0])
            def __index__(self):
                return int(self.reshape(-1)[0])
        _IntableArray = _IA

    class _NumpyProxy:
        def __getattr__(self, name):
            return getattr(np_mod, name)

        def diff(self, a, *args, **kwargs):
            r = np_mod.diff(a, *args, **kwargs)
            if getattr(r, "size", None) == 1:      # compat: desempacota escalar
                return r.reshape(()).item()
            return r

        def argwhere(self, *args, **kwargs):
            r = np_mod.argwhere(*args, **kwargs)
            return r.view(_IntableArray)           # int()/reshape(1) seguros

    return _NumpyProxy()


def apply():
    """Aplica o shim ao pycufsm se necessario. No-op no numpy<2 ou se ja
    aplicado. Retorna True se o shim ficou ativo (numpy>=2)."""
    global _applied
    if _applied:
        return True
    import numpy as np
    if int(np.__version__.split(".")[0]) < 2:      # numpy<2 nao precisa
        return False
    try:
        from pycufsm.pre import cutwp
        from pycufsm.solve import analysis_p
        from pycufsm.solve import analysis as analysis_sel
    except Exception:
        return False
    proxy = _make_proxy(np)
    # (A) prop2: diff seguro
    cutwp.np = proxy
    # (B) k_kg_global: argwhere seguro + forca o caminho PURO (analysis_p),
    #     ja que o analysis_c compilado nao e patchavel.
    analysis_p.np = proxy
    analysis_sel.analysis = analysis_p
    # Consumidores que fizeram `from pycufsm.solve.analysis import analysis` na
    # importacao ja fixaram o compilado no proprio namespace (o __init__ do
    # pycufsm carrega fsm.py antes do shim). Repontar cada um p/ o puro.
    for modname in ("pycufsm.fsm", "pycufsm.solve.cfsm", "pycufsm.post.plotters"):
        try:
            import importlib
            m = importlib.import_module(modname)
            if getattr(m, "analysis", None) is not None:
                m.analysis = analysis_p
        except Exception:
            pass
    _applied = True
    return True


apply()
