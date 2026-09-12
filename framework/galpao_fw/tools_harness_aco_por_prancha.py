# ============================================================================
# tools_harness_aco_por_prancha.py - G105: HARNESS DE MEDICAO POR PRANCHA.
# SCRIPT AVULSO: ferramenta rodada a mao (python
# tools_harness_aco_por_prancha.py), nunca importada por orquestrador do Loop
# - declarada em SCRIPTS_AVULSOS em tests/test_alcancabilidade.py, no mesmo
# molde de tools_probe_pe13.py. A parte pura (registro, boot, checker) e
# coberta por tests/test_harness_aco_g105.py sem FreeCAD.
#
# Motivacao (D118/G96): o executivo de aco precisa do freecad.exe com GUI em
# 11 folhas projetadas (DrawViewPart/DrawViewSection); so PE09 (quadros) e
# PE16 (montagem) sao 2D puro. Nenhuma iteracao manual de timing foi rodada:
# o custo por prancha e desconhecido; so se sabe o peso do estagio inteiro
# (7,0 em caderno_turnkey._STAGE_WEIGHTS) e que o executivo estoura ~15 min
# em rodada (06-open-threads T13). O precedente e tools_probe_pe13.py: uma
# execucao mede o que a iteracao manual nao mede.
#
# O que este harness entrega (ferramenta, nao otimizacao): para cada prancha,
# tempo de construcao, tempo de HLR, tempo de cotas e tempo de export, com o
# processo REINICIADO a cada medicao e kill via RP._matar_processo_freecad
# (kill -> taskkill /F /T -> WMI Terminate; taskkill sozinho nao derruba
# FreeCAD travado - D64). Os numeros vao para JSON + CSV por prancha.
# ============================================================================
"""Harness G105: mede o executivo de aco por prancha (build/HLR/cotas/export).

Uso manual (dentro de framework/galpao_fw, com freecad.exe + modelo FCStd)::

    python tools_harness_aco_por_prancha.py --fcstd <modelo.FCStd> --out <dir>

Sem modelo FCStd no disco o launcher declara a falta e sai (nao inventa
dado de projeto: ausencia se declara, nunca se preenche).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time

GALPAO = os.path.dirname(os.path.abspath(__file__))
if GALPAO not in sys.path:
    sys.path.insert(0, GALPAO)

# Registro das paginas do executivo de aco (medido em techdraw_exec.py; o
# teste-guarda confere cada entrada contra o fonte, entao pagina nova sem
# registro aqui derruba a suite nos dois sentidos).
# classe: "hlr" = HLR real (DrawViewPart coarse=False / DrawViewSection /
# crop com Part.common); "coarse" = silhueta rapida; "2d" = Annotation +
# Spreadsheet, custo ~zero (controles do harness).
# construtor/nargs espelham gerar_executivo: 4-arg precisam de `todos`
# (miudezas), 3-arg de `objs`, 2-arg (_pr_quadros) so de (doc, cfg).
PRANCHAS = (
    {"chave": "PE01_COBERTURA", "pagina": "PE01_COBERTURA",
     "construtor": "_pr_cobertura", "nargs": 3, "classe": "coarse"},
    {"chave": "PE02_FUNDACOES", "pagina": "PE02_FUNDACOES",
     "construtor": "_pr_fundacoes", "nargs": 3, "classe": "coarse"},
    {"chave": "PE03_ELEVACOES", "pagina": "PE03_ELEVACOES",
     "construtor": "_pr_elevacoes", "nargs": 3, "classe": "coarse"},
    {"chave": "PE04_PORTICO", "pagina": "PE04_PORTICO",
     "construtor": "_pr_portico", "nargs": 3, "classe": "hlr"},
    {"chave": "PE05_CONTRAVENTAMENTO", "pagina": "PE05_CONTRAVENTAMENTO",
     "construtor": "_pr_contravent", "nargs": 4, "classe": "coarse"},
    {"chave": "PE06_DET_BASE", "pagina": "PE06_DET_BASE",
     "construtor": "_pr_base", "nargs": 4, "classe": "hlr"},
    {"chave": "PE07_DET_JOELHO", "pagina": "PE07_DET_JOELHO",
     "construtor": "_pr_joelho", "nargs": 4, "classe": "hlr"},
    {"chave": "PE08_FECHAMENTO", "pagina": "PE08_FECHAMENTO",
     "construtor": "_pr_fechamento", "nargs": 3, "classe": "coarse"},
    {"chave": "PE09_QUADROS", "pagina": "PE09_QUADROS",
     "construtor": "_pr_quadros", "nargs": 2, "classe": "2d"},
    {"chave": "PE10_DET_CUMEEIRA", "pagina": "PE10_DET_CUMEEIRA",
     "construtor": "_pr_ligacoes", "nargs": 4, "classe": "hlr",
     "prefixo_ligacao": "CONEX_CUMEEIRA", "indice_ligacao": 0},
    {"chave": "PE11_DET_GUSSET_COB", "pagina": "PE11_DET_GUSSET_COB",
     "construtor": "_pr_ligacoes", "nargs": 4, "classe": "hlr",
     "prefixo_ligacao": "CONEX_GUSSET_COB", "indice_ligacao": 1},
    {"chave": "PE12_DET_GUSSET_PAR", "pagina": "PE12_DET_GUSSET_PAR",
     "construtor": "_pr_ligacoes", "nargs": 4, "classe": "hlr",
     "prefixo_ligacao": "CONEX_GUSSET_PAR", "indice_ligacao": 2},
    {"chave": "PE13_DET_CLIPE_GIRT", "pagina": "PE13_DET_CLIPE_GIRT",
     "construtor": "_pr_ligacoes", "nargs": 4, "classe": "hlr",
     "prefixo_ligacao": "CLIPE_GIRT", "indice_ligacao": 3},
    {"chave": "PE14_DET_CONSOLE", "pagina": "PE14_DET_CONSOLE",
     "construtor": "_pr_ligacoes", "nargs": 4, "classe": "hlr",
     "prefixo_ligacao": "CONEX_CONSOLE", "indice_ligacao": 4},
    # PE15 so sai com fundacao profunda (sem BLOCO o construtor devolve
    # ([], [])); PE14_CROQUIS so sai com Marca no 3D. Pagina vazia por
    # condicional sai no JSON com motivo, nunca como zero silencioso.
    {"chave": "PE15_DET_BLOCO", "pagina": "PE15_DET_BLOCO",
     "construtor": "_pr_bloco", "nargs": 4, "classe": "hlr"},
    # Colisao de numero herdada: PE14_DET_CONSOLE x PE14_CROQUIS usam o mesmo
    # numero com nomes distintos. O harness chaveia pelo nome completo.
    {"chave": "PE14_CROQUIS", "pagina": "PE14_CROQUIS",
     "construtor": "_pr_croquis", "nargs": 4, "classe": "hlr"},
    {"chave": "PE16_MONTAGEM", "pagina": "PE16_MONTAGEM",
     "construtor": "_pr_montagem", "nargs": 3, "classe": "2d"},
)

# BASELINE_G105 (registro congelado nos dois sentidos, molde BASELINE_G91):
# pagina nova sem entrada aqui, ou entrada sem pagina no fonte, reprova.
# Os tempos ficam not_available ate a primeira rodada manual com modelo
# real (nao ha FCStd no disco nesta entrega; orcamento inventado seria
# dado arbitrado, e o framework nao arbitra).
BASELINE_G105 = {p["chave"]: p["classe"] for p in PRANCHAS}
TEMPOS_G105 = {p["chave"]: None for p in PRANCHAS}

# G109: numeros medidos em 2026-09-11 no galpao-ufpe (44x90 2 vaos, FCStd
# 2,3 MB via montar_modelo headless; freecad.exe 1.1; maquina 8 GB com
# ~1 GB livre). Totais ≈ 578 s nas 16 medidas, compativel com os ~15 min
# do executivo inteiro (06-open-threads T13). PE05 sem numero entao: timeout
# sistematico 2x1200 s + diag 540 s, trava no doc.recompute() da pagina
# (t_hlr); build dela e instantaneo (1 pag + 1 cota). Tetos manuais com
# folga; None = sem numero (condicional ausente), nunca zero.
# G118 (2026-09-12, mesmo modelo/maquina/condicao ~1 GB livre): causa medida
# (topo com 432 TIRANTEs sem oclusores; 548 s so neles) e fix na producao
# (topo so CONTRAV). PE05 medida: build 0,2 / hlr 128,0 / cotas 47,1 / export
# 34,1 (total ≈ 209 s); teto 240 com folga. Total do aco ≈ 788 s.
MEDIDOS_G109 = {
    "PE01_COBERTURA": {"t_build": 0.1, "t_hlr": 67.3,
                       "t_cotas": 96.6, "t_export": 23.6},
    "PE02_FUNDACOES": {"t_build": 9.6, "t_hlr": 3.8,
                       "t_cotas": 35.5, "t_export": 9.8},
    "PE03_ELEVACOES": {"t_build": 0.2, "t_hlr": 70.7,
                       "t_cotas": 100.7, "t_export": 40.3},
    "PE04_PORTICO": {"t_build": 0.2, "t_hlr": 4.3,
                     "t_cotas": 6.8, "t_export": 4.1},
    "PE05_CONTRAVENTAMENTO": {"t_build": 0.2, "t_hlr": 128.0,
                              "t_cotas": 47.1, "t_export": 34.1},
    "PE06_DET_BASE": {"t_build": 0.3, "t_hlr": 3.0,
                      "t_cotas": 1.4, "t_export": 1.6},
    "PE07_DET_JOELHO": {"t_build": 1.2, "t_hlr": 3.0,
                        "t_cotas": 1.5, "t_export": 1.9},
    "PE08_FECHAMENTO": {"t_build": 0.1, "t_hlr": 8.8,
                        "t_cotas": 11.8, "t_export": 8.0},
    "PE09_QUADROS": {"t_build": 2.2, "t_hlr": 2.1,
                     "t_cotas": 0.4, "t_export": 3.0},
    "PE10_DET_CUMEEIRA": {"t_build": 1.5, "t_hlr": 3.2,
                          "t_cotas": 3.0, "t_export": 5.1},
    "PE11_DET_GUSSET_COB": {"t_build": 1.6, "t_hlr": 2.6,
                            "t_cotas": 1.5, "t_export": 2.9},
    "PE12_DET_GUSSET_PAR": {"t_build": 2.8, "t_hlr": 2.9,
                            "t_cotas": 2.3, "t_export": 2.7},
    "PE13_DET_CLIPE_GIRT": {"t_build": 2.2, "t_hlr": 3.0,
                            "t_cotas": 2.5, "t_export": 4.3},
    "PE14_DET_CONSOLE": {"t_build": 0.0, "t_hlr": 0.0,
                         "t_cotas": 0.0, "t_export": 0.0},
    "PE15_DET_BLOCO": {"t_build": 0.0, "t_hlr": 0.0,
                       "t_cotas": 0.0, "t_export": 0.0},
    "PE14_CROQUIS": {"t_build": 0.1, "t_hlr": 2.8,
                     "t_cotas": 0.5, "t_export": 1.5},
    "PE16_MONTAGEM": {"t_build": 0.7, "t_hlr": 2.0,
                      "t_cotas": 0.4, "t_export": 2.3},
}
ORCAMENTO_G109 = {
    "PE01_COBERTURA": 210.0, "PE02_FUNDACOES": 90.0,
    "PE03_ELEVACOES": 240.0,     "PE04_PORTICO": 30.0,
    "PE05_CONTRAVENTAMENTO": 240.0, "PE06_DET_BASE": 30.0,
    "PE07_DET_JOELHO": 30.0, "PE08_FECHAMENTO": 60.0,
    "PE09_QUADROS": 30.0, "PE10_DET_CUMEEIRA": 30.0,
    "PE11_DET_GUSSET_COB": 30.0, "PE12_DET_GUSSET_PAR": 30.0,
    "PE13_DET_CLIPE_GIRT": 30.0, "PE14_DET_CONSOLE": None,
    "PE15_DET_BLOCO": None, "PE14_CROQUIS": 30.0,
    "PE16_MONTAGEM": 30.0,
}

TEMPO_KEYS = ("t_build", "t_hlr", "t_cotas", "t_export")


def _entrada(chave):
    for p in PRANCHAS:
        if p["chave"] == chave:
            return p
    raise KeyError("prancha fora do registro G105: %r" % (chave,))


def montar_boot_por_prancha(cfg_nativa, fonte_td, chave, saida_json):
    """Monta o script que o freecad.exe roda para UMA prancha.

    Mede com time.perf_counter: t_build (construtor), t_hlr (recompute +
    assentamento na MDI, com os sleeps 1.0/0.3 do pipeline), t_cotas
    (aplica + recompute) e t_export (PDF + SVG + DXF por pagina). Escreve
    o JSON em saida_json e fecha limpo via QTimer (molde _entry).
    """
    ent = _entrada(chave)
    return (
        "# -*- coding: utf-8 -*-\n"
        "_CFG_ = %r\n" % (cfg_nativa,) +
        "_CHAVE_ = %r\n" % (chave,) +
        "_SAIDA_ = %r\n" % (saida_json,) +
        # G109: o boot roda DENTRO do freecad.exe com so o fonte do techdraw
        # no namespace; PRANCHAS vive neste harness, nao no techdraw. O boot
        # recebe so a entrada da prancha medida (_ENT_) em vez de olhar
        # PRANCHAS (NameError em toda medicao real; o teste-guarda nunca
        # executa o boot sem freecad.exe). Passar a entrada unica tambem
        # mantem o teste_05 (boot de PE13 sem "_pr_portico").
        "_ENT_ = %r\n" % (ent,) +
        fonte_td + r'''

def _medir_uma():
    import json, os, time, traceback
    import FreeCAD as App
    import FreeCADGui as Gui
    res = {"prancha": _CHAVE_, "ok": False, "motivo": "",
           "t_build": None, "t_hlr": None, "t_cotas": None,
           "t_export": None, "paginas": []}
    try:
        t0 = time.perf_counter()
        doc = App.openDocument(_CFG_["fcstd"])
        todos = [o for o in doc.Objects
                 if o.TypeId == "Part::Feature" and hasattr(o, "Shape")
                 and not o.Shape.isNull()]
        objs = [o for o in todos
                if not any(o.Label.startswith(p) for p in _MIUDEZAS)]
        velhos = [o.Name for o in doc.Objects
                  if o.TypeId.startswith("TechDraw::")
                  or o.TypeId == "Spreadsheet::Sheet"]
        for nome in velhos:
            if doc.getObject(nome) is not None:
                try:
                    doc.removeObject(nome)
                except Exception:
                    pass
        ent = _ENT_
        fn = globals()[ent["construtor"]]
        t_a = time.perf_counter()
        if ent["construtor"] == "_pr_ligacoes":
            (pref, titulo, base, KW, elev, chapa, callout,
             sec_n) = LIGACOES[ent["indice_ligacao"]]
            pg_name = "PE%02d_DET_%s" % (10 + ent["indice_ligacao"], base)
            try:
                pg, cts = _detalhe_ligacao(
                    doc, _CFG_, todos, pref, titulo, base, KW, elev,
                    chapa, pg_name, callout, sec_normal=sec_n)
                paginas, cotadores = ([pg] if pg is not None else []), (cts or [])
            except Exception as ex:
                paginas, cotadores = [], []
                res["motivo"] = "ligacao nao emitida: %s" % ex
        elif ent["nargs"] == 4:
            paginas, cotadores = fn(doc, _CFG_, objs, todos)
        elif ent["nargs"] == 3:
            paginas, cotadores = fn(doc, _CFG_, objs)
        else:
            paginas, _ = fn(doc, _CFG_)
            cotadores = []
        res["t_build"] = time.perf_counter() - t_a
        if not paginas:
            if not res["motivo"]:
                res["motivo"] = ("condicional nao presente no modelo "
                                 "(BLOCO/Marca/tipo de ligacao)")
            res["ok"] = True
            res["t_hlr"] = 0.0
            res["t_cotas"] = 0.0
            res["t_export"] = 0.0
        else:
            import TechDrawGui
            t_a = time.perf_counter()
            doc.recompute()
            for p in paginas:
                try:
                    p.ViewObject.doubleClicked()
                except Exception:
                    pass
            Gui.updateGui()
            time.sleep(1.0)
            Gui.updateGui()
            res["t_hlr"] = time.perf_counter() - t_a
            t_a = time.perf_counter()
            for c in cotadores:
                try:
                    c.aplica()
                except Exception:
                    pass
            doc.recompute()
            Gui.updateGui()
            time.sleep(0.3)
            Gui.updateGui()
            res["t_cotas"] = time.perf_counter() - t_a
            t_a = time.perf_counter()
            out = os.path.join(_CFG_["out"], "pranchas")
            os.makedirs(out, exist_ok=True)
            for p in paginas:
                base = os.path.join(out, p.Name)
                try:
                    TechDrawGui.exportPageAsPdf(p, base + ".pdf")
                except Exception as ex:
                    res["motivo"] += " PDF %s: %s;" % (p.Name, ex)
                try:
                    TechDrawGui.exportPageAsSvg(p, base + ".svg")
                    _svg_para_png(base + ".svg", base + ".png")
                except Exception:
                    pass
                try:
                    import TechDraw
                    TechDraw.writeDXFPage(p, base + ".dxf")
                except Exception:
                    pass
            res["t_export"] = time.perf_counter() - t_a
            res["paginas"] = [p.Name for p in paginas]
            res["ok"] = True
        res["t_total_proc"] = time.perf_counter() - t0
    except Exception:
        res["motivo"] = "fatal: " + traceback.format_exc()[-500:]
    try:
        with open(_SAIDA_, "w", encoding="utf-8") as f:
            json.dump(res, f, default=str, indent=1)
    except Exception:
        pass
    try:
        from PySide import QtCore
        for d in list(App.listDocuments().values()):
            App.closeDocument(d.Name)
        QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)
    except Exception:
        pass

from PySide import QtCore
QtCore.QTimer.singleShot(1500, _medir_uma)
''')


def conferir_medido(caminho):
    """Le o JSON de uma prancha (parse real, nao substring) e confere o
    esquema. Devolve (res, problemas): problemas vazio = esquema fecha."""
    with open(caminho, encoding="utf-8") as f:
        res = json.load(f)
    problemas = []
    if res.get("prancha") not in BASELINE_G105:
        problemas.append("prancha fora do registro: %r" % res.get("prancha"))
    for k in TEMPO_KEYS:
        v = res.get(k)
        if v is not None and not isinstance(v, (int, float)):
            problemas.append("tempo %s nao numerico: %r" % (k, v))
        if isinstance(v, (int, float)) and v < 0:
            problemas.append("tempo %s negativo: %r" % (k, v))
    return res, problemas


def conferir_orcamento(medidos, orcamento):
    """Portao do G105: prancha mais lenta que o orcamento reprova.

    medidos: {chave: {t_build, t_hlr, t_cotas, t_export}} (soma = total).
    orcamento: {chave: segundos|None}; None = sem numero medido ainda
    (declarado, nao default silencioso). Devolve dict com OK, estouros,
    sem_orcamento e faltando.
    """
    estouros, sem_orc, faltando = [], [], []
    for chave in BASELINE_G105:
        teto = (orcamento or {}).get(chave)
        med = (medidos or {}).get(chave)
        if med is None:
            faltando.append(chave)
            continue
        if teto is None:
            sem_orc.append(chave)
            continue
        total = sum(med.get(k) or 0.0 for k in TEMPO_KEYS)
        if total > teto:
            estouros.append("%s: %.1fs > orcamento %.1fs"
                            % (chave, total, teto))
    return {"OK": not estouros and not faltando,
            "estouros": sorted(estouros),
            "sem_orcamento": sorted(sem_orc),
            "faltando": sorted(faltando)}


def medir_todas(cfg, out_dir, freecad_exe=None, timeout=1200,
                so_pranchas=None):
    """Launcher manual: um processo freecad.exe por prancha, sempre
    encerrado via RP._matar_processo_freecad (WMI). Agrega JSON + CSV."""
    import techdraw_exec as TD
    import rodar_projeto as RP

    exe = (freecad_exe or os.environ.get("FREECAD_EXE")
           or r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe")
    if not os.path.exists(exe):
        return {"erro": "freecad.exe nao encontrado: %s" % exe}
    if not os.path.exists(cfg.get("fcstd", "")):
        return {"erro": "modelo FCStd nao encontrado: %s"
                % cfg.get("fcstd", "")}
    fonte = TD.codigo_fonte()
    cfg_nat = TD._para_nativo(cfg)
    alvos = [p["chave"] for p in PRANCHAS
             if so_pranchas is None or p["chave"] in so_pranchas]
    resultados = {}
    for chave in alvos:
        saida = os.path.join(out_dir, "tempo_%s.json" % chave)
        boot = tempfile.NamedTemporaryFile(
            mode="w", suffix="_harness_aco.py", delete=False,
            encoding="utf-8")
        boot.write(montar_boot_por_prancha(cfg_nat, fonte, chave, saida))
        boot.close()
        if os.path.exists(saida):
            os.remove(saida)
        proc = subprocess.Popen(
            [exe, boot.name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        try:
            while time.time() - t0 < timeout:
                if os.path.exists(saida):
                    time.sleep(0.5)
                    break
                if proc.poll() is not None:
                    time.sleep(2)
                    break
                time.sleep(2)
        finally:
            RP._matar_processo_freecad(proc)
            try:
                os.unlink(boot.name)
            except OSError:
                pass
        if os.path.exists(saida):
            res, problemas = conferir_medido(saida)
            res["problemas_esquema"] = problemas
        else:
            res = {"prancha": chave, "ok": False,
                   "motivo": "sem JSON em %ds (timeout/saida ausente)"
                   % timeout}
        resultados[chave] = res
    agregado = os.path.join(out_dir, "tempos_aco_por_prancha.json")
    with open(agregado, "w", encoding="utf-8") as f:
        json.dump(resultados, f, default=str, indent=1)
    planilha = os.path.join(out_dir, "tempos_aco_por_prancha.csv")
    with open(planilha, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prancha", "classe"] + list(TEMPO_KEYS)
                   + ["ok", "motivo"])
        for chave in alvos:
            r = resultados[chave]
            w.writerow([chave, BASELINE_G105[chave]]
                       + [r.get(k) for k in TEMPO_KEYS]
                       + [r.get("ok"), (r.get("motivo") or "")[:200]])
    return {"agregado": agregado, "planilha": planilha,
            "resultados": resultados}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="G105: mede o executivo de aco por prancha.")
    ap.add_argument("--fcstd", required=True, help="modelo 3D salvo (.FCStd)")
    ap.add_argument("--out", required=True, help="dir dos tempos medidos")
    ap.add_argument("--spec", default=os.path.join(
        GALPAO, "spec_amostra_engenheiro.json"))
    ap.add_argument("--so", default=None,
                    help="mede so estas pranchas (csv de chaves)")
    args = ap.parse_args(argv)
    import techdraw_exec as TD
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    os.makedirs(args.out, exist_ok=True)
    cfg = TD.config_de_spec(spec, args.fcstd, args.out)
    so = ([s.strip() for s in args.so.split(",")] if args.so else None)
    res = medir_todas(cfg, args.out, so_pranchas=so)
    print(json.dumps({k: v for k, v in res.items() if k != "resultados"},
                     indent=1))
    for chave, r in res.get("resultados", {}).items():
        print("%-22s build=%s hlr=%s cotas=%s export=%s ok=%s %s"
              % (chave, r.get("t_build"), r.get("t_hlr"),
                 r.get("t_cotas"), r.get("t_export"), r.get("ok"),
                 (r.get("motivo") or "")))


if __name__ == "__main__":
    main()
