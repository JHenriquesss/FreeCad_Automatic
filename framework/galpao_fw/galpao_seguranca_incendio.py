# ============================================================================
# galpao_seguranca_incendio.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Orquestra o VERTICAL DE SEGURANCA CONTRA INCENDIO de um galpao industrial (sistemas
# de saida/abandono seguro, exigidos p/ o AVCB), reaproveitando os modulos:
#   - iluminacao_emergencia_nbr10898 (NBR 10898): aclaramento + balizamento;
#   - sinalizacao_nbr16820           (NBR 16820): placas de rota de fuga;
#   - deteccao_alarme_nbr17240       (NBR 17240): detectores + acionadores + central;
#   - proteccao_sprinklers_nbr10897  (NBR 10897): chuveiros automaticos + reserva.
# STATELESS: rodar(spec) recebe um dict explicito (sem estado global). Dados de leiaute
# (rotas de fuga, saidas, altura de viga) marcados A CONFIRMAR quando ausentes.
# Complementa o vertical eletrico (a iluminacao de emergencia e alimentada por bloco
# autonomo/UPS; a central de alarme por 24 Vcc). Saidas em portugues. gates ->
# ATENDE/REPROVA como nos demais verticais.
# ============================================================================
"""Vertical de seguranca contra incendio do galpao (NBR 10898/16820/17240).
Orquestrador STATELESS: rodar(spec) -> gates ATENDE/REPROVA."""

from __future__ import annotations

import iluminacao_emergencia_nbr10898 as ie
import sinalizacao_nbr16820 as sn
import deteccao_alarme_nbr17240 as da
import proteccao_sprinklers_nbr10897 as sp
import hidrantes_nbr13714 as hd


