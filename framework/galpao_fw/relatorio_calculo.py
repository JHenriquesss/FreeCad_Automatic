# ============================================================================
# relatorio_calculo.py - Gera UM PDF com TODOS os memoriais de calculo do
# galpao, cada modulo precedido do METODO (norma + procedimento) para ajudar
# o Engenheiro Senior a conferir. Le o MEMORIAL-CONSOLIDADO.txt que o
# rodar_galpao ja produz (fonte unica da verdade: os numeros do calculo) e
# acrescenta o bloco de METODO curado por modulo.
#
# Uso:
#   python relatorio_calculo.py <out_dir> [pdf_saida]
#     <out_dir> = pasta onde calcular() gravou os memoriais (tem
#                 MEMORIAL-CONSOLIDADO.txt). Se faltar, roda um caso demo.
#   ou, de codigo:
#     import relatorio_calculo as RC
#     RC.gerar_pdf(out_dir, pdf_path, titulo="GALPAO ... ")
#     RC.gerar_de_spec(spec, out_dir, pdf_path)   # roda o calculo e o PDF
# ============================================================================
import os
import re
import sys
import math
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Preformatted,
                                PageBreak, Table, TableStyle, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ----------------------------------------------------------------------------
# METODO por modulo: norma + procedimento resumido. Chave = prefixo do titulo
# da secao no MEMORIAL-CONSOLIDADO (match por "startswith" apos normalizar).
# Texto conciso e verificavel; o CALCULO (numeros) vem do memorial ao lado.
# ----------------------------------------------------------------------------
METODOS = {
    "1. VENTO": (
        "NBR 6123:1988. Pressao dinamica q = 0,613 . Vk^2 (Vk em m/s -> q em "
        "N/m2), Vk = V0 . S1 . S2 . S3. Coeficientes de pressao externa (Cpe) "
        "por zona e interna (Cpi) conforme permeabilidade/abertura dominante. "
        "Carga em cada superficie = (Cpe - Cpi) . q. Combina-se o caso de maior "
        "sucecao/pressao para o portico."),
    "1b. VENTO LONGITUDINAL": (
        "NBR 6123:1988. Vento incidindo no oitao: forcas de arrasto sobre a "
        "area frontal projetada, distribuidas ao sistema de contraventamento "
        "longitudinal (barras e travamentos)."),
    "1c. PONTE ROLANTE": (
        "NBR 8800:2008 (acoes de equipamento) + dados do fabricante. Reacao "
        "vertical maxima por roda com o carro na aproximacao minima; impacto "
        "vertical pelo coeficiente phi; forcas horizontais transversais "
        "(translacao/frenagem do carro) e longitudinais como fracoes da carga "
        "movel. Aplicadas na viga de rolamento e no console."),
    "1d. CONSOLE": (
        "NBR 8800:2008 (metal da solda 6.2.5, cisalhamento da chapa 5.4) + "
        "grupo de solda ELASTICO (vetorial, mecanica/AISC). Console da ponte: "
        "reacao vertical do trilho + forca transversal, com excentricidade -> "
        "momento; dimensiona a perna do filete (first-fit padrao). Compoe "
        "primitivos de ligacoes.py."),
    "2. PORTICO": (
        "Analise elastica linear do portico plano (metodo da rigidez). Esforcos "
        "N, V, M em cada barra para todas as combinacoes de acoes (ELU/ELS), "
        "coerentes com as reacoes de apoio usadas na base e fundacao."),
    "3. 2a ORDEM": (
        "NBR 8800:2008, Anexo D (metodo da amplificacao). Efeitos de 2a ordem "
        "P-delta (local) e P-Delta (global) via coeficientes B1 e B2; verifica "
        "a estabilidade e amplifica os momentos para o dimensionamento."),
    "3b. PORTICO ALMA VARIAVEL": (
        "Portico de misula de alma variavel (tapered), perfil I duplamente "
        "simetrico com altura variando linearmente (funda no joelho, rasa na "
        "cumeeira). A analise do portico usa a secao por segmento (rigidez EI "
        "variavel ao longo do rafter); a secao do JOELHO governa a flexo-compressao "
        "(maior momento). Secoes geradas por alma_variavel.secao_tapered."),
    "3c. PORTICO TRELICADO (TESOURA)": (
        "Trelica de cobertura (Warren/Pratt) biapoiada nos pilares, banzo superior "
        "parabolico, isostatica (b+r=2j). Esforcos axiais pelo METODO DOS NOS "
        "(equilibrio nodal, sistema 2j x (b+3)); banzo inferior traciona, superior "
        "comprime. Barras verificadas por NBR 8800 (tracao = escoamento A.fy/ga1; "
        "compressao = flambagem chi.Q.A.fy/ga1). Sucao de vento = A CONFIRMAR."),
    "4. PERFIS": (
        "NBR 8800:2008. Barras a flexo-compressao: equacao de interacao 5.4.2 "
        "(N/Nrd + fatores . M/Mrd <= 1,0). Resistencias com estados-limite de "
        "flambagem global, local da alma (FLA), da mesa (FLM) e lateral com "
        "torcao (FLT); esbeltez reduzida e fatores de reducao."),
    "5. MAO-FRANCESA": (
        "NBR 8800:2008. Travamento da mesa comprimida por maos-francesas: forca "
        "de estabilizacao no ponto de travamento (fracao do esforco de "
        "compressao da mesa) e verificacao do elemento de travamento."),
    "6. TERCAS": (
        "NBR 14762:2010 (perfis formados a frio). Flexao obliqua (eixos x e y), "
        "estado-limite distorcional, e verificacao de flecha (ELS) para a "
        "combinacao de vento/permanente no vao entre porticos."),
    "6b. TELHA": (
        "Catalogo do fabricante + NBR 6123. Verifica o vao livre da telha para "
        "a sucecao de vento e o peso proprio, comparando com a tabela de "
        "vao x carga admissivel do perfil de telha adotado."),
    "7. SECUNDARIOS": (
        "NBR 8800/14762. Longarinas, escoras e montantes de fechamento: flexao "
        "e/ou compressao conforme funcao, esbeltez e flecha."),
    "8. CONTRAVENTAMENTO": (
        "NBR 8800:2008. Barras redondas tracionadas (contraventamento em X) "
        "pretensionadas: dimensionamento ao escoamento da secao bruta e "
        "ruptura da secao liquida; limite de esbeltez para montagem."),
    "8b. GUSSET": (
        "NBR 8800:2008 (estados-limite) + largura efetiva de Whitmore (convencao "
        "AISC, 30 graus). Chapa de gusset do no de contraventamento: tracao na "
        "secao de Whitmore (5.2.2), flambagem da faixa (5.3.3, so se comprimida), "
        "solda de filete ao membro (6.2.5) e rasgamento em bloco (6.5.6) se "
        "parafusada. Compoe primitivos verificados de ligacoes.py."),
    "9. VERGA": (
        "NBR 8800:2008. Viga sobre a abertura (portao/porta): flexao simples "
        "com a carga de fechamento acima do vao e verificacao de flecha."),
    "10. BASE": (
        "AISC Design Guide 1 + NBR 8800. Placa de base com chumbadores pelo "
        "metodo da excentricidade (e = M/N): distribuicao de pressao de contato "
        "no concreto, tracao nos chumbadores, flexao da placa e verificacao do "
        "concreto (esmagamento)."),
    "11. SAPATA": (
        "NBR 6118:2014. Envelope de combinacoes ELU (N, V, M na base). Verifica "
        "tensao no solo <= admissivel, seguranca ao tombamento e ao "
        "deslizamento (fatores FS), puncao (22.6.2.2) e armadura de flexao das "
        "duas direcoes. sigma_solo,adm e parametro de sondagem (geotecnia)."),
    "11. BLOCO": (
        "NBR 6122:2022 item 7.8.2 (fundacao rasa de concreto SIMPLES, sem armadura). "
        "O bloco resiste por bielas de compressao: a altura garante o angulo da face "
        "beta >= 60 graus com a horizontal (h >= tan(60).(dim_bloco - dim_pilar)/2), "
        "dispensando armadura de tracao. Envelope ELU: tensao no solo <= admissivel, "
        "seguranca ao tombamento e deslizamento, e tensao de tracao no concreto "
        "limitada a ~fck/25 (Alonso). sigma_solo,adm e parametro de sondagem."),
    "11b. VIGA DE BALDRAME": (
        "NBR 6118:2014. Viga de baldrame sob o fechamento: flexao e cisalhamento "
        "para a carga de parede/pe-direito, apoiada nos blocos/sapatas."),
    "11c. FUNDACAO PROFUNDA": (
        "Metodos semi-empiricos (Aoki-Velloso / Decourt-Quaresma) para "
        "capacidade por atrito lateral + ponta a partir do SPT; efeito de grupo "
        "e bloco de coroamento. Parametros do solo por sondagem."),
    "11d. FOGO": (
        "NBR 14323:2013. Verificacao em incendio: fator de massividade do "
        "perfil, elevacao de temperatura para o TRRF requerido e temperatura "
        "critica do aco (reducao de resistencia com a temperatura)."),
    "11e. ESCADA": (
        "NBR 8800 + NBR 6120 (sobrecargas). Degraus/longarinas da escada: "
        "flexao para a sobrecarga de uso e verificacao de flecha."),
    "11f. PLATAFORMA": (
        "NBR 8800 + NBR 6120. Piso/vigas da plataforma: flexao para a "
        "sobrecarga de uso, apoio e flecha."),
    "11g. SAPATA DE DIVISA": (
        "NBR 6118:2014 + metodo de Alonso. Pilar na linha do lote: sapata "
        "EXCENTRICA (a resultante do solo nao passa pelo eixo do pilar) equilibrada "
        "por VIGA ALAVANCA ate o pilar interno vizinho. Reacao majorada R = P . "
        "dist_eixos / (dist_eixos - e); alivio na sapata interna; flexao/cortante "
        "da viga de equilibrio. sigma_solo,adm por sondagem."),
    "12. LIGACOES": (
        "NBR 8800:2008 (cap. 6 e Anexo). Parafusos a cisalhamento e tracao, "
        "pressao de contato (bearing), ruptura de bloco de cisalhamento e "
        "solda de filete (metal-base e eletrodo E70XX)."),
    "13. CALHAS E CONDUTORES": (
        "NBR 10844:1989 + Bellei (Edificios Industriais 2.4). Area de contribuicao "
        "da cobertura x intensidade pluviometrica local I -> vazao de projeto Q; "
        "secao da calha (lamina d'agua + borda livre >= 25%, Manning) e diametro/"
        "numero de condutores. Criterio de Bellei (As >= 1 cm2 por m2 de telhado). "
        "I pluviometrica local = A CONFIRMAR (dado regional)."),
}

