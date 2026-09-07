# ============================================================================
# bim_instalacoes_casa.py - GEOMETRIA DAS INSTALACOES NO FRAME DA ESTRUTURA
#
# G58: o calculo das instalacoes da casa existia como numero (DN, pontos,
# circuitos) e a estrutura existia como MODELO (bim_edificio), mas nunca no
# MESMO frame. Sem posicao no modelo federado, o clash nao tem o que achar -
# e ligar o coordination sem posicao produziria o relatorio vazio que parece
# cobertura (a licao do predio antes do G53).
#
# Este modulo e' a fronteira geometrica, na mesma forma do G53:
# - ELETRICA: posicao REAL declarada. Cada ponto de circuito tem x/y/z
#   validado contra o comodo que ele declara (`layout_eletrico_residencial`:
#   rotulo x geometria); o quadro tambem. Nada aqui e' arbitrado: sem layout
#   validado, a eletrica nao entra no modelo ([]);
# - HIDRAULICA: tracado CONVENCIONAL em shaft (1,0 m do canto), como no predio.
#   A casa nao declara onde passa o tubo - e o DN sai do calculo. O shaft e'
#   deterministico e dito como convencional no perfil, para que o clash seja
#   CAPAZ de apontar o furo sem que ninguem leia o tracado como projeto.
#
# Frame: o MESMO do bim_edificio/bim_casa (mm; X=vaos_x, Y=vaos_y, Z=altura,
# origem no canto (0,0), base em z=0; secao de barra em METROS; caixa em MM).
# O envelope da arquitetura (layout) e o da estrutura (vaos) descrevem a MESMA
# casa - a costura arquitetura x estrutura do adaptador ja confere isso.
#
# REGRAS:
# - peca que ninguem calculou nao entra no modelo (disciplina ausente -> []).
# - DN/kind lidos do RESULTADO; sem eles, nada e' arbitrado.
# ============================================================================
"""Geometria das instalacoes da casa no frame da estrutura (G58)."""

from __future__ import annotations

SX_MM = 1000.0
SY_MM = 1000.0
DX_ESGOTO_MM = 300.0
DY_ELET_MM = 300.0
Z_HID_MM = 250.0
Z_AGUA_RAMAL_MM = 250.0
# Caixa do ponto eletrico (mm): tomada/luminaria como volume de clash. Nao e'
# o aparelho real - e' o envelope para o AABB acusar o encontro com viga/laje.
PONTO_DIM_MM = (120.0, 120.0, 80.0)
QUADRO_DIM_MM = (400.0, 200.0, 600.0)


def _eixos(vaos):
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + float(v))
    return xs


def _pe_direito(estrutura):
    try:
        import bim_edificio as bim

        return float(bim._pe_direito(estrutura["pilares"]))
    except Exception:
        pass
    raise ValueError("pe-direito indeterminavel: sem pilares dimensionados")


def _envelope(estrutura):
    pav = (estrutura or {}).get("pavimento") or {}
    xs = _eixos(pav["vaos_x"])
    ys = _eixos(pav["vaos_y"])
    return xs[-1] * 1000.0, ys[-1] * 1000.0


def _dn(valor):
    try:
        v = float(valor)
    except Exception:
        return None
    return v / 1000.0 if v > 1.0 else v


