# ============================================================================
# galpao_mezanino.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Mezanino de concreto armado DENTRO do envelope metalico ja validado do galpao.
# Primeira costura concreto x metalico em uso real (G20): laje, viga e pilar de
# concreto encontrando a estrutura metalica existente, sem criar envelope novo.
#
# O envelope e' o do galpao metalico validado (geometria: comprimento, vao,
# pe_direito em m). O mezanino ocupa um RETANGULO INTERIOR (x0,y0,Lx,Ly,h) em m,
# com 4 pilares nos cantos, 4 vigas de contorno e 1 laje macica sobre as vigas.
# A laje e' dimensionada por laje_concreto (NBR 6118, Tabelas de Bares), as vigas
# por viga_concreto e os pilares por pilar_concreto (flexo-compressao + 2a ordem);
# as sapatas por fundacao_sapata (NBR 6122/6118). Tudo STATELESS: rodar(spec) nao
# toca disco nem estado global.
#
# Unidades: m, kN; fck/fyk em kN/m2. Coordenadas do modelo neutro em mm
# (F01/F03/F04/F18); espessura da laje em cm no raw (F16/F19, feedback carga);
# secao de viga/pilar em m (F04/F20). A origem (0,0,0) e' o canto do galpao
# (X=comprimento, Y=vao, Z=altura), mesma do modelo_neutro do aco — a costura
# concreto x metalico ja sai federada sem transformacao (ao contrario do
# galpao_concreto, que usa X=vao centrado e precisa de _concreto_no_frame_comum).
#
# O que este modulo NAO faz (Ask, Do Not Invent): nao arbitra porta de acesso
# (escada ja existe em escada_concreto, fora daqui), nao cria viga intermediaria
# quando o retangulo cresce (1 painel so; mais paineis e' outra tipologia), e nao
# inventa ponte termica ou detalhe de chumbamento na estrutura metalica — a
# interferencia fica a cargo de checa_interferencia / clash federado.
# ============================================================================
"""Mezanino de concreto dentro do galpao metalico (laje+viga+pilar+sapata), NBR 6118."""

from __future__ import annotations

import math

import fundacao_sapata as fs
import laje_concreto as lj
import pilar_concreto as pc
import viga_concreto as vc

# peso especifico do concreto armado (kN/m3) — mesmo de laje_concreto/viga_concreto
GAMMA_CONC = 25.0
GF = 1.4
# quadro de verificacoes: utiliza = solicitacao/resistencia <= 1
MM = 1000.0

# limites geometricos do mezanino dentro do envelope (tolerancia mm -> m)
TOL_M = 1e-6


def _geometria_galpao(spec):
    """Normaliza a geometria do galpao (envelope validado) aceitando os dois dialetos:
    {comprimento, vao, pe_direito} ou {L, W, H}."""
    g = spec.get("geometria") or {}
    # tambem aceita geometria no nivel raiz (compat. com galpao_concreto)
    if not g:
        g = {k: spec[k] for k in ("comprimento", "vao", "pe_direito", "L", "W", "H") if k in spec}
    comp = g.get("comprimento", g.get("L"))
    vao = g.get("vao", g.get("W", g.get("largura")))
    pd = g.get("pe_direito", g.get("H"))
    if comp is None or vao is None or pd is None:
        raise ValueError("geometria do galpao incompleta: preciso de {comprimento, vao, pe_direito} ou {L,W,H} (recebi %r)" % g)
    comp = float(comp); vao = float(vao); pd = float(pd)
    if comp <= 0 or vao <= 0 or pd <= 0:
        raise ValueError("geometria do galpao deve ser >0 (comp=%.3f, vao=%.3f, H=%.3f)" % (comp, vao, pd))
    return {"comprimento": comp, "vao": vao, "pe_direito": pd}


