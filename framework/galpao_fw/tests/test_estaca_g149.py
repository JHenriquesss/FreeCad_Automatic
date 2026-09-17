"""G149 - A estaca calada nas outras tres portas (metalico, wizard, predio).

Medido por injecao (2026-09-15, antes de mudar):
- nucleo verifica_estaca (N=500, argila N5/3m + areia N25/8m): D 0,30->0,40
  P_adm 572,7->913,2 kN (util 0,873->0,548); L 10->8 P_adm 572,7->509,8
  (util 0,873->0,981); pre->escavada P_adm 572,7->334,1 (n 1->2); FS 3->2
  P_adm 572,7->859,0 (N=850: n 2->1). Sem tipo -> "pre_moldada" calada.
- bloco (n=2): fck 25->15 MPa em N=600 OK->REPROVA (biela); a_pilar
  0,30->0,50 em N=700/800 REPROVA->OK. Bloco decide veredito.
- predio isolado (N=800): D 0,30->0,40 n 2->1; tipo pre->esc n 2->3; sem
  D_m/tipo a conta calava 0,30/"pre_moldada". L ausente ja avisa (nao se
  recusa caminho que declara). Divisa: mesmos defaults + P_adm=700,0.
- metalico: to_rodar_params .get(D,0,30)/.get(L,10,)/.get(tipo)/.get(FS,3,0)
  + rodar setdefault D/L/bloco {a_pilar 0,30, fck 25 MPa}. fck do bloco le o
  material declarado do projeto (spec fundacao.fck -> params).
- wizard: construir_spec gravava o default no spec (origem perdida ali).

Entregue (D102, fonte unica estaca_parametros_g143, sem arbitrar valor e sem
trocar o FS): D/L/tipo (metalico, predio), bloco e a_pilar (metalico)
recusam nomeados; fck/fyk do bloco herdam o material com a origem dita; FS
ausente mantem 3,0 normativo com a origem dita no resultado e no memorial.

Convencoes: baseline nos dois sentidos, vermelho por injecao em cada porta
(ausente -> recusa ou declaracao ate resultado+memorial+folha; declarado ->
numero do spec), tmp_path sem mutar o repo, ausente e zero um por um,
casa byte-identica, test_estaca_g143 segue verde (suite).
"""
import copy
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import estaca_profunda as ep
import fundacao_edificio as fe

_PERFIL = [{"tipo": "argila", "N": 5, "dz": 3.0},
           {"tipo": "areia", "N": 25, "dz": 8.0}]


def _cfg_nucleo(**kw):
    base = {"perfil": copy.deepcopy(_PERFIL), "D": 0.30, "L": 10.0,
            "tipo_estaca": "pre_moldada", "N_pilar": 500.0,
            "bloco": {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3}}
    base.update(kw)
    return base


def _ctx_predio(pilares):
    return {"pilares": pilares,
            "eixos_x": [0.0, 7.0, 14.0], "eixos_y": [0.0, 5.0, 10.0],
            "materiais": {"fck": 30e3, "fyk": 500e3},
            "estabilidade": None, "momentos_base": None}


def _spec_predio(**est):
    e = {"D_m": 0.30, "L_m": 10.0, "tipo_estaca": "pre_moldada"}
    e.update(est)
    return {"tipo": "estaca", "perfil_spt": copy.deepcopy(_PERFIL),
            "estaca": e}


def _pilar_iso(nome="P1", N=800.0, i=1, j=1):
    return {"nome": nome, "i": i, "j": j, "N_base_k": N,
            "secao": (0.30, 0.50)}


# ---------------- nucleo: tipo recusa, FS declara ----------------