# fim de _METODOS -> texto padrao quando o modulo nao tem entrada dedicada
_METODO_PADRAO = ("Procedimento e norma conforme cabecalho do memorial abaixo. "
                  "Verificar contra a referencia normativa citada.")


def _metodo_para(titulo):
    t = titulo.strip()
    for chave, txt in METODOS.items():
        if t.startswith(chave):
            return txt
    return _METODO_PADRAO


# ----------------------------------------------------------------------------
# Parsing do MEMORIAL-CONSOLIDADO.txt: preambulo (capa/quadro) + secoes
# delimitadas por linhas de '#' (####\nTITULO\n####\n\nCORPO).
# ----------------------------------------------------------------------------
_SEP = "#" * 70


def _parse_consolidado(texto):
    """Retorna (preambulo, [(titulo, corpo), ...])."""
    linhas = texto.splitlines()
    # localiza blocos: SEP / TITULO / SEP
    idx = [i for i, l in enumerate(linhas) if l.strip(" ").startswith("#" * 10)]
    if not idx:
        return texto, []
    preamb = "\n".join(linhas[:idx[0]]).rstrip()
    secoes = []
    # cada secao: linha SEP em i, titulo em i+1, SEP em i+2, corpo ate proxima SEP-tripla
    marcas = []
    i = 0
    while i < len(linhas):
        if linhas[i].strip().startswith("#" * 10):
            marcas.append(i)
        i += 1
    # marcas vem em trincas (abre, titulo? , fecha). Mais simples: varre por
    # padrao SEP, TITULO, SEP.
    j = 0
    while j < len(marcas):
        a = marcas[j]
        # espera titulo em a+1 e SEP em a+2
        if a + 2 < len(linhas) and linhas[a + 2].strip().startswith("#" * 10):
            titulo = linhas[a + 1].strip()
            # corpo vai de a+3 ate a proxima marca de abertura
            prox = None
            for m in marcas:
                if m > a + 2:
                    prox = m
                    break
            fim = prox if prox is not None else len(linhas)
            corpo = "\n".join(linhas[a + 3:fim]).strip("\n")
            secoes.append((titulo, corpo))
            # avanca j para depois do SEP de fechamento
            while j < len(marcas) and marcas[j] <= a + 2:
                j += 1
        else:
            j += 1
    return preamb, secoes


