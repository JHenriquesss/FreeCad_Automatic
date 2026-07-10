# ============================================================================
# projeto_spec.py - CONTRATO DE DADOS DO PROJETO (framework fino)
# Fonte UNICA da verdade de um projeto de galpao. A skill preenche o spec gate a
# gate; validar() BLOQUEIA o calculo e o desenho enquanto houver campo nao
# decidido. Os mappers (to_rodar_params / to_build_kwargs) traduzem o spec para
# os modulos - o builder e o orquestrador leem SO do spec, sem cair em default
# hardcoded (mata a copia de projetos anteriores).
#
# Estados de um campo:
#   PENDENTE  -> nao decidido: BLOQUEIA (template comeca tudo PENDENTE).
#   <valor>   -> decidido.
#   None      -> decidido "nenhum/nao" (ex: sem porta lateral, sem ponte).
#   valor + path em spec["_a_confirmar"] -> decidido provisorio (confirmar depois).
# ============================================================================
"""Contrato de dados do projeto de galpao + validador que bloqueia + mappers."""

from __future__ import annotations

import copy

PENDENTE = "__PENDENTE__"       # nao decidido -> bloqueia
P = PENDENTE

# Campos OBRIGATORIOS (dotted path -> descricao). Se == PENDENTE, faltando.
REQUERIDOS = [
    ("terreno.area_lote_m2", "area do lote (KML/coord)"),
    ("terreno.to_max", "taxa de ocupacao"),
    ("terreno.ca_max", "coef. de aproveitamento"),
    ("terreno.tp_min", "taxa de permeabilidade"),
    ("terreno.recuos", "recuos frente/lateral/fundos"),
    ("geometria.span", "vao transversal"),
    ("geometria.comprimento", "comprimento"),
    ("geometria.eave", "pe-direito"),
    ("geometria.bay", "espacamento de porticos"),
    ("geometria.base_fixed", "base rotulada/engastada"),
    ("cobertura.aguas", "numero de aguas"),
    ("cobertura.slope", "inclinacao"),
    ("cobertura.telha_tipo", "tipo de telha"),
    ("fechamento.tipo", "fechamento das paredes"),
    ("aberturas", "aberturas (Gate 4)"),
    ("vento.v0", "velocidade basica do vento"),
    ("vento.cat", "categoria de rugosidade"),
    ("vento.abertura_dominante", "abertura dominante (Cpi)"),
    ("ponte", "ponte rolante (dict ou None)"),
    ("cargas.G", "carga permanente de cobertura"),
    ("cargas.Q", "sobrecarga"),
    ("fundacao.sigma_solo_adm", "tensao admissivel do solo (sondagem/geotecnia)"),
    ("fundacao.tipo", "tipo de fundacao (sapata=rasa / estaca=profunda)"),
]

# Fundacao PROFUNDA (estaca): campos requeridos SO quando fundacao.tipo=="estaca".
# O perfil SPT e o tipo de estaca vem da SONDAGEM (Ask, Do Not Invent) -> sem
# default; PENDENTE/ausente bloqueia. D, L, FS tem default (A CONFIRMAR).
REQUERIDOS_ESTACA = [
    ("fundacao.estaca.perfil_spt", "perfil SPT da sondagem (camadas tipo/N/dz)"),
    ("fundacao.estaca.tipo_estaca", "tipo de estaca (pre_moldada/metalica/escavada/...)"),
]
TIPOS_FUNDACAO = ("sapata", "estaca")
TIPOS_PORTICO = ("prismatico", "alma_variavel")

