# ============================================================================
# bim_instalacoes_edificio.py - GEOMETRIA DAS INSTALACOES NO FRAME DA ESTRUTURA
#
# G53: o calculo das instalacoes existia como numero (DN, secao, gates) e a
# estrutura existia como MODELO (bim_edificio), mas nunca no MESMO frame.
# Sem posicao no modelo federado, o clash nao tem o que achar - e o furo que
# a viga nao tem passa em silencio.
#
# Este modulo e' a fronteira geometrica: prumadas de agua/esgoto com tracado,
# eletrocalha + prumada eletrica, e rede de incendio, todas no MESMO frame do
# bim_edificio (mm; X=vaos_x, Y=vaos_y, Z=altura, origem no canto (0,0), base
# do 1o lance em z=0; secao de barra em METROS; caixa em MM).
#
# TRACADO CONVENCIONAL, nao leiaute de arquitetura. A planta da unidade nao
# existe neste framework para o edificio (a propria hidraulica publica
# tracado_das_prumadas como nao modelado no dimensionamento). O que aqui se
# fixa e' um SHAFT deterministico no primeiro painel (1,0 m do canto), com
# verticais que furam as lajes e horizontais por pavimento que cruzam as
# vigas na altura da nervura. E' o tracado minimo que torna o clash CAPAZ de
# apontar o furo - a coordenacao real desloca o shaft, nao o inventa.
#
# REGRAS:
# - peca que ninguem calculou nao entra no modelo (disciplina ausente -> []).
# - DN/secao lidos do RESULTADO do calculo; sem ele, nada e' arbitrado.
# - coluna de incendio DN65 fixo (NBR 13714, hidrante DN65) com proveniencia
#   declarada; nao e' dimensionamento, e' posicao para clash.
# - verticais cruzam lajes de proposito (furo na laje); horizontais correm a
#   250-400 mm abaixo do topo da laje, DENTRO da altura da nervura, para que
#   o cruzamento com a viga seja detectavel como furo na viga.
# ============================================================================
"""Geometria das instalacoes do edificio no frame da estrutura (G53)."""

from __future__ import annotations

# Shaft convencional: 1,0 m do canto, dentro do primeiro painel. Qualquer
# vaos_x/vaos_y real (> 2 m) contem o ponto; pilar fica no eixo, nunca a 1 m.
SX_MM = 1000.0
SY_MM = 1000.0
# Afastamentos dentro do shaft (mm): cada prumada tem o seu eixo.
DX_ESGOTO_MM = 300.0
DX_VENT_MM = 600.0
DY_ELET_MM = 300.0
DY_INC_MM = 600.0
# Horizontais correm ABAIXO do topo da laje, dentro da nervura (viga h=500,
# laje h=100 -> nervura de 400 mm). A 250-400 mm o tubo esta na altura da
# viga: cruzar uma VY/VX e' furo na viga, nao folga acima dela.
Z_HID_MM = 250.0
Z_ELET_MM = 400.0
Z_INC_MM = 350.0
# Coluna de incendio: DN65 (NBR 13714, hidrante DN65), posicao para clash.
D_INCENDIO_M = 0.065
# Altura da coluna de agua ACIMA do ultimo nivel (mm): o barrilete/reservatorio
# superior. G54-rev: e' um valor DECLARADO aqui, nao lido do dimensionamento - a
# altura real depende do reservatorio, que o `hidraulica_edificio` nao posiciona.
# Antes esta linha lia `gate_pressao_estatica.desnivel_m`, multiplicava por ZERO
# e somava 3000: parecia proveniencia e nao era (rotulo x calculo).
H_RESERVATORIO_MM = 3000.0
# Eletrocalha padrao do tracado (bandeja 100x50, a mesma do galpao).
ELET_BF_M = 0.10
ELET_D_M = 0.05


def _eixos(vaos):
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + float(v))
    return xs


def _niveis(estrutura, pe_direito):
    """Cotas do topo da laje por pavimento, base->topo (mm). Delega ao
    bim_edificio para nao criar segunda descricao dos andares."""
    import bim_edificio as bim

    return bim.niveis(estrutura, pe_direito)


def _pe_direito(estrutura, contexto=None):
    try:
        import bim_edificio as bim

        return float(bim._pe_direito(estrutura["pilares"]))
    except Exception:
        pass
    if isinstance(contexto, dict) and contexto.get("pe_direito"):
        return float(contexto["pe_direito"])
    raise ValueError("pe-direito indeterminavel: sem pilares dimensionados")


def _dn(valor, nome="DN"):
    try:
        v = float(valor)
    except Exception:
        return None
    return v / 1000.0 if v > 1.0 else v


