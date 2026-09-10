# ============================================================================
# bim_telhado_madeira.py - BIM (IFC4) DO TELHADO DE MADEIRA (G72)
#
# O telhado era calculado, orcado, cronogramado e desenhado - e nao existia
# em nenhum modelo IFC, enquanto casa, edificio e galpao tem emissor cada
# um. Ilha de entrega: o federado nunca viu a tesoura contra reservatorio,
# prumada ou eletrocalha do sotao. Este modulo fecha a ilha.
#
# O QUE ELE EMITE, e por que so isso:
#   IfcMember - banzos, diagonais e montantes (um por barra por tesoura);
#   IfcBeam   - tercas (uma por linha de no superior, vencendo a extensao).
# CONTRATO G86 (D101/G72 redesenhado): o telhado calculado entra SEMPRE,
# ATENDA ou nao - o clash e' sobre ocupacao fisica, e a geometria da tesoura
# (secoes adotadas, posicao) existe nos dois casos. O veredito viaja em cada
# membro (`situacao`: "ATENDE"/"REPROVADO", lido do calculo, nao dos
# membros). Sem telhado calculado (None, nao-dict ou sem vao/n_tesouras)
# nao ha membro: ausencia honesta, nao silencio. A folha ja carimbava
# REPROVA (desenho_casa_residencial); o federado era o unico que sumia.
#
# MATERIAL: a classe declarada (C24, D40...) + a densidade MEDIA da Tab. 3
# (rhom, p.12 do F136) - nunca "madeira" generica. A string leva os dois:
# "Madeira C24 (rho 420 kg/m3)". O numero vem de madeira_nbr7190.
# propriedades_classe (lida na pagina), nao de memoria.
#
# FRAME (o mesmo do bim_edificio, para federar sem transformacao):
#   mm; X = vaos_x, Y = vaos_y, Z = altura; origem no canto (0,0);
#   secao de barra em METROS (bf = largura transversal, d = altura no plano
#   do portico da tesoura); `pavimento` = "Cobertura".
# A tesoura vence o vao (linhas_de_beiral de estrutura_casa): direcao "x"
# = vao em X, tesouras distribuidas em Y; direcao "y" = o contrario. A base
# (cota do apoio) e' H_total_m da estrutura - o topo da casa que o calculo
# ja entregou, sem arbitrar.
#
# ORIENTACAO DA SECAO (a guarda do G3): toda barra retangular do federado
# saiu girada 90 graus (viga deitada de lado). A regra aqui:
#   bf = largura HORIZONTAL TRANSVERSAL ao eixo (fora do plano da tesoura);
#   d  = altura NO PLANO do portico da tesoura.
# O membro carrega `plano_normal` (a normal do plano da tesoura) para que o
# emissor IFC (ifc_emit._base_axes com hint) coloque d no plano em vez do
# default que deita a peca. Os testes MEDEM os eixos locais emitidos, nao o
# nome do membro.
#
# VOLUME: exato (bf*d*L por barra), nao AABB - a envolvente de barra
# inclinada superestima. Tem de bater com vol_madeira_m3 do calculo.
# ============================================================================
"""Modelo neutro + IFC4 do telhado de madeira, puro-Python (sem FreeCAD)."""

from __future__ import annotations

import math

import geometria_membros as gm

MM = gm.MM

PAVIMENTO = "Cobertura"

# grupo do calculo -> tipo IFC (o contrato do G72).
GRUPO_TIPO = {
    "banzo_sup": "Member",
    "banzo_inf": "Member",
    "diagonal": "Member",
    "montante": "Member",
    "terca": "Beam",
}

_GRUPOS_TRELICADOS = ("banzo_sup", "banzo_inf", "diagonal", "montante")

TOL_VOL_REL = 5e-3  # modelo x calculo: mesma tolerancia do cross-check G8


class GeometriaTelhadoIncoerente(ValueError):
    """A entrada nao descreve um telhado posicionavel sobre a casa."""


def material_da_classe(classe, rho_medio_kgm3):
    """String de material com a classe declarada e a densidade da Tab. 3."""
    return "Madeira %s (rho %d kg/m3)" % (
        str(classe).strip(), int(round(float(rho_medio_kgm3))))