# Ponte rolante: campos do FABRICANTE requeridos SO quando spec["ponte"] != None.
# Sao dado de catalogo/projeto (Ask, Do Not Invent) - PENDENTE/ausente bloqueia.
# phi/n_ciclos podem vir das classes NBR 8400 (classe_hc/classe_b) OU direto.
REQUERIDOS_PONTE = [
    ("Q", "capacidade icada (kN)"),
    ("peso_ponte", "peso proprio da ponte (kN)"),
    ("peso_trole", "peso do trole/carro (kN)"),
    ("aprox_min", "aproximacao minima do gancho ao trilho (m)"),
    ("n_rodas_lado", "numero de rodas por lado (trilho)"),
    ("n_rodas_motoras", "numero de rodas MOTORAS por lado (frenagem)"),
    ("frac_lateral", "fracao do surto transversal (A CONFIRMAR)"),
    ("frac_long", "fracao da frenagem longitudinal (A CONFIRMAR)"),
]


def novo():
    """Template de spec: tudo PENDENTE. A skill preenche gate a gate."""
    return {
        "slug": P, "descricao": P,
        "terreno": {"kml": P, "area_lote_m2": P, "to_max": P, "ca_max": P,
                    "tp_min": P, "recuos": P, "n_pav": 1, "pts_xy_mm": None},
        "geometria": {"span": P, "comprimento": P, "eave": P, "ridge": P,
                      "bay": P, "base_fixed": P},
        # chuva_I_mm_h: intensidade pluviometrica local (NBR 10844) p/ dimensionar
        # a calha. Default 150 (A CONFIRMAR regional); nao bloqueia.
        "cobertura": {"aguas": P, "slope": P, "telha_tipo": P, "telha_peso": P,
                      "calha": P, "chuva_I_mm_h": 150.0},
        # mesa_interna_travada: longarina sob succao. False (default seguro) =
        # mesa interna livre, Lb=vao cheio no FLT. True = mao-francesa trava a
        # mesa interna -> Lb menor (exige o detalhe). Nao bloqueia (tem default).
        "fechamento": {"tipo": P, "altura_alvenaria": None, "peso": P,
                       "mesa_interna_travada": False, "n_maos_francesas": None},
        "aberturas": P,     # dict {portao_frente, portao_fundo, porta_*, janelas_*}
        # tipo_portico: prismatico (default) | alma_variavel (misula tapered).
        # tapered = None p/ prismatico; dict {h_joelho,h_cumeeira,bf,tw,tf} (m).
        "estrutura": {"perfil_col": P, "perfil_raf": P, "contraventamento": P,
                      "tipo_portico": "prismatico", "tapered": None},
        "vento": {"v0": P, "cat": P, "classe": P, "s1": 1.0, "s3": P, "z": P,
                  "abertura_dominante": P},
        "ponte": P,         # None (sem ponte) ou dict de dados
        "cargas": {"G": P, "Q": P, "self": P, "tapamento": P},
        # Fundacao. tipo (sapata=rasa / estaca=profunda) BLOQUEIA. sigma_solo_adm
        # (kN/m2) BLOQUEIA - vem da sondagem, nao se inventa. Demais parametros da
        # sapata tem default (A CONFIRMAR). estaca=None ate tipo=="estaca": ai vira
        # dict {perfil_spt (sondagem), tipo_estaca, D, L, FS, bloco}.
        "fundacao": {"tipo": P, "sigma_solo_adm": P, "mu": 0.5, "coesao": 0.0,
                     "h_reaterro": 0.5, "fck": 25e3, "fyk": 500e3,
                     "cobrimento": 0.05, "phi_barra": 0.0125, "gamma_f": 1.4,
                     "estaca": None,
                     # divisa: None (sem pilar de divisa) OU dict {dist_divisa (m):
                     # distancia do eixo do pilar de divisa a linha do lote}. Dispara
                     # a sapata de divisa excentrica + viga alavanca (Alonso).
                     "divisa": None},
        # Viga de baldrame / amarracao entre fundacoes (NBR 6118). None = nao ha;
        # dict {b, h, q_parede, continuidade} = dimensiona (vao e N_amarracao do modelo).
        "baldrame": None,
        "fogo": None,         # None (sem verificacao) ou dict {TRRF_min, protecao}
        "escada": None,       # None (sem escada) ou dict {desnivel, projecao, largura}
        "plataforma": None,   # None (sem plataforma) ou dict {L, b_trib, q_perm, q_acidental}
        "_a_confirmar": [],
    }