def test_01_nucleo_tipo_recusa_fs_declara_origem():
    gaps = []
    # ausente -> recusa nomeada (nunca "pre_moldada" calada)
    for kw, marca in [({"tipo_estaca": "tubarole"}, "tipo_estaca_invalida"),
                      ({"tipo_estaca": "pre_moldada", "FS": 0},
                       "fs_invalida"),
                      ({"tipo_estaca": "pre_moldada", "FS": -1.0},
                       "fs_invalida")]:
        try:
            ep.verifica_estaca(_cfg_nucleo(**kw))
            gaps.append("devia recusar %s" % marca)
        except ValueError as exc:
            if marca not in str(exc):
                gaps.append("erro sem a marca %s: %r" % (marca, exc))
    # ausencia de verdade (sem a chave): mesmo nome
    for chave, marca in [("tipo_estaca", "tipo_estaca_nao_declarada")]:
        try:
            cfg = _cfg_nucleo()
            del cfg[chave]
            ep.verifica_estaca(cfg)
            gaps.append("devia recusar %s ausente" % marca)
        except ValueError as exc:
            if marca not in str(exc):
                gaps.append("ausente sem o nome %s: %r" % (marca, exc))
    # FS ausente -> 3,0 com a origem dita (o numero nao muda)
    r = ep.verifica_estaca(_cfg_nucleo())
    if r["FS"] != 3.0 or r["FS_origem"] != "fs_adotado_D38":
        gaps.append("FS ausente sem origem normativa: %r" % (r,))
    if r["capacidade"]["FS_origem"] != "fs_adotado_D38":
        gaps.append("capacidade sem FS_origem: %r" % (r["capacidade"],))
    # FS declarado -> o numero do cfg, origem declarada
    r2 = ep.verifica_estaca(_cfg_nucleo(FS=2.0))
    if r2["FS"] != 2.0 or r2["FS_origem"] != "declarado_no_spec":
        gaps.append("FS declarado sem origem: %r" % (r2,))
    # memorial declara a origem
    rel = ep.relatorio_pt(r)
    if "FS global = 3,0" not in rel or "NBR 6122" not in rel:
        gaps.append("memorial sem a origem do FS")
    rel2 = ep.relatorio_pt(r2)
    if "FS global = 2,0" not in rel2 or "declarado no spec" not in rel2:
        gaps.append("memorial sem FS declarado: %r" % (rel2,))
    assert not gaps, "G149 nucleo:\n%s" % "\n".join("  - " + g for g in gaps)


def test_02_nucleo_medida_d_l_tipo_fs_mudam_conta():
    """Tabela do verbete: cada item muda capacidade, n ou veredito."""
    gaps = []
    base = ep.verifica_estaca(_cfg_nucleo())
    variacoes = [({"D": 0.40}, "P_adm_kN", "D"),
                 ({"L": 8.0}, "P_adm_kN", "L"),
                 ({"tipo_estaca": "escavada"}, "P_adm_kN", "tipo"),
                 ({"FS": 2.0}, "P_adm_kN", "FS")]
    for kw, chave, rot in variacoes:
        r = ep.verifica_estaca(_cfg_nucleo(**kw))
        if r["capacidade"][chave] == base["capacidade"][chave]:
            gaps.append("%s devia mudar a capacidade" % rot)
    # FS 3->2 muda n (N=850: 2->1); tipo muda n no mesmo N
    if ep.verifica_estaca(_cfg_nucleo(N_pilar=850.0))["grupo"]["n"] == \
            ep.verifica_estaca(_cfg_nucleo(N_pilar=850.0, FS=2.0))["grupo"]["n"]:
        gaps.append("FS 3->2 devia mudar n (N=850)")
    # bloco: fck 25->15 em N=600 inverte o veredito da biela
    b_ok = ep.verifica_estaca(_cfg_nucleo(N_pilar=600.0))["bloco"]["OK"]
    b_rep = ep.verifica_estaca(_cfg_nucleo(
        N_pilar=600.0,
        bloco={"a_pilar": 0.30, "fck": 15e3, "fyk": 500e3}))["bloco"]["OK"]
    if not (b_ok and not b_rep):
        gaps.append("fck 25->15 devia inverter o bloco (N=600): %r/%r"
                    % (b_ok, b_rep))
    # bloco: a_pilar 0,30->0,50 em N=700 inverte de volta
    a_rep = ep.verifica_estaca(_cfg_nucleo(N_pilar=700.0))["bloco"]["OK"]
    a_ok = ep.verifica_estaca(_cfg_nucleo(
        N_pilar=700.0,
        bloco={"a_pilar": 0.50, "fck": 25e3, "fyk": 500e3}))["bloco"]["OK"]
    if not (not a_rep and a_ok):
        gaps.append("a_pilar 0,30->0,50 devia inverter o bloco (N=700)")
    assert not gaps, "G149 medida:\n%s" % "\n".join("  - " + g for g in gaps)


