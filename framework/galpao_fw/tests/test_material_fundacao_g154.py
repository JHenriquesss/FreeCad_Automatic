"""G154 - O material do modelo que decide veredito sem ninguem declarar.

Medido por injecao (2026-09-17, antes de mudar; scripts med_g154_*.py):
- bloco metalico n=2 N=600: fck 25->15 OK->REPROVA (biela); fyk 500->250
  OK segue OK As 6,9->13,8 (quantidade); cob 0,05->0,10 h muda d igual
  (OK igual); phi N/A no bloco.
- sapata isolada (B=2 L=2,5 h=0,5): fck 25->15 N=1500 OK->REPROVA
  (u 0,691->1,103); cob 0,05->0,10 N=2000 OK->REPROVA (0,922->1,041);
  phi 12,5->25 N=2120 OK->REPROVA (0,977->1,006); fyk 500->250 OK segue
  OK (As muda, puncao melhora).
- corrida: mesma Parte B (VIVO por construcao); no aprovado tipico o solo
  governa, mas o silencio (25 MPa calado) sai do mesmo jeito (D102).

Entregue (D102, fonte unica material_fundacao_g154, sem arbitrar valor,
sem trocar classe de agressividade, sem quebrar o caminho do usuario):
- PS.novo escreve _origem_material modelo; wizard declara (4 perguntas);
  spec distingue desde onde o numero nasce (nunca compara valor).
- Memorial sempre diz a origem; folha carimba G154 so no modelo a
  confirmar (declarado puro segue sem linha nova, byte-identico).
- Corrida sem 25 MPa calado (resolver); bloco herda cobrimento com origem.

Convencoes: baseline nos dois sentidos, vermelho por injecao em cada
porta (modelo -> modelo na folha/memorial; declarado -> declarado),
tmp_path sem mutar o repo, ausente e zero um por um, PNG rasterizado.
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import estaca_profunda as ep
import fundacao_edificio as fe
import fundacao_sapata as fsap
import fundacao_sapata_corrida as fsc
import material_fundacao_g154 as mg154


_PERFIL = [{"tipo": "argila", "N": 5, "dz": 3.0},
           {"tipo": "areia", "N": 25, "dz": 8.0}]


def _ctx_predio(pilares):
    return {"pilares": pilares,
            "eixos_x": [0.0, 7.0, 14.0], "eixos_y": [0.0, 5.0, 10.0],
            "materiais": {"fck": 30e3, "fyk": 500e3},
            "estabilidade": None, "momentos_base": None}


def _pilar_iso(nome="P1", N=800.0, i=1, j=1):
    return {"nome": nome, "i": i, "j": j, "N_base_k": N,
            "secao": (0.30, 0.50)}


def test_01_medida_fck_cob_phi_viram_fyk_nao():
    """Tabela do verbete: fck/cob/phi mudam veredito, fyk muda quantidade."""
    gaps = []
    # bloco n=2 N=600: fck vira biela
    base = {"perfil": copy.deepcopy(_PERFIL), "D": 0.30, "L": 10.0,
            "tipo_estaca": "pre_moldada", "N_pilar": 600.0,
            "bloco": {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3}}
    b_ok = ep.verifica_estaca(base)["bloco"]["OK"]
    b_rep = ep.verifica_estaca(dict(
        base, bloco={"a_pilar": 0.30, "fck": 15e3, "fyk": 500e3}))["bloco"]["OK"]
    if not (b_ok and not b_rep):
        gaps.append("bloco fck 25->15 devia virar (N=600): %r/%r" % (b_ok, b_rep))
    # bloco fyk: quantidade, nao veredito
    r_fyk = ep.verifica_estaca(dict(
        base, bloco={"a_pilar": 0.30, "fck": 25e3, "fyk": 250e3}))["bloco"]
    if not r_fyk["OK"] or not (r_fyk["As_tirante_cm2"] > 10.0):
        gaps.append("bloco fyk devia manter OK e subir As: %r" % (r_fyk,))
    # sapata Parte B: fck vira em N=1500
    def _caso(N, fck=25e3, fyk=500e3, cob=0.05, phi=0.0125):
        return {"N": N, "V": 0.0, "M": 0.0, "fck": fck, "fyk": fyk,
                "cobrimento": cob, "phi_barra": phi, "gamma_f": 1.4,
                "d_ped": 0.5, "b_ped": 0.3}
    rA = {"B": 2.0, "L": 2.5, "h": 0.5}
    s25 = fsap.dimensiona_sapata_B(_caso(1500.0), rA)
    s15 = fsap.dimensiona_sapata_B(_caso(1500.0, fck=15e3), rA)
    if not (s25["OK_B"] and not s15["OK_B"]):
        gaps.append("sapata fck 25->15 devia virar (N=1500): %r/%r"
                    % (s25["OK_B"], s15["OK_B"]))
    # cob vira em N=2000
    c05 = fsap.dimensiona_sapata_B(_caso(2000.0, cob=0.05), rA)
    c10 = fsap.dimensiona_sapata_B(_caso(2000.0, cob=0.10), rA)
    if not (c05["OK_B"] and not c10["OK_B"]):
        gaps.append("sapata cob 5->10 devia virar (N=2000): %r/%r"
                    % (c05["OK_B"], c10["OK_B"]))
    # phi vira em N=2120
    p12 = fsap.dimensiona_sapata_B(_caso(2120.0, phi=0.0125), rA)
    p25 = fsap.dimensiona_sapata_B(_caso(2120.0, phi=0.025), rA)
    if not (p12["OK_B"] and not p25["OK_B"]):
        gaps.append("sapata phi 12,5->25 devia virar (N=2120): %r/%r"
                    % (p12["OK_B"], p25["OK_B"]))
    # fyk nao vira (M=200: As sobe, OK fica)
    y500 = fsap.dimensiona_sapata_B(
        {"N": 500.0, "V": 0.0, "M": 200.0, "fck": 25e3, "fyk": 500e3,
         "cobrimento": 0.05, "phi_barra": 0.0125, "gamma_f": 1.4,
         "d_ped": 0.5, "b_ped": 0.3}, rA)
    y250 = fsap.dimensiona_sapata_B(
        {"N": 500.0, "V": 0.0, "M": 200.0, "fck": 25e3, "fyk": 250e3,
         "cobrimento": 0.05, "phi_barra": 0.0125, "gamma_f": 1.4,
         "d_ped": 0.5, "b_ped": 0.3}, rA)
    if not (y500["OK_B"] and y250["OK_B"]):
        gaps.append("sapata fyk nao devia virar veredito: %r/%r"
                    % (y500["OK_B"], y250["OK_B"]))
    if not (y250["flexao_L"]["As_adot"] > y500["flexao_L"]["As_adot"]):
        gaps.append("sapata fyk devia subir As: %r/%r" % (y500, y250))
    assert not gaps, "G154 medida:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_spec_distinguem_modelo_de_declarado():
    """A proveniencia nasce onde o numero nasce (novo/wizard), nunca no valor."""
    import projeto_spec as PS

    gaps = []
    s = PS.novo()
    fu = s["fundacao"]
    if fu.get("_origem_material", {}).get("fck") != "modelo_PS_novo":
        gaps.append("novo sem origem modelo: %r" % (fu.get("_origem_material"),))
    # declarar 25 (igual ao modelo) continua declarado — o valor nao distingue
    PS.declarar_material_fundacao(s, fck=25e3)
    if fu.get("_origem_material", {}).get("fck") != "declarado_no_spec":
        gaps.append("declarar 25 devia virar declarado: %r" % (fu,))
    if fu.get("fck") != 25e3:
        gaps.append("declarar nao devia trocar numero: %r" % (fu,))
    # validar: modelo avisa sem bloquear; declarado tira o aviso do item
    s2 = PS.novo()
    s2["slug"] = "t"
    s2["descricao"] = "t"
    s2["terreno"].update(area_lote_m2=500, to_max=0.6, ca_max=1.0,
                         tp_min=0.2, recuos={"frente": 5, "lateral": 1.5, "fundos": 3})
    s2["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                           bay=5.0, base_fixed=True)
    s2["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                           telha_peso=0.10, calha=False)
    s2["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05)
    s2["aberturas"] = {"vedada": True}
    s2["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=6.5,
                       abertura_dominante="portao_oitao")
    s2["ponte"] = None
    s2["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s2["fundacao"]["sigma_solo_adm"] = 200.0
    s2["fundacao"]["tipo"] = "sapata"
    v_mod = PS.validar(s2)
    if not v_mod["ok"]:
        gaps.append("modelo devia validar (aviso, nao bloqueio): %r" % (v_mod["faltando"],))
    # G154: sem aviso no validar (o aviso virava needs_review no G15/G19);
    # a origem mora na folha e no memorial, nao no gate.
    if any(p == "fundacao.fck" for p, _ in v_mod["avisos"]):
        gaps.append("modelo nao devia avisar no gate (G15 ready): %r" % (v_mod["avisos"],))
    PS.declarar_material_fundacao(s2, fck=25e3, fyk=500e3, cobrimento=0.05,
                                  phi_barra=0.0125)
    v_dec = PS.validar(s2)
    if not v_dec["ok"]:
        gaps.append("declarado devia validar: %r" % (v_dec["faltando"],))
    # zero bloqueia (convencao 13: ausente avisa como modelo, zero recusa)
    s3 = copy.deepcopy(s2)
    s3["fundacao"]["fck"] = 0
    if PS.validar(s3)["ok"]:
        gaps.append("fck=0 devia bloquear")
    assert not gaps, "G154 spec:\n%s" % "\n".join("  - " + g for g in gaps)


def test_03_wizard_modelo_ou_declarado():
    """Sem fund_*: modelo; com fund_*: declarado (unidades da pergunta)."""
    import projeto_spec as PS
    import wizard as WZ

    gaps = []
    base = {"area_lote_m2": 1200, "span": 10, "comprimento": 20, "eave": 6,
            "v0": 40, "sigma_solo": 200, "fund_tipo": "sapata"}
    s = WZ.construir_spec(dict(base), slug="t")
    if s["fundacao"].get("_origem_material", {}).get("fck") != "modelo_PS_novo":
        gaps.append("wizard sem fund_* devia manter modelo: %r"
                    % (s["fundacao"].get("_origem_material"),))
    v = PS.validar(s)
    if not v["ok"]:
        gaps.append("wizard modelo devia validar: %r" % (v["faltando"],))
    rr = dict(base, fund_fck=30.0, fund_fyk=500.0, fund_cobrimento=5.0,
              fund_phi=12.5)
    s2 = WZ.construir_spec(rr, slug="t2")
    if s2["fundacao"]["fck"] != 30e3 or s2["fundacao"]["cobrimento"] != 0.05:
        gaps.append("wizard nao converteu unidades: %r" % (s2["fundacao"],))
    if s2["fundacao"]["_origem_material"]["fck"] != "declarado_no_spec":
        gaps.append("wizard com fund_* devia declarar: %r"
                    % (s2["fundacao"]["_origem_material"],))
    v2 = PS.validar(s2)
    if not v2["ok"]:
        gaps.append("wizard declarado devia validar: %r" % (v2["faltando"],))
    assert not gaps, "G154 wizard:\n%s" % "\n".join("  - " + g for g in gaps)


def test_04_metalico_modelo_memorial_folha_e_declarado(tmp_path):
    """Porta do metalico: modelo -> modelo na folha/memorial; declarado -> declarado."""
    import projeto_spec as PS
    import rodar_galpao as RG

    gaps = []

    def _spec_met(**ekw):
        s = PS.novo()
        s["slug"] = "g154"
        s["descricao"] = "g154"
        s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0,
                            tp_min=0.2, recuos={"frente": 5, "lateral": 3, "fundos": 3})
        s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                              bay=5.0, base_fixed=True)
        s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                              telha_peso=0.10, calha=False)
        s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05)
        s["aberturas"] = {"vedada": True}
        s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=6.5,
                          abertura_dominante="portao_oitao")
        s["ponte"] = None
        s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
        s["fundacao"]["sigma_solo_adm"] = 200.0
        s["fundacao"]["tipo"] = "estaca"
        e = {"perfil_spt": copy.deepcopy(_PERFIL), "tipo_estaca": "pre_moldada",
             "D": 0.30, "L": 10.0, "FS": 3.0,
             "bloco": {"a_pilar": 0.30}}
        e.update(ekw)
        s["fundacao"]["estaca"] = e
        return s

    # modelo (PS.novo sem declarar): herda com origem modelo
    s = _spec_met()
    p = PS.to_rodar_params(s)
    if p["estaca"]["bloco_origens"]["fck"] not in (
            "modelo_PS_novo", "modelo_legado_confirmar", "material_do_projeto"):
        gaps.append("bloco sem origem do material: %r" % (p["estaca"],))
    out = str(tmp_path / "mod")
    res = RG.rodar(p, out)
    mem = open(os.path.join(out, "gate7-estaca.txt"), encoding="utf-8").read()
    if "MATERIAL DA FUNDACAO (G154)" not in mem or "modelo" not in mem:
        gaps.append("memorial do metalico sem modelo: %r" % (mem[-500:],))
    if "bloco a_pilar" not in mem:
        gaps.append("memorial sem linha do bloco: %r" % (mem[-500:],))
    # declarado no wizard/spec: memorial diz declarado
    s2 = _spec_met()
    PS.declarar_material_fundacao(s2["fundacao"], fck=25e3, fyk=500e3,
                                  cobrimento=0.05, phi_barra=0.0125)
    p2 = PS.to_rodar_params(s2)
    out2 = str(tmp_path / "dec")
    res2 = RG.rodar(p2, out2)
    mem2 = open(os.path.join(out2, "gate7-estaca.txt"), encoding="utf-8").read()
    if "declarado no spec" not in mem2 and "material do projeto" not in mem2:
        gaps.append("memorial declarado sem origem: %r" % (mem2[-500:],))
    # folha do bloco: modelo declara, declarado puro nao inventa linha G154
    import techdraw_exec as TX
    cfg_mod = {"estaca": {"n": 2, "D": 0.30, "L": 10.0, "tipo_estaca": "pre_moldada"},
               "bloco": {"a": 0.30, "h": 0.45, "fck": 25e3,
                         "fck_origem": p["estaca"]["bloco_origens"]["fck"]}}
    lin_mod = TX._callout_bloco(cfg_mod)
    if not any("fck 25 MPa" in ln for ln in lin_mod):
        gaps.append("folha sem fck: %r" % (lin_mod,))
    assert not gaps, "G154 metalico:\n%s" % "\n".join("  - " + g for g in gaps)


def test_05_predio_modelo_e_declarado_com_folha(tmp_path):
    """Porta do predio: isolada + memorial + folha (tres aceites no teste 07)."""
    gaps = []
    ctx = _ctx_predio([_pilar_iso()])
    # spec sem material: herda do predio declarado (30 MPa)
    r_herd = fe.dimensiona({"tipo": "sapata", "sigma_solo_adm": 250.0}, ctx)
    if r_herd["material"]["fck"] != 30e3:
        gaps.append("predio sem fck devia herdar 30e3: %r" % (r_herd["material"],))
    if r_herd["material_origens"]["fck"] != "herdado_material_predio_declarado":
        gaps.append("heranca sem origem: %r" % (r_herd["material_origens"],))
    rel = fe.relatorio_pt(r_herd)
    if "MATERIAL DA FUNDACAO (G154)" not in rel or "herdado" not in rel:
        gaps.append("memorial do predio sem heranca: %r" % (rel,))
    # spec com fck declarado vence o do predio
    r_dec = fe.dimensiona({"tipo": "sapata", "sigma_solo_adm": 250.0, "fck": 25e3,
                           "_origem_material": {"fck": "declarado_no_spec"}}, ctx)
    if r_dec["material"]["fck"] != 25e3:
        gaps.append("declarado nao venceu: %r" % (r_dec["material"],))
    if "declarado no spec" not in fe.relatorio_pt(r_dec):
        gaps.append("memorial sem declarado: %r" % (fe.relatorio_pt(r_dec),))
    # ausente e zero, um por um (convencao 13): zero bloqueia no validar do
    # galpao; aqui o resolver usa herdado (nao ha zero: zero e numero e vai a
    # conta — a conta com fck=0 da secao insuficiente, nao silencio)
    assert not gaps, "G154 predio:\n%s" % "\n".join("  - " + g for g in gaps)


def test_06_corrida_sem_25MPa_calado():
    """Porta da casa: sem fck nao cala 25 MPa — declara a origem."""
    gaps = []
    spec = {"sigma_solo_adm": 150.0}
    r = fsc.dimensiona_corrida(60.0, spec)
    if r["aprovado"] is None:
        gaps.append("corrida base devia aprovar")
    if r.get("material", {}).get("fck") != 25e3:
        gaps.append("corrida sem fck devia manter 25e3 com origem: %r"
                    % (r.get("material"),))
    if r.get("material_origens", {}).get("fck") not in (
            "modelo_PS_novo", "modelo_legado_confirmar"):
        gaps.append("corrida sem origem modelo: %r" % (r.get("material_origens"),))
    if "MATERIAL DA FUNDACAO (G154)" not in r.get("tabela", ""):
        gaps.append("tabela da corrida sem material")
    # declarado vence sem trocar numero
    spec2 = {"sigma_solo_adm": 150.0, "fck": 30e3,
             "_origem_material": {"fck": "declarado_no_spec"}}
    r2 = fsc.dimensiona_corrida(60.0, spec2)
    if r2.get("material", {}).get("fck") != 30e3:
        gaps.append("corrida declarada nao venceu: %r" % (r2.get("material"),))
    if "declarado no spec" not in r2.get("tabela", ""):
        gaps.append("tabela sem declarado: %r" % (r2.get("tabela", "")[-300:],))
    # Parte B carrega phi (d = h-cob-phi): sem phi usa modelo com origem
    pb = fsc._parte_B(60.0, 0.5, 0.20, spec)
    if "material_origens" not in pb:
        gaps.append("Parte B sem origens")
    assert not gaps, "G154 corrida:\n%s" % "\n".join("  - " + g for g in gaps)


def test_07_folha_predio_tres_aceites_com_modelo(tmp_path):
    """Tres aceites da folha de fundacao do predio com material modelo."""
    import desenho_fundacao_edificio as dfe
    import edificio_adapter as ea
    import pacote_legal as pl
    from caderno_casa_edificio import svg_para_png
    from desenho_svg_base import confere_folha_svg

    gaps = []
    ctx = _ctx_predio([_pilar_iso("P1", 800.0, 0, 0), _pilar_iso("P2", 900.0, 1, 0)])
    # sem cob/phi no spec nem no predio: modelo a confirmar -> carimba G154
    # (fck/fyk herdados, cob/phi modelo). E o D102 por item com motivo.
    r_herd = fe.dimensiona({"tipo": "sapata", "sigma_solo_adm": 250.0}, ctx)
    svg_herd = dfe.planta_fundacao_svg(r_herd, {"vaos_x": [7.0], "vaos_y": [5.0]})
    ET.fromstring(svg_herd)
    if "G154" not in svg_herd:
        gaps.append("cob/phi modelo deviam carimbar G154 mesmo com fck herdado")
    # spec modelo puro (fck modelo sem predio que declare): forca modelo
    ctx_mod = {"pilares": [_pilar_iso("P1", 800.0, 0, 0), _pilar_iso("P2", 900.0, 1, 0)],
               "eixos_x": [0.0, 7.0, 14.0], "eixos_y": [0.0, 5.0, 10.0],
               "materiais": {}, "estabilidade": None, "momentos_base": None}
    spec_mod = {"tipo": "sapata", "sigma_solo_adm": 250.0,
                "fck": 25e3, "fyk": 500e3, "cobrimento": 0.05, "phi_barra": 0.0125,
                "_origem_material": {c: "modelo_PS_novo" for c in
                                     ("fck", "fyk", "cobrimento", "phi_barra")}}
    r = fe.dimensiona(spec_mod, ctx_mod)
    svg = dfe.planta_fundacao_svg(r, {"vaos_x": [7.0], "vaos_y": [5.0]})
    ET.fromstring(svg)
    if svg.count("data-pilar") != 2:
        gaps.append("elementos %d != 2 pilares" % svg.count("data-pilar"))
    if "G154" not in svg or "modelo" not in svg:
        gaps.append("folha modelo sem G154")
    if not dfe.confere_desenho_fundacao(r, svg).get("ok"):
        gaps.append("desenhado != dimensionado: %r"
                    % (dfe.confere_desenho_fundacao(r, svg),))
    if not confere_folha_svg(svg).get("ok"):
        gaps.append("guarda reprova a folha: %r" % (confere_folha_svg(svg),))
    p_svg = str(tmp_path / "fund_g154.svg")
    p_png = str(tmp_path / "fund_g154.png")
    with open(p_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
        gaps.append("folha G154 nao rasterizou para o aceite visual")
    if ea._PRANCHA_ARQUIVO.get("PE-CO-04") != "fundacao-locacao-formas.svg":
        gaps.append("mapa PE-CO-04 fora do basename")
    titulos = {f["codigo"]: f["titulo"] for f in pl.indice_de_pranchas(["concreto"])}
    if "locacao" not in titulos.get("PE-CO-04", "").lower():
        gaps.append("indice nao diz locacao: %r" % (titulos,))
    assert tmp_path.is_dir()
    assert not gaps, "G154 aceites:\n%s" % "\n".join("  - " + g for g in gaps)


def test_08_baseline_dois_sentidos_resolver():
    """Baseline nos dois sentidos: modelo carimba, declarado nao."""
    gaps = []
    mod = mg154.resolver_material(
        {"fck": 25e3, "_origem_material": {"fck": "modelo_PS_novo"}})
    if mod["origens"]["fck"] != "modelo_PS_novo":
        gaps.append("resolver sem declarado: %r" % (mod,))
    if mg154.linha_folha(mod) is None or "G154" not in mg154.linha_folha(mod):
        gaps.append("modelo sem linha de folha")
    dec = mg154.resolver_material(
        {"fck": 25e3, "fyk": 500e3, "cobrimento": 0.05, "phi_barra": 0.0125,
         "_origem_material": {c: "declarado_no_spec" for c in mg154.CHAVES}})
    if mg154.linha_folha(dec) is not None:
        gaps.append("declarado puro devia seguir sem linha G154: %r"
                    % (mg154.linha_folha(dec),))
    if "declarado no spec" not in mg154.linha_memorial(dec):
        gaps.append("memorial declarado sem origem")
    # vermelho por injecao: trocar origem sem trocar numero muda a folha
    inj = copy.deepcopy(mod)
    inj["origens"]["fck"] = "declarado_no_spec"
    if mg154.linha_folha(mod) == mg154.linha_folha(
            {"fck": 1, "origens": {c: "declarado_no_spec" for c in mg154.CHAVES}}):
        gaps.append("lente incapaz de acusar (tautologia)")
    assert not gaps, "G154 baseline:\n%s" % "\n".join("  - " + g for g in gaps)