def rodar(spec):
    """Dimensiona os sistemas de seguranca contra incendio do galpao e devolve os gates.
    spec: {
      'geometria': {L(=comprimento), W(=vao/largura), H(=pe-direito)} (m),
      'iluminacao_emergencia': {tipo_area, fluxo_bloco_lm, tipo_fonte, fumaca...} (opc),
      'sinalizacao': {rota_continuada, n_saidas, dist_visualizacao_m...} (opc),
      'deteccao': {viga_m, altura_teto...} (opc),
      'rota_fuga_m' : comprimento das rotas de fuga (opc; default = perimetro).
    }"""
    geo = spec.get("geometria") or {}
    C = float(geo.get("L", 40.0)); L = float(geo.get("W", 20.0)); H = float(geo.get("H", 6.0))
    if C <= 0 or L <= 0 or H <= 0:
        raise ValueError("[A CONFIRMAR] geometria do galpao invalida: comprimento=%g, "
                         "largura=%g, pe-direito=%g (devem ser > 0)." % (C, L, H))
    rota = spec.get("rota_fuga_m")

    # -------------------------------------------- ILUMINACAO DE EMERGENCIA
    ie_spec = dict(spec.get("iluminacao_emergencia", {}))
    ie_spec.update({"C": C, "L": L, "pe_direito": H})
    if rota is not None:
        ie_spec.setdefault("rota_fuga_m", rota)
    emerg = ie.dimensiona_iluminacao_emergencia(ie_spec)

    # -------------------------------------------------------- SINALIZACAO
    sn_spec = dict(spec.get("sinalizacao", {}))
    sn_spec.update({"C": C, "L": L})
    if rota is not None:
        sn_spec.setdefault("rota_fuga_m", rota)
    sinal = sn.dimensiona_sinalizacao(sn_spec)

    # -------------------------------------------------- DETECCAO E ALARME
    da_spec = dict(spec.get("deteccao", {}))
    da_spec.update({"C": C, "L": L})
    da_spec.setdefault("altura_teto", H)
    alarme = da.dimensiona_deteccao_alarme(da_spec)

    # -------------------------------------------- CHUVEIROS AUTOMATICOS (opc)
    # protecao ativa por agua (NBR 10897); exigida por area/altura conforme legislacao.
    sprk = None
    if spec.get("sprinklers"):
        sp_spec = dict(spec["sprinklers"])
        sp_spec.update({"C": C, "L": L})
        sprk = sp.dimensiona_sprinklers(sp_spec)

    # -------------------------------------- HIDRANTES E MANGOTINHOS (NBR 13714)
    # protecao ativa por agua operada por pessoas; exigida se area > 750 m2 e/ou > 12 m.
    # spec['hidrantes'] = {ocupacao(='industrial_I2'), tipo(opc)}. Sem o spec o gate e'
    # informativo (verificar a exigencia pela legislacao/IT do Corpo de Bombeiros).
    hidr = None
    if spec.get("hidrantes"):
        hd_spec = dict(spec["hidrantes"])
        hd_spec.update({"C": C, "L": L, "altura_m": hd_spec.get("altura_m", H)})
        hidr = hd.dimensiona_hidrantes(hd_spec)

    # --------------------------------------------------------------- GATES
    gates = {
        "iluminacao_emergencia": {"E_min_lux": emerg["E_min_lux"],
                                  "N_aclaramento": emerg["N_aclaramento"],
                                  "N_balizamento": emerg["N_balizamento"],
                                  "autonomia_h": emerg["autonomia_h"],
                                  "comutacao_max_s": emerg["comutacao_max_s"],
                                  "OK": emerg["OK"]},
        "sinalizacao": {"placa_lado_mm": sinal["placa_lado_mm"],
                        "N_placas": sinal["N_total"],
                        "espacamento_m": sinal["espacamento_m"],
                        "letra_min_mm": sinal["letra_min_mm"], "OK": sinal["OK"]},
        "deteccao_alarme": {"tipo_detector": alarme["tipo_detector"],
                            "N_detectores": alarme["N_detectores"],
                            "N_acionadores": alarme["N_acionadores"],
                            "tensao_Vcc": alarme["tensao_Vcc"],
                            "autonomia_supervisao_h": alarme["autonomia_supervisao_h"],
                            "OK": alarme["OK"]},
        "sprinklers": {"risco": sprk["risco"] if sprk else None,
                       "N_chuveiros": sprk["N_chuveiros_total"] if sprk else None,
                       "reserva_m3": sprk["reserva_incendio_m3"] if sprk else None,
                       "pressao_bar": sprk["pressao_bar"] if sprk else None,
                       "nota": "" if sprk else "chuveiros automaticos nao exigidos/nao informados (verificar legislacao/IT)",
                       "OK": sprk["OK"] if sprk else True},
        "hidrantes": {"tipo": hidr["tipo"] if hidr else None,
                      "sistema": hidr["sistema"] if hidr else None,
                      "N_hidrantes": hidr["N_hidrantes"] if hidr else None,
                      "vazao_total_Lmin": hidr["vazao_total_Lmin"] if hidr else None,
                      "reserva_m3": hidr["reserva_incendio_m3"] if hidr else None,
                      "nota": "" if hidr else "hidrantes nao informados (exigido se area > 750 m2 e/ou > 12 m - verificar legislacao/IT)",
                      "OK": hidr["OK"] if hidr else True},
    }
    res = {"spec": {"C": C, "L": L, "H": H}, "iluminacao_emergencia": emerg,
           "sinalizacao": sinal, "deteccao_alarme": alarme, "sprinklers": sprk,
           "hidrantes": hidr, "gates": gates}
    reprovados = [k for k, g in gates.items() if not g["OK"]]
    res["reprovados"] = reprovados
    res["ATENDE"] = len(reprovados) == 0
    return res


