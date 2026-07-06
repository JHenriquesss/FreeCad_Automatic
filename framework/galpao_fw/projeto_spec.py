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
]


def novo():
    """Template de spec: tudo PENDENTE. A skill preenche gate a gate."""
    return {
        "slug": P, "descricao": P,
        "terreno": {"kml": P, "area_lote_m2": P, "to_max": P, "ca_max": P,
                    "tp_min": P, "recuos": P, "n_pav": 1, "pts_xy_mm": None},
        "geometria": {"span": P, "comprimento": P, "eave": P, "ridge": P,
                      "bay": P, "base_fixed": P},
        "cobertura": {"aguas": P, "slope": P, "telha_tipo": P, "telha_peso": P,
                      "calha": P},
        "fechamento": {"tipo": P, "altura_alvenaria": None, "peso": P},
        "aberturas": P,     # dict {portao_frente, portao_fundo, porta_*, janelas_*}
        "estrutura": {"perfil_col": P, "perfil_raf": P, "contraventamento": P},
        "vento": {"v0": P, "cat": P, "classe": P, "s1": 1.0, "s3": P, "z": P,
                  "abertura_dominante": P},
        "ponte": P,         # None (sem ponte) ou dict de dados
        "cargas": {"G": P, "Q": P, "self": P, "tapamento": P},
        "_a_confirmar": [],  # paths com valor provisorio (confirmar depois)
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
    p["ponte"] = spec["ponte"] if spec["ponte"] else None
    if spec["ponte"]:
        import ponte_rolante as pr
        p["ponte"].setdefault("perfil_viga", pr.VS500)
        p["ponte"].setdefault("fy", 250e3)
        p["ponte"].setdefault("E_Ix", pr.ck.E * pr.VS500["Ix"])
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
    r = validar(s)
    print(resumo_pt(s))
    assert r["ok"], r["faltando"]
    # remover um obrigatorio volta a bloquear
    s["geometria"]["bay"] = PENDENTE
    assert validar(s)["ok"] is False
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
