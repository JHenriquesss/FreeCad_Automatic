# ============================================================================
# techdraw_mezanino.py - PROJETO EXECUTIVO (prancha A1 TechDraw) do MEZANINO DE
# CONCRETO do galpao (PE-MZ-01), a partir de galpao_mezanino.rodar().
# ----------------------------------------------------------------------------
# Como o vertical de incendio, o mezanino NAO tem modelo 3D proprio nesta
# folha: as pranchas sao ESQUEMAS (planta de formas + armacao de
# vigas/pilares via desenho_pavimento adaptado do calculo, G146) embutidos
# via TechDraw::DrawViewSymbol. Logo aqui NAO se abre um FCStd: cria-se um
# documento VAZIO e monta-se a prancha so com os SVGs + quadro de sapatas.
#
# 1 prancha A1: MZ01_MEZANINO (formas + armacao + quadro de sapatas e da
# laje, G146). Carimbo proprio (_carimbo_mz) evita o vazamento de
# material/norma de ACO do carimbo generico. A numeracao de producao (MZ-01)
# segue distinta do codigo do indice (PE-MZ-01), mesma regra do G137/G138:
# a correspondencia viaja na tabela do pacote legal (G112).
#
# Roda DENTRO do freecad.exe (GUI -> exportPageAsPdf), disparado por QTimer,
# como os demais techdraw_*. Contextos: FORA (config_de_spec/codigo_fonte/
# script_bootstrap) e DENTRO (gerar_executivo_mezanino/_entry_mezanino).
# ============================================================================
import os

from techdraw_exec import (
    _nova_prancha, _anot, _carimbo, _svg_para_png)


#: D176: titulo do carimbo da MZ01 (fonte unica da rota SVG e do TechDraw).
#: `techdraw_exec._cap_titulo` corta acima de 26 caracteres; o titulo antigo
#: ("MEZANINO DE CONCRETO - FORMAS E ARMACAO", 39) saia "... - FO…" na folha.
TITULO_CARIMBO_MZ01 = "MEZANINO - FORMAS/ARMACAO"


def _carimbo_mz(cfg, titulo, numero, escala, folha):
    """Carimbo do mezanino: corrige os defaults ESTRUTURAIS de aco do carimbo
    generico (material, norma, tipo de documento e departamento). Sem isso a
    prancha de concreto armado sairia como 'ACO MR250' / 'NBR 8800'."""
    car = _carimbo(cfg, titulo, numero, escala, folha)
    car["part_material"] = cfg.get("carimbo_material", "CONCRETO ARMADO")
    car["general_tolerances"] = "NBR 6118/6122"      # compacto (celula estreita)
    car["document_type"] = "PROJETO ESTRUTURAL - MEZANINO"
    car["responsible_department"] = "ESTRUTURAS"
    return car


# ─────────────────────────────────────────────────────────────────────────
# PRANCHAS (rodam dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _pr_mezanino(doc, cfg):
    """MZ01 - MEZANINO DE CONCRETO (G146): planta de formas + armacao de
    vigas/pilares (SVGs do cfg, ja adaptados com as ausencias declaradas) +
    quadro de sapatas e da laje. Sem recalculo dentro do FreeCAD."""
    page = _nova_prancha(doc, "MZ01_MEZANINO",
                         _carimbo_mz(cfg, TITULO_CARIMBO_MZ01,
                                      "MZ-01", "S/ESC", "01/01"))
    if not cfg.get("formas_svg") or not cfg.get("armacao_svg"):
        raise ValueError("MZ01 sem esquemas: %s"
                         % (cfg.get("mezanino_erro") or "svgs ausentes"))
    formas = doc.addObject("TechDraw::DrawViewSymbol", "MEZ_FORMAS")
    formas.Symbol = cfg["formas_svg"]
    page.addView(formas)
    try:
        formas.X = 420.0                    # centro da A1 (841 x 594 mm)
        formas.Y = 400.0
        formas.Scale = 3.0
    except Exception:
        pass
    armacao = doc.addObject("TechDraw::DrawViewSymbol", "MEZ_ARMACAO")
    armacao.Symbol = cfg["armacao_svg"]
    page.addView(armacao)
    try:
        armacao.X = 420.0
        armacao.Y = 170.0
        armacao.Scale = 2.0
    except Exception:
        pass
    _anot(doc, page, "A01s", ["QUADRO DE SAPATAS E LAJE"] + cfg.get("quadro_linhas", []),
           420, 60, 5)
    return [page]