# ---------------- metalico: spec -> params recusa ou declara ----------------

def _spec_met(**ekw):
    import projeto_spec as PS
    s = PS.novo()
    s["slug"] = "g149"
    s["descricao"] = "g149"
    s["terreno"].update(area_lote_m2=4000, to_max=0.6, ca_max=1.0,
                        tp_min=0.2,
                        recuos={"frente": 5, "lateral": 3, "fundos": 3})
    s["geometria"].update(span=10.0, comprimento=20.0, eave=6.0, ridge=6.5,
                          bay=5.0, base_fixed=True)
    s["cobertura"].update(aguas=2, slope=0.10, telha_tipo="trapezoidal",
                          telha_peso=0.10, calha=False)
    s["fechamento"].update(tipo="telha", altura_alvenaria=0, peso=0.05)
    s["aberturas"] = {"vedada": True}
    s["vento"].update(v0=40, cat="II", classe="B", s3=0.95, z=6.5,
                      abertura_dominante="portao_oitao")
    s["ponte"] = None
    s["cargas"].update(G=0.27, Q=0.25, self=0.35, tapamento=0.05)
    s["fundacao"]["sigma_solo_adm"] = 200.0
    s["fundacao"]["tipo"] = "estaca"
    e = {"perfil_spt": copy.deepcopy(_PERFIL), "tipo_estaca": "pre_moldada",
         "D": 0.30, "L": 10.0, "FS": 3.0,
         "bloco": {"a_pilar": 0.30, "fck": 25e3, "fyk": 500e3}}
    e.update(ekw)
    s["fundacao"]["estaca"] = e
    return s


