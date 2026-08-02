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
    }
    res = {"spec": {"C": C, "L": L, "H": H}, "iluminacao_emergencia": emerg,
           "sinalizacao": sinal, "deteccao_alarme": alarme, "sprinklers": sprk,
           "gates": gates}
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
         f"  RESULTADO: {'ATENDE' if r['ATENDE'] else 'REPROVA - ' + ', '.join(r['reprovados'])}"]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    spec = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0},
            "sprinklers": {"altura_estoque_m": 3.0}}
    r = rodar(spec)
    g = r["gates"]
    assert g["iluminacao_emergencia"]["N_aclaramento"] == 6
    assert g["iluminacao_emergencia"]["autonomia_h"] == 2.0
    assert g["sinalizacao"]["placa_lado_mm"] == 600
    assert g["deteccao_alarme"]["N_detectores"] == 10
    assert g["deteccao_alarme"]["tensao_Vcc"] == 24.0
    assert g["sprinklers"]["risco"] == "ordinario_II" and g["sprinklers"]["N_chuveiros"] == 67
    assert r["ATENDE"] is True
    print(relatorio_pt(r))
    print("galpao_seguranca_incendio self-test PASSED")


if __name__ == "__main__":
    _selftest()
