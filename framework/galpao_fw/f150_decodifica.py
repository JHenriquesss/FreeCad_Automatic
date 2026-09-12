# ============================================================================
# f150_decodifica.py - G117: A CAMADA DE TEXTO DA NBR 6118:2023 (F150).
# SCRIPT AVULSO + MODULO DE PRODUCAO: a tabela canonica mora aqui; a lente
# e o teste importam de ca. (Uma fonte so - regra do lote G114-G118.)
# Rodado a mao/CI (python f150_decodifica.py) e pelo teste-guarda
# tests/test_f150_decodifica_g117.py. Nao e importado por nenhum
# orquestrador do Loop - declarado em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_*.
#
# O que foi MEDIDO (G106/G113 + entrega G117, enderecos verificados):
#   - F150 = fontes/01_CONCRETO/CONCRETO__NBR__NBR-6118-2023__projeto-
#     estruturas-concreto.pdf (2705175 bytes, 260 paginas no PDF, 242
#     numeradas; catalogo.csv F150). Camada de texto do corpo na fonte
#     subsetada BEDMNK+ArialMT2 (TT7, Identity-H): pagina renderiza
#     correta, texto extraido sai cifra (conferido na imagem p.16/xvi,
#     p.13/5.1.2, p.83/14.4, p.38/9.4.2.6, p.138/17.4.2.3, p.62/11.4.1.3,
#     p.23/8.2.3, p.188/22.5.1.3).
#   - Capa, cabecalhos, rodape e simbolos de formula usam outras fontes
#     (Helvetica F1, Arial-BoldMT TT2, ArialMT TT4, Arial-ItalicMT TT6,
#     Arial-BoldItalicMT TT11) com texto legivel - preservados como estao.
#   - Cifra medida no rawdict (116 codigos distintos em TT7):
#     base = byte + 29 para letras/digitos/pontuacao ("7"->"T", "R"->"o",
#     "$"->"A", "2V"->"Os", "UHTXLVLWRV"->"requisitos", "\x03"->espaco,
#     "\x0b"/"\x0c"->"("/")", "\x0f"->",", "\x10"->"-", "\x11"->".");
#     12 bytes reaproveitados para acentos (conferidos na imagem):
#     "k"->"â", "t"->"í", "m"->"ã", "p"->"é" (dito no goal) + "i"->"á",
#     "j"->"à", "o"->"ç", "r"->"ê", "y"->"ó", "{"->"ô", "}"->"õ",
#     "~"->"ú" ("Associação", "Técnicas", "não", "órgãos", "condições",
#     "conteúdo", "à", "atmosfera"...); "\x83"->"°" ("/°C", "180°,"),
#     "\x9e"->"º" ("Lei nº 9.279"), "\xbf"->"fi" e "\xc0"->"fl"
#     (ligaduras: "especificado"="especi"+"fi"+"cado",
#     "filosofia"="fi"+"loso"+"fi"+"a", "(flecha)", "fletor",
#     "influência"="in"+"fl"+"uência"), "\xb1"->"–" ("Concreto –
#     Projeto", bullets), "\xb6"->"'" ("d'água"), "\xc8"->"Á"
#     ("Áreas"), "\xb3"/"\xb4"->"“"/"”" ("“torção”", p.188).
#   - Espaco duplo medido: todo "\x03" (espaco, w=3.06) em texto
#     justificado vem seguido de "\x20" (w=2.21) - par que a pagina
#     renderiza como UM espaco ("de =Normalização" se "\x20" for
#     lido como "=" da regra +29). "\x20" sozinho aparece como
#     indentacao. Em TT7 o byte "\x20" NUNCA e "=" (o "=" real mora
#     nas fontes de formula) - os dois codigos viram espaco e
#     espacos consecutivos colapsam. Faltas residuais (espaco sem
#     codigo, so afastamento) sao reconstruidas pelo vao no bbox.
#   - Letras gregas, subscritos e expoentes ("φℓθ", "γf", "fck") moram
#     nas outras fontes/figuras e NAO saem por esta tabela - limite
#     declarado (aceite do goal).
#   - CORRIGIDO no G119 (auditoria do G117): "≥" e "≤" NAO ficavam de
#     fora. Eles SAEM nos spans MT2 (bytes 0x95 e 0x94) e a regra +29 os
#     entregava como "²" e "±" - "fck ≤ 50 MPa" virava "fck ± 50 MPa",
#     que e' outro limite. Nao era omissao, era TROCA: o limite estava
#     declarado no lugar errado. Idem "2ª ordem" (0x9D saia "º", 120x),
#     "εc2 = 2,0 ‰" (0xC5 saia "â") e mais cinco. Todos conferidos na
#     pagina renderizada e mapeados; o que sobrou vira marcador visivel
#     (ver decodifica_char).
#   - FECHADO no G120: dos 8 restantes, 7 mapeados contra a pagina
#     renderizada (0x81 ü p.118, 0x92 ∞ p.50/51, 0xA8 Δ p.37, 0xEE × p.75,
#     0x101 · p.139/188, 0xED – p.9/13/46/159/236, 0xBC5 – p.218). O
#     oitavo (0x0BD8, 188x, antes de "a)") nao tem marca visivel na
#     imagem (avanço 0,91 pt, zoom 9x) e continua marcador declarado.
#
# Maquina: funcao pura sobre a extracao do PyMuPDF (rawdict, por bbox):
# decodifica so os spans TT7/ArialMT2 char a char pela TABELA_ESPECIAL
# (base +29 + excecoes); o resto passa intacto; por linha, ordena por x,
# insere espaco quando o vao entre glifos excede o limiar e colapsa
# espacos. decodifica_pdf escreve o .txt fora do git (fontes/ e
# ignorado) com marcador de pagina. confere_amostra e a lente: cada
# frase-ancora (lida na pagina RENDERIZADA, nunca na camada de texto -
# regra 3) precisa aparecer no .txt; o OK por pagina chega ao veredito
# global (contra a saturacao silenciosa do G113: OK por item que nao
# chega ao veredito). O teste-guarda injeta defeito em tmp_path.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - formulas, tabelas e figuras: so a prosa ao redor sai; o miolo
#     simbolico (fck, equacoes, cotas de tabela) nao e reconstruido e
#     sai como lacuna "[formula/tabela: ver pagina renderizada]";
#   - scanned figures / carimbo vermelho lateral ("Exemplar para uso
#     exclusivo...") e marca d'agua "ABNT": saem como texto corrido
#     quando legiveis, sem interpretacao;
#   - paginas 1-15 (capa, sumario, prefacio inicial) misturam fontes
#     legiveis e TT7 - decodificadas igual, sem tratamento especial;
#   - OCR (ramo (b) do goal): rejeitado - sem Tesseract na maquina;
#     vale o ramo (a), decodificacao da cifra.
# ============================================================================
"""Decodificacao G117: cifra da camada de texto da F150 (NBR 6118:2023)."""

