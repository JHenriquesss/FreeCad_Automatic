# ============================================================================
# ifc_tanque.py - MODELO IFC4 DO TANQUE-BASE (REV.02)
# Cada peca do calculo (projeto_rev02) vira um elemento IFC com perfil
# extrudado: tubos como IfcBeam / IfcColumn / IfcMember, chapas como IfcPlate,
# os seis apoios como IfcFooting de referencia. O peso de cada peca vai no pset
# Calc_Quantitativo, que e' o que a lista de material das pranchas le.
# Unidade do arquivo: milimetro (as cotas das pranchas saem em mm).
# ============================================================================
"""Emissor IFC do tanque-base integral."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import projeto_rev02 as P   # noqa: E402
import tanque_base as TB    # noqa: E402

# eixo da peca -> (x local, y local, z local = direcao da extrusao), em colunas
_EIXOS = {
    "x": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "y": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "z": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
}


def _n(x, casas=0):
    return ("%.*f" % (casas, x)).replace(".", ",")


def emitir(caminho, spec=None, com_conteiner=False):
    """Grava o IFC em `caminho` e devolve {'elementos': n, 'peso_kg': total}."""
    import ifcopenshell
    import ifcopenshell.api.aggregate
    import ifcopenshell.api.context
    import ifcopenshell.api.feature
    import ifcopenshell.api.geometry
    import ifcopenshell.api.project
    import ifcopenshell.api.pset
    import ifcopenshell.api.root
    import ifcopenshell.api.spatial
    import ifcopenshell.api.unit

    if (spec or P.SPEC_REV02)["apoios_por_lado"] != 3:
        raise NotImplementedError(
            "o modelo 3D do tanque-base esta' feito para 3 apoios por lado (conteiner de "
            "20 pes); para outro numero de apoios so' o calculo e' parametrico")

    spec = spec or P.SPEC_REV02
    g = P.geometria(spec)
    s, q, ch = spec["skid"], spec["tubo_quadro"], spec["chapas"]
    ti, ts = spec["tubo_travessa_inf"], spec["tubo_travessa_sup"]
    mm = 0.001   # as contas abaixo sao em metro; U converte para a unidade do arquivo
    U = 1000.0
    L, B, H = s["comp"] * mm, s["larg"] * mm, s["alt"] * mm

    m = ifcopenshell.api.project.create_file(version="IFC4")
    proj = ifcopenshell.api.root.create_entity(m, ifc_class="IfcProject",
                                               name="Tanque-base integral 20 pes")
    ifcopenshell.api.unit.assign_unit(m, length={"is_metric": True, "raw": "MILLIMETERS"})
    ctx = ifcopenshell.api.context.add_context(m, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        m, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW",
        parent=ctx)
    site = ifcopenshell.api.root.create_entity(m, ifc_class="IfcSite", name="Local")
    predio = ifcopenshell.api.root.create_entity(m, ifc_class="IfcBuilding", name="Tanque-base")
    piso = ifcopenshell.api.root.create_entity(m, ifc_class="IfcBuildingStorey", name="Terreo")
    ifcopenshell.api.aggregate.assign_object(m, products=[site], relating_object=proj)
    ifcopenshell.api.aggregate.assign_object(m, products=[predio], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(m, products=[piso], relating_object=predio)

    feitos, peso_total = [], 0.0

    def peca(classe, marca, perfil, origem, eixo, comprimento, peso=None, linear=True):
        """Extruda `perfil` (centrado na origem local) de `origem` ao longo de `eixo`."""
        nonlocal peso_total
        el = ifcopenshell.api.root.create_entity(m, ifc_class=classe, name=marca)
        mat = np.eye(4)
        if isinstance(eixo, str):
            colunas = _EIXOS[eixo]
        else:                               # direcao qualquer no plano x-z (escada)
            zl = np.array(eixo, dtype=float) / np.linalg.norm(eixo)
            xl = np.cross((0.0, 1.0, 0.0), zl)
            colunas = (xl, np.cross(zl, xl), zl)
        for col, v in enumerate(colunas):
            mat[:3, col] = v
        mat[:3, 3] = origem
        ifcopenshell.api.geometry.edit_object_placement(m, product=el, matrix=mat,
                                                        is_si=True)
        solido = m.createIfcExtrudedAreaSolid(
            perfil, None, m.createIfcDirection((0.0, 0.0, 1.0)), float(comprimento) * U)
        rep = m.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solido])
        ifcopenshell.api.geometry.assign_representation(m, product=el, representation=rep)
        ifcopenshell.api.spatial.assign_container(m, products=[el], relating_structure=piso)
        if peso is not None:
            props = {"Peso_kg": round(float(peso), 1), "Origem": "secao x comprimento"}
            if linear:
                props["Comprimento_m"] = round(float(comprimento), 3)
            ps = ifcopenshell.api.pset.add_pset(m, product=el, name="Calc_Quantitativo")
            ifcopenshell.api.pset.edit_pset(m, pset=ps, properties=props)
            peso_total += peso
        feitos.append(el)
        return el

    def tubo(t, deitado_em_x=False):
        """Perfil tubular: XDim e' a largura no plano, YDim a altura."""
        nome = "TB %sx%sx%s" % (_n(t["h"]), _n(t["b"]), _n(t["t"], 2))
        r_ext = TB.RAIO_EXTERNO_MAX_SOBRE_T * t["t"]
        xd, yd = (t["h"], t["b"]) if deitado_em_x else (t["b"], t["h"])
        return m.createIfcRectangleHollowProfileDef(
            "AREA", nome, None, float(xd), float(yd), float(t["t"]),
            float(r_ext - t["t"]), float(r_ext)), TB.tubo_retangular(t)["massa_kg_m"]

    def chapa(esp, larg_x, larg_y, corte=None):
        """`corte` = (a, b) em m: as duas medidas de corte da chapa, que vao para a lista."""
        nome = "CH %s" % _n(esp, 2)
        if corte:
            nome += " - %s x %s" % (_n(corte[0] * 1000), _n(corte[1] * 1000))
        return m.createIfcRectangleProfileDef("AREA", nome, None,
                                              float(larg_x) * U, float(larg_y) * U)

    def furo(elemento, perfil, origem, eixo, comprimento):
        """Abertura que atravessa `elemento` (IfcOpeningElement): aparece recortada."""
        ab = ifcopenshell.api.root.create_entity(m, ifc_class="IfcOpeningElement")
        mat = np.eye(4)
        for col, v in enumerate(_EIXOS[eixo]):
            mat[:3, col] = v
        mat[:3, 3] = origem
        ifcopenshell.api.geometry.edit_object_placement(m, product=ab, matrix=mat, is_si=True)
        solido = m.createIfcExtrudedAreaSolid(
            perfil, None, m.createIfcDirection((0.0, 0.0, 1.0)), float(comprimento) * U)
        ifcopenshell.api.geometry.assign_representation(
            m, product=ab,
            representation=m.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solido]))
        ifcopenshell.api.feature.add_feature(m, feature=ab, element=elemento)

    def circulo(d_mm):
        return m.createIfcCircleProfileDef("AREA", None, None, d_mm / 2 * mm * U)

    p_quadro, kg_quadro = tubo(q)
    p_montante, _ = tubo(q, deitado_em_x=True)        # 150 ao longo do comprimento
    p_ti, kg_ti = tubo(ti)
    p_ts, kg_ts = tubo(ts)
    qh, qb = q["h"] * mm, q["b"] * mm

    # montantes: 4 de canto e 2 no meio dos lados longos
    xs_m = (qh / 2, L / 2, L - qh / 2)
    # Os de canto param sob a chapa de topo, que fica no plano dos cantos do
    # conteiner; os do meio param no topo da gaiola (nao encostam no conteiner).
    det = spec["detalhes"]
    ct = det["chapa_topo"]
    h_canto, h_meio = H - ct["t"] * mm, g["z_topo_gaiola"] * mm
    for xc in xs_m:
        for yc in (qb / 2, B - qb / 2):
            alt = h_meio if xc == L / 2 else h_canto
            peca("IfcColumn", "M", p_montante, (xc, yc, 0.0), "z", alt, kg_quadro * alt)
    # chapas de topo, rentes ao canto externo, e cone no centro do canto ISO
    p_ct = chapa(ct["t"], ct["comp"] * mm, ct["larg"] * mm)
    p_cone = m.createIfcCircleProfileDef("AREA", "CONE ISO 1161 (ITEM COMERCIAL)", None,
                                         det["cone"]["d"] / 2 * mm * U)
    for sx in (0, 1):
        for sy in (0, 1):
            xc = L - ct["comp"] * mm / 2 if sx else ct["comp"] * mm / 2
            yc = B - ct["larg"] * mm / 2 if sy else ct["larg"] * mm / 2
            peca("IfcPlate", "CT", p_ct, (xc, yc, h_canto), "z", ct["t"] * mm,
                 ct["comp"] * mm * ct["larg"] * mm * ct["t"] * mm * TB.RHO_ACO, linear=False)
            xi = (L + spec["conteiner"]["S"] * mm) / 2 if sx else (L - spec["conteiner"]["S"] * mm) / 2
            yi = (B + spec["conteiner"]["P"] * mm) / 2 if sy else (B - spec["conteiner"]["P"] * mm) / 2
            peca("IfcBuildingElementProxy", "CONE", p_cone, (xi, yi, H), "z",
                 det["cone"]["h"] * mm)
    # longarinas e testeiras, nos dois niveis, entre montantes
    z_inf, z_sup = qh / 2, g["z_topo_gaiola"] * mm - qh / 2
    for z, sufixo in ((z_inf, "INF"), (z_sup, "SUP")):
        for yc in (qb / 2, B - qb / 2):
            for xa, xb in zip(xs_m, xs_m[1:]):
                comp = (xb - qh / 2) - (xa + qh / 2)
                peca("IfcBeam", "L-" + sufixo, p_quadro, (xa + qh / 2, yc, z), "x", comp,
                     kg_quadro * comp)
        for xc in (qb / 2, L - qb / 2):
            comp = B - 2 * qb
            peca("IfcBeam", "TE-" + sufixo, p_quadro, (xc, qb, z), "y", comp, kg_quadro * comp)
    # travessas: inferiores em pe' sob o fundo, superiores deitadas sobre a tampa
    x0 = (q["b"] + spec["folga_lateral"]) * mm
    ce, le, ae = (v * mm for v in g["tanque_ext"])
    vao = g["vao_travessa"] * mm
    for i in range(g["n_travessas"]):
        for t, perfil, kg, z, marca in (
                (ti, p_ti, kg_ti, ti["h"] * mm / 2, "TI"),
                (ts, p_ts, kg_ts, g["z_tampa"] * mm + ts["h"] * mm / 2, "TS")):
            meia = t["b"] * mm / 2
            xt = min(max(x0 + i * g["passo"] * mm, x0 + meia), x0 + ce - meia)
            peca("IfcMember", marca, perfil, (xt, qb, z), "y", vao, kg * vao)

    # tanque: fundo, tampa e quatro laterais
    rho = TB.RHO_ACO
    zf, zt = g["z_fundo"] * mm, g["z_tampa"] * mm
    cx, cy = x0 + ce / 2, x0 + le / 2
    el_fundo = peca("IfcPlate", "CH-FUNDO", chapa(ch["fundo"], ce, le, (ce, le)),
                    (cx, cy, zf), "z", ch["fundo"] * mm, ce * le * ch["fundo"] * mm * rho,
                    linear=False)
    el_tampa = peca("IfcPlate", "CH-TAMPA", chapa(ch["tampa"], ce, le, (ce, le)),
                    (cx, cy, zt - ch["tampa"] * mm), "z", ch["tampa"] * mm,
                    ce * le * ch["tampa"] * mm * rho, linear=False)
    tl = ch["lateral"] * mm
    alt_lat = (zt - ch["tampa"] * mm) - (zf + ch["fundo"] * mm)
    z_lat = zf + ch["fundo"] * mm
    for yc in (x0 + tl / 2, x0 + le - tl / 2):
        peca("IfcPlate", "CH-LATERAL", chapa(ch["lateral"], ce, tl, (ce, alt_lat)),
             (cx, yc, z_lat), "z", alt_lat, ce * tl * alt_lat * rho, linear=False)
    testas = [peca("IfcPlate", "CH-TESTA", chapa(ch["lateral"], tl, le - 2 * tl,
                                                 (le - 2 * tl, alt_lat)), (xc, cy, z_lat),
                   "z", alt_lat, (le - 2 * tl) * tl * alt_lat * rho, linear=False)
              for xc in (x0 + tl / 2, x0 + ce - tl / 2)]
    el_testa = testas[1]                    # a testa voltada para a baia tecnica

    # apoios de referencia: o produto de serie pede no minimo 350 x 350 mm
    p_bloco = m.createIfcRectangleProfileDef("AREA", "BLOCO 350x350 (REFERENCIA)", None,
                                             0.35 * U, 0.35 * U)
    cal = det["calco"]
    p_calco = chapa(cal["t"], cal["comp"] * mm, cal["larg"] * mm,
                    (cal["comp"] * mm, cal["larg"] * mm))
    kg_calco = cal["comp"] * cal["larg"] * cal["t"] * mm ** 3 * rho
    for xc in xs_m:
        for yc in (qb / 2, B - qb / 2):
            peca("IfcPlate", "CALCO", p_calco, (xc, yc, -cal["t"] * mm), "z", cal["t"] * mm,
                 kg_calco, linear=False)
            peca("IfcFooting", "APOIO", p_bloco, (xc, yc, -0.20 - cal["t"] * mm), "z", 0.20)
    # olhais de icamento: chapa no plano x-z, na face de topo dos montantes de canto
    ol = det["olhal"]
    p_olhal = chapa(ol["t"], ol["proj"] * mm, ol["t"] * mm, (ol["alt"] * mm, ol["proj"] * mm))
    z_olhal = h_canto - 0.02 - ol["alt"] * mm
    for xc in (-ol["proj"] * mm / 2, L + ol["proj"] * mm / 2):
        for yc in (qb / 2, B - qb / 2):
            el = peca("IfcPlate", "OLHAL", p_olhal, (xc, yc, z_olhal), "z", ol["alt"] * mm,
                      ol["proj"] * ol["alt"] * ol["t"] * mm ** 3 * rho, linear=False)
            furo(el, circulo(ol["furo"]), (xc, yc - ol["t"] * mm, z_olhal + ol["alt"] * mm / 2),
                 "y", 2 * ol["t"] * mm)

    # --- conexoes (indicativas) ---
    def cano(dn, nome=None):
        return m.createIfcCircleHollowProfileDef("AREA", nome or "DN%s" % _n(dn), None,
                                                 dn / 2 * mm * U, 0.004 * U)

    x_testa = x0 + ce                       # face do tanque voltada para a baia tecnica
    z_piso_tanque = zf + ch["fundo"] * mm
    # succao: sai baixo pela testa, entra na baia; por dentro vai ate' perto do fundo
    y_suc, z_suc = B / 2 - 0.60, z_piso_tanque + 0.09
    peca("IfcBuildingElementProxy", "SUCCAO", cano(det["dn_succao"]),
         (x_testa - 0.40, y_suc, z_suc), "x", 0.40 + 0.10)
    fl = det["flange_succao"]
    peca("IfcBuildingElementProxy", "FLANGE", m.createIfcCircleHollowProfileDef(
        "AREA", "FLANGE DN%s" % _n(det["dn_succao"]), None, fl["d"] / 2 * mm * U,
        (fl["d"] - det["dn_succao"]) / 2 * mm * U),
        (x_testa + 0.10 - fl["t"] * mm, y_suc, z_suc), "x", fl["t"] * mm)
    peca("IfcBuildingElementProxy", "VALVULA", m.createIfcRectangleProfileDef(
        "AREA", "VALVULA DE ESFERA DN%s" % _n(det["dn_succao"]), None, 0.16 * U, 0.16 * U),
        (x_testa + 0.10, y_suc, z_suc), "x", 0.20)
    peca("IfcBuildingElementProxy", "ENGATE", cano(det["dn_succao"] + 20.0, "ENGATE RAPIDO DN%s" % _n(det["dn_succao"])),
         (x_testa + 0.30, y_suc, z_suc), "x", 0.08)
    furo(el_testa, circulo(det["dn_succao"] + 2.0), (x_testa - 0.02, y_suc, z_suc), "x", 0.04)
    # poco do pescador: caixa sob o fundo, no ultimo vao entre travessas inferiores,
    # com o tubo pescador descendo ate' 20 mm do fundo do poco
    pc = det["poco"]
    xp = x0 + (g["n_travessas"] - 1.5) * g["passo"] * mm
    z_poco = zf - pc["prof"] * mm                    # face interna do fundo do poco
    tp = pc["t"] * mm
    peca("IfcPlate", "POCO", chapa(pc["t"], pc["comp"] * mm, pc["larg"] * mm),
         (xp, y_suc, z_poco - tp), "z", tp)
    furo(el_fundo, m.createIfcRectangleProfileDef(
        "AREA", None, None, (pc["comp"] * mm - tp) * U, (pc["larg"] * mm - tp) * U),
        (xp, y_suc, zf - 0.01), "z", ch["fundo"] * mm + 0.02)
    for dx, dy, lx_, ly_ in ((pc["comp"] * mm / 2, 0, tp, pc["larg"] * mm),
                             (-pc["comp"] * mm / 2, 0, tp, pc["larg"] * mm),
                             (0, pc["larg"] * mm / 2, pc["comp"] * mm, tp),
                             (0, -pc["larg"] * mm / 2, pc["comp"] * mm, tp)):
        peca("IfcPlate", "POCO", chapa(pc["t"], lx_, ly_), (xp + dx, y_suc + dy, z_poco),
             "z", pc["prof"] * mm)
    peca("IfcBuildingElementProxy", "PESCADOR", cano(det["dn_succao"]),
         (xp, y_suc, z_poco + 0.02), "z", z_suc - z_poco - 0.02)
    # nivel: transmissor hidrostatico embaixo e chave de nivel alto-alto independente,
    # os dois na testa (sobre a tampa so' ha' 65 mm ate' o conteiner)
    hh = z_piso_tanque + P.capacidade(spec)["niveis"]["alarme_alto_alto"]["lamina_mm"] * mm
    for marca, zc in (("SENSOR-NIVEL", z_piso_tanque + 0.04), ("CHAVE-HH", hh)):
        peca("IfcBuildingElementProxy", marca, cano(50.0), (x_testa, B / 2 - 0.30, zc), "x",
             0.12)
        furo(el_testa, circulo(52.0), (x_testa - 0.02, B / 2 - 0.30, zc), "x", 0.04)
    peca("IfcPlate", "PLACA", chapa(2.0, 0.002, 0.20), (x_testa + 0.002, B / 2 + 0.85,
                                                        (zf + zt) / 2), "z", 0.15)
    peca("IfcBuildingElementProxy", "LAVAGEM", cano(det["dn_lavagem"]),
         (x_testa - 0.05, B / 2 + 0.60, zt - 0.12), "x", 0.05 + 0.20)
    furo(el_testa, circulo(det["dn_lavagem"] + 2.0), (x_testa - 0.02, B / 2 + 0.60, zt - 0.12),
         "x", 0.04)
    bi = det["boca_inspecao"]
    # vao livre da boca: 40 mm menor que a tampa em cada lado (aba da junta)
    furo(el_testa, m.createIfcRectangleProfileDef(
        "AREA", None, None, (bi["larg"] - 80.0) * mm * U, (bi["alt"] - 80.0) * mm * U),
        (x_testa - 0.02, B / 2, (zf + zt) / 2), "x", 0.04)
    peca("IfcPlate", "BI", chapa(bi["t"], bi["t"] * mm, bi["larg"] * mm),
         (x_testa + bi["t"] * mm / 2, B / 2, (zf + zt) / 2 - bi["alt"] * mm / 2), "z",
         bi["alt"] * mm)
    # Respiro e entradas de esgoto saem pela TAMPA e atravessam o piso do conteiner.
    # Pela testa da baia o respiro ficaria abaixo do nivel alto-alto: a tampa esta'
    # a 65 mm do conteiner e as longarinas superiores fecham a faixa de cima.
    topo_conteiner = H + spec["conteiner"]["alt"] * mm
    y_shaft = B - qb - spec["folga_lateral"] * mm - 0.30
    # todo tubo que sai pela tampa passa no MEIO de um vao entre travessas superiores
    n_vaos = g["n_travessas"] - 1
    passo = g["passo"] * mm

    def meio_do_vao(i):
        return x0 + (i + 0.5) * passo

    peca("IfcBuildingElementProxy", "RESPIRO", cano(spec["adotado"]["d_respiro_mm"]),
         (meio_do_vao(n_vaos - 1), y_shaft, zt), "z", topo_conteiner + 0.30 - zt)
    furo(el_tampa, circulo(spec["adotado"]["d_respiro_mm"] + 2.0),
         (meio_do_vao(n_vaos - 1), y_shaft, zt - 0.02), "z", 0.04)
    # quebra-vacuo: derivacao no respiro, dentro do shaft (nao cabe sobre a tampa)
    peca("IfcBuildingElementProxy", "QUEBRA-VACUO", cano(50.0),
         (meio_do_vao(n_vaos - 1) - 0.20, y_shaft, H + 0.60), "x", 0.20)
    # degraus de acesso ate' o piso do conteiner (NBR 9050), na frente: a posicao
    # real segue a porta do conteiner
    ac = P.acesso(spec)
    p_degrau = m.createIfcRectangleProfileDef("AREA", "DEGRAU %s x %s" % (
        _n(ac["piso_mm"]), _n(det["largura_escada"])), None,
        ac["piso_mm"] * mm * U, det["largura_escada"] * mm * U)
    for k in range(1, ac["espelhos"]):
        topo = (ac["desnivel_mm"] - k * ac["espelho_mm"]) * mm
        peca("IfcBuildingElementProxy", "DEGRAU", p_degrau,
             (-(k - 0.5) * ac["piso_mm"] * mm, B / 2, topo - 0.04), "z", 0.04)
    pm, em, ne = ac["piso_mm"] * mm, ac["espelho_mm"] * mm, ac["espelhos"]
    rampa = (pm, 0.0, em)                              # direcao da linha dos degraus
    comp_rampa = float(np.hypot(pm, em)) * ne
    cor = det["corrimao"]
    p_cor = m.createIfcCircleHollowProfileDef("AREA", "TUBO %s" % _n(cor["d"]), None,
                                              cor["d"] / 2 * mm * U, 0.003 * U)
    for lado in (-1, 1):
        yb = B / 2 + lado * (det["largura_escada"] * mm / 2 + 0.025)
        # banzo: mesmo tubo das travessas, 100 mm abaixo da linha dos degraus
        peca("IfcBuildingElementProxy", "BANZO", p_ti, (-ne * pm + 0.30, yb, 0.0), rampa,
             comp_rampa - 0.36)
        for alt_c in cor["alturas"]:
            peca("IfcBuildingElementProxy", "CORRIMAO", p_cor,
                 (-ne * pm, yb, alt_c * mm), rampa, comp_rampa)
        for xk, zk in ((-ne * pm, 0.0), (0.0, ne * em)):
            peca("IfcBuildingElementProxy", "CORRIMAO", p_cor, (xk, yb, max(zk - 0.84, 0.0)),
                 "z", zk + max(cor["alturas"]) * mm - max(zk - 0.84, 0.0))
    for k in range(det["n_entradas"]):
        xe = meio_do_vao(int(n_vaos * (k + 1) / (det["n_entradas"] + 1)))
        peca("IfcBuildingElementProxy", "ENTRADA", cano(det["dn_entrada"]),
             (xe, B / 2, zt), "z", H + 0.10 - zt)
        furo(el_tampa, circulo(det["dn_entrada"] + 2.0), (xe, B / 2, zt - 0.02), "z", 0.04)
    if com_conteiner:
        p_cont = m.createIfcRectangleProfileDef("AREA", "CONTEINER 1CC (REFERENCIA)", None,
                                                L * U, B * U)
        peca("IfcBuildingElementProxy", "CONTEINER", p_cont, (L / 2, B / 2, H), "z",
             spec["conteiner"]["alt"] * mm)

    m.write(caminho)
    return {"elementos": len(feitos), "peso_kg": round(peso_total, 1), "caminho": caminho}


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else "tanque_base_rev02.ifc"
    print(emitir(destino, com_conteiner="--conteiner" in sys.argv))