# ----------------------------------------------------------------------------
# Geracao do PDF
# ----------------------------------------------------------------------------
def _estilos():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Capa", parent=ss["Title"], fontSize=22, leading=26,
                          alignment=TA_CENTER))
    ss.add(ParagraphStyle("SubCapa", parent=ss["Normal"], fontSize=11,
                          leading=15, alignment=TA_CENTER, textColor=colors.grey))
    ss.add(ParagraphStyle("Secao", parent=ss["Heading1"], fontSize=13,
                          leading=16, spaceBefore=6, spaceAfter=4,
                          textColor=colors.HexColor("#12395b")))
    ss.add(ParagraphStyle("MetodoTit", parent=ss["Normal"], fontSize=9,
                          leading=11, textColor=colors.HexColor("#12395b"),
                          fontName="Helvetica-Bold", spaceAfter=1))
    ss.add(ParagraphStyle("Metodo", parent=ss["Normal"], fontSize=9,
                          leading=12, alignment=TA_LEFT))
    ss.add(ParagraphStyle("Mono", parent=ss["Code"], fontSize=7.2, leading=8.6,
                          fontName="Courier"))
    ss.add(ParagraphStyle("Nota", parent=ss["Normal"], fontSize=8,
                          leading=10, textColor=colors.grey))
    ss.add(ParagraphStyle("Intro", parent=ss["Normal"], fontSize=9.5, leading=13,
                          alignment=TA_LEFT, spaceAfter=4))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], fontSize=11, leading=14,
                          textColor=colors.HexColor("#12395b"), spaceBefore=8,
                          spaceAfter=3))
    ss.add(ParagraphStyle("Cell", parent=ss["Normal"], fontSize=8.3, leading=10))
    ss.add(ParagraphStyle("CellB", parent=ss["Normal"], fontSize=8.3, leading=10,
                          fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("CellHead", parent=ss["Normal"], fontSize=8.3, leading=10,
                          fontName="Helvetica-Bold", textColor=colors.white))
    return ss


def _cabecalho_rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(15 * mm, 8 * mm, doc._titulo_curto)
    canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, "Pag. %d" % doc.page)
    canvas.drawCentredString(A4[0] / 2, 8 * mm,
                             "MEMORIAL DE CALCULO - CONCEITUAL - PENDENTE ART")
    canvas.restoreState()


