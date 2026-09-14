"""G140 - PE-CO-04 locacao e formas da fundacao do galpao pre-moldado.

Medido (2026-09-14, antes de mudar):
- `galpao_concreto.rodar` devolve a sapata UNICA dimensionada
  (`sapata.aprovado = (B, L, h, rA, cA)`) + `spec {vao, comprimento, H,
  n_porticos, s}` + `tipo_fundacao`: sem `por_pilar`, sem
  `proveniencia_sigma`, sem `cota_apoio_m` — 3 campos que
  `desenho_fundacao_edificio.planta_fundacao_svg` le no shape do predio
  (fundacao.{tipo, sigma, proveniencia, cota, por_pilar[{i, j,
  N_dimensionamento, geometria}]} + estrutura.{vaos_x, vaos_y}).
  Remeça no test_01.
- O emissor era chamado pela casa (`desenho_casa_residencial:733`,
  que delega a mesma funcao do G80) e pelo predio
  (`edificio_adapter.py:982`); a PE-CO-04 do galpao saia pulada com
  motivo "sem emissor de locacao e formas ..." .

Entregue:
- `desenho_fundacao_edificio.adaptar_galpao_para_locacao(r, spec)`:
  (fundacao, estrutura, ausentes) lidos do calculo — um elemento por
  pilar (malha 2 x n_porticos, P<j><E|D> como no `membros_bim`), cada
  um com a sapata (ou o grupo de estacas) DIMENSIONADA, sem
  redimensionar; ausentes = subconjunto de `AUSENCIAS_GALPAO_LOCACAO`
  (cota_apoio_m sempre; tensao sem sondagem quando o sigma e default).
- `planta_fundacao_svg(..., ausencias=None)`: defaults = caminho do
  predio/casa byte-identico; com ausencias desenha a mesma planta e
  declara a caixa vermelha na folha.
- `gerar_locacao_galpao` (SVG) + `galpao_concreto.gerar_prancha_locacao`
  (PDF A1 puro-Python, mesma via do INC03 no G138) + `_pr_locacao` no
  `techdraw_concreto` (PE04_LOCACAO_FUNDACAO, carimbo PE-04 04/04;
  PE01..PE03 passam a 01/04..03/04); motivo/correspondencia/baselines
  atualizados (G112: 24 entradas, PE04 em fora_do_mapa).

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), substring ->
parse -> renderizar (o PNG e rasterizado e o texto e conferido no
render), fonte independente (o vertical + o emissor, nunca o proprio
mapa) e sem valor normativo arbitrado.
"""
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def _spec_galpao(**kw):
    base = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}
    base.update(kw)
    return base


def _r_galpao(**kw):
    import galpao_concreto as gc

    return gc.rodar(_spec_galpao(**kw))


def _fundacao_predio():
    """Shape do predio que o emissor le (fonte independente: o que
    `fundacao_edificio.dimensiona` devolve + estrutura com vaos)."""
    import fundacao_edificio as fe

    pilares = [{"nome": "P%d" % (k + 1), "i": k % 2, "j": k // 2,
                "N_base_k": 800.0 + 50.0 * k, "secao": (0.20, 0.40),
                "posicao": "interna"}
               for k in range(4)]
    ctx = {"pilares": pilares, "eixos_x": [0.0, 7.0, 14.0],
           "eixos_y": [0.0, 5.0, 10.0],
           "materiais": {"fck": 30e3, "fyk": 500e3}}
    return (fe.dimensiona({"sigma_solo_adm": 250.0}, ctx),
            {"vaos_x": [7.0, 7.0], "vaos_y": [5.0, 5.0]})


