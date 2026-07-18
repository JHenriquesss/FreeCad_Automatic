# ============================================================================
# verificar_amostra.py - VERIFICACAO VISUAL da amostra do engenheiro.
# Roda o pipeline COMPLETO (3D + pranchas 2D + dossie) sobre o spec de amostra e
# aponta os artefatos para inspecao. Uso pos-caca sessao 14: confirmar VISUALMENTE
# (1) a mao-francesa corrigida (mesa inferior -> terca, com offset longitudinal) e
# (2) o layout das pranchas executivas.
#
# PRE-REQUISITO: FreeCAD ABERTO (o RobustMCPBridge escuta na porta 9875). O 3D e o
# executivo NAO sobem sozinhos. Abra o FreeCAD, espere alguns segundos, e rode:
#     python verificar_amostra.py
# (ou passe outro spec:  python verificar_amostra.py meu_spec.json)
# ============================================================================
"""Roda a amostra completa (3D+2D) e aponta os artefatos p/ verificacao visual."""

from __future__ import annotations

import os
import socket
import sys
import xmlrpc.client

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

HOST = "http://localhost:9875"


def _bridge_no_ar(host=HOST, timeout=4.0):
    try:
        socket.setdefaulttimeout(timeout)
        xmlrpc.client.ServerProxy(host).execute("_result_ = 1")
        return True
    except Exception:
        return False


def _abrir(caminho):
    """Abre a pasta/arquivo no explorador (best-effort, so Windows)."""
    try:
        os.startfile(caminho)  # noqa
    except Exception:
        pass


def main():
    import projeto_spec as PS
    import wizard as WZ

    spec_path = sys.argv[1] if len(sys.argv) >= 2 else os.path.join(
        AQUI, "spec_amostra_engenheiro.json")
    if not os.path.isfile(spec_path):
        print(f"[!] Spec nao encontrado: {spec_path}")
        return 2
    spec = WZ.carregar_spec(spec_path)

    val = PS.validar(spec)
    if not val["ok"]:
        print("[!] Spec INCOMPLETO/INCOERENTE - resolva antes:")
        for p, d in val["faltando"]:
            print(f"    - {p}: {d}")
        return 1
    if val.get("avisos"):
        print("Avisos (nao bloqueiam, ficam na memoria de calculo):")
        for p, d in val["avisos"]:
            print(f"    - {p}: {d}")

    if not _bridge_no_ar():
        print("=" * 68)
        print("[!] O bridge do FreeCAD (porta 9875) NAO respondeu.")
        print("    Abra o FreeCAD, espere o RobustMCPBridge subir (alguns")
        print("    segundos) e rode este script de novo. O 3D/executivo nao")
        print("    sobem sozinhos.")
        print("=" * 68)
        return 3

    print("Bridge FreeCAD OK. Rodando pipeline COMPLETO (3D + pranchas + dossie)...")
    print("(o executivo demora - pranchas TechDraw; aguarde)")
    import rodar_projeto as RP
    saida = RP.rodar_tudo(
        spec, com_3d=True, com_executivo=True, gerar_pdf=True, gerar_dossie=True,
        host=HOST, verbose=True)

    out = saida["out_dir"]
    modelo = saida.get("modelo") or {}
    rm = modelo.get("result") if isinstance(modelo, dict) else None
    vistas = (rm or {}).get("vistas") if isinstance(rm, dict) else None
    executivo = saida.get("executivo") or {}
    pranchas = executivo.get("pranchas") if isinstance(executivo, dict) else None
    dossie = saida.get("dossie") or {}

    print("\n" + "=" * 68)
    print("VEREDITO GLOBAL (atende):", saida.get("atende"))
    print("Saida em:", out)

    # 1) MAO-FRANCESA: confirmar que os objetos existem e apontar a vista iso.
    print("\n--- MAO-FRANCESA (fix da geometria 3D) ---")
    n_mf = None
    if isinstance(rm, dict):
        objs = rm.get("nomes_objetos") or rm.get("objetos") or []
        if objs:
            n_mf = sum(1 for o in objs if str(o).startswith("MAO_FRANCESA"))
    if n_mf is not None:
        print(f"  {n_mf} objeto(s) MAO_FRANCESA no modelo.")
    print("  O QUE CONFERIR na vista ISOMETRICA: cada mao-francesa deve ligar a")
    print("  MESA INFERIOR do rafter a uma TERCA, INCLINADA no sentido LONGITUDINAL")
    print("  (fora do plano do portico). Antes ficava no plano do portico (errado).")

    if vistas:
        print(f"\n--- 3D: {len(vistas)} vista(s) PNG ---")
        for v in vistas:
            print("   ", v)
        _abrir(os.path.dirname(vistas[0]))
    else:
        print("\n[!] Nenhuma vista 3D PNG retornada. Confira se o FreeCAD estava")
        print("    com a janela visivel (GuiUp). Motivo:", (modelo or {}).get("erro"))

    if pranchas:
        print(f"\n--- PRANCHAS EXECUTIVAS 2D: {len(pranchas)} ---")
        for p in pranchas:
            print("   ", p)
        _abrir(os.path.dirname(pranchas[0]) if isinstance(pranchas[0], str) else out)
        print("  O QUE CONFERIR (layout): cotas sem sobreposicao, rotulos dentro")
        print("  da folha, vistas centradas e legiveis, carimbo completo.")
    else:
        print("\n[!] Pranchas nao geradas. Motivo:", executivo.get("erro"))

    if isinstance(dossie, dict) and dossie.get("path"):
        print(f"\n--- DOSSIE (PDF unico): {dossie['path']} "
              f"({dossie.get('n_paginas', '?')} paginas) ---")
        _abrir(dossie["path"])

    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