# ----------------------------------------------------------------------------
# Blocos DIDATICOS (a partir do spec): premissas, levantamento de cargas e quadro
# de verificacoes colorido. Objetivo: um leitor entende de onde vem cada numero
# antes de chegar ao memorial de cada modulo.
# ----------------------------------------------------------------------------
def _vg(s):
    """Ponto decimal -> virgula (padrao BR) em textos ja formatados."""
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", str(s))


def _n(x, casas=2, suf=""):
    try:
        return _vg(("%%.%df" % casas) % float(x)) + suf
    except (TypeError, ValueError):
        return str(x)


def _tab(rows, widths, ss, header=None, destaque_ultima=False):
    """Table estilizada (zebra, cabecalho azul). rows = lista de listas de str."""
    data = []
    if header:
        data.append([Paragraph(str(c), ss["CellHead"]) for c in header])
    for r in rows:
        data.append([Paragraph(str(c), ss["Cell"]) for c in r])
    tb = Table(data, colWidths=widths, hAlign="LEFT")
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cdd6df")),
          ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9fb2c4"))]
    r0 = 0
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12395b"))]
        r0 = 1
    for i in range(r0, len(data)):
        if (i - r0) % 2 == 1:
            st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#eef2f6")))
    tb.setStyle(TableStyle(st))
    return tb


