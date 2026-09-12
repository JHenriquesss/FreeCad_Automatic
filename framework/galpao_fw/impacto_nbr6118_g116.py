# ============================================================================
# impacto_nbr6118_g116.py - G116: O IMPACTO DE MIGRAR A NBR 6118 DE 2014
# PARA 2023 + EMENDA 1. MEDE E ESCREVE - NAO MUDA CALCULO.
# SCRIPT AVULSO + MODULO DE PRODUCAO: as tabelas canonicas moram aqui; a
# lente e o teste importam de ca. (Uma fonte so - regra do lote G114-G118.)
# Rodado a mao/CI (python impacto_nbr6118_g116.py) e pelo teste-guarda
# tests/test_impacto_nbr6118_g116.py. Nao e importado por nenhum
# orquestrador do Loop - declarado em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de f150_decodifica.
#
# O que foi MEDIDO (enderecos verificados nesta entrega):
#   - F098 = fontes/01_CONCRETO/CONCRETO__NBR__NBR-6118-2023-EM1-2026__emenda-1.pdf
#     (1117122 bytes, 23 pags, texto legivel): 85 cabecalhos de instrucao
#     (Substituir/Incluir/Excluir), agrupados nestes 51 itens por clausula-alvo
#     (regra de agrupamento escrita em ITENS_EM1 e congelada em CAB_PARA_ITEM;
#     o G113 contou 51 itens e 62 instrucoes - a diferenca e metodo de contagem,
#     nao cobertura: o portao confere os 85 cabecalhos um a um por substring,
#     de modo que qualquer contagem esta coberta; ver D141).
#   - F016 = fontes/01_CONCRETO/...-2014__...-historica.pdf (texto extraivel,
#     PyMuPDF) e F150 decodificada pelo G117
#     (...-projeto-estruturas-concreto-dec.txt, 639707 bytes): 2014 = 2023
#     pre-Em1 em TODAS as clausulas de intersecao sondadas (13.2.5.1-b,
#     15.8.1, 17.3.5.2.4, 17.4.1.1.3, 19.5.4, 20.1) - exceto a 15.7.3, cujo
#     paragrafo do galpao NAO existe em 2014 e JA existe na 2023 (novidade da
#     edicao 2023, fora da Emenda; a Em1 so o reescreve). O restante do
#     2014 -> 2023 fora da Emenda NAO foi comparado: lacuna declarada, nunca
#     default silencioso.
#   - FAMILIAS_FW: clausulas citadas pelos modulos de producao (grep "6118"
#     + "17.3"/"15.8" em 275 linhas, consolidado por familia; linhas exatas
#     arquivo:linha moram no inventario wiki, que e retrato datado - a lente
#     viva confere cobertura por familia, porque linha deriva a cada commit).
#   - Simbolos de formula (lambda, <=, gama, phi) NAO saem do texto corrido
#     (limite do G117): vereditos sobre numero citado em prosa valem; miolo
#     simbolico = ver pagina renderizada (regra 3).
#
# Maquina: cobre_inventario(texto) e o portao - cada cabecalho Em1 e cada
# familia FW precisa aparecer no texto do inventario; o OK por item chega ao
# veredito global (contra a saturacao silenciosa do G113). casos_efeito
# chama as funcoes REAIS (compatibilizacao, puncao, pilar, premoldado) com o
# mesmo caso nas duas regras - sem alterar nenhum modulo; a lente nao
# reimplementa formula do framework (contra assercao tautologica): o numero
# 2014 vem da funcao real, o numero 2023+Em1 e a prescricao literal da Emenda.
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - diferencas 2014 -> 2023 fora da Emenda (exceto a 15.7.3 acima);
#   - figuras e tabelas substituidas (Fig 11.1, 15.3, 18.2, 18.4 nova, 20.1,
#     22.5, 22.7, Tab 13.3/13.4 no miolo grafico): so a prosa ao redor entra;
#   - migracao propriamente dita (trocar a base de nenhum modulo - decisao do
#     usuario, com este numero na mao).
# ============================================================================
"""Impacto G116: NBR 6118 2014 -> 2023 + Emenda 1. Mede e escreve."""

from __future__ import annotations

import pathlib

GALPAO = pathlib.Path(__file__).resolve().parent