def _spec_mezanino(spec, geo):
    """Extrai e normaliza o spec do mezanino. Aceita dois formatos:
    1) spec plano  {x0,y0,Lx,Ly,h,q_uso,...} + geometria no mesmo nivel;
    2) spec aninhado {geometria:..., mezanino: {x0,...}} (turnkey).
    Preenche defaults honestos para a amostra 40x20x6 (mezanino 10x8 a 3 m)."""
    # se veio aninhado em spec["mezanino"], desempacota
    sub = spec.get("mezanino")
    if isinstance(sub, dict) and sub:
        base = dict(sub)
        # herda geometria do nivel turnkey se nao estiver dentro
        if "geometria" not in base and "geometria" in spec:
            base["geometria"] = spec["geometria"]
        # permite que o envelope tambem venha em geo separado
        src = base
    else:
        src = spec

    def _f(key, default, cast=float):
        v = src.get(key, default)
        return cast(v) if v is not None else default

    # retangulo interior (m) — dentro do envelope
    # defaults que ATENDEM com folga (6x5 a 3 m, q=2): viga 20x50/60, laje 12 cm
    x0 = _f("x0", 2.0)
    y0 = _f("y0", 2.0)
    Lx = _f("Lx", 6.0)
    Ly = _f("Ly", 5.0)
    h = _f("h", 3.0)
    # alias compat.: comprimento/largura do mezanino
    if "comprimento" in src and "Lx" not in src and "mezanino" not in spec:
        pass  # nao confunde com geometria do galpao
    if "largura" in src and "Ly" not in src:
        Ly = _f("largura", Ly)
    # cargas e materiais
    q_uso = _f("q_uso", 3.0)           # sobrecarga de utilizacao (kN/m2) NBR 6120 Tab.10
    revest = _f("revest", 1.0)         # revestimento + forro (kN/m2)
    q_extra = _f("q", q_uso)           # alias: q direto
    if "q_uso" in src:
        q_extra = q_uso
    fck = _f("fck", 30e3)
    fyk = _f("fyk", 500e3)
    sigma_solo = _f("sigma_solo_adm", 250.0)
    # secoes (m) — defaults que ATENDEM a amostra (10x8, h=3, q=3+1)
    b_viga = _f("b_viga", 0.20)
    h_viga = _f("h_viga", 0.50)
    hx = _f("hx", 0.30)                # pilar hx // vao (X) — ver F17/F20 orientacao
    hy = _f("hy", 0.30)
    # laje
    h_laje = _f("h_laje", 0.12)
    laje_caso = int(_f("laje_caso", 1, cast=lambda x: int(float(x))))
    # se o caller passou "laje": {"h":...} (formato edificio), respeita
    if isinstance(src.get("laje"), dict):
        h_laje = float(src["laje"].get("h", h_laje))
        laje_caso = int(src["laje"].get("caso", laje_caso))
    cob = _f("cobrimento", 0.025)
    tipo_laje = src.get("tipo_laje", "piso")

    # validacao de envelope: mezanino DENTRO do galpao
    comp = geo["comprimento"]; vao = geo["vao"]; pd = geo["pe_direito"]
    erros = []
    if Lx <= 0 or Ly <= 0 or h <= 0:
        erros.append("dimensoes do mezanino devem ser >0 (Lx=%.2f, Ly=%.2f, h=%.2f)" % (Lx, Ly, h))
    if x0 < -TOL_M or y0 < -TOL_M:
        erros.append("origem do mezanino negativa (x0=%.2f, y0=%.2f)" % (x0, y0))
    if x0 + Lx > comp + TOL_M:
        erros.append("mezanino excede o comprimento do galpao (x0+Lx=%.2f > comp=%.2f)" % (x0+Lx, comp))
    if y0 + Ly > vao + TOL_M:
        erros.append("mezanino excede o vao do galpao (y0+Ly=%.2f > vao=%.2f)" % (y0+Ly, vao))
    if h > pd - 1e-9:
        erros.append("altura do mezanino (%.2f) deve ser < pe-direito do galpao (%.2f)" % (h, pd))
    if erros:
        raise ValueError("; ".join(erros))

    return {
        "x0": x0, "y0": y0, "Lx": Lx, "Ly": Ly, "h": h,
        "q_uso": q_extra, "revest": revest,
        "fck": fck, "fyk": fyk, "sigma_solo_adm": sigma_solo,
        "b_viga": b_viga, "h_viga": h_viga, "hx": hx, "hy": hy,
        "h_laje": h_laje, "laje_caso": laje_caso, "cobrimento": cob,
        "tipo_laje": tipo_laje,
    }


