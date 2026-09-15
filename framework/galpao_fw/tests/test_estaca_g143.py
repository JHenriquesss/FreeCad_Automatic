"""G143 - A estaca do galpao com diametro e comprimento que ninguem declarou.

Medido (2026-09-15, antes de mudar, galpao 10x40x6, tipo_fundacao="estaca",
perfil SPT de test_build_concreto.py:114):
- sem D_estaca/L_estaca a conta usava D=0,30/L=8,0 calados
  (galpao_concreto.py:351) e a PE-CO-04 desenhava "D30 L8" como projeto;
- L 8->10: util 0,116->0,103; D 0,30->0,40: util 0,116->0,071; L=0: n 1->5
  em silencio; D=0: TypeError cru; tipo pre_moldada->escavada:
  util 0,116->0,198, e com Q_roof=0,25/L=6 no perfil fraco a pre_moldada
  ATENDE (n=2) e a escavada REPROVA (n=4) — o tipo INVERTE o veredito;
- cota_apoio/B_max nao mudam o caminho com tipo explicito, mas com tipo
  auto B_max 0,5->estaca e >=1,0->sapata (carga alta), e cota 2,0->estaca
  e 2,5->sapata — decidem o tipo;
- mu_solo/sigma_solo_adm ignorados no caminho estaca (0,9/500 -> identico).

Entregue (D102, sem arbitrar valor):
- D/L/tipo: RECUSA NOMEADA com tipo_fundacao="estaca" (ou auto-estaca);
- cota/B_max: mesmos numeros, origem dita (resultado, memorial, folha,
  sinais assumed_default); mu/sigma: N/A na estaca, origem dita na sapata.

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao (valor ausente -> recusa ou declaracao; declarado ->
numero do spec), substring -> parse -> renderizar (PNG olhado), injecao
em cada porta de entrada (spec direto, sub-spec turnkey; wizard nao
alimenta o concreto — terceiro valor declarado), ausente e zero um por
um, casa e predio byte-identicos.
"""
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import galpao_concreto as gc

_PERFIL = [{"tipo": "argila", "N": 5, "dz": 3.0},
           {"tipo": "areia", "N": 25, "dz": 8.0}]
_PERFIL_FRACO = [{"tipo": "argila", "N": 4, "dz": 6.0},
                 {"tipo": "areia", "N": 12, "dz": 8.0}]


def _spec(**kw):
    base = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "s1": 1.0, "s3": 1.0, "G_roof": 0.30, "Q_roof": 0.25,
            "fck": 30e3, "fyk": 500e3, "travamento_longitudinal": "topo",
            "tipo_fundacao": "estaca", "perfil_spt": [dict(c) for c in _PERFIL]}
    base.update(kw)
    return base


def _recusa_marca(spec, marca):
    with pytest.raises(ValueError) as exc:
        gc.rodar(spec)
    assert marca in str(exc.value), (marca, str(exc.value)[:200])