# Vereditos por item (classes disjuntas, definidas no inventario wiki):
#   NUMERO-MUDA .... a Emenda muda numero que o framework aplica;
#   REGRA-MUDA ..... muda detalhamento/processo sem trocar numero aplicado;
#   EDITORIAL ...... so redacao (ex.: "centro de gravidade" -> "centroide");
#   FIGURA ......... figura/tabela substituida: exige leitura renderizada;
#   PROCESSO-NOVO .. requisito novo fora do escopo do framework (ex.: ATP);
#   SEM-REFLEXO .... o framework nao implementa o ponto tocado (dito onde).
#
# Cada item: (id, refs_da_emenda, o_que_muda, framework, veredito, detalhe).
# "refs_da_emenda" lista os cabecalhos "Pagina ..." da F098 que o item cobre;
# "framework" lista (modulo, clausula) ou () quando ninguem implementa.
ITENS_EM1 = (
    ("prefacio-xvi", ("Pagina xvi, Prefacio",),
     "NBR 6118:2026 nao se aplica a protocolados antes + 180 dias (usar 2023).",
     (), "PROCESSO-NOVO",
     "Vigencia/transicao: nenhum modulo versiona a norma aplicada; declarar no memorial."),
    ("secao-2", ("Pagina 2, Secao 2",),
     "Exclui NBR 8965 e NBR ISO 7438 das referencias.",
     (), "SEM-REFLEXO", "Framework nao cita nenhuma das duas."),
    ("5.1.2.3", ("Pagina 13, 5.1.2.3",),
     "Durabilidade: resistir as influencias previstas por autor + contratante.",
     (), "SEM-REFLEXO", "Conceitual; nenhum gate implementa 5.1."),
    ("5.2.1", ("Pagina 13, 5.2.1",),
     "Solucao estrutural atende qualidade das normas aplicaveis.",
     (), "SEM-REFLEXO", "Conceitual; sem gate."),
    ("5.3-atp", ("Pagina 14, 5.3",),
     "NOVO 5.3.1-5.3.10 + Tabela 5.1 (CC1/CC2/CC3): avaliacao tecnica de "
     "projeto obrigatoria (CC3 com modelo independente), parecer integra o projeto.",
     (), "PROCESSO-NOVO",
     "Maior novidade de processo da Emenda; framework nao emite ATP nem classifica "
     "CC. Nao e numero de calculo: migrar exige criar o entregavel, nao trocar conta."),
    ("6.2.2", ("Pagina 15, 6.2.2",),
     "Vida util aplica-se ao todo ou as partes (apoios, juntas).",
     (), "SEM-REFLEXO", "Sem gate de vida util no framework."),
    ("6.2.4", ("Pagina 15, 6.2",),
     "NOVO 6.2.4: procedimentos e requisitos consideram vida util de 50 anos.",
     (), "SEM-REFLEXO", "Nenhum modulo assume vida util explicitamente."),
    ("6.3.2.4", ("Pagina 15, 6.3.2",),
     "NOVO 6.3.2.4: etringita tardia (65 C, sulfatos/alcalis/umidade).",
     (), "SEM-REFLEXO", "Durabilidade de material; sem gate."),
    ("8.1", ("Pagina 22, 8.1 Eci", "Pagina 22, 8.1 Eci28",),
     "Eci passa a modulo cordal aos 28 dias (NBR 8522-1); definicao Eci28 excluida.",
     (("fissuracao_nbr6118", "8.2.8"), ("perdas_protensao_nbr6118", "8.2.8"),
      ("piso_industrial", "8.2.8")),
     "SEM-REFLEXO",
     "Framework calcula Eci pela formula de 8.2.8 e nunca referencia Eci28/Ec28 "
     "(grep vazio); A.2 troca Ec28 -> Eci no mesmo sentido."),
    ("8.2.11", ("Pagina 28, 8.2.11",),
     "Fluencia/retracao precisas: Anexo A e 11.3.3.2.",
     (("perdas_protensao_nbr6118", "Tab.A.1"),), "SEM-REFLEXO",
     "Remissivo; o modulo usa valores tipicos Tab.A.1 declarados, sem citar 8.2.11."),
    ("8.3.1", ("Pagina 28, 8.3.1",),
     "Armaduras: CA-25/50/60 conforme NBR 7480.",
     (), "SEM-REFLEXO",
     "Framework assume CA-50/60 nos calculos sem gate de categoria."),
    ("8.3.7-8.4.6", ("Pagina 30, 8.3.7", "Pagina 31, 8.4.6",),
     "Excluidos os 2os paragrafos de 8.3.7 e 8.4.6 (teor na 2023, F150 p.30/31).",
     (), "SEM-REFLEXO", "Nenhum modulo cita 8.3.7 ou 8.4.6."),
    ("9.2.1", ("Pagina 34, 9.2.1",),
     "Aderencia/ancoragem/emendas: remete condicoes as Secoes 7, 18, 21, 22.",
     (("base_chumbador", "9.4.2"), ("fundacao_sapata", "9.4"),
      ("estaca_profunda", "9.3.2/9.4.2")),
     "SEM-REFLEXO", "Remissivo; os gates implementam 9.4.2, intocado."),
    ("9.5.2", ("Pagina 42, 9.5.2",),
     "Emenda por traspasse proibida acima de 32 mm; costura em tirantes.",
     (), "SEM-REFLEXO", "Nenhum modulo implementa 9.5."),
    ("9.5.3", ("Pagina 45, 9.5.3 titulo", "Pagina 45, 9.5.3 paragrafo",),
     "Luvas: resistencia por norma aplicavel ou +15% do escoamento.",
     (), "SEM-REFLEXO", "Nenhum modulo implementa 9.5.3."),
    ("9.6.3.3.2.2", ("Pagina 51, 9.6.3.3.2.2",),
     "Atrito pos-tracao: mu = 0,07 bainha PP lubrificada; k = 0,065.mu ou 0,01.mu.",
     (("perdas_protensao_nbr6118", "9.6.3"),), "SEM-REFLEXO",
     "Modulo e de PRE-tracao (9.6.3.3.1 + aproximado 9.6.3.4.3): sem bainha, "
     "sem mu; equacao de atrito fora do escopo implementado."),
    ("9.6.3.4.2", ("Pagina 52, 9.6.3.4.2",),
     "Equacao do processo exato sem o indice 28 (Eci no lugar de Ec28).",
     (("perdas_protensao_nbr6118", "9.6.3"),), "SEM-REFLEXO",
     "Modulo implementa o processo APROXIMADO (9.6.3.4.3), nao a equacao exata; "
     "nunca referencia Ec28."),
    ("11.2.2", ("Pagina 56, 11.2.2",),
     "Agua: permanente/variavel, normal/especial, por NBR 6120/8681.",
     (), "SEM-REFLEXO", "Sem gate de acao da agua."),
    ("11.3.3.2", ("Pagina 58, 11.3.3.2",),
     "Fluencia: Anexo A e 8.2.11.",
     (), "SEM-REFLEXO", "Remissivo; sem gate."),
    ("fig-11.1", ("Pagina 59, Figura 11.1",),
     "Figura do desaprumo sem o texto 'n prumadas de pilares' (n segue definido).",
     (("estabilidade_edificio", "11.3.3.4.1"), ("estrutura_casa", "11.3.3.4.1")),
     "EDITORIAL",
     "Limpeza da figura; o n (no de pilares) continua definido e o framework o usa."),
    ("11.8.3.1", ("Pagina 68, 11.8.3.1",),
     "Quase-permanentes (ELS deformacao) e frequentes (fissuras/vibracao/vento) "
     "com a clausula 'desde que as condicionantes nao imponham outra combinacao'.",
     (), "SEM-REFLEXO",
     "Explicita ELS sem trocar numero; nenhum modulo cita 11.8.3.1."),
    ("12.3.3", ("Pagina 71, 12.3.3",),
     "s = 0,20 para CPV-ARI E para todo concreto C60 ou superior.",
     (("premoldado_nbr9062", "12.3.3"),), "NUMERO-MUDA",
     "2014: s por cimento (0,38/0,25/0,20) sem clausula C60+. Framework "
     "S_CIMENTO sem o override C60+: C60+ nao-ARI diverge (caso C4)."),
    ("12.4.1", ("Pagina 71, 12.4.1",),
     "Novo paragrafo: outros gama-c em casos especificos, por outras secoes.",
     (), "SEM-REFLEXO", "Framework usa 1,4; casos especificos nao implementados."),
    ("13.2.5.1", ("Pagina 75, 13.2.5.1",),
     "Furo em viga: 12 cm x 12 cm (retangular) e 12,5 cm (circular), ambos <= h/3.",
     (("compatibilizacao", "13.2.5.1"),), "NUMERO-MUDA",
     "2014 = 2023 pre-Em1: '12 cm e h/3'. Circular 12,1-12,5 cm sai da dispensa "
     "em 2014 e entra em 2023+Em1 (caso C1)."),
    ("tab-13.3", ("Pagina 77, Tabela 13.3 5a-coluna", "Pagina 78, Tabela 13.3 nota-d",
                  "Pagina 77, Tabela 13.3 notas", "Pagina 78, Tabela 13.3 NOTA-6",),
     "Some 'e teta = 0,0017 rad' (alvenaria pos-parede) + nota d; renumera e/f/g; "
     "NOTA 6: deslocamento total = combinacao do projetista + longa duracao.",
     (("laje_concreto", "Tab.13.3"), ("estabilidade_edificio", "Tab.13.3"),
      ("estrutura_casa", "Tab.13.3"), ("escada_concreto", "Tab.13.3")),
     "REGRA-MUDA",
     "O teta removido era criterio da linha alvenaria (l/500 + 10 mm seguem). "
     "Framework: THETA_APOIO_LIM = 0.0017 existe mas e orfa (definida, nunca "
     "usada em veredito) - remocao sem efeito comportamental; H/1700 e Hi/850 "
     "mantidos (estabilidade conforme)."),
    ("tab-13.4", ("Pagina 80, Tabela 13.4 NOTA-2",),
     "Laje protendida: basta ELS-F na combinacao frequente, toda CAA.",
     (("desempenho_nbr15575", "Tab.13.4"), ("viga_protendida", "ELS-F/ELS-D")),
     "REGRA-MUDA",
     "Relaxamento para protendidas; framework nao tem gate da NOTA 2 "
     "(viga_protendida verifica ELS-F/ELS-D sem invocar a nota) - declarar."),
    ("14.6.4.2", ("Pagina 91, 14.6.4.2",),
     "Redistribuicao: considerar efeito na estabilidade global e em todos os "
     "elementos.",
     (("viga_continua", "14.6.6"),), "SEM-REFLEXO",
     "Framework implementa 14.6.6 (continua), nao redistribuicao 14.6.4.2."),
    ("14.6.4.3", ("Pagina 91, 14.6.4.3 travessao", "Pagina 91, 14.6.4.3 delta",),
     "Alineas viram travessao; delta >= 0,75 em qualquer caso.",
     (("fundacao_sapata", "14.6.4.3"),), "SEM-REFLEXO",
     "O modulo usa de 14.6.4.3 so o limite x/d de dutilidade (intocado); nao "
     "implementa delta de redistribuicao."),
    ("14.7.8", ("Pagina 97, 14.7.8 titulo", "Pagina 97, 14.7.8 texto",),
     "Lajes-cogumelo (com/sem capitel); lisa = cogumelo macica sem capitel.",
     (), "EDITORIAL", "Definicoes; sem gate."),
    ("fig-15.3", ("Pagina 103, Figura 15.3",),
     "Figura 15.3 substituida.",
     (), "FIGURA", "Ver pagina renderizada; nenhum modulo cita a figura."),
    ("15.7.3", ("Pagina 106, 15.7.3",),
     "Edificacoes < 4 pavimentos com NSd < 0,10 Ac fcd (alguns galpoes): "
     "reducao de rigidez avaliada de forma especifica.",
     (("estabilidade_edificio", "15.7.3"), ("estrutura_casa", "15.7.3"),
      ("fundacao_edificio", "15.7.3")),
     "EDITORIAL",
     "Em1 vs 2023: so redacao (andares -> pavimentos). Mas 2014 NAO tem o "
     "paragrafo (novidade da edicao 2023, fora da Emenda - gap medido aqui). "
     "Framework ja separa a rigidez 15.7.3 do ELS e declara o campo de validade."),
    ("15.8.1", ("Pagina 107, 15.8.1",),
     "lambda <= 200; pouco comprimido (Nd < 0,10 fcd Ac, de CALCULO) pode passar.",
     (("pilar_concreto", "15.8.1"), ("pilar_continuo", "15.8.1"),
      ("galpao_concreto", "15.8.1")),
     "EDITORIAL",
     "2014 = 2023 pre-Em1 = Em1 na regra (Em1 so insere 'de calculo'). "
     "Framework ja implementa a ressalva (NU_POUCO_COMPRIMIDO, caso C3)."),
    ("centroide", ("Pagina 119, 17.1", "Pagina 123, 17.2.4.1",
                  "Pagina 125, 17.3.1", "Pagina 137, 17.4.2.2",
                  "Pagina 209, 24.6.3",),
     "'centro de gravidade' -> 'centroide' (5 pontos).",
     (), "EDITORIAL", "Troca terminologica pura; sem numero."),
    ("17.3.2.1.1", ("Pagina 127, 17.3.2.1.1",),
     "Rigidez equivalente de viga: valor ponderado pelo criterio da Figura 17.3.",
     (("laje_concreto", "17.3.2"), ("viga_baldrame", "17.3.2"),
      ("vibracao_piso", "17.3.2")),
     "FIGURA",
     "O criterio mora na figura (ver render); framework usa Branson 17.3.2, nao "
     "a ponderacao Fig 17.3 - declarar."),
    ("17.3.3.2", ("Pagina 129, 17.3.3.2", "Pagina 130, 17.3.3.2",),
     "sigma-si no centroide (estadio II); protensao: acrescimo entre "
     "descompressao e carregamento, toda armadura ativa.",
     (("fissuracao_nbr6118", "17.3.3.2"),), "EDITORIAL",
     "Redacao (centroide) + explicita protensao; formulas do wk intocadas."),
    ("17.3.5.2.4", ("Pagina 133, 17.3.5.2.4",),
     "As + As' <= 4% Ac fora das emendas + dutilidade 14.6.4.3.",
     (("laje_concreto", "17.3.5.2.4"),), "EDITORIAL",
     "2014 = 2023 pre-Em1 ('garantidas' -> 'asseguradas', 'A soma' -> 'As somas'). "
     "Framework As_max = 0,04 conforme."),
    ("17.4.1.1.3", ("Pagina 135, 17.4.1.1.3",),
     "Barras dobradas: <= 60% da FORCA (era 'esforco') total da armadura.",
     (), "EDITORIAL", "Uma palavra; nenhum modulo cita 17.4.1.1.3."),
    ("17.5.1.4.1", ("Pagina 141, 17.5.1.4.1",),
     "Se A/u < 2c1, pode-se adotar he = A/u <= bw - 2c1, com Ae pelos eixos "
     "das armaduras do canto.",
     (("torcao_nbr6118", "17.5.1.4.1"), ("viga_concreto", "17.5")),
     "REGRA-MUDA",
     "Alternativa nova para secao pequena: framework faz he = max(A/u, 2c1) "
     "(regra antiga), sem a variante pelos eixos das armaduras (dado que nao "
     "recebe). Direcao: framework mais rigido no he; declarar, sem caso "
     "(Ae alternativa exige armadura declarada)."),
    ("18.1", ("Pagina 145, 18.1",),
     "'FSd' -> 'Fsd' (penultima linha).",
     (), "EDITORIAL", "Caixa da sigla."),
    ("18.2.4-fig", ("Pagina 147, 18.2.4", "Pagina 147, Figura 18.2",),
     "Grampo reto: ganchos preferencialmente 135-180 g, atravessa a secao, "
     "envolve a barra (ou o estribo principal, indicado em projeto). Figura nova.",
     (("executivo_concreto", "18.2.4"), ("pilar_concreto", "18.3/18.4.3")),
     "REGRA-MUDA",
     "Framework admite '90-180 g envolvendo a barra' (executivo_concreto): 90 g "
     "era tolerado e a Em1 prefere 135-180 g. Detalhamento, sem numero; figura "
     "= ver render."),
    ("18.3.2.4", ("Pagina 149 e 150, 18.3.2.4 a), b) e c)",
                  "Pagina 150, 18.3.2.4",
                  "Pagina 150, 18.3.2.4.1, 1o e 2o paragrafos",
                  "Pagina 150, 18.3.2.4.1, 3o paragrafo",
                  "Pagina 150, 18.3.2.4.1, ultimo paragrafo",),
     "Ancoragem em apoios reescrita (Fsd = MSd/z + (al/d)VSd + NSd; alinea d "
     "para momento negativo no extremo; comprimentos e dispensas).",
     (), "SEM-REFLEXO",
     "Nenhum modulo de viga implementa 18.3.2.4 (ancoragem em apoio); "
     "fundacao usa 9.4. Migrar exigiria criar o gate, nao trocar conta."),
    ("18.3.3.2", ("Pagina 150, 18.3.3.2",),
     "NOVO paragrafo: cantos de estribo/ganchos sem barra de calculo levam "
     "barra de amarracao >= phi_estribo.",
     (("pilar_concreto", "18.3.3.2"), ("viga_baldrame", "18.3.3.2"),
      ("sapata_divisa", "18.3.3.2"), ("viga_equilibrio", "18.3.3.2")),
     "REGRA-MUDA",
     "Detalhamento novo; framework dimensiona espacamentos, nao planta barra "
     "de amarracao - declarar."),
    ("18.3.4", ("Pagina 151, 18.3.4",),
     "Estribo de torcao fechado no contorno, gancho 135 g.",
     (("torcao_nbr6118", "17.5"),), "SEM-REFLEXO",
     "Modulo calcula (17.5), nao detalha estribo; sem gate de 18.3.4."),
    ("18.3.6-fig", ("Pagina 152, 18.3.6-red", "Pagina 152, 18.3.6-fig",
                    "Pagina 152, 18.3.6-fig18.4",),
     "Suspensao: fator (1 - hsusp/hviga) p/ viga nao pendurada + '(ver Fig 18.4)' "
     "+ Figura 18.4 nova.",
     (), "SEM-REFLEXO", "Armadura de suspensao nao implementada; figura = render."),
    ("19.5.2.3", ("Pagina 164, 19.5.2.3-borda", "Pagina 164, 19.5.2.3-form",),
     "Pilar de borda: texto introdutorio + formatacao das expressoes de "
     "tau (formulas como figura na Emenda).",
     (("puncao_nbr6118", "19.5.2.3"), ("fundacao_sapata", "19.5")),
     "FIGURA",
     "Prosa mantida; miolo simbolico na Emenda sai como figura - ver render. "
     "Framework implementa borda (K1, u*); sem mudanca na prosa."),
    ("19.5.4", ("Pagina 170, 19.5.4",),
     "'Para ASSEGURAR...' + ancoragem alem de C', ou C'' QUANDO a armadura "
     "transversal for necessaria.",
     (("puncao_nbr6118", "19.5.4"), ("fundacao_sapata", "19.5")),
     "REGRA-MUDA",
     "Numero (fyd.As >= 1,5 FSd) identico; o que muda e o detalhamento (C'' "
     "condicional). Framework declara 'ancorada alem de C'/C''' sem distinguir "
     "(caso C2)."),
    ("20.1-fig", ("Pagina 172, 20.1", "Pagina 173, Figura 20.1",),
     "'armadura POSITIVA secundaria >= 20% DA PRINCIPAL, espac <= 33 cm' + "
     "Figura 20.1 nova.",
     (("escada_concreto", "20.1"), ("laje_concreto", "20.1")),
     "EDITORIAL",
     "2014 = 2023 pre-Em1 ja diziam '20% da principal, 33 cm' (Em1 so insere "
     "'positiva'). Escada cita 20.1 como fonte sem gate dedicado - declarar; "
     "figura = render."),
    ("20.4", ("Pagina 176, 20.4",),
     "Estribo em laje: phi <= h/20, contato com cantos, barra >= phi_estribo.",
     (), "SEM-REFLEXO", "Detalhamento de laje nervurada nao implementado."),
    ("20.5-20.6", ("Pagina 176, 20.5.1", "Pagina 176, 20.5.2",),
     "Tela soldada ate o apoio (10 phi, >= 10 cm) + NOVO 20.6: balanco "
     "(marquise) com armadura inferior ancorada p/ acoes permanentes.",
     (), "PROCESSO-NOVO",
     "20.6 e requisito estrutural novo (anti-colapso de marquise); framework "
     "nao verifica laje em balanco - migrar exige criar o gate."),
    ("22.x", ("Pagina 182, 22.1", "Pagina 187, 22.5.1.2",
              "Pagina 189, Figura 22.5", "Pagina 194, Figura 22.7",),
     "fcd1/fcd2/fcd3 reescritos (CCC/CTT-TTT/CCT) + consolos remetem a NBR 9062 "
     "+ Figs 22.5/22.7 novas.",
     (("estaca_profunda", "22.3.2"),), "EDITORIAL",
     "So redacao em 22.1 (0,85/0,72 seguem; framework conforme); consolo e "
     "figuras fora do escopo (ver render)."),
    ("finais", ("Pagina 195, 23.3-fn", "Pagina 196, 23.3-3Hz",
                "Pagina 208, 24.6.1", "Pagina 209, 24.6.3",
                "Pagina 211, A.2.1", "Pagina 211, A.2.2.1",
                "Pagina 213, A.2.2.3-eq", "Pagina 213, A.2.2.3-def",
                "Pagina 219, A.2.5-eq", "Pagina 219, A.2.5-tx",),
     "23.3: fn longe de fcrit + NUNCA < 3 Hz; 24.6.1: pilar-parede simples no "
     "terco central; 24.6.3: centroide; Anexo A: Ec28 -> Eci (4 pontos).",
     (("vibracao_piso", "23?"), ("fissuracao_nbr6118", "8.2.8")),
     "SEM-REFLEXO",
     "Agrupados por veredito comum (regra de agrupamento escrita no D141): "
     "nenhum modulo implementa 23.3 (fn >= 3 Hz seria gate novo), 24.6 ou o "
     "Anexo A exato (framework usa Tab.A.1 tipicos + Eci de 8.2.8, sem Ec28)."),
)

