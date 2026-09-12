# ============================================================================
# confronto_2014_2023_g122.py - G122: AS DIFERENCAS 2014 -> 2023 QUE NAO ESTAO
# NA EMENDA. MEDE E ESCREVE - NAO MUDA CALCULO.
# SCRIPT AVULSO + MODULO DE PRODUCAO: as tabelas canonicas moram aqui; a
# lente e o teste importam de ca. (Uma fonte so - regra do lote.)
# Rodado a mao/CI (python confronto_2014_2023_g122.py) e pelo teste-guarda
# tests/test_confronto_2014_2023_g122.py. Nao e importado por nenhum
# orquestrador do Loop - declarado em SCRIPTS_AVULSOS no
# tests/test_alcancabilidade.py, no mesmo molde de impacto_nbr6118_g116.
#
# O que foi MEDIDO (enderecos verificados nesta entrega):
#   - F016 = fontes/01_CONCRETO/...-2014__...-historica.pdf (256 p., texto
#     extraivel, PyMuPDF) e F150 = fontes/01_CONCRETO/...-2023__...pdf
#     (260 p.) + decodificada G117/G120 (...-dec.txt, 641190 bytes,
#     desconhecidos={'0BD8': 188} declarado). G120 fechado: 7/8 codigos
#     mapeados na imagem, 0BD8 segue marcador (avanco 0,91 pt, sem marca).
#   - Confronto SECAO A SECAO 2014 x 2023 PRE-EMENDA (nao por amostragem)
#     para cada clausula que o framework cita (grep "6118" em 217 .py,
#     295 linhas; consolidado nas 45 FAMILIAS_G122, mesma particao do G116
#     para compatibilidade). Para cada familia: texto das duas (janela de
#     corpo, fora do sumario) + veredito (IGUAL / EDITORIAL / REGRA-MUDA /
#     NUMERO-MUDA). O que e formula/tabela/figura e declarado por clausula
#     como limite (ver pagina renderizada), nunca silenciado.
#   - Diferenca achada por comparacao de texto so virou veredito depois de
#     confirmada na IMAGEM das duas edicoes (regra 3). Imagens lidas em
#     200 dpi via PyMuPDF (F016 + F150 lado a lado):
#       8.2.5 fct,m C55+ : F016 p.23 PDF41 "2,12 ln (1 + 0,11 fck)" x
#         F150 p.23 PDF41 "2,12 ln [1 + 0,1 (fck + 8)]" -> NUMERO-MUDA.
#       8.2.8 Eci ensaio/faixa: F016 p.24 PDF42 "NBR 8522 / 20-50 e 55-90" x
#         F150 p.24 PDF42 "NBR 8522-1 e 8522-2 / ate 50 e acima de 50" -> EDITORIAL.
#       15.4.2 exemplo: F016 p.103 PDF121 "...postes e em certos pilares de
#         galpoes industriais." x F150 p.103 PDF121 "...postes." -> EDITORIAL.
#       15.7.2 acao: F016 p.106 PDF124 "majoracao adicional dos esforcos
#         horizontais" x F150 p.106 PDF124 "majoracao adicional das acoes
#         horizontais" -> EDITORIAL.
#       15.7.3 paragrafo do galpao: AUSENTE na F016 p.106 PDF124 (termina em
#         "...maior da modelagem.") x PRESENTE na F150 p.106 PDF124 ("Em
#         estruturas de edificacoes com menos de quatro andares... como em
#         alguns galpoes") -> novidade da edicao (ja apontada no G116 item
#         31; aqui confirmada ausente x presente em imagem).
#       18.2.3/18.2.4 frases novas: F016 p.146 PDF164 (sem as frases) x
#         F150 p.147 PDF165 ("Deve-se verificar tambem os efeitos... no
#         banzo comprimido." + "O estribo suplementar deve atender ao minimo
#         estabelecido em 18.4.3...") -> REGRA-MUDA (detalhamento, sem n.).
#   - Cobertura nos dois sentidos: cada citacao de "6118" no codigo tem
#     linha no inventario (MODULOS_POR_FAMILIA congela o mapa modulo ->
#     familias; o portao cobra substring do modulo + da familia no texto
#     do inventario), e cada secao divergente tem endereco arquivo:linha
#     (o portao cobra ".py:" junto a familia divergente).
#
# Maquina: cobre_inventario(texto) e o portao - cada familia e cada modulo
# precisa aparecer no texto do inventario; cada familia com veredito
# NUMERO-MUDA ou REGRA-MUDA precisa vir com endereco arquivo:linha; o OK
# por item chega ao veredito global (contra a saturacao silenciosa do
# G113). caso_fctm_c60 chama a funcao REAL (premoldado_nbr9062._fctm para
# 2014; a prescricao literal da 2023 para o novo numero) - a lente nao
# reimplementa formula do framework (contra assercao tautologica). O
# instrumento acusa: faltando_familias / faltando_modulos / sem_endereco
# sao acumuladores com teste que os faz disparar (convencao 7 do lote).
#
# O que a lente NAO cobre, dito aqui (molde DIVIDA-LENTE do G51):
#   - clausulas que o framework NAO cita (ex.: 17.2.4.4 novo de protensao,
#     5.3 ATP, 20.6 marquise): fora do inventario por definicao;
#   - miolo simbolico de formulas/tabelas/figuras (limite declarado por
#     familia no proprio CONFRONTO_G122, campo de limite): ver pagina
#     renderizada;
#   - migracao propriamente dita (trocar a base de nenhum modulo - decisao
#     do usuario, G123).
# ============================================================================
"""Confronto G122: NBR 6118 2014 -> 2023 pre-Emenda, secao a secao."""

