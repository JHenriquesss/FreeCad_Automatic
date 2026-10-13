"""Extrai do MCP_Fontes os trechos literais citados no memorial e escreve trechos_norma.py.
Uso: python gera_trechos.py <saida.py>"""
import json
import os
import pprint
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontes_mcp as fontes

V = "ed_01M3CN7934JXME00Z2FQA4MKTD"     # NBR 6123:2023
A = "ed_01M4GD7SQPANJ9K94E21ZJYEFB"     # NBR 8800:2024/Er1:2025
NOME = {V: "ABNT NBR 6123:2023", A: "ABNT NBR 8800:2024/Er1:2025"}

# (secao do memorial, edicao, item a ler, rotulo do item, inicio, fim)
PEDIDOS = [
    ("1. VENTO", V, "5.1", "5.1", "A velocidade básica do vento, V0, é", "uma vez em 50 anos."),
    ("1. VENTO", V, "4.2", "4.2 b)", "a velocidade básica do vento é multiplicada",
     "Vk = V0 S1 S2 S3"),
    ("1. VENTO", V, "4.2", "4.2 c)", "q = 0,613 Vk²", "(N/m²)"),
    ("1. VENTO", V, "5.4", "5.4, Tabela 4 (grupo 3)", "Edificações para residências, hotéis",
     "desmontáveis com vistas a reutilização."),
    ("1. VENTO", V, "5.4", "5.4, Tabela 4 (grupo 4)", "Edificações não destinadas à ocupação",
     "pessoas no entorno."),
    ("1. VENTO", V, "6.3", "6.3.2.1 a)", "Duas faces opostas igualmente permeáveis",
     "cpi = -0,3"),
    # para antes da lista de valores: no texto do acervo a coluna das razoes de area
    # perdeu celulas (so' aparecem "1,5" e "6 ou mais"), e citar a lista assim engana
    ("1. VENTO", V, "6.3", "6.3.2.1 c)", "Abertura dominante em uma face",
     "submetidas a sucções externas:"),
    ("1b. VENTO LONGITUDINAL", V, "4.3.3", "4.3.3", "A componente da força global na direção",
     "Fa = q Ca Ae fv"),
    ("2. PORTICO", A, "4.8.7.2.1", "4.8.7.2.1", "Em cada combinação, devem estar incluídas",
     "valores reduzidos de combinação."),
    ("2. PORTICO", A, "4.8.6", "4.8.6.2, Tabela 1, nota a", "Os valores entre parênteses correspondem",
     "não podem ser incluídas nas combinações."),
    ("2. PORTICO", A, "B.3", "B.3, Tabela B.1", "Galpões em geral e edificações de um pavimento:",
     "H/300"),
    ("4. PERFIS", A, "5.3", "5.3.2", "A força axial de compressão resistente de cálculo, N_c,Rd",
     "N_c,Rd = χ A_ef f_y/γ_a1"),
    ("4. PERFIS", A, "5.3", "5.3.4.1", "A área efetiva da seção transversal, A_ef, deve ser",
     "dado na Tabela 4."),
    ("4. PERFIS", A, "4.6.2.9", "4.6.2.9", "a) módulo de elasticidade", "G = 77 000 MPa;"),
    ("12b. SOLDA", A, "6.2.6.2", "6.2.6.2.1", "O tamanho mínimo da perna de uma solda de filete",
     "Acima de 19 mm | 8 mm"),
    ("12b. SOLDA", A, "6.2.2.2", "6.2.2.2 a)", "a área efetiva de uma solda de filete deve ser",
     "garganta efetiva;"),
    ("12b. SOLDA", A, "A.4", "A.4, Tabela A.4", "Todos os eletrodos com classe de resistência 7 ou 70",
     "485"),
]


def limpa(s):
    s = s.replace("\r", "")
    # rodape de pagina preso no meio do item (nao e' texto da norma)
    s = re.sub(r"\n?[^\n]{0,3}ABNT 20\d\d - Todos os direitos reservados ?\d*\n?", "\n", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return re.sub(r"[ \t]+", " ", s).strip()


cache = {}
saida = []
for secao, ed, item, rotulo, ini, fim in PEDIDOS:
    if (ed, item) not in cache:
        r = fontes.chamar([("read_clause", {"edition_id": ed, "number": item, "limit": 60000})])[0]
        d = json.loads(r["result"]["content"][0]["text"])
        assert "data" in d, (item, d)
        cache[(ed, item)] = d["data"]
    dado = cache[(ed, item)]
    txt = dado["texto"]
    i = txt.find(ini)
    assert i >= 0, ("inicio nao achado", item, ini)
    j = txt.find(fim, i)
    assert j >= 0, ("fim nao achado", item, fim)
    trecho = limpa(txt[i:j + len(fim)])
    paginas = sorted({p["page_label"] for p in dado["pecas"] if p.get("page_label")},
                     key=lambda x: int(x) if str(x).isdigit() else 0)
    saida.append({"secao": secao, "norma": NOME[ed], "edicao_id": ed, "item": rotulo,
                  "lido_no_item": item, "paginas_do_item": paginas, "texto": trecho})
    print("%-24s %-28s %4d car." % (secao, rotulo, len(trecho)))

cab = '''# ============================================================================
# trechos_norma.py - TRECHOS LITERAIS DAS NORMAS CITADOS NO MEMORIAL
# Cada entrada e' um recorte do texto nativo da norma, extraido do acervo
# (MCP_Fontes) por marcador de inicio e de fim, sem redigitacao: gerado em
# 2026-10-13 (D228). `edicao_id` e `lido_no_item` dizem de onde saiu, para
# quem quiser ler o item inteiro. NAO editar o campo `texto` a mao: refazer a
# extracao. Tabelas e figuras (Tabelas 6 e 7 e Figura 1 da NBR 6123) nao tem
# trecho aqui: sao citadas pelo numero.
# ============================================================================
"""Trechos literais das normas, por secao do memorial de calculo."""

TRECHOS = '''
corpo = pprint.pformat(saida, width=100, sort_dicts=False)
fim = '''


def da_secao(titulo):
    """Trechos da secao do memorial cujo titulo comeca pela chave (ex.: '1. VENTO')."""
    alvo = (titulo or "").strip().upper()
    return [t for t in TRECHOS if alvo.startswith(t["secao"].upper())]
'''
open(sys.argv[1], "w", encoding="utf-8", newline="\n").write(cab + corpo + fim)
print("gravado", sys.argv[1], len(saida))
