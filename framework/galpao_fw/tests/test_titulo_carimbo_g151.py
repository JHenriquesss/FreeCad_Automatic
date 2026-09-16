"""G151 - o titulo que o carimbo corta em 26 caracteres.

Medido (D176 + G151): techdraw_exec._cap_titulo(t, maxlen=26) corta com "…".
AST de toda chamada _carimbo* com titulo literal + LIGACOES + TITULOS da rota
SVG + TITULO_CARIMBO_MZ01: 20 cortados (15 literais em 9 arquivos + 5 TITULOS
espelho em prancha_svg_direta) + 10 limpas declaradas (DETALHE-/MAO-FRANCESA
sem reticencia). A MZ01 foi curada na D176 (25).

Entregue:
  1. LENTE (varredura_titulo_carimbo_g151.py, fonte unica): todo titulo passa
     por _cap_titulo sem "…"; limpa so com entrada em ABREVIACOES_LIMPAS.
  2. TITULOS curtos <=26 sem mudar drawing_number nem codigo de prancha;
     sheet_number coerente com as paginas de cada PDF (MZ01 01/03..03/03).
  3. BASELINE nos dois sentidos + vermelho por injecao em tmp_path.

Convencoes: 01 baseline dois sentidos, 02 tmp_path, 07 instrumento acusa,
uma fonte so (a lente e importada da producao).
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_titulo_carimbo_g151 as vt


def _escreve(tmp_path, nome, fonte):
    p = tmp_path / nome
    p.write_text(fonte, encoding="utf-8")
    return p


def test_01_baseline_repo_verde_e_fechado():
    """O repo corrigido: 0 cortados, 10 limpas triadas, confere OK."""
    res = vt.confere()
    falhas = []
    if not res["OK"]:
        falhas.append("confere nao OK:\n%s" % vt.relatorio_pt(res))
    if res["cortados"]:
        falhas.append("cortados=%d, esperado 0:\n%s" % (len(res["cortados"]), vt.relatorio_pt(res)))
    if len(vt.ABREVIACOES_LIMPAS) != 10:
        falhas.append("abreviacoes=%d, esperado 10" % len(vt.ABREVIACOES_LIMPAS))
    # todo titulo no disco cabe sem reticencia (prova independente da lente)
    from techdraw_exec import _cap_titulo
    for d in vt.varredura():
        if "…" in _cap_titulo(d["titulo"]):
            falhas.append("titulo cortado no disco: %s:%d %r -> %r"
                          % (d["arquivo"], d["linha"], d["titulo"], _cap_titulo(d["titulo"])))
        if len(_cap_titulo(d["titulo"])) > 26:
            falhas.append("titulo estoura a celula: %s:%d %r" % (d["arquivo"], d["linha"], d["titulo"]))
    assert not falhas, "\n---\n".join(falhas)


def test_02_vermelho_por_injecao_titulo_longo_nomeia_arquivo_linha(tmp_path):
    """O instrumento acusa (convencao 7): titulo longo novo reprova."""
    _escreve(tmp_path, "techdraw_exec.py",
             "def f(cfg):\n"
             "    from techdraw_exec import _carimbo\n"
             "    return _carimbo(cfg, \"TITULO INJETADO MUITO LONGO PARA A CELULA XYZ\", \"PE-99\", \"-\", \"99/99\")\n")
    res = vt.confere(raiz=tmp_path, abreviacoes={})
    assert not res["OK"] and len(res["cortados"]) == 1, res
    arq, func, tit, linha = res["cortados"][0]
    assert arq == "techdraw_exec.py" and linha == 3, res
    assert "INJETADO" in tit, res


def test_03_resolvida_acusa_nos_dois_sentidos(tmp_path):
    """Baseline nos dois sentidos: abrevicao que sumiu vira resolvida."""
    _escreve(tmp_path, "techdraw_exec.py",
             "def f(cfg):\n"
             "    return 1\n")
    tri = {"TITULO SUMIDO XYZ": ("CURTO", "motivo escrito")}
    res = vt.confere(raiz=tmp_path, abreviacoes=tri)
    assert not res["OK"] and res["resolvidas"] == ["TITULO SUMIDO XYZ"], res


def test_04_limpa_sem_motivo_ou_nao_declarada_reprova(tmp_path):
    """Limpa sem motivo ou sem entrada reprova."""
    _escreve(tmp_path, "techdraw_exec.py",
             "def f(cfg):\n"
             "    from techdraw_exec import _carimbo\n"
             "    return _carimbo(cfg, \"DETALHE - BASE DE COLUNA\", \"PE-06\", \"-\", \"06/09\")\n")
    res = vt.confere(raiz=tmp_path, abreviacoes={})
    assert not res["OK"] and res["nao_declaradas"], res
    chave = ("techdraw_exec.py", "f", "DETALHE - BASE DE COLUNA")
    res2 = vt.confere(raiz=tmp_path, abreviacoes={"DETALHE - BASE DE COLUNA": ("BASE DE COLUNA", "")})
    assert not res2["OK"] and res2["sem_motivo"], res2


def test_05_mz01_sheet_number_coerente_e_sem_reticencia(tmp_path):
    """MZ01: 3 paginas, carimbo 01/03..03/03, sem reticencia no PDF."""
    import galpao_mezanino as gmz
    import fitz
    pdf = gmz.gerar_prancha_mezanino(
        gmz.rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
                   "x0": 2.0, "y0": 2.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0}),
        str(tmp_path), {"slug": "g151"})
    gaps = []
    with fitz.open(pdf) as d:
        if d.page_count != 3:
            gaps.append("MZ01 paginas=%d, esperado 3" % d.page_count)
        folhas = []
        for k in range(d.page_count):
            txt = d[k].get_text()
            if "…" in txt:
                gaps.append("pagina %d com reticencia no carimbo" % (k + 1))
            for ln in txt.splitlines():
                if ln.startswith("Folha "):
                    folhas.append(ln.split("|")[0].strip())
        if folhas != ["Folha 01/03", "Folha 02/03", "Folha 03/03"]:
            gaps.append("sheet_number incoerente: %r" % folhas)
    assert not gaps, "G151 MZ01:\n" + "\n".join("  - " + g for g in gaps)


def test_06_rota_svg_sheet_number_coerente_e_sem_reticencia(tmp_path):
    """Rota SVG: cada PDF de 1 pagina carimba a propria folha, sem reticencia."""
    import fitz
    import galpao_hidraulica as ghi
    import prancha_svg_direta as psd
    r = ghi.rodar({"geometria": {"L": 40.0, "W": 20.0, "H": 6.0},
                   "hidraulica": {"aparelhos_agua": {"bacia_caixa": 2, "lavatorio": 2},
                                  "aparelhos_esgoto": {"bacia": 2, "lavatorio": 2}}})
    res = psd.montar_pranchas_rota_direta(r, str(tmp_path), "hidraulica")
    assert res.get("ok"), res
    gaps = []
    for pdf, esperada in zip(res["arquivos"], ("Folha 01/02", "Folha 02/02")):
        with fitz.open(pdf) as d:
            txt = " ".join(d[k].get_text() for k in range(d.page_count))
            if "…" in txt:
                gaps.append("%s com reticencia" % pdf)
            if esperada not in txt:
                gaps.append("%s sem %r" % (pdf, esperada))
    assert not gaps, "G151 rota SVG:\n" + "\n".join("  - " + g for g in gaps)