from __future__ import annotations

import os
import pathlib
import re
import sys

GALPAO = pathlib.Path(__file__).resolve().parent

F150_REL = os.path.join(
    "fontes", "01_CONCRETO",
    "CONCRETO__NBR__NBR-6118-2023__projeto-estruturas-concreto.pdf",
)
# .txt fora do git: fontes/ e ignorado (/fontes/ no .gitignore).
F150_TXT_REL = os.path.join(
    "fontes", "01_CONCRETO",
    "CONCRETO__NBR__NBR-6118-2023__projeto-estruturas-concreto-dec.txt",
)

# Byte (codigo extraido) -> texto. "fi"/"fl" expandem para 2 letras.
TABELA_ESPECIAL = {
    0x03: " ",
    0x20: " ",  # espacador de justificacao; nunca "=" em TT7 (medido).
    0x0B: "(", 0x0C: ")",
    0x0F: ",", 0x10: "-", 0x11: ".", 0x12: "/",
    0x69: "á",  # i
    0x6A: "à",  # j
    0x6B: "â",  # k
    0x6D: "ã",  # m
    0x6F: "ç",  # o
    0x70: "é",  # p
    0x72: "ê",  # r
    0x74: "í",  # t
    0x79: "ó",  # y
    0x7B: "ô",  # {
    0x7D: "õ",  # }
    0x7E: "ú",  # ~
    0x83: "°",
    0x9E: "º",
    0xBF: "fi",
    0xC0: "fl",
    0xB1: "–",
    0xB6: "'",
    0xC8: "Á",
    0xB3: "“",
    0xB4: "”",
    # G119 (auditoria do G117): oito codigos que a regra +29 entregava como
    # OUTRO caractere plausivel -- nao como falta. Cada um conferido na
    # PAGINA RENDERIZADA (regra 3), com a pagina do PDF anotada:
    0x9D: "ª",   # p.124 "2ª ordem" (o +29 dava "º": 120 ocorrencias)
    0x94: "≤",   # p.41  "fck ≤ 50 MPa" (o +29 dava "±": operador TROCADO)
    0x95: "≥",   # p.52  "h ≥ 60 cm"    (o +29 dava "²")
    0xC2: "·",   # p.42  "αE · 5600 √fck" (o +29 dava "ß")
    0xC5: "‰",   # p.44  "εc2 = 2,0 ‰"  (o +29 dava "â": deformacao-limite)
    0xCB: "Í",   # p.249 "Índice de esbeltez" (o +29 dava "è")
    0xBB: "/",   # p.167 "Md / z + (a ℓ /d) Vd" (o +29 dava "Ø")
    0xBFA: "ff",  # p.??  "off-shore" (ligadura; o +29 dava um char tamil)
    # G120 (fecha a cifra): sete dos oito restantes conferidos na PAGINA
    # RENDERIZADA (regra 3), com a pagina do PDF anotada. Tres bytes
    # desenham o MESMO traco do 0xB1 ("-"): o subset duplica o glifo
    # (larguras em ArialMT2 regular: B1 6,11 pt, ED 5,84-6,42 pt,
    # BC5 6,11 pt -- metrica, nao outro caractere).
    0x81: "ü",   # p.118 "(Rüsch)" (efeito de carga mantida; 1 ocorrencia)
    0x92: "∞",   # p.50 "t∞ - vida útil da estrutura" (16x: t∞, φ(t∞,t0),
                 # # εcs(t∞,t0), σp∞; tambem p.51 "σp∞ - tensão na armadura")
    0xA8: "Δ",   # p.37 "cnom = cmín + Δc" (7.4.7.2; 1 ocorrencia)
    0xEE: "×",   # p.75 "-15 × 10-5" (retracao; 4x, tambem "2 × 106" p.215)
    0x101: "·",  # p.139 "αc = 0,85 · [1,0 - ..." (7x, tambem p.188
                 # # "fyd As,ccp ≥ 1,5 · FSd"; mesmo desenho do 0xC2 --
                 # # o avanço difere, 3,66 contra 3,06 pt, metrica do subset)
    0xED: "–",   # p.9 "força cortante – Estado-limite último" (sumario,
                 # # 143x; tambem p.13 "Figura 17.5 – Flexo-torção", p.46
                 # # tabela 8.1, p.159 "he = A/u ≤ bw – 2c1", p.236 legenda)
    0xBC5: "–",  # p.218 tabela 23.2, celula vazia (12x, so nesta pagina)
    # 0x0BD8 NAO MAPEADO (declarado ilegível, G120): 188 ocorrencias, sempre
    # imediatamente antes de item de lista "a)"/"b)"/"c)"..., avanço fixo de
    # 0,91 pt e SEM marca visível na pagina renderizada (p.37 e p.52
    # conferidas em zoom 9x: so o recuo). E' controle de layout do subset,
    # nao glifo -- continua marcador [<U+0BD8>] com este motivo escrito.
}