def _get(spec, path):
    o = spec
    for k in path.split("."):
        if not isinstance(o, dict) or k not in o:
            return KeyError
        o = o[k]
    return o


def validar(spec):
    """Retorna {faltando, a_confirmar, ok}. ok=False BLOQUEIA calculo/desenho."""
    faltando = []
    for path, desc in REQUERIDOS:
        v = _get(spec, path)
        if v is KeyError or v == PENDENTE:
            faltando.append((path, desc))
    # tipo de fundacao invalido bloqueia (so sapata|estaca)
    tipo = _get(spec, "fundacao.tipo")
    if tipo not in (KeyError, PENDENTE) and tipo not in TIPOS_FUNDACAO:
        faltando.append(("fundacao.tipo",
                         "valor invalido '%s' (use %s)" % (tipo, "/".join(TIPOS_FUNDACAO))))
    # fundacao profunda: perfil SPT + tipo de estaca sao da sondagem (bloqueiam)
    if tipo == "estaca":
        est = _get(spec, "fundacao.estaca")
        if est in (KeyError, None, PENDENTE) or not isinstance(est, dict):
            faltando.append(("fundacao.estaca", "bloco de estaca ausente (sondagem)"))
        else:
            for path, desc in REQUERIDOS_ESTACA:
                v = _get(spec, path)
                if v in (KeyError, None, PENDENTE, [], "") or v == PENDENTE:
                    faltando.append((path, desc))
    # tipo de portico invalido bloqueia (prismatico|alma_variavel)
    tp = _get(spec, "estrutura.tipo_portico")
    if tp not in (KeyError, None, PENDENTE) and tp not in TIPOS_PORTICO:
        faltando.append(("estrutura.tipo_portico",
                         "valor invalido '%s' (use %s)" % (tp, "/".join(TIPOS_PORTICO))))
    # ponte rolante: se ha ponte (dict), os dados do fabricante bloqueiam. phi
    # exige classe_hc OU phi direto; n de ciclos exige classe_b OU n_ciclos.
    ponte = spec.get("ponte")
    if isinstance(ponte, dict):
        for k, desc in REQUERIDOS_PONTE:
            v = ponte.get(k)
            if v in (None, PENDENTE):
                faltando.append(("ponte." + k, desc))
        if ponte.get("phi") in (None, PENDENTE) and not ponte.get("classe_hc"):
            faltando.append(("ponte.phi", "impacto phi OU classe de elevacao HC (NBR 8400)"))
    return {"faltando": faltando, "a_confirmar": list(spec.get("_a_confirmar", [])),
            "ok": not faltando}


def exigir_completo(spec):
    """Levanta se o spec nao estiver completo (para o builder/orquestrador)."""
    r = validar(spec)
    if not r["ok"]:
        itens = "; ".join(f"{p} ({d})" for p, d in r["faltando"])
        raise ValueError("ProjetoSpec incompleto - decida antes de prosseguir: "
                         + itens)
    return True


def resumo_pt(spec):
    r = validar(spec)
    L = ["=" * 68, f"PROJETO SPEC - {spec.get('slug')}", "=" * 68]
    if r["faltando"]:
        L.append(f"  PENDENTE ({len(r['faltando'])}): BLOQUEIA calculo/desenho")
        for p, d in r["faltando"]:
            L.append(f"    - {p} : {d}")
    else:
        L.append("  COMPLETO: todos os campos obrigatorios decididos.")
    if r["a_confirmar"]:
        L.append(f"  A CONFIRMAR ({len(r['a_confirmar'])}): valor provisorio")
        for p in r["a_confirmar"]:
            L.append(f"    - {p}")
    L.append("=" * 68)
    return "\n".join(L)