from __future__ import annotations

import math
import pathlib
import re
import unicodedata

GALPAO = pathlib.Path(__file__).resolve().parent

# Vereditos por familia (classes disjuntas, mesmo sentido do G116):
#   IGUAL ....... numero e regra aplicados iguais (prosa equivalente a menos
#                 de ortografia/marcador de lista; formula/tabela/figura e
#                 limite declarado, ver imagem).
#   EDITORIAL ... so redacao com imagem confirmada (exemplo, remissivo,
#                 norma de ensaio desdobrada), sem troca de numero aplicado.
#   REGRA-MUDA .. detalhamento/processo novo sem trocar numero aplicado.
#   NUMERO-MUDA . troca numero que o framework aplica (entra na Tabela 1).
CONFRONTO_G122 = (
    ("geral", "IGUAL",
     "Mencao sem clausula (caderno_encargos, dossie, relatorios). Sem numero.",
     "F016/F150 capa+prefacio", ()),
    ("7.2", "IGUAL",
     "Cobrimento Tab.7.2: valores nominais por CAA inalterados na prosa; "
     "miolo da Tabela 7.2 = ver pagina renderizada (limite).",
     "F016 p.20 / F150 p.20", (("techdraw_concreto", "Tab.7.2"),)),
    ("8.2.2", "IGUAL",
     "Massa especifica: 2000-2800, 2400 simples, 2500 armado. F016 p.22-23 "
     "PDF40-41 x F150 p.22-23 PDF40-41, numeros identicos.",
     "F016 p.23 PDF41 / F150 p.23 PDF41",
     (("build_concreto", "8.2.2"),)),
    ("8.2.5", "NUMERO-MUDA",
     "fct,m C55+: 2014 '2,12 ln (1 + 0,11 fck)' x 2023 '2,12 ln [1 + 0,1 "
     "(fck + 8)]' + limiar 'classes ate C50 / C55 a C90' -> 'fck ate 50 / fck "
     "acima de 50 MPa'. Confirmado na imagem F016 p.23 PDF41 x F150 p.23 PDF41. Caso C5: "
     "C60 da 4,30 MPa (2014) contra 4,35 MPa (2023), +1,3%.",
     "F016 p.23 PDF41 / F150 p.23 PDF41",
     (("base_chumbador", "8.2.5"), ("fundacao_sapata", "8.2.5"),
      ("piso_industrial", "8.2.5"), ("premoldado_nbr9062", "8.2.5"),
      ("viga_protendida", "8.2.5"), ("desenho_piso", "8.2.5"),
      # G125 (auditoria do G122): cinco modulos que CALCULAM a formula C55+
      # e nao estavam aqui - o inventario partiu do grep "6118", e estes
      # citam so "8.2.5" na linha da conta. Achados por sites_formula_fctm.
      ("estaca_profunda", "8.2.5"), ("fissuracao_nbr6118", "8.2.5"),
      ("laje_concreto", "8.2.5"), ("pilar_concreto", "8.2.5"),
      ("viga_baldrame", "8.2.5"))),
    ("8.2.8", "EDITORIAL",
     "Eci: ensaio 'NBR 8522' -> 'NBR 8522-1 e 8522-2'; faixas '20-50 e 55-90'"
     " -> 'ate 50 e acima de 50' (fecha o gap 51-54; formulas identicas). Confirmado "
     "F016 p.24 PDF42 x F150 p.24 PDF42. Sem efeito nos casos do repo (ate 50).",
     "F016 p.24 PDF42 / F150 p.24 PDF42",
     (("fissuracao_nbr6118", "8.2.8"), ("perdas_protensao_nbr6118", "8.2.8"),
      ("piso_industrial", "8.2.8"))),
    ("8.2.10", "IGUAL",
     "Diagramas/pivos Fig.8.2 (fck ate 50): prosa igual; miolo da figura e das "
     "expressoes = ver pagina renderizada (limite).",
     "F016 p.26 / F150 p.26", (("pilar_concreto", "8.2.10"),)),
    ("9.3.2", "IGUAL",
     "Aderencia eta1/eta2/eta3: numeros iguais (1,0/1,4/2,25; 1,0 boa/0,7 ma;"
     " 1,0 phi<32mm); 2023 remete eta1 a Tab.8.2 (reorganizacao). Tabela = "
     "ver imagem (limite).",
     "F016 p.34-35 / F150 p.34-35", (("estaca_profunda", "9.3.2"),
      ("base_chumbador", "9.4.2"))),
    ("9.4.2", "IGUAL",
     "Ancoragem lb/fbd: numeros iguais; 9.4.1.1 reescrita com lista "
     "explicita (gancho/barra transversal/chapa) sem trocar conta. Formula "
     "lb = ver imagem (limite).",
     "F016 p.36 / F150 p.36",
     (("base_chumbador", "9.4.2"), ("fundacao_sapata", "9.4"),
      ("estaca_profunda", "9.4.2"))),
    ("9.6.3", "IGUAL",
     "Perdas pre-tracao (9.6.3.3.1 + aproximado 9.6.3.4.3): prosa igual; "
     "Fig.9.6 -> Fig.9.7 (renumeracao por figura nova anterior). Figura = "
     "ver imagem (limite).",
     "F016 p.49 / F150 p.49", (("perdas_protensao_nbr6118", "9.6.3"),)),
    ("11.3.3.4.1", "IGUAL",
     "Desaprumo theta1min=1/300, theta1max=1/200, n/H/Nk/EcsIc: prosa e "
     "numeros iguais pre-Emenda (Fig.11.1 e da Emenda, item 20).",
     "F016 p.59 / F150 p.59",
     (("estabilidade_edificio", "11.3.3.4.1"),
      ("estrutura_casa", "11.3.3.4.1"))),
    ("12.3.3", "IGUAL",
     "s do cimento 0,38/0,25/0,20: igual pre-Emenda (2014=2023pre; o override"
     " C60+ e da Emenda, item 22).",
     "F016 p.71 / F150 p.71", (("premoldado_nbr9062", "12.3.3"),)),
    ("13.2.2", "IGUAL",
     "Vigas 12cm / vigas-parede 15cm / minimo absoluto 10cm: identicos.",
     "F016 p.73 / F150 p.73", (("viga_baldrame", "13.2.2"),)),
    ("13.2.3", "IGUAL",
     "Pilares 19cm / 14-19cm com gama-n Tab.13.1 (1,00-1,25; gama-n=1,95-"
     "0,05b) / area >=360cm2: identicos. Tabela = ver imagem (limite).",
     "F016 p.73-74 / F150 p.73-74", (("pilar_concreto", "13.2.3"),)),
    ("13.2.4.1", "IGUAL",
     "Lajes macicas 7/8/10/12cm (cobertura/piso/balanco/veiculos 30kN): "
     "identicos.",
     "F016 p.74 / F150 p.74", (("escada_concreto", "13.2.4.1"),)),
    ("13.2.5", "IGUAL",
     "Furos caput + 13.2.5.1 '12 cm e h/3' + 13.2.5.2 (1/10 vao, 1/4 vao, "
     "metade vao) + 21.3.1/21.3.3 (b/3 Fig.21.5)/21.3.4: iguais pre-Emenda "
     "(o 12,5cm circular e da Emenda, item 24). Figuras = ver imagem.",
     "F016 p.75-76 / F150 p.75-76",
     (("compatibilizacao", "13.2.5"),)),
    ("13.2.6", "IGUAL",
     "Canalizacoes embutidas: prosa igual.",
     "F016 p.76 / F150 p.76", (("compatibilizacao", "13.2.6"),)),
    ("13.3", "IGUAL",
     "Tab.13.3 H/1700 e Hi/850, l/500 etc.: iguais pre-Emenda (o 'teta = "
     "0,0017 rad' sai na Emenda, item 25). Miolo da tabela = ver imagem.",
     "F016 p.77-78 / F150 p.77-78",
     (("laje_concreto", "Tab.13.3"), ("estabilidade_edificio", "Tab.13.3"),
      ("estrutura_casa", "Tab.13.3"), ("escada_concreto", "Tab.13.3"),
      ("viga_baldrame", "Tab.13.3"), ("desempenho_nbr15575", "Tab.13.3"),
      ("vibracao_piso", "13.3"))),
    ("13.4", "IGUAL",
     "Tab.13.4 wk por CAA + ELS-F/ELS-D: iguais pre-Emenda (NOTA 2 de "
     "protendida e da Emenda, item 26). Miolo da tabela = ver imagem.",
     "F016 p.79-80 / F150 p.79-80",
     (("desempenho_nbr15575", "Tab.13.4"), ("viga_protendida", "ELS"),)),
    ("14.6.4.3", "IGUAL",
     "Dutilidade x/d: limites iguais; delta de redistribuicao e da Emenda "
     "(item 28, sem gate no framework). Expressoes = ver imagem.",
     "F016 p.91 / F150 p.91", (("fundacao_sapata", "14.6.4.3"),)),
    ("14.6.6", "IGUAL",
     "Viga continua 14.6.6.1 (texto literal a/b/c): igual.",
     "F016 p.93-94 / F150 p.93-94", (("viga_continua", "14.6.6"),)),
    ("15.5", "IGUAL",
     "Alpha (alfa1 0,6/0,7/0,5; n<=3/n>=4) e gama-z (<=1,1; 0,95*gama-z; "
     "<=1,3): numeros iguais. Confirmado F016 p.104 PDF122 x F150 p.104 "
     "PDF122. Formulas = ver imagem.",
     "F016 p.104 PDF122 / F150 p.104 PDF122",
     (("estabilidade_global_nbr6118", "15.5"),
      ("estabilidade_edificio", "15.5"), ("galpao_concreto", "15.5"))),
    ("15.6", "IGUAL",
     "le = l0+h / le = l: iguais.",
     "F016 p.106 / F150 p.106",
     (("galpao_mezanino", "15.6"), ("pilar_continuo", "15.6"))),
    ("15.7.2", "EDITORIAL",
     "0,95*gama-z (gama-z<=1,3): numeros iguais; 'esforcos horizontais' -> "
     "'acoes horizontais'. Confirmado F016 p.106 PDF124 x F150 p.106 PDF124.",
     "F016 p.106 PDF124 / F150 p.106 PDF124",
     (("estabilidade_edificio", "15.7.2"),)),
    ("15.7.3", "EDITORIAL",
     "Rigidez (EI)sec 0,3/0,4/0,5/0,8: iguais; paragrafo novo do galpao "
     "(<4 andares, NSd<0,10 Ac fcd) AUSENTE na F016 p.106 PDF124 x PRESENTE"
     " na F150 p.106 PDF124. Novidade da edicao (G116 item 31 aqui "
     "reconfirmada em imagem); framework ja declara o campo.",
     "F016 p.106 PDF124 (ausente) / F150 p.106 PDF124 (presente)",
     (("estabilidade_edificio", "15.7.3"),
      ("estrutura_casa", "15.7.3"), ("fundacao_edificio", "15.7.3"))),
    ("15.8", "IGUAL",
     "Esbeltez lambda<=200, pouco comprimido <0,10 fcdAc, lambda1, 15.8.3: "
     "iguais pre-Emenda (o 'de calculo' e da Emenda, item 32). Formulas = "
     "ver imagem.",
     "F016 p.107 / F150 p.107",
     (("pilar_concreto", "15.8"), ("pilar_continuo", "15.8"),
      ("galpao_concreto", "15.8"))),
    ("17.2.2", "IGUAL",
     "Hipoteses a/b/c + bloco parabola-retangulo: prosa igual; miolo "
     "simbolico = ver imagem.",
     "F016 p.120 / F150 p.120",
     (("pilar_concreto", "17.2.2"), ("fundacao_sapata", "17.2.2"),
      ("escada_concreto", "17.2.2"))),
    ("17.2.5", "IGUAL",
     "Flexao composta obliqua (interacao): prosa e numeros iguais. Formula "
     "= ver imagem.",
     "F016 p.125 / F150 p.125", (("pilar_concreto", "17.2.5"),)),
    ("17.3.2", "IGUAL",
     "Deformacao/Branson + 17.3.2.1.2 fluencia (1+alfa_f): numeros iguais; "
     "Fig.17.3 ponderada e da Emenda (item 34). Formulas/figura = ver "
     "imagem.",
     "F016 p.126 / F150 p.126",
     (("laje_concreto", "17.3.2"), ("viga_baldrame", "17.3.2"),
      ("vibracao_piso", "17.3.2"), ("escada_concreto", "17.3.2"),
      ("desempenho_nbr15575", "17.3.2"))),
    ("17.3.3.2", "IGUAL",
     "Fissuracao wk: prosa igual pre-Emenda (centroide/protensao e da "
     "Emenda, item 35). Formulas = ver imagem.",
     "F016 p.128-129 / F150 p.129-130",
     (("fissuracao_nbr6118", "17.3.3.2"),)),
    ("17.3.5.2.4", "IGUAL",
     "As+As'<=4% Ac + dutilidade 14.6.4.3: identicos ('garantidas' -> "
     "'asseguradas', 'A soma' -> 'As somas' na Emenda, item 36).",
     "F016 p.132 / F150 p.133", (("laje_concreto", "17.3.5.2.4"),)),
    ("17.3.5.3", "IGUAL",
     "Pilar 0,15Nd/fyd>=0,004Ac e 0,08Ac: identicos. Formulas = ver imagem.",
     "F016 p.132-133 / F150 p.133", (("pilar_concreto", "17.3.5.3"),)),
    ("17.4", "IGUAL",
     "Cortante VRd2/VRd3, Modelo I/II, Vc, al: numeros iguais. Formulas = "
     "ver imagem.",
     "F016 p.133-138 / F150 p.134-139",
     (("pilar_concreto", "17.4"), ("viga_baldrame", "17.4"),
      ("viga_equilibrio", "17.4"), ("sapata_divisa", "17.4"),
      ("viga_concreto", "17.4"), ("viga_protendida", "17.4"))),
    ("17.5", "IGUAL",
     "Torcao he=A/u, trelica 30-45graus: iguais pre-Emenda (o he alternativo"
     " e da Emenda, item 38). Formulas/figura = ver imagem.",
     "F016 p.139 / F150 p.139-140",
     (("torcao_nbr6118", "17.5"), ("viga_concreto", "17.5"))),
    ("18.2.4", "REGRA-MUDA",
     "Flambagem 20phit, ganchos 90-180graus, Fig.18.2: numeros iguais; "
     "frases NOVAS na 2023: 18.2.3 'Deve-se verificar tambem os efeitos... "
     "no banzo comprimido.' + 18.2.4 'O estribo suplementar deve atender ao"
     " minimo estabelecido em 18.4.3...'. Confirmado F016 p.146 PDF164 x "
     "F150 p.147 PDF165. Detalhamento, sem numero.",
     "F016 p.146 PDF164 / F150 p.147 PDF165",
     (("executivo_concreto", "18.2.4"), ("pilar_concreto", "18.3"))),
    ("18.3", "IGUAL",
     "Vigas 18.3.1 (l/h>=2,0/>=3,0), 18.3.2/18.3.3 (inclui 18.3.3.2 "
     "espacamentos): iguais pre-Emenda (a barra de amarracao e da Emenda, "
     "item 42). Figura = ver imagem.",
     "F016 p.147-150 / F150 p.147-150",
     (("executivo_concreto", "18.3"), ("pilar_concreto", "18.3"),
      ("viga_baldrame", "18.3"), ("sapata_divisa", "18.3"),
      ("viga_equilibrio", "18.3"))),
    ("18.4.3", "IGUAL",
     "Pilar estribos (5mm, 1/4 phi, 135graus C55 a C90, espacamentos): iguais.",
     "F016 p.153 / F150 p.153",
     (("desenho_concreto", "18.4.3"), ("desenho_pavimento", "18.4.3"),
      ("executivo_concreto", "18.4.3"))),
    ("19.3.3", "IGUAL",
     "Laje armaduras max/min (Tab.19.1, 17.3.5): prosa igual; tabela = ver "
     "imagem.",
     "F016 p.157-159 / F150 p.159-160", (("escada_concreto", "19.3.3"),)),
    ("19.4.1", "IGUAL",
     "Laje sem armadura cortante VRd1: prosa igual; formula = ver imagem.",
     "F016 p.158-160 / F150 p.160-162", (("escada_concreto", "19.4.1"),)),
    ("19.5", "IGUAL",
     "Puncao C/C'/C'', K Tab.19.2, 1,5FSd: iguais pre-Emenda (C'' "
     "condicional e da Emenda, item 46). Formulas/tabelas/figuras = ver "
     "imagem.",
     "F016 p.160-168 / F150 p.162-171",
     (("puncao_nbr6118", "19.5"), ("fundacao_sapata", "19.5"),
      ("estaca_profunda", "19.5"))),
    ("20.1", "IGUAL",
     "Laje prescricoes (h/8, 2h/20cm, 20%/33cm): iguais pre-Emenda (o "
     "'positiva' e da Emenda, item 47). Figura 20.1 nova e da Emenda.",
     "F016 p.169 / F150 p.172",
     (("escada_concreto", "20.1"), ("laje_concreto", "20.1"))),
    ("20.2", "IGUAL",
     "Bordas/aberturas + Fig.20.1: prosa igual pre-Emenda; figura = ver "
     "imagem.",
     "F016 p.169 / F150 p.172", (("compatibilizacao", "20.2"),)),
    ("21.3", "IGUAL",
     "Furos/aberturas bielas (21.3.1/21.3.3 b/3 Fig.21.5/21.3.4): iguais. "
     "Figuras = ver imagem.",
     "F016 p.176-178 / F150 p.179-181", (("compatibilizacao", "21.3"),)),
    ("22.3", "IGUAL",
     "Bielas fcd1/fcd2/fcd3 (0,85/0,72) + limite 2,0: iguais pre-Emenda (a "
     "reescrita CCC/CTT e da Emenda, item 50). Formulas = ver imagem.",
     "F016 p.180-181 / F150 p.183-184",
     (("estaca_profunda", "22.3"),)),
    ("22.6", "IGUAL",
     "Sapatas rigidas h>=(a-ap)/3 (22.6.1/22.6.2.2): iguais. Formulas = ver "
     "imagem.",
     "F016 p.188-189 / F150 p.191-192",
     (("fundacao_sapata", "22.6"),)),
    ("Tab.A.1", "IGUAL",
     "Fluencia/retracao tipicos Tab.A.1: iguais (o Anexo A exato Ec28->Eci e"
     " da Emenda, finais). Tabela = ver imagem.",
     "F016 p.209-213 / F150 p.211-219",
     (("perdas_protensao_nbr6118", "Tab.A.1"),)),
)