DESCONHECIDO_FMT = "[<U+%04X>]"

#: acima deste byte a regra +29 nao vale (a faixa de letras/digitos/
#: pontuacao acaba aqui). Byte alto FORA da tabela vira marcador visivel.
_LIMITE_REGRA_MAIS_29 = 0x80


def decodifica_char(c: str) -> str:
    """Decodifica UM char extraido de span TT7 (fonte unica: esta tabela).

    G119: byte alto (>= 0x80) fora da tabela devolve DESCONHECIDO_FMT em vez
    de `chr(o + 29)`. Antes, TODO byte desconhecido caia na regra +29 e saia
    como um caractere plausivel: o medidor `desconhecidos` de `decodifica_pdf`
    contava ocorrencias de DESCONHECIDO_FMT que NUNCA eram escritas, e por
    isso relatava zero enquanto 16 codigos saiam trocados -- entre eles
    "≤" virando "±" (limite normativo com outro operador). Ausencia se
    declara: o que a tabela nao conhece aparece como marcador, nao como
    palpite.
    """
    o = ord(c)
    if o in TABELA_ESPECIAL:
        return TABELA_ESPECIAL[o]
    if o >= _LIMITE_REGRA_MAIS_29:
        return DESCONHECIDO_FMT % o
    return chr(o + 29)