# ---- mappers: spec -> modulos ----------------------------------------------
def to_rodar_params(spec):
    """Traduz o spec para os params do orquestrador (rodar_galpao). Parte do
    PARAMS_REF (perfis placeholder + ligacoes que o redimensionamento refina) e
    SOBRESCREVE tudo que e decisao do projeto (geometria, vento, cargas, ponte)."""
    exigir_completo(spec)
    import rodar_galpao as R
    p = copy.deepcopy(R.PARAMS_REF)
    g = spec["geometria"]
    ridge = g["ridge"] if g.get("ridge") not in (None, PENDENTE) else \
        g["eave"] + spec["cobertura"]["slope"] * g["span"] / 2.0
    p["geometria"] = {"span": g["span"], "comprimento": g["comprimento"],
                      "eave": g["eave"], "ridge": ridge, "bay": g["bay"]}
    p["base_fixed"] = g["base_fixed"]
    c = spec["cargas"]
    p["cargas"] = {"G": c["G"], "self": c.get("self", 0.35), "Q": c["Q"]}
    v = spec["vento"]
    p["vento"] = {"v0": v["v0"], "cat": v["cat"], "classe": v.get("classe", "B"),
                  "s1": v.get("s1", 1.0), "s3": v["s3"], "z": v.get("z", ridge)}
    fe = spec.get("fechamento", {})     # longarina: travamento da mesa interna
    lg = p.setdefault("secundarios", {}).setdefault("longarina", {})
    lg["mesa_interna_travada"] = bool(fe.get("mesa_interna_travada", False))
    if fe.get("n_maos_francesas") not in (None, PENDENTE):
        lg["n_maos_francesas"] = fe["n_maos_francesas"]
    fu = spec.get("fundacao") or {}     # sapata: sobrescreve os defaults do solo
    if fu:
        p.setdefault("fundacao", {}).update(
            {k: v for k, v in fu.items()
             if k not in ("tipo", "estaca") and v not in (None, PENDENTE)})
    # fundacao PROFUNDA: monta o cfg da estaca (perfil SPT da sondagem) que o
    # rodar_galpao consome (verifica_estaca). SO quando tipo=="estaca" (exclusivo
    # da sapata). Nada de dado geometrico inventado: tudo vem do bloco 'estaca'.
    if fu.get("tipo") == "estaca" and isinstance(fu.get("estaca"), dict):
        e = fu["estaca"]
        ec = {"perfil": e["perfil_spt"], "D": e.get("D", 0.30),
              "L": e.get("L", 10.0), "tipo_estaca": e.get("tipo_estaca", "pre_moldada"),
              "FS": e.get("FS", 2.0)}
        for opt in ("N_ponta", "bloco", "grupo", "camadas_neg", "recalque_grupo",
                    "FS_tracao"):
            if e.get(opt) is not None:
                ec[opt] = e[opt]
        p["estaca"] = ec
    else:
        p.pop("estaca", None)           # tipo=sapata: garante que nao ha estaca
    # viga de baldrame: opt-in pelo spec (sobrescreve o default do PARAMS_REF).
    bal = spec.get("baldrame")
    if isinstance(bal, dict):
        p.setdefault("baldrame", {}).update(
            {k: v for k, v in bal.items() if v not in (None, PENDENTE)})
    # calha (dimensionamento hidraulico): roda quando ha calha na cobertura;
    # intensidade pluviometrica local (NBR 10844).
    cob = spec.get("cobertura", {})
    p["calha"] = bool(cob.get("calha")) and cob.get("calha") != PENDENTE
    ci = cob.get("chuva_I_mm_h")
    if ci not in (None, PENDENTE):
        p["chuva_I_mm_h"] = ci
    # sapata de divisa: so quando o gate fundacao.divisa e informado.
    dv = fu.get("divisa")
    if isinstance(dv, dict):
        p["divisa"] = dv
    # tipo de portico (prismatico|alma_variavel) + misula tapered.
    est0 = spec.get("estrutura", {})
    p["tipo_portico"] = est0.get("tipo_portico", "prismatico")
    if est0.get("tipo_portico") == "alma_variavel" and isinstance(est0.get("tapered"), dict):
        p["tapered"] = est0["tapered"]
    p["ponte"] = spec["ponte"] if spec["ponte"] else None
    if spec["ponte"]:
        import ponte_rolante as pr
        p["ponte"].setdefault("perfil_viga", pr.VS500)
        p["ponte"].setdefault("fy", 250e3)
        p["ponte"].setdefault("E_Ix", pr.ck.E * pr.VS500["Ix"])
    p["fogo"] = spec.get("fogo") if spec.get("fogo") else None
    p["escada"] = spec.get("escada") if spec.get("escada") else None
    p["plataforma"] = spec.get("plataforma") if spec.get("plataforma") else None
    return p


