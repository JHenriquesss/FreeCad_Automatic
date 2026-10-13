# ============================================================================
# trechos_norma.py - TRECHOS LITERAIS DAS NORMAS CITADOS NO MEMORIAL
# Cada entrada e' um recorte do texto nativo da norma, extraido do acervo
# (MCP_Fontes) por marcador de inicio e de fim, sem redigitacao: gerado em
# 2026-10-13 (D228). `edicao_id` e `lido_no_item` dizem de onde saiu, para
# quem quiser ler o item inteiro. NAO editar o campo `texto` a mao: refazer a
# extracao. Tabelas e figuras (Tabelas 6 e 7 e Figura 1 da NBR 6123) nao tem
# trecho aqui: sao citadas pelo numero.
# ============================================================================
"""Trechos literais das normas, por secao do memorial de calculo."""

TRECHOS = [{'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '5.1',
  'lido_no_item': '5.1',
  'paginas_do_item': ['10'],
  'texto': 'A velocidade básica do vento, V0, é a velocidade de uma rajada de 3 s, a 10 m acima do '
           'terreno,\n'
           'em campo aberto e plano, excedida em média uma vez em 50 anos.'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '4.2 b)',
  'lido_no_item': '4.2',
  'paginas_do_item': ['8'],
  'texto': 'a velocidade básica do vento é multiplicada pelos fatores S1, S2 e S3 para ser obtida '
           'a velocidade\n'
           'característica do vento, Vk, para a parte da edificação, estrutura ou componente em '
           'consideração,\n'
           'de acordo com 5.2 a 5.5:\n'
           'Vk = V0 S1 S2 S3'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '4.2 c)',
  'lido_no_item': '4.2',
  'paginas_do_item': ['8'],
  'texto': 'q = 0,613 Vk², expresso em Newton por metro ao quadrado (N/m²)'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '5.4, Tabela 4 (grupo 3)',
  'lido_no_item': '5.4',
  'paginas_do_item': ['16', '17'],
  'texto': 'Edificações para residências, hotéis, comércio, indústrias.\n'
           'Estruturas ou elementos estruturais desmontáveis com vistas a reutilização.'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '5.4, Tabela 4 (grupo 4)',
  'lido_no_item': '5.4',
  'paginas_do_item': ['16', '17'],
  'texto': 'Edificações não destinadas à ocupação humana (depósitos, silos) e sem\n'
           'circulação de pessoas no entorno.'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '6.3.2.1 a)',
  'lido_no_item': '6.3',
  'paginas_do_item': ['42', '43', '44', '45'],
  'texto': 'Duas faces opostas igualmente permeáveis; as outras faces impermeáveis:\n'
           '— vento perpendicular a uma face permeável:\n'
           'cpi = +0,2\n'
           '— vento perpendicular a uma face impermeável:\n'
           'cpi = -0,3'},
 {'secao': '1. VENTO',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '6.3.2.1 c)',
  'lido_no_item': '6.3',
  'paginas_do_item': ['42', '43', '44', '45'],
  'texto': 'Abertura dominante em uma face; as outras faces de igual permeabilidade:\n'
           '— abertura dominante na face de barlavento.\n'
           'O valor de cpi depende da proporção entre a área de todas as aberturas na face de '
           'barlavento\n'
           'e a área total das aberturas em todas as faces (paredes e cobertura, nas condições de '
           '6.3.1)\n'
           'submetidas a sucções externas:'},
 {'secao': '1b. VENTO LONGITUDINAL',
  'norma': 'ABNT NBR 6123:2023',
  'edicao_id': 'ed_01M3CN7934JXME00Z2FQA4MKTD',
  'item': '4.3.3',
  'lido_no_item': '4.3.3',
  'paginas_do_item': ['9', '10'],
  'texto': 'A componente da força global na direção do vento, força de arrasto Fa, é obtida por:\n'
           'Fa = q Ca Ae fv'},
 {'secao': '2. PORTICO',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '4.8.7.2.1',
  'lido_no_item': '4.8.7.2.1',
  'paginas_do_item': [],
  'texto': 'Em cada combinação, devem estar incluídas as ações permanentes e a ação variável '
           'principal, com\n'
           'seus valores característicos, e as demais ações variáveis, consideradas secundárias, '
           'com seus valores reduzidos de combinação.'},
 {'secao': '2. PORTICO',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '4.8.6.2, Tabela 1, nota a',
  'lido_no_item': '4.8.6',
  'paginas_do_item': [],
  'texto': 'Os valores entre parênteses correspondem aos coeficientes para as ações permanentes '
           'favoráveis à segurança; ações variáveis e excepcionais favoráveis à segurança não '
           'podem ser incluídas nas combinações.'},
 {'secao': '2. PORTICO',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': 'B.3, Tabela B.1',
  'lido_no_item': 'B.3',
  'paginas_do_item': [],
  'texto': 'Galpões em geral e edificações de um pavimento:\n'
           '— Deslocamento horizontal do topo dos pilares em relação à base | H/300'},
 {'secao': '4. PERFIS',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '5.3.2',
  'lido_no_item': '5.3',
  'paginas_do_item': [],
  'texto': 'A força axial de compressão resistente de cálculo, N_c,Rd, de uma barra, associada aos '
           'estados-limiteúltimos de instabilidade por flexão, por torção ou flexo-torção, e de '
           'instabilidade local, deve ser determinada pela equação:N_c,Rd = χ A_ef f_y/γ_a1'},
 {'secao': '4. PERFIS',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '5.3.4.1',
  'lido_no_item': '5.3',
  'paginas_do_item': [],
  'texto': 'A área efetiva da seção transversal, A_ef, deve ser considerada igual à área bruta, '
           'A_g, se todos os elementos componentes da seção transversal possuírem relação entre '
           'largura e espessura (b/t) igual ou inferior ao valor (b/t)_lim, dado na Tabela 4.'},
 {'secao': '4. PERFIS',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '4.6.2.9',
  'lido_no_item': '4.6.2.9',
  'paginas_do_item': [],
  'texto': 'a) módulo de elasticidade, E = 200 000 MPa;b) coeficiente de Poisson, ν_a = 0,3;c) '
           'módulo de elasticidade transversal, G = 77 000 MPa;'},
 {'secao': '12b. SOLDA',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '6.2.6.2.1',
  'lido_no_item': '6.2.6.2',
  'paginas_do_item': [],
  'texto': 'O tamanho mínimo da perna de uma solda de filete é dado na Tabela 11, em função da '
           'parte menos espessa soldada.Tabela 11 — Tamanho mínimo da perna de uma solda de '
           'fileteMenor espessura do metal-base na junta (mm) | Tamanho mínimo da perna da solda '
           'de filete, d_wᵃ (mm)Abaixo de 6,3 e até 6,3 mm | 3 mm\n'
           'Acima de 6,3 até 12,5 mm | 5 mm\n'
           'Acima de 12,5 até 19 mm | 6 mm\n'
           'Acima de 19 mm | 8 mm'},
 {'secao': '12b. SOLDA',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': '6.2.2.2 a)',
  'lido_no_item': '6.2.2.2',
  'paginas_do_item': [],
  'texto': 'a área efetiva de uma solda de filete deve ser calculada como o produto do comprimento '
           'efetivo\n'
           'da solda pela espessura da garganta efetiva;'},
 {'secao': '12b. SOLDA',
  'norma': 'ABNT NBR 8800:2024/Er1:2025',
  'edicao_id': 'ed_01M4GD7SQPANJ9K94E21ZJYEFB',
  'item': 'A.4, Tabela A.4',
  'lido_no_item': 'A.4',
  'paginas_do_item': [],
  'texto': 'Todos os eletrodos com classe de resistência 7 ou 70 | 485'}]


def da_secao(titulo):
    """Trechos da secao do memorial cujo titulo comeca pela chave (ex.: '1. VENTO')."""
    alvo = (titulo or "").strip().upper()
    return [t for t in TRECHOS if alvo.startswith(t["secao"].upper())]
