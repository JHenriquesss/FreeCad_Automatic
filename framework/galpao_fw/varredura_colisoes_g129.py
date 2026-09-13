# ============================================================================
# varredura_colisoes_g129.py - G129: O CENSO DAS COLISOES DE ROTULO.
# SCRIPT AVULSO: ferramenta permanente rodada a mao/CI (python
# varredura_colisoes_g129.py) e pelo teste-guarda
# tests/test_colisoes_censo_g129.py. Nao e importada por nenhum
# orquestrador do Loop - declarada em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de varredura_carimbo_mapa.
#
# O que foi MEDIDO (G125, remedido no G129 sobre a arvore de hoje):
#   - com `desenho_svg_base.colisoes_de_rotulo_svg` sobre as folhas de uma
#     rodada real de casa e predio: 6 de 27 folhas com colisao, 48 pares
#     (`planta-eletrica.svg` 15, `planta-baixa.svg` 8, `telhado-tesoura.svg`
#     8, `quadro-cargas.svg` 7, `detalhes-concreto-casa.svg` 5,
#     `planta-laje-pavimento-tipo.svg` 5). A funcao existe desde o G56 e 11
#     arquivos de teste a usam, cada um para a sua folha - nenhum censo a
#     rodava sobre todas as folhas entregues.
#   - o galpao nao tinha sido medido (a rodada e cara): medido no G129 via
#     o turnkey real do spec persistido (`galpao-tp-g95`, `tk.rodar` puro,
#     sem freecad.exe, ~30 s) + os emissores SVG que alimentam os PDFs do
#     manifesto via `config_de_spec` (convencao 9: a lente parte de onde o
#     dado e PRODUZIDO). 8 fontes, 14 pares (`planta-seguranca` 8,
#     `diagrama-unifilar` 3, `planta-formas` 2, `esquema-hidraulica` 1;
#     climatizacao, quadro-cargas, planta-eletrica e prancha-armacao com 0).
#     O manifesto do galpao entrega PDFs (`*/pranchas/*.pdf`, cobertos pelo
#     G102); o SVG medido aqui e a fonte que o PDF rasteriza (rota G104).
#   - triagem par a par olhando o PNG renderizado (regra 3, via fitz como
#     no G94/G104): 19 colisoes REAIS viraram correcao na folha
#     (`planta-eletrica` 12 etiquetas sobrepostas, `quadro-cargas` 7
#     transbordos de coluna; CORRIGIDOS_G129, PNG re-conferido) e 43
#     pares viraram isencao com motivo (ISENCOES_G129): linhas empilhadas
#     legiveis, entrelinha apertada porem legivel, textos sem text-anchor
#     (start real, o estimador centra a caixa em middle) e um texto
#     rotacionado (o estimador ignora o rotate). Nenhuma isencao sem o PNG
#     conferido: o teste-guarda exige "png" em todo motivo.
#
# Maquina: funcoes puras, sem rodada e sem FreeCAD. `pares_de_svg` embrulha
# o estimador (parse XML, nunca substring) e ordena os pares; a identidade
# do par e a do estimador (prefixo de 24 caracteres). `confere_censo`
# recebe o censo vivo ({folha: [(a, b), ...]}), o baseline e as isencoes e
# devolve pares_novos / pares_sumidos / sem_triagem / isencoes_mortas /
# folhas_novas / folhas_sumidas + OK. O teste-guarda aplica a funcao ao
# censo vivo das tres tipologias (casa+predio via `run_project` no spec
# persistido com `generate_2d`, galpao via `tk.rodar` + emissores) e falha
# UMA vez so, com todos os lados na mensagem (a receita do G97).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - geometria da folha (viewBox, desenho contido): e de
#     `confere_folha_svg` e do censo do G77, nao desta lente;
#   - colisao de rotulo contra SIMBOLO ou linha (o estimador so mede
#     texto x texto): nao-coverture declarada; o PNG da triagem mostra
#     simbolos e linhas, e a correcao F1 os manteve legiveis;
#   - texto rotacionado (o estimador ignora o `rotate` e centra caixa
#     horizontal): o unico caso medido (`90.00 m` na planta de formas do
#     galpao) e isento com esse motivo; rotacao nova em folha com par
#     continua acusando como par novo;
#   - indice x disco (arquivo emitido ou nao): e da lente do G91/G102,
#     nao desta (pares de rotulo, nao promessa x arquivo).
# ============================================================================
"""Varredura G129: censo de colisoes de rotulo sobre as folhas entregues."""