# ─────────────────────────────────────────────────────────────────────────
# ORQUESTRACAO (dentro do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def gerar_executivo_mezanino(cfg):
    import FreeCAD as App
    import FreeCADGui as Gui
    import TechDrawGui
    import time

    try:
        App.Units.setSchema(0)
    except Exception:
        pass
    out = os.path.join(cfg["out"], "pranchas")
    os.makedirs(out, exist_ok=True)

    doc = App.newDocument("executivo_mezanino")         # SEM FCStd: esquemas

    paginas = []
    for fn in (_pr_mezanino,):
        try:
            paginas += fn(doc, cfg)
        except Exception as ex:
            App.Console.PrintError("Prancha %s: %s\n" % (fn.__name__, ex))

    doc.recompute()
    for p in paginas:
        try:
            p.ViewObject.doubleClicked()
        except Exception:
            pass
    Gui.updateGui()
    time.sleep(1.0)
    Gui.updateGui()
    doc.recompute()
    Gui.updateGui()
    time.sleep(0.3)
    Gui.updateGui()

    arquivos = []
    for p in paginas:
        base = os.path.join(out, p.Name)
        try:
            TechDrawGui.exportPageAsPdf(p, base + ".pdf")
            arquivos.append(base + ".pdf")
        except Exception as ex:
            App.Console.PrintError("PDF %s: %s\n" % (p.Name, ex))
        try:
            TechDrawGui.exportPageAsSvg(p, base + ".svg")
            arquivos.append(base + ".svg")
            _svg_para_png(base + ".svg", base + ".png")
        except Exception:
            pass
    fcstd_out = os.path.join(out, "executivo_mezanino.FCStd")
    try:
        doc.saveAs(fcstd_out)
    except Exception:
        pass
    return {"ok": True, "pranchas": [p.Name for p in paginas],
            "arquivos": arquivos, "fcstd": fcstd_out}


def _entry_mezanino(cfg):
    """Ponto unico chamado pelo bootstrap (via QTimer). Grava status e fecha."""
    import json
    import FreeCAD as App
    out = os.path.join(cfg["out"], "pranchas")
    try:
        os.makedirs(out, exist_ok=True)
    except Exception:
        pass
    status = os.path.join(out, "_status.json")
    try:
        res = gerar_executivo_mezanino(cfg)
    except Exception:
        import traceback
        res = {"erro": traceback.format_exc()}
    try:
        with open(status, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str)
    except Exception:
        pass
    try:
        import FreeCADGui as Gui
        from PySide import QtCore

        def _quit():
            try:
                for nome in list(App.listDocuments().keys()):
                    App.closeDocument(nome)
            except Exception:
                pass
            try:
                QtCore.QCoreApplication.quit()
            except Exception:
                try:
                    Gui.getMainWindow().close()
                except Exception:
                    pass
        QtCore.QTimer.singleShot(400, _quit)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────
# API PUBLICA (roda FORA do FreeCAD)
# ─────────────────────────────────────────────────────────────────────────
def _laje_linhas(laje):
    """Linhas do quadro da laje a partir das armaduras calculadas (uma fonte
    so, sem redimensionar). Sem armaduras, declara em texto (convencao 13:
    nunca um numero)."""
    arm = laje.get("armaduras") if isinstance(laje, dict) else None
    if not arm:
        return (["LAJE m-x", "armadura nao dimensionada nesta rodada"],
                ["LAJE m-y", "armadura nao dimensionada nesta rodada"])
    linhas = []
    for direcao in ("m_x", "m_y"):
        det = arm.get(direcao) if isinstance(arm, dict) else None
        if not isinstance(det, dict):
            linhas.append(["LAJE %s" % direcao.replace("_", "-"),
                           "armadura nao dimensionada nesta rodada"])
            continue
        try:
            as_m = float(det["As_adotada"]) * 1e4
        except (KeyError, TypeError, ValueError):
            linhas.append(["LAJE %s" % direcao.replace("_", "-"),
                           "armadura nao dimensionada nesta rodada"])
            continue
        malha = det.get("malha") if isinstance(det.get("malha"), dict) else {}
        try:
            phi = float(malha["phi_mm"])
            passo = float(malha["s"])
            linhas.append(["LAJE %s" % direcao.replace("_", "-"),
                           "f%.1f c/%d ; %.2f cm2/m"
                           % (phi, round(passo * 100), as_m)])
        except (KeyError, TypeError, ValueError):
            linhas.append(["LAJE %s" % direcao.replace("_", "-"),
                           "%.2f cm2/m (malha nao detalhada)" % as_m])
    return linhas