def membros_hidraulica(estrutura, resultado, pe_direito=None):
    """Prumadas de agua/esgoto + pluvial no frame da estrutura.

    Le DNs do `hidraulica_edificio.dimensiona`. Sem resultado -> [].
    """
    if not isinstance(resultado, dict):
        return []
    try:
        import bim_edificio as bim

        pe = float(pe_direito if pe_direito else bim._pe_direito(
            estrutura["pilares"]))
        lvls = bim.niveis(estrutura, pe)
    except Exception:
        return []
    pav = estrutura.get("pavimento") or {}
    try:
        xs = _eixos(pav["vaos_x"])
        ys = _eixos(pav["vaos_y"])
    except Exception:
        return []
    Lx = xs[-1] * 1000.0
    H_total = lvls[-1]["elevacao_mm"] if lvls else 0.0
    col = resultado.get("coluna") or {}
    dn_col = (col.get("dn") or {}).get("DN_mm")
    esg = resultado.get("esgoto") or {}
    dn_queda = (esg.get("tubo_de_queda") or {}).get("DN_mm")
    dn_vent = esg.get("coluna_ventilacao_DN_mm")
    plv = resultado.get("pluvial") or {}
    dn_cond = (plv.get("condutor") or {}).get("DN_mm")
    n_desc = int(plv.get("n_descidas") or 1)
    membros = []
    if dn_col:
        d = _dn(dn_col)
        x, y = SX_MM, SY_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-AGUA-PRU",
            "perfil": "Coluna agua fria DN%.0f" % float(dn_col),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, 0.0], "p2": [x, y, H_total + H_RESERVATORIO_MM],
            "material": "PVC", "pavimento": "Prumada",
            "disciplina": "hidraulica"})
        for nv in lvls:
            z = nv["elevacao_mm"] - Z_HID_MM
            membros.append({
                "tipo": "Pipe", "marca": "H-AGUA-R-%s" % nv["nome"],
                "perfil": "Ramal agua DN%.0f" % float(dn_col),
                "secao": {"forma": "ROUND", "D": d},
                "p1": [x, y, z], "p2": [min(x + 4000.0, Lx), y, z],
                "material": "PVC", "pavimento": nv["nome"],
                "disciplina": "hidraulica"})
    if dn_queda:
        d = _dn(dn_queda)
        x, y = SX_MM + DX_ESGOTO_MM, SY_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-ESG-PRU",
            "perfil": "Tubo de queda DN%.0f" % float(dn_queda),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, -300.0], "p2": [x, y, H_total],
            "material": "PVC", "pavimento": "Prumada",
            "disciplina": "hidraulica"})
        for nv in lvls:
            z = nv["elevacao_mm"] - Z_HID_MM
            membros.append({
                "tipo": "Pipe", "marca": "H-ESG-R-%s" % nv["nome"],
                "perfil": "Ramal esgoto DN%.0f" % float(dn_queda),
                "secao": {"forma": "ROUND", "D": d},
                "p1": [x, y, z], "p2": [min(x + 3500.0, Lx), y, z],
                "material": "PVC", "pavimento": nv["nome"],
                "disciplina": "hidraulica"})
    if dn_vent:
        d = _dn(dn_vent)
        x, y = SX_MM + DX_VENT_MM, SY_MM
        membros.append({
            "tipo": "Pipe", "marca": "H-VENT-PRU",
            "perfil": "Ventilacao DN%.0f" % float(dn_vent),
            "secao": {"forma": "ROUND", "D": d},
            "p1": [x, y, 0.0], "p2": [x, y, H_total + 1000.0],
            "material": "PVC", "pavimento": "Prumada",
            "disciplina": "hidraulica"})
    if dn_cond and n_desc > 0:
        d = _dn(dn_cond)
        cantos = [(300.0, 300.0), (Lx - 300.0, 300.0),
                  (Lx - 300.0, ys[-1] * 1000.0 - 300.0),
                  (300.0, ys[-1] * 1000.0 - 300.0)]
        for i in range(n_desc):
            x, y = cantos[i % 4]
            membros.append({
                "tipo": "Pipe", "marca": "H-PLUV-D%d" % (i + 1),
                "perfil": "Descida pluvial DN%.0f" % float(dn_cond),
                "secao": {"forma": "ROUND", "D": d},
                "p1": [x, y, H_total], "p2": [x, y, 0.0],
                "material": "PVC", "pavimento": "Prumada",
                "disciplina": "hidraulica"})
    return membros


