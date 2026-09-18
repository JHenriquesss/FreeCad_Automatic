"""G156 - lente das frases que atribuem numero a NBR (D182).

Defeito (D179): uma citacao normativa errada (FS 3,0 da estaca "pela
NBR 6122") viveu dois meses porque nenhuma lente confere o numero citado
contra a pagina. Esta lente fecha a porta para TODA frase que atribui
numero a NBR: cada uma traz o item e foi triada contra a imagem da pagina
do acervo (convencao 15).

Regra (heuristica ruidosa, triagem e o goal): literal (AST Constant str)
ou comentario (tokenize) em *.py de producao que menciona NBR (inclui
"NBR NM") + contem numero com valor (decimal, inteiro com unidade, razao,
%, =, :) depois de remover identificadores NBR/anos/placeholders + NAO
contem padrao de item (n.n, Tabela/Tab., Anexo, Secao/Sec., Figura/Fig.,
Quadro) REPROVA, salvo triado na BASELINE.

Fora da lente, com a regra escrita aqui (decisao do goal):
- fonte que nao e NBR (livro, catalogo, fabricante): Pfeil, Mamede,
  Negrisoli, Creder, Alonso, catalogo de perfil, ANEEL, ANSI 50/51;
- remissao ("ver NBR", titulo que so nomeia a norma, parametro descrito
  com numero do PROJETO, mensagem com %r/%s, geometria do desenho,
  etapa ordinal "2a/4a", dado de ensaio declarado);
- frase nao conferivel (norma fora do acervo ou pagina ilegivel): fica
  como esta, com o motivo;
- frase ja coberta por lente anterior (D179: FS 3,0 + NBR 6122).

Baseline nos dois sentidos (convencao 1): frase sem triagem reprova;
triagem sem frase reprova (atualize a BASELINE no mesmo commit).
Injecao em tmp_path (convencao 2), nunca mutando o repo. A lente acusa
por frase, nomeando arquivo:linha (convencoes 7/G125).
"""
import ast
import io
import os
import re
import tokenize

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)

PAT_NBR = re.compile(r"NBR\s+(?:NM\s+)?\d{3,5}(?:[-:/]\d+)*(?::\d+)?",
                     re.IGNORECASE)
PAT_ITEM = re.compile(
    r"\d+\.\d+|Tabela|TABELA|Tab\.|Anexo|ANEXO|Secao|Se\u00e7\u00e3o"
    r"|Sec\.|Figura|Fig\.|Quadro|Cap\.\d+", re.IGNORECASE)
PAT_PLACE = re.compile(r"%[srdf\d.]*|%\.\d+f|\{[^}]*\}|%\(.*?\)")
PAT_VALOR = re.compile(
    r"\d+[,.]\d+|\d+\s*/\s*\d+|\d+\s*%|=\s*-?\d|:\s*\d"
    r"|\d+\s*(?:ohm|mm|cm|m2|m\u00b2|MPa|kPa|Pa|kN|kg|MJ|m/s|m3/h|TR"
    r"|V\b|A\b|bit|DN\b|UHC\b|N\b)",
    re.IGNORECASE)

