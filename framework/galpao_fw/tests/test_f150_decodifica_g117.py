"""G117 - a camada de texto da NBR 6118:2023 (F150) decodificada.

Medido (G106/G113 + entrega G117): o corpo da F150
(fontes/01_CONCRETO/CONCRETO__NBR__NBR-6118-2023__projeto-estruturas-
concreto.pdf, 260 pags, catalogo.csv F150) usa a fonte subsetada
BEDMNK+ArialMT2 (+ BoldMT2/ItalicMT2, "MT2") com cifra: byte+29 para
letras/digitos/pontuacao ("7"->"T", "R"->"o", "2V"->"Os") e 12 bytes
reaproveitados para acentos ("k"->"â", "t"->"í", "m"->"ã", "p"->"é",
"i"->"á", "j"->"à", "o"->"ç", "r"->"ê", "y"->"ó", "{"->"ô", "}"->"õ",
"~"->"ú") + "°/º/fi/fl/–/'/Á/“/”" e o par de espaco "\\x03\\x20"
(medido no rawdict; pagina renderiza correta - conferido na imagem).
Sem Tesseract na maquina: vale o ramo (a), decodificacao.

Entregue:
  1. LENTE (f150_decodifica.py, fonte unica): tabela canonica
     TABELA_ESPECIAL + decodifica_char/texto_bruto/pagina/pdf +
     confere_amostra (cada ancora precisa aparecer; o OK por item
     chega ao veredito global - contra a saturacao silenciosa).
  2. PORTAO (test_01): a lente sobre 10 paginas vivas da F150 com as
     ancoras lidas na pagina RENDERIZADA (regra 3), incluindo duas de
     formula (9.4.2.6 e 17.4.2.3: a prosa ao redor; o miolo simbolico
     e limite declarado). Um assert so.
  3. BASELINE (test_02, nos dois sentidos): fixtures cifra->plano
     congeladas + tamanho da amostra congelado - cura muda o baseline
     junto; gap novo = vermelho.
  4. INJECAO (test_03, tmp_path, nunca mutando o repo): ancora
     corrompida e cifra trocada deixam a suite vermelha; o caso bom
     fica verde. A lente nao reimplementa a tabela (chama a funcao
     real - contra assercao tautologica).

O que a lente NAO cobre: formulas/tabelas/figuras (so a prosa ao
redor sai); simbolos gregos/subscritos (o "phi" extrai como "I" da
fonte SymbolMT - declarado, nao adivinhado); carimbo vermelho
lateral e marca d'agua (texto corrido, sem interpretacao).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import f150_decodifica as lente

REPO = os.path.dirname(os.path.dirname(GALPAO))
F150 = os.path.join(
    REPO, "fontes", "01_CONCRETO",
    "CONCRETO__NBR__NBR-6118-2023__projeto-estruturas-concreto.pdf",
)

# Baseline nos dois sentidos: fixtures cifra->plano (a tabela real e
# chamada, nunca copiada para o teste - fonte unica).
BASELINE_FIXTURES = [
    ("7RGRV", "Todos"),
    ("2V", "Os"),
    ("UHTXLVLWRV", "requisitos"),
    ("$VVRFLDomR", "Associação"),
    ("7pFQLFDV", "Técnicas"),
    ("QmR", "não"),
    ("yUJmRV", "órgãos"),
    ("FRQGLo}HV", "condições"),
    ("FRQWH~GR", "conteúdo"),
    ("jV", "às"),
    ("LQVWkQFLD", "instância"),
    ("DUTXLWHW{QLFDV", "arquitetônicas"),
    ("HVSHFL\xbfFDGR", "especificado"),
    ("\xc0HFKD", "flecha"),
    ("\x83&", "°C"),
    ("Q\x9e", "nº"),
    ("3URMHWR\x03 \x0b$%17", "Projeto (ABNT"),
]


def test_01_portao_amostra_dez_paginas_lidas_na_imagem():
    """Um assert so: as 19 ancoras (13 paginas, 2 de formula) estao no
    texto decodificado das paginas vivas (regra 3: render, nunca texto)."""
    if not os.path.exists(F150):
        pytest.skip("F150 ausente no checkout (fontes/ e ignorado) - "
                    "portao vivo so roda com o PDF; o resto da suite usa "
                    "fixtures em tmp_path")
    fitz = pytest.importorskip("fitz")
    doc = fitz.open(F150)
    paginas = sorted(set(p for p, _ in lente.AMOSTRA_G117))
    assert len(paginas) >= 10, \
        "amostra caiu para %d paginas - o aceite pede 10" % len(paginas)
    texto = "\n".join(lente.decodifica_pagina(doc[p]) for p in paginas)
    veredito = lente.confere_amostra(texto)
    faltando = [k for k, v in veredito["itens"].items() if not v]
    assert veredito["ok"], "ancoras ausentes no decodificado: %r" % faltando


def test_02_baseline_cifra_nos_dois_sentidos():
    """Baseline congelado: cada fixture decodifica no exato plano; a
    amostra tem 26 ancoras em 20 paginas. Cura muda o baseline junto.

    G119: eram 15 em 10 paginas. As quatro novas cobrem os codigos que
    saiam TROCADOS (2ª ordem, "≤ 50 MPa", "≥ 60 cm", "2,0 ‰") - nenhuma
    das 15 originais tinha ordinal feminino nem operador, e foi por isso
    que a troca passou pela amostra. Triagem escrita, nao numero novo.

    G120: 19 em 13 paginas. As sete novas cobrem os codigos que o G119
    deixou como marcador visivel e agora foram conferidos na pagina
    renderizada (Rüsch, t∞, Δc, ×, ·, – de titulo, – de tabela). O oitavo
    (0x0BD8, antes de "a)") nao tem marca visivel na imagem e segue
    marcador declarado - sem ancora possivel, com teste proprio
    (test_06). Triagem escrita, nao numero novo.
    """
    quebras = ["%r -> %r (esperado %r)" % (cifra, lente.decodifica_texto_bruto(cifra), plano)
               for cifra, plano in BASELINE_FIXTURES
               if lente.decodifica_texto_bruto(cifra) != plano]
    paginas = set(p for p, _ in lente.AMOSTRA_G117)
    if len(lente.AMOSTRA_G117) != 26:
        quebras.append("amostra mudou de tamanho sem triagem: %d"
                       % len(lente.AMOSTRA_G117))
    if len(paginas) < 10:
        quebras.append("amostra cobre %d paginas - o aceite pede 10"
                       % len(paginas))
    assert not quebras, "baseline quebrou:\n" + "\n".join(quebras)


def test_03_injecao_vermelho_quando_corrompe_verde_quando_bom(tmp_path):
    """tmp_path, nunca o repo: ancora corrompida e cifra trocada dao
    vermelho; o caso bom da verde. A lente e chamada de verdade."""
    bom = ("A Associação Brasileira de Normas Técnicas (ABNT) é o Foro "
           "Nacional de Normalização. (Lei nº 9.279, de 14 de maio de 1996).")
    assert lente.confere_amostra(
        bom, amostra=[(0, "Associação Brasileira"),
                      (0, "Lei nº 9.279")])["ok"] is True
    corrompido = bom.replace("Associação", "ASSOCIAÇÃO TROCADA")
    assert lente.confere_amostra(
        corrompido, amostra=[(0, "Associação Brasileira"),
                             (0, "Lei nº 9.279")])["ok"] is False
    # Cifra trocada ("7"->"X" em vez de "T"): o plano muda junto.
    assert lente.decodifica_texto_bruto("7RGRV") == "Todos"
    assert lente.decodifica_texto_bruto("XRGRV") != "Todos"
    # O .txt de saida vai para tmp_path, nunca para o repo.
    saida = str(tmp_path / "amostra.txt")
    with open(saida, "w", encoding="utf-8") as f:
        f.write(bom + "\n")
    with open(saida, encoding="utf-8") as f:
        assert "Associação Brasileira" in f.read()


# ---------------------------------------------------------------- G119
# Auditoria do G117: a regra base+29 nao tinha fundo. Byte fora da tabela
# caia em `chr(o + 29)` e saia como um caractere PLAUSIVEL, nunca como
# falta - e o medidor `desconhecidos` de `decodifica_pdf` contava um
# marcador que ninguem escrevia, relatando zero enquanto 16 codigos saiam
# trocados. Os dois testes abaixo cobram (a) os oito codigos conferidos na
# pagina renderizada e (b) que o medidor consiga acusar.

#: byte extraido -> texto correto, conferido na PAGINA RENDERIZADA (regra 3).
#: O par (byte, esperado, o_que_a_regra_dava) documenta a troca silenciosa.
_TROCAS_G119 = [
    (0x9D, "ª", "º"),   # p.124 "2ª ordem"
    (0x94, "≤", "±"),   # p.41  "fck ≤ 50 MPa" - operador normativo
    (0x95, "≥", "²"),   # p.52  "h ≥ 60 cm"
    (0xC2, "·", "ß"),   # p.42  "αE · 5600 √fck"
    (0xC5, "‰", "â"),   # p.44  "εc2 = 2,0 ‰"
    (0xCB, "Í", "è"),   # p.249 "Índice de esbeltez"
    (0xBB, "/", "Ø"),   # p.167 "Md / z"
]

#: G120 - os sete que eram marcador e foram conferidos na PAGINA
#: RENDERIZADA (regra 3). O terceiro elemento e' o que saia SEM o
#: mapeamento (marcador visivel, nunca palpite - licao do G119).
_MAPEADOS_G120 = [
    (0x81, "ü", "[<U+0081>]"),    # p.118 "(Rüsch)"
    (0x92, "∞", "[<U+0092>]"),    # p.50 "t∞ - vida útil da estrutura"
    (0xA8, "Δ", "[<U+00A8>]"),    # p.37 "cnom cmín + Δc"
    (0xEE, "×", "[<U+00EE>]"),    # p.75 "-15 × 10-5"
    (0x101, "·", "[<U+0101>]"),   # p.139 "0,85 · [1,0 - ..."
    (0xED, "–", "[<U+00ED>]"),    # p.9 "cortante – Estado-limite último"
    (0xBC5, "–", "[<U+0BC5>]"),   # p.218 tabela 23.2, celula vazia
]

#: G120 - o que NAO foi mapeado, com o motivo. 0x0BD8 (188x, sempre antes
#: de item de lista "a)") tem avanço fixo de 0,91 pt e nenhuma marca
#: visivel na pagina renderizada (p.37 e p.52 em zoom 9x): controle de
#: layout do subset, nao glifo. Continua marcador declarado.
_ILEGIVEL_G120 = {0x0BD8: 188}


def test_04_codigos_que_saiam_trocados_g119():
    """Cada byte da lista sai com o caractere da PAGINA, nao com o da
    regra +29 - e a funcao real e' quem responde (sem reimplementar).

    G120: ganha as linhas dos sete codigos que eram marcador visivel e
    foram conferidos na pagina renderizada (lista _MAPEADOS_G120: sem o
    mapeamento cada um sai "[<U+XXXX>]", nunca palpite)."""
    quebras = []
    for byte, esperado, regra_antiga in _TROCAS_G119 + _MAPEADOS_G120:
        saiu = lente.decodifica_char(chr(byte))
        if saiu != esperado:
            quebras.append("0x%02X saiu %r, esperado %r (a regra +29 dava %r)"
                           % (byte, saiu, esperado, regra_antiga))
        if esperado == regra_antiga:            # guarda da propria tabela
            quebras.append("0x%02X: esperado igual ao da regra antiga"
                           % byte)
    assert not quebras, "G119 (troca silenciosa):\n" + "\n".join(quebras)


def test_05_medidor_de_desconhecidos_consegue_acusar_g119():
    """O medidor nao pode ser uma regua sem marca: byte alto fora da
    tabela sai como marcador, e um byte mapeado NAO sai como marcador."""
    fora = 0xF7                                  # alto e fora da tabela
    assert fora not in lente.TABELA_ESPECIAL, "escolha outro byte para o teste"
    marcado = lente.decodifica_char(chr(fora))
    assert marcado == lente.DESCONHECIDO_FMT % fora, marcado
    # o caminho vivo (texto inteiro) tambem marca, e a regra +29 segue
    # valendo para a faixa baixa: "7RGRV" continua "Todos".
    assert lente.DESCONHECIDO_FMT % fora in lente.decodifica_texto_bruto(
        "7RGRV" + chr(fora))
    assert lente.decodifica_texto_bruto("7RGRV") == "Todos"
    # byte mapeado nunca vira marcador (senao o medidor acusaria o proprio
    # acerto e voltaria a nao significar nada)
    for byte, esperado, _ in _TROCAS_G119 + _MAPEADOS_G120:
        assert lente.decodifica_char(chr(byte)) == esperado


def test_06_0bd8_declarado_ilegivel_g120():
    """O oitavo codigo nao e' glifo: 0x0BD8 sai marcador, e a contagem
    declarada (188, sempre antes de "a)") e' travada aqui - remapear sem
    conferir a imagem tem de passar por este teste (triagem escrita)."""
    for byte, contagem in _ILEGIVEL_G120.items():
        assert byte not in lente.TABELA_ESPECIAL, \
            "0x%04X entrou na tabela sem triagem escrita" % byte
        assert lente.decodifica_char(chr(byte)) == lente.DESCONHECIDO_FMT % byte
        assert contagem == 188, "triagem do 0BD8 mudou sem recontagem"
    # o caminho vivo tambem marca (o .txt declara, nao esconde)
    assert "[<U+0BD8>]" in lente.decodifica_texto_bruto(chr(0x0BD8) + "D")