def membros_eletrica(estrutura, resultado, pe_direito=None):
    """Prumada eletrica + eletrocalhas por pavimento no frame da estrutura."""
    if not isinstance(resultado, dict):
        return []
    try:
        import bim_edificio as bim

        pe = float(pe_direito if pe_direito else bim._pe_direito(
            estrutura["pilares"]))
        lvls = bim.niveis(estrutura, pe)
    except Exception:
        return []
    pav = estrutura.get("pavimento") or {}
    try:
        xs = _eixos(pav["vaos_x"])
    except Exception:
        return []
    Lx = xs[-1] * 1000.0
    H_total = lvls[-1]["elevacao_mm"] if lvls else 0.0
    pru = resultado.get("prumada") or {}
    secao = pru.get("secao_mm2", "?")
    x, y = SX_MM, SY_MM + DY_ELET_MM
    membros = [{
        "tipo": "CableCarrier", "marca": "E-PRU-VERT",
        "perfil": "Prumada eletrica %s mm2 (bandeja 100x50)" % secao,
        "secao": {"forma": "RECT", "bf": ELET_BF_M, "d": ELET_D_M},
        "p1": [x, y, 0.0], "p2": [x, y, H_total],
        "material": "Aco", "pavimento": "Prumada",
        "disciplina": "eletrico"}]
    for nv in lvls:
        z = nv["elevacao_mm"] - Z_ELET_MM
        membros.append({
            "tipo": "CableCarrier", "marca": "E-CALHA-%s" % nv["nome"],
            "perfil": "Eletrocalha 100x50",
            "secao": {"forma": "RECT", "bf": ELET_BF_M, "d": ELET_D_M},
            "p1": [0.0, y, z], "p2": [Lx, y, z],
            "material": "Aco", "pavimento": nv["nome"],
            "disciplina": "eletrico"})
        base = nv["elevacao_mm"] - pe * 1000.0
        membros.append({
            "tipo": "Board", "marca": "E-QD-%s" % nv["nome"],
            "perfil": "Quadro de pavimento",
            "dims": [400.0, 200.0, 600.0],
            "centro": [x, y + 400.0, base + 1500.0],
            "material": "Aco", "pavimento": nv["nome"],
            "disciplina": "eletrico"})
    return membros


def membros_incendio(estrutura, resultado, pe_direito=None):
    """Rede de incendio: coluna de hidrantes + hidrante por pavimento.

    A coluna e' DN65 (NBR 13714) em posicao para clash; os hidrantes saem um
    por pavimento ocupado. Sem resultado de incendio -> [].
    """
    if not isinstance(resultado, dict):
        return []
    try:
        import bim_edificio as bim

        pe = float(pe_direito if pe_direito else bim._pe_direito(
            estrutura["pilares"]))
        lvls = bim.niveis(estrutura, pe)
    except Exception:
        return []
    H_total = lvls[-1]["elevacao_mm"] if lvls else 0.0
    x, y = SX_MM + DX_ESGOTO_MM, SY_MM + DY_INC_MM
    membros = [{
        "tipo": "Pipe", "marca": "I-COL-HID",
        "perfil": "Coluna hidrantes DN65 (NBR 13714, posicao p/ clash)",
        "secao": {"forma": "ROUND", "D": D_INCENDIO_M},
        "p1": [x, y, 0.0], "p2": [x, y, H_total],
        "material": "Aco", "pavimento": "Prumada",
        "disciplina": "incendio"}]
    for nv in lvls:
        z = nv["elevacao_mm"] - Z_INC_MM
        membros.append({
            "tipo": "Pipe", "marca": "I-RAMAL-%s" % nv["nome"],
            "perfil": "Ramal hidrante DN65",
            "secao": {"forma": "ROUND", "D": D_INCENDIO_M},
            "p1": [x, y, z], "p2": [x + 1500.0, y, z],
            "material": "Aco", "pavimento": nv["nome"],
            "disciplina": "incendio"})
        base = nv["elevacao_mm"] - pe * 1000.0
        membros.append({
            "tipo": "Hydrant", "marca": "I-HID-%s" % nv["nome"],
            "perfil": "Hidrante de pavimento",
            "dims": [500.0, 250.0, 900.0],
            "centro": [x + 1700.0, y, base + 900.0],
            "material": "Aco", "pavimento": nv["nome"],
            "disciplina": "incendio"})
    return membros


def membros_federados_edificio(estrutura, instalacoes, pe_direito=None):
    """Estrutura + instalacoes no frame comum (o da estrutura, sem conversao).

    instalacoes: {'hidraulica': resultado, 'eletrico': resultado,
                  'incendio': resultado} (cada um ou None).
    Prefixa a marca por disciplina (C-/P-/E-/I-) como o federado do galpao.
    """
    import bim_edificio as bim

    membros = []
    for m in bim.membros_bim(estrutura, pe_direito):
        m = dict(m)
        m["marca"] = "C-" + str(m.get("marca", ""))
        m["disciplina"] = "estrutura"
        membros.append(m)
    disc = ["estrutura"]
    inst = instalacoes or {}
    mapa = (("hidraulica", membros_hidraulica, "P-"),
            ("eletrico", membros_eletrica, "E-"),
            ("incendio", membros_incendio, "I-"))
    for nome, func, prefixo in mapa:
        res = inst.get(nome)
        if not isinstance(res, dict):
            continue
        try:
            lst = func(estrutura, res, pe_direito)
        except Exception:
            continue
        for m in lst:
            m = dict(m)
            m["marca"] = prefixo + str(m.get("marca", ""))
            m["disciplina"] = ({"P-": "hidraulica", "E-": "eletrico",
                                "I-": "incendio"}[prefixo])
            membros.append(m)
        if lst:
            disc.append(nome)
    return membros, disc