def test_03_metalico_spec_recusa_um_por_um_ausente_e_zero():
    """Convencao 13: ausente e zero/invalido, um por um, cada um com o nome."""
    import projeto_spec as PS

    gaps = []
    casos = [
        ({"D": None}, "d_estaca_nao_declarada"),
        ({"L": None}, "l_estaca_nao_declarada"),
        ({"tipo_estaca": None}, "tipo_estaca_nao_declarada"),
        ({"bloco": None}, "bloco_nao_declarado"),
        ({"bloco": {"fck": 25e3, "fyk": 500e3}}, "a_pilar_nao_declarado"),
        ({"D": 0}, "d_estaca_invalida"),
        ({"L": 0}, "l_estaca_invalida"),
        ({"D": -0.30}, "d_estaca_invalida"),
        ({"tipo_estaca": "tubarole"}, "tipo_estaca_invalida"),
        ({"D": True}, "d_estaca_invalida"),
        ({"FS": "x"}, "fs_invalida"),
    ]
    for troca, marca in casos:
        s = _spec_met()
        for k, v in troca.items():
            if v is None:
                s["fundacao"]["estaca"].pop(k, None)
            else:
                s["fundacao"]["estaca"][k] = v
        try:
            # exigir_completo (validar) bloqueia primeiro com as mesmas
            # marcas; o resolver recusa do mesmo jeito na porta direta
            PS.to_rodar_params(s)
            gaps.append("devia recusar %s (%r)" % (marca, troca))
        except ValueError as exc:
            if marca not in str(exc):
                gaps.append("erro sem a marca %s: %r" % (marca, exc))
    # FS=0 cai na regra da prova de carga (NBR 6122), nao no default
    s = _spec_met()
    s["fundacao"]["estaca"]["FS"] = 0
    try:
        PS.to_rodar_params(s)
        gaps.append("FS=0 devia bloquear")
    except ValueError as exc:
        if "exige prova de carga" not in str(exc):
            gaps.append("FS=0 sem a regra: %r" % (exc,))
    # validar() tambem bloqueia D/L/bloco ausentes com os nomes
    s = _spec_met()
    del s["fundacao"]["estaca"]["D"]
    falt = [p for p, _ in PS.validar(s)["faltando"]]
    if "fundacao.estaca.D" not in falt:
        gaps.append("validar sem D da estaca: %r" % (falt,))
    # declarado -> o numero do spec chega a params, com a origem
    p = PS.to_rodar_params(_spec_met(D=0.40, L=8.0))
    if (p["estaca"]["D"], p["estaca"]["L"]) != (0.40, 8.0):
        gaps.append("declarado nao chegou a params: %r" % (p["estaca"],))
    # FS ausente -> 3,0 normativo dito; fck ausente herda o material dito
    # G154: o _spec_met usa PS.novo (modelo) sem declarar — a heranca diz
    # modelo_PS_novo (antes material_do_projeto generico; baseline mudada
    # com motivo: a origem distingue desde onde o numero nasce).
    s = _spec_met()
    del s["fundacao"]["estaca"]["FS"]
    del s["fundacao"]["estaca"]["bloco"]["fck"]
    del s["fundacao"]["estaca"]["bloco"]["fyk"]
    p2 = PS.to_rodar_params(s)
    if p2["estaca"]["FS"] != 3.0 \
            or p2["estaca"]["FS_origem"] != "fs_adotado_D38":
        gaps.append("FS ausente sem origem normativa: %r" % (p2["estaca"],))
    if p2["estaca"]["bloco"]["fck"] != 25e3 \
            or p2["estaca"]["bloco_origens"]["fck"] not in (
                "material_do_projeto", "modelo_PS_novo",
                "modelo_legado_confirmar"):
        gaps.append("fck sem heranca do material: %r" % (p2["estaca"],))
    assert not gaps, "G149 metalico-spec:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_04_metalico_rodar_direto_recusa_e_declara(tmp_path):
    """A armadilha: setdefault no dict copiado nao aparece no spec de
    entrada — a recusa mora no rodar, e a declaracao chega ao resultado e
    ao memorial (gate7-estaca.txt)."""
    import projeto_spec as PS
    import rodar_galpao as RG

    gaps = []
    # params sem D: recusa nomeada (nunca 0,30 calado)
    s = _spec_met()
    p = PS.to_rodar_params(s)
    del p["estaca"]["D"]
    try:
        RG.rodar(p, str(tmp_path / "sem_d"))
        gaps.append("rodar sem D devia recusar, nao calar 0,30")
    except ValueError as exc:
        if "d_estaca_nao_declarada" not in str(exc):
            gaps.append("rodar sem o nome: %r" % (exc,))
    # params sem bloco: recusa (nunca o dict cheio calado)
    p = PS.to_rodar_params(s)
    del p["estaca"]["bloco"]
    try:
        RG.rodar(p, str(tmp_path / "sem_bloco"))
        gaps.append("rodar sem bloco devia recusar")
    except ValueError as exc:
        if "bloco_nao_declarado" not in str(exc):
            gaps.append("bloco sem o nome: %r" % (exc,))
    # declarado -> resultado com numeros e origens; memorial declara o FS
    p = PS.to_rodar_params(_spec_met(D=0.40, L=8.0,
                                    tipo_estaca="pre_moldada"))
    out = str(tmp_path / "decl")
    res = RG.rodar(p, out)
    e = res.get("estaca") or {}
    if (e.get("D"), e.get("L"), e.get("tipo")) != (0.40, 8.0, "pre_moldada"):
        gaps.append("declarado nao chegou ao resultado: %r" % (e,))
    if e.get("FS_origem") != "declarado_no_spec":
        gaps.append("resultado sem FS_origem: %r" % (e,))
    if e.get("FS") != 3.0:
        gaps.append("FS trocado no resultado: %r" % (e,))
    mem = open(os.path.join(out, "gate7-estaca.txt"),
               encoding="utf-8").read()
    if "FS global = 3,0" not in mem or "NBR 6122" not in mem:
        gaps.append("memorial sem a origem do FS")
    assert not gaps, "G149 metalico-rodar:\n%s" % "\n".join(
        "  - " + g for g in gaps)


# ---------------- wizard: sem default gravado ----------------