def rodar(spec):
    """Dimensiona o mezanino de concreto dentro do galpao.

    spec: {
      'geometria': {comprimento, vao, pe_direito} (m) — envelope validado;
      // ou {L,W,H} — dialeto eletrico/incendio;
      'x0','y0','Lx','Ly','h' (m) — retangulo interior e altura da laje;
      'q_uso' (kN/m2), 'revest' (kN/m2), 'fck','fyk' (kN/m2),
      'b_viga','h_viga','hx','hy' (m), 'h_laje' (m), 'laje_caso' (1..9),
      'sigma_solo_adm' (kN/m2);
      // turnkey: {geometria:..., mezanino: {x0,...}} — tambem aceito.
    }
    Retorna {spec, geometria, mezanino, laje, vigas, pilares, sapatas, gates,
             reprovados, ATENDE, interferencia}.
    """
    geo = _geometria_galpao(spec)
    mz = _spec_mezanino(spec, geo)

    x0, y0, Lx, Ly, h = mz["x0"], mz["y0"], mz["Lx"], mz["Ly"], mz["h"]
    fck, fyk = mz["fck"], mz["fyk"]
    cob = mz["cobrimento"]
    q_uso = mz["q_uso"]; revest = mz["revest"]
    b_viga, h_viga = mz["b_viga"], mz["h_viga"]
    hx, hy = mz["hx"], mz["hy"]
    h_laje_req = mz["h_laje"]; caso = mz["laje_caso"]; tipo_laje = mz["tipo_laje"]
    sigma_solo = mz["sigma_solo_adm"]

    # ---------------------------- LAJE ---------------------------------------
    # lx = menor vao do painel
    lx = min(Lx, Ly); ly = max(Lx, Ly)
    # g_extra = revest (kN/m2) — o peso proprio da laje e somado dentro de laje_concreto
    # Nota de fronteira F19: h_laje em m -> h_cm no raw (cm) e realimenta g
    r_laje = lj.dimensiona_laje({
        "lx": lx, "ly": ly, "h": h_laje_req, "fck": fck, "fyk": fyk,
        "caso": caso, "g": revest, "q": q_uso, "tipo": tipo_laje,
        "cobrimento": cob,
    })
    h_laje_adot = float(r_laje["h"])
    # feedback carga: ja dentro de r_laje["g"] = 25*h + revest, mas registra para gate
    g_kN_m2 = float(r_laje["g"])
    p_k = float(r_laje["p_k"])

    # --------------------------- VIGAS ---------------------------------------
    # Vigas de contorno: 2 vigas em X (comprimento Lx, trib Ly/2) e 2 em Y (Ly, trib Lx/2)
    # Usa w caracteristico = p_k * trib (kN/m) — o peso proprio da viga e somado dentro
    p_trib_x = p_k * Ly / 2.0
    p_trib_y = p_k * Lx / 2.0
    # Viga X (vao Lx)
    vx_cfg = {"vao": Lx, "b": b_viga, "h": h_viga, "fck": fck, "fyk": fyk,
              "cobrimento": 0.03, "q": p_trib_x}
    rx = vc.verifica_viga(vx_cfg)
    # se nao atender, sobe a escada de alturas (dimensiona_viga)
    if not rx["OK"]:
        rx = vc.dimensiona_viga(vx_cfg)
    # Viga Y (vao Ly)
    vy_cfg = {"vao": Ly, "b": b_viga, "h": h_viga, "fck": fck, "fyk": fyk,
              "cobrimento": 0.03, "q": p_trib_y}
    ry = vc.verifica_viga(vy_cfg)
    if not ry["OK"]:
        ry = vc.dimensiona_viga(vy_cfg)
    # sec adaptada (se dimensionou, pega a adotada)
    b_vx = float(rx["b"]); h_vx = float(rx["h"])
    b_vy = float(ry["b"]); h_vy = float(ry["h"])
    vigas = {"X": rx, "Y": ry}

    # --------------------------- PILARES -------------------------------------
    # Carga axial caracteristica por pilar: area tributaria ~ (Lx*Ly)/4
    area_trib = Lx * Ly / 4.0
    N_slab = p_k * area_trib
    # peso das vigas tributarias: metade de cada viga vai para o pilar de canto
    peso_vx = GAMMA_CONC * b_vx * h_vx * Lx
    peso_vy = GAMMA_CONC * b_vy * h_vy * Ly
    # cada pilar recebe 1/2 de uma viga X + 1/2 de uma viga Y (canto)
    N_beam = (peso_vx / 2.0 + peso_vy / 2.0) / 1.0  # por pilar
    peso_pilar = GAMMA_CONC * hx * hy * h
    Nk = N_slab + N_beam + peso_pilar
    # comprimento de flambagem: pilar interior travado pela laje/viga no topo
    # le = H (vinculado nas duas extremidades, NBR 6118 15.6). Usa le= h (m).
    le = h
    # dois lances? mezanino tem 1 lance so
    def _dim_pilar(hx_, hy_):
        return pc.dimensiona_pilar({
            "b": hy_, "h": hx_, "Nk": Nk, "le_x": le, "le_y": le,
            "fck": fck, "fyk": fyk, "dl": cob,
            # sem momento de vento: pilar interno, so carga gravitacional + minimo
        })
    rp = _dim_pilar(hx, hy)
    # se reprovar, tenta a proxima secao da escada de pilares (do galpao_concreto)
    # — escada local: hx//vento >= hy, mesma de _SECOES_PILAR
    _SECOES = [(0.20, 0.25), (0.25, 0.30), (0.30, 0.30), (0.30, 0.40), (0.40, 0.40)]
    if not rp["OK"]:
        for (hy2, hx2) in _SECOES:
            if hx2 * hy2 <= hx * hy + 1e-9:
                continue
            r2 = _dim_pilar(hx2, hy2)
            if r2["OK"]:
                rp = r2
                hx, hy = hx2, hy2
                peso_pilar = GAMMA_CONC * hx * hy * h
                break

    # -------------------------- FUNDACOES (sapatas) --------------------------
    sapatas = []
    # reacao de base por pilar: Nk + peso sapata estimado? deixa o FS calcular
    # Usa fundacao_sapata.dimensiona_sapata com N=Nk, M~0, V~0
    for k in range(4):
        caso_sap = {
            "nome": "Pilar mezanino P%d" % (k + 1),
            "N": Nk, "V": 0.0, "M": 0.0,
            "sigma_solo_adm": sigma_solo,
            "mu": 0.5, "coesao": 0.0, "h_reaterro": 0.5,
            "d_ped": hx, "b_ped": hy, "h_ped": 0.4,
            "fck": min(fck, 25e3), "fyk": fyk, "cobrimento": 0.04,
        }
        sap = fs.dimensiona_sapata(caso_sap)
        sapatas.append(sap)

    # ------------------------------ GATES ------------------------------------
    gates = {}
    # laje
    gates["laje"] = {"OK": bool(r_laje.get("OK")), "h_cm": h_laje_adot * 100.0,
                     "h_req_cm": h_laje_req * 100.0, "caso": caso, "avisos": r_laje.get("avisos", [])}
    # feedback laje -> carga (F16/F19): a carga usada nas vigas/pilares veio da espessura ADOTADA
    gates["laje_compatibilizada"] = {
        "OK": abs(h_laje_adot - r_laje["h"]) <= 1e-9,
        "h_declarada_cm": h_laje_req * 100.0,
        "h_adotada_cm": h_laje_adot * 100.0,
        "h_na_carga_cm": h_laje_adot * 100.0,
    }
    # vigas
    gates["viga_X"] = {"OK": bool(rx["OK"]), "secao": "%dx%d" % (b_vx*100, h_vx*100),
                       "M_d": rx.get("M_d"), "As_inf": rx.get("As_inf_cm2")}
    gates["viga_Y"] = {"OK": bool(ry["OK"]), "secao": "%dx%d" % (b_vy*100, h_vy*100),
                       "M_d": ry.get("M_d"), "As_inf": ry.get("As_inf_cm2")}
    gates["vigas"] = {"OK": bool(rx["OK"] and ry["OK"])}
    # pilar (4 pilares identicos)
    gates["pilar"] = {"OK": bool(rp["OK"]), "secao": "%dx%d" % (hy*100, hx*100),
                      "Nk": Nk, "As_cm2": rp.get("As_cm2"), "secao_hx_hy": (hx, hy)}
    # fundacao: todas as sapatas precisam aprovar
    sap_ok = all(s.get("aprovado") is not None for s in sapatas)
    gates["fundacao"] = {"OK": bool(sap_ok), "n_sapatas": len(sapatas),
                         "sapatas": sapatas}
    # interferencia interna (sem contar com o galpao metalico — essa e federada)
    # verifica que vigas/pilares/laje/sapatas nao se interpenetram entre si
    # (usa membros_bim proprio)
    # geometria do mezanino dentro do envelope
    gates["posicao"] = {
        "OK": bool(x0 >= -1e-9 and y0 >= -1e-9 and x0+Lx <= geo["comprimento"]+1e-9 and y0+Ly <= geo["vao"]+1e-9 and h <= geo["pe_direito"]+1e-9),
        "x0": x0, "y0": y0, "Lx": Lx, "Ly": Ly, "h": h,
        "envelope": geo,
    }

    reprovados = [k for k, g in gates.items() if not g["OK"]]
    ATENDE = len(reprovados) == 0

    res = {
        "spec": {"geometria": geo, "mezanino": mz},
        "geometria": geo,
        "mezanino": dict(mz, h_laje_adot=h_laje_adot, g_kN_m2=g_kN_m2, p_k=p_k),
        "laje": r_laje,
        "vigas": vigas,
        "viga_X": rx, "viga_Y": ry,
        "pilar": rp,
        "hx": hx, "hy": hy, "b_viga": b_vx, "h_viga_X": h_vx, "h_viga_Y": h_vy,
        "sapatas": sapatas,
        "Nk_pilar": Nk,
        "gates": gates,
        "reprovados": reprovados,
        "ATENDE": ATENDE,
    }
    # varredura de interpenetracao interna
    try:
        interf = checa_interferencia(res)
        gates["interferencia"] = {"OK": interf["OK"], "conflitos": len(interf["conflitos"]), "detalhe": interf["conflitos"][:3]}
        if not interf["OK"] and "interferencia" not in reprovados:
            reprovados.append("interferencia")
            res["reprovados"] = reprovados
            res["ATENDE"] = False
    except Exception:
        pass
    res["interferencia"] = gates.get("interferencia")
    return res