# Familias congeladas nos dois sentidos (mesma particao do G116 para
# compatibilidade; o teste prova igualdade de conjuntos).
FAMILIAS_G122 = tuple(f for f, _v, _d, _p, _m in CONFRONTO_G122)

# Mapa modulo -> familias (para o portao cobrar cada citacao; "geral" cobre
# mencoes sem clausula). Congelado: modulo novo que cite 6118 sem estar aqui
# = vermelho; modulo daqui sumido do inventario = vermelho.
MODULOS_POR_FAMILIA = tuple(
    (fam, tuple(sorted({m for m, _c in mods})))
    for fam, _v, _d, _p, mods in CONFRONTO_G122
)

# G124: LIMITE_FORMULA_TABELA removido (residuo: lista de escopo sem
# consumidor; o limite por familia segue no campo de limite de cada entrada
# do CONFRONTO_G122; cobre_inventario nao a lia e nao e' tocado).


def _dobra(texto):
    """Dobra acentos/maiusculas para o portao substring."""
    sem = "".join(c for c in unicodedata.normalize("NFD", texto)
                  if unicodedata.category(c) != "Mn")
    return sem.lower()


def cobre_inventario(texto_inventario):
    """Portao do inventario G122: cada familia e cada modulo precisa
    aparecer no texto; cada familia NUMERO-MUDA/REGRA-MUDA precisa vir com
    endereco arquivo:linha (".py:"); o OK por item chega ao veredito global.
    Acumuladores (faltando_*) disparam de verdade (convencao 7)."""
    dobrado = _dobra(texto_inventario)
    fams = {f: (_dobra(f) in dobrado) for f in FAMILIAS_G122}
    # modulo aparece como substring "nome_modulo" no inventario
    mods = {}
    for fam, mlns in MODULOS_POR_FAMILIA:
        for m in mlns:
            if m not in mods:
                mods[m] = (m in texto_inventario)
    # divergentes exigem endereco arquivo:linha perto da familia: simplifica
    # para "familia presente E '.py:' presente no texto" + familia marcada.
    # (O teste de injecao remove a linha da familia, derrubando os dois.)
    # G125 (auditoria do G122): o endereco e cobrado NA LINHA da familia
    # ("- <familia> | arquivo.py:linha"). Antes bastava um ".py:" em
    # qualquer lugar do texto - um unico endereco satisfazia todas as
    # divergentes, e apagar o da 8.2.5 nao acusava nada.
    divs = {}
    for fam, ver, _det, _pg, _ml in CONFRONTO_G122:
        if ver in ("NUMERO-MUDA", "REGRA-MUDA"):
            padrao = re.compile(r"^-\s*" + re.escape(fam) + r"\s*\|(.*)$",
                                re.MULTILINE)
            divs[fam] = any(".py:" in m.group(1)
                            for m in padrao.finditer(texto_inventario))
    # OK por item: familia presente E (se divergente, com endereco)
    itens = {}
    for fam, ver, _det, _pg, _ml in CONFRONTO_G122:
        if ver in ("NUMERO-MUDA", "REGRA-MUDA"):
            itens[fam] = bool(fams[fam] and divs[fam])
        else:
            itens[fam] = bool(fams[fam])
    faltando_fams = sorted(k for k, v in fams.items() if not v)
    faltando_mods = sorted(k for k, v in mods.items() if not v)
    sem_endereco = sorted(k for k, v in divs.items() if not v)
    ok = (all(fams.values()) and all(mods.values())
          and all(itens.values()) and all(divs.values())
          and len(fams) == len(CONFRONTO_G122))
    return {"familias": fams, "modulos": mods, "divergentes": divs,
            "itens": itens, "faltando_familias": faltando_fams,
            "faltando_modulos": faltando_mods, "sem_endereco": sem_endereco,
            "ok": bool(ok)}


