# ============================================================================
# bim_casa_residencial.py - BIM (IFC4) DA ARQUITETURA DA CASA RESIDENCIAL
#
# A tipologia 'casa-residencial' calculava arquitetura, eletrica e hidraulica e
# entregava report + drawings. O modelo nunca existiu: `desenho_casa_residencial`
# diz, na sua propria abertura, que NAO ha planta baixa porque "o programa
# declara area e perimetro, nao posicoes". Este modulo fecha esse buraco pelo
# unico caminho honesto - usando o LAYOUT DECLARADO, o mesmo contrato de
# retangulos que a eletrica ja exigia para posicionar pontos de circuito
# (`layout_ambientes`, a primitiva compartilhada).
#
# O QUE ELE EMITE, e por que so isso:
#   IfcSpace  - um por ambiente: o PROGRAMA como objeto BIM (area, volume,
#               nome), que e' exatamente o que o calculo produziu;
#   IfcSlab   - o piso de cada ambiente, espessura declarada em
#               `layout.piso_espessura_m` (sem ela, nao ha piso a emitir).
#   IfcWall   - APENAS as paredes explicitamente declaradas em `layout.paredes`.
#
# O que ele NAO faz: deduzir paredes do contorno dos comodos. Espessura,
# material e vao de porta/janela nao sao declarados em lugar nenhum do spec, e
# um IFC com paredes de espessura arbitrada seria um modelo que o projetista
# leria como projeto sem que ninguem o tenha projetado. Ausencia declarada e'
# melhor que geometria inventada - e' a mesma regra que manteve a planta baixa
# fora das pranchas.
#
# COSTURA rotulo x geometria: o retangulo do layout tem de reproduzir a AREA e o
# PERIMETRO que a arquitetura calculou para aquele ambiente (foi sobre esses dois
# numeros que a previsao de carga da NBR 5410 9.5.2 foi feita). Divergiu, o
# layout e' recusado com o ambiente nomeado: o modelo e o calculo nao podem
# descrever casas diferentes.
#
# Convencao: coordenadas em MILIMETROS (a mesma dos demais verticais, para
# federar com a eletrica sem transformacao); X/Y do layout, Z = altura, piso em
# z = 0.
# ============================================================================
"""IFC4 da arquitetura residencial a partir do layout declarado. Sem FreeCAD."""

from __future__ import annotations

import copy
import math

import geometria_membros as gm
import layout_ambientes as la


MM = gm.MM

# tolerancia relativa da costura rotulo x geometria. 1e-3 e' a mesma que
# `arquitetura_residencial` usa para conferir area declarada x largura x
# comprimento - uma so tolerancia para a mesma pergunta.
TOL_REL = 1e-3


def layout_declarado(arquitetura_payload) -> bool:
    """True se a secao de layout existir na entrada (mesmo que invalida)."""
    return isinstance(arquitetura_payload, dict) and "layout" in arquitetura_payload


def validar_layout(layout, resultado_arquitetura) -> dict:
    """Valida o layout arquitetonico contra o PROGRAMA ja calculado.

    Retorna {'declared', 'ok', 'errors', 'layout'}. `layout` so vem preenchido
    quando ok; nunca ha valor inventado. `resultado_arquitetura` e' o retorno de
    `arquitetura_residencial.rodar`.
    """
    if layout is None:
        return {"declared": False, "ok": False, "errors": [], "layout": None}
    if not isinstance(layout, dict):
        return {"declared": True, "ok": False, "layout": None,
                "errors": [la.erro("invalid_layout",
                                   detail="o layout deve ser um objeto")]}

    errors: list[dict] = []
    if layout.get("units") != "m":
        errors.append(la.erro("invalid_layout_value", field="units",
                              detail="layout.units deve ser metro"))
    comodos = la.validar_comodos(layout, errors)
    _conferir_programa(resultado_arquitetura, comodos, errors)
    piso = _validar_piso(layout, errors)
    paredes = _validar_paredes(layout, errors)

    if errors:
        return {"declared": True, "ok": False, "errors": errors, "layout": None}
    return {"declared": True, "ok": True, "errors": [],
            "layout": {"units": "m", "rooms": copy.deepcopy(list(comodos.values())),
                       "piso_espessura_m": piso, "paredes": copy.deepcopy(paredes)}}