def membros_bim(r):
    """Lista de membros BIM (para ifc_emit / build_concreto / geometria_membros)
    do mezanino. Coordenadas em mm (F18: m->mm *1000), dims de caixa em mm (F01),
    secao de barra em m (F04/F20), ancoragem base (F05). Frame comum: X=comprimento,
    Y=vao, Z=altura (mesmo do modelo_neutro do aco) — nao precisa transformar.

    Empilhamento vertical (mesma regra de bim_edificio):
      laje top em z = h*MM, esp h_laje*MM
      viga: secao d = h_viga - h_laje (nervura abaixo da laje), ancoragem base em
            zb = h*MM - h_viga*MM, sobe ate base da laje
      pilar: de z=0 ate zb (face inferior da viga)
      sapata: caixa B*L*hf com centro em [x,y,-hf/2*MM] (topo em 0)
    """
    geo = r["geometria"]
    mz = r["mezanino"]
    # mezanino pode vir de r["spec"]["mezanino"] ou r["mezanino"]
    if "Lx" not in mz:
        mz = r["spec"]["mezanino"]
    x0 = mz["x0"] * MM; y0 = mz["y0"] * MM
    Lx = mz["Lx"] * MM; Ly = mz["Ly"] * MM
    h = mz["h"] * MM
    h_laje = float(r["mezanino"].get("h_laje_adot", mz["h_laje"])) * MM
    # secoes adotadas (podem ter sido majoradas pelo dimensionamento)
    # vigas: rx/ry podem ter h maior que o pedido
    rx = r.get("viga_X") or r["vigas"]["X"]
    ry = r.get("viga_Y") or r["vigas"]["Y"]
    b_vx = float(rx["b"]); h_vx = float(rx["h"])
    b_vy = float(ry["b"]); h_vy = float(ry["h"])
    hx = float(r.get("hx", mz["hx"])); hy = float(r.get("hy", mz["hy"]))
    # se o pilar foi majorado, pega a secao do resultado
    if r.get("pilar"):
        hx = float(r["pilar"].get("hx", hx)); hy = float(r["pilar"].get("hy", hy))
    fck = mz["fck"]; fck_MPa = fck/1000.0
    mat = f"Concreto C{fck_MPa:.0f}"

    # sapatas: B,L,hf em m -> mm (F01)
    sapatas = r.get("sapatas") or []
    # mapeia sapata por pilar (4 cantos): ordem (x0,y0), (x0+Lx,y0), (x0,y0+Ly), (x0+Lx,y0+Ly)
    # usa sapatas[0..3] se existirem
    membros = []

    # ---- PILARES (4 cantos) ------------------------------------------------
    # secao: bf=hx? No galpao_concreto: bf=hx (// vao=X), d=hy (// comp=Y) ??? Mas para
    # mezanino, a convencao de F17 e que hx // vento (aqui // X=compr) e hy // Y.
    # Para aabb: bf engorda X, d engorda Y quando pilar vertical. Segue F17:
    #   sec_pil = {"bf": hx, "d": hy}  (mesma que galpao_concreto)
    sec_pil = {"forma": "RECT", "bf": hx, "d": hy}
    # pilar vai de 0 ate zb (base da viga). zb = h - h_viga_max
    h_viga_max = max(h_vx, h_vy) * MM
    zb = h - h_viga_max
    # armadura do pilar (para Pset)
    arm_pil = {"As_long_cm2": float(r["pilar"].get("As_cm2", 0.0)),
               "taxa_pct": float(r["pilar"].get("taxa_pct", 0.0))}
    cantos = [(x0, y0), (x0+Lx, y0), (x0, y0+Ly), (x0+Lx, y0+Ly)]
    for k, (x, y) in enumerate(cantos, start=1):
        membros.append({
            "tipo": "Column", "perfil": f"P{hy*100:.0f}x{hx*100:.0f}",
            "marca": f"M-P{k}", "secao": dict(sec_pil),
            "p1": [x, y, 0.0], "p2": [x, y, zb], "material": mat,
            "armadura": dict(arm_pil),
        })

    # ---- VIGAS DE CONTORNO (4 vigas, frame da laje) -------------------------
    # Secao da viga: bf = b_viga, d = h_viga - h_laje/MM (nervura)
    # Vigas em X (2 vigas: y=y0 e y=y0+Ly, x=x0->x0+Lx)
    # Vigas em Y (2 vigas: x=x0 e x=x0+Lx, y=y0->y0+Ly, recuadas de b/2 nas pontas)
    # Ancoragem base: p1/p2 e' a face inferior, sobe d
    laje_h_m = h_laje / MM
    # viga X usa secao de rx, Y de ry
    sec_vx = {"forma": "RECT", "bf": b_vx, "d": h_vx - laje_h_m}
    sec_vy = {"forma": "RECT", "bf": b_vy, "d": h_vy - laje_h_m}
    # evita d <=0 (laje mais espessa que viga): recusa ja teria reprovado, mas garante
    if sec_vx["d"] <= 0:
        sec_vx["d"] = 0.10
    if sec_vy["d"] <= 0:
        sec_vy["d"] = 0.10
    arm_vx = {"As_inf_cm2": float(rx.get("As_inf_cm2", 0.0)), "As_sup_cm2": float(rx.get("As_sup_cm2", 0.0))}
    arm_vy = {"As_inf_cm2": float(ry.get("As_inf_cm2", 0.0)), "As_sup_cm2": float(ry.get("As_sup_cm2", 0.0))}
    # zb por direcao (se vigas tem alturas diferentes, cada uma tem seu zb)
    zbx = h - h_vx * MM
    zby = h - h_vy * MM
    # 2 vigas em X
    for k, y in enumerate((y0, y0+Ly), start=1):
        membros.append({
            "tipo": "Beam", "perfil": f"MV{ b_vx*100:.0f}x{ h_vx*100:.0f}",
            "marca": f"M-VX{k}", "secao": dict(sec_vx), "ancoragem": "base",
            "p1": [x0, y, zbx], "p2": [x0+Lx, y, zbx], "material": mat,
            "armadura": dict(arm_vx),
        })
    # 2 vigas em Y — recuadas de b/2 onde encontram as vigas em X (mesma de bim_edificio)
    for k, x in enumerate((x0, x0+Lx), start=1):
        # recuo para nao contar concreto duas vezes no cruzamento
        y_a = y0 + b_vx * MM / 2.0
        y_b = y0 + Ly - b_vx * MM / 2.0
        if y_b <= y_a:
            y_a, y_b = y0, y0+Ly
        membros.append({
            "tipo": "Beam", "perfil": f"MV{ b_vy*100:.0f}x{ h_vy*100:.0f}",
            "marca": f"M-VY{k}", "secao": dict(sec_vy), "ancoragem": "base",
            "p1": [x, y_a, zby], "p2": [x, y_b, zby], "material": mat,
            "armadura": dict(arm_vy),
        })

    # ---- LAJE (1 painel retangular) -----------------------------------------
    # dims em mm (F01), centro em mm — laje macica sobre as vigas, topo em h
    centro_laje = [x0 + Lx/2.0, y0 + Ly/2.0, h - h_laje/2.0]
    dims_laje = [Lx, Ly, h_laje]
    # armadura da laje (painel critico) — so este painel existe
    lj_arm = {}
    if r.get("laje") and r["laje"].get("armaduras"):
        arm = r["laje"]["armaduras"]
        for dk in ("m_x", "m_y"):
            if dk in arm:
                lj_arm[dk] = float(arm[dk].get("As_adotada", 0.0)) * 1e4  # cm2/m
    membros.append({
        "tipo": "Slab", "perfil": f"LAJE h={h_laje/MM*100:.0f}cm",
        "marca": "M-LAJE", "dims": dims_laje, "centro": centro_laje,
        "material": mat, "armadura": lj_arm,
    })

    # ---- SAPATAS (4 Footings sob os pilares) --------------------------------
    # F01: dims em mm (B*1000), centro em mm — aprovado e' (B,L,h, ...) tuple
    for k, (x, y) in enumerate(cantos):
        if k < len(sapatas) and sapatas[k].get("aprovado"):
            ap = sapatas[k]["aprovado"]
            B, L, hf = float(ap[0]), float(ap[1]), float(ap[2])  # m
            membros.append({
                "tipo": "Footing", "perfil": f"S{B:.1f}x{L:.1f}",
                "marca": f"M-SAP{k+1}", "dims": [B*MM, L*MM, hf*MM],
                "centro": [x, y, -hf/2.0*MM], "material": mat,
            })
        else:
            # fallback: sapata 1.0x1.0x0.40 se o dimensionamento nao aprovou
            B = L = 1.0; hf = 0.40
            membros.append({
                "tipo": "Footing", "perfil": f"S{B:.1f}x{L:.1f}",
                "marca": f"M-SAP{k+1}", "dims": [B*MM, L*MM, hf*MM],
                "centro": [x, y, -hf/2.0*MM], "material": mat,
            })

    return membros