def _secoes_por_grupo(telhado):
    """(b, h) por grupo lidos do RESULTADO (pecas), nao do spec."""
    pecas = telhado.get("pecas") or []
    out = {}
    for p in pecas:
        if isinstance(p, dict) and p.get("grupo"):
            out[p["grupo"]] = (float(p["b_m"]), float(p["h_m"]))
    faltando = [g for g in list(_GRUPOS_TRELICADOS) + ["terca"]
                if g not in out]
    if faltando:
        raise GeometriaTelhadoIncoerente(
            "o resultado nao traz secao para %s; sem secao calculada nao "
            "ha barra a emitir" % ", ".join(sorted(faltando)))
    return out


def _enquadramento(telhado, estrutura, vaos_x, vaos_y, z_base_m):
    """Resolve (vaos_x, vaos_y, z_base_m, direcao) a partir da estrutura ou
    dos argumentos explicitos. Estrutura tem prioridade quando presente."""
    if estrutura is not None:
        try:
            pav = estrutura["pavimento"]
            vaos_x = list(pav["vaos_x"])
            vaos_y = list(pav["vaos_y"])
        except (KeyError, TypeError):
            raise GeometriaTelhadoIncoerente(
                "a estrutura nao traz pavimento.vaos_x/vaos_y para "
                "posicionar o telhado")
        try:
            z_base_m = float(estrutura["H_total_m"])
        except (KeyError, TypeError, ValueError):
            raise GeometriaTelhadoIncoerente(
                "a estrutura nao traz H_total_m (cota do apoio do telhado)")
    if vaos_x is None or vaos_y is None or z_base_m is None:
        raise GeometriaTelhadoIncoerente(
            "sem estrutura, declare vaos_x, vaos_y e z_base_m")
    import estrutura_casa as _ec
    beiral = telhado.get("_beiral") or _ec.linhas_de_beiral(
        float(telhado["vao_m"]), vaos_x, vaos_y)
    direcao = beiral["direcao"]
    return ([float(v) for v in vaos_x], [float(v) for v in vaos_y],
            float(z_base_m), direcao)


