# ============================================================================
# envio_cliente.py - PASTA UNICA PARA ENVIAR AO CLIENTE
# Junta o que ja' foi gerado (memoria, relatorio de alteracoes, pranchas, DXF,
# DWG, IFC, GLB, renders e video) numa pasta numerada e escreve o relatorio final,
# em linguagem de quem nao e' da area. Nada e' recalculado aqui alem dos
# numeros que o relatorio imprime, lidos de projeto_rev02.calcular().
# Pasta de um envio anterior e' renomeada (arquivada), nunca apagada.
# ============================================================================
"""Relatorio final e pasta de envio do tanque-base ao cliente."""

import glob
import os
import shutil
import sys
import time

from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entrega_rev02 as E   # noqa: E402
import projeto_rev02 as P   # noqa: E402

NOME_PASTA = "ENVIO_CLIENTE_TANQUE_BASE_REV02"


def _imagem(caminho, largura_mm):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(caminho).getSize()
    return Image(caminho, width=largura_mm * mm, height=largura_mm * mm * h / w)


def relatorio_final(res, caminho, render_base, render_conteiner):
    spec, g, cap, m, r, ad = (res["spec"], res["geometria"], res["capacidade"], res["massas"],
                              res["reacoes"], res["spec"]["adotado"])
    n, p, H, lista, tab = E._n, E._p, E._H, E._lista, E._tab
    ce, le, ae = g["tanque_ext"]
    vazio = m["aco_kg"] + m["acessorios_kg"]
    c = []

    c += [Paragraph("1. O que é", H), p(
        "Uma base de aço que fica embaixo do contêiner sanitário de 20 pés e guarda o esgoto "
        "até o caminhão limpa-fossa vir buscar. Ela tem duas partes: uma gaiola de tubos, que "
        "sustenta o contêiner pelos quatro cantos, e um tanque de chapa dentro da gaiola, que "
        "só guarda o esgoto e não recebe o peso do contêiner."),
        p("O conceito é o mesmo de um produto que já existe em série na Europa (tanque de "
          "dejetos para cabines sanitárias de 20 pés). Usamos esse produto como referência de "
          "como se faz na prática."),
        Spacer(1, 4), _imagem(render_conteiner, 150),
        Paragraph("A base com o contêiner em cima (contêiner transparente, só para referência).",
                  E._C)]

    c += [Paragraph("2. Números principais", H), tab([
        ["Item", "Valor"],
        ["Tamanho da base", "%s x %s mm, com %s mm de altura" % (
            n(spec["skid"]["comp"], 0), n(spec["skid"]["larg"], 0), n(spec["skid"]["alt"], 0))],
        ["Tamanho do tanque", "%s x %s x %s mm" % (n(ce, 0), n(le, 0), n(ae, 0))],
        ["Volume do tanque cheio", "%s m³" % n(cap["volume_m3"], 2)],
        ["Volume de trabalho (80%)", "%s m³" % n(cap["niveis"]["alarme_alto"]["volume_m3"], 2)],
        ["Autonomia até 80%", "cerca de %s turnos de 8 h com 100 usuários por turno"
         % n(cap["turnos_ate_alarme_alto"])],
        ["Peso da base vazia", "cerca de %s kg" % n(vazio, 0)],
        ["Peso do conjunto em uso", "cerca de %s toneladas (base, esgoto, contêiner e pessoas)"
         % n(r["total_kN"] / 9.80665)],
        ["Apoio no terreno", "6 pontos: os 4 cantos e 2 no meio dos lados compridos"],
        ["Carga máxima por canto", "%s kN (cerca de %s toneladas)" % (
            n(ad["carga_canto_kN"], 0), n(ad["carga_canto_kN"] / 9.80665))],
        ["Material", "Tubos de aço 150 x 100 mm e 100 x 50 mm; chapas de 4,75 e 6,35 mm"],
        ["Fabricação", "Tudo soldado. Só a tampa da boca de inspeção é aparafusada"],
    ], [55, 119])]

    c += [Paragraph("3. Como funciona no dia a dia", H)] + lista([
        "O esgoto dos vasos, do mictório e dos lavatórios desce por dois tubos para dentro do "
        "tanque.",
        "Um medidor avisa quando o tanque chega a 70% (hora de chamar o caminhão) e a 80% "
        "(limite de uso). Aos 90% um segundo sensor, independente, manda parar o uso.",
        "O caminhão liga a mangueira na parte de trás da base, numa válvula de 4 polegadas. "
        "O tubo de sucção desce até um poço no fundo, para esvaziar quase tudo.",
        "Um tubo de respiro sobe até acima do teto do contêiner. Ele solta o gás e deixa o ar "
        "entrar enquanto o caminhão puxa.",
        "Há uma tomada para ligar mangueira e lavar o tanque por dentro, sem ninguém entrar.",
    ])

    c += [Paragraph("4. Três cuidados que não podem falhar", H)] + lista([
        "<b>O respiro tem de estar desobstruído antes de cada sucção.</b> O caminhão puxa com "
        "muita força; se o ar não entrar pelo respiro, o tanque amassa. Há uma válvula de "
        "segurança para isso, mas a conferência do respiro é obrigatória.",
        "<b>A base só pode ser içada e transportada vazia.</b>",
        "<b>A base precisa dos 6 apoios.</b> Apoiada só nos 4 cantos e com o tanque cheio, a "
        "estrutura não aguenta.",
    ])

    c += [Spacer(1, 4), _imagem(render_base, 150),
          Paragraph("A base sem o contêiner: gaiola (vermelho), tanque (cinza), escada de acesso, "
                    "respiro e os seis apoios.", E._C)]

    c += [Paragraph("5. O que mudou em relação à primeira versão", H), tab([
        ["Item", "Antes (REV.01)", "Agora (REV.02)", "Por quê"],
        ["Altura da base", "600 mm", "%s mm" % n(spec["skid"]["alt"], 0),
         "Faltava altura para a estrutura embaixo e em cima do tanque"],
        ["Tanque", "5.550 x 2.280 mm", "%s x %s mm" % (n(ce, 0), n(le, 0)),
         "A estrutura não cabia ao lado do tanque"],
        ["Volume de trabalho", "cerca de 5,2 m³",
         "%s m³" % n(cap["niveis"]["alarme_alto"]["volume_m3"], 2),
         "Consequência das duas linhas acima"],
        ["Apoios", "4 cantos", "6 pontos", "Com 4 apoios a estrutura não aguenta o tanque cheio"],
        ["Respiro", "Por fora, na traseira", "Por dentro do contêiner, até o teto",
         "Pela traseira ele ficaria abaixo do nível do esgoto"],
        ["Medidor de nível", "Em cima do tanque", "Na parede traseira do tanque",
         "Em cima não há espaço sob o contêiner"],
        ["Divisórias internas", "Previstas", "Retiradas",
         "Não são necessárias; menos solda dentro do esgoto"],
        ["Escada", "Não prevista", "%d degraus com corrimão" % res["acesso"]["espelhos"],
         "A base fica a %s mm do chão" % n(spec["skid"]["alt"], 0)],
    ], [30, 36, 46, 62]), p(
        "Se o volume de 5,2 m³ for importante, basta subir a base de %s para 740 mm; a escada "
        "ganha um degrau. É uma troca simples no projeto." % n(spec["skid"]["alt"], 0))]

    c += [Paragraph("6. O que precisamos de você", H)] + lista([
        "Medidas do contêiner que será usado: comprimento, largura, posição dos cantos e o peso "
        "que consta na placa.",
        "Planta interna do contêiner: onde fica a porta, onde descem os tubos de esgoto e onde "
        "pode subir o tubo de respiro.",
        "Qual empresa fará a sucção, e os dados do caminhão dela.",
        "Como é o chão no ponto exato da instalação: se for concreto, a espessura do piso; se "
        "for brita ou terra, será preciso uma placa de concreto sob cada um dos seis apoios. "
        "Em qualquer caso os apoios têm de ser presos ao chão, por causa do vento.",
        "Quantas pessoas vão usar por turno e quantos turnos por dia.",
    ])

    c += [Paragraph("7. O que há nesta pasta", H), tab([
        ["Pasta", "Conteúdo"],
        ["1_Relatorio", "Este relatório"],
        ["2_Pranchas", "As 5 folhas de desenho em PDF, mais os arquivos DXF e DWG para quem "
                       "usa AutoCAD"],
        ["3_Modelo_3D", "Imagens e vídeo do modelo; arquivo GLB, que abre no Visualizador 3D do "
                        "Windows ou no navegador; arquivo IFC, para programas de engenharia"],
        ["4_Calculo", "Memória de cálculo e relatório técnico de alterações, para o engenheiro"],
    ], [34, 140])]

    c += [Paragraph("8. Situação do projeto", H), p(
        "Este é um projeto básico, feito para você ter uma ideia clara do equipamento e pedir "
        "orçamento. <b>Ainda não está liberado para fabricação.</b> Antes de cortar aço é "
        "preciso: receber os dados do item 6, fechar a pintura com o fabricante da tinta, "
        "projetar a fundação e ter a revisão e a ART de um engenheiro habilitado, como a NR-24 "
        "exige para contêineres transformados."),
        p("O cálculo tem %d verificações e todas passam. Alguns valores foram adotados com "
          "margem, por falta dos dados acima; eles estão listados na memória de cálculo."
          % sum(1 for v in res["verificacoes"] if not v.get("informativo")))]

    E._pdf(caminho, "Tanque-base para contêiner sanitário de 20 pés",
           "Relatório para o cliente | %s | %s" % (spec["documento"], time.strftime("%d/%m/%Y")),
           c, spec["documento"])