# Os 85 cabecalhos de instrucao da F098 (extracao literal dos "Pagina ..."
# da Emenda, com acentos dobrados para ASCII no portao). Congelado:
# instrucao nova = vermelho. (O G113 contou 51 itens e 62 instrucoes: era
# agrupamento por clausula; aqui vao os 85 cabecalhos literais, e os 51
# itens de ITENS_EM1 os agrupam - o mapa CAB_PARA_ITEM congela o agrupamento
# e o teste prova que e particao exata.)
CABECALHOS_EM1 = (
    "Pagina xvi, Prefacio, paragrafo especial",
    "Pagina 2, Secao 2",
    "Pagina 13, 5.1.2.3, paragrafo unico",
    "Pagina 13, 5.2.1, 1o paragrafo",
    "Pagina 14, 5.3",
    "Pagina 15, 6.2.2, paragrafo unico",
    "Pagina 15, 6.2",
    "Pagina 15, 6.3.2",
    "Pagina 22, 8.1, 5a linha, definicao de Eci",
    "Pagina 22, 8.1, 8a linha, definicao de Eci28",
    "Pagina 28, 8.2.11, 2o paragrafo da pagina",
    "Pagina 28, 8.3.1, paragrafo unico",
    "Pagina 30, 8.3.7, 2o paragrafo",
    "Pagina 31, 8.4.6, 2o paragrafo",
    "Pagina 34, 9.2.1, paragrafo unico",
    "Pagina 42, 9.5.2, 1o paragrafo",
    "Pagina 45, 9.5.3, Titulo",
    "Pagina 45, 9.5.3, paragrafo unico",
    "Pagina 51, 9.6.3.3.2.2, 6a e 7a designacoes da equacao",
    "Pagina 52, 9.6.3.4.2, 2a equacao da pagina",
    "Pagina 56, 11.2.2, 3o paragrafo",
    "Pagina 58, o 11.3.3.2, 1o paragrafo",
    "Pagina 59, Figura 11.1",
    "Pagina 68, 11.8.3.1-a) e b)",
    "Pagina 71, 12.3.3, 3a designacao da equacao",
    "Pagina 71, 12.4.1",
    "Pagina 75, 13.2.5.1-b)",
    "Pagina 77, Tabela 13.3, 5a coluna, 7a linha",
    "Pagina 78, Tabela 13.3, Nota de rodape d",
    "Pagina 77, Tabela 13.3, citacao da nota de rodape",
    "Pagina 78, Tabela 13.3",
    "Pagina 80, Tabela 13.4, NOTA 2",
    "Pagina 91, 14.6.4.2, 2o paragrafo",
    "Pagina 91, 14.6.4.3, 4o paragrafo e respectivas alineas a) e b)",
    "Pagina 91, 14.6.4.3, 5o paragrafo e respectivas alineas a) e b)",
    "Pagina 97, 14.7.8, Titulo",
    "Pagina 97, 14.7.8, 1o paragrafo",
    "Pagina 103, Figura 15.3",
    "Pagina 106, 15.7.3, ultimo paragrafo",
    "Pagina 107, 15.8.1, 2o paragrafo",
    "Pagina 119, 17.1, 19a linha",
    "Pagina 123, 17.2.4.1, 1o paragrafo",
    "Pagina 125, 17.3.1, 2a designacao da equacao",
    "Pagina 127, 17.3.2.1.1, 1o paragrafo da pagina",
    "Pagina 129, 17.3.3.2, ultima designacao da equacao",
    "Pagina 130, 17.3.3.2, 1o paragrafo da pagina",
    "Pagina 133, 17.3.5.2.4, paragrafo unico",
    "Pagina 135, 17.4.1.1.3, paragrafo unico",
    "Pagina 137, 17.4.2.2, 2a designacao da equacao (d)",
    "Pagina 141, 17.5.1.4.1, ultimo paragrafo",
    "Pagina 145, 18.1, penultima linha",
    "Pagina 147, 18.2.4, 3o paragrafo",
    "Pagina 147, Figura 18.2",
    "Pagina 149 e 150, 18.3.2.4 a), b) e c)",
    "Pagina 150, 18.3.2.4",
    "Pagina 150, 18.3.2.4.1, 1o e 2o paragrafos",
    "Pagina 150, 18.3.2.4.1, 3o paragrafo",
    "Pagina 150, 18.3.2.4.1, ultimo paragrafo",
    "Pagina 150, 18.3.3.2, apos o 2o paragrafo",
    "Pagina 151, 18.3.4, 3o paragrafo",
    "Pagina 152, 18.3.6, 4o paragrafo",
    "Pagina 152, 18.3.6, 3o paragrafo",
    "Pagina 152, 18.3.6, apos o ultimo paragrafo",
    "Pagina 164, 19.5.2.3, antes da alinea a)",
    "Pagina 164, 19.5.2.3",
    "Pagina 170, 19.5.4, 1o paragrafo",
    "Pagina 172, 20.1, penultimo paragrafo",
    "Pagina 173, Figura 20.1",
    "Pagina 176, 20.4, 3o paragrafo",
    "Pagina 176, 20.5.1, paragrafo unico",
    "Pagina 176, 20.5.2",
    "Pagina 182, 22.1, simbologia",
    "Pagina 187, 22.5.1.2-d)",
    "Pagina 189, Figura 22.5",
    "Pagina 194, Figura 22.7",
    "Pagina 195, 23.3, 2o paragrafo",
    "Pagina 196, 23.3, apos a Tabela 23.1",
    "Pagina 208, 24.6.1, 1o paragrafo",
    "Pagina 209, 24.6.3, 1o paragrafo",
    "Pagina 211, A.2.1, 2a designacao da equacao",
    "Pagina 211, A.2.2.1, 2a equacao",
    "Pagina 213, A.2.2.3, 1a equacao",
    "Pagina 213, A.2.2.3, designacao da 1a equacao",
    "Pagina 219, A.2.5, 1a e 2a equacoes",
    "Pagina 219, A.2.5, 5o e 6o paragrafos",
)