def _dados_entrada_flow(spec, ss):
    g = spec.get("geometria", {}); cob = spec.get("cobertura", {})
    ven = spec.get("vento", {}); car = spec.get("cargas", {})
    fec = spec.get("fechamento", {}); fun = spec.get("fundacao", {})
    slope = cob.get("slope"); incl = ("%s%%" % _n(slope * 100, 0)) if slope else "-"
    rows = [
        ["Geometria", "Vao transversal", _n(g.get("span"), 1, " m")],
        ["", "Comprimento total", _n(g.get("comprimento"), 1, " m")],
        ["", "Pe-direito (beiral)", _n(g.get("eave"), 2, " m")],
        ["", "Altura da cumeeira", _n(g.get("ridge"), 2, " m")],
        ["", "Inclinacao do telhado", incl],
        ["", "Vinculacao da base", "Engastada" if g.get("base_fixed") else "Rotulada"],
        ["Cobertura", "N de aguas", str(cob.get("aguas", 2))],
        ["", "Telha", str(cob.get("telha_tipo", "-"))],
        ["", "Calha de agua pluvial", "Sim" if cob.get("calha") else "Nao"],
        ["Vento", "V0 (velocidade basica)", _n(ven.get("v0"), 0, " m/s")],
        ["", "Categoria / Classe", "%s / %s" % (ven.get("cat", "-"), ven.get("classe", "-"))],
        ["", "S1 / S3", "%s / %s" % (_n(ven.get("s1"), 2), _n(ven.get("s3"), 2))],
        ["", "Abertura dominante (Cpi)",
         "Vedada" if str(ven.get("abertura_dominante", "")).startswith("veda") else "Portao"],
        ["Cargas", "Permanente cobertura G", _n(car.get("G"), 2, " kN/m2")],
        ["", "Sobrecarga Q", _n(car.get("Q"), 2, " kN/m2")],
        ["", "Peso proprio estrutura", _n(car.get("self"), 2, " kN/m2")],
        ["Fechamento", "Tipo", str(fec.get("tipo", "-"))],
        ["", "Peso do fechamento", _n(fec.get("peso"), 2, " kN/m2")],
        ["Fundacao", "Tipo", str(fun.get("tipo", "-"))],
        ["", "Tensao adm. do solo", _n(fun.get("sigma_solo_adm"), 0, " kN/m2")],
        ["", "fck do concreto", _n((fun.get("fck") or 0) / 1000.0, 0, " MPa")],
    ]
    return [Paragraph("Premissas e dados de entrada", ss["Secao"]),
            Paragraph("Todos os resultados deste memorial partem dos dados abaixo, "
                      "informados no projeto. Os itens marcados como dado de sitio "
                      "(solo, vento local) sao de responsabilidade de quem os forneceu.",
                      ss["Intro"]),
            _tab(rows, [70, 210, 130], ss,
                 header=["Grupo", "Dado", "Valor"]), Spacer(1, 5 * mm)]