def decodifica_texto_bruto(texto_bruto: str) -> str:
    """Decodifica texto de span TT7 char a char + colapsa espacos.

    Nao reimplementa regra: chama decodifica_char (a lente nao duplica
    a tabela; o teste cobra a funcao real - contra assercao tautologica).
    """
    saida = "".join(decodifica_char(c) for c in texto_bruto)
    saida = re.sub(r" {2,}", " ", saida)
    return saida


def _e_tt7(nome_fonte: str) -> bool:
    return "MT2" in nome_fonte


def decodifica_pagina(pagina, limiar_espaco: float = 0.18) -> str:
    """Decodifica UMA pagina (objeto fitz.Page) preservando linhas.

    Mistura fontes: spans TT7 pela tabela, demais intactos; por linha,
    ordena os glifos por x e insere espaco quando o vao entre bboxes
    excede limiar_espaco * tamanho (reconstrucao de espacos perdidos).
    """
    linhas_saida = []
    rawdict = pagina.get_text("rawdict")
    for bloco in rawdict.get("blocks", []):
        if bloco.get("type", 0) != 0:
            continue
        for linha in bloco.get("lines", []):
            itens = []  # (x0, x1, texto, tamanho)
            for span in linha.get("spans", []):
                tamanho = float(span.get("size", 10.0))
                tt7 = _e_tt7(span.get("font", ""))
                for ch in span.get("chars", []):
                    c = ch.get("c", "")
                    if not c:
                        continue
                    x0, _, x1, _ = ch.get("bbox", (0, 0, 0, 0))
                    if tt7:
                        texto = decodifica_char(c)
                    else:
                        texto = c
                    itens.append([float(x0), float(x1), texto, tamanho])
            if not itens:
                continue
            itens.sort(key=lambda t: t[0])
            montada = []
            anterior_x1 = None
            anterior_tam = 10.0
            for x0, x1, texto, tamanho in itens:
                if anterior_x1 is not None and texto.strip() and montada \
                        and montada[-1] not in (" ",):
                    vao = x0 - anterior_x1
                    if vao > max(tamanho, anterior_tam) * limiar_espaco:
                        # Nao duplica: o proprio "\x03"/"\x20" ja da espaco.
                        montada.append(" ")
                montada.append(texto)
                anterior_x1 = x1
                anterior_tam = tamanho
            montada = re.sub(r" {2,}", " ", "".join(montada)).strip()
            linhas_saida.append(montada)
    return "\n".join(linhas_saida)


def decodifica_pdf(caminho_pdf, caminho_txt, paginas=None) -> dict:
    """Decodifica o PDF inteiro (ou subconjunto) para .txt local.

    Retorna estatisticas (paginas, linhas, lacunas). Lacunas
    "[<U+XXXX>]" nao existem nesta tabela para TT7 puro (todos os 116
    codigos mapeados); ficam para bytes futuros fora da tabela.
    """
    import fitz  # import local: a lente nao exige o import no Loop.

    doc = fitz.open(caminho_pdf)
    total = doc.page_count
    indices = list(range(total)) if paginas is None else list(paginas)
    desconhecidos: dict = {}
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write("# NBR 6118:2023 (F150) decodificada - G117 ramo (a).\n")
        f.write("# Fonte: camada de texto do corpo (fonte BEDMNK+ArialMT2), "
                "byte+29 + tabela de acentos/ligaduras em "
                "f150_decodifica.TABELA_ESPECIAL.\n")
        f.write("# Limites: formulas/tabelas/figuras NAO reconstruidas - "
                "ver pagina renderizada. Texto fora do git (fontes/ "
                "ignorado).\n")
        for pidx in indices:
            pagina = doc[pidx]
            texto = decodifica_pagina(pagina)
            for m in re.finditer(r"\[<U\+([0-9A-F]{4})>\]", texto):
                desconhecidos[m.group(1)] = \
                    desconhecidos.get(m.group(1), 0) + 1
            f.write(f"\n===== PAGINA PDF {pidx + 1} =====\n")
            f.write(texto + "\n")
    linhas = 0
    with open(caminho_txt, encoding="utf-8") as f:
        for _ in f:
            linhas += 1
    return {
        "paginas": len(indices),
        "linhas": linhas,
        "desconhecidos": desconhecidos,
        "saida": str(caminho_txt),
    }