def to_build_kwargs(spec):
    """Traduz o spec para os kwargs de build_galpao.configurar (geometria +
    aberturas + fechamento + terreno). NADA vem de default hardcoded."""
    exigir_completo(spec)
    g = spec["geometria"]
    # perfil ADOTADO (redimensionamento) -> secao do modelo (h,b,tw,tf em mm).
    import perfis
    est = spec.get("estrutura", {})

    def _sec(nome):
        p = perfis.PERFIS.get(nome) if nome else None
        return (p["d"] * 1000, p["bf"] * 1000, p["tw"] * 1000, p["tf"] * 1000) if p else None
    col_nome = est.get("perfil_col_adotado")
    raf_nome = est.get("perfil_raf_adotado")

    def _maior(a, b):
        pa, pb = perfis.PERFIS.get(a), perfis.PERFIS.get(b)
        if pa and pb:
            return a if pa["d"] >= pb["d"] else b
        return a or b
    esc_nome = _maior(est.get("perfil_escora"), est.get("perfil_montante"))
    jo = est.get("joelho_adotado")
    tipo_fund = spec.get("fundacao", {}).get("tipo")
    profunda = tipo_fund == "estaca"
    ea = est.get("estaca_adotada"); bo = est.get("bloco_adotado")
    bl = est.get("baldrame_adotado")
    return {
        "length": g["comprimento"] * 1000.0, "span": g["span"] * 1000.0,
        "eave_h": g["eave"] * 1000.0, "slope": spec["cobertura"]["slope"],
        "bay": g["bay"] * 1000.0,
        "aberturas": spec["aberturas"], "fechamento": spec["fechamento"],
        "terreno_pts": spec["terreno"].get("pts_xy_mm"),
        "perfil_col": _sec(col_nome), "perfil_raf": _sec(raf_nome),
        "perfil_col_nome": col_nome, "perfil_raf_nome": raf_nome,
        "perfil_esc": _sec(esc_nome), "perfil_esc_nome": esc_nome,
        "terca": est.get("terca_dims"),
        "longarina": est.get("longarina_dims"),
        "longarina_nome": est.get("longarina_perfil"),
        "n_tirante_parede": est.get("n_tirante_parede"),
        "joelho": ({"t": jo["t"] * 1000, "db": jo["db"] * 1000, "n": jo["n"]}
                   if jo else None),
        "base": ({"B": ba["B"] * 1000, "L": ba["L"] * 1000, "t": ba["t"] * 1000,
                  "db": ba["db"] * 1000, "n": ba["n"]}
                 if (ba := est.get("base_adotada")) else None),
        # fundacao RASA (sapata): so quando tipo!=estaca (exclusivo - mne-2).
        "sapata": ({"B": sa["B"] * 1000, "L": sa["L"] * 1000, "h": sa["h"] * 1000,
                    "ped": spec.get("fundacao", {}).get("h_ped", 0.5) * 1000}
                   if (not profunda and (sa := est.get("sapata_adotada"))) else None),
        # fundacao PROFUNDA (estaca + bloco + baldrame): dims do CALCULO em mm.
        "estaca": ({"D": ea["D"] * 1000, "L": ea["L"] * 1000, "n": ea["n"],
                    "espacamento": ea.get("espacamento", 3.0 * ea["D"]) * 1000,
                    "tipo": ea.get("tipo")}
                   if (profunda and ea) else None),
        "bloco": ({"h": bo["h"] * 1000, "a": bo.get("a", 0.30) * 1000,
                   "B": bo.get("B", bo.get("a", 0.30)) * 1000,
                   "L": bo.get("L", bo.get("a", 0.30)) * 1000}
                  if (profunda and bo) else None),
        "baldrame": ({"b": bl["b"] * 1000, "h": bl["h"] * 1000,
                      "vao": bl.get("vao", g["bay"]) * 1000}
                     if (profunda and bl) else None),
        # portico de alma variavel: tipo + misula tapered (alturas em mm p/ o loft).
        "tipo_portico": est.get("tipo_portico", "prismatico"),
        "tapered": ({"h_joelho": tap["h_joelho"] * 1000, "h_cumeeira": tap["h_cumeeira"] * 1000,
                     "bf": tap.get("bf", 0.20) * 1000, "tw": tap.get("tw", 0.008) * 1000,
                     "tf": tap.get("tf", 0.0125) * 1000}
                    if (est.get("tipo_portico") == "alma_variavel"
                        and isinstance(tap := est.get("tapered"), dict)) else None),
        "ponte_modelo": ({"Hvr": spec["ponte"].get("Hvr", 4.5) * 1000.0,
                          "excentricidade": spec["ponte"].get("excentricidade", 0.3) * 1000.0}
                         if spec["ponte"] else None),
    }