# (arquivo, marcador estavel, veredicto). Veredictos:
#   CONFERE <item> <pagina> - numero bate com a pagina (imagem conferida);
#   DIVERGE <o que mudou> - atribuicao corrigida, numero NUNCA trocado;
#   NAO_CONFERIVEL <motivo> - fica como esta;
#   REMISSAO <motivo> / FONTE_NAO_NBR <motivo> - fora da lente;
#   D179 <motivo> - ja coberto pela lente da auditoria.
# Pagina = "p.<da norma> (arq p.<do arquivo>)" ou "catalogo" quando o motivo
# vem do catalogo.csv (ausencia no acervo).
BASELINE = [
    # --- CONFERE (item acrescentado no G156, numero identico) ---
    ("validacao.py", "Vk = V0*S1*S2*S3 e q = 0,613",
     "CONFERE NBR 6123:1988 4.2 c) p.4 (q = 0,613 Vk2, q em N/m2, Vk em m/s)"),
    ("validacao.py", "Vento (NBR 6123:1988 4.2 c)",
     "CONFERE NBR 6123:1988 4.2 c) p.4"),
    ("validacao.py", "3) Vento NBR 6123:1988 4.2 c)",
     "CONFERE NBR 6123:1988 4.2 c) p.4 (comentario do check)"),
    ("relatorio_calculo.py", "Pressao dinamica q = 0,613",
     "CONFERE NBR 6123:1988 4.2 c) p.4"),
    ("desempenho_nbr15575.py", "0,6 mm em qualquer situacao",
     "CONFERE NBR 15575-2:2013 7.3.1 p.7"),
    ("fogo_nbr14323.py", "Combinacao excepcional de incendio",
     "CONFERE NBR 14323:2013 6.3.1 Tab.3 p.13 (gama 1,0 fav; 1,10/1,15/1,20/1,30 desf); "
     "psi2 0,2/0,4/0,6 como Pendencia ao usuario (6.3.1 traz 0,21/0,28/0,42)"),
    ("protecao_nbr5410.py", "I2<=1,45*IZ",
     "CONFERE NBR 5410:2004 5.3.4.1 p.63 (IB<=In<=Iz; I2<=1,45 Iz)"),
    ("ponte_rolante.py", "NBR 8800:2008 Tab.C.1: L/600",
     "CONFERE NBR 8800:2008 Tab.C.1 p.117 (L/600 <200 kN; L/800 >=200; L/1000 siderurgica)"),
    ("ponte_rolante.py", "ELS (NBR 8800:2008 Tab.C.1): flecha vertical L/600",
     "CONFERE NBR 8800:2008 Tab.C.1 p.117 (comentario)"),
    ("tesoura.py", "NBR 8800:2008 Tab.3: ruptura (1,35)",
     "CONFERE NBR 8800:2008 4.8.2.1 Tab.3 p.23 (gama2 ruptura = 1,35)"),
    ("techdraw_hidraulica.py", "v<=3 m/s",
     "CONFERE NBR 5626:2020 6.8.3 NOTA p.21 (limite maximo 3 m/s)"),
    ("techdraw_hidraulica.py", "coletor predial DN minimo 100",
     "CONFERE NBR 8160:1999 5.1.4.1 p.17 (DN minimo 100) e 4.2.3.2 p.4 (2% DN<=75; 1% DN>=100)"),
    ("impacto_nbr6118_g116.py", "CA-25/50/60 conforme NBR 7480",
     "CONFERE NBR 7480:2024 4.1.2 p.3 (barras CA-25/50/70; fios CA-60)"),
    ("spda_nbr5419.py", "RT=1e-5",
     "CONFERE NBR 5419-2:2026 5.3 Tab.4 p.27 (R1 = 1e-5)"),
    ("viga_protendida.py", "Cordoalha CP-190 RB (NBR 7483:2021 4.1.2)",
     "CONFERE NBR 7483:2021 4.1.2 p.3 (categoria CP-190)"),
    ("telhado_casa_madeira.py", "1,4.(G+Q) (NBR 8681",
     "CONFERE-parcial NBR 8681:2025 Tab.1 p.14 (adotado 1,4; madeira desf 1,30) - "
     "Pendencia ao usuario: confirmar 1,4 ante o 1,30 da madeira"),
    ("tesoura.py", "gamma_g do peso permanente (NBR 8681:2025 Tab.1",
     "CONFERE-parcial NBR 8681:2025 Tab.1 p.14 (fav 1,0; adotado 0,9 conservador p/ uplift; "
     "desf 1,4) - Pendencia ao usuario: confirmar 0,9/1,4 ante Tab.1"),
    ("tercas_nbr14762.py", "gamma_g FAVORAVEL: adotado 0,90",
     "CONFERE-parcial NBR 8681:2025 Tab.1 p.14 (fav 1,0; adotado 0,90 conservador) + "
     "NBR 8800 Tab.1 (permite 1,00) ja declarados no comentario"),
    ("tercas_nbr14762.py", "gamma_g FAVORAVEL = 0,90",
     "CONFERE-parcial NBR 8681:2025 Tab.1 p.14 (idem)"),
    ("galpao_portico.py", "gamma_f * psi0 = 1,40 * 0,60 = 0,84",
     "CONFERE NBR 8681:2025 Tab.4 p.15 (gama-q vento 1,4) + Tab.6 (psi0 vento 0,6) + "
     "Tab.1 p.14 (gama-g fav 1,0) + 5.1.4.2 p.15"),
    ("galpao_portico.py", "acoes variaveis favoraveis nao entram na combinacao",
     "CONFERE NBR 8681:2025 5.1.4.2 p.15"),
    # --- DIVERGE (so a atribuicao; nenhum numero mudou) ---
    ("instalacao_eletrica.py", "vem da NBR NM 247-3 Tabela 1",
     "DIVERGE: diametro externo do cabo isolado e da NBR NM 247-3 Tab.1 p.5 "
     "(2,5 mm2 cl.1 = 3,2 a 3,9 mm); a NBR NM 280 Tab.1 p.9 trata da resistencia "
     "do condutor (2,5 mm2 = 7,41 ohm/km). _ELETRODUTO_POR_SECAO inalterado"),
    ("incendio_edificio.py", "risco extraordinario grupo 1 (NBR 10897:2014 Anexo A",
     "DIVERGE-parcial: grupo 1 existe na NBR 10897:2014 Anexo A Tab.A.1 p.92; a faixa "
     "3,0 m < H <= 5,0 m NAO foi localizada na 10897 nem na 16981 - "
     "Pendencia ao usuario: confirmar o item da faixa"),
    ("aterramento_nbr15749.py", "metodo de WENNER (norma de resistividade",
     "DIVERGE: NBR 15749:2009 1.1 (escopo: resistencia de aterramento e potenciais, "
     "nao resistividade Wenner); Wenner e objeto da 7117-1 (fora do acervo; ref. na "
     "NBR 5419-3:2026). "
     "Re-atribuido a base declarada no cabecalho (Negrisoli Cap.11) - Pendencia ao usuario"),
    ("aterramento_nbr15749.py", "Resistividade aparente do solo (metodo de Wenner",
     "DIVERGE idem (docstring do Wenner)"),
    ("aterramento_nbr15749.py", "LIMITE recomendado: R <= 10 ohm adotado",
     "DIVERGE: NBR 5419-3:2026 7.1.4 nao exige medicao de resistencia (10 ohm era da "
     "edicao anterior/pratica); mantido como limite adotado - Pendencia ao usuario"),
    ("aterramento_nbr15749.py", "limite de 10 ohm adotado",
     "DIVERGE idem (docstring do modulo)"),
    ("techdraw_eletrico.py", "limite 10 ohm adotado; NBR 5419-3:2026 7.1.4",
     "DIVERGE idem (texto da folha; numero do carimbo inalterado)"),
    ("esgoto_reuso.py", "METODO DE RIPPL (balanco de massa;",
     "DIVERGE: NBR 15527:2019 4.4.10 (reservatorio por criterios tecnicos, sem prescrever "
     "metodo); Rippl pode ser da ed. 2007 - Pendencia ao usuario"),
    ("projeto_spec.py", "theta_critica ausente -> assumindo 550 C",
     "DIVERGE-parcial: 550 C e o theta-o,t p/ TRRF 30 na NBR 14323:2013 Tab.B.6 p.42 "
     "(nao theta-critica p/ mu 0,6); mantido como assumido/CONFIRMAR - Pendencia ao usuario"),
    ("rodar_galpao.py", "theta_critica = 550 C (mu~0,6;",
     "DIVERGE-parcial idem (DEFAULT - CONFIRMAR)"),
    ("rodar_galpao.py", "theta_critica (NBR 14323:2013 Tab.B.6",
     "DIVERGE-parcial idem (comentario)"),
    ("rodar_galpao.py", ">= 10% da carga vertical, NBR 6122 / Alonso",
     "DIVERGE-fonte-mista: 10% com NBR 6122 E Alonso (livro); item da norma nao "
     "localizado - numero do codigo (0.10) inalterado - Pendencia ao usuario"),
    # --- NAO_CONFERIVEL (fica como esta, com o motivo) ---
    ("climatizacao_nbr16401.py", "27*n + 1,5*A (NBR 16401-3)",
     "NAO_CONFERIVEL: NBR 16401-3 fora do acervo (so F077 parte 1); catalogo."),
    ("techdraw_climatizacao.py", "0,335.dT",
     "NAO_CONFERIVEL: NBR 16401-2 fora do acervo (so F077 parte 1); catalogo."),
    # --- REMISSAO / FONTE_NAO_NBR (fora da lente, regra escrita) ---
    ("projeto_spec.py", "FS < 3,0 SEM prova de carga BLOQUEIA (NBR 6122 semi-empirico)",
     "D179: FS 3,0 coberto pela lente test_03 (6.2.1.2.1); comentario sem item, numero ja triado"),
    ("fundacao_sapata_corrida.py", "Concreto da faixa de 1 m (NBR 6118)",
     "REMISSAO: 1 m e a faixa de analise (geometria convencionada), nao valor da norma"),
    ("projeto_spec.py", "abaixo do minimo do mapa de isopletas NBR 6123",
     "REMISSAO: ~30 com til e contexto (comparacao com dado de sitio), nao valor atribuido"),
    ("vento_nbr6123.py", "VENTO LONGITUDINAL (ABNT NBR 6123/1988",
     "REMISSAO: titulo do emissor, sem valor"),
    ("dossie.py", "Normas:       NBR 8800 / 6118",
     "REMISSAO: lista de normas do dossie, sem valor"),
    ("edificio_adapter.py", "Agua fria, esgoto e pluvial do predio (NBR 5626:2020",
     "REMISSAO: titulo do vertical, sem valor"),
    ("hidraulica_edificio.py", "hidraulica_predial (NBR 5626:2020",
     "REMISSAO: titulo/contexto, sem valor"),
    ("hidraulica_edificio.py", "HIDRAULICA DO EDIFICIO MULTIPAVIMENTO - NBR 5626:2020",
     "REMISSAO: titulo, sem valor"),
    ("hidraulica_predial.py", "hidraulica_predial self-test PASSED (NBR 5626:2020",
     "REMISSAO: self-test, sem valor"),
    ("hidraulica_residencial.py", "reusando hidraulica_predial (NBR 5626:2020",
     "REMISSAO: contexto, sem valor"),
    ("hidraulica_residencial.py", "hidraulica_residencial self-test PASSED (NBR 5626:2020",
     "REMISSAO: self-test, sem valor"),
    ("galpao_hidraulica.py", "HIDRAULICA PREDIAL - GALPAO (NBR 5626:2020",
     "REMISSAO: titulo, sem valor"),
    ("galpao_hidraulica.py", "PLUVIAL (NBR 10844): Q = i*A/60",
     "REMISSAO: fragmento; conjunto com item (Tab.4/Tab.5 nas linhas seguintes) + "
     "i e DADO DE SITIO declarado"),
    ("hidraulica_predial.py", "adaptado da NBR 5626",
     "REMISSAO: fragmento de nota de proveniencia multi-linha (Tab.B.4 + cited_text + "
     "AUDITADO S41 nas linhas vizinhas)"),
    ("hidraulica_predial.py", "telhado 100 m2, i=150 mm/h",
     "REMISSAO: numeros do exemplo de comentario (dados de sitio), nao da norma"),
    ("escada.py", "Escada de VARIOS LANCES",
     "REMISSAO: docstring de parametros (N = n. de lances do projeto); NBR 9050/9077 "
     "citada como A CONFIRMAR onde aplicavel"),
    ("escada.py", "Dimensiona longarina de escada reta",
     "REMISSAO: docstring de parametros, sem valor da norma"),
    ("fundacao_sapata.py", "Traduz As requerido",
     "REMISSAO: numeros sao constantes do codigo ([S_MIN, S_MAX]), nao da norma"),
    ("fundacao_edificio.py", "M_portico nos pilares de divisa",
     "REMISSAO: numeros do projeto (~800-1500 kNm via %s), nao da norma"),
    ("relatorio_calculo.py", "Trelica de cobertura (Warren/Pratt)",
     "REMISSAO: numeros estruturais (b+r=2j, 2j x (b+3)), nao da norma"),
    ("validacao_sistema_g15.py", "G25",
     "REMISSAO: definicao do caso de validacao (dados do galpao UFPE), nao da norma"),
    ("desenho_casa_residencial.py", "calculados (NBR 5626 / 8160 / 10844)",
     "REMISSAO: comentario de contexto, sem valor"),
    ("desenho_incendio.py", "N_hidrantes distribuidos junto ao perimetro (<= 5 m das",
     "REMISSAO: fragmento; conjunto com item (5.2.1 na linha seguinte)"),
    ("galpao_seguranca_incendio.py", "eixo longitudinal central, z=2,1 m",
     "REMISSAO: numero do desenho (posicionamento), nao da norma"),
    ("galpao_seguranca_incendio.py", "abrigo a 0,9 m",
     "REMISSAO: numero do desenho, nao da norma"),
    ("condutores_nbr5410.py", "2a etapa do projeto eletrico",
     "REMISSAO: ordinal (etapa), nao valor"),
    ("protecao_nbr5410.py", "4a etapa do projeto eletrico",
     "REMISSAO: ordinal, nao valor"),
    ("spda_nbr5419.py", "partes 1 a 4, ed. 2026",
     "REMISSAO: edicao/partes, nao valor"),
    ("console_ponte.py", "0,707*perna",
     "REMISSAO: 0,707 e geometria (cos45); NBR 8400 citada p/ n_ciclos (input), nao p/ o valor"),
    ("ponte_rolante.py", "phi (do fabricante ou NBR 8400",
     "REMISSAO: parametro A CONFIRMAR declarado (1,10..1,25 faixa do comentario)"),
    ("rodar_galpao.py", "ponte rolante de 100 kN (exemplo; dados A CONFIRMAR",
     "REMISSAO: exemplo com dados A CONFIRMAR declarados"),
    ("subestacao_nbr14039.py", "protecao 50/51 ou fusivel HH",
     "FONTE_NAO_NBR: 50/51 sao codigos ANSI; base Mamede Cap.12 declarada no literal"),
    ("techdraw_concreto.py", "tolerancias 'NBR 8800/6118'",
     "REMISSAO: mensagem de diff de carimbo (fields), sem valor"),
    ("perdas_protensao_nbr6118.py", "-3,8e-4..-6,2e-4",
     "REMISSAO: fragmento; conjunto com item (Tab.A.1 na linha anterior) + fonte lida declarada"),
    ("torcao_nbr6118.py", "theta arbitrado em 30..45 graus",
     "REMISSAO: fragmento; conjunto com itens (17.5.1.6a/6b e 17.7.2.2 nas linhas "
     "vizinhas) + fonte lida declarada (NotebookLM, nao de memoria)"),
    ("fundacao_edificio.py", "numero do FS nao muda",
     "D179: fragmento; conjunto com item (6.2.1.2.1 nas linhas seguintes); numero ja triado"),
]