# Agrupamento congelado cabecalho -> item (particao dos 85 em 51 itens).
CAB_PARA_ITEM = {
    "Pagina xvi, Prefacio, paragrafo especial": "prefacio-xvi",
    "Pagina 2, Secao 2": "secao-2",
    "Pagina 13, 5.1.2.3, paragrafo unico": "5.1.2.3",
    "Pagina 13, 5.2.1, 1o paragrafo": "5.2.1",
    "Pagina 14, 5.3": "5.3-atp",
    "Pagina 15, 6.2.2, paragrafo unico": "6.2.2",
    "Pagina 15, 6.2": "6.2.4",
    "Pagina 15, 6.3.2": "6.3.2.4",
    "Pagina 22, 8.1, 5a linha, definicao de Eci": "8.1",
    "Pagina 22, 8.1, 8a linha, definicao de Eci28": "8.1",
    "Pagina 28, 8.2.11, 2o paragrafo da pagina": "8.2.11",
    "Pagina 28, 8.3.1, paragrafo unico": "8.3.1",
    "Pagina 30, 8.3.7, 2o paragrafo": "8.3.7-8.4.6",
    "Pagina 31, 8.4.6, 2o paragrafo": "8.3.7-8.4.6",
    "Pagina 34, 9.2.1, paragrafo unico": "9.2.1",
    "Pagina 42, 9.5.2, 1o paragrafo": "9.5.2",
    "Pagina 45, 9.5.3, Titulo": "9.5.3",
    "Pagina 45, 9.5.3, paragrafo unico": "9.5.3",
    "Pagina 51, 9.6.3.3.2.2, 6a e 7a designacoes da equacao": "9.6.3.3.2.2",
    "Pagina 52, 9.6.3.4.2, 2a equacao da pagina": "9.6.3.4.2",
    "Pagina 56, 11.2.2, 3o paragrafo": "11.2.2",
    "Pagina 58, o 11.3.3.2, 1o paragrafo": "11.3.3.2",
    "Pagina 59, Figura 11.1": "fig-11.1",
    "Pagina 68, 11.8.3.1-a) e b)": "11.8.3.1",
    "Pagina 71, 12.3.3, 3a designacao da equacao": "12.3.3",
    "Pagina 71, 12.4.1": "12.4.1",
    "Pagina 75, 13.2.5.1-b)": "13.2.5.1",
    "Pagina 77, Tabela 13.3, 5a coluna, 7a linha": "tab-13.3",
    "Pagina 78, Tabela 13.3, Nota de rodape d": "tab-13.3",
    "Pagina 77, Tabela 13.3, citacao da nota de rodape": "tab-13.3",
    "Pagina 78, Tabela 13.3": "tab-13.3",
    "Pagina 80, Tabela 13.4, NOTA 2": "tab-13.4",
    "Pagina 91, 14.6.4.2, 2o paragrafo": "14.6.4.2",
    "Pagina 91, 14.6.4.3, 4o paragrafo e respectivas alineas a) e b)": "14.6.4.3",
    "Pagina 91, 14.6.4.3, 5o paragrafo e respectivas alineas a) e b)": "14.6.4.3",
    "Pagina 97, 14.7.8, Titulo": "14.7.8",
    "Pagina 97, 14.7.8, 1o paragrafo": "14.7.8",
    "Pagina 103, Figura 15.3": "fig-15.3",
    "Pagina 106, 15.7.3, ultimo paragrafo": "15.7.3",
    "Pagina 107, 15.8.1, 2o paragrafo": "15.8.1",
    "Pagina 119, 17.1, 19a linha": "centroide",
    "Pagina 123, 17.2.4.1, 1o paragrafo": "centroide",
    "Pagina 125, 17.3.1, 2a designacao da equacao": "centroide",
    "Pagina 127, 17.3.2.1.1, 1o paragrafo da pagina": "17.3.2.1.1",
    "Pagina 129, 17.3.3.2, ultima designacao da equacao": "17.3.3.2",
    "Pagina 130, 17.3.3.2, 1o paragrafo da pagina": "17.3.3.2",
    "Pagina 133, 17.3.5.2.4, paragrafo unico": "17.3.5.2.4",
    "Pagina 135, 17.4.1.1.3, paragrafo unico": "17.4.1.1.3",
    "Pagina 137, 17.4.2.2, 2a designacao da equacao (d)": "centroide",
    "Pagina 141, 17.5.1.4.1, ultimo paragrafo": "17.5.1.4.1",
    "Pagina 145, 18.1, penultima linha": "18.1",
    "Pagina 147, 18.2.4, 3o paragrafo": "18.2.4-fig",
    "Pagina 147, Figura 18.2": "18.2.4-fig",
    "Pagina 149 e 150, 18.3.2.4 a), b) e c)": "18.3.2.4",
    "Pagina 150, 18.3.2.4": "18.3.2.4",
    "Pagina 150, 18.3.2.4.1, 1o e 2o paragrafos": "18.3.2.4",
    "Pagina 150, 18.3.2.4.1, 3o paragrafo": "18.3.2.4",
    "Pagina 150, 18.3.2.4.1, ultimo paragrafo": "18.3.2.4",
    "Pagina 150, 18.3.3.2, apos o 2o paragrafo": "18.3.3.2",
    "Pagina 151, 18.3.4, 3o paragrafo": "18.3.4",
    "Pagina 152, 18.3.6, 4o paragrafo": "18.3.6-fig",
    "Pagina 152, 18.3.6, 3o paragrafo": "18.3.6-fig",
    "Pagina 152, 18.3.6, apos o ultimo paragrafo": "18.3.6-fig",
    "Pagina 164, 19.5.2.3, antes da alinea a)": "19.5.2.3",
    "Pagina 164, 19.5.2.3": "19.5.2.3",
    "Pagina 170, 19.5.4, 1o paragrafo": "19.5.4",
    "Pagina 172, 20.1, penultimo paragrafo": "20.1-fig",
    "Pagina 173, Figura 20.1": "20.1-fig",
    "Pagina 176, 20.4, 3o paragrafo": "20.4",
    "Pagina 176, 20.5.1, paragrafo unico": "20.5-20.6",
    "Pagina 176, 20.5.2": "20.5-20.6",
    "Pagina 182, 22.1, simbologia": "22.x",
    "Pagina 187, 22.5.1.2-d)": "22.x",
    "Pagina 189, Figura 22.5": "22.x",
    "Pagina 194, Figura 22.7": "22.x",
    "Pagina 195, 23.3, 2o paragrafo": "finais",
    "Pagina 196, 23.3, apos a Tabela 23.1": "finais",
    "Pagina 208, 24.6.1, 1o paragrafo": "finais",
    "Pagina 209, 24.6.3, 1o paragrafo": "centroide",
    "Pagina 211, A.2.1, 2a designacao da equacao": "finais",
    "Pagina 211, A.2.2.1, 2a equacao": "finais",
    "Pagina 213, A.2.2.3, 1a equacao": "finais",
    "Pagina 213, A.2.2.3, designacao da 1a equacao": "finais",
    "Pagina 219, A.2.5, 1a e 2a equacoes": "finais",
    "Pagina 219, A.2.5, 5o e 6o paragrafos": "finais",
}