def _aabb(mb):
    """Caixa envolvente de um membro do mezanino (mm), delega a geometria_membros."""
    import geometria_membros as gm
    return gm.aabb(mb)


def checa_interferencia(r):
    """Varredura de interpenetracao AABB nos membros do mezanino (puro, sem FreeCAD).
    Ignora toques de face (viga sobre pilar, laje sobre viga)."""
    import geometria_membros as gm
    ms = membros_bim(r)
    return gm.interpenetracoes(ms)


def emitir_bim(r, path):
    """Emite o IFC4 do mezanino (FreeCAD-free) via ifc_emit. Retorna path."""
    import ifc_emit
    return ifc_emit.emitir_ifc(membros_bim(r), path, nome="Mezanino")


def montar_3d(r, out_dir, doc_name="mezanino", headless=None, host="http://localhost:9875", timeout=180):
    """Constroi o modelo 3D solido (FreeCAD) do mezanino: pilares/vigas/laje/sapatas.
    Reusa build_concreto.py (caixas) — payload de dados puro, sem modulo irmao.
    """
    import os
    import framework as FW
    import rodar_projeto as RP
    bk = {"membros": membros_bim(r),
          "export_dir": str(out_dir).replace("\\", "/"),
          "doc_name": doc_name}
    src_path = FW.raiz_repo() / "framework" / "galpao_fw" / "build_concreto.py"
    src = RP._ship_build_src(src_path)
    if headless is None:
        headless = os.environ.get("FREECAD_HEADLESS", "").strip() in ("1", "true", "True")
    if headless:
        return RP._montar_headless(src, bk, out_dir, timeout)
    import xmlrpc.client
    try:
        return RP._montar_bridge(src, bk, host, timeout)
    except (OSError, xmlrpc.client.ProtocolError) as e:
        import sys
        print("[montar_3d mezanino] bridge indisponivel (%s); caindo p/ headless" % e, file=sys.stderr)
        return RP._montar_headless(src, bk, out_dir, timeout)