from __future__ import annotations

import desenho_svg_base as sb


#: O universo do censo, por tipologia: toda folha SVG que o manifesto
#: entrega (casa+predio, artefatos `drawings/*.svg` da rodada real) mais
#: toda fonte SVG que alimenta os PDFs do manifesto do galpao (o emissor
#: que o `config_de_spec` da disciplina rasteriza na rota G104). Folha
#: nova sem triagem = vermelho; folha que some sem triagem = vermelho.
FOLHAS_DO_CENSO = {
    "casa": [
        "casa/drawings/armacao-vigas-pilares-casa.svg",
        "casa/drawings/conferencia-nbr5410.svg",
        "casa/drawings/detalhes-concreto-casa.svg",
        "casa/drawings/esquema-hidraulico.svg",
        "casa/drawings/fundacao-locacao-formas-casa.svg",
        "casa/drawings/planta-baixa.svg",
        "casa/drawings/planta-eletrica.svg",
        "casa/drawings/planta-formas.svg",
        "casa/drawings/quadro-ambientes.svg",
        "casa/drawings/quadro-cargas.svg",
        "casa/drawings/telhado-tesoura.svg",
        "casa/drawings/unifilar.svg",
    ],
    "predio": [
        "predio/drawings/armacao-vigas-pavimento-tipo.svg",
        "predio/drawings/coordenacao-federado.svg",
        "predio/drawings/eletrica-infra-aterramento.svg",
        "predio/drawings/eletrica-planta-pavimento-tipo.svg",
        "predio/drawings/eletrica-qdc-quadros.svg",
        "predio/drawings/eletrica-unifilar-prumada.svg",
        "predio/drawings/fundacao-locacao-formas.svg",
        "predio/drawings/hidraulica-agua-fria.svg",
        "predio/drawings/hidraulica-esgoto-ventilacao.svg",
        "predio/drawings/hidraulica-pluvial.svg",
        "predio/drawings/incendio-detalhes-hidrantes-rotas.svg",
        "predio/drawings/incendio-escada-planta-corte.svg",
        "predio/drawings/incendio-ppci-pavimento-tipo.svg",
        "predio/drawings/planta-formas-pavimento-tipo.svg",
        "predio/drawings/planta-laje-pavimento-tipo.svg",
    ],
    "galpao": [
        "galpao/diagrama-unifilar.svg",
        "galpao/esquema-climatizacao.svg",
        "galpao/esquema-hidraulica.svg",
        "galpao/planta-eletrica.svg",
        "galpao/planta-formas.svg",
        "galpao/planta-seguranca.svg",
        "galpao/prancha-armacao.svg",
        "galpao/quadro-cargas.svg",
    ],
}