def test_01_medido_default_calado_vira_recusa():
    """Remeça: o que era default calado agora recusa com nome."""
    gaps = []
    for kw, marca in [
            ({}, "d_estaca_nao_declarada"),
            ({"D_estaca": 0.30}, "l_estaca_nao_declarada"),
            ({"D_estaca": 0.30, "L_estaca": 8.0},
             "tipo_estaca_nao_declarada")]:
        try:
            gc.rodar(_spec(**kw))
            gaps.append("devia recusar %s" % marca)
        except ValueError as exc:
            if marca not in str(exc):
                gaps.append("erro sem a marca %s: %r" % (marca, exc))
    # declarado -> o numero do spec chega a capacidade e a geometria
    r = gc.rodar(_spec(D_estaca=0.30, L_estaca=10.0,
                       tipo_estaca="pre_moldada"))
    cap = r["estaca"]["capacidade"]
    if (cap.get("D"), cap.get("L")) != (0.30, 10.0):
        gaps.append("declarado nao chegou a conta: %r" % (cap,))
    if "L10" not in r["gates"]["fundacao"]["geom"]:
        gaps.append("geometria sem o L declarado: %r"
                    % (r["gates"]["fundacao"]["geom"],))
    # o numero muda geometria e capacidade (tabela do verbete)
    r8 = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                        tipo_estaca="pre_moldada"))
    if r8["estaca"]["grupo"]["util"] == r["estaca"]["grupo"]["util"]:
        gaps.append("L 8->10 devia mudar a capacidade")
    assert not gaps, "G143 medida:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_recusa_um_por_um_ausente_e_zero():
    """Convencao 13: ausente e zero, um por um, cada um com o seu nome."""
    gaps = []
    casos = [
        ({}, "d_estaca_nao_declarada"),
        ({"D_estaca": 0.30}, "l_estaca_nao_declarada"),
        ({"D_estaca": 0.30, "L_estaca": 8.0}, "tipo_estaca_nao_declarada"),
        ({"D_estaca": 0, "L_estaca": 8.0, "tipo_estaca": "pre_moldada"},
         "d_estaca_invalida"),
        ({"D_estaca": 0.30, "L_estaca": 0, "tipo_estaca": "pre_moldada"},
         "l_estaca_invalida"),
        ({"D_estaca": -0.30, "L_estaca": 8.0, "tipo_estaca": "pre_moldada"},
         "d_estaca_invalida"),
        ({"D_estaca": 0.30, "L_estaca": 8.0, "tipo_estaca": "tubarole"},
         "tipo_estaca_invalida"),
        ({"D_estaca": True, "L_estaca": 8.0, "tipo_estaca": "pre_moldada"},
         "d_estaca_invalida"),
    ]
    for kw, marca in casos:
        try:
            gc.rodar(_spec(**kw))
            gaps.append("devia recusar %s (%r)" % (marca, kw))
        except ValueError as exc:
            if marca not in str(exc):
                gaps.append("erro sem a marca %s: %r" % (marca, exc))
    # zero e invalido nunca viram n=5 silencioso nem TypeError cru
    try:
        gc.rodar(_spec(D_estaca=0.30, L_estaca=0,
                       tipo_estaca="pre_moldada"))
        gaps.append("L=0 devia recusar, nao virar n=5")
    except ValueError as exc:
        if "l_estaca_invalida" not in str(exc):
            gaps.append("L=0 sem o nome: %r" % (exc,))
    except TypeError as exc:
        gaps.append("L=0 com TypeError cru: %r" % (exc,))
    assert not gaps, "G143 recusas:\n%s" % "\n".join("  - " + g for g in gaps)


def test_03_tipo_decide_veredito():
    """O tipo INVERTE o veredito: pre_moldada ATENDE, escavada REPROVA."""
    gaps = []
    kw = {"perfil_spt": [dict(c) for c in _PERFIL_FRACO], "D_estaca": 0.30,
          "L_estaca": 6.0, "Q_roof": 0.25, "G_roof": 0.50}
    r_pre = gc.rodar(_spec(tipo_estaca="pre_moldada", **kw))
    r_esc = gc.rodar(_spec(tipo_estaca="escavada", **kw))
    if r_pre["estaca"]["grupo"]["util"] == r_esc["estaca"]["grupo"]["util"]:
        gaps.append("tipo devia mudar a capacidade")
    if not (r_pre["gates"]["fundacao"]["OK"]
            and not r_esc["gates"]["fundacao"]["OK"]):
        gaps.append("tipo devia inverter o veredito: pre=%r esc=%r"
                    % (r_pre["gates"]["fundacao"]["OK"],
                       r_esc["gates"]["fundacao"]["OK"]))
    assert not gaps, "G143 tipo:\n%s" % "\n".join("  - " + g for g in gaps)