def _cargas_flow(spec, out_dir, ss):
    """Levantamento de cargas DIDATICO: cada acao com valor, origem e destino, mais
    o vento (Vk, q) e a filosofia das combinacoes."""
    car = spec.get("cargas", {}); cob = spec.get("cobertura", {})
    fec = spec.get("fechamento", {}); ven = spec.get("vento", {})
    flow = [Paragraph("Levantamento de cargas", ss["Secao"]),
            Paragraph("O caminho das cargas segue a hierarquia da estrutura: a "
                      "cobertura carrega as <b>tercas</b>, que apoiam nos <b>porticos</b>; "
                      "os porticos descem para a <b>base</b> e a <b>fundacao</b>. O vento "
                      "atua nas superficies (paredes e telhado) e o fechamento pendura "
                      "na coluna (leve) ou desce pela <b>viga de baldrame</b> (alvenaria).",
                      ss["Intro"])]
    # --- Acoes permanentes e variaveis (verticais) ---
    perm = [
        ["Permanente", "Cobertura (telha + tercas + acessorios)", _n(car.get("G"), 2, " kN/m2"),
         "NBR 8800", "tercas -> portico"],
        ["Permanente", "Peso proprio da estrutura", _n(car.get("self"), 2, " kN/m2"),
         "perfis adotados", "portico -> base"],
        ["Permanente", "Fechamento (%s)" % fec.get("tipo", "-"), _n(fec.get("peso"), 2, " kN/m2"),
         "parede", "coluna / baldrame"],
        ["Variavel", "Sobrecarga de cobertura Q", _n(car.get("Q"), 2, " kN/m2"),
         "NBR 8800 (manutencao)", "tercas -> portico"],
    ]
    if (spec.get("neve") or {}).get("sk"):
        perm.append(["Variavel", "Neve", _n(spec["neve"]["sk"], 2, " kN/m2"),
                     "EN 1991-1-3", "tercas -> portico"])
    flow += [Paragraph("Acoes verticais", ss["H2"]),
             _tab(perm, [58, 190, 78, 88, 96], ss,
                  header=["Tipo", "Acao", "Valor", "Norma/Origem", "Destino"]),
             Spacer(1, 3 * mm)]
    # --- Vento (recomputa Vk, q para explicar) ---
    try:
        import vento_nbr6123 as V
        g = spec.get("geometria", {})
        r = V.compute(v0=ven.get("v0"), cat=ven.get("cat"), classe=ven.get("classe"),
                      s1=ven.get("s1"), s3=ven.get("s3"), z=ven.get("z"),
                      theta=math.degrees(math.atan((g.get("ridge", 0) - g.get("eave", 0)) /
                                                    max(g.get("span", 1) / 2.0, 1e-6))),
                      larg_b=g.get("span", 10), alt_h=g.get("eave", 6),
                      comp_a=g.get("comprimento", 20),
                      abertura_dominante=ven.get("abertura_dominante", "portao_oitao"))
        vrows = [
            ["Velocidade basica V0", _n(r["v0"], 0, " m/s"), "dado de sitio (NBR 6123 Anexo A)"],
            ["Fator S2 (rugosidade/altura)", _n(r["s2"], 3), "Cat. %s, Classe %s, z=%s m"
             % (r["cat"], r["classe"], _n(r["z"], 1))],
            ["Velocidade caract. Vk = V0.S1.S2.S3", _n(r["vk"], 2, " m/s"), "S1=%s ; S3=%s"
             % (_n(r["s1"], 2), _n(r["s3"], 2))],
            ["Pressao dinamica q = 0,613.Vk2", _n(r["q_kN_m2"], 3, " kN/m2"), "base do vento"],
        ]
        # pior sobrepressao e pior succao liquidas no telhado (Cpe-Cpi)
        cob_vals = [v for c in r["net"] for s, v in r["net"][c].items() if s.startswith("cobertura")]
        if cob_vals:
            vrows.append(["Sucao liquida max no telhado (Cpe-Cpi).q",
                          _n(min(cob_vals) * r["q_kN_m2"], 3, " kN/m2"),
                          "arranque (uplift) - governa terca/telha/fundacao"])
        flow += [Paragraph("Vento (NBR 6123) &mdash; passo a passo", ss["H2"]),
                 _tab(vrows, [200, 90, 220], ss, header=["Grandeza", "Valor", "Observacao"]),
                 Spacer(1, 3 * mm)]
    except Exception:
        pass
    # --- Combinacoes ---
    flow += [Paragraph("Combinacoes de acoes", ss["H2"]),
             Paragraph("<b>ELU</b> (estados-limite ultimos, resistencia): as acoes sao "
                       "majoradas &mdash; permanente x1,25 (desfavoravel) ou x1,00 (favoravel, "
                       "quando o vento alivia), sobrecarga x1,50 e vento x1,40. O envelope "
                       "toma a pior combinacao por elemento. <b>ELS</b> (servico, "
                       "deslocamentos): acoes caracteristicas (sem majorar), limitando o "
                       "drift lateral a H/300 e a flecha vertical da cobertura.", ss["Intro"]),
             Spacer(1, 4 * mm)]
    return flow