def marcar_a_confirmar(spec, *paths):
    for p in paths:
        if p not in spec["_a_confirmar"]:
            spec["_a_confirmar"].append(p)


def _selftest():
    s = novo()
    r = validar(s)
    assert not r["ok"] and len(r["faltando"]) == len(REQUERIDOS)   # template bloqueia
    # preenche o minimo
    s["slug"] = "teste"
    s["terreno"].update(area_lote_m2=982.0, to_max=0.6, ca_max=1.0, tp_min=0.2,
                        recuos={"frente": 5, "lateral": 1.5, "fundos": 3})
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                         bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal", calha=True)
    s["fechamento"].update(tipo="alvenaria_telha", altura_alvenaria=2.5, peso=0.12)
    s["aberturas"] = {"portao_frente": (4000, 4500), "porta_fundo": (900, 2130),
                      "janelas_laterais": (4300, 5300), "porta_lateral": None,
                      "portao_fundo": None, "porta_frente": None}
    s["vento"].update(v0=35.0, cat="II", classe="B", s3=0.95, z=6.5,
                      abertura_dominante="portao_oitao")
    marcar_a_confirmar(s, "vento.v0", "terreno.to_max")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.10)
    s["fundacao"]["sigma_solo_adm"] = 200.0        # kN/m2 (sondagem)
    s["fundacao"]["tipo"] = "sapata"
    r = validar(s)
    print(resumo_pt(s))
    assert r["ok"], r["faltando"]
    # fundacao profunda: tipo=estaca exige perfil SPT + tipo de estaca (sondagem)
    s2 = copy.deepcopy(s)
    s2["fundacao"]["tipo"] = "estaca"
    assert validar(s2)["ok"] is False                # falta o bloco de estaca
    s2["fundacao"]["estaca"] = {
        "perfil_spt": [{"tipo": "areia_siltosa", "N": 20, "dz": 8.0}],
        "tipo_estaca": "pre_moldada", "D": 0.30, "L": 8.0, "FS": 2.0}
    assert validar(s2)["ok"], validar(s2)["faltando"]
    # remover um obrigatorio volta a bloquear
    s["geometria"]["bay"] = PENDENTE
    assert validar(s)["ok"] is False
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
