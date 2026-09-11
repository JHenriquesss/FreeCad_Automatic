"""G83 - a varredura das guardas de um eixo so.

Contexto: o G77 achou uma guarda que media SO o X
(test_desenho_concreto.py::test_tudo_cabe_no_canvas, regex sobre a fonte
do SVG, 4 coletas de x/cx/x1/x2 e nenhuma de y). O defeito que ela
deixou passar por anos: a cota de largura do pilar caia 3,5 px ABAIXO
da folha, invisivel no entregue.

1. FERRAMENTA (varredura_guardas_um_eixo.py, mesma familia de AST do
   G48/G51/G75): para cada funcao em tests/**/test_*.py que mencione
   SVG, mede tres sinais sintaticos: X_ONLY (x/cx/x1/x2/width sem nenhum
   y/cy/y1/y2/height), W_SEM_H (width sem height, e espelhos Y_ONLY /
   H_SEM_W) e REGEX_COORD_SEM_PARSE (re.findall/search com padrao que
   cita coordenada sem nenhum parse no corpo). Regex sobre ROTULO
   (">([^<]+)</text>") nao e coordenada e nao entra.
2. PROMOCOES (neste goal, sem apagar a guarda antiga): test_tudo_cabe_
   no_canvas ganhou o eixo Y por regex + parse (ET.fromstring) + a
   guarda generica confere_folha_svg; test_planta_cabe_no_canvas ganhou
   parse + confere_folha_svg. A prova do defeito original mora no G77
   (test_prancha_de_armacao_acompanha_a_altura_da_secao, com baseline
   na altura fixa antiga); a prova da perna de parse nova esta no
   test_04 abaixo (injeta rect abaixo da folha e a guarda acusa).
3. TRIAGEM (rigor G10): item a item, medida. So os 2 de desenho_
   concreto viraram correcao; o resto fica com o motivo medido pelo
   qual NAO e bug. O que a lente NAO cobre esta dito no cabecalho da
   ferramenta (molde DIVIDA-LENTE do G51).

Triagem do que FICOU (legitimo ou falso-positivo, com motivo):
- branches/g4 test_toda_celula_das_tres_pranchas_cabe_na_coluna
  (X_ONLY + W_SEM_H): guarda HORIZONTAL por parse (ET.fromstring; le
  x/width via .get). O eixo X e o objeto da guarda (texto caber na
  largura da coluna); eventual estouro vertical e outra propriedade,
  fora do escopo desta guarda.
- branches/phase6b test_nenhum_texto_do_quadro_invade_a_coluna_seguinte
  (W_SEM_H): colisao HORIZONTAL por parse (agrupa por y como chave,
  ordena por x). O width lido e a largura da folha (borda direita); a
  altura nao entra porque a propriedade e horizontal por construcao.
- test_alvenaria_bim_pranchas_g62 test_faixa_de_ajuste_nao_cobre_a_linha_
  de_Nd (Y_ONLY): ordenacao VERTICAL por parse (y_texto < y_faixa). O
  eixo Y e o objeto da guarda (faixa acima da linha de Nd); o X nao
  se aplica.
- test_executivo_hidr_cli test_svg_*_sem_virgula_nas_coordenadas (2x
  REGEX_COORD_SEM_PARSE): propriedade POR ATRIBUTO (nenhuma coordenada
  com virgula decimal), nao medida de posicao. O padrao cita x|y|cx|cy|
  width|height juntos (os dois eixos); o eixo e irrelevante por
  construcao. E anda em par com o teste irmao de parse
  (test_svg_hidraulica_e_xml_bem_formado).
- test_executivo_incendio test_planta_desenha_contagem_exata e test_
  planta_iluminacao_emergencia_count_driven (X_ONLY + W_SEM_H): CONTAGEM
  desenho-vs-dado (svg.count de estilo), nao medida de posicao. O
  `width` que a lente ve e `stroke-width` do estilo contado. Cegueira
  de eixo nao se aplica a quem nao mede eixo.
- test_fase619_glifo_solda _tris (REGEX_COORD_SEM_PARSE): helper que
  extrai os triangulos do filete; os chamadores checam Y (acima/abaixo
  da linha, "30,24" vs "30,4") contra a fonte independente AWS A2.4.
  Assercao pontual de conteudo geometrico, nao guarda de folha.
- test_folhas_g77 _cota_mais_baixa (H_SEM_W + Y_ONLY): helper da guarda
  VERTICAL do proprio defeito do G77 (y do texto mais baixo vs height),
  por parse. Y-only por desenho; o X mora na guarda irma promovida
  neste goal.
- test_folhas_g77 test_nota_c55_c90_nao_pisa_na_cota_da_secao (H_SEM_W +
  Y_ONLY): reserva VERTICAL de linha (h_com >= h_sem + ALTURA_NOTA) +
  confere_folha_svg (que cobre os dois eixos). Y-only no trecho
  vertical; o resto esta na guarda generica chamada no corpo.
- test_fotovoltaico test_grafico_svg_xml_valido (X_ONLY):
  FALSO-POSITIVO conhecido da lente: o "x" e valor de dicionario
  ({"motivo": "x"}), nao coordenada. O corpo so checa titulo + parse
  (nao e guarda geometrica). Limitacao dita no cabecalho da ferramenta.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_guardas_um_eixo as vg


def _contagem():
    return Counter((d["arquivo"], d["funcao"], d["classe"])
                   for d in vg.varredura())


def test_01_ferramenta_enxerga_piso_e_so_classe_conhecida():
    tudo = vg.varredura()
    assert len(tudo) >= 16, "piso G83: a varredura tem de enxergar >= 16, viu %d" % len(tudo)
    assert {d["classe"] for d in tudo} <= {"X_ONLY", "Y_ONLY", "W_SEM_H",
                                          "H_SEM_W", "REGEX_COORD_SEM_PARSE"}
    assert all(set(d) == {"arquivo", "funcao", "linha", "classe"}
               for d in tudo)
    # o caso que motivou o goal ja foi promovido: nao pode reaparecer aqui
    alvos = {(d["arquivo"], d["funcao"]) for d in tudo}
    assert ("test_desenho_concreto.py", "test_tudo_cabe_no_canvas") not in alvos, alvos
    assert ("test_desenho_concreto.py", "test_planta_cabe_no_canvas") not in alvos, alvos


BASELINE_G83 = Counter({
    (u'branches/g4/test_casa_residencial_adapter.py', u'test_toda_celula_das_tres_pranchas_cabe_na_coluna', u'W_SEM_H'): 1,
    (u'branches/g4/test_casa_residencial_adapter.py', u'test_toda_celula_das_tres_pranchas_cabe_na_coluna', u'X_ONLY'): 1,
    (u'branches/phase6b/test_residential_electrical_deliverables.py', u'test_nenhum_texto_do_quadro_invade_a_coluna_seguinte', u'W_SEM_H'): 1,
    (u'test_alvenaria_bim_pranchas_g62.py', u'test_faixa_de_ajuste_nao_cobre_a_linha_de_Nd', u'Y_ONLY'): 1,
    (u'test_executivo_hidr_cli.py', u'test_svg_climatizacao_sem_virgula_nas_coordenadas', u'REGEX_COORD_SEM_PARSE'): 1,
    (u'test_executivo_hidr_cli.py', u'test_svg_hidraulica_sem_virgula_nas_coordenadas', u'REGEX_COORD_SEM_PARSE'): 1,
    (u'test_executivo_incendio.py', u'test_planta_desenha_contagem_exata', u'W_SEM_H'): 1,
    (u'test_executivo_incendio.py', u'test_planta_desenha_contagem_exata', u'X_ONLY'): 1,
    (u'test_executivo_incendio.py', u'test_planta_iluminacao_emergencia_count_driven', u'W_SEM_H'): 1,
    (u'test_executivo_incendio.py', u'test_planta_iluminacao_emergencia_count_driven', u'X_ONLY'): 1,
    (u'test_fase619_glifo_solda.py', u'_tris', u'REGEX_COORD_SEM_PARSE'): 1,
    (u'test_folhas_g77.py', u'_cota_mais_baixa', u'H_SEM_W'): 1,
    (u'test_folhas_g77.py', u'_cota_mais_baixa', u'Y_ONLY'): 1,
    (u'test_folhas_g77.py', u'test_nota_c55_c90_nao_pisa_na_cota_da_secao', u'H_SEM_W'): 1,
    (u'test_folhas_g77.py', u'test_nota_c55_c90_nao_pisa_na_cota_da_secao', u'Y_ONLY'): 1,
    (u'test_fotovoltaico.py', u'test_grafico_svg_xml_valido', u'X_ONLY'): 1,
})


def test_02_baseline_nos_dois_sentidos():
    """Regra do G33 aplicada a esta varredura (molde do test_08 do G51 e
    do test_02 do G75). Sem o baseline a ferramenta e RELATORIO, nao guarda."""
    agora = _contagem()
    mudaram = sorted(
        chave for chave in set(agora) | set(BASELINE_G83)
        if agora[chave] != BASELINE_G83[chave])
    novas = sorted(set(agora) - set(BASELINE_G83))
    sumidas = sorted(set(BASELINE_G83) - set(agora))
    # G97: um assert so. O loop que levantava mais dois asserts em sequencia
    # escondia o segundo lado (a licao do G77).
    lados = []
    if mudaram:
        lados.append("contagem mudou: %s" % (
            ", ".join("em %r: baseline %d, agora %d"
                      % (chave, BASELINE_G83[chave], agora[chave])
                      for chave in mudaram),))
    if novas:
        lados.append("guarda de um eixo (ou regex sem parse) nao triada: %r. "
                     "Ou e promovida a parse + confere_folha_svg, ou entra no "
                     "BASELINE_G83 com motivo medido (rigor G10)." % (novas,))
    if sumidas:
        lados.append("sitios que a varredura nao acha mais: %r. Se viraram "
                     "parse, o baseline MUDA junto (senao protege nome morto)."
                     % (sumidas,))
    assert not lados, "baseline G83 reprova:\n" + "\n".join(lados)


_GAP_X_ONLY = [
    "import re",
    "",
    "def test_guarda_so_x(svg):",
    "    W = int(re.search(r'width=\"(\\d+)\"', svg).group(1))",
    "    xs = [float(v) for v in re.findall(r'x=\"([\\d.]+)\"', svg)]",
    "    assert max(xs) <= W + 5",
    "",
]

_GAP_OK = [
    "import re",
    "import xml.etree.ElementTree as ET",
    "import desenho_svg_base as sb",
    "",
    "def test_guarda_dois_eixos(svg):",
    "    root = ET.fromstring(svg)",
    "    W, H = float(root.get(\"width\")), float(root.get(\"height\"))",
    "    assert sb.confere_folha_svg(svg)[\"ok\"]",
    "",
]


def test_03_vermelho_por_injecao_nos_dois_sentidos(tmp_path):
    """Prova por injecao em diretorio temporario (licao do D81: sem mutar o
    repo). A guarda X-only do G77 e acusada nas tres classes; a guarda
    completa (dois eixos por parse + confere) passa limpa."""
    gap = tmp_path / "test_gap_x.py"
    gap.write_text(chr(10).join(_GAP_X_ONLY) + chr(10), encoding="utf-8")
    achados = {(d["arquivo"], d["funcao"], d["classe"])
               for d in vg.varredura(raiz=str(tmp_path))}
    assert ("test_gap_x.py", "test_guarda_so_x", "X_ONLY") in achados, achados
    assert ("test_gap_x.py", "test_guarda_so_x", "W_SEM_H") in achados, achados
    assert ("test_gap_x.py", "test_guarda_so_x", "REGEX_COORD_SEM_PARSE") in achados, achados
    limpo = tmp_path / "test_limpo_xy.py"
    limpo.write_text(chr(10).join(_GAP_OK) + chr(10), encoding="utf-8")
    so_limpo = [d for d in vg.varredura(raiz=str(tmp_path))
                if d["arquivo"] == "test_limpo_xy.py"]
    assert so_limpo == [], so_limpo


def _armacao_g83():
    import galpao_concreto as gc
    import desenho_concreto as dc
    r = gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0, "n_porticos": 7,
                  "v0": 40.0, "cat": "IV", "classe": "B", "G_roof": 0.30,
                  "Q_roof": 0.25, "fck": 30e3, "sigma_solo_adm": 250.0})
    return dc.prancha_armacao_svg(r)


def test_04_guarda_promovida_acusa_estouro_em_y():
    """A perna de parse da guarda completa acusa o defeito que a versao
    X-only deixava passar: elemento abaixo da folha (a cota a 3,5 px).
    Injecao em string em memoria (D81: sem mutar o repo); a comparacao e
    contra a altura declarada no cabecalho (fonte independente do desenho,
    conv. 5: nada deriva do resultado)."""
    import desenho_svg_base as sb
    svg_ok = _armacao_g83()
    assert sb.confere_folha_svg(svg_ok)["ok"], sb.confere_folha_svg(svg_ok)
    svg_ruim = svg_ok.replace("</svg>",
                              '<rect x="10" y="99999" width="10" height="10"/></svg>')
    c = sb.confere_folha_svg(svg_ruim)
    assert c["ok"] is False and "desenho-fora-da-folha" in c["motivo"], c