def _conferir_programa(resultado_arquitetura, comodos, errors):
    """Todo ambiente do programa tem um retangulo, e o retangulo bate com ele.

    Sem esta conferencia o BIM poderia mostrar um dormitorio de 6 m2 enquanto a
    previsao de carga do mesmo dormitorio foi feita sobre 12 m2 - duas casas
    diferentes com o mesmo nome, e nenhum teste de numero enxergaria.
    """
    if not isinstance(resultado_arquitetura, dict):
        errors.append(la.erro("missing_architecture_result",
                              detail="sem o programa calculado nao ha o que conferir"))
        return
    ambientes = resultado_arquitetura.get("ambientes") or []
    nomes_programa = {a.get("nome") for a in ambientes if isinstance(a, dict)}
    sobrando = sorted(set(comodos) - nomes_programa)
    if sobrando:
        errors.append(la.erro("layout_room_not_in_programme", rooms=sobrando,
                              detail="o layout declara comodos que o programa de "
                                     "ambientes nao tem"))
    for ambiente in ambientes:
        if not isinstance(ambiente, dict):
            continue
        nome = ambiente.get("nome")
        comodo = comodos.get(nome)
        if comodo is None:
            errors.append(la.erro("missing_layout_room", room=nome,
                                  detail="ambiente do programa sem retangulo no layout"))
            continue
        area_programa = ambiente.get("area_m2")
        perim_programa = ambiente.get("perimetro_m")
        if area_programa is None or perim_programa is None:
            # ambiente sem previsao (geometria contestada na arquitetura): nao ha
            # numero conferivel, e inventar um aqui seria repor o dado recusado la.
            continue
        area_layout = float(comodo["width_m"]) * float(comodo["depth_m"])
        perim_layout = 2.0 * (float(comodo["width_m"]) + float(comodo["depth_m"]))
        if not math.isclose(area_layout, float(area_programa), rel_tol=TOL_REL):
            errors.append(la.erro(
                "layout_area_mismatch", room=nome,
                area_layout_m2=round(area_layout, 4),
                area_programa_m2=float(area_programa),
                detail="o retangulo do layout nao reproduz a area do programa"))
        if not math.isclose(perim_layout, float(perim_programa), rel_tol=TOL_REL):
            errors.append(la.erro(
                "layout_perimeter_mismatch", room=nome,
                perimetro_layout_m=round(perim_layout, 4),
                perimetro_programa_m=float(perim_programa),
                detail="o retangulo do layout nao reproduz o perimetro do programa"))


def _validar_piso(layout, errors):
    """Espessura do piso (m). Ausente = sem piso a emitir, nao um piso default."""
    valor = layout.get("piso_espessura_m")
    if valor is None:
        return None
    if not la.finito_positivo(valor):
        errors.append(la.erro("invalid_layout_value", field="piso_espessura_m",
                              detail="a espessura do piso deve ser > 0"))
        return None
    return float(valor)


_PAREDE_FIELDS = ("id", "x0_m", "y0_m", "x1_m", "y1_m", "espessura_m", "altura_m")