def membros_bim(telhado, estrutura=None, vaos_x=None, vaos_y=None,
                z_base_m=None, origem=(0.0, 0.0)):
    """Modelo neutro do telhado no frame da casa (mm, secao em m).

    `telhado` e' o retorno de telhado_casa_madeira.rodar (com _beiral quando
    veio via estrutura_casa). `estrutura` e' o retorno de
    estrutura_casa.rodar (fornece vaos + H_total_m). Sem estrutura, os tres
    tem de vir explicitos. Cada barra leva `plano_normal` (normal do plano
    da tesoura) para o emissor orientar d no plano, e `situacao`
    ("ATENDE"/"REPROVADO" do calculo - G86: o reprovado entra carimbado,
    nunca some).
    """
    if telhado is None:
        return []
    if not isinstance(telhado, dict):
        return []
    if telhado.get("vao_m") is None or telhado.get("n_tesouras") is None:
        return []
    try:
        vao = float(telhado["vao_m"])
        inc = float(telhado["inclinacao_graus"])
        ext = float(telhado["extensao_m"])
        esp = float(telhado["espacamento_m"])
        n_pain = int(telhado.get("n_paineis") or 2)
        n_tes = int(telhado["n_tesouras"])
        classe = telhado["madeira"]["classe"]
        rho = float(telhado["rho_madeira_kgm3"])
    except (KeyError, TypeError, ValueError):
        raise GeometriaTelhadoIncoerente(
            "o resultado do telhado nao traz vao/inclinacao/extensao/"
            "espacamento/n_tesouras/madeira para emitir")
    import madeira_nbr7190 as _mad
    prop = _mad.propriedades_classe(classe)
    if abs(float(prop["rhom"]) - rho) > 1e-6:
        raise GeometriaTelhadoIncoerente(
            "rho do resultado (%.1f) diverge da Tab. 3 para %s (%.1f): o "
            "material do modelo tem de ser o da pagina" % (
                rho, classe, float(prop["rhom"])))
    vxs, vys, zbase, direcao = _enquadramento(
        telhado, estrutura, vaos_x, vaos_y, z_base_m)
    import telhado_casa_madeira as _tm
    geo = _tm.geometria(vao, inc, n_pain)
    nos, barras = geo["nos"], geo["barras"]
    secoes = _secoes_por_grupo(telhado)
    material = material_da_classe(prop["classe"], prop["rhom"])
    situacao = "ATENDE" if telhado.get("ATENDE") else "REPROVADO"
    ox, oy = float(origem[0]), float(origem[1])
    a = geo["meio_vao"]
    normal = [0.0, 1.0, 0.0] if direcao == "x" else [1.0, 0.0, 0.0]
    membros = []
    for k in range(n_tes):
        off = k * esp
        for n1, n2, grupo in barras:
            x1, y1 = nos[n1]
            x2, y2 = nos[n2]
            if direcao == "x":
                p1 = [(ox + x1 + a) * MM, (oy + off) * MM,
                      (zbase + y1) * MM]
                p2 = [(ox + x2 + a) * MM, (oy + off) * MM,
                      (zbase + y2) * MM]
            else:
                p1 = [(ox + off) * MM, (oy + x1 + a) * MM,
                      (zbase + y1) * MM]
                p2 = [(ox + off) * MM, (oy + x2 + a) * MM,
                      (zbase + y2) * MM]
            b, h = secoes[grupo]
            membros.append({
                "tipo": GRUPO_TIPO[grupo],
                "marca": "T-%s-%02d" % (_marca_grupo(grupo), k + 1),
                "perfil": "%s %.0fx%.0f" % (grupo, b * 100, h * 100),
                "secao": {"forma": "RECT", "bf": b, "d": h},
                "p1": p1, "p2": p2,
                "plano_normal": list(normal),
                "material": material, "pavimento": PAVIMENTO,
                "disciplina": "telhado", "situacao": situacao,
                "tesoura": k + 1, "grupo": grupo,
                "barra": "%s-%s" % (n1, n2)})
    # tercas: uma por no superior, vencendo a extensao inteira.
    sup_ids = sorted({n1 for n1, _n2, g in barras if g == "banzo_sup"} |
                     {n2 for _n1, n2, g in barras if g == "banzo_sup"},
                     key=lambda nid: nos[nid][0])
    bt, ht = secoes["terca"]
    for nid in sup_ids:
        x, y = nos[nid]
        z = (zbase + y) * MM
        if direcao == "x":
            X = (ox + x + a) * MM
            p1 = [X, oy * MM, z]
            p2 = [X, (oy + ext) * MM, z]
        else:
            Y = (oy + x + a) * MM
            p1 = [ox * MM, Y, z]
            p2 = [(ox + ext) * MM, Y, z]
        membros.append({
            "tipo": "Beam",
            "marca": "T-TER-%s" % nid,
            "perfil": "terca %.0fx%.0f" % (bt * 100, ht * 100),
            "secao": {"forma": "RECT", "bf": bt, "d": ht},
            "p1": p1, "p2": p2,
            "plano_normal": list(normal),
            "material": material, "pavimento": PAVIMENTO,
            "disciplina": "telhado", "situacao": situacao,
            "grupo": "terca", "no_superior": nid})
    return membros


def _marca_grupo(grupo):
    return {"banzo_sup": "BS", "banzo_inf": "BI", "diagonal": "DG",
            "montante": "MT"}.get(grupo, grupo[:2].upper())


def volume_exato_m3(membros):
    """Volume EXATO das barras (bf*d*L), em m3. Nao usa AABB."""
    tot = 0.0
    for m in membros:
        s = m.get("secao") or {}
        if "p1" not in m or "p2" not in m or "bf" not in s or "d" not in s:
            continue
        tot += (float(s["bf"]) * float(s["d"])
                * math.dist(m["p1"], m["p2"]) / 1000.0)
    return tot


def confere_modelo(telhado, membros):
    """Contagens do MODELO contra o CALCULO (origens independentes).

    O esperado e' recomputado da geometria (n_barras x n_tesouras +
    n_tercas), nao lido dos membros - senao fecharia por construcao.
    """
    import telhado_casa_madeira as _tm
    geo = _tm.geometria(float(telhado["vao_m"]),
                        float(telhado["inclinacao_graus"]),
                        int(telhado.get("n_paineis") or 2))
    n_bar = len(geo["barras"])
    sup = ({n1 for n1, _n2, g in geo["barras"] if g == "banzo_sup"} |
           {n2 for _n1, n2, g in geo["barras"] if g == "banzo_sup"})
    n_tes = int(telhado["n_tesouras"])
    esperado = {"Member": n_bar * n_tes, "Beam": len(sup)}
    por_tipo = {}
    for m in membros:
        por_tipo[m["tipo"]] = por_tipo.get(m["tipo"], 0) + 1
    return {"ok": por_tipo == esperado, "por_tipo": por_tipo,
            "esperado": esperado, "n_tesouras": n_tes,
            "n_barras_por_tesoura": n_bar, "n_tercas": len(sup)}