#: Baseline congelado nos dois sentidos (medido 2026-09-13, pos-correcao
#: F1/F2): so folhas com pares vivos; folha limpa nao entra aqui (o
#: universo acima ja a prende: par novo em folha limpa = vermelho). Par
#: novo = vermelho; par que some sem triagem = vermelho.
BASELINE_G129 = {
    "casa/drawings/detalhes-concreto-casa.svg": [
        ("Cortante 19.4.1", "V_Sd 7.9 / V_Rd1 43.2 kN"),
        ("Fissuracao ELS-W", "wk 0.062 / 0.3 mm -> ATE"),
        ("Flecha total", "1.8 mm / limite 14.0 mm "),
        ("Momentos Md (kN.m/m)", "m_x 2.70 | m_y 2.16 | X_"),
        ("Reacoes (kN/m)", "x0 5.6 ; x1 3.2 ; y0 5.0"),
    ],
    "casa/drawings/planta-baixa.svg": [
        ("2.40 x 1.50 m", "area 3.60 m2"),
        ("3.00 x 2.00 m", "area 6.00 m2"),
        ("3.00 x 3.00 m", "area 9.00 m2"),
        ("3.50 x 3.00 m", "area 10.50 m2"),
        ("3.60 x 2.50 m", "area 9.00 m2"),
        ("4.00 x 1.00 m", "area 4.00 m2"),
        ("5.00 x 4.00 m", "area 20.00 m2"),
        ("Circulacao", "4.00 x 1.00 m"),
    ],
    "casa/drawings/planta-eletrica.svg": [
        ("(esquem\u00e1tica: N\u00c3O \u00e9 tra\u00e7", "de eletroduto)"),
        ("Area de servico", "3.00 x 2.00 m"),
        ("Cozinha", "3.60 x 2.50 m"),
    ],
    "casa/drawings/telhado-tesoura.svg": [
        ("contraventamento 6.6: F1", "L/tesoura (m)"),
        ("contraventamento 6.6: F1", "Peca"),
        ("contraventamento 6.6: F1", "Secao (cm)"),
        ("contraventamento 6.6: F1", "Situacao"),
        ("contraventamento 6.6: F1", "Volume total (m3)"),
        ("contraventamento 6.6: F1", "ligacao chapa_aco: ATEND"),
        ("sem vento declarado: cad", "ligacao chapa_aco: ATEND"),
        ("vao 8.00 m ; 6 tesouras ", "sem vento declarado: cad"),
    ],
    "predio/drawings/planta-laje-pavimento-tipo.svg": [
        ("Cortante 19.4.1", "V_Sd 11.0 / V_Rd1 50.1 k"),
        ("Fissuracao ELS-W", "wk 0.076 / 0.3 mm -> ATE"),
        ("Flecha total", "4.6 mm / limite 18.0 mm "),
        ("Momentos Md (kN.m/m)", "m_x 4.75 | m_y 3.98 | X_"),
        ("Reacoes (kN/m)", "x0 7.8 ; x1 4.5 ; y0 7.1"),
    ],
    "galpao/diagrama-unifilar.svg": [
        ("BANCO CAP.", "16 kVAr"),
        ("iluminacao", "20 kW"),
        ("motores", "94 kW"),
    ],
    "galpao/esquema-hidraulica.svg": [
        ("90 m", "Calha DN150"),
    ],
    "galpao/planta-formas.svg": [
        ("4", "90.00 m"),
        ("PLANTA DE FORMAS - GALPA", "vao 20.0 x comp 90.0 m ;"),
    ],
    "galpao/planta-seguranca.svg": [
        ("Acionadores: 2", "Placas de rota: 7"),
        ("Aclaramento: 18 pts", "Balizamento: 16 pts"),
        ("Balizamento: 16 pts", "Chuveiros: 328 (ordinari"),
        ("Chuveiros: 328 (ordinari", "Reserva chuv.: 192 m3"),
        ("Detectores: 49 (pontual)", "Acionadores: 2"),
        ("Hidrantes: 12 (tipo 2)", "Reserva hidr.: 36 m3"),
        ("Placas de rota: 7", "Aclaramento: 18 pts"),
        ("Reserva chuv.: 192 m3", "Hidrantes: 12 (tipo 2)"),
    ],
}


def _motivo_verificacoes(png):
    return ("FP G129: textos do bloco VERIFICACOES sem text-anchor (start "
            "real no SVG); o estimador centra a caixa (middle) e superestima "
            "a largura (0,6*size) - colunas rotulo+valor com vao livre e "
            "legiveis no PNG %s. Nenhuma isencao sem o PNG conferido."
            % png)


def _motivo_empilhadas(png, onde):
    return ("FP G129: %s em linhas empilhadas, legiveis no PNG %s; o "
            "estimador usa caixa 1,1*size de altura e acusa o empilhamento. "
            "Nenhuma isencao sem o PNG conferido." % (onde, png))