def _validar_paredes(layout, errors):
    """Paredes DECLARADAS (segmento + espessura + altura). Ausentes = nenhuma."""
    brutas = layout.get("paredes")
    if brutas is None:
        return []
    if not isinstance(brutas, list):
        errors.append(la.erro("invalid_layout_value", field="paredes",
                              detail="layout.paredes deve ser uma lista"))
        return []
    paredes = []
    for indice, parede in enumerate(brutas):
        if not isinstance(parede, dict):
            errors.append(la.erro("invalid_layout_value", field="paredes",
                                  index=indice))
            continue
        faltando = [campo for campo in _PAREDE_FIELDS if campo not in parede]
        if faltando:
            errors.append(la.erro("missing_layout_field", field="paredes",
                                  index=indice, missing=sorted(faltando)))
            continue
        if not (la.texto_nao_vazio(parede["id"])
                and all(la.finito(parede[c]) for c in ("x0_m", "y0_m", "x1_m", "y1_m"))
                and la.finito_positivo(parede["espessura_m"])
                and la.finito_positivo(parede["altura_m"])):
            errors.append(la.erro("invalid_layout_value", field="paredes.geometry",
                                  index=indice, parede=parede["id"]))
            continue
        dx = float(parede["x1_m"]) - float(parede["x0_m"])
        dy = float(parede["y1_m"]) - float(parede["y0_m"])
        if math.hypot(dx, dy) < 1e-6:
            errors.append(la.erro("degenerate_wall", parede=parede["id"],
                                  detail="parede de comprimento nulo"))
            continue
        if abs(dx) > 1e-9 and abs(dy) > 1e-9:
            # o emissor extruda a secao retangular ao longo do eixo com a base
            # local alinhada aos eixos globais; uma parede oblíqua sairia com a
            # espessura no plano errado. Recusar e' melhor que emitir torto.
            errors.append(la.erro(
                "oblique_wall", parede=parede["id"],
                detail="parede obliqua nao suportada: declare-a paralela a X ou a Y"))
            continue
        paredes.append({campo: parede[campo] for campo in _PAREDE_FIELDS})
    return paredes


def _pe_direito(resultado_arquitetura):
    valor = (resultado_arquitetura or {}).get("pe_direito_m")
    return float(valor) if la.finito_positivo(valor) else None


def membros_bim(resultado_arquitetura, layout):
    """Modelo neutro da arquitetura: IfcSpace por ambiente (+ piso e paredes).

    Sem layout valido devolve lista vazia - sem posicao declarada nao existe
    elemento BIM honesto a emitir.
    """
    if not layout:
        return []
    pe = _pe_direito(resultado_arquitetura)
    if pe is None:
        return []
    piso = layout.get("piso_espessura_m")
    membros = []
    for comodo in layout["rooms"]:
        w, d = float(comodo["width_m"]), float(comodo["depth_m"])
        cx = (float(comodo["x_m"]) + w / 2.0) * MM
        cy = (float(comodo["y_m"]) + d / 2.0) * MM
        membros.append({
            "tipo": "Space", "marca": comodo["name"],
            "perfil": "Ambiente %s" % comodo["name"],
            "dims": [w * MM, d * MM, pe * MM],
            "centro": [cx, cy, pe * MM / 2.0],
            "pavimento": "Terreo"})
        if piso:
            membros.append({
                "tipo": "Slab", "marca": "PISO-%s" % comodo["id"],
                "perfil": "Piso h=%.0fcm" % (piso * 100),
                "dims": [w * MM, d * MM, piso * MM],
                # o piso fica ABAIXO da cota zero do ambiente: assim ele nao
                # divide volume com o IfcSpace que comeca em z=0.
                "centro": [cx, cy, -piso * MM / 2.0],
                "material": "Concreto", "pavimento": "Terreo"})
    for parede in layout.get("paredes") or []:
        membros.append(_membro_parede(parede))
    return membros


def _membro_parede(parede):
    """Parede declarada -> barra horizontal com secao espessura x altura.

    `bf` = espessura (horizontal, transversal ao eixo) e `d` = altura, que e' a
    mesma regra de orientacao das vigas do edificio; a barra e' ancorada pelo
    fundo (z=0) e sobe `d`.
    """
    x0, y0 = float(parede["x0_m"]) * MM, float(parede["y0_m"]) * MM
    x1, y1 = float(parede["x1_m"]) * MM, float(parede["y1_m"]) * MM
    return {
        "tipo": "Wall", "marca": parede["id"],
        "perfil": "PAR e=%.0fcm" % (float(parede["espessura_m"]) * 100),
        "secao": {"forma": "RECT", "bf": float(parede["espessura_m"]),
                  "d": float(parede["altura_m"])},
        "ancoragem": "base",
        "p1": [x0, y0, 0.0], "p2": [x1, y1, 0.0],
        "material": "Alvenaria", "pavimento": "Terreo"}