def test_04_portas_de_entrada_direto_e_turnkey():
    """Convencao 11: spec direto e sub-spec do turnkey; wizard N/A."""
    import galpao_turnkey as tk

    gaps = []
    # ausente recusa nas duas portas
    _recusa_marca(_spec(), "d_estaca_nao_declarada")
    conc = _spec(D_estaca=0.30, L_estaca=10.0, tipo_estaca="pre_moldada")
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 10.0,
                                "pe_direito": 6.0},
                  "concreto": {k: v for k, v in _spec().items()}})
    if R["disciplinas"]["concreto"].get("rodou") is not False:
        gaps.append("turnkey com D/L ausentes devia isolar o erro, nao rodar")
    else:
        erro = R["disciplinas"]["concreto"].get("erro", "")
        if "nao_declarada" not in erro:
            gaps.append("turnkey sem o nome da recusa: %r" % (erro,))
    # declarado -> o numero do spec nas duas portas
    R2 = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 10.0,
                                 "pe_direito": 6.0},
                   "concreto": conc})
    cap2 = R2["disciplinas"]["concreto"]["raw"]["estaca"]["capacidade"]
    if (cap2.get("D"), cap2.get("L")) != (0.30, 10.0):
        gaps.append("turnkey nao levou o declarado: %r" % (cap2,))
    # wizard: est_D/est_L sao do ProjetoSpec METALICO e nao alimentam o
    # concreto — declarar so eles segue recusando (terceiro valor).
    try:
        gc.rodar(_spec(est_D=0.30, est_L=10.0))
        gaps.append("est_D/est_L do wizard deviam ser ignorados pelo concreto")
    except ValueError as exc:
        if "d_estaca_nao_declarada" not in str(exc):
            gaps.append("wizard sem o nome: %r" % (exc,))
    # mu/sigma nao entram na conta da estaca (N/A declarado)
    r = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                       tipo_estaca="pre_moldada", mu_solo=0.9,
                       sigma_solo_adm=500.0))
    r0 = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                        tipo_estaca="pre_moldada"))
    if (r["estaca"]["grupo"]["util"] != r0["estaca"]["grupo"]["util"]
            or r["gates"]["fundacao"]["geom"]
            != r0["gates"]["fundacao"]["geom"]):
        gaps.append("mu/sigma deviam ser ignorados na estaca")
    assert not gaps, "G143 portas:\n%s" % "\n".join("  - " + g for g in gaps)


def test_05_cota_e_bmax_decidem_tipo_auto():
    """cota_apoio/B_max com tipo auto decidem sapata x estaca (medido)."""
    gaps = []
    perfil = [{"tipo": "argila", "N": 5, "dz": 3.0},
              {"tipo": "areia", "N": 30, "dz": 8.0}]
    base = {"perfil_spt": perfil, "D_estaca": 0.30, "L_estaca": 8.0,
            "tipo_estaca": "pre_moldada"}
    s = _spec(**dict(base, cota_apoio=2.0))
    del s["tipo_fundacao"]
    if gc.rodar(s)["tipo_fundacao"] != "estaca":
        gaps.append("cota 2,0 devia recomendar estaca")
    s = _spec(**dict(base, cota_apoio=2.5))
    del s["tipo_fundacao"]
    if gc.rodar(s)["tipo_fundacao"] != "sapata":
        gaps.append("cota 2,5 devia recomendar sapata")
    # B_max: carga alta, perfil mediano
    perfil_m = [{"tipo": "areia", "N": 10, "dz": 4.0},
                {"tipo": "areia", "N": 30, "dz": 8.0}]
    for bmax, esperado in [(0.5, "estaca"), (1.0, "sapata")]:
        s = _spec(perfil_spt=perfil_m, D_estaca=0.30, L_estaca=8.0,
                  tipo_estaca="pre_moldada", G_roof=2.0, Q_roof=2.0,
                  B_max_sapata=bmax)
        del s["tipo_fundacao"]
        if gc.rodar(s)["tipo_fundacao"] != esperado:
            gaps.append("B_max %s devia dar %s" % (bmax, esperado))
    # a origem viaja no resultado (default x declarado)
    r = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                       tipo_estaca="pre_moldada"))
    par = r["fundacao_parametros"]["parametros"]
    if par["cota_apoio"]["origem"] != "default" \
            or par["B_max_sapata"]["origem"] != "default":
        gaps.append("origem default sem marca: %r" % (par,))
    r2 = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                        tipo_estaca="pre_moldada", cota_apoio=1.5,
                        B_max_sapata=4.0))
    par2 = r2["fundacao_parametros"]["parametros"]
    if par2["cota_apoio"]["origem"] != "declarado_no_spec" \
            or par2["B_max_sapata"]["valor"] != 4.0:
        gaps.append("declarado sem origem: %r" % (par2,))
    assert not gaps, "G143 cota/B_max:\n%s" % "\n".join("  - " + g for g in gaps)