#: G125: modulos que CITAM a 8.2.5 sem calcular fct,m (desenho da folha).
CITAM_SEM_CALCULAR_8_2_5 = ("desenho_piso",)

_RE_FCTM_C55 = re.compile(
    r"2\.12\s*\*\s*math\.log\(\s*1(?:\.0)?\s*\+\s*0\.11\s*\*")


def sites_formula_fctm(raiz=None):
    """Modulos de producao que CALCULAM fct,m C55+ pela formula de 2014.

    G125 (auditoria do G122): o item NUMERO-MUDA listava 6 modulos e a
    formula morava em 11 - o inventario partiu das citacoes de "6118", e
    quem cita so "8.2.5" na linha da conta ficou de fora. Esta varredura
    procura a CONTA, nao a citacao. Devolve {modulo: [linhas]}."""
    base = pathlib.Path(raiz) if raiz is not None else pathlib.Path(
        __file__).resolve().parent
    achados = {}
    for caminho in sorted(base.glob("*.py")):
        if caminho.name == pathlib.Path(__file__).name:
            continue
        try:
            linhas = caminho.read_text(encoding="utf-8",
                                       errors="replace").splitlines()
        except OSError:
            continue
        for i, linha in enumerate(linhas, 1):
            codigo = linha.split("#", 1)[0]
            if _RE_FCTM_C55.search(codigo):
                achados.setdefault(caminho.stem, []).append(i)
    return achados


