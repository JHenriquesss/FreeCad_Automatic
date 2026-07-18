# ============================================================================
# demo_engenheiro.py - AMOSTRA GUIADA para o engenheiro responsavel.
# Roda o wizard COMPLETO (todas as perguntas, gate a gate) e, ao final, gera
# APENAS a imagem 3D (as pranchas 2D sao puladas nesta amostra - demoram).
#
#   com_3d=True        -> monta o modelo 3D via bridge FreeCAD + captura vistas PNG
#   com_executivo=False-> NAO gera pranchas 2D (TechDraw) - o passo lento
#   gerar_dossie=False -> dossie junta as pranchas; sem elas, fica de fora
#   gerar_pdf=True     -> memorial de calculo (rapido) fica disponivel
#
# Uso:  python demo_engenheiro.py            # wizard interativo -> 3D
#       python demo_engenheiro.py spec.json  # reusa um spec salvo -> 3D
# ============================================================================
"""Amostra para o engenheiro: wizard completo -> somente a imagem 3D."""

from __future__ import annotations

import os
import socket
import sys
import xmlrpc.client

import projeto_spec as PS
import wizard as WZ


HOST = "http://localhost:9875"


def _bridge_no_ar(host=HOST, timeout=3.0):
    """True se o bridge FreeCAD responde (3D disponivel)."""
    try:
        socket.setdefaulttimeout(timeout)
        srv = xmlrpc.client.ServerProxy(host)
        srv.execute("_result_ = 1")
        return True
    except Exception:
        return False


def _obter_spec():
    """spec de arquivo (argv[1]) OU do wizard interativo (todas as perguntas)."""
    if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
        spec = WZ.carregar_spec(sys.argv[1])
        print(PS.resumo_pt(spec))
        return spec
    print("Presets (comece de um modelo e ajuste com Enter, ou do zero):")
    for k, (desc, _kw) in WZ.PRESETS.items():
        print(f"  {k}) {desc}")
    esc = input("Preset? (numero, ou Enter p/ do zero): ").strip()
    preset = WZ.PRESETS.get(esc, (None, None))[1]
    spec = WZ.perguntar(preset=preset)
    print("\n" + PS.resumo_pt(spec))
    destino = input("\nSalvar spec em (Enter=spec_%s.json): " % spec["slug"]).strip() \
        or ("spec_%s.json" % spec["slug"])
    WZ.salvar_spec(spec, destino)
    print("Spec salvo em:", destino)
    return spec


def main():
    aqui = os.path.dirname(os.path.abspath(__file__))
    if aqui not in sys.path:
        sys.path.insert(0, aqui)

    print("=" * 68)
    print("AMOSTRA PARA O ENGENHEIRO RESPONSAVEL - wizard completo -> 3D")
    print("(pranchas 2D puladas nesta amostra; o 3D e a imagem que sera exibida)")
    print("=" * 68)

    spec = _obter_spec()

    val = PS.validar(spec)
    if not val["ok"]:
        print("\nSpec INCOMPLETO - resolva os campos de sitio/fabricante antes:")
        for p, d in val["faltando"]:
            print(f"  - {p}: {d}")
        return 1

    if not _bridge_no_ar():
        print("\n[!] O bridge do FreeCAD (porta 9875) nao respondeu.")
        print("    Abra o FreeCAD e aguarde alguns segundos (o RobustMCPBridge")
        print("    inicia sozinho), depois rode este script de novo.")
        return 2

    print("\nBridge FreeCAD OK. Gerando SOMENTE a imagem 3D (sem pranchas 2D)...")
    import rodar_projeto as RP
    saida = RP.rodar_tudo(
        spec,
        com_3d=True,          # monta o 3D + captura as vistas PNG
        com_executivo=False,  # pula as pranchas 2D (passo lento)
        gerar_pdf=True,       # memorial de calculo (rapido)
        gerar_dossie=False,   # dossie depende das pranchas -> fora nesta amostra
        host=HOST,
    )

    out = saida["out_dir"]
    modelo = saida.get("modelo") or {}
    rm = modelo.get("result") if isinstance(modelo, dict) else None
    vistas = (rm or {}).get("vistas") if isinstance(rm, dict) else None

    print("\n" + "=" * 68)
    print("ATENDE (veredito global):", saida["atende"])
    print("Saida em:", out)
    if vistas:
        print("Imagens 3D geradas (%d vistas):" % len(vistas))
        for v in vistas:
            print("  -", v)
        vdir = os.path.dirname(vistas[0])
        try:
            os.startfile(vdir)   # abre a pasta das imagens p/ o engenheiro ver
        except Exception:
            pass
    else:
        print("Nenhuma vista PNG retornada. Confira se o FreeCAD estava com a")
        print("janela visivel (GuiUp) - vistas exigem o modo grafico.")
        erro = (modelo or {}).get("erro")
        if erro:
            print("Motivo do 3D:", erro)
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
