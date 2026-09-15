"""G146 - PE-MZ-01: a folha do mezanino calculado.

Medido (antes de mudar, fontes vivas):
- `galpao_mezanino.rodar` devolve `laje` (com `armaduras`), `viga_X`/`viga_Y`
  simples, `pilar` unico, `sapatas[4]` com `aprovado` e a posicao
  x0/y0/Lx/Ly/h — sem `pav` (vaos_x/vaos_y/paineis/por_pilar), sem
  `por_linha`/`tramos` de vigas e sem `lances` de pilares, que sao o que
  `desenho_pavimento.planta_formas_svg` e
  `prancha_armacao_vigas_pilares_svg` leem no shape do predio.
  Remeça no test_01.
- D170/G141: com mezanino executado a PE-MZ-01 era prometida e saia pulada
  ("sem emissor ligado"); o arquivo MZ01_MEZANINO.pdf ja estava mapeado.

Entregue:
- `desenho_pavimento.adaptar_galpao_mezanino(r)`: (pav, vigas_verificacao,
  pilares, sapatas, ausentes) lidos do calculo — 1 painel Lx x Ly, 4
  pilares M-P1..M-P4 com o Nk calculado, 4 linhas de viga de 1 tramo
  (M-VX1/M-VX2 do viga_X, M-VY1/M-VY2 do viga_Y), 4 lances unicos do pilar
  e as 4 sapatas DIMENSIONADAS; ausentes = subconjunto de
  `AUSENCIAS_GALPAO_MEZANINO` (+ armadura da laje quando o calculo nao a
  produz). Sem redimensionar; sem sapata aprovada nao ha folha honesta
  (ValueError nomeando a PE-MZ-01).
- `planta_formas_svg(..., ausencias=None)`: defaults = caminho do
  predio/casa byte-identico; com ausencias desenha a mesma planta e
  declara a caixa vermelha na faixa extra (a malha e a legenda nao se
  movem).
- `techdraw_mezanino` (cfg + carimbo MZ-01 + pagina MZ01_MEZANINO) e
  `galpao_mezanino.gerar_prancha_mezanino` (PDF A1 puro-Python de 3
  paginas: formas, armacao, quadro de sapatas/laje) +
  `galpao_mezanino.montar_pranchas` (a MZ01 que cai fica nomeada em
  `mezanino_erro, sem derrubar as demais); motivo/causa no laco,
  dispatch no caderno e correspondencia atualizados (G112: 25 entradas,
  MZ-01 distinto de PE-MZ-01).

Cada teste segue as convencoes do BACKLOG: baseline nos dois sentidos,
vermelho por injecao em tmp_path (nunca mutando o repo), substring ->
parse -> renderizar (o PNG e rasterizado e o texto e conferido no
render), fonte independente (o vertical + o emissor, nunca o proprio
mapa), convencao 13 (ausente e zero um por um; falha so na folha nova) e
sem valor normativo arbitrado.
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)


def _spec_mez(**kw):
    base = {"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
            "q_uso": 2.0}
    base.update(kw)
    return base


def _r_mez(**kw):
    import galpao_mezanino as gmz

    return gmz.rodar(_spec_mez(**kw))


def test_01_medido_diferenca_de_forma_entre_mezanino_e_primitivas():
    """Remeça: o que as primitivas leem no predio e o mezanino nao produz."""
    import copy

    import desenho_pavimento as dp

    r = _r_mez()
    gaps = []
    # o que as primitivas leem (fonte viva: o fonte dos emissores)
    import inspect

    fonte_formas = inspect.getsource(dp.planta_formas_svg)
    for termo in ("vaos_x", "vaos_y", "area_m2", "paineis", "pilares",
                  "N_k", "g_kN_m2", "q_kN_m2", "caso", "engastes"):
        if termo not in fonte_formas:
            gaps.append("formas nao le %r no fonte vivo" % termo)
    fonte_arm = inspect.getsource(dp.prancha_armacao_vigas_pilares_svg)
    for termo in ("por_linha", "tramos"):
        if termo not in fonte_arm:
            gaps.append("armacao nao le %r no fonte vivo" % termo)
    fonte_mod = open(os.path.join(GALPAO, "desenho_pavimento.py"),
                     encoding="utf-8").read()
    for termo in ("lances", "Nd", "As_cm2"):
        if termo not in fonte_mod:
            gaps.append("armacao nao le %r no fonte vivo" % termo)
    # o que o mezanino produz (chaves vivas do rodar)
    for termo in ("por_linha", "lances", "vaos_x", "por_pilar"):
        if termo in r:
            gaps.append("mezanino nao devia ter %r: %r" % (termo, sorted(r)))
    # o adaptador constroi um elemento por peca calculada, sem mutar
    antes = copy.deepcopy(r)
    pav, vv, pilares, sapatas, ausentes = dp.adaptar_galpao_mezanino(r)
    if r != antes:
        gaps.append("adaptar mutou o resultado (redimensionar e proibido)")
    if len(pav.get("pilares") or []) != 4:
        gaps.append("formas devia ter 4 pilares: %r" % (pav.get("pilares"),))
    if len(pav.get("paineis") or []) != 1:
        gaps.append("formas devia ter 1 painel: %r" % (pav.get("paineis"),))
    if [l["nome"] for l in vv.get("por_linha") or []] != [
            "M-VX1", "M-VX2", "M-VY1", "M-VY2"]:
        gaps.append("vigas fora do 1-por-1: %r" % (vv.get("por_linha"),))
    if vv.get("n_tramos") != 4:
        gaps.append("n_tramos devia ser 4: %r" % (vv.get("n_tramos"),))
    if sorted(pilares) != ["M-P1", "M-P2", "M-P3", "M-P4"]:
        gaps.append("pilares fora do 1-por-1: %r" % (sorted(pilares),))
    if [s["marca"] for s in sapatas] != ["M-SAP%d" % k for k in (1, 2, 3, 4)]:
        gaps.append("sapatas fora do 1-por-1: %r" % (sapatas,))
    # cada numero desenhado e o calculado (sem recalculo)
    if abs(pav["pilares"][0]["N_k"] - r["Nk_pilar"]) > 1e-9:
        gaps.append("Nk fora do calculo: %r vs %r"
                    % (pav["pilares"][0]["N_k"], r["Nk_pilar"]))
    if abs(vv["por_linha"][0]["tramos"][0]["M_d_kNm"]
           - r["viga_X"]["M_d"]) > 1e-9:
        gaps.append("M_d fora do calculo")
    B, L, h = r["sapatas"][0]["aprovado"][:3]
    if (sapatas[0]["B_m"], sapatas[0]["L_m"], sapatas[0]["h_m"]) != (B, L, h):
        gaps.append("sapata fora da dimensionada: %r" % (sapatas[0],))
    if ausentes != list(dp.AUSENCIAS_GALPAO_MEZANINO):
        gaps.append("com tudo calculado so as 3 estaticas sao ausentes: %r"
                    % (ausentes,))
    # sem sapata dimensionada nao ha folha honesta (erro nomeado)
    r3 = _r_mez()
    r3["sapatas"][1] = {"aprovado": None}
    try:
        dp.adaptar_galpao_mezanino(r3)
        gaps.append("sem sapata devia levantar, nao desenhar vazio")
    except ValueError as exc:
        if "PE-MZ-01" not in str(exc):
            gaps.append("erro sem o codigo da folha: %r" % (exc,))
    assert not gaps, (
        "G146 medida:\n%s" % "\n".join("  - " + g for g in gaps))


def test_02_predio_byte_identico_mezanino_um_por_um(tmp_path):
    """O predio nao muda um byte; o mezanino desenha cada peca calculada."""
    import desenho_pavimento as dp

    from tests.test_edificio_pranchas_g56 import _caso

    R = _caso()[0]
    gaps = []
    antes = dp.planta_formas_svg(R["pavimento"])
    if "NAO DECLARADOS" in antes or "MEZANINO" in antes:
        gaps.append("caminho do predio vazou marcacao do mezanino")
    depois = dp.planta_formas_svg(R["pavimento"], ausencias=None)
    if depois != antes:
        gaps.append("ausencias=None mudou o predio")
    # mezanino: cada viga, pilar e sapata do resultado, desenhados um por um
    r = _r_mez()
    pav, vv, pilares, sapatas, ausentes = dp.adaptar_galpao_mezanino(r)
    svg_f = dp.planta_formas_svg(pav, ausencias=ausentes)
    ET.fromstring(svg_f)  # parse: SVG bem-formado
    for nome in ("M-P1", "M-P2", "M-P3", "M-P4"):
        if svg_f.count(nome) < 1:
            gaps.append("pilar %s nao desenhado nas formas" % nome)
    conf_f = dp.confere_desenho(pav)
    if (conf_f["n_pilares"], conf_f["n_paineis"]) != (4, 1):
        gaps.append("formas fora do calculado: %r" % (conf_f,))
    for campo in ausentes:
        if campo not in svg_f:
            gaps.append("ausencia nao declarada nas formas: %r" % campo)
    if "DADOS NAO DECLARADOS" not in svg_f:
        gaps.append("caixa de ausencias fora da folha do mezanino")
    svg_a = dp.prancha_armacao_vigas_pilares_svg(vv, pilares)
    ET.fromstring(svg_a)
    conf_v = dp.confere_armacao_vigas(vv, svg_a)
    if not conf_v.get("ok"):
        gaps.append("viga desenhada != calculada: %r" % (conf_v,))
    conf_p = dp.confere_armacao_pilares(pilares, svg_a)
    if not conf_p.get("ok"):
        gaps.append("pilar desenhado != calculado: %r" % (conf_p,))
    for nome in ("M-VX1", "M-VX2", "M-VY1", "M-VY2",
                 "M-P1", "M-P2", "M-P3", "M-P4"):
        if nome not in svg_a:
            gaps.append("peca %s fora da armacao" % nome)
    # sem recalculo: o calculado segue o mesmo objeto
    ap_antes = r["sapatas"][0]["aprovado"]
    dp.adaptar_galpao_mezanino(r)
    if r["sapatas"][0]["aprovado"] != ap_antes:
        gaps.append("adaptar tocou na sapata dimensionada")
    assert tmp_path.is_dir()
    assert not gaps, (
        "G146 emissor:\n%s" % "\n".join("  - " + g for g in gaps))


def test_03_rota_emite_MZ01_e_renderiza(tmp_path):
    """A rota pura grava MZ01 valida que rasteriza (sem freecad.exe)."""
    import galpao_mezanino as gmz

    r = _r_mez()
    pdf = gmz.gerar_prancha_mezanino(r, str(tmp_path), {"slug": "g146"})
    gaps = []
    if not str(pdf).endswith("MZ01_MEZANINO.pdf"):
        gaps.append("basename fora do mapa: %r" % (pdf,))
    if not os.path.getsize(pdf):
        gaps.append("MZ01_MEZANINO.pdf vazio no disco")
    # substring -> parse -> renderizar: os SVGs da folha passam nas guardas
    # e viram PNG com bytes (o que os tres aceites olham no verbete D173).
    import desenho_pavimento as dp
    from desenho_svg_base import confere_folha_svg
    from caderno_casa_edificio import svg_para_png
    import techdraw_mezanino as tdm

    cfg = tdm.config_de_spec(r, str(tmp_path), {"slug": "g146"})
    for chave, termos in (
            ("formas_svg", ("M-P1", "M-P4", "L11", "DADOS NAO DECLARADOS")),
            ("armacao_svg", ("M-VX1", "M-VY2", "M-P3", "30x30"))):
        svg = cfg[chave]
        for termo in termos:
            if termo not in svg:
                gaps.append("%s sem %r" % (chave, termo))
        ET.fromstring(svg)
        guarda = confere_folha_svg(svg)
        if not guarda.get("ok"):
            gaps.append("guarda reprova %s: %r" % (chave, guarda))
        p_svg = str(tmp_path / (chave + ".svg"))
        p_png = str(tmp_path / (chave + ".png"))
        with open(p_svg, "w", encoding="utf-8") as f:
            f.write(svg)
        if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
            gaps.append("%s nao rasterizou para o aceite visual" % chave)
    import fitz

    with fitz.open(pdf) as d:
        if d.page_count != 3:
            gaps.append("MZ01 devia ter 3 paginas (formas/armacao/quadro): %d"
                        % d.page_count)
        textos = " ".join(d[k].get_text() for k in range(d.page_count))
        for termo in ("MZ-01", "MEZANINO", "M-SAP1", "M-SAP4", "LAJE",
                      "nao declarado"):
            if termo not in textos:
                gaps.append("PDF sem %r" % termo)
        for k in range(d.page_count):
            pix = d[k].get_pixmap(dpi=50)
            if all(b == 255 for b in pix.samples):
                gaps.append("pagina %d do PDF em branco: esquema nao renderizou"
                            % k)
    # o quadro declara cada sapata com a geometria dimensionada
    for row in cfg["quadro_sap"]:
        if row[0].startswith("M-SAP") and "120 x 120" not in row[1]:
            gaps.append("sapata fora da dimensionada no quadro: %r" % (row,))
    assert not gaps, (
        "G146 MZ01:\n%s" % "\n".join("  - " + g for g in gaps))


def test_04_conv13_ausente_zero_e_falha_so_na_folha_nova(tmp_path, monkeypatch):
    """Convecao 13: ausente e zero um por um; a falha mora so na MZ01."""
    import desenho_pavimento as dp
    import galpao_adapter as ga
    import galpao_mezanino as gmz

    gaps = []
    # ausente (sem a chave) e zero (vazio) um por um: sapata vira erro
    # nomeado, nunca folha vazia
    for nome, mut in (("sem chave sapatas",
                       lambda r: r.pop("sapatas", None)),
                      ("aprovado None",
                       lambda r: r.__setitem__(
                           "sapatas", [{**s, "aprovado": None}
                                       for s in r["sapatas"]]))):
        r = _r_mez()
        mut(r)
        try:
            gmz.gerar_prancha_mezanino(r, str(tmp_path / "nunca"), {})
            gaps.append("%s devia levantar erro nomeado" % nome)
        except ValueError as exc:
            if "PE-MZ-01" not in str(exc):
                gaps.append("%s sem o codigo da folha: %r" % (nome, exc))
    # ausente e vazio um por um: laje sem armadura declara em texto,
    # nunca numero
    for nome, mut in (("armaduras None",
                       lambda r: r["laje"].pop("armaduras", None)),
                      ("armaduras {}",
                       lambda r: r["laje"].__setitem__("armaduras", {}))):
        r = _r_mez()
        mut(r)
        _p, _v, _pl, _s, aus = dp.adaptar_galpao_mezanino(r)
        if dp.AUSENCIA_LAJE_SEM_ARMADURA not in aus:
            gaps.append("%s sem declarar a armadura: %r" % (nome, aus))
        pdf = gmz.gerar_prancha_mezanino(r, str(tmp_path / "sem-arm"),
                                        {"slug": "g146"})
        import fitz

        with fitz.open(pdf) as d:
            texto = " ".join(d[k].get_text() for k in range(d.page_count))
        if "armadura nao dimensionada" not in texto:
            gaps.append("%s fora do quadro da folha" % nome)
        if "0.00 cm2/m" in texto:
            gaps.append("%s virou numero inventado" % nome)
    # zero calculado honesto: q_uso=0 sai com q 0.00 (numero do calculo)
    r0 = _r_mez(q_uso=0.0)
    pav0 = dp.adaptar_galpao_mezanino(r0)[0]
    if abs(pav0["q_kN_m2"]) > 1e-9:
        gaps.append("q_uso=0 devia chegar a folha como 0: %r" % (pav0,))
    # injecao: emissor morto derruba so a MZ01 (erro nomeado, nunca
    # silencio) e as antigas seguem no status
    def emissor_morto(*_a, **_k):
        raise RuntimeError("formas do mezanino desligadas (injecao G146)")

    monkeypatch.setattr(dp, "planta_formas_svg", emissor_morto)
    res = gmz.montar_pranchas(_r_mez(), str(tmp_path / "morto"))
    if res.get("ok") or res.get("pranchas") != []:
        gaps.append("com o emissor morto a MZ01 devia cair: %r" % (res,))
    if "injecao G146" not in str(res.get("mezanino_erro")):
        gaps.append("causa da MZ01 nao nomeada: %r" % (res,))
    indice = [{"codigo": "PE-CO-04", "titulo": "Locacao"},
              {"codigo": "PE-MZ-01", "titulo": "Mezanino"}]
    puladas = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO,
        ["PE04_LOCACAO_FUNDACAO.pdf"],
        causas=ga._causas_folhas_galpao(
            {"mezanino": {"ok": False,
                          "mezanino_erro": res.get("mezanino_erro")}}))
    motivos = {p["prancha"]: p["motivo"] for p in puladas}
    if "injecao G146" not in motivos.get("MZ01_MEZANINO.pdf", ""):
        gaps.append("causa fora do motivo da pulada: %r" % (puladas,))
    if len(puladas) != 1:
        gaps.append("a PE-CO-04 nao devia cair junto: %r" % (puladas,))
    sem_causa = ga._conferir_indice_galpao(
        indice, ga._PRANCHA_ARQUIVO_GALPAO, ["PE04_LOCACAO_FUNDACAO.pdf"])
    if "causa proxima" in sem_causa[0]["motivo"]:
        gaps.append("sem causa medida o motivo inventou uma: %r" % (sem_causa,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G146 conv13:\n%s" % "\n".join("  - " + g for g in gaps))


def test_05_tres_aceites_da_folha(tmp_path):
    """Os tres aceites (convencao 6): esta certa, sai no manifesto, diz o
    que desenha — pagina no emissor, codigo no mapa, titulo que desenha."""
    import ast

    import galpao_adapter as ga
    import pacote_legal as pl

    gaps = []
    # (1) esta certa: a pagina existe no emissor (AST, fonte independente)
    arvore = ast.parse(open(os.path.join(GALPAO, "techdraw_mezanino.py"),
                            encoding="utf-8").read())
    paginas = {n.args[1].value for n in ast.walk(arvore)
               if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "_nova_prancha"
               and len(n.args) >= 2
               and isinstance(n.args[1], ast.Constant)}
    if "MZ01_MEZANINO" not in paginas:
        gaps.append("MZ01_MEZANINO fora do techdraw_mezanino: %r"
                    % sorted(paginas))
    carimbos = set()
    for n in ast.walk(arvore):
        if isinstance(n, ast.Call) and len(n.args) >= 3 \
                and isinstance(n.args[2], ast.Constant):
            carimbos.add(n.args[2].value)
    if "MZ-01" not in carimbos:
        gaps.append("carimbo MZ-01 fora do techdraw_mezanino: %r"
                    % sorted(carimbos))
    # (2) sai no manifesto: codigo no mapa 1:1 com o arquivo emitido
    if ga._PRANCHA_ARQUIVO_GALPAO.get("PE-MZ-01") != "MZ01_MEZANINO.pdf":
        gaps.append("mapa PE-MZ-01 != MZ01_MEZANINO.pdf: %r"
                    % (ga._PRANCHA_ARQUIVO_GALPAO.get("PE-MZ-01"),))
    # (3) diz o que desenha: titulo do indice + carimbo + cobertura escrita
    titulos = {f["codigo"]: f["titulo"]
               for f in pl.indice_de_pranchas(["mezanino"])}
    if "mezanino" not in titulos.get("PE-MZ-01", "").lower():
        gaps.append("indice nao diz mezanino: %r" % (titulos,))
    entradas = {e["arquivo"]: e
                for e in pl.CORRESPONDENCIA_NUMERACAO_GALPAO["entradas"]}
    ent = entradas.get("MZ01_MEZANINO.pdf") or {}
    if ent.get("cobre") != ["PE-MZ-01"]:
        gaps.append("correspondencia sem cobrir PE-MZ-01: %r" % (ent,))
    if "MZ-01" not in str(ent.get("carimbo", "")):
        gaps.append("correspondencia sem o carimbo MZ-01: %r" % (ent,))
    assert tmp_path.is_dir()
    assert not gaps, (
        "G146 aceites:\n%s" % "\n".join("  - " + g for g in gaps))