def confere_sites_8_2_5(raiz=None):
    """Conta x inventario da 8.2.5, nos dois sentidos (convencao 7).

    `nao_inventariados`: modulo que calcula a formula e nao esta no item;
    `sem_formula`: modulo do item (fora dos que so citam) sem a conta."""
    sites = sites_formula_fctm(raiz)
    item = dict((f, mods) for f, _v, _d, _p, mods in CONFRONTO_G122)["8.2.5"]
    listados = {m for m, _c in item}
    calculam = listados - set(CITAM_SEM_CALCULAR_8_2_5)
    nao_inv = sorted(set(sites) - listados)
    sem_formula = sorted(calculam - set(sites))
    return {"sites": sites, "nao_inventariados": nao_inv,
            "sem_formula": sem_formula,
            "OK": not (nao_inv or sem_formula)}


def caso_c5_fctm_c60():
    """8.2.5: fct,m aos 60 MPa. 2014: 2,12*ln(1+0,11*fck). 2023 pre-Emenda:
    2,12*ln[1+0,1*(fck+8)]. O numero 2014 vem da funcao REAL."""
    import premoldado_nbr9062 as pm
    fck_MPa = 60.0
    f2014 = float(pm._fctm(fck_MPa * 1000.0)) / 1000.0
    f2023 = 2.12 * math.log(1.0 + 0.1 * (fck_MPa + 8.0))
    return {"fctm_2014_MPa": float(f2014),
            "fctm_2023_MPa": float(f2023)}


def main() -> int:
    print("familias=%d divergentes=%d"
          % (len(FAMILIAS_G122),
             sum(1 for _f, v, _d, _p, _m in CONFRONTO_G122
                 if v in ("NUMERO-MUDA", "REGRA-MUDA"))))
    c5 = caso_c5_fctm_c60()
    print("C5 fctm C60: 2014=%.3f 2023=%.3f MPa"
          % (c5["fctm_2014_MPa"], c5["fctm_2023_MPa"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