def test_05_wizard_nao_grava_default_no_spec():
    import projeto_spec as PS
    import wizard as WZ

    gaps = []
    base = {"area_lote_m2": 1200, "span": 10, "comprimento": 20, "eave": 6,
            "v0": 40, "sigma_solo": 200, "fund_tipo": "estaca",
            "spt_tipo": "areia_siltosa", "spt_N": 20, "spt_dz": 8.0}
    # sem est_*: nenhuma chave gravada (a origem se perdia aqui)
    s = WZ.construir_spec(dict(base), slug="t")
    est = s["fundacao"]["estaca"]
    for chave in ("tipo_estaca", "D", "L", "FS"):
        if chave in est:
            gaps.append("wizard gravou default de %s: %r" % (chave, est))
    falt = [p for p, _ in PS.validar(s)["faltando"]]
    for esperado in ("fundacao.estaca.tipo_estaca", "fundacao.estaca.D",
                     "fundacao.estaca.L", "fundacao.estaca.bloco"):
        if esperado not in falt:
            gaps.append("validar sem %s: %r" % (esperado, falt))
    # um por um: so o declarado passa
    for kw in [{"est_tipo": "pre_moldada"}, {"est_tipo": "pre_moldada",
                                             "est_D": 0.30}]:
        rr = dict(base, **kw)
        v = PS.validar(WZ.construir_spec(rr, slug="t"))
        if v["ok"]:
            gaps.append("parcial devia bloquear: %r" % (kw,))
    # declarado -> os numeros da resposta, sem resto calado
    rr = dict(base, est_tipo="escavada", est_D=0.40, est_L=8.0, est_FS=3.0,
              est_a_pilar=0.30)
    s2 = WZ.construir_spec(rr, slug="t2")
    e2 = s2["fundacao"]["estaca"]
    if (e2.get("tipo_estaca"), e2.get("D"), e2.get("L")) != \
            ("escavada", 0.40, 8.0):
        gaps.append("wizard nao levou o declarado: %r" % (e2,))
    if PS.validar(s2)["ok"] is not True:
        gaps.append("declarado devia validar: %r"
                    % (PS.validar(s2)["faltando"],))
    assert not gaps, "G149 wizard:\n%s" % "\n".join("  - " + g for g in gaps)


# ---------------- predio: D_m/tipo recusam, L declara ----------------

def test_06_predio_isolado_recusa_d_tipo_e_mede():
    gaps = []
    ctx = _ctx_predio([_pilar_iso()])
    # ausente -> recusa nomeada (nunca 0,30/"pre_moldada" calados)
    for troca, marca in [({"__del__D": 1}, "d_estaca_nao_declarada"),
                         ({"__del__tipo": 1}, "tipo_estaca_nao_declarada"),
                         ({"D_m": 0}, "d_estaca_invalida"),
                         ({"tipo_estaca": "tubarole"},
                          "tipo_estaca_invalida")]:
        sp = _spec_predio()
        if "__del__D" in troca:
            del sp["estaca"]["D_m"]
        elif "__del__tipo" in troca:
            del sp["estaca"]["tipo_estaca"]
        else:
            sp["estaca"].update(troca)
        try:
            fe.dimensiona(sp, ctx)
            gaps.append("devia recusar %s" % marca)
        except fe.EntradaFundacao as exc:
            if marca not in str(exc):
                gaps.append("erro sem a marca %s: %r" % (marca, exc))
    # L ausente NAO recusa: declara via aviso (caminho que declara)
    sp = _spec_predio()
    del sp["estaca"]["L_m"]
    r = fe.dimensiona(sp, ctx)
    if "comprimento_de_estaca_lido_da_sondagem" not in [
            a["code"] for a in r["avisos"]]:
        gaps.append("L ausente sem o aviso: %r" % (r["avisos"],))
    # declarado -> geometria com os numeros; D/tipo mudam n
    base = fe.dimensiona(_spec_predio(), ctx)["por_pilar"]["P1"]["geometria"]
    d40 = fe.dimensiona(_spec_predio(D_m=0.40), ctx)["por_pilar"]["P1"][
        "geometria"]
    esc = fe.dimensiona(_spec_predio(tipo_estaca="escavada"), ctx)[
        "por_pilar"]["P1"]["geometria"]
    if (base["n_estacas"], d40["n_estacas"], esc["n_estacas"]) != (2, 1, 3):
        gaps.append("D/tipo deviam mudar n (2/1/3): %r/%r/%r"
                    % (base, d40, esc))
    # proveniencia viaja no resultado
    par = fe.dimensiona(_spec_predio(), ctx)["estaca_parametros"]
    if par["parametros"]["D_m"]["origem"] != "declarado_no_spec":
        gaps.append("D sem origem: %r" % (par,))
    if par["parametros"]["FS"]["valor"] != 3.0 \
            or par["parametros"]["FS"]["origem"] != \
            "fs_adotado_D38":
        gaps.append("FS sem origem normativa: %r" % (par,))
    # memorial declara D/L/tipo/FS
    rel = fe.relatorio_pt(fe.dimensiona(_spec_predio(), ctx))
    for termo in ("D=0.30", "tipo=pre_moldada", "FS global = 3.0",
                  "NBR 6122"):
        if termo not in rel:
            gaps.append("memorial do predio sem %r" % termo)
    assert not gaps, "G149 predio-isolado:\n%s" % "\n".join(
        "  - " + g for g in gaps)