def _quadro_flow(preamb, ss):
    """Converte o QUADRO DE VERIFICACOES (texto do memorial) numa tabela colorida
    (verde=OK, vermelho=NAO ATENDE)."""
    linhas = [l for l in preamb.splitlines()
              if l.strip() and ("OK" in l or "NAO ATENDE" in l) and "util" not in l.lower()]
    if not linhas:
        return []
    rows, flags = [], []
    for l in linhas:
        ok = "OK" in l and "NAO" not in l
        txt = l.replace("*** NAO ATENDE ***", "").replace("NAO ATENDE", "").replace("OK", "")
        m = re.search(r"(.+?)\s+([0-9]+[.,][0-9]+)\s*$", txt.strip())
        if m:
            nome, u = m.group(1).strip(), m.group(2)
        else:
            nome, u = txt.strip(), "-"
        rows.append([nome, _vg(u), "ATENDE" if ok else "NAO ATENDE"])
        flags.append(ok)
    tb = _tab(rows, [220, 70, 110], ss, header=["Elemento", "Utilizacao", "Situacao"])
    st = list(tb.getStyle()._cmds) if hasattr(tb, "getStyle") else []
    # colore a coluna 'Situacao' por linha
    extra = []
    for i, ok in enumerate(flags):
        r = i + 1  # +1 pelo cabecalho
        extra.append(("TEXTCOLOR", (2, r), (2, r),
                      colors.HexColor("#1a7a3a") if ok else colors.HexColor("#b3261e")))
        extra.append(("FONTNAME", (2, r), (2, r), "Helvetica-Bold"))
    tb.setStyle(TableStyle(extra))
    return [Paragraph("Quadro de verificacoes", ss["Secao"]),
            Paragraph("Utilizacao = solicitacao / resistencia. Um elemento ATENDE quando "
                      "util &le; 1,0. Este quadro e a sintese; o memorial de cada modulo "
                      "detalha o calculo que produziu cada numero.", ss["Intro"]),
            tb, Spacer(1, 5 * mm)]


def _resultado_modulo(corpo):
    """Extrai um destaque de RESULTADO do corpo do memorial de um modulo (a ultima
    utilizacao/veredito que aparecer), para o cabecalho didatico da secao."""
    m = re.findall(r"(u(?:tilizacao|_max|til)?|interacao)\s*[=:]?\s*([0-9]+[.,][0-9]+)",
                   corpo, flags=re.IGNORECASE)
    veredito = None
    if re.search(r"NAO ATENDE|REPROVA|NAO PASSA", corpo):
        veredito = "requer atencao"
    elif re.search(r"\bOK\b|ATENDE|PASSA|APROVAD", corpo):
        veredito = "atende"
    if m:
        return "utilizacao ~ %s%s" % (_vg(m[-1][1]), " (%s)" % veredito if veredito else "")
    return veredito or ""