def _eixo_membro(mb):
    """Direcao normalizada de um membro barra (p1->p2) ou None (caixa)."""
    try:
        p1, p2 = mb.get("p1"), mb.get("p2")
        if p1 is None or p2 is None:
            return None
        v = (float(p2[0]) - float(p1[0]), float(p2[1]) - float(p1[1]),
             float(p2[2]) - float(p1[2]))
        n = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5
        if n <= 0:
            return None
        return (v[0] / n, v[1] / n, v[2] / n)
    except Exception:
        return None


_TIPOS_BARRA_INST = ("Pipe", "CableCarrier")


def _tipos_do_par(tipos):
    """'BeamxPipe' -> ('Beam','Pipe'). Tipos conhecidos nao contem 'x'."""
    for conhecido in ("Column", "CableCarrier", "Footing", "Member", "Plate",
                      "Slab", "Beam", "Pile", "Pipe", "Board", "Hydrant",
                      "Luminaire", "Outlet", "Cable", "Earthing"):
        if tipos.startswith(conhecido + "x"):
            return conhecido, tipos[len(conhecido) + 1:]
    ps = tipos.split("x")
    return (ps[0], ps[1]) if len(ps) == 2 else (tipos, "")


def cruzamentos_edificio(membros, report):
    """Geometria declarada do cruzamento por clash (G55).

    Para cada clash estrutura x instalacao com Beam/Slab, declara "transversal"
    (passagem que fura: eletrocalha perpendicular a viga, prumada vertical na
    laje) ou "longitudinal" (tubo correndo ao longo do elemento = embutido
    13.2.6, nao furo). Criterio: |cos| entre eixos < 0,5 -> transversal;
    laje x tubo vertical -> transversal, x tubo horizontal -> longitudinal.
    Sem eixo (caixa) ou fora de Beam/Slab, sem hint (conflito). Chave
    (a, b, tipos), pronta para compatibilizacao.gerar_pendencias.
    """
    mapa = {}
    for m in membros or []:
        try:
            mapa[str(m.get("marca"))] = m
        except Exception:
            continue
    hints = {}
    for c in (report or {}).get("clashes", []):
        a, b, tipos = c.get("a"), c.get("b"), str(c.get("tipos") or "")
        ta, tb = _tipos_do_par(tipos)
        ma, mb = mapa.get(str(a)), mapa.get(str(b))
        if ma is None or mb is None:
            continue
        da, db = ma.get("disciplina"), mb.get("disciplina")
        if da == "estrutura":
            test, tinst, mest, minst = ta, tb, ma, mb
        elif db == "estrutura":
            test, tinst, mest, minst = tb, ta, mb, ma
        else:
            continue
        if tinst not in _TIPOS_BARRA_INST:
            continue
        if test == "Beam":
            e_est, e_inst = _eixo_membro(mest), _eixo_membro(minst)
            if e_est is None or e_inst is None:
                continue
            cos = abs(e_est[0] * e_inst[0] + e_est[1] * e_inst[1]
                      + e_est[2] * e_inst[2])
            hints[(a, b, tipos)] = {
                "direcao": "transversal" if cos < 0.5 else "longitudinal"}
        elif test == "Slab":
            e_inst = _eixo_membro(minst)
            if e_inst is None:
                continue
            hints[(a, b, tipos)] = {
                "direcao": ("transversal" if abs(e_inst[2]) > 0.9
                            else "longitudinal")}
    return hints


def checa_interferencia_edificio(estrutura, instalacoes, pe_direito=None,
                                 folga=1.0, vol_min=1000.0):
    """Clash ENTRE disciplinas no federado do edificio (AABB, sem FreeCAD).

    So pares de disciplinas DIFERENTES; intra-disciplina e' de cada vertical.
    Retorna o mesmo shape do clash do galpao (n_membros, n_clashes, clashes,
    por_par, OK, OK_revisar). O clash que importa aqui e' instalacao x
    estrutura: ele aponta o furo que a viga/laje nao tem.
    """
    import geometria_membros as gm

    membros, _ = membros_federados_edificio(estrutura, instalacoes, pe_direito)
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
    L = ["CLASH FEDERADO DO EDIFICIO - INSTALACOES x ESTRUTURA (G53)",
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