def test_01_medido_campos_do_galpao_que_faltam_ao_emissor():
    """Remeça: o que o emissor le no predio e o galpao nao produz."""
    import copy

    import desenho_fundacao_edificio as dfe

    r = _r_galpao()
    gaps = []
    # o que o emissor le (linhas vivas de planta_fundacao_svg)
    import inspect

    fonte = inspect.getsource(dfe.planta_fundacao_svg)
    for termo in ("por_pilar", "vaos_x", "vaos_y", "sigma_solo_adm",
                  "proveniencia_sigma", "cota_apoio_m",
                  "N_dimensionamento_kN"):
        if termo not in fonte:
            gaps.append("emissor nao le %r no fonte vivo" % termo)
    # o que o galpao produz (chaves vivas do rodar)
    if "por_pilar" in r:
        gaps.append("galpao nao devia ter 'por_pilar': %r" % sorted(r))
    if "proveniencia_sigma" in r:
        gaps.append("galpao nao devia ter 'proveniencia_sigma'")
    # o adaptador constroi um elemento por pilar da sapata dimensionada
    spec = {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
            "sigma_solo_adm": 250.0}
    antes = copy.deepcopy(r)
    fund, est, ausentes = dfe.adaptar_galpao_para_locacao(r, spec)
    if r != antes:
        gaps.append("adaptar mutou o resultado (redimensionar e proibido)")
    n_esp = 2 * 7
    if len(fund.get("por_pilar") or {}) != n_esp:
        gaps.append("por_pilar devia ter 2 x n_porticos=%d: %d"
                    % (n_esp, len(fund.get("por_pilar") or {})))
    if est != {"vaos_x": [10.0],
               "vaos_y": [r["spec"]["s"]] * 6}:
        gaps.append("malha devia ser [vao] x [s]*6: %r" % (est,))
    # cada sapata desenhada e a dimensionada (B/L/h do aprovado)
    B, L, h = r["sapata"]["aprovado"][:3]
    for nome, reg in sorted((fund.get("por_pilar") or {}).items()):
        g = reg.get("geometria") or {}
        if (g.get("B_m"), g.get("L_m"), g.get("h_m")) != (B, L, h):
            gaps.append("%s com geometria != dimensionada: %r" % (nome, g))
            break
    # sigma do spec com proveniencia dita; cota ausente declarada
    if fund.get("sigma_solo_adm") != 250.0:
        gaps.append("sigma fora do calculo: %r"
                    % (fund.get("sigma_solo_adm"),))
    if "spec" not in str(fund.get("proveniencia_sigma")):
        gaps.append("proveniencia sem a origem: %r"
                    % (fund.get("proveniencia_sigma"),))
    if ausentes != [dfe.AUSENCIAS_GALPAO_LOCACAO[0]]:
        gaps.append("com sigma no spec so a cota e ausente: %r" % (ausentes,))
    # sem sigma e sem sondagem: o 2o (tensao default) entra junto
    import galpao_concreto as gc

    spec_sem_sigma = {k: v for k, v in _spec_galpao().items()
                      if k != "sigma_solo_adm"}
    r2 = gc.rodar(spec_sem_sigma)
    _f2, _e2, aus2 = dfe.adaptar_galpao_para_locacao(
        r2, {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7})
    if len(aus2) != 2 or aus2[0] != dfe.AUSENCIAS_GALPAO_LOCACAO[0]:
        gaps.append("sem sigma devia declarar os 2: %r" % (aus2,))
    # sem sapata dimensionada nao ha folha honesta (erro nomeado)
    r3 = _r_galpao()
    r3["sapata"] = {"aprovado": None}
    try:
        dfe.adaptar_galpao_para_locacao(r3, spec)
        gaps.append("sem sapata devia levantar, nao desenhar vazio")
    except ValueError as exc:
        if "PE-CO-04" not in str(exc):
            gaps.append("erro sem o codigo da folha: %r" % (exc,))
    assert not gaps, (
        "G140 medida:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_predio_byte_identico_galpao_sem_recalculo(tmp_path):
    """A casa e o predio nao mudam um byte; o galpao usa o numero calculado."""
    import desenho_casa_residencial as dcr
    import desenho_fundacao_edificio as dfe

    fund_p, est_p = _fundacao_predio()
    gaps = []
    antes = dfe.planta_fundacao_svg(fund_p, est_p)
    if "NAO DECLARADOS" in antes or "GALPAO" in antes:
        gaps.append("caminho do predio vazou marcacao do galpao")
    # gerar_* com 4 args (o chamado do edificio_adapter) == o SVG direto
    p_predio = str(tmp_path / "predio.svg")
    dfe.gerar_planta_fundacao(fund_p, est_p, p_predio)
    with open(p_predio, encoding="utf-8") as f:
        em_disco = f.read()
    if em_disco != antes:
        gaps.append("gerar_planta_fundacao com defaults mudou o predio")
    # a casa delega a mesma funcao do G80 com o dado da casa
    if "desenho_fundacao_edificio.planta_fundacao_svg" not in open(
            os.path.join(GALPAO, "desenho_casa_residencial.py"),
            encoding="utf-8").read():
        gaps.append("casa:733 sem delegar a primitiva do predio")
    # galpao: UM elemento por pilar do resultado, dimensoes == dimensionadas
    r = _r_galpao()
    n_esp = 2 * r["spec"]["n_porticos"]
    fund, est, aus = dfe.adaptar_galpao_para_locacao(
        r, {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
            "sigma_solo_adm": 250.0})
    svg_g = dfe.planta_fundacao_svg(fund, est, ausencias=aus or None)
    ET.fromstring(svg_g)  # parse: SVG bem-formado
    if svg_g.count("data-pilar") != n_esp:
        gaps.append("elementos %d != 2 x n_porticos=%d do calculo"
                    % (svg_g.count("data-pilar"), n_esp))
    conf = dfe.confere_desenho_fundacao(fund, svg_g)
    if not conf.get("ok"):
        gaps.append("desenhado != dimensionado: %r" % (conf,))
    for campo in aus:
        if campo not in svg_g:
            gaps.append("ausencia nao declarada na folha: %r" % campo)
    if aus and "DADOS NAO DECLARADOS" not in svg_g:
        gaps.append("caixa de ausencias fora da folha do galpao")
    # sem recalculo: o aprovado do calculo segue o mesmo objeto
    ap_antes = r["sapata"]["aprovado"]
    dfe.adaptar_galpao_para_locacao(r, {"vao": 10.0, "comprimento": 40.0,
                                        "n_porticos": 7,
                                        "sigma_solo_adm": 250.0})
    if r["sapata"]["aprovado"] != ap_antes:
        gaps.append("adaptar tocou na sapata dimensionada")
    assert tmp_path.is_dir()
    assert not gaps, (
        "G140 emissor:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_rota_emite_PE04_e_renderiza(tmp_path):
    """A rota pura grava PE04 valido que rasteriza (sem freecad.exe)."""
    import galpao_concreto as gc

    r = _r_galpao()
    res_pdf = gc.gerar_prancha_locacao(
        r, str(tmp_path),
        {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
         "sigma_solo_adm": 250.0, "slug": "g140"})
    gaps = []
    if not str(res_pdf).endswith("PE04_LOCACAO_FUNDACAO.pdf"):
        gaps.append("basename fora do mapa: %r" % (res_pdf,))
    if not os.path.getsize(res_pdf):
        gaps.append("PE04_LOCACAO_FUNDACAO.pdf vazio no disco")
    # substring -> parse -> renderizar: o SVG da folha passa na guarda e
    # vira PNG com bytes (o que os tres aceites olham no verbete D169).
    import desenho_fundacao_edificio as dfe
    from desenho_svg_base import confere_folha_svg
    from caderno_casa_edificio import svg_para_png

    fund, est, aus = dfe.adaptar_galpao_para_locacao(
        r, {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
            "sigma_solo_adm": 250.0})
    svg = dfe.planta_fundacao_svg(fund, est, ausencias=aus or None)
    for termo in ("LOCACAO", "QUADRO DE FUNDACAO", "DADOS NAO DECLARADOS",
                  "2.00 x 2.50"):
        if termo not in svg:
            gaps.append("folha sem %r" % termo)
    ET.fromstring(svg)
    guarda = confere_folha_svg(svg)
    if not guarda.get("ok"):
        gaps.append("guarda reprova a folha: %r" % (guarda,))
    p_svg = str(tmp_path / "pe04.svg")
    p_png = str(tmp_path / "pe04.png")
    with open(p_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
        gaps.append("PE04 nao rasterizou para o aceite visual")
    import fitz

    with fitz.open(res_pdf) as d:
        txt = d[0].get_text()
    # o esquema entra rasterizado (pixels, nao texto): titulo/carimbo em
    # texto + pagina nao em branco provam o render no PDF.
    for termo in ("PE-04", "LOCACAO"):
        if termo not in txt:
            gaps.append("PDF sem %r: %r" % (termo, txt[:300]))
    with fitz.open(res_pdf) as d:
        pix = d[0].get_pixmap(dpi=50)
        amostras = pix.samples
        if all(b == 255 for b in amostras):
            gaps.append("pagina do PDF em branco: esquema nao renderizou")
    assert not gaps, (
        "G140 PE04:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_vermelho_por_injecao_emissor_desligado(tmp_path, monkeypatch):
    """Nos dois sentidos: com o emissor a lente fecha; sem ele, PE-CO-04
    volta a faltar com motivo (o defeito mora em tmp_path)."""
    import json

    import galpao_adapter as ga
    import galpao_concreto as gc
    import varredura_indice_disco as lente

    gaps = []
    # lado bom: a emissao real fecha PE-CO-04 na lente
    res = gc.gerar_prancha_locacao(
        _r_galpao(), str(tmp_path / "bom"),
        {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
         "sigma_solo_adm": 250.0})
    if not str(res).endswith("PE04_LOCACAO_FUNDACAO.pdf"):
        gaps.append("emissao real fora do basename: %r" % (res,))
    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    sub = {c: mapa[c] for c in ("PE-CO-01", "PE-CO-04")}
    bom = lente.conferir_indice_disco(
        ["PE-CO-01", "PE-CO-04"], sub,
        ["PE01_FORMAS.pdf", "PE04_LOCACAO_FUNDACAO.pdf"], {})
    if not bom["OK"]:
        gaps.append("caso bom devia fechar PE-CO-01/04: %r" % (bom,))
    # injecao: emissor desligado nao grava PE04 (erro nomeado, nunca
    # silencio) e a lente acusa PE-CO-04 faltando
    import desenho_fundacao_edificio as dfe

    def emissor_morto(*_a, **_k):
        raise RuntimeError("emissor de locacao desligado (injecao G140)")

    monkeypatch.setattr(dfe, "planta_fundacao_svg", emissor_morto)
    try:
        gc.gerar_prancha_locacao(
            _r_galpao(), str(tmp_path / "morto"),
            {"vao": 10.0, "comprimento": 40.0, "n_porticos": 7,
             "sigma_solo_adm": 250.0})
        gaps.append("com o emissor morto devia levantar erro nomeado")
    except RuntimeError as exc:
        if "G140" not in str(exc):
            gaps.append("erro sem a marca da injecao: %r" % (exc,))
    caminho = tmp_path / "mapa_galpao.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    copia = {c: dict(json.loads(caminho.read_text(encoding="utf-8")))[c]
             for c in ("PE-CO-01", "PE-CO-04")}
    sem_pdf = lente.conferir_indice_disco(
        ["PE-CO-01", "PE-CO-04"], copia, ["PE01_FORMAS.pdf"], {})
    if sem_pdf["OK"] or "PE-CO-04" not in sem_pdf["faltando"]:
        gaps.append("sem o PE04 PE-CO-04 devia faltar: %r" % (sem_pdf,))
    # o motivo vivo nomeia codigo + dado (nunca generico)
    motivo = ga._motivo_folha_galpao_nao_emitida("PE-CO-04", "Locacao")
    if "PE-CO-04" not in motivo or "PE04_LOCACAO_FUNDACAO" not in motivo:
        gaps.append("motivo sem codigo/arquivo: %r" % (motivo,))
    if "nao declarado" not in motivo.lower() \
            and "not_available" not in motivo:
        gaps.append("motivo sem o dado nomeado: %r" % (motivo,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G140 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_tres_aceites_da_folha(tmp_path):
    """Os tres aceites (convencao 6): esta certa, sai no manifesto, diz o
    que desenha — pagina no emissor, codigo no mapa, titulo que desenha."""
    import ast

    import galpao_adapter as ga
    import pacote_legal as pl

    gaps = []
    # (1) esta certa: a pagina existe no emissor (AST, fonte independente)
    arvore = ast.parse(open(os.path.join(GALPAO, "techdraw_concreto.py"),
                            encoding="utf-8").read())
    paginas = {n.args[1].value for n in ast.walk(arvore)
               if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "_nova_prancha"
               and len(n.args) >= 2
               and isinstance(n.args[1], ast.Constant)}
    if "PE04_LOCACAO_FUNDACAO" not in paginas:
        gaps.append("PE04_LOCACAO_FUNDACAO fora do techdraw_concreto: %r"
                    % sorted(paginas))
    # (2) sai no manifesto: codigo no mapa 1:1 com o arquivo emitido
    if ga._PRANCHA_ARQUIVO_GALPAO.get("PE-CO-04") != \
            "PE04_LOCACAO_FUNDACAO.pdf":
        gaps.append("mapa PE-CO-04 != PE04_LOCACAO_FUNDACAO.pdf: %r"
                    % (ga._PRANCHA_ARQUIVO_GALPAO.get("PE-CO-04"),))
    # (3) diz o que desenha: titulo do indice + carimbo + cobertura escrita
    titulos = {f["codigo"]: f["titulo"]
               for f in pl.indice_de_pranchas(["concreto"])}
    if "locacao" not in titulos.get("PE-CO-04", "").lower():
        gaps.append("indice nao diz locacao: %r" % (titulos,))
    entradas = {e["arquivo"]: e
                for e in pl.CORRESPONDENCIA_NUMERACAO_GALPAO["entradas"]}
    ent = entradas.get("PE04_LOCACAO_FUNDACAO.pdf") or {}
    if ent.get("cobre") != ["PE-CO-04"]:
        gaps.append("correspondencia sem cobrir PE-CO-04: %r" % (ent,))
    if "PE-04" not in str(ent.get("carimbo", "")):
        gaps.append("correspondencia sem o carimbo PE-04: %r" % (ent,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G140 aceites:\n%s" % "\n".join("  - " + g for g in gaps))
