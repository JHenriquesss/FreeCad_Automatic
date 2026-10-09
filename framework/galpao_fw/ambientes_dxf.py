# ============================================================================
# ambientes_dxf.py - SCRIPT AVULSO: AMBIENTES LIDOS DE UMA PLANTA DXF (plano de
# 2026-10-08, Fase 5, primeiro passo). Servico frequente: o cliente manda a
# planta e quer so o eletrico. O motor eletrico trabalha com o AMBIENTE
# abstrato (tipo, area, perimetro); este modulo so tira os ambientes da planta
# e entrega ao motor que ja existe (arquitetura_residencial.rodar).
#
# CONVENCAO DA PLANTA (o que o desenhista marca antes de mandar):
#   - cada ambiente e' uma POLILINHA FECHADA numa camada propria (padrao
#     AMBIENTES);
#   - dentro de cada polilinha, na mesma camada, um TEXTO com o tipo do
#     ambiente (ex.: "cozinha") ou "nome; tipo" (ex.: "Suite casal; suite").
# O que nao segue a convencao vira ERRO NOMEADO na saida, nunca um ambiente
# adivinhado: polilinha sem texto, com dois textos, com arco, texto solto.
#
# UNIDADE: lida do cabecalho do DXF ($INSUNITS). Desenho sem unidade declarada
# e' recusado, a menos que quem chama informe `unidade` - area errada por um
# fator de 10^6 nao e' erro que apareca sozinho.
#
# QUADRO: a posicao do quadro de distribuicao e' UMA entidade (ponto, bloco,
# circulo ou texto) na camada QUADRO. Nenhuma -> posicao nao informada (so
# faz falta para estimar comprimento de circuito); mais de uma -> erro nomeado.
#
# Nenhum valor de norma mora aqui: quantidades e cargas vem do motor.
#
# Uso:  python ambientes_dxf.py <planta.dxf> [camada] [unidade: mm|cm|m]
#                               [criterios=<criterios.json>] [saida=<pasta>]
# Com `criterios=` sai tambem a divisao em circuitos e o quadro de cargas
# (circuitos_planta.dividir); os criterios sao declarados, sem padrao. Se o
# arquivo de criterios trouxer `instalacao` (e `tracado` ou `comprimentos_m`),
# sai o dimensionamento; com `saida=` saem o unifilar e o quadro em SVG.
# ============================================================================
"""Ambientes (tipo, area, perimetro) lidos de polilinhas fechadas de um DXF."""

from __future__ import annotations

import json
import sys
import unicodedata

CAMADA_PADRAO = "AMBIENTES"
CAMADA_QUADRO = "QUADRO"
# $INSUNITS do DXF -> metros por unidade de desenho
METROS_POR_INSUNITS = {4: 0.001, 5: 0.01, 6: 1.0}
METROS_POR_NOME = {"mm": 0.001, "cm": 0.01, "m": 1.0}