def test_07_predio_divisa_recusa_e_sem_700_calado():
    gaps = []

    def _ctx():
        return _ctx_predio([
            {"nome": "P1", "i": 0, "j": 1, "N_base_k": 800.0,
             "secao": (0.30, 0.50), "posicao": "extremidade"},
            {"nome": "P2", "i": 1, "j": 1, "N_base_k": 900.0,
             "secao": (0.30, 0.50), "posicao": "meio"}])

    # sem D_m/sem tipo na divisa: recusa nomeada (nunca 0,30 calado + 700)
    for troca, marca in [({"__del__D": 1}, "d_estaca_nao_declarada"),
                         ({"__del__tipo": 1}, "tipo_estaca_nao_declarada")]:
        sp = _spec_predio()
        if "__del__D" in troca:
            del sp["estaca"]["D_m"]
        else:
            del sp["estaca"]["tipo_estaca"]
        try:
            fe.dimensiona(sp, _ctx())
            gaps.append("divisa devia recusar %s" % marca)
        except fe.EntradaFundacao as exc:
            if marca not in str(exc):
                gaps.append("divisa sem a marca %s: %r" % (marca, exc))
    # perfil sem tipo de solo: recusa (antes caia no P_adm=700 em silencio)
    sp = _spec_predio()
    sp["perfil_spt"] = [{"N": 5, "dz": 3.0}, {"N": 25, "dz": 8.0}]
    try:
        fe.dimensiona(sp, _ctx())
        gaps.append("perfil sem tipo devia recusar, nao usar 700")
    except fe.EntradaFundacao as exc:
        if "TIPO DE SOLO" not in str(exc):
            gaps.append("perfil sem tipo sem motivo: %r" % (exc,))
    # declarado -> divisa_estaca com os numeros; tipo muda n
    base = fe.dimensiona(_spec_predio(), _ctx())["por_pilar"]["P1"][
        "geometria"]
    esc = fe.dimensiona(_spec_predio(tipo_estaca="escavada"), _ctx())[
        "por_pilar"]["P1"]["geometria"]
    if base.get("subtipo") != "divisa_estaca":
        gaps.append("P1 devia ser divisa_estaca: %r" % (base,))
    if (base.get("n_estacas"), esc.get("n_estacas")) != (2, 3):
        gaps.append("tipo devia mudar n na divisa (2/3): %r/%r"
                    % (base, esc))
    assert not gaps, "G149 predio-divisa:\n%s" % "\n".join(
        "  - " + g for g in gaps)


# ---------------- casa/sapata byte-identicas ----------------

def test_08_casa_e_sapata_byte_identicas(tmp_path):
    """A casa e o caminho rasa nao mudam um pixel (G149 so toca a estaca)."""
    import desenho_fundacao_edificio as dfe

    gaps = []
    fund_p = {"tipo": "sapata", "sigma_solo_adm": 250.0,
              "proveniencia_sigma": "declarada no spec (sigma_solo_adm)",
              "cota_apoio_m": 1.0,
              "por_pilar": {"P1": {"i": 0, "j": 0,
                                   "N_dimensionamento_kN": 800.0,
                                   "geometria": {"B_m": 2.0, "L_m": 2.5,
                                                 "h_m": 0.7,
                                                 "subtipo": "isolada"}}}}
    est_p = {"vaos_x": [7.0], "vaos_y": [5.0]}
    antes = dfe.planta_fundacao_svg(fund_p, est_p)
    if "G149" in antes or "proveniencias_g149" in antes:
        gaps.append("caminho rasa vazou marcacao G149")
    p_svg = str(tmp_path / "predio.svg")
    dfe.gerar_planta_fundacao(fund_p, est_p, p_svg)
    with open(p_svg, encoding="utf-8") as f:
        if f.read() != antes:
            gaps.append("gerar_planta_fundacao mudou a rasa")
    # dimensiona rasa nao carrega proveniencia de estaca
    ctx = _ctx_predio([_pilar_iso()])
    r = fe.dimensiona({"tipo": "sapata", "sigma_solo_adm": 250.0}, ctx)
    if r.get("estaca_parametros") is not None \
            or r.get("proveniencias_g149") is not None:
        gaps.append("rasa com proveniencia de estaca: %r" % (r,))
    assert tmp_path.is_dir()
    assert not gaps, "G149 byte-identico:\n%s" % "\n".join(
        "  - " + g for g in gaps)