def _modulos_fonte():
    return sorted(
        p for p in os.listdir(GALPAO)
        if p.endswith(".py") and os.path.isfile(os.path.join(GALPAO, p))
        and not p.startswith("test_") and not p.startswith("varredura_")
    )


def _candidatos_em_texto(nome, texto):
    """Rende (linha, origem, trecho) para cada frase sem item com valor."""
    achados = []
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return achados
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            v = no.value
            if not PAT_NBR.search(v) or PAT_ITEM.search(v):
                continue
            sem = PAT_NBR.sub("", v)
            sem = re.sub(r"\b(?:19|20)\d{2}\b", "", sem)
            sem = PAT_PLACE.sub("", sem)
            if PAT_VALOR.search(sem):
                achados.append((no.lineno, "literal",
                                v.replace("\n", " ")[:220]))
    try:
        toks = tokenize.generate_tokens(io.StringIO(texto).readline)
        for tk in toks:
            if tk.type == tokenize.COMMENT:
                v = tk.string
                if not PAT_NBR.search(v) or PAT_ITEM.search(v):
                    continue
                sem = PAT_NBR.sub("", v)
                sem = re.sub(r"\b(?:19|20)\d{2}\b", "", sem)
                if PAT_VALOR.search(sem):
                    achados.append((tk.start[0], "comentario", v[:220]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return achados


def _candidatos():
    out = []
    for nome in _modulos_fonte():
        with open(os.path.join(GALPAO, nome), encoding="utf-8",
                  errors="ignore") as fh:
            texto = fh.read()
        for linha, origem, trecho in _candidatos_em_texto(nome, texto):
            out.append((nome, linha, origem, trecho))
    return out


def _cobre(marcador, trecho):
    return marcador in trecho


def test_nenhuma_frase_nova_sem_triagem():
    """Toda frase com valor sem item esta na BASELINE (sentido 1)."""
    base = {}
    for arq, marcador, _ver in BASELINE:
        base.setdefault(arq, []).append(marcador)
    faltando = []
    for nome, linha, origem, trecho in _candidatos():
        ok = any(_cobre(m, trecho) for m in base.get(nome, []))
        if not ok:
            faltando.append("%s:%d [%s]: %r"
                            % (nome, linha, origem, trecho[:120]))
    assert not faltando, (
        "frase que atribui numero a NBR sem item e sem triagem (G156):\n"
        + "\n".join(faltando)
        + "\nTrie contra a imagem da pagina (confere/diverge/nao e da "
        "norma/nao conferivel) e registre na BASELINE."
    )


def test_baseline_sem_fantasma():
    """Toda triagem existe no codigo (sentido 2; atualize a BASELINE)."""
    textos = {}
    for nome in _modulos_fonte():
        with open(os.path.join(GALPAO, nome), encoding="utf-8",
                  errors="ignore") as fh:
            textos[nome] = fh.read()
    fantasmas = []
    for arq, marcador, _ver in BASELINE:
        if marcador not in textos.get(arq, ""):
            fantasmas.append("%s: marcador sumiu do codigo: %r" % (arq, marcador))
    assert not fantasmas, (
        "BASELINE desatualizada (G156):\n" + "\n".join(fantasmas)
        + "\nAtualize a BASELINE no mesmo commit."
    )


def test_injecao_sem_item_reprova_nomeando_arquivo_linha(tmp_path):
    """Vermelho por injecao: frase sem item reprova com arquivo:linha."""
    sujo = ('X = "vazao minima 27*n + 1,5*A (NBR 16401-3)"\n'
            '# diametro externo pela NBR NM 280 sem item, 3,9 mm\n')
    limpo = ('X = "vazao minima (NBR 16401-3 7.2.1)"\n'
             '# diametro externo pela NBR NM 247-3 Tab.1, 3,9 mm\n')
    ok_sujo = [c for c in _candidatos_em_texto("inj_sujo.py", sujo)]
    ok_limpo = [c for c in _candidatos_em_texto("inj_limpo.py", limpo)]
    p = tmp_path / "inj_sujo.py"
    p.write_text(sujo, encoding="utf-8")
    lados = []
    if len(ok_sujo) != 2:
        lados.append("injetado sem item nao acusa nos 2 lugares: %r" % (ok_sujo,))
    linhas = sorted(c[0] for c in ok_sujo)
    if linhas != [1, 2]:
        lados.append("a lente nao nomeia arquivo:linha do injetado: %r" % (ok_sujo,))
    if ok_limpo:
        lados.append("a lente acusa o caso corrigido (com item): %r" % (ok_limpo,))
    assert not lados, "\n".join(lados)