# Familias de clausulas citadas pelos modulos de producao (medido por grep
# "6118"/"17.3"/"15.8": 275 linhas; consolidado por familia; "geral" = menção
# sem clausula). Congelado nos dois sentidos: familia nova some do portao
# (silencio) ou some do codigo (nome morto) = vermelho.
FAMILIAS_FW = (
    "geral", "7.2", "8.2.2", "8.2.5", "8.2.8", "8.2.10",
    "9.3.2", "9.4.2", "9.6.3",
    "11.3.3.4.1", "12.3.3",
    "13.2.2", "13.2.3", "13.2.4.1", "13.2.5", "13.2.6", "13.3", "13.4",
    "14.6.4.3", "14.6.6",
    "15.5", "15.6", "15.7.2", "15.7.3", "15.8",
    "17.2.2", "17.2.5", "17.3.2", "17.3.3.2", "17.3.5.2.4", "17.3.5.3",
    "17.4", "17.5",
    "18.2.4", "18.3", "18.4.3",
    "19.3.3", "19.4.1", "19.5",
    "20.1", "20.2", "21.3",
    "22.3", "22.6", "Tab.A.1",
)


def _dobra(texto):
    """Dobra acentos/maiusculas para o portao substring (o inventario e
    escrito sem acentos nas referencias 'Pagina ...', mesma forma daqui)."""
    import unicodedata
    sem = "".join(c for c in unicodedata.normalize("NFD", texto)
                  if unicodedata.category(c) != "Mn")
    return sem.lower()


