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
    ss.add(ParagraphStyle("Mono", parent=ss["Code"], fontSize=6.7, leading=7.8,
                          fontName="Courier"))
    ss.add(ParagraphStyle("Nota", parent=ss["Normal"], fontSize=8,
                          leading=10, textColor=colors.grey))
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


def gerar_pdf(out_dir, pdf_path=None, titulo="GALPAO EM ACO"):
    """Le out_dir/MEMORIAL-CONSOLIDADO.txt e escreve um PDF com METODO+memorial
    por modulo. Retorna o caminho do PDF."""
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

    # ---- PREAMBULO / QUADRO DE VERIFICACOES ----
    if preamb:
        fluxo += [Paragraph("Resumo e quadro de verificacoes", ss["Secao"]),
                  Preformatted(preamb, ss["Mono"]),
                  Spacer(1, 4 * mm)]

    # ---- INDICE ----
    if secoes:
        fluxo += [Paragraph("Indice dos modulos", ss["Secao"])]
        linhas_idx = [[t] for t, _ in secoes]
        tb = Table(linhas_idx, colWidths=[170 * mm])
        tb.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#12395b")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ]))
        fluxo += [tb, PageBreak()]

    # ---- SECOES: METODO + MEMORIAL ----
    for titulo_sec, corpo in secoes:
        bloco = [Paragraph(titulo_sec, ss["Secao"]),
                 Paragraph("METODO", ss["MetodoTit"]),
                 Paragraph(_metodo_para(titulo_sec), ss["Metodo"]),
                 Spacer(1, 2 * mm),
                 Paragraph("CALCULO (memorial)", ss["MetodoTit"])]
        # KeepTogether so no cabecalho+metodo; corpo pode quebrar de pagina
        fluxo.append(KeepTogether(bloco))
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
    return gerar_pdf(out_dir, pdf_path, titulo=titulo)


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