def test_06_memorial_folha_e_sinais_declaram():
    """O que foi default chega ao memorial, a folha e aos sinais."""
    import desenho_fundacao_edificio as dfe
    import galpao_adapter as ga

    gaps = []
    r = gc.rodar(_spec(D_estaca=0.30, L_estaca=10.0,
                       tipo_estaca="pre_moldada"))
    rel = gc.relatorio_pt(r)
    for termo in ("PARAMETROS DA FUNDACAO (G143)", "D=0,30", "L=10,0",
                  "pre_moldada", "declarado no spec", "nao se aplicam"):
        if termo not in rel:
            gaps.append("memorial sem %r" % termo)
    # sinais de revisao: cota/B defaultados acusam assumed_default por parte
    sig = ga._review_signals({"rodou": True, "raw": r})
    caminhos = {s["path"] for s in sig if s["code"] == "assumed_default"}
    if not any("cota_apoio" in p for p in caminhos):
        gaps.append("sinais sem cota_apoio: %r" % (caminhos,))
    if not any("B_max_sapata" in p for p in caminhos):
        gaps.append("sinais sem B_max_sapata: %r" % (caminhos,))
    if any("D_estaca" in p and "default" in p.lower() for p in caminhos):
        gaps.append("D declarado nao devia acusar default: %r" % (caminhos,))
    # com cota/B declarados os sinais deles somem
    r2 = gc.rodar(_spec(D_estaca=0.30, L_estaca=10.0,
                        tipo_estaca="pre_moldada", cota_apoio=1.5,
                        B_max_sapata=4.0))
    cam2 = {s["path"] for s in ga._review_signals({"rodou": True, "raw": r2})
            if s["code"] == "assumed_default"}
    if any("cota_apoio" in p or "B_max_sapata" in p for p in cam2):
        gaps.append("declarado segue acusando: %r" % (cam2,))
    # folha declara a proveniencia (D/L/tipo) sem recalcular
    fund, est, aus = dfe.adaptar_galpao_para_locacao(
        r, _spec(D_estaca=0.30, L_estaca=10.0, tipo_estaca="pre_moldada"))
    svg = dfe.planta_fundacao_svg(fund, est, ausencias=aus or None)
    ET.fromstring(svg)
    for termo in ("G143", "D30", "L10", "declarado no spec"):
        if termo not in svg:
            gaps.append("folha sem %r" % termo)
    conf = dfe.confere_desenho_fundacao(fund, svg)
    if not conf.get("ok"):
        gaps.append("desenhado != dimensionado: %r" % (conf,))
    assert not gaps, "G143 declaracao:\n%s" % "\n".join("  - " + g for g in gaps)


def test_07_producao_le_a_fonte_unica():
    """Convencao 8: os defaults da recomendacao saem do modulo, nao de
    literal — mesmo numero com e sem declaracao, origem diferente."""
    import estaca_parametros_g143 as g143

    gaps = []
    if (g143.COTA_APOIO_DEFAULT, g143.B_MAX_SAPATA_DEFAULT) != (0.5, 2.5):
        gaps.append("fonte unica fora dos numeros historicos")
    r_def = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                           tipo_estaca="pre_moldada"))
    r_dec = gc.rodar(_spec(D_estaca=0.30, L_estaca=8.0,
                           tipo_estaca="pre_moldada", cota_apoio=0.5,
                           B_max_sapata=2.5))
    if (r_def["geotecnia"] or {}).get("justificativa") \
            != (r_dec["geotecnia"] or {}).get("justificativa"):
        gaps.append("mesmo numero devia dar a mesma recomendacao")
    p_def = r_def["fundacao_parametros"]["parametros"]
    p_dec = r_dec["fundacao_parametros"]["parametros"]
    if p_def["cota_apoio"]["origem"] != "default" \
            or p_dec["cota_apoio"]["origem"] != "declarado_no_spec":
        gaps.append("origem nao distingue default de declarado")
    assert not gaps, "G143 fonte unica:\n%s" % "\n".join("  - " + g for g in gaps)