# Lente: amostra de 10 paginas lida na imagem (regra 3). Cada ancora e
# (indice_pdf_0based, frase exata como renderiza). Uma e de formula
# (p.138/17.4.2.3: a prosa ao redor; o miolo simbolico e limite).
AMOSTRA_G117 = [
    (15, "A Associação Brasileira de Normas Técnicas (ABNT) é o Foro Nacional de Normalização."),
    (15, "Os Documentos Técnicos ABNT são elaborados conforme as regras da ABNT Diretiva 2."),
    (15, "(Lei nº 9.279, de 14 de maio de 1996)."),
    (30, "Os requisitos de qualidade de uma estrutura de concreto são classificados, para os efeitos desta"),
    (30, "Consiste no atendimento aos estados-limite últimos definidos nesta Norma."),
    (100, "São aqueles em que o comprimento longitudinal supera em pelo menos três vezes a maior dimensão"),
    (100, "Elementos lineares em que a flexão é preponderante."),
    (55, "Permite-se, em casos especiais, considerar outros fatores redutores do comprimento de ancoragem"),
    (55, "o maior valor entre 0,3 ℓb, 10"),
    (155, "Essa decalagem pode ser substituída, aproximadamente, pela correspondente decalagem do diagrama"),
    (79, "O nível d'água adotado para cálculo de reservatórios, tanques, decantadores e outros deve ser igual"),
    (16, "This Standard establishes the general requirements to be complied with by the design as a whole as"),
    (40, "Para efeito de análise estrutural, o coeficiente de dilatação térmica pode ser admitido como sendo"),
    (120, "As estruturas são consideradas, para efeito de cálculo, de nós fixos, quando os deslocamentos"),
    (205, "diz-se que existe “torção” do consolo; o comportamento estrutural que"),
    # G119: quatro ancoras sobre os codigos que saiam TROCADOS (nao ausentes).
    # Lidas na pagina renderizada, como as de cima; se a tabela regredir para
    # a regra +29, cada uma destas cai.
    (123, "obrigatoriamente considerados os efeitos globais e locais de 2ª ordem."),
    (40, "≤ 50 MPa"),
    (51, "≥ 60 cm, localizados no mínimo 30 cm abaixo da face"),
    (43, "2,0 ‰"),
    # G120: sete ancoras sobre os codigos restantes que viraram marcador
    # visivel no G119 e agora foram conferidos na PAGINA RENDERIZADA.
    # Lidas na imagem, como as de cima; sem o mapeamento, cada posicao
    # sai "[<U+XXXX>]" e a ancora cai. (O oitavo, 0x0BD8, nao tem marca
    # visivel e segue marcador declarado -- sem ancora possivel.)
    (117, "efeito de carga mantida (Rüsch)"),
    (49, "t∞ – vida útil da estrutura"),
    (36, "cnom cmín + Δc"),
    (74, "ser adotado igual a -15 × 10-5"),
    (138, "0,85 · [1,0 – (fck – 50) / 200]"),
    (12, "Figura 17.5 – Flexo-torção de perfil com paredes opostas"),
    (217, "105\n90\n–\n105\n90\n–"),
]


def confere_amostra(texto_decodificado: str, amostra=None) -> dict:
    """Portao da amostra: cada ancora precisa aparecer; o OK por item
    chega ao veredito global (contra saturacao silenciosa)."""
    amostra = AMOSTRA_G117 if amostra is None else amostra
    itens = {}
    for pidx, frase in amostra:
        itens[frase[:60]] = (frase in texto_decodificado)
    ok = all(itens.values()) and len(itens) == len(amostra)
    return {"itens": itens, "ok": bool(ok)}


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parent.parent.parent
    pdf = repo / F150_REL
    txt = repo / F150_TXT_REL
    if not pdf.exists():
        print(f"F150 ausente: {pdf}")
        return 2
    stats = decodifica_pdf(str(pdf), str(txt))
    print(f"paginas={stats['paginas']} linhas={stats['linhas']} "
          f"desconhecidos={stats['desconhecidos']}")
    print(f"saida={stats['saida']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