def gerar_pdf(out_dir, pdf_path=None, titulo="GALPAO EM ACO", spec=None):
    """Le out_dir/MEMORIAL-CONSOLIDADO.txt e escreve um PDF DIDATICO: capa, premissas,
    levantamento de cargas, quadro de verificacoes e, por modulo, METODO + memorial.
    Se `spec` for dado, inclui as secoes de premissas e cargas. Retorna o path."""
    cons = os.path.join(out_dir, "MEMORIAL-CONSOLIDADO.txt")
    if not os.path.exists(cons):
        raise FileNotFoundError("MEMORIAL-CONSOLIDADO.txt nao encontrado em %s "
                                "(rode o calculo antes)" % out_dir)
    texto = open(cons, encoding="utf-8").read()
    preamb, secoes = _parse_consolidado(texto)
    # descarta modulos que nao rodam neste projeto (corpo vazio ou "(falta)"):
    # ex. estaca/fogo/escada/plataforma so aparecem se o projeto os pede.
    secoes = [(t, c) for t, c in secoes
              if c.strip() and c.strip().lower() != "(falta)"]
    if pdf_path is None:
        pdf_path = os.path.join(out_dir, "MEMORIAL-DE-CALCULO.pdf")

    ss = _estilos()
    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=14 * mm,
                            title="Memorial de Calculo - %s" % titulo,
                            author="framework galpao_fw")
    doc._titulo_curto = titulo[:60]
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    fluxo = []

    # ---- CAPA ----
    fluxo += [Spacer(1, 45 * mm),
              Paragraph("MEMORIAL DE CALCULO", ss["Capa"]),
              Spacer(1, 6 * mm),
              Paragraph(titulo, ss["SubCapa"]),
              Spacer(1, 3 * mm),
              Paragraph("Projeto executivo estrutural &mdash; galpao em aco",
                        ss["SubCapa"]),
              Spacer(1, 20 * mm),
              Paragraph("Emitido em %s" % hoje, ss["SubCapa"]),
              Spacer(1, 60 * mm),
              Paragraph("DOCUMENTO CONCEITUAL &mdash; PENDENTE DE REVISAO E ART "
                        "DO ENGENHEIRO RESPONSAVEL. Cada modulo traz o METODO "
                        "(norma e procedimento) seguido do calculo para "
                        "conferencia.", ss["Nota"]),
              PageBreak()]

    # ---- COMO LER ESTE MEMORIAL ----
    fluxo += [Paragraph("Como ler este memorial", ss["Secao"]),
              Paragraph("Este documento e organizado do geral para o detalhe: (1) as "
                        "<b>premissas</b> e os dados de entrada; (2) o <b>levantamento de "
                        "cargas</b>, mostrando de onde vem cada acao e por onde ela desce "
                        "na estrutura; (3) o <b>quadro de verificacoes</b>, a sintese do "
                        "que atende; e (4) o <b>memorial por modulo</b>, cada um com o "
                        "METODO (norma e procedimento, passo a passo) seguido do CALCULO "
                        "com os numeros. A utilizacao (util) e sempre solicitacao dividida "
                        "por resistencia: <b>util &le; 1,0 = ATENDE</b>.", ss["Intro"]),
              Spacer(1, 4 * mm)]

    # ---- PREMISSAS + LEVANTAMENTO DE CARGAS (didaticos; exigem o spec) ----
    if spec:
        try:
            fluxo += _dados_entrada_flow(spec, ss)
            fluxo += _cargas_flow(spec, out_dir, ss)
            fluxo.append(PageBreak())
        except Exception:
            pass

    # ---- QUADRO DE VERIFICACOES (colorido) ----
    q = _quadro_flow(preamb, ss) if preamb else []
    if q:
        fluxo += q
    elif preamb:
        fluxo += [Paragraph("Resumo e quadro de verificacoes", ss["Secao"]),
                  Preformatted(preamb, ss["Mono"]), Spacer(1, 4 * mm)]

    # ---- INDICE ----
    if secoes:
        fluxo += [Paragraph("Indice dos modulos", ss["Secao"])]
        linhas_idx = [[Paragraph(t, ss["Cell"])] for t, _ in secoes]
        tb = Table(linhas_idx, colWidths=[170 * mm])
        tb.setStyle(TableStyle([
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#12395b")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ]))
        fluxo += [tb, PageBreak()]

    # ---- SECOES: METODO + MEMORIAL ----
    for titulo_sec, corpo in secoes:
        res_hl = _resultado_modulo(corpo or "")
        cab = [Paragraph(titulo_sec, ss["Secao"])]
        if res_hl:
            cab.append(Paragraph("Resultado: %s" % res_hl, ss["Nota"]))
        cab += [Paragraph("METODO (norma e procedimento)", ss["MetodoTit"]),
                Paragraph(_metodo_para(titulo_sec), ss["Metodo"]),
                Spacer(1, 2 * mm),
                Paragraph("CALCULO (memorial &mdash; numeros do dimensionamento)",
                          ss["MetodoTit"])]
        # KeepTogether so no cabecalho+metodo; corpo pode quebrar de pagina
        fluxo.append(KeepTogether(cab))
        fluxo.append(Preformatted(corpo or "(sem conteudo)", ss["Mono"]))
        fluxo.append(Spacer(1, 5 * mm))

    doc.build(fluxo, onFirstPage=_cabecalho_rodape,
              onLaterPages=_cabecalho_rodape)
    return pdf_path


def gerar_de_spec(spec, out_dir, pdf_path=None, titulo=None):
    """Roda o calculo (gera memoriais em out_dir) e depois o PDF."""
    import rodar_projeto as RP
    os.makedirs(out_dir, exist_ok=True)
    RP.calcular(spec, out_dir)
    g = spec.get("geometria", {})
    if titulo is None:
        titulo = "GALPAO %sx%s m" % (g.get("comprimento", "?"), g.get("span", "?"))
    return gerar_pdf(out_dir, pdf_path, titulo=titulo, spec=spec)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) >= 2 and os.path.isdir(sys.argv[1]):
        out = sys.argv[1]
        pdf = sys.argv[2] if len(sys.argv) >= 3 else None
        p = gerar_pdf(out, pdf)
        print("PDF gerado:", p)
    else:
        # demo: roda um caso e gera o PDF
        import tempfile
        import smoke_executivo as SM
        s = SM._spec("demo", span=15, comp=20, eave=7, ridge=7.75, ponte=SM.PONTE)
        out = tempfile.mkdtemp(prefix="memorial_")
        p = gerar_de_spec(s, out)
        print("PDF gerado:", p)