def _cabecalhos_por_item():
    """Indice reverso item -> cabecalhos, pelo mapa congelado CAB_PARA_ITEM."""
    mapa = {}
    for cab, item_id in CAB_PARA_ITEM.items():
        mapa.setdefault(item_id, []).append(cab)
    return mapa


def cobre_inventario(texto_inventario):
    """Portao do inventario: cada um dos 85 cabecalhos Em1 e cada familia FW
    precisa aparecer no texto; cada modulo citado por item com framework
    precisa aparecer; o OK por item chega ao veredito global (contra a
    saturacao silenciosa do G113)."""
    dobrado = _dobra(texto_inventario)
    cabs = {c: (_dobra(c) in dobrado) for c in CABECALHOS_EM1}
    por_item = _cabecalhos_por_item()
    itens = {i: all(cabs[c] for c in cs) and bool(cs)
             for i, cs in por_item.items()}
    fams = {f: (_dobra(f) in dobrado) for f in FAMILIAS_FW}
    # Sentido Em1 -> framework: todo item com framework nao-vazio precisa
    # citar o modulo na linha (o inventario escreve "modulo (clausula)").
    latentes = {}
    for item_id, _refs, _novo, fw, _ver, _det in ITENS_EM1:
        for mod, _cl in fw:
            latentes.setdefault(item_id, []).append(mod.split(".")[0]
                                                    in texto_inventario)
    latentes_ok = {k: all(v) and bool(v) for k, v in latentes.items()}
    ok = (all(cabs.values()) and all(itens.values())
          and all(fams.values()) and all(latentes_ok.values())
          and len(itens) == len(ITENS_EM1))
    return {"cabecalhos": cabs, "itens": itens, "familias": fams,
            "modulos": latentes_ok, "ok": bool(ok)}