def montar(raiz):
    """Monta a pasta de envio a partir de ENTREGA_TANQUE_BASE_REV02. Devolve o caminho."""
    origem = os.path.join(raiz, "ENTREGA_TANQUE_BASE_REV02")
    pranchas = os.path.join(origem, "modelo", "pranchas")
    destino = os.path.join(raiz, NOME_PASTA)
    if os.path.isdir(destino):
        carimbo = time.strftime("%Y%m%d-%H%M%S")
        try:
            os.rename(destino, destino + ".anterior-" + carimbo)
        except PermissionError:
            # pasta aberta em outro programa: a nova sai ao lado, a antiga fica como esta'
            destino += "-" + carimbo
    partes = {k: os.path.join(destino, k)
              for k in ("1_Relatorio", "2_Pranchas", "3_Modelo_3D", "4_Calculo")}
    for pasta in partes.values():
        os.makedirs(pasta)

    res, arqs = E.gerar(origem)
    for a in arqs.values():
        shutil.copy2(a, partes["4_Calculo"])
    faltando = []

    def copiar(padrao, para, obrigatorio=True):
        achados = sorted(glob.glob(padrao))
        if not achados and obrigatorio:
            faltando.append(padrao)
        for a in achados:
            shutil.copy2(a, para)
        return achados

    copiar(os.path.join(pranchas, "pdf", "*.pdf"), partes["2_Pranchas"])
    copiar(os.path.join(pranchas, "dxf", "*.dxf"), partes["2_Pranchas"])
    copiar(os.path.join(pranchas, "dwg", "tanque_base_rev02.dwg"), partes["2_Pranchas"])
    renders = copiar(os.path.join(pranchas, "render", "*.png"), partes["3_Modelo_3D"])
    copiar(os.path.join(origem, "modelo", "tanque_base_rev02.ifc"), partes["3_Modelo_3D"])
    copiar(os.path.join(origem, "modelo", "tanque_base_rev02.glb"), partes["3_Modelo_3D"])
    # o video e' opcional: sai de scripts/video_tanque.py, que leva uns 20 minutos
    copiar(os.path.join(origem, "modelo", "video", "tanque_base_rev02.mp4"),
           partes["3_Modelo_3D"], obrigatorio=False)
    if faltando:
        raise FileNotFoundError("faltam arquivos para o envio (rode pranchas_tanque.py): %s"
                                % "; ".join(faltando))
    base = [a for a in renders if a.endswith("apresentacao.png")][0]
    cont = [a for a in renders if a.endswith("apresentacao_com_conteiner.png")][0]
    relatorio_final(res, os.path.join(partes["1_Relatorio"],
                                      "Relatorio_Tanque_Base_REV02.pdf"), base, cont)
    return destino


if __name__ == "__main__":
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pasta = montar(raiz)
    print(pasta)
    for b, _d, fs in os.walk(pasta):
        for f in sorted(fs):
            print("  ", os.path.relpath(os.path.join(b, f), pasta))