def confere_volume(telhado, membros, tol_rel=TOL_VOL_REL):
    """Volume medido no MODELO contra vol_madeira_m3 do CALCULO."""
    esperado = float(telhado["vol_madeira_m3"])
    medido = volume_exato_m3(membros)
    erro = abs(medido - esperado) / esperado if esperado > 0 else 0.0
    return {"ok": bool(erro <= tol_rel), "medido_m3": round(medido, 4),
            "esperado_m3": round(esperado, 4), "erro_rel": round(erro, 6)}


def confere_orientacao(membros):
    """A altura d tem de estar NO PLANO da tesoura (guarda do G3).

    Mede os eixos locais que o emissor IFC vai usar (ifc_emit._base_axes
    com o hint plano_normal): o eixo de d (local Y) tem de ser coplanar
    (dot ~ 0 com a normal) e o de bf (local X) tem de sair do plano
    (|dot| ~ 1). Nao le o nome do membro.
    """
    import ifc_emit as _emit
    linhas = []
    for m in membros:
        if "p1" not in m or "p2" not in m:
            continue
        n = m.get("plano_normal") or ([0.0, 1.0, 0.0])
        nn = math.sqrt(sum(c * c for c in n))
        n = [c / nn for c in n]
        x, y, _z, L = _emit._base_axes(
            m["p1"], m["p2"], ref_hint=m.get("plano_normal"))
        if L < 1e-9:
            continue
        dot_d = abs(y[0] * n[0] + y[1] * n[1] + y[2] * n[2])
        dot_bf = abs(x[0] * n[0] + x[1] * n[1] + x[2] * n[2])
        # barra horizontal na direcao da distribuicao (terca): d e'
        # vertical por construcao; a normal do plano e' horizontal e
        # ortogonal a ela - o criterio de coplanaridade nao se aplica do
        # mesmo jeito: mede-se d vertical (|y.z| ~ 1).
        p1, p2 = m["p1"], m["p2"]
        horizontal_distrib = (
            abs(p2[2] - p1[2]) < 1e-6
            and abs((p2[0] - p1[0]) * n[0] + (p2[1] - p1[1]) * n[1]
                    + (p2[2] - p1[2]) * n[2]) > 1e-6)
        if horizontal_distrib:
            ok = bool(abs(y[2]) > 0.99)
        else:
            ok = bool(dot_d < 0.05 and dot_bf > 0.99)
        linhas.append({"marca": m.get("marca"), "ok": ok,
                       "dot_d_normal": round(dot_d, 4),
                       "dot_bf_normal": round(dot_bf, 4),
                       "eixo_d": tuple(round(c, 4) for c in y)})
    return {"ok": all(l["ok"] for l in linhas), "linhas": linhas}


def emitir_bim(telhado, estrutura, path, nome="TelhadoMadeira"):
    """Escreve o IFC4 do telhado. Retorna o path, ou None sem membros."""
    import ifc_emit

    membros = membros_bim(telhado, estrutura=estrutura)
    if not membros:
        return None
    try:
        z = float(estrutura["H_total_m"]) * MM
    except (KeyError, TypeError, ValueError):
        z = 0.0
    return ifc_emit.emitir_ifc(
        membros, path, nome=nome,
        pavimentos=[{"nome": PAVIMENTO, "elevacao_mm": z}])


def montar_3d(membros, out_dir, doc_name="telhado", headless=None,
              host="http://localhost:9875", timeout=300):
    """Constroi o 3D SOLIDO (FreeCAD) via build_federado (barras inclinadas).

    O build_concreto so monta caixas horizontais/verticais; a tesoura tem
    banzo inclinado, entao o caminho e' o prisma orientado do federado -
    o mesmo solido que o clash entre disciplinas usa.
    """
    import os

    import framework as FW
    import rodar_projeto as RP

    payload = {"membros": [_marca_federada(m) for m in membros],
               "export_dir": str(out_dir).replace("\\", "/"),
               "doc_name": doc_name}
    src = RP._ship_build_src(
        FW.raiz_repo() / "framework" / "galpao_fw" / "build_federado.py")
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


def _marca_federada(m):
    """Marca com prefixo de disciplina do federado (T- = telhado)."""
    m = dict(m)
    if not str(m.get("marca", "")).startswith("T-"):
        m["marca"] = "T-" + str(m.get("marca", ""))
    return m