def caso_c1_furo_circular():
    """13.2.5.1-b: furo circular d = 125 mm em viga h = 600 mm (<= h/3).
    2014: fora da dispensa (12 cm). 2023+Em1: dispensavel (12,5 cm)."""
    import compatibilizacao as co
    r = co.avalia_furo_viga(
        d_furo_mm=125.0, h_viga_mm=600.0, dist_apoio_mm=1300.0,
        zona_tracao=True, dist_face_mm=60.0, cobrimento_mm=25.0,
        furo_unico=True, armadura_seccionada=False)
    nova_regra = (125.0 <= 125.0 and 125.0 <= 600.0 / 3.0)
    return {"veredito_2014": r["veredito"], "motivos_2014": r["motivos"],
            "dispensavel_2023_em1": bool(nova_regra)}


def caso_c2_colapso():
    """19.5.4: mesmo pilar-laje pelas duas regras. Numero identico
    (fyd.As >= 1,5 FSd); muda o detalhamento (C'' condicional)."""
    import puncao_nbr6118 as pu
    cfg = {"tipo": "interno", "c1": 0.40, "c2": 0.40, "d": 0.16,
           "fck": 30e3, "F_sd": 350.0, "M_sd_x": 0.0, "M_sd_y": 0.0,
           "rho_x": 0.005, "rho_y": 0.005,
           "As_ccp": 1.5 * 350.0 / (500e3 / 1.15) * 1.01}
    r = pu.verifica_puncao(cfg)
    return {"ok_2014": bool(r["OK"]),
            "numero_2023_em1_igual": True,
            "detalhe_novo": "C'' so quando houver armadura transversal "
                            "(framework declara C'/C'' sem distinguir)"}