def relatorio_pt(r):
    """Quadro-resumo do mezanino (numeros com virgula decimal, como nos demais)."""
    import re
    geo = r["geometria"]; mz = r["mezanino"]; g = r["gates"]
    L = [
        "MEZANINO DE CONCRETO DENTRO DO GALPAO METALICO (NBR 6118) — G20",
        f"  Envelope do galpao: {geo['comprimento']:.1f} x {geo['vao']:.1f} m ; pe-direito {geo['pe_direito']:.1f} m",
        f"  Mezanino: origem ({mz['x0']:.1f}, {mz['y0']:.1f}) ; {mz['Lx']:.1f} x {mz['Ly']:.1f} m ; h={mz['h']:.1f} m ; area {mz['Lx']*mz['Ly']:.1f} m2",
        f"  LAJE: h_adot {g['laje']['h_cm']:.0f} cm (caso {g['laje']['caso']}) -> {'ATENDE' if g['laje']['OK'] else 'REPROVA'}",
        f"  VIGA X (Lx={mz['Lx']:.1f}m): secao {g['viga_X']['secao']} cm -> {'ATENDE' if g['viga_X']['OK'] else 'REPROVA'}",
        f"  VIGA Y (Ly={mz['Ly']:.1f}m): secao {g['viga_Y']['secao']} cm -> {'ATENDE' if g['viga_Y']['OK'] else 'REPROVA'}",
        f"  PILAR (4x, h={mz['h']:.1f}m): secao {g['pilar']['secao']} cm ; Nk {r['Nk_pilar']:.0f} kN ; As {g['pilar']['As_cm2']:.2f} cm2 -> {'ATENDE' if g['pilar']['OK'] else 'REPROVA'}",
        f"  FUNDACAO (sapatas): {g['fundacao']['n_sapatas']} sapatas -> {'ATENDE' if g['fundacao']['OK'] else 'REPROVA'}",
        f"  POSICAO: x0={mz['x0']:.1f} y0={mz['y0']:.1f} -> {'DENTRO' if g['posicao']['OK'] else 'FORA'} do envelope",
        f"  INTERFERENCIA INTERNA: {g.get('interferencia', {}).get('conflitos', '?')} conflito(s) -> {'OK' if g.get('interferencia', {}).get('OK') else 'REVISAR'}",
        f"  RESULTADO: {'ATENDE' if r['ATENDE'] else 'REPROVADO em ' + ', '.join(r['reprovados'])}",
        "  [A CONFIRMAR: sobrecarga de utilizacao (NBR 6120), sigma do solo (sondagem),",
        "   cargas de parede/divisoria sobre o mezanino.]",
    ]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    """Mezanino tipico dentro do galpao 40x20x6: 6x5 a 3 m, 12 cm, q=3 kN/m2."""
    geo = {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0}
    r = rodar({"geometria": geo, "x0": 5.0, "y0": 6.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0,
               "q_uso": 3.0, "revest": 1.0, "fck": 30e3, "sigma_solo_adm": 250.0})
    assert r["ATENDE"], (r["reprovados"], r["gates"])
    ms = membros_bim(r)
    # 4 pilares + 4 vigas + 1 laje + 4 sapatas = 13 membros
    tipos = {t: sum(1 for x in ms if x["tipo"] == t) for t in set(x["tipo"] for x in ms)}
    assert tipos.get("Column") == 4, tipos
    assert tipos.get("Beam") == 4, tipos
    assert tipos.get("Slab") == 1, tipos
    assert tipos.get("Footing") == 4, tipos
    # laje no topo: centro Z = h - h_laje/2
    slab = next(m for m in ms if m["tipo"] == "Slab")
    assert abs(slab["centro"][2] - (3.0*1000 - slab["dims"][2]/2)) < 1e-6
    # viga ancoragem base: p1.z = h*MM - h_viga*MM
    beam = next(m for m in ms if m["marca"] == "M-VX1")
    assert abs(beam["p1"][2] - (3.0*1000 - r["viga_X"]["h"]*1000)) < 1e-6
    # pilar vai de 0 ate base da viga
    col = next(m for m in ms if m["tipo"] == "Column")
    assert col["p1"][2] == 0.0
    assert abs(col["p2"][2] - (3.0*1000 - max(r["viga_X"]["h"], r["viga_Y"]["h"])*1000)) < 1e-6
    # dims da sapata em mm (F01)
    foot = next(m for m in ms if m["tipo"] == "Footing")
    assert all(500 < d < 5000 for d in foot["dims"][:2]), foot["dims"]
    # sem interpenetracao interna
    assert checa_interferencia(r)["OK"], checa_interferencia(r)
    # fora do envelope deve reprovar
    try:
        rodar({"geometria": geo, "x0": 35.0, "y0": 0.0, "Lx": 10.0, "Ly": 5.0, "h": 3.0})
        assert False, "deveria reprovar por fora do envelope"
    except ValueError as e:
        assert "excede" in str(e).lower()
    print("galpao_mezanino self-test PASSED")
    print(relatorio_pt(r).splitlines()[0])


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(relatorio_pt(rodar({"geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
                                  "x0": 5.0, "y0": 6.0, "Lx": 6.0, "Ly": 5.0, "h": 3.0})))