def membros_eletrica(estrutura, resultado_eletrico):
    """Pontos e quadro no frame da estrutura, nas posicoes DECLARADAS.

    Le o layout VALIDADO (circuits.layout_validation.layout) e o kind de cada
    ponto (circuits.points). Sem layout validado -> [] (sem posicao honesta).
    """
    del estrutura
    if not isinstance(resultado_eletrico, dict):
        return []
    circuitos = resultado_eletrico.get("circuits") or {}
    validacao = circuitos.get("layout_validation") or {}
    if not validacao.get("ok") or not isinstance(validacao.get("layout"), dict):
        return []
    layout = validacao["layout"]
    kinds = {}
    for p in circuitos.get("points") or []:
        if isinstance(p, dict) and p.get("id"):
            kinds[str(p["id"])] = p.get("kind")
    membros = []
    for pos in layout.get("points") or []:
        if not isinstance(pos, dict):
            continue
        try:
            x = float(pos["x_m"]) * 1000.0
            y = float(pos["y_m"]) * 1000.0
            z = float(pos["z_m"]) * 1000.0
        except (KeyError, TypeError, ValueError):
            continue
        kind = kinds.get(str(pos.get("id")))
        tipo = "Luminaire" if kind == "lighting" else "Outlet"
        membros.append({
            "tipo": tipo, "marca": "E-PTO-%s" % pos.get("id"),
            "perfil": "Ponto %s (%s)" % (pos.get("id"), kind or "?"),
            "dims": list(PONTO_DIM_MM),
            "centro": [x, y, z],
            "material": "PVC", "pavimento": "Terreo",
            "disciplina": "eletrico"})
    board = layout.get("board") or {}
    try:
        bx = float(board["x_m"]) * 1000.0
        by = float(board["y_m"]) * 1000.0
        bz = float(board["z_m"]) * 1000.0
        membros.append({
            "tipo": "Board", "marca": "E-QD-%s" % board.get("id", "QD"),
            "perfil": "Quadro de distribuicao",
            "dims": list(QUADRO_DIM_MM),
            "centro": [bx, by, bz],
            "material": "Aco", "pavimento": "Terreo",
            "disciplina": "eletrico"})
    except (KeyError, TypeError, ValueError):
        pass
    return membros


def membros_hidraulica(estrutura, resultado_hidraulica):
    """Tracado CONVENCIONAL em shaft no frame da estrutura.

    Le os DNs do `hidraulica_residencial.rodar`. Sem resultado -> []. O perfil
    de cada peca diz "convencional": posicao para clash, nao projeto.
    """
    if not isinstance(resultado_hidraulica, dict):
        return []
    redes = resultado_hidraulica.get("redes") or {}
    try:
        Lx, _Ly = _envelope(estrutura)
        pe = _pe_direito(estrutura)
        n_pav = int((estrutura or {}).get("n_pavimentos") or 1)
        H_total = n_pav * pe * 1000.0
    except Exception:
        return []
    membros = []
    agua = redes.get("agua_fria") or {}
    if agua.get("DN_mm"):
        d = _dn(agua["DN_mm"])
        x, y = SX_MM, SY_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-AGUA-PRU",
            "perfil": "Coluna agua fria DN%.0f (convencional p/ clash)"
                      % float(agua["DN_mm"]),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, 0.0], "p2": [x, y, H_total],
            "material": "PVC", "pavimento": "Prumada",
            "disciplina": "hidraulica"})
        z = H_total - Z_AGUA_RAMAL_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-AGUA-RAMAL",
            "perfil": "Ramal agua DN%.0f (convencional p/ clash)"
                      % float(agua["DN_mm"]),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, z], "p2": [min(x + 4000.0, Lx), y, z],
            "material": "PVC", "pavimento": "Terreo",
            "disciplina": "hidraulica"})
    esgoto = redes.get("esgoto") or {}
    dn_esg = esgoto.get("tubo_queda_DN_mm") or esgoto.get("ramal_DN_mm")
    if dn_esg:
        d = _dn(dn_esg)
        x, y = SX_MM + DX_ESGOTO_MM, SY_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-ESG-QUEDA",
            "perfil": "Esgoto DN%.0f (convencional p/ clash)" % float(dn_esg),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, -300.0], "p2": [x, y, H_total],
            "material": "PVC", "pavimento": "Prumada",
            "disciplina": "hidraulica"})
    pluvial = redes.get("pluvial") or {}
    dn_cond = pluvial.get("condutor_DN_mm")
    n_desc = int(pluvial.get("n_condutores") or 0)
    if dn_cond and n_desc > 0:
        d = _dn(dn_cond)
        try:
            _Lx, Ly = _envelope(estrutura)
        except Exception:
            return membros
        cantos = [(300.0, 300.0), (Lx - 300.0, 300.0),
                  (Lx - 300.0, Ly - 300.0), (300.0, Ly - 300.0)]
        for i in range(min(n_desc, 4)):
            x, y = cantos[i % 4]
            membros.append({
                "tipo": "Pipe", "marca": "H-PLUV-D%d" % (i + 1),
                "perfil": "Descida pluvial DN%.0f (convencional p/ clash)"
                          % float(dn_cond),
                "secao": {"forma": "ROUND", "D": d},
                "p1": [x, y, H_total], "p2": [x, y, 0.0],
                "material": "PVC", "pavimento": "Prumada",
                "disciplina": "hidraulica"})
    return membros