def normaliza_tipo(texto):
    """'Área de Serviço' -> 'area_servico': sem acento, minusculo, com _ e sem
    a preposicao, no formato dos tipos do motor."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    palavras = [p for p in sem_acento.lower().replace("-", " ").replace("_", " ").split()
                if p not in ("de", "da", "do", "e")]
    return "_".join(palavras)


def _area_e_perimetro(pts):
    area2 = perim = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        area2 += x0 * y1 - x1 * y0
        perim += ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    return abs(area2) / 2.0, perim


def _dentro(ponto, pts):
    """Ponto dentro do poligono (paridade de cruzamentos)."""
    x, y = ponto
    dentro = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            dentro = not dentro
    return dentro


def _quadro(msp, camada, esc, erros):
    """Posicao (x, y) em metros da unica entidade da camada do quadro."""
    achados = []
    for e in msp.query('POINT INSERT CIRCLE TEXT MTEXT[layer=="%s"]' % camada):
        tipo = e.dxftype()
        p = (e.dxf.location if tipo == "POINT" else
             e.dxf.center if tipo == "CIRCLE" else e.dxf.insert)
        achados.append([round(p.x * esc, 4), round(p.y * esc, 4)])
    if len(achados) > 1:
        erros.append({"code": "varios_quadros", "n": len(achados),
                      "detail": "a camada do quadro tem de ter UMA entidade"})
        return None
    return achados[0] if achados else None


def ler_ambientes(caminho, camada=CAMADA_PADRAO, unidade=None, camada_quadro=CAMADA_QUADRO):
    """{ambientes: [{nome, tipo, area_m2, perimetro_m}], geometria: {nome:
    [[x_m, y_m], ...]}, quadro_m: [x, y] ou None, erros: [...]}.
    `unidade` ('mm', 'cm' ou 'm') so e' usada quando o DXF nao declara a sua."""
    import ezdxf

    doc = ezdxf.readfile(caminho)
    ins = doc.header.get("$INSUNITS", 0)
    if ins in METROS_POR_INSUNITS:
        esc = METROS_POR_INSUNITS[ins]
    elif unidade in METROS_POR_NOME:
        esc = METROS_POR_NOME[unidade]
    else:
        raise ValueError(
            "%s: unidade do desenho nao declarada ($INSUNITS=%r). Informe a unidade "
            "(mm, cm ou m): a area nao pode ser adivinhada." % (caminho, ins))
    msp = doc.modelspace()
    erros, poligonos = [], []
    for pl in msp.query('LWPOLYLINE[layer=="%s"]' % camada):
        pts = [(p[0], p[1]) for p in pl.get_points("xy")]
        if not pl.closed:
            erros.append({"code": "polilinha_aberta", "n_vertices": len(pts),
                          "detail": "ambiente tem de ser polilinha FECHADA"})
            continue
        if any(abs(p[4]) > 1e-12 for p in pl.get_points("xyseb")):
            erros.append({"code": "polilinha_com_arco", "n_vertices": len(pts),
                          "detail": "trecho em arco nao e' tratado: area sairia errada"})
            continue
        if len(pts) < 3:
            erros.append({"code": "polilinha_degenerada", "n_vertices": len(pts),
                          "detail": "menos de 3 vertices"})
            continue
        poligonos.append(pts)
    rotulos = []
    for t in msp.query('TEXT MTEXT[layer=="%s"]' % camada):
        frase = (t.plain_text() if t.dxftype() == "MTEXT" else t.dxf.text).strip()
        rotulos.append(((t.dxf.insert.x, t.dxf.insert.y), frase))
    usados = set()
    ambientes, contagem, geometria = [], {}, {}
    for pts in poligonos:
        dentro = [i for i, (pos, _f) in enumerate(rotulos) if _dentro(pos, pts)]
        area, perim = _area_e_perimetro(pts)
        area_m2, perim_m = area * esc * esc, perim * esc
        if len(dentro) != 1:
            erros.append({
                "code": "ambiente_sem_texto" if not dentro else "ambiente_com_varios_textos",
                "area_m2": round(area_m2, 3), "textos": [rotulos[i][1] for i in dentro],
                "detail": "cada polilinha precisa de exatamente um texto com o tipo"})
            usados.update(dentro)
            continue
        usados.add(dentro[0])
        frase = rotulos[dentro[0]][1]
        nome, _sep, tipo = frase.rpartition(";")
        tipo = normaliza_tipo(tipo)
        nome = nome.strip()
        if not nome:                                   # sem nome: tipo + numero de ordem
            contagem[tipo] = contagem.get(tipo, 0) + 1
            nome = "%s %d" % (tipo, contagem[tipo])
        ambientes.append({"nome": nome, "tipo": tipo, "area_m2": round(area_m2, 4),
                          "perimetro_m": round(perim_m, 4)})
        geometria[nome] = [[round(x * esc, 4), round(y * esc, 4)] for x, y in pts]
    for i, (_pos, frase) in enumerate(rotulos):
        if i not in usados:
            erros.append({"code": "texto_fora_de_ambiente", "texto": frase,
                          "detail": "texto da camada fora de qualquer polilinha fechada"})
    quadro = _quadro(msp, camada_quadro, esc, erros)
    return {"ambientes": ambientes, "erros": erros, "camada": camada,
            "metros_por_unidade": esc, "geometria": geometria, "quadro_m": quadro}


def previsao_de_cargas(caminho, camada=CAMADA_PADRAO, unidade=None):
    """Le os ambientes e roda o motor de previsao de carga. Erro de leitura
    impede o ATENDE: planta mal marcada nao vira previsao parcial calada."""
    import arquitetura_residencial as AR

    lido = ler_ambientes(caminho, camada, unidade)
    resultado = AR.rodar({"ambientes": lido["ambientes"]})
    resultado["leitura_dxf"] = {"arquivo": caminho, "camada": lido["camada"],
                                "metros_por_unidade": lido["metros_por_unidade"],
                                "geometria": lido["geometria"],
                                "quadro_m": lido["quadro_m"], "erros": lido["erros"]}
    if lido["erros"]:
        resultado["ATENDE"] = False
    return resultado


if __name__ == "__main__":
    _args = [a for a in sys.argv[1:] if not a.startswith(("criterios=", "saida="))]
    _crit = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("criterios=")]
    _saida = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("saida=")]
    if not _args:
        sys.exit(__doc__ + "\nuso: python ambientes_dxf.py <planta.dxf> [camada] [mm|cm|m] "
                           "[criterios=<criterios.json>]")
    import arquitetura_residencial as _AR
    res = previsao_de_cargas(_args[0], *(_args[1:2] or [CAMADA_PADRAO]),
                             unidade=(_args[2] if len(_args) > 2 else None))
    print(_AR.relatorio_pt(res))
    if res["leitura_dxf"]["erros"]:
        print("ERROS DE LEITURA DA PLANTA:")
        print(json.dumps(res["leitura_dxf"]["erros"], ensure_ascii=False, indent=1))
    if _crit:
        import circuitos_planta as _CP
        with open(_crit[0], encoding="utf-8") as _f:
            _criterios = json.load(_f)
        _div = _CP.dividir(res, _criterios)
        print(_CP.relatorio_pt(_div))
        if "instalacao" in _criterios:
            _dim = _CP.dimensionar_da_planta(_div, res["leitura_dxf"], _criterios)
            print(_CP.relatorio_dimensionamento_pt(_dim))
            if _saida:
                print("desenhos:", _CP.desenhos(_dim, _saida[0]))
