# ============================================================================
# entrega_rev02.py - DOCUMENTOS DE ENTREGA DA REV.02 DO TANQUE-BASE
#   01 memoria de calculo (PDF)
#   02 relatorio de alteracoes REV.01 -> REV.02 (PDF)
# As pranchas, o modelo IFC e os renders saem de pranchas_tanque.py (Bonsai).
# Todo numero impresso vem de projeto_rev02.calcular(): nada e' digitado aqui.
# ============================================================================
"""Gera a pasta de entrega da REV.02 do tanque-base integral."""

import os
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import projeto_rev02 as P   # noqa: E402
import tanque_base as TB    # noqa: E402

AVISO = ("Documento preparado para revisão e assinatura de profissional legalmente "
         "habilitado. Não liberado para fabricação sem ART/RRT.")
_E = getSampleStyleSheet()
_N = ParagraphStyle("n", parent=_E["Normal"], fontSize=9, leading=12)
_C = ParagraphStyle("c", parent=_N, fontSize=7.5, leading=9.5)
_H = ParagraphStyle("h", parent=_E["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4,
                    textColor=colors.HexColor("#1f3a5f"))
_T = ParagraphStyle("t", parent=_E["Title"], fontSize=16, spaceAfter=4)


def _n(x, casas=1):
    return ("%.*f" % (casas, x)).replace(".", ",")


def _tab(linhas, larguras, cabecalho=True):
    dados = [[Paragraph(str(c), _C) for c in lin] for lin in linhas]
    t = Table(dados, colWidths=[w * mm for w in larguras], repeatRows=1 if cabecalho else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
              ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if cabecalho:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe6ee")))
    t.setStyle(TableStyle(estilo))
    return t


def _pdf(caminho, titulo, subtitulo, corpo, doc_id):
    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 12 * mm, AVISO)
        canvas.drawString(18 * mm, 8.5 * mm, "%s | pág. %d" % (doc_id, doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm, title=titulo)
    doc.build([Paragraph(titulo, _T), Paragraph(subtitulo, _N), Spacer(1, 6)] + corpo,
              onFirstPage=rodape, onLaterPages=rodape)


def _p(texto):
    return Paragraph(texto, _N)


def _lista(itens):
    return [Paragraph("&bull; " + i, _N) for i in itens]


# ---------------------------------------------------------------------------
def memoria(res, caminho):
    spec, g, cap, m = res["spec"], res["geometria"], res["capacidade"], res["massas"]
    ad, b, r, rsp = spec["adotado"], res["barras"], res["reacoes"], res["respiro"]
    q, ch = spec["tubo_quadro"], spec["chapas"]
    ti = spec["tubo_travessa_inf"]
    tq, tt = TB.tubo_retangular(q), TB.tubo_retangular(ti)
    c = []

    c += [Paragraph("1. Objeto e concepção", _H), _p(
        "Base sanitária integral sob contêiner marítimo transformado de 20 pés: reservatório "
        "estanque de acumulação temporária de esgoto, esvaziado por sucção, montado dentro de "
        "uma gaiola de tubos de aço que recebe o contêiner pelos quatro cantos. A chapa do "
        "tanque não recebe carga do contêiner."),
        _p("A concepção segue o produto de série equivalente do mercado (tanque de dejetos "
           "CONTAINEX para cabines sanitárias de 20 pés, descrição técnica de 22.02.2024): "
           "longarinas inferiores e superiores, apoio em 6 pontos de fundação para o módulo "
           "de 20 pés, altura de 690 mm, capacidade de até 7 m³, cones de centragem nos cantos, "
           "movimentação somente vazio e ensaio de estanqueidade em fábrica. As espessuras "
           "desta REV.02 são maiores que as do produto de série (fundo e laterais de 3 mm, "
           "tampa de 1,5 mm), por margem de corrosão e para suportar a pressão de projeto.")]

    c += [Paragraph("2. Normas e fontes", _H)] + _lista([
        "NR-24, Anexo IV (Portaria MTE 1.591, de 08/09/2026): item 3.2.2 a) projeto por "
        "profissional legalmente habilitado; item 4.1.1 base capaz de suportar o peso próprio "
        "e a carga de utilização; item 4.4.2 esgoto ligado à rede ou a sistema sem risco à saúde.",
        "NR-24, item 24.2.4.4 (Portaria MTE 1.590, de 08/09/2026): respiro do compartimento de "
        "dejetos com saída acima da cobertura do módulo (adotado por analogia).",
        "ISO 1496-1:2013: 5.3.1 contêiner apoiado só pelos cantos inferiores; 5.3.4 flecha de "
        "até 6 mm da base abaixo do plano dos cantos.",
        "ISO 668:2020 e Amd.1:2022: Tabela 2 (6.058 x 2.438 mm; massa bruta máxima R = 36.000 "
        "kg) e Tabela A.1 (centros dos cantos S = 5.853 mm, P = 2.259 mm).",
        "ABNT NBR 8800:2024 (Er1:2025): resistências de cálculo de barras, chapas e soldas.",
        "ABNT NBR 8261:2019: tubos retangulares; Tabela 4 (escoamento), 4.6.6 (raio de canto).",
        "ASTM A36/A36M-19: chapas, escoamento mínimo de 250 MPa.",
        "ABNT NBR 6123:2023: vento; Figura 1 (velocidade básica), Tabela 3 (S2), Tabela 4 (S3) "
        "e Figura 4 (coeficiente de arrasto).",
        "ABNT NBR 6122:2022: 7.3 (a tensão admissível do terreno vem de ensaio ou de "
        "investigação) e 7.7.1 (sapata com no mínimo 60 cm de lado).",
        "AWS D1.1:2025 (soldagem) e ABNT NBR NM 334:2012 (líquido penetrante).",
        "ISO 12944-2:2017 e ISO 12944-5:2019: classificação de ambiente e sistemas de pintura.",
        "NR-33: o projeto não prevê entrada de pessoa no reservatório.",
    ])

    c += [Paragraph("3. Premissas adotadas (a confirmar)", _H), _p(
        "Os valores abaixo não vêm de norma. Foram adotados com margem, a partir da prática de "
        "mercado, e devem ser confirmados pelo responsável técnico e pelo cliente."),
        _tab([["Premissa", "Valor", "Origem"],
              ["Pressão de projeto do tanque (sobrepressão e depressão)",
               "%s kPa" % _n(ad["pressao_projeto_kPa"]),
               "Tanque atmosférico com respiro permanente; cobre transbordo até 0,5 m acima "
               "da tampa e a depressão da sucção"],
              ["Sobre-espessura de corrosão", "%s mm" % _n(ad["corrosao_mm"]),
               "Descontada de todas as chapas nas verificações"],
              ["Carga de serviço máxima por canto", "%s kN" % _n(ad["carga_canto_kN"], 0),
               "Vai para a placa de identificação; o produto de série declara 30 kN"],
              ["Massa do contêiner transformado", "%s kg" % _n(ad["massa_conteiner_kg"], 0),
               "Estimativa para as reações de fundação; conferir placa CSC e pesagem"],
              ["Sobrecarga de uso no piso do contêiner",
               "%s kN/m²" % _n(ad["sobrecarga_piso_kPa"]),
               "Conferir na Tabela 10 da ABNT NBR 6120:2019"],
              ["Fator dinâmico no içamento", _n(ad["fator_dinamico_icamento"]), "Adotado"],
              ["Vazão de ar do caminhão de sucção",
               "%s m³/h" % _n(ad["vazao_ar_caminhao_m3h"], 0),
               "Bomba de vácuo típica de limpa-fossa (275 a 325 m³/h); confirmar com o operador"],
              ["Massa específica do efluente", "%s kg/m³" % _n(spec["rho_efluente"], 0),
               "Igual à da água"],
              ["Coeficientes de ponderação", "1,25 e 1,50",
               "Peso próprio do aço (NBR 8681:2025, Tabela 1) e ações variáveis; o líquido "
               "entra como variável"],
              ["Espessura de cálculo dos tubos", "%s da nominal"
               % _n(ad["fator_espessura_tubo"], 3),
               "A NBR 8261 (4.6.3) admite parede 12,5% mais fina; as resistências usam a "
               "parede reduzida"],
              ["Massa mínima do contêiner, para a estabilidade ao vento",
               "%s kg" % _n(ad["massa_conteiner_minima_kg"], 0),
               "Tara de um contêiner de 20 pés sem a transformação (referência de mercado); "
               "conferir placa CSC"],
              ["Peso próprio da placa de apoio no terreno",
               "%s%% da carga" % _n((ad["fator_peso_proprio_apoio"] - 1) * 100, 0), "Adotado"],
              ["Ângulo mínimo do cabo de içamento", "%s graus com a horizontal"
               % _n(ad["angulo_cabo_icamento_graus"], 0), "Prática do produto de série"],
              ["Piso do contêiner acima do plano dos cantos",
               "%s mm" % _n(ad["piso_conteiner_acima_dos_cantos_mm"], 0),
               "A medir no contêiner real; define a escada"]],
             [62, 26, 86])]

    ce, le, ae = g["tanque_ext"]
    ci, li, ai = g["interno"]
    c += [Paragraph("4. Geometria", _H),
          _tab([["Elemento", "Dimensão (mm)", "Observação"],
                ["Envelope da base", "%s x %s x %s" % (_n(spec["skid"]["comp"], 0),
                 _n(spec["skid"]["larg"], 0), _n(spec["skid"]["alt"], 0)),
                 "Projeção do contêiner 1CC (ISO 668); conferir no contêiner real"],
                ["Tanque, externo", "%s x %s x %s" % (_n(ce, 0), _n(le, 0), _n(ae, 0)),
                 "Folga de %s mm até os tubos" % _n(spec["folga_lateral"], 0)],
                ["Tanque, interno", "%s x %s x %s" % (_n(ci), _n(li), _n(ai)), ""],
                ["Baia técnica", _n(spec["baia_tecnica"], 0), "Comprimento útil, na traseira"],
                ["Topo da gaiola abaixo do plano dos cantos",
                 _n(spec["folga_sob_conteiner"], 0), "ISO 1496-1 5.3.4 admite 6 mm de flecha"],
                ["Longarinas, testeiras e montantes",
                 "tubo %s x %s x %s" % (_n(q["h"], 0), _n(q["b"], 0), _n(q["t"], 2)),
                 "NBR 8261 grau %s; %s kg/m" % (spec["grau_tubo"], _n(tq["massa_kg_m"]))],
                ["Travessas: inferiores em pé, superiores deitadas",
                 "tubo %s x %s x %s" % (_n(ti["h"], 0), _n(ti["b"], 0), _n(ti["t"], 2)),
                 "%d por nível, passo de %s mm; %s kg/m" % (g["n_travessas"], _n(g["passo"], 0),
                                                           _n(tt["massa_kg_m"]))],
                ["Chapas (ASTM A36)", "fundo %s; laterais %s; tampa %s" % (
                    _n(ch["fundo"], 2), _n(ch["lateral"], 2), _n(ch["tampa"], 2)), ""],
                ["Vão das longarinas", _n(g["vao_longarina"]),
                 "Dois vãos: canto, meio, canto (6 pontos de apoio)"]],
               [58, 50, 66])]

    lin = [["Nível", "%", "Volume (m³)", "Lâmina (mm)", "Função"]]
    func = {"alerta": "Programar sucção", "alarme_alto": "Limite operacional",
            "alarme_alto_alto": "Interromper o uso"}
    for nome, d in cap["niveis"].items():
        lin.append([nome.replace("_", " "), _n(d["fracao"] * 100, 0), _n(d["volume_m3"], 2),
                    _n(d["lamina_mm"], 0), func.get(nome, "")])
    lin.append(["cheio", "100", _n(cap["volume_m3"], 2), _n(ai, 0), "Não é capacidade operacional"])
    c += [Paragraph("5. Capacidade", _H), _tab(lin, [34, 14, 28, 28, 70]), _p(
        "Com a geração da memória do cliente (%s m³ por turno de 8 h, 100 usuários), o limite "
        "operacional de 80%% é atingido em %s turnos."
        % (_n(spec["geracao_m3_por_turno"], 2), _n(cap["turnos_ate_alarme_alto"])))]

    lin = [["Item", "Massa (kg)"]] + [[k, _n(v, 0)] for k, v in m["itens"].items()]
    lin += [["Acessórios (10% adotado)", _n(m["acessorios_kg"], 0)],
            ["Base vazia, total", _n(m["aco_kg"] + m["acessorios_kg"], 0)],
            ["Efluente com o tanque cheio", _n(m["efluente_cheio_kg"], 0)]]
    c += [Paragraph("6. Massas", _H), _tab(lin, [100, 30])]

    lin = [["Verificação", "Solicitante", "Resistente", "Un.", "S/R", "Situação", "Critério"]]
    for v in res["verificacoes"]:
        sit = "atende" if v["ok"] else "NÃO ATENDE"
        if v.get("informativo"):
            sit += " (informativo)"
        lin.append([v["nome"], _n(v["sd"], 2), _n(v["rd"], 2), v["unid"], _n(v["razao"], 2),
                    sit, v["ref"]])
    c += [Paragraph("7. Verificações", _H), _tab(lin, [50, 18, 18, 10, 11, 20, 47]), _p(
        "A longarina inferior não resiste ao tanque cheio apoiada só nos quatro cantos. "
        "<b>Os dois apoios no meio dos lados longos são obrigatórios</b>; é a mesma exigência "
        "do produto de série de 20 pés."),
        _p("Montante de canto: resistência à compressão de %s kN (lambda0 = %s); o centro do "
           "canto ISO fica a %s mm e %s mm do eixo do tubo, e o momento dessa excentricidade "
           "está na verificação." % (_n(b["N_Rd_kN"], 0), _n(b["lambda0"], 2),
                                     _n(abs(b["excentricidade_mm"][0])),
                                     _n(abs(b["excentricidade_mm"][1])))),
        _p("Flechas sem majoração: tampa %s mm e fundo %s mm entre travessas, sob a pressão de "
           "projeto; travessa inferior %s mm com o tanque cheio em operação normal e %s mm "
           "(vão/%s) no caso de transbordo; travessa superior %s mm sob a pressão de projeto."
           % (_n(res["verificacoes"][0]["flecha_mm"]), _n(res["verificacoes"][1]["flecha_mm"]),
              _n(res["verificacoes"][3]["flecha_normal_mm"]),
              _n(res["verificacoes"][3]["flecha_mm"]),
              _n(res["verificacoes"][3]["vao_sobre_flecha"], 0),
              _n(res["verificacoes"][5]["flecha_mm"])))]

    c += [Paragraph("8. Respiro e proteção contra vácuo", _H), _p(
        "O caso crítico é o fim do esvaziamento: o pescador descobre e o caminhão passa a puxar "
        "ar através do tanque. Com respiro DN%s e %s m³/h de ar, a depressão estimada é de %s kPa "
        "(velocidade de %s m/s), contra %s kPa de projeto. O respiro deixa de bastar acima de "
        "cerca de %s m³/h de ar." % (
            _n(ad["d_respiro_mm"], 0), _n(ad["vazao_ar_caminhao_m3h"], 0),
            _n(rsp["depressao_kPa"], 2), _n(rsp["velocidade_m_s"]),
            _n(ad["pressao_projeto_kPa"]), _n(rsp["vazao_limite_m3h"], 0)))] + _lista([
        "Respiro DN100 permanente, sem válvula, saindo pela tampa do tanque e subindo por "
        "um shaft dentro do contêiner até acima da cobertura. Pela baia técnica ele ficaria "
        "abaixo do nível alto-alto: a tampa está a 65 mm do contêiner e as longarinas "
        "superiores fecham a faixa de cima.",
        "Válvula quebra-vácuo independente, com abertura total até %s kPa de depressão, em "
        "derivação no respiro, dentro do shaft: sobre a tampa não há altura para ela."
        % _n(ad["pressao_projeto_kPa"] / 2),
        "Um caminhão de sucção atinge 500 a 850 mbar de vácuo; nenhum tanque de paredes planas "
        "resiste a isso. Respiro obstruído com sucção ligada destrói o tanque: a inspeção do "
        "respiro antes de cada sucção é item obrigatório do procedimento.",
        "O cálculo de perda de carga é uma estimativa; confirmar com a vazão real do operador.",
    ])

    c += [Paragraph("9. Reações de apoio (serviço)", _H),
          _tab([["Parcela", "kN"],
                ["Base vazia", _n(r["base_kN"])], ["Efluente, tanque cheio", _n(r["efluente_kN"])],
                ["Contêiner (estimado)", _n(r["conteiner_kN"])],
                ["Uso do contêiner", _n(r["uso_kN"])], ["Total", _n(r["total_kN"])],
                ["Em cada um dos 4 cantos", _n(r["canto_kN"])],
                ["Em cada um dos 2 apoios do meio", _n(r["meio_kN"])],
                ["Canto, com a carga máxima da placa", _n(r["canto_placa_kN"])]], [100, 30]),
          _p("Seis pontos nivelados, um sob cada montante. O produto de série pede pontos de "
             "no mínimo 350 x 350 mm.")]

    loc, vt, est, ap = spec["local"], res["vento"], res["estabilidade"], res["apoios"]
    c += [Paragraph("9.1 Vento (ABNT NBR 6123:2023)", _H),
          _tab([["Parâmetro", "Valor", "Origem"],
                ["Local", loc["municipio"], "Informado pelo cliente"],
                ["Velocidade básica V0", "%s m/s" % _n(loc["v0"], 0),
                 "Figura 1: o município fica entre as isopletas de 30 e 35 m/s; adotada a "
                 "maior. Leitura de mapa, a conferir pelo responsável técnico"],
                ["Fator topográfico S1", _n(loc["s1"], 2), "5.2: terreno plano"],
                ["Fator S2", _n(vt["s2"], 2),
                 "Tabela 3: categoria %s, classe %s, altura até 5 m (o conjunto tem %s m)"
                 % (loc["categoria"], loc["classe"], _n(vt["h_m"], 2))],
                ["Fator estatístico S3", _n(loc["s3"], 2),
                 "Tabela 4, grupo 3 (inclui estruturas desmontáveis reutilizáveis)"],
                ["Velocidade característica Vk", "%s m/s" % _n(vt["vk_m_s"]), "4.2: V0.S1.S2.S3"],
                ["Pressão dinâmica q", "%s kPa" % _n(vt["q_kPa"], 3), "4.2: 0,613.Vk²"],
                ["Coeficiente de arrasto Ca", _n(loc["ca"]),
                 "Figura 4, vento na lateral: o ponto cai entre as curvas de 1,1 e 1,2; "
                 "adotada a maior"],
                ["Força na lateral do contêiner", "%s kN" % _n(vt["forca_conteiner_kN"]),
                 "4.3.3: q.Ca.A; passa pelos quatro montantes de canto"],
                ["Força na lateral do conjunto", "%s kN" % _n(vt["forca_total_kN"]),
                 "Base e contêiner tratados como um corpo fechado"]], [50, 28, 96]),
          _p("O contêiner foi tomado com %s mm de altura (ISO 668, tipo 1CC). Se for do tipo "
             "alto (high cube), a área exposta cresce e esta seção deve ser refeita."
             % _n(P.H_CONTEINER_1CC, 0)),
          _p("Estabilidade com o tanque vazio e o contêiner mais leve (%s kN no total): o "
             "momento de tombamento de cálculo é %s kN.m, contra %s kN.m estabilizantes; "
             "<b>não tomba</b>. Para não escorregar, o atrito entre os calços e o piso teria de "
             "ser de %s; esse valor não pode ser garantido para aço solto sobre "
             "concreto ou brita. <b>Os apoios precisam ser travados no piso para uma força "
             "horizontal de cálculo de %s kN no total</b> (batente, chumbador ou calço "
             "embutido na placa de apoio); o detalhe depende do piso do local."
             % (_n(est["peso_minimo_kN"]), _n(est["tombamento"]["sd"]),
                _n(est["tombamento"]["rd"]), _n(est["atrito_necessario"], 2),
                _n(est["forca_horizontal_sd_kN"])))]

    lin = [["Tensão admissível do terreno (kPa)", "Lado da placa quadrada (mm)"]]
    lin += [[_n(sg, 0), _n(lado, 0)] for sg, lado in ap["cenarios"]]
    if ap["lado_mm"]:
        situacao = ("Com a tensão admissível declarada de %s kPa, a placa de apoio tem %s mm "
                    "de lado." % (_n(ap["tensao_admissivel_kPa"], 0), _n(ap["lado_mm"], 0)))
    else:
        situacao = ("<b>A tensão admissível do terreno não foi declarada; a tabela é de "
                    "cenários, não um dimensionamento.</b> A ABNT NBR 6122 (7.3) manda fixá-la "
                    "por prova de carga ou por investigação do terreno.")
    c += [Paragraph("9.2 Apoio no terreno", _H), _p(
        "Maior carga de serviço num apoio: %s kN (canto com a carga máxima da placa, mais %s kN "
        "do vento). Sob o calço de %s x %s mm isso dá %s MPa."
        % (_n(ap["carga_max_kN"]), _n(ap["vento_canto_kN"]),
           _n(spec["detalhes"]["calco"]["comp"], 0), _n(spec["detalhes"]["calco"]["larg"], 0),
           _n(ap["pressao_calco_MPa"], 2))),
        _p("<b>Sobre piso de concreto:</b> essa pressão é pequena para o concreto em si. O que "
           "decide é a espessura do piso e a base sob ele, que precisam ser conhecidas para "
           "conferir a carga concentrada de cada apoio."),
        _p("<b>Sobre brita ou solo:</b> o calço não basta. Cada apoio precisa de uma placa de "
           "concreto, com o lado da tabela abaixo conforme o terreno (mínimo de %s mm pela "
           "ABNT NBR 6122, 7.7.1; a carga inclui %s%% de peso próprio da placa)."
           % (_n(P.LADO_MIN_SAPATA, 0), _n((ad["fator_peso_proprio_apoio"] - 1) * 100, 0))),
        _tab(lin, [70, 60]), _p(situacao)]

    c += [Paragraph("10. Especificações de fabricação", _H)] + _lista([
        "Soldas do envelope molhado: cordão contínuo, procedimento qualificado (AWS D1.1). "
        "Soldas estruturais em todo o contorno: filete de %s mm entre os tubos do quadro "
        "(mínimo da NBR 8800 para parede de 6,35 mm) e de %s mm nas travessas."
        % (_n(spec["perna_solda"], 0), _n(spec["perna_solda_travessa"], 0)),
        "Chapas do tanque nas travessas: filete intermitente de %s mm, trechos de %s mm a cada "
        "%s mm, dos dois lados da travessa." % (
            _n(spec["solda_chapa"]["perna"], 0), _n(spec["solda_chapa"]["trecho"], 0),
            _n(spec["solda_chapa"]["passo"], 0)),
        "Poço do pescador: caixa de %s x %s mm com %s mm de profundidade sob o fundo, no último "
        "vão entre travessas, junto à baia técnica; o tubo de sucção desce até 20 mm do fundo "
        "do poço." % (_n(spec["detalhes"]["poco"]["comp"], 0),
                      _n(spec["detalhes"]["poco"]["larg"], 0),
                      _n(spec["detalhes"]["poco"]["prof"], 0)),
        "Nível: transmissor hidrostático na parte baixa da testa e chave de nível alto-alto "
        "independente na cota de 90%, os dois dentro da baia técnica. Sensor ultrassônico "
        "sobre a tampa não cabe sob o contêiner.",
        "Chapas do tanque presas às travessas por solda externa; as travessas ficam fora do "
        "esgoto e substituem os diafragmas internos da REV.01.",
        "Inspeção visual de 100% das soldas de estanqueidade e líquido penetrante (NBR NM 334) "
        "nos cantos e nas conexões.",
        "Ensaio de estanqueidade com água até 0,5 m acima da tampa (coluna no respiro), sobre "
        "os seis apoios, por no mínimo 24 h. Não usar ensaio pneumático.",
        "Pintura interna: sistema para imersão indicado pelo fabricante da tinta para esgoto e "
        "H2S (ISO 12944-5, Tabela C.6). Referência de mercado: betume, 200 micrômetros.",
        "Pintura externa: categoria de corrosividade conforme o local (ISO 12944-2, Tabela 1). "
        "Referência de mercado: poliuretano, 80 a 100 micrômetros.",
        "Cantos: chapa de topo de %s x %s x %s mm (indicativa) sobre cada montante de canto, "
        "com cone de centragem ou twistlock compatível com ISO 1161, centrado em S = 5.853 mm "
        "e P = 2.259 mm. Só as chapas de topo tocam o contêiner."
        % (_n(spec["detalhes"]["chapa_topo"]["comp"], 0),
           _n(spec["detalhes"]["chapa_topo"]["larg"], 0),
           _n(spec["detalhes"]["chapa_topo"]["t"])),
        "Conexões: sucção DN%s com pescador, lavagem DN%s e boca de inspeção de %s x %s mm "
        "(flange cega) na testa do tanque, dentro da baia técnica; %d entradas de esgoto DN%s "
        "e o respiro pela tampa, no meio dos vãos entre travessas. Dimensões indicativas."
        % (_n(spec["detalhes"]["dn_succao"], 0), _n(spec["detalhes"]["dn_lavagem"], 0),
           _n(spec["detalhes"]["boca_inspecao"]["larg"], 0),
           _n(spec["detalhes"]["boca_inspecao"]["alt"], 0),
           spec["detalhes"]["n_entradas"], _n(spec["detalhes"]["dn_entrada"], 0)),
        "Içamento: somente vazio, pelos quatro cantos superiores, com cabos a no mínimo %s "
        "graus da horizontal. Quatro olhais de chapa de %s mm soldados nas faces de topo dos "
        "montantes de canto, cada um para %s kN de cálculo no cabo; eles passam %s mm do "
        "comprimento da base em cada ponta." % (_n(spec["detalhes"]["olhal"]["t"], 0),_n(ad["angulo_cabo_icamento_graus"], 0),
                              _n([v for v in res["verificacoes"]
                                  if "ponto_de_icamento_kN" in v][0]["ponto_de_icamento_kN"]),
                              _n(spec["detalhes"]["olhal"]["proj"], 0)),
        "Apoio: um calço de %s x %s x %s mm sob cada montante, travado no piso contra o "
        "vento (seção 9.1)." % (
            _n(spec["detalhes"]["calco"]["comp"], 0), _n(spec["detalhes"]["calco"]["larg"], 0),
            _n(spec["detalhes"]["calco"]["t"])),
        "Acesso: %d espelhos de %s mm e pisos de %s mm até o piso do contêiner (NBR 9050, "
        "6.8.2), para um desnível de %s mm, com corrimãos a 0,70 m e 0,92 m dos dois lados "
        "(6.9.2). Banzos e fixação da escada são indicativos."
        % (res["acesso"]["espelhos"], _n(res["acesso"]["espelho_mm"], 0),
           _n(res["acesso"]["piso_mm"], 0), _n(res["acesso"]["desnivel_mm"], 0)),
        "Placa: volumes, massa vazia, carga máxima por canto, 'TRANSPORTAR SOMENTE VAZIO' e "
        "'APOIAR EM 6 PONTOS'.",
    ])

    lin = [["Junta", "Tipo", "Perna (mm)", "Qtd x compr. (mm)", "Observação"]]
    for junta, tipo, perna, qtd, comp, obs in res["juntas"]:
        lin.append([junta, tipo.capitalize(), _n(perna, 0), "%d x %s" % (qtd, _n(comp, 0)),
                    obs.capitalize()])
    c += [Paragraph("11. Soldas", _H), _p(
        "Tudo é soldado. O único item aparafusado é a tampa da boca de inspeção, que precisa "
        "abrir para inspeção e retoque."), _tab(lin, [48, 50, 16, 26, 34])]

    lin = [["Item", "Especificação", "Qtd"]]
    lin += [[i, e, str(q_)] for i, e, q_ in res["componentes"]]
    c += [Paragraph("12. Componentes comprados", _H), _tab(lin, [50, 108, 16])]

    c += [Paragraph("13. Sequência de fabricação", _H), _p(
        "A tampa soldada fecha o tanque e ninguém entra nele; por isso a pintura interna é "
        "feita antes do fechamento:")] + _lista([
        "Montar a gaiola inferior: longarinas, testeiras, montantes e travessas inferiores.",
        "Soldar fundo, laterais, testas, poço e bocais, com o tanque ainda aberto em cima.",
        "Jatear e pintar o interior do tanque aberto.",
        "Em bancada, soldar a chapa da tampa nas travessas superiores e pintar a face de baixo, "
        "deixando 30 mm sem tinta nas bordas.",
        "Posicionar a tampa, soldar as travessas superiores nas longarinas e fazer a solda de "
        "fechamento por fora.",
        "Retocar por dentro, pela boca de inspeção, a faixa junto à solda de fechamento. O que "
        "não for alcançado fica coberto pela sobre-espessura de corrosão de %s mm."
        % _n(ad["corrosao_mm"]),
        "Ensaio de estanqueidade, pintura externa, montagem dos componentes e placa.",
    ])

    c += [Paragraph("14. Pendências antes da liberação", _H)] + _lista([
        "Medir o contêiner real (comprimento, largura, posição dos cantos) e registrar a tara.",
        "Confirmar a vazão e o vácuo do caminhão de sucção contratado.",
        "Tensão admissível do terreno (ou espessura e base do piso de concreto) e, com ela, "
        "o projeto das placas dos seis apoios (seção 9.2).",
        "Detalhe do travamento horizontal dos apoios no piso (seção 9.1).",
        "Conferir a velocidade básica do vento lida no mapa e a categoria do terreno no local.",
        "Sistema de pintura fechado com o fabricante da tinta; preparo de superfície (ISO 8501-1).",
        "Compatibilizar com a planta do contêiner real a posição do respiro e das entradas "
        "de esgoto, que atravessam o piso.",
        "Fechar com o fabricante as dimensões das conexões, da boca de inspeção e das chapas "
        "de topo, que nas pranchas são indicativas.",
        "Validar com o fabricante da tinta a sequência de pintura da seção 13.",
        "Extravasor: não há. Se o alarme alto-alto falhar, o esgoto volta pelos ralos do "
        "contêiner; decidir se isso é aceitável.",
        "Rota acessível (rampa), se o módulo for de uso acessível.",
        "Revisão e ART/RRT de profissional legalmente habilitado.",
    ])
    _pdf(caminho, "Memória de cálculo - Tanque-base integral", spec["documento"]
         + " | Contêiner sanitário de 20 pés | Situação: para revisão do responsável técnico",
         c, spec["documento"])


# ---------------------------------------------------------------------------
def alteracoes(res, caminho):
    spec, g, cap, m, r = (res["spec"], res["geometria"], res["capacidade"], res["massas"],
                          res["reacoes"])
    v1 = TB.capacidade(TB.SPEC_REV01)
    e1 = TB.encaixe(TB.SPEC_REV01)["folgas"]
    ce, le, ae = g["tanque_ext"]
    so4 = [v for v in res["verificacoes"] if "4 cantos, tanque" in v["nome"]][0]
    lin = [["Item", "REV.01", "REV.02", "Por que mudou"],
           ["Altura da base", "600 mm", "%s mm" % _n(spec["skid"]["alt"], 0),
            "A estrutura sob o tanque (100 mm), a estrutura sobre a tampa (50 mm) e a folga sob "
            "o contêiner (15 mm) ocupam altura que a REV.01 não contava. 690 mm é a altura do "
            "produto de série."],
           ["Tanque em planta", "5.550 x 2.280 mm", "%s x %s mm" % (_n(ce, 0), _n(le, 0)),
            "O quadro da REV.01 não cabia ao lado do tanque: faltavam %s mm por lado e %s mm "
            "no comprimento." % (_n(-e1["lateral_por_lado_mm"], 0),
                                 _n(-e1["longitudinal_total_mm"], 0))],
           ["Altura do tanque", "550 mm", "%s mm" % _n(ae, 0), "Consequência da altura da base."],
           ["Volume cheio", "cerca de 6,5 m³ (bruto calculado: %s)" % _n(v1["volume_bruto_m3"], 2),
            "%s m³" % _n(cap["volume_m3"], 2),
            "Tanque menor em planta; a altura maior da base compensa só em parte."],
           ["Volume operacional (80%)", "cerca de 5,2 m³",
            "%s m³" % _n(cap["niveis"]["alarme_alto"]["volume_m3"], 2),
            "Idem. Cada 50 mm a mais na altura da base devolvem cerca de 0,46 m³ operacionais."],
           ["Autonomia até 80% (100 usuários por turno)", "cerca de 3,3 turnos",
            "%s turnos" % _n(cap["turnos_ate_alarme_alto"]), "Consequência do volume."],
           ["Estrutura", "Quadro perimetral e travessas",
            "Gaiola: longarinas e testeiras em dois níveis, 6 montantes",
            "A tampa precisa de apoio contra pressão e vácuo; a gaiola dá esse apoio por fora "
            "do esgoto. É o arranjo do produto de série."],
           ["Apoio no terreno", "Não definido (4 cantos)", "6 pontos obrigatórios",
            "Com o tanque cheio sobre 4 cantos, a longarina fica com %s vezes a resistência."
            % _n(so4["razao"], 2)],
           ["Travessas", "Tubo 100 x 50 x 4,75, passo de 500 a 700 mm",
            "Mesmo tubo, passo de %s mm: em pé sob o fundo, deitado sobre a tampa"
            % _n(g["passo"], 0),
            "Sob o fundo precisa dos 100 mm de altura para limitar a flecha; sobre a tampa "
            "basta deitado, que ocupa 50 mm."],
           ["Diafragmas internos", "Previstos", "Eliminados",
            "O transporte é só vazio e o produto de série não tem. Menos solda e menos aresta "
            "dentro do esgoto; a rigidez vem das travessas externas."],
           ["Tampa do tanque", "Rente ao contêiner",
            "%s mm abaixo do plano dos cantos" % _n(spec["skid"]["alt"] - g["z_tampa"], 0),
            "A base do contêiner pode descer 6 mm (ISO 1496-1, 5.3.4)."],
           ["Respiro", "Na baia técnica, subindo por fora",
            "Pela tampa, subindo por shaft dentro do contêiner",
            "Pela baia o tubo ficaria abaixo do nível alto-alto e não ventilaria o tanque "
            "cheio. A posição depende da planta do contêiner."],
           ["Pressão de projeto", "Não definida",
            "%s kPa, positiva e negativa" % _n(spec["adotado"]["pressao_projeto_kPa"]),
            "Sem esse número não se dimensiona chapa nem quebra-vácuo."],
           ["Aço", "'Aço estrutural'", "Tubos NBR 8261 grau %s; chapas ASTM A36"
            % spec["grau_tubo"], "Especificação para compra."],
           ["Poço do pescador", "Pedido, sem dimensão",
            "%s x %s x %s mm sob o fundo" % (_n(spec["detalhes"]["poco"]["comp"], 0),
                                              _n(spec["detalhes"]["poco"]["larg"], 0),
                                              _n(spec["detalhes"]["poco"]["prof"], 0)),
            "Cabe entre duas travessas inferiores, sem tocar o terreno."],
           ["Medição de nível", "Ultrassônico ou radar, mais contato alto-alto",
            "Transmissor hidrostático e chave alto-alto, na testa",
            "Sobre a tampa só há 65 mm até o contêiner."],
           ["Chapa de topo dos cantos", "Não definida",
            "%s x %s x %s mm, com cone ISO 1161" % (
                _n(spec["detalhes"]["chapa_topo"]["comp"], 0),
                _n(spec["detalhes"]["chapa_topo"]["larg"], 0),
                _n(spec["detalhes"]["chapa_topo"]["t"], 0)),
            "Verificada para a carga máxima por canto."],
           ["Tampa do tanque: fixação", "Não definida",
            "Soldada, pré-montada com as travessas superiores",
            "Decisão: tudo soldado. A pintura interna é feita antes do fechamento."],
           ["Içamento", "Pontos 'calculados', sem definição",
            "4 olhais de chapa de %s mm nas faces de topo" % _n(
                spec["detalhes"]["olhal"]["t"], 0),
            "Verificados. Passam %s mm do comprimento em cada ponta."
            % _n(spec["detalhes"]["olhal"]["proj"], 0)],
           ["Acesso", "Remetido ao projeto civil",
            "Escada de %d espelhos com corrimão" % res["acesso"]["espelhos"],
            "NBR 9050; depende da altura do piso do contêiner."],
           ["Soldas estruturais", "Não definidas",
            "Filete de %s mm no quadro e %s mm nas travessas" % (
                _n(spec["perna_solda"], 0), _n(spec["perna_solda_travessa"], 0)),
            "Perna mínima da NBR 8800 pela espessura da parede."],
           ["Carga por canto", "Não definida",
            "%s kN de serviço, na placa" % _n(spec["adotado"]["carga_canto_kN"], 0),
            "Limite de uso declarado."],
           ["Massa da base vazia", "Não informada",
            "cerca de %s kg" % _n(m["aco_kg"] + m["acessorios_kg"], 0), "Calculada."],
           ["Massa em serviço", "'Pode ultrapassar 10 t'",
            "cerca de %s t" % _n(r["total_kN"] / 9.80665),
            "Base, efluente cheio, contêiner estimado e uso."],
           ["Vento", "Não tratado",
            "ABNT NBR 6123:2023 para %s: %s kN na lateral do conjunto"
            % (res["spec"]["local"]["municipio"], _n(res["vento"]["forca_total_kN"])),
            "Não tomba, mas pode escorregar vazio: os apoios precisam de travamento no piso."],
           ["Portarias da NR-24", "Datadas de 11/09/2026", "08/09/2026",
            "Data que consta nos textos oficiais."]]
    c = [Paragraph("O que mudou", _H), _tab(lin, [28, 36, 42, 68])]
    c += [Paragraph("O que foi mantido", _H)] + _lista([
        "Projeção de 6.058 x 2.438 mm e apoio do contêiner pelos quatro cantos.",
        "Espessuras de chapa: fundo 6,35 mm; laterais e tampa 4,75 mm.",
        "Tubos 150 x 100 x 6,35 mm e 100 x 50 x 4,75 mm.",
        "Sucção DN100 com pescador, respiro DN100, lavagem DN32, sensor de nível com alarme "
        "alto-alto independente, baia técnica traseira de 400 mm.",
        "Níveis de 70%, 80% e 90%; transporte somente vazio; projeto sem entrada de pessoa.",
    ])
    c += [Paragraph("O que é fácil de alterar", _H), _p(
        "O cálculo é paramétrico. Mudar qualquer valor abaixo refaz a memória, este relatório "
        "e o desenho em segundos:")] + _lista([
        "Altura da base: 600 mm dá cerca de 3,9 m³ operacionais; 740 mm devolve os 5,2 m³ da "
        "REV.01 (a escada de acesso ganha um degrau).",
        "Espessuras de chapa. As do produto de série são bem menores; há folga para reduzir "
        "fundo e tampa se o custo pesar. A lateral é a mais solicitada.",
        "Passo das travessas, folgas, comprimento da baia técnica, carga por canto.",
    ])
    c += [Paragraph("O que ainda depende de terceiros", _H)] + _lista([
        "Medição e tara do contêiner real.", "Dados do caminhão de sucção.",
        "Tensão admissível do terreno ou dados do piso de concreto; placas de apoio e "
        "travamento.", "Sistema de pintura com o fabricante da tinta.",
        "Validação da sequência de pintura com o fabricante da tinta.",
        "Planta do contêiner: porta, shaft do respiro e passagens de esgoto pelo piso.",
        "Revisão e ART/RRT de profissional legalmente habilitado.",
    ])
    _pdf(caminho, "Relatório de alterações - REV.01 para REV.02", spec["documento"]
         + " | Tanque-base integral para contêiner sanitário de 20 pés", c, spec["documento"])


def gerar(pasta, spec=None):
    res = P.calcular(spec)
    os.makedirs(pasta, exist_ok=True)
    arqs = {"memoria": os.path.join(pasta, "01_Memoria_de_calculo_REV02.pdf"),
            "alteracoes": os.path.join(pasta, "02_Relatorio_de_alteracoes_REV01_para_REV02.pdf")}
    memoria(res, arqs["memoria"])
    alteracoes(res, arqs["alteracoes"])
    return res, arqs


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    res, arqs = gerar(os.path.join(raiz, "ENTREGA_TANQUE_BASE_REV02"))
    print("APROVADO" if res["aprovado"] else "REPROVADO")
    for a in arqs.values():
        print(a)