def config_de_spec(r, out_dir, spec=None):
    """Monta o cfg (dados JA computados) a partir de galpao_mezanino.rodar(r).

    Os SVGs de formas e armacao sao gerados AQUI (desenho_pavimento adaptado
    do calculo, G146) e injetados como string - nada e' recalculado dentro
    do FreeCAD. Nao precisa de FCStd (a folha e' esquema). O fck vem do
    resultado (a conta le direto, sem default - D172); a adaptacao fica num
    `try` proprio (convencao 13: so a MZ01 cai, com a causa em
    `mezanino_erro`, nunca o executivo inteiro).
    """
    import desenho_pavimento as dp
    spec = spec if isinstance(spec, dict) else {}
    if not isinstance(r, dict) or not isinstance(r.get("mezanino"), dict):
        raise ValueError(
            "config da PE-MZ-01 sem bloco 'mezanino' no resultado "
            "(sem calculo nao ha folha PE-MZ-01)")
    mz = r["mezanino"]
    # D172: le da conta, sem default (default calado no carimbo e' a mesma
    # classe do `or 1` que desenhava hidrante inventado).
    fck_MPa = float(mz["fck"]) / 1000.0
    fyk = float(mz.get("fyk", 500e3))
    if abs(fyk - 500e3) < 1e-6:
        aco = "CA-50"
    elif abs(fyk - 600e3) < 1e-6:
        aco = "CA-60"
    else:
        aco = "fyk=%.0f MPa" % (fyk / 1000.0)

    # G146: formas + armacao a partir do calculo (adaptacao na producao, sem
    # recalcular; ausencias declaradas na folha). Sem sapata dimensionada o
    # cfg carrega o erro e so a MZ01 cai (nunca o executivo inteiro).
    try:
        pav, vv, pilares, sapatas, ausentes = dp.adaptar_galpao_mezanino(r)
        formas_svg = dp.planta_formas_svg(
            pav, titulo=("PE-MZ-01 - PLANTA DE FORMAS DO MEZANINO "
                         "(1 painel ; %.1f x %.1f m ; %.1f m2)")
            % (pav["vaos_x"][0], pav["vaos_y"][0], pav["area_m2"]),
            ausencias=ausentes if ausentes else None,
            rotulo_viga=dp.rotulo_viga_mezanino)   # D176: marca = armacao = BIM
        armacao_svg = dp.prancha_armacao_vigas_pilares_svg(
            vv, pilares,
            titulo=("PE-MZ-01 - ARMACAO DE VIGAS E PILARES DO MEZANINO "
                    "(%d tramos / %d pilares)" % (vv["n_tramos"], len(pilares))))
        mezanino_erro = None
    except Exception as exc:                            # noqa: BLE001
        formas_svg, armacao_svg = None, None
        pav, vv, pilares, sapatas, ausentes = None, None, None, [], []
        mezanino_erro = "%s: %s" % (type(exc).__name__, exc)

    quadro_hdr = ["PECA", "DIMENSOES / ARMADURA"]
    quadro = []
    for sap in sapatas:
        quadro.append([sap["marca"], "%d x %d x %d cm ; Nk %.1f kN"
                       % (round(sap["B_m"] * 100), round(sap["L_m"] * 100),
                          round(sap["h_m"] * 100), sap["Nk_kN"])])
    quadro.extend(_laje_linhas(r.get("laje")))
    quadro_linhas = ["%s: %s" % (q[0], q[1]) for q in quadro]
    notas = [
        "NOTAS TECNICAS E MEMORIAL - MEZANINO DE CONCRETO (NBR 6118)",
        "1. Concreto: fck = %.0f MPa (concreto armado, gamma_c = 1,4)." % fck_MPa,
        "2. Aco das armaduras: %s (fyk conforme quadro; gamma_s = 1,15)." % aco,
        "3. Mezanino de 1 painel sobre 4 pilares de canto, dentro do envelope "
        "do galpao metalico (ver memorial para x0/y0).",
        "4. Sapatas de concreto armado (NBR 6122/6118); Nk por pilar no quadro.",
        "5. CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.",
    ]
    for campo in ausentes:
        notas.append("6. Dado nao declarado pelo calculo: %s." % campo)

    return {
        "out": str(out_dir).replace("\\", "/"),
        "slug": spec.get("slug", "galpao_mezanino"),
        "descricao": spec.get("descricao", "Galpao industrial - Mezanino de concreto"),
        "autor": spec.get("autor", "galpao_fw"),
        "fck_MPa": fck_MPa, "aco": aco,
        "carimbo_material": "CONCRETO ARMADO",
        "formas_svg": formas_svg,
        "armacao_svg": armacao_svg,
        "mezanino_ausentes": list(ausentes),
        "mezanino_erro": mezanino_erro,
        "quadro_sap_hdr": quadro_hdr, "quadro_sap": quadro,
        "quadro_linhas": quadro_linhas,
        "notas": notas,
        "materiais": None,
    }


def codigo_fonte():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "techdraw_mezanino.py")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _para_nativo(o):
    import techdraw_exec as TE
    return TE._para_nativo(o)


def script_bootstrap(cfg):
    """Script que o freecad.exe roda: prepende o dir do galpao_fw no sys.path,
    injeta cfg + a fonte, e dispara _entry_mezanino via QTimer. Os SVGs ja
    vem prontos em cfg (desenho_pavimento rodou fora)."""
    galpao_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    return ("# -*- coding: utf-8 -*-\n"
            "import sys\n"
            "if %r not in sys.path: sys.path.insert(0, %r)\n" % (galpao_dir, galpao_dir)
            + "_CFG_ = %r\n" % (_para_nativo(cfg),)
            + codigo_fonte()
            + "\nfrom PySide import QtCore\n"
            "QtCore.QTimer.singleShot(1500, lambda: _entry_mezanino(_CFG_))\n")