def caso_c3_lambda_pouco_comprimido():
    """15.8.1: lambda = 210. Pouco comprimido (nu = 0,05) admitido nas tres
    edicoes; nao pouco comprimido (nu = 0,50) reprovado nas tres."""
    import pilar_concreto as pc
    r_baixo = pc.valida_esbeltez(210.0, 0.05)
    r_alto = pc.valida_esbeltez(210.0, 0.50)
    return {
        "admite_baixo": any("pouco comprimido" in a for a in r_baixo["avisos"])
                        and not any("REPROVA (15.8.1)" in a
                                    for a in r_baixo["avisos"]),
        "reprova_alto": any("REPROVA (15.8.1)" in a for a in r_alto["avisos"])}


def caso_c4_fckj_c60():
    """12.3.3: fckj aos 7 dias, C60 CPIII. 2014: s = 0,38. 2023+Em1: s = 0,20
    (todo C60+)."""
    import math
    import premoldado_nbr9062 as pm
    fck = float(pm.fckj_idade(60e3, 7, cimento="CPIII"))
    novo = 60e3 * math.exp(0.20 * (1.0 - math.sqrt(28.0 / 7.0)))
    return {"fckj_2014_kNm2": float(fck), "fckj_2023_em1_kNm2": float(novo)}


def main() -> int:
    print("itens=%d cabecalhos=%d familias=%d"
          % (len(ITENS_EM1), len(CABECALHOS_EM1), len(FAMILIAS_FW)))
    c1 = caso_c1_furo_circular()
    print("C1 furo125: 2014=%s 2023+Em1 dispensavel=%s"
          % (c1["veredito_2014"], c1["dispensavel_2023_em1"]))
    c2 = caso_c2_colapso()
    print("C2 colapso: OK_2014=%s numero_igual=%s"
          % (c2["ok_2014"], c2["numero_2023_em1_igual"]))
    c3 = caso_c3_lambda_pouco_comprimido()
    print("C3 lambda210: admite_baixo=%s reprova_alto=%s"
          % (c3["admite_baixo"], c3["reprova_alto"]))
    c4 = caso_c4_fckj_c60()
    print("C4 fckj C60/CPIII/7d: 2014=%.0f 2023+Em1=%.0f kN/m2"
          % (c4["fckj_2014_kNm2"], c4["fckj_2023_em1_kNm2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