def montar_pranchas(r, out_dir, spec=None, freecad_exe=None, timeout=1200):
    """Gera o PROJETO EXECUTIVO (pranchas A1 TechDraw) da seguranca contra incendio
    a partir de rodar(r). NAO precisa de FCStd: a planta de seguranca e' um ESQUEMA
    (SVG do desenho_incendio), nao vista de um 3D. Roda o freecad.exe em modo grafico
    HEADLESS (GUI p/ exportar PDF, job por QTimer, janela fecha sozinha). Exporta
    PDF+SVG+PNG por prancha em out_dir/pranchas.

    Mesma mecanica dos demais montar_pranchas (freecad.exe NOVO -> processo limpo;
    kill de zumbi garantido na saida). Retorna {ok, pranchas, arquivos, fcstd} | {erro}."""
    import os, json, time, tempfile, subprocess
    import techdraw_incendio as TDI
    import rodar_projeto as RP

    exe = freecad_exe or os.environ.get("FREECAD_EXE") or \
        r"C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
    if not os.path.exists(exe):
        return {"erro": f"freecad.exe nao encontrado: {exe}"}

    cfg = TDI.config_de_spec(r, str(out_dir), spec)
    prdir = os.path.join(str(out_dir), "pranchas")
    os.makedirs(prdir, exist_ok=True)
    status = os.path.join(prdir, "_status.json")
    try:
        os.remove(status)
    except OSError:
        pass

    boot = tempfile.NamedTemporaryFile(mode="w", suffix="_exec_inc.py",
                                       delete=False, encoding="utf-8")
    boot.write(TDI.script_bootstrap(cfg))
    boot.close()

    proc = subprocess.Popen([exe, boot.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    res = None
    try:
        while time.time() - t0 < timeout:
            if os.path.exists(status):
                time.sleep(0.5)
                with open(status, encoding="utf-8") as f:
                    res = json.load(f)
                break
            if proc.poll() is not None and not os.path.exists(status):
                time.sleep(2)
                if os.path.exists(status):
                    with open(status, encoding="utf-8") as f:
                        res = json.load(f)
                else:
                    res = {"erro": "freecad.exe encerrou sem gerar _status.json"}
                break
            time.sleep(2)
        if res is None:
            res = {"erro": f"timeout {timeout}s aguardando pranchas"}
    finally:
        RP._matar_processo_freecad(proc)
        try:
            os.unlink(boot.name)
        except OSError:
            pass
    return res


# ============================== BIM / IFC ====================================
# Modelo neutro dos EQUIPAMENTOS de seguranca contra incendio para o ifc_emit puro
# (mesma forma dos verticais de concreto/eletrico). Cada equipamento e' uma CAIXA
# (dims+centro, em mm) num ponto; o ifc_emit mapeia o 'tipo' -> classe IFC4 via
# _IFC_CLASS (IfcFireSuppressionTerminal / IfcSensor / IfcAlarm / IfcLightFixture /
# IfcTank / IfcBuildingElementProxy). COUNT-DRIVEN: usa as MESMAS contagens do resumo
# (N_chuveiros, N_detectores, N_acionadores, N_placas, N_hidrantes, N_aclaramento,
# N_balizamento) -> o modelo BIM bate com as pranchas. Eixos: X=C, Y=L, Z=altura.

def _pts_grade_real(n, C, L):
    """n pontos numa grade proporcional a C x L (metros -> mm), cortada em n. Usa a
    MESMA grade do desenho (desenho_incendio._grade) p/ BIM e planta coincidirem."""
    if n <= 0:
        return []
    from desenho_incendio import _grade
    cols, rows = _grade(n, C, L)
    pts = [((i + 0.5) * C / cols * 1000.0, (j + 0.5) * L / rows * 1000.0)
           for j in range(rows) for i in range(cols)]
    return pts[:n]


def _pts_perimetro_real(n, C, L, inset=0.5):
    """n pontos igualmente espacados no perimetro do retangulo recuado de `inset` (m),
    em mm. Para hidrantes/balizamento junto as paredes."""
    if n <= 0:
        return []
    x0, y0, x1, y1 = inset, inset, C - inset, L - inset
    w, h = max(x1 - x0, 0.0), max(y1 - y0, 0.0)
    per = 2.0 * (w + h) or 1.0
    pts = []
    for k in range(n):
        d = (k + 0.5) * per / n
        if d <= w:                              # parede inferior (y=y0)
            x, y = x0 + d, y0
        elif d <= w + h:                        # parede direita (x=x1)
            x, y = x1, y0 + (d - w)
        elif d <= 2.0 * w + h:                  # parede superior (y=y1)
            x, y = x1 - (d - w - h), y1
        else:                                   # parede esquerda (x=x0)
            x, y = x0, y1 - (d - 2.0 * w - h)
        pts.append((x * 1000.0, y * 1000.0))
    return pts


def _eq(tipo, marca, perfil, dims, centro, material):
    return {"tipo": tipo, "marca": marca, "perfil": perfil,
            "dims": [float(dims[0]), float(dims[1]), float(dims[2])],
            "centro": [float(centro[0]), float(centro[1]), float(centro[2])],
            "material": material}


def membros_bim(r):
    """Modelo neutro dos equipamentos de seguranca contra incendio (para ifc_emit).
    Requer r['spec'] {C,L,H} (m). Emite chuveiros e detectores no teto, luminarias de
    aclaramento (teto) e balizamento (perimetro), acionadores e placas nas paredes,
    hidrantes/mangotinhos no perimetro, extintores nos cantos e o reservatorio de
    incendio. COORDENADAS em mm. Lista vazia se faltar geometria."""
    sp = r.get("spec") or {}
    if not all(k in sp for k in ("C", "L", "H")):
        return []
    C, L, H = float(sp["C"]), float(sp["L"]), float(sp["H"])
    Hmm = H * 1000.0
    g = r["gates"]
    M = []

    # CHUVEIROS AUTOMATICOS (NBR 10897) - grade no teto
    nc = int(g["sprinklers"]["N_chuveiros"] or 0)
    for i, (x, y) in enumerate(_pts_grade_real(nc, C, L), 1):
        M.append(_eq("Sprinkler", "SPK%d" % i, "Chuveiro automatico",
                     [100, 100, 100], [x, y, Hmm - 200.0], "Latao"))

    # DETECTORES DE FUMACA pontuais (NBR 17240) - grade no teto
    if g["deteccao_alarme"]["tipo_detector"] == "pontual":
        nd = int(g["deteccao_alarme"]["N_detectores"] or 0)
        for i, (x, y) in enumerate(_pts_grade_real(nd, C, L), 1):
            M.append(_eq("SmokeSensor", "DET%d" % i, "Detector de fumaca",
                         [120, 120, 60], [x, y, Hmm - 150.0], "Plastico"))

    # ILUMINACAO DE EMERGENCIA (NBR 10898): aclaramento no teto + balizamento no perimetro
    na = int(g["iluminacao_emergencia"]["N_aclaramento"] or 0)
    for i, (x, y) in enumerate(_pts_grade_real(na, C, L), 1):
        M.append(_eq("EmergencyLight", "ACL%d" % i, "Luminaria de aclaramento",
                     [300, 120, 120], [x, y, Hmm - 500.0], "Aluminio"))
    nb = int(g["iluminacao_emergencia"]["N_balizamento"] or 0)
    for i, (x, y) in enumerate(_pts_perimetro_real(nb, C, L), 1):
        M.append(_eq("EmergencyLight", "BAL%d" % i, "Balizamento de rota",
                     [200, 100, 100], [x, y, 500.0], "Aluminio"))

    # ACIONADORES MANUAIS (NBR 17240 5.5.2: 0,90-1,35 m do piso) - parede inferior
    nac = int(g["deteccao_alarme"]["N_acionadores"] or 0)
    for i in range(nac):
        x = (i + 0.5) * C / max(nac, 1) * 1000.0
        M.append(_eq("ManualCall", "ACN%d" % (i + 1), "Acionador manual",
                     [120, 120, 60], [x, 300.0, 1200.0], "Plastico"))

    # PLACAS DE SINALIZACAO (NBR 16820) - eixo longitudinal central, z=2,1 m
    npl = int(g["sinalizacao"]["N_placas"] or 0)
    for i in range(npl):
        x = (i + 0.5) * C / max(npl, 1) * 1000.0
        M.append(_eq("Sign", "PLC%d" % (i + 1), "Placa de rota de fuga",
                     [300, 20, 200], [x, L * 500.0, 2100.0], "Fotoluminescente"))

    # HIDRANTES / MANGOTINHOS (NBR 13714) - perimetro, abrigo a 0,9 m
    hid = r.get("hidrantes")
    nh = int(g["hidrantes"]["N_hidrantes"] or 0)
    if hid and nh:
        eh_mangotinho = int(hid.get("tipo", 2)) == 1
        classe = "HoseReel" if eh_mangotinho else "Hydrant"
        nome = hid.get("sistema", "hidrante")
        for i, (x, y) in enumerate(_pts_perimetro_real(nh, C, L, inset=0.3), 1):
            M.append(_eq(classe, "HID%d" % i, nome.capitalize(),
                         [500, 250, 900], [x, y, 900.0], "Aco"))

    # EXTINTORES - 4 cantos (recuo 1 m), a 1,0 m
    for i, (fx, fy) in enumerate(((0.06, 0.06), (0.94, 0.06), (0.06, 0.94), (0.94, 0.94)), 1):
        M.append(_eq("Extinguisher", "EXT%d" % i, "Extintor portatil",
                     [200, 200, 600], [fx * C * 1000.0, fy * L * 1000.0, 1000.0], "Aco"))

    # RESERVATORIO DE INCENDIO (maior reserva entre hidrantes e sprinklers) fora da planta
    reservas = [g[k]["reserva_m3"] for k in ("hidrantes", "sprinklers")
                if g[k].get("reserva_m3")]
    if reservas:
        V = max(reservas)                        # m3
        lado = 3000.0                            # 3 x 3 m em planta
        alt = max(1000.0, V / 9.0 * 1000.0)      # altura p/ conter o volume (mm)
        M.append(_eq("WaterTank", "RTI", "Reserva de incendio %.0f m3" % V,
                     [lado, lado, alt], [-3000.0, L * 500.0, alt / 2.0], "Concreto"))
    return M


def emitir_bim(r, path, nome="GalpaoSegurancaIncendio"):
    """Emite o IFC4 dos equipamentos de seguranca contra incendio (via ifc_emit puro).
    None se faltar geometria ou o ifcopenshell."""
    import ifc_emit
    if not ifc_emit.disponivel():
        return None
    membros = membros_bim(r)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(membros, path, nome=nome, secao_em_metros=True)


def relatorio_pt(r):
    g = r["gates"]; sp = r["spec"]
    L = ["SEGURANCA CONTRA INCENDIO - GALPAO (NBR 10898/16820/17240)",
         f"  Galpao {sp['C']:.0f} x {sp['L']:.0f} m ; pe-direito {sp['H']:.1f} m",
         f"  Iluminacao de emergencia (NBR 10898): E >= {g['iluminacao_emergencia']['E_min_lux']:.0f} lux ; "
         f"{g['iluminacao_emergencia']['N_aclaramento']} pontos de aclaramento + "
         f"{g['iluminacao_emergencia']['N_balizamento']} de balizamento ; "
         f"autonomia {g['iluminacao_emergencia']['autonomia_h']:.0f} h ; "
         f"comutacao <= {g['iluminacao_emergencia']['comutacao_max_s']:.0f} s",
         f"  Sinalizacao (NBR 16820): placa {g['sinalizacao']['placa_lado_mm']} mm ; "
         f"{g['sinalizacao']['N_placas']} placas ; espacamento {g['sinalizacao']['espacamento_m']:.0f} m ; "
         f"letra >= {g['sinalizacao']['letra_min_mm']:.0f} mm",
         f"  Deteccao e alarme (NBR 17240): {g['deteccao_alarme']['N_detectores']} detectores "
         f"({g['deteccao_alarme']['tipo_detector']}) + {g['deteccao_alarme']['N_acionadores']} acionadores ; "
         f"{g['deteccao_alarme']['tensao_Vcc']:.0f} Vcc ; autonomia supervisao "
         f"{g['deteccao_alarme']['autonomia_supervisao_h']:.0f} h",
         (f"  Sprinklers (NBR 10897): risco {g['sprinklers']['risco']} ; "
          f"{g['sprinklers']['N_chuveiros']} chuveiros ; reserva {g['sprinklers']['reserva_m3']} m3 ; "
          f"pressao {g['sprinklers']['pressao_bar']} bar"
          if g['sprinklers']['risco'] else "  Sprinklers: " + g['sprinklers']['nota']),
         (f"  Hidrantes (NBR 13714): sistema tipo {g['hidrantes']['tipo']} "
          f"({g['hidrantes']['sistema']}) ; {g['hidrantes']['N_hidrantes']} hidrantes ; "
          f"vazao {g['hidrantes']['vazao_total_Lmin']:.0f} L/min (2 jatos) ; "
          f"reserva {g['hidrantes']['reserva_m3']} m3"
          if g['hidrantes']['tipo'] else "  Hidrantes: " + g['hidrantes']['nota']),
         f"  RESULTADO: {'ATENDE' if r['ATENDE'] else 'REPROVA - ' + ', '.join(r['reprovados'])}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    spec = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0},
            "sprinklers": {"altura_estoque_m": 3.0},
            "hidrantes": {"ocupacao": "industrial_I2"}}
    r = rodar(spec)
    g = r["gates"]
    assert g["iluminacao_emergencia"]["N_aclaramento"] == 6
    assert g["iluminacao_emergencia"]["autonomia_h"] == 2.0
    assert g["sinalizacao"]["placa_lado_mm"] == 600
    assert g["deteccao_alarme"]["N_detectores"] == 10
    assert g["deteccao_alarme"]["tensao_Vcc"] == 24.0
    assert g["sprinklers"]["risco"] == "ordinario_II" and g["sprinklers"]["N_chuveiros"] == 67
    assert g["hidrantes"]["tipo"] == 2 and g["hidrantes"]["reserva_m3"] == 36.0
    assert r["ATENDE"] is True
    print(relatorio_pt(r))
    print("galpao_seguranca_incendio self-test PASSED")


if __name__ == "__main__":
    _selftest()