def confere_areas(resultado_arquitetura, membros):
    """Area de cada IfcSpace do modelo x area do programa (rotulo x geometria).

    Devolve {'ok', 'por_ambiente', 'ausentes'}. E' a conferencia que roda DEPOIS
    de montar o modelo: `validar_layout` confere a entrada, esta confere o que
    de fato foi emitido.
    """
    por_nome = {}
    for m in membros:
        if m["tipo"] != "Space":
            continue
        dx, dy, _dz = m["dims"]
        por_nome[m["marca"]] = (dx / MM) * (dy / MM)
    ambientes = (resultado_arquitetura or {}).get("ambientes") or []
    linhas, ausentes = [], []
    for ambiente in ambientes:
        nome = ambiente.get("nome")
        if nome not in por_nome:
            ausentes.append(nome)
            continue
        area_programa = ambiente.get("area_m2")
        if area_programa is None:
            continue
        linhas.append({
            "ambiente": nome, "area_modelo_m2": round(por_nome[nome], 4),
            "area_programa_m2": float(area_programa),
            "ok": math.isclose(por_nome[nome], float(area_programa),
                               rel_tol=TOL_REL)})
    return {"ok": not ausentes and all(linha["ok"] for linha in linhas),
            "por_ambiente": linhas, "ausentes": ausentes}


def confere_solidos(membros):
    """Nenhuma peca CONSTRUIDA pode ocupar o volume de outra.

    O IfcSpace fica de fora: ele e' volume de AMBIENTE, e o piso e as paredes que
    o delimitam legitimamente o tocam. O que nao pode e' parede dentro de parede
    ou piso dentro de piso - e isso vem do que o projetista declarou, entao o
    entregavel nomeia as pecas em vez de calar.
    """
    return gm.interpenetracoes([m for m in membros if m["tipo"] != "Space"])


def emitir_bim(resultado_arquitetura, layout, path, nome="CasaResidencial"):
    """Escreve o IFC4 da arquitetura. Retorna o path, ou None sem membros."""
    import ifc_emit

    membros = membros_bim(resultado_arquitetura, layout)
    if not membros:
        return None
    return ifc_emit.emitir_ifc(
        membros, path, nome=nome,
        pavimentos=[{"nome": "Terreo", "elevacao_mm": 0.0}])


def montar_3d(membros, out_dir, doc_name="casa", headless=None,
              host="http://localhost:9875", timeout=300):
    """Constroi o 3D SOLIDO (FreeCAD) das pecas construidas e exporta.

    Recebe a lista de membros JA FILTRADA (sem IfcSpace: volume de ambiente nao
    e' peca). Reusa `build_concreto.py`, que monta caixas a partir de um payload
    de dados puro - sem importar modulo irmao, entao o freecad.exe nao tem o que
    cachear de versao antiga.
    """
    import os

    import framework as FW
    import rodar_projeto as RP

    payload = {"membros": list(membros),
               "export_dir": str(out_dir).replace("\\", "/"),
               "doc_name": doc_name}
    src = RP._ship_build_src(
        FW.raiz_repo() / "framework" / "galpao_fw" / "build_concreto.py")
    if headless is None:
        headless = os.environ.get("FREECAD_HEADLESS", "").strip() in (
            "1", "true", "True")
    if headless:
        return RP._montar_headless(src, payload, out_dir, timeout)
    import xmlrpc.client
    try:
        return RP._montar_bridge(src, payload, host, timeout)
    except (OSError, xmlrpc.client.ProtocolError):
        return RP._montar_headless(src, payload, out_dir, timeout)
