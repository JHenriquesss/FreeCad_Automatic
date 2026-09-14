"""G138 - PE-IN-02 detalhes de hidrantes do galpao: o emissor existe e nao era chamado.

Medido (2026-09-14, antes de mudar):
- `galpao_seguranca_incendio.rodar` devolve gates {iluminacao_emergencia,
  sinalizacao, deteccao_alarme, sprinklers, hidrantes} + spec {C,L,H}:
  sem `sistemas`, sem `gates.rotas_verticais`/`escada_largura`, sem
  `estrategia_abandono`/`populacao_total`/`altura_edificacao_m` e sem
  `estrutura.pavimentos` (galpao terreo) — 6 campos que
  `desenho_incendio.detalhes_hidrantes_rotas_svg` le no shape do predio
  (sistemas.hidrantes + gates.rotas_verticais/escada_largura +
  estrategia/populacao/altura + pavimentos). Remeça no test_01.
- O emissor era chamado SO pelo predio (`edificio_adapter.py:1166`); o
  executivo do galpao emitia INC01+INC02 e PE-IN-02 saia pulada com motivo
  "sem emissor ... (PE-IN-02 ...)".

Entregue:
- `desenho_incendio.adaptar_galpao_para_detalhes(r)`: (inc, estrutura,
  ausentes) lidos do calculo (hidrantes cru de r["hidrantes"], com
  `reserva_incendio_m3` original), sem recalcular; ausentes =
  AUSENCIAS_GALPAO_DETALHES (+ hidrantes quando o spec nao declara).
- `detalhes_hidrantes_rotas_svg(..., ausencias=None, nivel_unico=False)`:
  defaults = caminho do predio byte-identico; nivel_unico desenha os N
  hidrantes lado a lado no nivel unico (nunca N pavimentos inventados) e
  declara as ausencias na folha.
- Executivo do galpao com INC03_DETALHES nos dois backends (svg-direta em
  `galpao_seguranca_incendio.montar_pranchas` + `_pr_detalhes` no
  `techdraw_incendio`); mapa ja apontava INC03; motivo/correspondencia/
  baselines atualizados (G112: 23 entradas, INC03 em fora_do_mapa).

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


def _r_galpao(**kw):
    import galpao_seguranca_incendio as gsi

    base = {"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
            "iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
            "deteccao": {"viga_m": 0.0},
            "sprinklers": {"altura_estoque_m": 3.0},
            "hidrantes": {"ocupacao": "industrial_I2"}}
    base.update(kw)
    return gsi.rodar(base)


def _inc_predio():
    """Shape do predio que o emissor le (fonte independente: o que
    `incendio_edificio.dimensiona` devolve + estrutura com pavimentos)."""
    return (
        {"sistemas": {"hidrantes": {"N_hidrantes": 2, "tipo": 2,
                                    "reserva_incendio_m3": 36.0}},
         "gates": {"rotas_verticais": {"n_minimo": 1, "n_declarado": 1},
                   "escada_largura": {"largura_exigida_m": 1.2}},
         "estrategia_abandono": "simultaneo",
         "populacao_total": 40,
         "altura_edificacao_m": 9.0},
        {"pavimentos": [{"nome": "T1"}, {"nome": "T2"}],
         "pavimento": {"vaos_x": [7.0, 7.0], "vaos_y": [4.5, 4.5]}},
    )


def test_01_medido_campos_do_galpao_que_faltam_ao_emissor():
    """Remeça: o que o emissor le no predio e o galpao nao produz."""
    import desenho_incendio as di
    import galpao_seguranca_incendio as gsi

    r = gsi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidrantes": {"ocupacao": "industrial_I2"}})
    gaps = []
    # o que o emissor le (linhas vivas de detalhes_hidrantes_rotas_svg)
    src_leituras = ["sistemas", "rotas_verticais", "escada_largura",
                    "reserva_incendio_m3", "estrategia_abandono",
                    "populacao_total", "altura_edificacao_m", "pavimentos"]
    import inspect

    fonte = inspect.getsource(di.detalhes_hidrantes_rotas_svg)
    for termo in src_leituras:
        if termo not in fonte:
            gaps.append("emissor nao le %r no fonte vivo" % termo)
    # o que o galpao produz (chaves vivas do rodar)
    if "sistemas" in r:
        gaps.append("galpao nao devia ter 'sistemas': %r" % sorted(r))
    for campo in ("rotas_verticais", "escada_largura"):
        if campo in (r.get("gates") or {}):
            gaps.append("galpao nao devia ter gate %r" % campo)
    for campo in ("estrategia_abandono", "populacao_total",
                  "altura_edificacao_m"):
        if campo in r:
            gaps.append("galpao nao devia ter %r no topo" % campo)
    # o adaptador declara exatamente os 6 (hidrantes calculado: sem o extra)
    _inc, _est, ausentes = di.adaptar_galpao_para_detalhes(r)
    if ausentes != list(di.AUSENCIAS_GALPAO_DETALHES):
        gaps.append("ausentes deviam ser os 6 medidos: %r" % (ausentes,))
    # sem hidrantes no spec: o 7o (hidrantes nao calculados) entra na frente
    r_sem = gsi.rodar({"geometria": {"L": 30.0, "W": 15.0, "H": 5.0}})
    _i2, _e2, aus2 = di.adaptar_galpao_para_detalhes(r_sem)
    if len(aus2) != 7 or "hidrantes" not in aus2[0].lower():
        gaps.append("sem hidrantes devia declarar o 7o primeiro: %r" % (aus2,))
    assert not gaps, (
        "G138 medida:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_predio_byte_identico_galpao_sem_recalculo(tmp_path):
    """O predio nao muda um byte; o galpao usa o numero calculado."""
    import desenho_incendio as di

    inc_p, est_p = _inc_predio()
    antes = di.detalhes_hidrantes_rotas_svg(inc_p, est_p)
    gaps = []
    if "NAO DECLARADOS" in antes or "terreo" in antes.lower():
        gaps.append("caminho do predio vazou marcacao do galpao")
    # gerar_* com 3 args (o chamado do edificio_adapter) == o SVG direto
    p_predio = str(tmp_path / "predio.svg")
    di.gerar_detalhes_hidrantes(inc_p, est_p, p_predio)
    with open(p_predio, encoding="utf-8") as f:
        em_disco = f.read()
    if em_disco != antes:
        gaps.append("gerar_detalhes_hidrantes com defaults mudou o predio")
    # galpao: N simbolos == N_hidrantes do calculo; reserva do calculo
    r = _r_galpao()
    n_calc = int(r["hidrantes"]["N_hidrantes"])
    res_calc = float(r["hidrantes"]["reserva_incendio_m3"])
    p_galpao = str(tmp_path / "galpao.svg")
    _path, ausentes = di.gerar_detalhes_galpao(r, p_galpao)
    with open(p_galpao, encoding="utf-8") as f:
        svg_g = f.read()
    ET.fromstring(svg_g)  # parse: SVG bem-formado
    n_simbolos = svg_g.count("HID-")
    if n_simbolos != n_calc:
        gaps.append("simbolos HID-%d != N_hidrantes=%d do calculo"
                    % (n_simbolos, n_calc))
    if "hidrante N2" in svg_g or "hidrante N1" in svg_g:
        gaps.append("galpao desenhou rotulo de pavimento do predio")
    if "RESERVA DE INCENDIO %.1f m3" % res_calc not in svg_g:
        gaps.append("reserva %.1f do calculo fora da folha" % res_calc)
    for campo in ausentes:
        if campo not in svg_g:
            gaps.append("ausencia nao declarada na folha: %r" % campo)
    if "DADOS NAO DECLARADOS" not in svg_g:
        gaps.append("caixa de ausencias fora da folha do galpao")
    assert not gaps, (
        "G138 emissor:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_rota_svg_emite_INC03_e_renderiza(tmp_path):
    """A rodada de esquema do galpao grava INC03 valido que rasteriza."""
    import galpao_seguranca_incendio as gsi

    r = _r_galpao()
    res = gsi.montar_pranchas(r, str(tmp_path))
    gaps = []
    if not res.get("ok"):
        gaps.append("montar_pranchas falhou: %r" % (res,))
    if (res.get("pranchas") or [])[-1:] != ["INC03_DETALHES"]:
        gaps.append("terceira prancha devia ser INC03_DETALHES: %r"
                    % (res.get("pranchas"),))
    pdf3 = [a for a in (res.get("arquivos") or [])
            if str(a).endswith("INC03_DETALHES.pdf")]
    if not pdf3 or not os.path.getsize(pdf3[0]):
        gaps.append("INC03_DETALHES.pdf fora do disco: %r"
                    % (res.get("arquivos"),))
    # substring -> parse -> renderizar: o SVG da folha passa na guarda e
    # vira PNG com bytes (o que os tres aceites olham no verbete D168).
    import desenho_incendio as di
    from desenho_svg_base import confere_folha_svg
    from caderno_casa_edificio import svg_para_png

    _inc, _est, _aus = di.adaptar_galpao_para_detalhes(r)
    svg = di.detalhes_hidrantes_rotas_svg(
        _inc, _est, ausencias=_aus, nivel_unico=True)
    for termo in ("COLUNA DN65", "QUADRO DE ROTAS", "DADOS NAO DECLARADOS",
                  "GALPAO TERREO"):
        if termo not in svg:
            gaps.append("folha sem %r" % termo)
    ET.fromstring(svg)
    guarda = confere_folha_svg(svg)
    if not guarda.get("ok"):
        gaps.append("guarda reprova a folha: %r" % (guarda,))
    p_svg = str(tmp_path / "inc03.svg")
    p_png = str(tmp_path / "inc03.png")
    with open(p_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
        gaps.append("INC03 nao rasterizou para o aceite visual")
    import fitz

    with fitz.open(pdf3[0]) as d:
        txt = d[0].get_text()
    # o esquema entra rasterizado (pixels, nao texto): titulo/carimbo em
    # texto + pagina nao em branco provam o render no PDF.
    for termo in ("PE-INC-03", "DETALHES DE HIDRANTES"):
        if termo not in txt:
            gaps.append("PDF sem %r: %r" % (termo, txt[:300]))
    with fitz.open(pdf3[0]) as d:
        pix = d[0].get_pixmap(dpi=50)
        amostras = pix.samples
        if all(b == 255 for b in amostras):
            gaps.append("pagina do PDF em branco: esquema nao renderizou")
    assert not gaps, (
        "G138 INC03:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_vermelho_por_injecao_emissor_desligado(tmp_path, monkeypatch):
    """Nos dois sentidos: com o emissor a lente fecha; sem ele, PE-IN-02
    volta a faltar com motivo (o defeito mora em tmp_path)."""
    import json

    import galpao_adapter as ga
    import galpao_seguranca_incendio as gsi
    import varredura_indice_disco as lente

    gaps = []
    # lado bom: a emissao real fecha PE-IN-02 na lente
    res = gsi.montar_pranchas(_r_galpao(), str(tmp_path / "bom"))
    disco_bom = sorted(a.split("/")[-1].split("\\")[-1]
                       for a in (res.get("arquivos") or []))
    mapa = dict(ga._PRANCHA_ARQUIVO_GALPAO)
    sub = {c: mapa[c] for c in ("PE-IN-01", "PE-IN-02")}
    bom = lente.conferir_indice_disco(
        ["PE-IN-01", "PE-IN-02"], sub,
        ["INC01_PLANTA.pdf", "INC03_DETALHES.pdf"], {})
    if not bom["OK"]:
        gaps.append("caso bom devia fechar PE-IN-01/02: %r" % (bom,))
    # injecao: emissor desligado nao grava INC03 (erro nomeado, nunca
    # silencio) e a lente acusa PE-IN-02 faltando
    import desenho_incendio as di

    def emissor_morto(*_a, **_k):
        raise RuntimeError("emissor de detalhes desligado (injecao G138)")

    monkeypatch.setattr(di, "detalhes_hidrantes_rotas_svg", emissor_morto)
    morto = gsi.montar_pranchas(_r_galpao(), str(tmp_path / "morto"))
    if "erro" not in morto:
        gaps.append("com o emissor morto devia voltar erro nomeado: %r"
                    % (morto,))
    caminho = tmp_path / "mapa_galpao.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    copia = {c: dict(json.loads(caminho.read_text(encoding="utf-8")))[c]
             for c in ("PE-IN-01", "PE-IN-02")}
    furado = [a for a in disco_bom if a != "INC03_DETALHES.pdf"]
    sem_pdf = lente.conferir_indice_disco(
        ["PE-IN-01", "PE-IN-02"], copia,
        ["INC01_PLANTA.pdf"], {})
    if sem_pdf["OK"] or "PE-IN-02" not in sem_pdf["faltando"]:
        gaps.append("sem o INC03 PE-IN-02 devia faltar: %r" % (sem_pdf,))
    # o motivo vivo nomeia codigo + dado (nunca generico)
    motivo = ga._motivo_folha_galpao_nao_emitida("PE-IN-02", "Detalhes")
    if "PE-IN-02" not in motivo or "INC03_DETALHES" not in motivo:
        gaps.append("motivo sem codigo/arquivo: %r" % (motivo,))
    if "nao declarado" not in motivo.lower() \
            and "not_available" not in motivo:
        gaps.append("motivo sem o dado nomeado: %r" % (motivo,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G138 injecao:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_tres_aceites_da_folha(tmp_path):
    """Os tres aceites (convencao 6): esta certa, sai no manifesto, diz o
    que desenha — pagina no emissor, codigo no mapa, titulo que desenha."""
    import ast

    import galpao_adapter as ga
    import pacote_legal as pl

    gaps = []
    # (1) esta certa: a pagina existe no emissor (AST, fonte independente)
    arvore = ast.parse(open(os.path.join(GALPAO, "techdraw_incendio.py"),
                            encoding="utf-8").read())
    paginas = {n.args[1].value for n in ast.walk(arvore)
               if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "_nova_prancha"
               and len(n.args) >= 2
               and isinstance(n.args[1], ast.Constant)}
    if "INC03_DETALHES" not in paginas:
        gaps.append("INC03_DETALHES fora do techdraw_incendio: %r"
                    % sorted(paginas))
    # (2) sai no manifesto: codigo no mapa 1:1 com o arquivo emitido
    if ga._PRANCHA_ARQUIVO_GALPAO.get("PE-IN-02") != "INC03_DETALHES.pdf":
        gaps.append("mapa PE-IN-02 != INC03_DETALHES.pdf: %r"
                    % (ga._PRANCHA_ARQUIVO_GALPAO.get("PE-IN-02"),))
    # (3) diz o que desenha: titulo do indice + carimbo + cobertura escrita
    titulos = {f["codigo"]: f["titulo"]
               for f in pl.indice_de_pranchas(["incendio"])}
    if "hidrante" not in titulos.get("PE-IN-02", "").lower():
        gaps.append("indice nao diz hidrantes: %r" % (titulos,))
    entradas = {e["arquivo"]: e
                for e in pl.CORRESPONDENCIA_NUMERACAO_GALPAO["entradas"]}
    ent = entradas.get("INC03_DETALHES.pdf") or {}
    if ent.get("cobre") != ["PE-IN-02"]:
        gaps.append("correspondencia sem cobrir PE-IN-02: %r" % (ent,))
    if "PE-INC-03" not in str(ent.get("carimbo", "")):
        gaps.append("correspondencia sem o carimbo PE-INC-03: %r" % (ent,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G138 aceites:\n%s" % "\n".join("  - " + g for g in gaps))