def test_08_casa_e_predio_byte_identicos(tmp_path):
    """A casa e o predio nao mudam um byte (o G143 so toca o galpao)."""
    import desenho_fundacao_edificio as dfe

    gaps = []
    fund_p = {"tipo": "sapata", "sigma_solo_adm": 250.0,
              "proveniencia_sigma": "declarada no spec (sigma_solo_adm)",
              "cota_apoio_m": 1.0,
              "por_pilar": {"P1": {"i": 0, "j": 0,
                                   "N_dimensionamento_kN": 800.0,
                                   "geometria": {"B_m": 2.0, "L_m": 2.5,
                                                 "h_m": 0.7,
                                                 "subtipo": "isolada"}}}}
    est_p = {"vaos_x": [7.0], "vaos_y": [5.0]}
    antes = dfe.planta_fundacao_svg(fund_p, est_p)
    if "G143" in antes or "NAO DECLARADOS" in antes:
        gaps.append("caminho do predio vazou marcacao do galpao")
    p_svg = str(tmp_path / "predio.svg")
    dfe.gerar_planta_fundacao(fund_p, est_p, p_svg)
    with open(p_svg, encoding="utf-8") as f:
        if f.read() != antes:
            gaps.append("gerar_planta_fundacao mudou o predio")
    assert tmp_path.is_dir()
    assert not gaps, "G143 byte-identico:\n%s" % "\n".join("  - " + g for g in gaps)


def test_09_pe_co04_tres_aceites_com_estaca(tmp_path):
    """Os tres aceites da PE-CO-04 com estaca (convencao 6), olhando o PNG."""
    import ast

    import desenho_fundacao_edificio as dfe
    import galpao_adapter as ga
    import pacote_legal as pl
    from caderno_casa_edificio import svg_para_png
    from desenho_svg_base import confere_folha_svg

    gaps = []
    r = gc.rodar(_spec(D_estaca=0.30, L_estaca=10.0,
                       tipo_estaca="pre_moldada"))
    fund, est, aus = dfe.adaptar_galpao_para_locacao(
        r, _spec(D_estaca=0.30, L_estaca=10.0, tipo_estaca="pre_moldada"))
    # (1) esta certa: cada estaca do resultado desenhada, uma por uma
    svg = dfe.planta_fundacao_svg(fund, est, ausencias=aus or None)
    ET.fromstring(svg)
    n_esp = 2 * r["spec"]["n_porticos"]
    if svg.count("data-pilar") != n_esp:
        gaps.append("elementos %d != 2 x n_porticos=%d"
                    % (svg.count("data-pilar"), n_esp))
    if "1est D30 L10" not in svg:
        gaps.append("quadro sem a estaca dimensionada (1est D30 L10)")
    if not confere_folha_svg(svg).get("ok"):
        gaps.append("guarda reprova a folha: %r"
                    % (confere_folha_svg(svg),))
    p_svg = str(tmp_path / "pe04_estaca.svg")
    p_png = str(tmp_path / "pe04_estaca.png")
    with open(p_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
        gaps.append("PE-CO-04 com estaca nao rasterizou para o aceite visual")
    # sem D/L nao ha folha silenciosa: a conta recusa antes de desenhar
    try:
        gc.rodar(_spec())
        gaps.append("sem D/L devia recusar, nao desenhar")
    except ValueError as exc:
        if "nao_declarada" not in str(exc):
            gaps.append("recusa sem nome: %r" % (exc,))
    # (2) sai no manifesto: codigo no mapa 1:1 com o arquivo emitido
    if ga._PRANCHA_ARQUIVO_GALPAO.get("PE-CO-04") != \
            "PE04_LOCACAO_FUNDACAO.pdf":
        gaps.append("mapa PE-CO-04 fora do basename")
    # (3) diz o que desenha: titulo do indice cobre locacao
    titulos = {f["codigo"]: f["titulo"]
               for f in pl.indice_de_pranchas(["concreto"])}
    if "locacao" not in titulos.get("PE-CO-04", "").lower():
        gaps.append("indice nao diz locacao: %r" % (titulos,))
    # pagina no emissor (AST, fonte independente)
    arvore = ast.parse(open(os.path.join(GALPAO, "techdraw_concreto.py"),
                            encoding="utf-8").read())
    paginas = {n.args[1].value for n in ast.walk(arvore)
               if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "_nova_prancha"
               and len(n.args) >= 2
               and isinstance(n.args[1], ast.Constant)}
    if "PE04_LOCACAO_FUNDACAO" not in paginas:
        gaps.append("PE04 fora do techdraw_concreto")
    assert tmp_path.is_dir()
    assert not gaps, "G143 aceites:\n%s" % "\n".join("  - " + g for g in gaps)
