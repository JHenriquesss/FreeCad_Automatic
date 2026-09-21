"""G156 - lente das frases que atribuem numero a NBR (D182).
G160 - a mesma lente passa a enxergar fonte normativa de conta que nao
e NBR (D189): distribuidora (WKI/ENEL, por codigo de documento), IEC,
ISO/CIE 8995. WKI nunca vai para FONTE_NAO_NBR (ela e fonte de conta).

Defeito (D179): uma citacao normativa errada (FS 3,0 da estaca "pela
NBR 6122") viveu dois meses porque nenhuma lente confere o numero citado
contra a pagina. Esta lente fecha a porta para TODA frase que atribui
numero a norma de conta: cada uma traz o item e foi triada contra a imagem
da pagina do acervo (convencao 15).

Regra (heuristica ruidosa, triagem e o goal): literal (AST Constant str)
ou comentario (tokenize) em *.py de producao que menciona FONTE DE CONTA
(NBR, inclui "NBR NM", OU distribuidora/IEC/ISO-CIE abaixo) + contem numero
com valor (decimal, inteiro com unidade, razao, %, =, :) depois de remover
identificadores NBR/anos/placeholders + NAO contem padrao de item (n.n,
Tabela/Tab., Anexo, Secao/Sec., Figura/Fig., Quadro) REPROVA, salvo triado
na BASELINE. E TODA frase que menciona fonte de conta (com ou sem item,
com ou sem valor) tem de estar na BASELINE com o veredicto (CONFERE,
DIVERGE, NAO_CONFERIVEL, REMISSAO): citacao de conta sem triagem reprova,
mesmo com item (e o ponto do G160 - as 11+ citacoes WKI trazem item e a
lente do G156 nunca as viu).

Fonte de conta (coberta pela lente, com item e triagem na imagem):
- NBR (PAT_NBR, como no G156);
- distribuidora POR CODIGO DE DOCUMENTO: WKI (abreviacao E codigo cheio
  WKI-OMBR-MAT-18-0263-INBR-R01 - o padrao casa os dois, nunca so um),
  CNC-... (qualquer CNC-...-EDBR/EDRJ, com ou sem revisao) e ET-123-R01;
- IEC (com ou sem "NBR" na frente, com ou sem numero);
- ISO/CIE da iluminacao (NBR ISO/CIE 8995-1, ISO/CIE 8995-1, NBR 8995-1,
  8995-1). "ISO" sozinho NAO e fonte de conta (ISO 5457 de prancha,
  ISO-8601 de data, "piso"/"aviso" que contem "iso" nunca casam: o padrao
  exige 8995 ou CIE ao lado).

Fora da lente, com a regra escrita aqui (decisao do goal):
- fonte que nao e normativa de conta (livro, catalogo, fabricante -
  isencao do G156 MANTIDA): Pfeil, Mamede,
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
# G160 - fonte normativa de conta que nao e NBR (distribuidora por codigo,
# IEC, ISO/CIE da iluminacao). Cada sub-padrao casa a abreviacao E o codigo
# cheio (anti-filtro-morto: substring que nunca casa vira no-op silencioso).
PAT_WKI = re.compile(r"\bWKI(?:-OMBR-MAT-18-0263-INBR-R01)?\b",
                     re.IGNORECASE)
PAT_CNC_ET = re.compile(r"\bCNC-[A-Z0-9\-]+\b|\bET-123-R01\b",
                        re.IGNORECASE)
PAT_IEC = re.compile(r"\bNBR\s+IEC\s*\d*(?:[-/]\d+)*"
                     r"|\bIEC\s*\d*(?:[-/]\d+)*",
                     re.IGNORECASE)
PAT_ISO_CIE = re.compile(r"\bNBR\s+ISO/CIE\s*8995(?:-1)?\b"
                         r"|\bISO/CIE\s*8995(?:-1)?\b"
                         r"|\bNBR\s*8995-1\b|\b8995-1\b",
                         re.IGNORECASE)
PAT_CONTA = re.compile("|".join((PAT_WKI.pattern, PAT_CNC_ET.pattern,
                                 PAT_IEC.pattern, PAT_ISO_CIE.pattern)),
                       re.IGNORECASE)
PAT_FONTE = re.compile(PAT_NBR.pattern + "|" + PAT_CONTA.pattern,
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
    # --- G160 (D189): fonte normativa de conta que nao e NBR, triada na ---
    # --- imagem. F131 = WKI-OMBR-MAT-18-0263-INBR-R01 (44 pp., PDF digital);
    # --- pagina do arquivo = pagina impressa da norma (o rodape numerado ---
    # --- coincide com a pagina do viewer; conferido nas imagens p.5-8,13-14).
    # --- WKI nunca vai para FONTE_NAO_NBR (ela e fonte de conta). ---
    # WKI 6.1: potencia instalada (CONFERE p.5, imagem vista).
    ("demanda_residencial_enel.py", "WKI Enel item 6.1, PDF p. 5",
     "CONFERE WKI-OMBR-MAT-18-0263-INBR-R01 6.1 p.5 (arq p.5): "
     "P(kW) = Pn(CV) x 0,736 / eta; sem placa 1 CV = 1500 W"),
    # WKI Tabela 1 (CONFERE descricao; celulas ao G161).
    ("demanda_residencial_enel.py", "WKI - Tabela 1: (quantidade",
     "CONFERE WKI 6.2.3.1/TABELA 1 p.13 (arq p.13): limite 3,5 kW, "
     "kW = kVA (resistiva); fatores celula a celula ao G161"),
    # WKI TABELAS 2 e 3: notas de transcricao (sem valor na frase).
    ("demanda_residencial_enel.py", "WKI TABELA 2 (PDF p. 14): three-phase",
     "REMISSAO: nota de proveniencia da transcricao (TABELA 2 trifasica, "
     "PDF p.14); celulas ao G161"),
    ("demanda_residencial_enel.py", "WKI TABELA 3 (PDF p. 14): single-phase",
     "REMISSAO: nota de proveniencia da transcricao (TABELA 3 monofasica, "
     "PDF p.14); celulas ao G161"),
    # WKI 6.2.3.3 (CONFERE p.8, imagem vista).
    ("demanda_residencial_enel.py", "WKI 6.2.3.3:",
     "CONFERE WKI 6.2.3.3 p.8 (arq p.8): vapor Hg/Na/metalico / 0,9; "
     "incandescente kW = kVA; 100% da instalada"),
    # WKI notes 1-2 / modulo da cozinha (CONFERE p.7, imagem vista).
    ("demanda_residencial_enel.py", "WKI notes 1 and 2 (p. 7)",
     "CONFERE WKI NOTAS 1-2 p.7 (arq p.7): COZINHA 1 ate 2 quartos, "
     "COZINHA 2 com 3+"),
    # WKI 6.2.3.2 (CONFERE p.8, imagem vista).
    ("demanda_residencial_enel.py", "O item 6.2.3.2",
     "CONFERE WKI 6.2.3.2 p.8 (arq p.8): TABELAS 2 e 3 por quantidade de "
     "motores de MESMA potencia; 100% da maior + 70% das demais"),
    # WKI recusas: textos sem valor (a tabela citada confere p.14).
    ("demanda_residencial_enel.py", "motor bif",
     "REMISSAO: texto de recusa (bifasico fora das TABELAS 2 e 3), sem "
     "valor; tabelas vistas p.14 (arq p.14)"),
    ("demanda_residencial_enel.py", "sem linha exata nas TABELAS 2 e 3 da WKI",
     "REMISSAO: texto de recusa (sem interpolar grafia fora da fonte), sem "
     "valor; tabelas vistas p.14 (arq p.14)"),
    ("demanda_residencial_enel.py", "deve ser inteiro",
     "CONFERE WKI TABELAS 2-3 p.14 (arq p.14): colunas de quantidade "
     "1 a 10, so inteiro >= 1 entra"),
    ("demanda_residencial_enel.py", "acima de 10 recusada",
     "CONFERE WKI TABELAS 2-3 p.14 (arq p.14): so as colunas de 1 a 10"),
    # WKI base citada sem valor.
    ("demanda_residencial_enel.py", "base WKI/Enel",
     "REMISSAO: docstring nomeia a base (WKI/Enel), sem valor"),
    # WKI no caso de validacao (oraculo do teste, nao celula da norma).
    ("validacao_sistema_g15.py", "WKI fator de demanda por modulo",
     "REMISSAO: definicao do caso de validacao (area_servico 1,9 kVA etc. "
     "computados dos modulos); numero do teste, nao da norma"),
    ("validacao_sistema_g15.py", "Eletrica demanda 8.875 kVA (Enel WKI)",
     "REMISSAO: oraculo do teste (8,875 kVA computado), nao celula da "
     "norma; WKI citada como base"),
    # CNC-NDBR-DBR-25-1580 (F128): 75 kW / 7.8.2-7.8.3 (imagem p.25 vista).
    ("eletrica_edificio.py", "Enel CNC-NDBR-DBR-25-1580 7.8.3",
     "CONFERE Enel CNC-NDBR-DBR-25-1580 7.8.2 a/b p.25 (arq p.25): "
     "<= 75 kW em BT, > 75 kW em MT (limites de 7.8.3); numero do GATE "
     "inalterado"),
    ("eletrica_edificio.py", "conexao coletiva BT): ",
     "REMISSAO: referencia do GATE (documento citado, sem valor na frase; "
     "o 75 kW vive no comentario 7.8.3 ja triado)"),
    ("eletrica_edificio.py", "fator_demanda_entre_unidades nao declarado",
     "REMISSAO: aviso declara a fonte do fator (concessionaria), sem valor"),
    ("eletrica_edificio.py", "dado da CONCESSIONARIA (Enel CNC-NDBR-DBR-25-1580,",
     "REMISSAO: comentario declara a fonte (concessionaria, nao NBR 5410), "
     "sem valor"),
    ("entrada_enel_bt.py", "CNC-NDBR-DBR-24-1569-EDBR",
     "REMISSAO: identificador do documento transcrito (Anexos A e C), "
     "sem valor"),
    # IEC 60364: fora do acervo (F148 = 60617, F149 = 60417).
    ("comissionamento_fv.py", "instalado conforme IEC 60364 e",
     "NAO_CONFERIVEL: IEC 60364 fora do acervo (F148 e 60617, F149 e "
     "60417); fica como esta"),
    ("comissionamento_fv.py", "Meios de desconexao devem existir",
     "NAO_CONFERIVEL idem (IEC 60364-7-712 fora do acervo)"),
    ("comissionamento_fv.py", "tensao reversa deve atender",
     "NAO_CONFERIVEL idem (IEC 60364-7-712 fora do acervo)"),
    # NBR 5444/IEC e NBR IEC 60898: pratica/serie citada, sem valor.
    ("desenho_eletrico.py", "NBR 5444/IEC",
     "REMISSAO: pratica citada (simbolos), sem valor"),
    ("desenho_svg_base.py", "NBR 5444/IEC",
     "REMISSAO: pratica citada (simbologia), sem valor"),
    ("protecao_nbr5410.py", "NBR IEC 60898/60947-2) que atenda",
     "REMISSAO: serie comercial citada como input (IB <= IN <= IZ), "
     "sem valor da norma"),
    ("protecao_nbr5410.py", "NBR IEC 60898 / 60947-2), A",
     "REMISSAO idem (correntes nominais de disjuntor, sem valor)"),
    # NBR ISO/CIE 8995-1 (F102): base citada, sem valor na frase.
    ("luminotecnica_nbr8995.py", "NBR 8995-1 / Mamede",
     "REMISSAO: docstring cita a base (norma + livros), sem valor"),
    ("luminotecnica_nbr8995.py", "para a atividade (NBR 8995-1)",
     "REMISSAO: docstring de parametro (E por atividade), sem valor"),
    ("luminotecnica_nbr8995.py", "Base: ABNT NBR ISO/CIE 8995-1",
     "REMISSAO: comentario cita a base, sem valor"),
    ("luminotecnica_nbr8995.py", "por atividade (NBR ISO/CIE 8995-1 / 5413)",
     "REMISSAO: comentario cita a base, sem valor"),
    ("techdraw_eletrico.py", "metodo dos lumens, NBR ISO/CIE 8995-1",
     "REMISSAO: nota da folha cita o metodo, sem valor (placeholders %s)"),
]


def _modulos_fonte():
    return sorted(
        p for p in os.listdir(GALPAO)
        if p.endswith(".py") and os.path.isfile(os.path.join(GALPAO, p))
        and not p.startswith("test_") and not p.startswith("varredura_")
    )


def _candidatos_em_texto(nome, texto):
    """Rende (linha, origem, trecho) para cada frase sem item com valor.

    G160: a mesma lente, agora com PAT_FONTE (NBR + fonte de conta:
    WKI/ENEL por codigo, IEC, ISO/CIE 8995). Nenhuma copia: o corpo e o
    mesmo do G156, so o padrao de fonte alargou.
    """
    achados = []
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return achados
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            v = no.value
            if not PAT_FONTE.search(v) or PAT_ITEM.search(v):
                continue
            sem = PAT_FONTE.sub("", v)
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
                if not PAT_FONTE.search(v) or PAT_ITEM.search(v):
                    continue
                sem = PAT_FONTE.sub("", v)
                sem = re.sub(r"\b(?:19|20)\d{2}\b", "", sem)
                if PAT_VALOR.search(sem):
                    achados.append((tk.start[0], "comentario", v[:220]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return achados


def _citacoes_conta_em_texto(nome, texto):
    """Rende (linha, origem, trecho) para TODA frase que menciona fonte de
    conta nao-NBR (PAT_CONTA), com ou sem item, com ou sem valor.

    G160 (segundo sentido da baseline): as citacoes WKI trazem item e pagina
    e a lente do G156 nunca as viu porque so enxergava NBR. Toda frase de
    conta tem de estar na BASELINE com veredicto (CONFERE/DIVERGE/
    NAO_CONFERIVEL/REMISSAO) - com item ou sem.
    """
    achados = []
    try:
        arvore = ast.parse(texto)
    except SyntaxError:
        return achados
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            v = no.value
            if PAT_CONTA.search(v):
                achados.append((no.lineno, "literal",
                                v.replace("\n", " ")[:220]))
    try:
        toks = tokenize.generate_tokens(io.StringIO(texto).readline)
        for tk in toks:
            if tk.type == tokenize.COMMENT:
                if PAT_CONTA.search(tk.string):
                    achados.append((tk.start[0], "comentario",
                                    tk.string[:220]))
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


def _citacoes_conta():
    """Toda frase de producao que menciona fonte de conta nao-NBR."""
    out = []
    for nome in _modulos_fonte():
        with open(os.path.join(GALPAO, nome), encoding="utf-8",
                  errors="ignore") as fh:
            texto = fh.read()
        for linha, origem, trecho in _citacoes_conta_em_texto(nome, texto):
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


def test_nenhuma_citacao_conta_sem_triagem():
    """G160: toda frase de fonte de conta nao-NBR esta na BASELINE.

    As citacoes WKI trazem item e pagina e a lente do G156 nunca as viu
    (so enxergava NBR). Sentido 1 para conta: frase com WKI/CNC/ET/IEC/
    ISO-CIE 8995 sem marcador na BASELINE reprova, nomeando arquivo:linha
    (tenha ou nao item). Sentido 2 (fantasma) ja vale para todas via
    test_baseline_sem_fantasma.
    """
    base = {}
    for arq, marcador, _ver in BASELINE:
        base.setdefault(arq, []).append(marcador)
    faltando = []
    for nome, linha, origem, trecho in _citacoes_conta():
        ok = any(_cobre(m, trecho) for m in base.get(nome, []))
        if not ok:
            faltando.append("%s:%d [%s]: %r"
                            % (nome, linha, origem, trecho[:120]))
    assert not faltando, (
        "citacao de fonte de conta (WKI/ENEL/IEC/ISO-CIE) sem triagem "
        "(G160):\n" + "\n".join(faltando)
        + "\nTrie contra a imagem da pagina (CONFERE/DIVERGE/NAO_CONFERIVEL/"
        "REMISSAO) e registre na BASELINE. WKI nunca vai para FONTE_NAO_NBR."
    )


def test_conta_injecao_e_padrao_vivo(tmp_path):
    """G160: conta sem triagem reprova (mesmo com item) e o padrao nao e
    filtro morto (casa abreviacao E codigo; nao casa ISO de prancha/data)."""
    lados = []
    # (a) padrao vivo: abreviacao e codigo cheio casam; ISO de prancha,
    # data, "piso"/"aviso" e "piece" nunca casam.
    vivos = ["WKI Enel item 6.1",
             "WKI-OMBR-MAT-18-0263-INBR-R01 item 6.1",
             "Enel CNC-NDBR-DBR-25-1580 7.8.3",
             "CNC-NDBR-DBR-24-1569-EDBR",
             "conforme IEC 60364-7-712",
             "NBR IEC 60898",
             "NBR ISO/CIE 8995-1",
             "metodo dos lumens (NBR 8995-1)"]
    for texto in vivos:
        if not PAT_CONTA.search(texto):
            lados.append("filtro morto: PAT_CONTA nao casa %r" % (texto,))
    mortos = ["pagina A1 (ISO 5457): 841 x 594 mm",
              "timestamp ISO-8601",
              "template ISO A1",
              "peso = 7,0 x t_seg",
              "piece marks por grupo",
              " fulfilled"]
    for texto in mortos:
        if PAT_CONTA.search(texto):
            lados.append("falso-positivo: PAT_CONTA casa %r" % (texto,))
    # (b) injecao Tier A: conta sem item com valor reprova com arquivo:linha.
    sujo_a = ('X = "demanda 2,28 kVA pela WKI sem item"\n')
    ok_a = _candidatos_em_texto("inj_conta_a.py", sujo_a)
    if len(ok_a) != 1 or ok_a[0][0] != 1:
        lados.append("conta sem item com valor nao acusa em arquivo:linha: "
                     "%r" % (ok_a,))
    # (c) injecao Tier B: conta COM item sem triagem reprova na baseline.
    sujo_b = ('X = "demanda pela WKI TABELA 2 (PDF p. 14), 2,28 kVA"\n')
    cont_b = _citacoes_conta_em_texto("inj_conta_b.py", sujo_b)
    base_b = [m for a, m, _v in BASELINE if a == "inj_conta_b.py"]
    if not cont_b:
        lados.append("Tier B nao ve a frase de conta com item: %r" % (sujo_b,))
    elif any(_cobre(m, cont_b[0][2]) for m in base_b):
        lados.append("Tier B cobre frase sem triagem: %r" % (cont_b,))
    # (d) isencao mantida: livro/catalogo continua fora da lente.
    isentos = ['X = "viga por Pfeil, 2,28 kNm"\n',
               'X = "catalogo de perfil, 2,28 kNm"\n']
    for sujo in isentos:
        if _candidatos_em_texto("inj_isento.py", sujo):
            lados.append("isencao livro/catalogo quebrada: %r" % (sujo,))
        if _citacoes_conta_em_texto("inj_isento.py", sujo):
            lados.append("conta alcanca livro/catalogo: %r" % (sujo,))
    assert not lados, "\n".join(lados)