def membros_federados_casa(estrutura, resultado_eletrico, resultado_hidraulica):
    """Estrutura + instalacoes no frame comum (o da estrutura, sem conversao)."""
    import bim_edificio as bim

    membros = []
    for m in bim.membros_bim(estrutura):
        m = dict(m)
        m["marca"] = "C-" + str(m.get("marca", ""))
        m["disciplina"] = "estrutura"
        membros.append(m)
    disc = ["estrutura"]
    pares = (("eletrico", resultado_eletrico, membros_eletrica, "E-"),
             ("hidraulica", resultado_hidraulica, membros_hidraulica, "H-"))
    for nome, resultado, func, prefixo in pares:
        if not isinstance(resultado, dict):
            continue
        try:
            lst = func(estrutura, resultado)
        except Exception:
            continue
        for m in lst:
            m = dict(m)
            m["marca"] = prefixo + str(m.get("marca", ""))
            m["disciplina"] = nome
            membros.append(m)
        if lst:
            disc.append(nome)
    return membros, disc


def checa_interferencia_casa(estrutura, resultado_eletrico,
                             resultado_hidraulica, folga=1.0,
                             vol_min=1000.0):
    """Clash ENTRE disciplinas no federado da casa (AABB, sem FreeCAD).

    So pares de disciplinas DIFERENTES; intra-disciplina e' de cada vertical.
    Mesmo shape do clash do galpao/predio.
    """
    import geometria_membros as gm

    membros, _ = membros_federados_casa(estrutura, resultado_eletrico,
                                        resultado_hidraulica)
    caixas = []
    for mb in membros:
        disc = mb.get("disciplina")
        if disc is None:
            continue
        try:
            box = gm.aabb(mb)
        except Exception:
            continue
        caixas.append((mb.get("marca"), disc, mb.get("tipo"), box))
    clashes = []
    por_par = {}
    for i in range(len(caixas)):
        ma, da, ta, ba = caixas[i]
        for j in range(i + 1, len(caixas)):
            mb_, db, tb, bb = caixas[j]
            if da == db:
                continue
            # Ponto de luz no teto e' HOSPEDADO na laje (luminaria sob o forro),
            # nao furo a prever: a caixa do ponto toca a face inferior da laje
            # por construcao do envelope. Sem este filtro, todo ponto de luz
            # viraria "furacao na laje" com acao errada.
            par_tipos = {ta, tb}
            if par_tipos == {"Slab", "Luminaire"}:
                continue
            v = gm.volume_comum(ba, bb, folga=folga)
            if v > vol_min:
                par = "x".join(sorted((da, db)))
                por_par[par] = por_par.get(par, 0) + 1
                clashes.append({"a": ma, "b": mb_, "disciplinas": par,
                                "tipos": "%sx%s" % (ta, tb),
                                "vol_mm3": round(v, 0), "esperado": False})
    clashes.sort(key=lambda c: -c["vol_mm3"])
    return {"n_membros": len(caixas), "n_clashes": len(clashes),
            "n_revisar": len(clashes), "n_esperado": 0,
            "clashes": clashes, "revisar": list(clashes), "esperados": [],
            "por_par": por_par, "OK": not clashes,
            "OK_revisar": not clashes}


def relatorio_pt(rep):
    """Relatorio-texto do clash federado da casa."""
    L = ["CLASH FEDERADO DA CASA - INSTALACOES x ESTRUTURA (G58)",
         "  %d membros ; %d conflitos A REVISAR" % (
             rep["n_membros"], rep["n_clashes"])]
    if rep["por_par"]:
        L.append("  Por par: " + "; ".join(
            "%s=%d" % (k, v) for k, v in sorted(rep["por_par"].items())))
    for c in rep["clashes"][:30]:
        L.append("   ! %-16s x %-16s [%s] %s : %.0f mm3" % (
            c["a"], c["b"], c["disciplinas"], c["tipos"], c["vol_mm3"]))
    if len(rep["clashes"]) > 30:
        L.append("   ... (+%d)" % (len(rep["clashes"]) - 30))
    if not rep["n_clashes"]:
        L.append("  RESULTADO: nenhuma interferencia entre disciplinas > limite")
    else:
        L.append("  RESULTADO: %d A REVISAR - cada um e' um furo/furacao a "
                 "prever na estrutura" % rep["n_clashes"])
    return "\n".join(L)