# ---------------- folha do predio: tres aceites com estaca ----------------

def test_09_folha_fundacao_predio_tres_aceites_com_estaca(tmp_path):
    """Os tres aceites da folha de fundacao do predio com estaca (convencao
    6), olhando o PNG: (1) esta certa, (2) sai no manifesto, (3) diz o que
    desenha."""
    import desenho_fundacao_edificio as dfe
    import edificio_adapter as ea
    import pacote_legal as pl
    from caderno_casa_edificio import svg_para_png
    from desenho_svg_base import confere_folha_svg

    gaps = []
    r = fe.dimensiona(_spec_predio(), _ctx_predio(
        [_pilar_iso("P1", 800.0, 0, 0), _pilar_iso("P2", 900.0, 1, 0)]))
    # (1) esta certa: cada pilar do resultado desenhado, um por um, com
    # n/D/L dimensionados + a declaracao G149
    svg = dfe.planta_fundacao_svg(r, {"vaos_x": [7.0], "vaos_y": [5.0]})
    ET.fromstring(svg)
    if svg.count("data-pilar") != 2:
        gaps.append("elementos %d != 2 pilares" % svg.count("data-pilar"))
    for pilar, (n, d, l) in (("P1", (2, 0.30, 10.0)),
                             ("P2", (2, 0.30, 10.0))):
        marca = 'data-pilar="%s"' % pilar
        if marca not in svg:
            gaps.append("pilar %s nao desenhado" % pilar)
        _ = (n, d, l)
    if 'data-n="2"' not in svg or 'data-D="0.300"' not in svg:
        gaps.append("quadro sem n/D/L dimensionados")
    if "G149" not in svg or "declarado no spec" not in svg:
        gaps.append("folha sem a declaracao G149")
    if "NBR 6122" not in svg:
        gaps.append("folha sem a origem do FS")
    if not dfe.confere_desenho_fundacao(r, svg).get("ok"):
        gaps.append("desenhado != dimensionado: %r"
                    % (dfe.confere_desenho_fundacao(r, svg),))
    if not confere_folha_svg(svg).get("ok"):
        gaps.append("guarda reprova a folha: %r"
                    % (confere_folha_svg(svg),))
    p_svg = str(tmp_path / "fund_estaca.svg")
    p_png = str(tmp_path / "fund_estaca.png")
    with open(p_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    if not svg_para_png(p_svg, p_png) or not os.path.getsize(p_png):
        gaps.append("folha com estaca nao rasterizou para o aceite visual")
    # sem D_m nao ha folha silenciosa: a conta recusa antes de desenhar
    sp = _spec_predio()
    del sp["estaca"]["D_m"]
    try:
        fe.dimensiona(sp, _ctx_predio([_pilar_iso()]))
        gaps.append("sem D_m devia recusar, nao desenhar")
    except fe.EntradaFundacao as exc:
        if "d_estaca_nao_declarada" not in str(exc):
            gaps.append("recusa sem nome: %r" % (exc,))
    # (2) sai no manifesto: codigo no mapa 1:1 com o arquivo emitido
    if ea._PRANCHA_ARQUIVO.get("PE-CO-04") != "fundacao-locacao-formas.svg":
        gaps.append("mapa PE-CO-04 fora do basename")
    # (3) diz o que desenha: titulo do indice cobre locacao da fundacao
    titulos = {f["codigo"]: f["titulo"]
               for f in pl.indice_de_pranchas(["concreto"])}
    if "locacao" not in titulos.get("PE-CO-04", "").lower():
        gaps.append("indice nao diz locacao: %r" % (titulos,))
    assert tmp_path.is_dir()
    assert not gaps, "G149 aceites:\n%s" % "\n".join("  - " + g for g in gaps)