#: Cada par vivo triado olhando o PNG, com o motivo escrito. Motivo em
#: branco = silencio, nao triagem. Isencao de par que sumiu (nome morto)
#: reprova - a correcao que apaga par sai em CORRIGIDOS_G129, nunca aqui.
ISENCOES_G129 = {
    "casa/drawings/detalhes-concreto-casa.svg": {
        ("Cortante 19.4.1", "V_Sd 7.9 / V_Rd1 43.2 kN"):
            _motivo_verificacoes("casa-detalhes-concreto-casa.png"),
        ("Fissuracao ELS-W", "wk 0.062 / 0.3 mm -> ATE"):
            _motivo_verificacoes("casa-detalhes-concreto-casa.png"),
        ("Flecha total", "1.8 mm / limite 14.0 mm "):
            _motivo_verificacoes("casa-detalhes-concreto-casa.png"),
        ("Momentos Md (kN.m/m)", "m_x 2.70 | m_y 2.16 | X_"):
            _motivo_verificacoes("casa-detalhes-concreto-casa.png"),
        ("Reacoes (kN/m)", "x0 5.6 ; x1 3.2 ; y0 5.0"):
            _motivo_verificacoes("casa-detalhes-concreto-casa.png"),
    },
    "casa/drawings/planta-baixa.svg": {
        ("2.40 x 1.50 m", "area 3.60 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco do Banheiro"),
        ("3.00 x 2.00 m", "area 6.00 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco da Area de servico"),
        ("3.00 x 3.00 m", "area 9.00 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco do Dormitorio 02"),
        ("3.50 x 3.00 m", "area 10.50 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco do Dormitorio 01"),
        ("3.60 x 2.50 m", "area 9.00 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco da Cozinha"),
        ("4.00 x 1.00 m", "area 4.00 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco da Circulacao"),
        ("5.00 x 4.00 m", "area 20.00 m2"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "dimensao e area no bloco da Sala"),
        ("Circulacao", "4.00 x 1.00 m"):
            _motivo_empilhadas("casa-planta-baixa.png",
                               "nome e dimensao no bloco da Circulacao"),
    },
    "casa/drawings/planta-eletrica.svg": {
        ("(esquem\u00e1tica: N\u00c3O \u00e9 tra\u00e7", "de eletroduto)"):
            _motivo_empilhadas("posfix-planta-eletrica.png",
                               "nota da legenda em 2 linhas"),
        ("Area de servico", "3.00 x 2.00 m"):
            _motivo_empilhadas("posfix-planta-eletrica.png",
                               "nome e dimensao no bloco da Area de servico"),
        ("Cozinha", "3.60 x 2.50 m"):
            _motivo_empilhadas("posfix-planta-eletrica.png",
                               "nome e dimensao no bloco da Cozinha"),
    },
    "casa/drawings/telhado-tesoura.svg": {
        ("contraventamento 6.6: F1", "L/tesoura (m)"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linha do contraventamento e cabecalho L/tesoura"),
        ("contraventamento 6.6: F1", "Peca"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linha do contraventamento e cabecalho Peca"),
        ("contraventamento 6.6: F1", "Secao (cm)"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linha do contraventamento e cabecalho Secao"),
        ("contraventamento 6.6: F1", "Situacao"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linha do contraventamento e cabecalho Situacao"),
        ("contraventamento 6.6: F1", "Volume total (m3)"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linha do contraventamento e cabecalho Volume"),
        ("contraventamento 6.6: F1", "ligacao chapa_aco: ATEND"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linhas do bloco (ligacao x contraventamento)"),
        ("sem vento declarado: cad", "ligacao chapa_aco: ATEND"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linhas do bloco (sem-vento x ligacao)"),
        ("vao 8.00 m ; 6 tesouras ", "sem vento declarado: cad"):
            _motivo_empilhadas("casa-telhado-tesoura.png",
                               "linhas do bloco (vao x sem-vento)"),
    },
    "predio/drawings/planta-laje-pavimento-tipo.svg": {
        ("Cortante 19.4.1", "V_Sd 11.0 / V_Rd1 50.1 k"):
            _motivo_verificacoes("predio-planta-laje-pavimento-tipo.png"),
        ("Fissuracao ELS-W", "wk 0.076 / 0.3 mm -> ATE"):
            _motivo_verificacoes("predio-planta-laje-pavimento-tipo.png"),
        ("Flecha total", "4.6 mm / limite 18.0 mm "):
            _motivo_verificacoes("predio-planta-laje-pavimento-tipo.png"),
        ("Momentos Md (kN.m/m)", "m_x 4.75 | m_y 3.98 | X_"):
            _motivo_verificacoes("predio-planta-laje-pavimento-tipo.png"),
        ("Reacoes (kN/m)", "x0 7.8 ; x1 4.5 ; y0 7.1"):
            _motivo_verificacoes("predio-planta-laje-pavimento-tipo.png"),
    },
    "galpao/diagrama-unifilar.svg": {
        ("BANCO CAP.", "16 kVAr"):
            _motivo_empilhadas("galpao-diagrama-unifilar.png",
                               "rotulo e valor sob o banco de capacitores"),
        ("iluminacao", "20 kW"):
            _motivo_empilhadas("galpao-diagrama-unifilar.png",
                               "rotulo e valor sob a iluminacao"),
        ("motores", "94 kW"):
            _motivo_empilhadas("galpao-diagrama-unifilar.png",
                               "rotulo e valor sob os motores"),
    },
    "galpao/esquema-hidraulica.svg": {
        ("90 m", "Calha DN150"):
            _motivo_empilhadas("galpao-esquema-hidraulica.png",
                               "nome da calha sobre o comprimento"),
    },
    "galpao/planta-formas.svg": {
        ("4", "90.00 m"):
            ("FP G129: '90.00 m' e texto rotacionado (rotate -90, cota "
             "vertical); o estimador ignora a rotacao e centra caixa "
             "horizontal - no PNG galpao-planta-formas.png o numero do "
             "portico e a cota estao separados. Nenhuma isencao sem o PNG "
             "conferido."),
        ("PLANTA DE FORMAS - GALPA", "vao 20.0 x comp 90.0 m ;"):
            _motivo_empilhadas("galpao-planta-formas.png",
                               "titulo e subtitulo da folha"),
    },
    "galpao/planta-seguranca.svg": {
        ("Acionadores: 2", "Placas de rota: 7"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (acionadores x placas)"),
        ("Aclaramento: 18 pts", "Balizamento: 16 pts"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (aclaramento x balizamento)"),
        ("Balizamento: 16 pts", "Chuveiros: 328 (ordinari"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (balizamento x chuveiros)"),
        ("Chuveiros: 328 (ordinari", "Reserva chuv.: 192 m3"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (chuveiros x reserva)"),
        ("Detectores: 49 (pontual)", "Acionadores: 2"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (detectores x acionadores)"),
        ("Hidrantes: 12 (tipo 2)", "Reserva hidr.: 36 m3"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (hidrantes x reserva hidr.)"),
        ("Placas de rota: 7", "Aclaramento: 18 pts"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (placas x aclaramento)"),
        ("Reserva chuv.: 192 m3", "Hidrantes: 12 (tipo 2)"):
            _motivo_empilhadas("galpao-planta-seguranca.png",
                               "linhas do RESUMO (reserva chuv. x hidrantes)"),
    },
}


#: Colisoes REAIS que viraram correcao na folha (pares que sumiram do
#: censo COM triagem). Cada entrada nomeia a folha, os pares de antes, a
#: correcao e o PNG re-conferido. Par daqui que voltar ao censo = par
#: novo = vermelho (a correcao perdeu o efeito).
CORRIGIDOS_G129 = [
    {
        "folha": "casa/drawings/planta-eletrica.svg",
        "pares": [
            ("L-AS", "T-AS-02"),
            ("L-BAN", "T-BAN-01"),
            ("L-BAN", "TUE-CHUV"),
            ("L-CIRC", "QD-01"),
            ("L-CIRC", "T-CIRC-01"),
            ("L-COZ", "T-COZ-02"),
            ("L-COZ", "T-COZ-03"),
            ("L-DOR1", "T-DOR1-02"),
            ("L-DOR2", "T-DOR2-02"),
            ("L-SALA", "T-SALA-02"),
            ("T-BAN-01", "TUE-CHUV"),
            ("T-CIRC-01", "QD-01"),
        ],
        "correcao": ("desenho_eletrico_residencial."
                     "planta_eletrica_residencial_svg: a etiqueta tenta 10 "
                     "deslocamentos fixos, em ordem, e fica no primeiro que "
                     "nao encosta em rotulo de comodo, no quadro nem em "
                     "etiqueta ja posta (regua do G129); censo 15 -> 3"),
        "png": ("PNG posfix-planta-eletrica.png re-conferido: etiquetas L-* "
                "acima e T-* abaixo dos simbolos, todas legiveis"),
    },
    {
        "folha": "casa/drawings/quadro-cargas.svg",
        "pares": [
            ("Area de servico, Banheir", "10 A"),
            ("Area de servico, Banheir", "2.5 mm\u00b2"),
            ("Area de servico, Banheir", "7.40"),
            ("Area de servico, Banheir", "940 VA"),
            ("Area de servico, Banheir", "Ilumina\u00e7\u00e3o"),
            ("Circulacao, Dormitorio 0", "1100 VA"),
            ("Circulacao, Dormitorio 0", "TUG"),
        ],
        "correcao": ("desenho_eletrico_residencial."
                     "quadro_cargas_residencial_svg: a celula quebra em "
                     "linhas que cabem na coluna (_quebra_celula, item com "
                     "virgula fica inteiro) e a altura da linha acompanha a "
                     "celula mais alta; censo 7 -> 0"),
        "png": ("PNG posfix-quadro-cargas.png re-conferido: C1/C5 com COMODO "
                "em varias linhas dentro da coluna, demais colunas legiveis"),
    },
]


def chaves_do_censo():
    """Todas as 35 chaves do universo, ordenadas."""
    return sorted(chave for folhas in FOLHAS_DO_CENSO.values()
                  for chave in folhas)


def pares_de_svg(svg):
    """Pares de rotulos que se sobrepoem no SVG, ordenados.

    Pura: parse XML via o estimador (nunca substring). SVG malformado
    vira [("svg-malformado", "")] - o sentinela de 1-tupla do estimador
    vira par acusador (nunca consta do baseline, logo e par novo e o
    portao fica vermelho); o instrumento acusa, nunca passa em silencio.
    Entrada nao-str levanta TypeError.
    """
    if not isinstance(svg, str):
        raise TypeError("svg tem de ser str")
    saida = []
    for par in sb.colisoes_de_rotulo_svg(svg):
        if isinstance(par, (tuple, list)) and len(par) == 1:
            saida.append((str(par[0]), ""))
        else:
            a, b = par
            saida.append((str(a), str(b)))
    return sorted(saida)


def _pares_norm(pares):
    if pares is None:
        raise TypeError("pares nao pode ser None")
    norm = []
    for par in pares:
        try:
            a, b = par
        except (TypeError, ValueError):
            raise TypeError("par tem de ser (a, b): %r" % (par,))
        norm.append((str(a), str(b)))
    return sorted(norm)


def _isencoes_validas(isencoes):
    """Pares com motivo escrito (texto nao vazio apos strip).

    Motivo apagado/em branco e silencio, nao triagem - a mesma regra que
    derrubou o G77 (molde de _isencoes_validas do G103). Entrada vazia/
    None = nenhuma isencao, nunca erro; nao-dict levanta TypeError.
    """
    if not isencoes:
        return {}
    if not isinstance(isencoes, dict):
        raise TypeError("isencoes tem de ser dict folha->{par: motivo}")
    validas = {}
    for folha, pares in isencoes.items():
        if not isinstance(pares, dict):
            raise TypeError("isencao da folha %r tem de ser dict par->motivo"
                            % (folha,))
        for par, motivo in pares.items():
            a, b = _pares_norm([par])[0]
            if str(motivo or "").strip():
                validas.setdefault(str(folha), {})[(a, b)] = motivo
    return validas


def confere_censo(atual, baseline=None, isencoes=None):
    """Confronta o censo vivo com o baseline e as isencoes, nos dois sentidos.

    atual: {folha: [(a, b), ...]} (o censo vivo das 35 folhas).
    baseline: {folha: [(a, b), ...]} (default BASELINE_G129, fonte unica).
    isencoes: {folha: {(a, b): motivo}} (default ISENCOES_G129).

    Devolve {"OK", "pares_novos", "pares_sumidos", "sem_triagem",
      "isencoes_mortas", "folhas_novas", "folhas_sumidas"}:
      - pares_novos: {folha: [pares]} vivos fora do baseline (par novo =
        vermelho, inclusive em folha limpa);
      - pares_sumidos: {folha: [pares]} do baseline fora do vivo (par que
        some sem triagem = vermelho; a correcao que apaga par sai em
        CORRIGIDOS_G129 e no baseline junto, nunca em silencio);
      - sem_triagem: pares vivos sem motivo escrito;
      - isencoes_mortas: motivos de pares que nao estao mais vivos;
      - folhas_novas / folhas_sumidas: chaves fora do universo FOLHAS_DO_
        CENSO, nos dois sentidos;
      - OK: tudo vazio (a lente nao enfraquece: sem isencoes o censo com
        43 pares reprova como antes).
    Entrada malformada (None ou nao-dict) levanta TypeError: lente que
    devolve OK sobre lixo e saturacao silenciosa.
    """
    if atual is None:
        raise TypeError("atual nao pode ser None")
    if not isinstance(atual, dict):
        raise TypeError("atual tem de ser dict folha->[pares]")
    if baseline is None:
        baseline = BASELINE_G129
    if not isinstance(baseline, dict):
        raise TypeError("baseline tem de ser dict folha->[pares]")
    universo = set(chaves_do_censo())
    vivo = {str(folha): _pares_norm(pares) for folha, pares in atual.items()}
    base = {str(folha): _pares_norm(pares)
            for folha, pares in baseline.items()}
    validas = _isencoes_validas(isencoes if isencoes is not None
                                else ISENCOES_G129)
    pares_novos = {}
    for folha in sorted(vivo):
        novos = [p for p in vivo[folha] if p not in base.get(folha, [])]
        if novos:
            pares_novos[folha] = novos
    pares_sumidos = {}
    for folha in sorted(base):
        sumidos = [p for p in base[folha] if p not in vivo.get(folha, [])]
        if sumidos:
            pares_sumidos[folha] = sumidos
    sem_triagem = {}
    for folha in sorted(vivo):
        motivos = validas.get(folha, {})
        faltam = [p for p in vivo[folha] if p not in motivos]
        if faltam:
            sem_triagem[folha] = faltam
    isencoes_mortas = {}
    for folha in sorted(validas):
        mortas = [p for p in validas[folha] if p not in vivo.get(folha, [])]
        if mortas:
            isencoes_mortas[folha] = mortas
    folhas_novas = sorted(set(vivo) - universo)
    folhas_sumidas = sorted(universo - set(vivo))
    return {"OK": not (pares_novos or pares_sumidos or sem_triagem
                       or isencoes_mortas or folhas_novas or folhas_sumidas),
            "pares_novos": pares_novos,
            "pares_sumidos": pares_sumidos,
            "sem_triagem": sem_triagem,
            "isencoes_mortas": isencoes_mortas,
            "folhas_novas": folhas_novas,
            "folhas_sumidas": folhas_sumidas}


def relatorio_pt(res):
    """Uma mensagem so com todos os lados (receita do G97)."""
    linhas = ["VARREDURA G129 - CENSO DE COLISOES DE ROTULO"]
    for rotulo in ("pares_novos", "pares_sumidos", "sem_triagem",
                   "isencoes_mortas"):
        bloco = res.get(rotulo) or {}
        total = sum(len(v) for v in bloco.values())
        linhas.append("  %-15s %d pares em %d folhas"
                      % (rotulo, total, len(bloco)))
        for folha in sorted(bloco):
            for par in bloco[folha][:12]:
                linhas.append("    %-15s %-38s %s x %s"
                              % (rotulo, folha, par[0], par[1]))
            if len(bloco[folha]) > 12:
                linhas.append("    ... mais %d pares em %s"
                              % (len(bloco[folha]) - 12, folha))
    for rotulo in ("folhas_novas", "folhas_sumidas"):
        bloco = res.get(rotulo) or []
        linhas.append("  %-15s %d: %s" % (rotulo, len(bloco), bloco))
    linhas.append("  OK=%s" % res.get("OK"))
    return "\n".join(linhas)


def _selftest():
    vazio = {chave: [] for chave in chaves_do_censo()}

    def com(base, folha, pares):
        copia = {k: list(v) for k, v in base.items()}
        copia[folha] = [tuple(p) for p in pares]
        return copia

    f1 = "casa/drawings/unifilar.svg"
    base_um = com(vazio, f1, [("a", "b")])
    bom = confere_censo(base_um, base_um, {f1: {("a", "b"): "visto no PNG x.png"}})
    assert bom["OK"] and bom["pares_novos"] == {} \
        and bom["pares_sumidos"] == {}, bom
    # par novo (inclusive em folha limpa) = vermelho; caso bom verde
    novo = confere_censo(com(vazio, f1, [("a", "c")]),
                         {k: list(v) for k, v in vazio.items()}, {})
    assert novo["pares_novos"] == {f1: [("a", "c")]} \
        and not novo["OK"], novo
    limpo = confere_censo({k: list(v) for k, v in vazio.items()},
                          {k: list(v) for k, v in vazio.items()}, {})
    assert limpo["OK"], limpo
    # par que some sem triagem = vermelho (e a isencao vira morta)
    sumido = confere_censo({k: list(v) for k, v in vazio.items()}, base_um,
                           {f1: {("a", "b"): "motivo PNG x.png"}})
    assert sumido["pares_sumidos"] == {f1: [("a", "b")]} \
        and sumido["isencoes_mortas"] == {f1: [("a", "b")]} \
        and not sumido["OK"], sumido
    # motivo em branco e silencio, nao triagem
    apagada = confere_censo(base_um, base_um, {f1: {("a", "b"): "   "}})
    assert apagada["sem_triagem"] == {f1: [("a", "b")]} \
        and not apagada["OK"], apagada
    # par vivo sem motivo = sem_triagem
    sem = confere_censo(base_um, base_um, {})
    assert sem["sem_triagem"] == {f1: [("a", "b")]} \
        and not sem["OK"], sem
    # folha fora do universo = folha nova; folha do universo ausente = sumida
    extra = dict(base_um)
    extra["folha-fantasma.svg"] = [("a", "b")]
    fora = confere_censo(extra, base_um,
                         {f1: {("a", "b"): "motivo PNG x.png"}})
    assert fora["folhas_novas"] == ["folha-fantasma.svg"] \
        and not fora["OK"], fora
    furado = {k: v for k, v in base_um.items() if k != f1}
    falta = confere_censo(furado, base_um,
                          {f1: {("a", "b"): "motivo PNG x.png"}})
    assert falta["folhas_sumidas"] == [f1] \
        and falta["pares_sumidos"] == {f1: [("a", "b")]} \
        and not falta["OK"], falta
    # svg malformado acusa em vez de passar (instrumento que acusa)
    mal = pares_de_svg("<svg><text")
    assert mal == [("svg-malformado", "")], mal
    # malformada grita
    for ruim in (None, ["f1"]):
        try:
            confere_censo(ruim)
            raise AssertionError("atual %r devia levantar" % (ruim,))
        except TypeError:
            pass
    try:
        pares_de_svg(None)
        raise AssertionError("svg None devia levantar")
    except TypeError:
        pass
    try:
        confere_censo({"f1": [("a",)]})
        raise AssertionError("par unitario devia levantar")
    except TypeError:
        pass
    # baseline e isencoes fecham entre si: todo par do baseline tem motivo
    # com PNG, nenhum motivo morto, nenhum corrigido vivo por construcao
    base = {f: sorted(ps) for f, ps in BASELINE_G129.items()}
    assert sum(len(v) for v in base.values()) == 43, \
        sum(len(v) for v in base.values())
    assert set(ISENCOES_G129) == set(BASELINE_G129), \
        (set(ISENCOES_G129) ^ set(BASELINE_G129))
    for folha, pares in BASELINE_G129.items():
        assert sorted(pares) == sorted(ISENCOES_G129[folha]), folha
        for par in pares:
            motivo = ISENCOES_G129[folha][par]
            assert str(motivo or "").strip() and "png" in str(motivo).lower(), \
                (folha, par)
    assert len(chaves_do_censo()) == 35, len(chaves_do_censo())
    for entrada in CORRIGIDOS_G129:
        assert str(entrada.get("folha") or "").strip()
        assert entrada.get("pares") and all(len(p) == 2 for p in
                                            entrada["pares"])
        assert str(entrada.get("correcao") or "").strip()
        assert "png" in str(entrada.get("png") or "").lower(), entrada
    sec = relatorio_pt(confere_censo(
        com(vazio, f1, [("a", "b")]),
        {k: list(v) for k, v in vazio.items()}, {}))
    assert "pares_novos" in sec and "OK=False" in sec, sec
    return True


if __name__ == "__main__":
    _selftest()
    vazio = {chave: [] for chave in chaves_do_censo()}
    vazio["casa/drawings/unifilar.svg"] = [("rotulo A", "rotulo B")]
    demo = confere_censo(vazio, {k: [] for k in chaves_do_censo()}, {})
    print(relatorio_pt(demo))
    print("selftest OK")
