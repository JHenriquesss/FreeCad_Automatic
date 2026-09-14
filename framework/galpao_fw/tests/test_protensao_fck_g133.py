"""G133 - a viga protendida num concreto que o projeto nao declarou.

Medido (G131 + remedicao G133 na funcao real): galpao_concreto.py:223
passava `max(fck, 40e3)` a viga protendida (projeto C30 calculado em C40) e
viga_protendida.py:154 fazia `fckj = cfg.get("fckj", fck)` (o ato usava o
fck de 28 dias, sem fckj passado). Galpao de 15 m em C30: tipo_viga =
"protendida", lim_comp = -28000 kN/m2 no ato, relatorio "C30" e memorial
sem C40; o "[A CONFIRMAR: fckj ...]" da viga chegava ao memorial pelo
executivo, mas nao as folhas nem ao relatorio do galpao.

Entregue:
  1. FONTE UNICA (protensao_fck_g133.py, producao): CHAVES
     ("fck_protendida", "fckj_protensao"), _parse_fck (kN/m2, atalho MPa),
     fck_protendida/fckj_de_spec (sem default silencioso; invalido LEVANTA),
     resolver_entrada (ausente = fck do projeto / fckj = fck usado, com a
     origem dita; nunca C40 de fabrica, nunca idade inventada),
     protensao_do_turnkey/protensao_da_entrega (o que a conta USOU vence;
     divergencia LEVANTA), linha_protensao (o que a folha e o memorial
     dizem), contem_declaracao/confere_pecas (peca sem declaracao reprova),
     defaults_de_protensao/confere_defaults (nenhum `max(fck, ...)` nem
     default numerico, por AST) e arquivos_que_importam/confere_uso
     (ninguem le por conta propria).
  2. PISO DECLARADO (nao bloqueio, nao C40): ausente usa o fck do projeto e
     o fckj = fck, e a folha e o memorial dizem isso; desconhecido levanta
     em toda porta. Nao escolhe o fck de fabrica nem a idade de protensao.
  3. FIACAO: viga_protendida (origem gravada no resultado + linha no
     relatorio), galpao_concreto.rodar (resolve do spec, viaja no
     resultado, relatorio declara), desenho_concreto (2 SVG, bloco no
     rodape), techdraw_concreto (notas, do resultado), pacote_legal
     (secao G133, do calculado) e galpao_adapter (topo chega ao payload;
     divergencia levanta).
  4. PORTAO (test_01): as pecas reais declaram; sem declaracao reprova, por
     parte (convencao 7).
  5. BASELINE (test_02, nos dois sentidos): chaves, piso = fck do projeto,
     8 leitores, zero defaults, invalido levanta.
  6. INJECAO (test_03, tmp_path, nunca o repo): `max(fck, ...)` e default
     numerico novos acusam; spec C30 sem declaracao sai calculado em C30
     (nunca C40 calado); peca antiga sem a linha reprova.
  7. ENTRADAS (test_04, convencao 11): cada entrada que o produto aceita
     (spec do galpao_concreto, payload turnkey.concreto, topo do
     project-spec via adapter/rodada real) chega a conta; topo x payload
     divergentes falham com o motivo escrito. O ProjetoSpec/wizard do
     galpao METALICO nao e entrada (sem viga protendida la: nao repetir o
     G134, dito na fonte).
  8. CASOS (test_05): os casos do repo antes/depois na funcao REAL.
  9. FONTES (test_06, anti-tautologia): a producao LE a fonte unica; sem
     parametro = piso declarado; invalida levanta.
 10. ENTREGA (test_07): o calculado vence e a divergencia levanta; sem
     concreto / sem protendida / casa declaram o terceiro valor.

O que a lente NAO cobre: valores de `s`/beta1 da 12.3.3 (fonte da edicao /
premoldado; aqui nunca se converte idade em resistencia); o cimento do
icamento (fonte G126); ProjetoSpec/wizard metalico (sem protendida); o PDF
do memorial (a declaracao mora no memorial em texto, que o portao confere).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import protensao_fck_g133 as lente


def _galpao_concreto(**kw):
    import galpao_concreto as gc
    base = {"vao": 15.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}
    base.update(kw)
    return gc.rodar(base)


def _pecas_reais(vao=15.0):
    """As pecas que o cliente recebe, emitidas de verdade (piso: sem chaves)."""
    import desenho_concreto as dc
    import pacote_legal as pl
    import executivo_concreto as ex
    import galpao_concreto as gc
    import techdraw_concreto as tc
    import viga_protendida as vp

    r = _galpao_concreto(vao=vao)
    svg_arm = dc.prancha_armacao_svg(r)
    svg_for = dc.planta_formas_svg(r)
    pac = pl.gerar_pacote(["concreto"], spec={"fck": 30e3},
                          protensao_calculada=r.get("protensao"))
    md = pl.markdown(pac)
    mem = ex.memorial(r)
    rel = gc.relatorio_pt(r)
    cfg = tc.config_de_spec(r, "dummy.FCStd", "/tmp")
    notas = "\n".join(cfg["notas"])
    pecas = {"desenho_concreto.prancha_armacao_svg": svg_arm,
             "desenho_concreto.planta_formas_svg": svg_for,
             "pacote_legal.markdown": md,
             "executivo_concreto.memorial": mem,
             "galpao_concreto.relatorio_pt": rel,
             "techdraw_concreto.notas": notas,
             "_resultado": r}
    if r.get("viga_prot"):
        pecas["viga_protendida.relatorio_pt"] = vp.relatorio_pt(r["viga_prot"])
    return pecas


def test_01_portao_pecas_reais_declaram_e_sem_declaracao_reprova():
    """Um assert so (receita G97): toda peca real declara a protensao; a
    mesma peca sem a declaracao reprova no mesmo portao (o instrumento
    acusa por parte, convencao 7 do lote). Vale para a protendida (15 m)
    e para o terceiro valor (10 m, concreto armado)."""
    lados = []
    for vao in (15.0, 10.0):
        pecas = _pecas_reais(vao=vao)
        reais = {k: v for k, v in pecas.items() if not k.startswith("_")}
        conf = lente.confere_pecas(reais)
        sem_nome = {n: t.replace("Protensao (fck da viga", "PROTENSAO REMOVIDA")
                    for n, t in reais.items()}
        conf_sem = lente.confere_pecas(sem_nome)
        if not conf["OK"] or conf["sem_declaracao"]:
            lados.append("vao %.0f: peca real sem declaracao de protensao: %r"
                         % (vao, conf["sem_declaracao"]))
        if conf_sem["OK"] or sorted(conf_sem["sem_declaracao"]) != sorted(reais):
            lados.append("vao %.0f: o portao nao acusa por parte: %r"
                         % (vao, conf_sem["sem_declaracao"]))
        # o terceiro valor so onde nao ha protendida.
        tem_prot = pecas["_resultado"].get("tipo_viga") == "protendida"
        for nome, texto in reais.items():
            c = lente.contem_declaracao_protensao(texto)
            if tem_prot and c["origem"] == lente.ORIGEM_SEM_PROTENSAO:
                lados.append("vao %.0f %s declara sem-protendida com protendida: %r"
                             % (vao, nome, c))
            if not tem_prot and c["origem"] != lente.ORIGEM_SEM_PROTENSAO:
                lados.append("vao %.0f %s devia declarar o terceiro valor: %r"
                             % (vao, nome, c))
    assert not lados, "portao G133 reprova:\n" + "\n".join(lados)


def test_02_baseline_nos_dois_sentidos():
    """Um assert so: chaves, piso = fck do projeto, 8 leitores, zero
    defaults, atalho MPa, invalido levanta."""
    lados = []
    if set(lente.CHAVE_FCK for _ in [0]) != {"fck_protendida"}:
        lados.append("chave do fck mudou de nome sem triagem")
    if lente.CHAVE_FCKJ != "fckj_protensao":
        lados.append("chave do fckj mudou de nome sem triagem")
    r = lente.resolver_entrada({"fck": 30e3}, 30e3)
    if not (r["fck_usado"] == 30e3 and r["fckj_usado"] == 30e3
            and r["fck_origem"] == lente.ORIGEM_FCK_PISO
            and r["fckj_origem"] == lente.ORIGEM_FCKJ_PISO):
        lados.append("sem chaves devia ser piso C30 declarado: %r" % (r,))
    if lente.MARCA_FABRICA not in lente.linha_protensao(r):
        lados.append("linha sem declaracao esconde que nao ha piso C40: %r"
                     % (lente.linha_protensao(r),))
    if "nao declarado" not in lente.linha_protensao(r):
        lados.append("linha sem declaracao esconde a ausencia: %r"
                     % (lente.linha_protensao(r),))
    rd = lente.resolver_entrada({"fck": 30e3, "fck_protendida": 40e3,
                                 "fckj_protensao": 40e3}, 30e3)
    if not (rd["fck_usado"] == 40e3 and rd["fckj_usado"] == 40e3
            and rd["fck_origem"] == lente.ORIGEM_FCK_DECLARADO
            and rd["fckj_origem"] == lente.ORIGEM_FCKJ_DECLARADO):
        lados.append("declarado C40 devia vencer com a origem dita: %r" % (rd,))
    if lente.MARCA_FCK_DECLARADO not in lente.linha_protensao(rd) \
            or lente.MARCA_FCKJ_DECLARADO not in lente.linha_protensao(rd):
        lados.append("linha declarada sem marcas: %r"
                     % (lente.linha_protensao(rd),))
    if lente._parse_fck("40 MPa", "fck_protendida") != 40e3:
        lados.append("atalho MPa devia valer 40 MPa = 40e3")
    if lente._parse_fck(40, "fck_protendida") != 40e3:
        lados.append("atalho numerico 40 devia valer 40e3")
    for mau in ("XYZ", -5, 0):
        for fn in (lente.fck_protendida_de_spec, lente.fckj_protensao_de_spec):
            try:
                fn({"fck_protendida": mau, "fckj_protensao": mau,
                    "fck": 30e3} if fn is lente.fck_protendida_de_spec
                   else {"fckj_protensao": mau, "fck": 30e3})
                lados.append("valor %r devia levantar em %s"
                             % (mau, fn.__name__))
            except ValueError:
                pass
    try:
        lente.resolver_entrada({"fck": 30e3}, None)
        lados.append("resolver sem fck do projeto devia levantar")
    except ValueError:
        pass
    u = lente.confere_uso_protensao()
    if not u["OK"]:
        lados.append("leitores divergem do baseline: extras=%r faltando=%r"
                     % (u["extras"], u["faltando"]))
    if len(u["tem"]) != 8:
        lados.append("leitores esperados = 8, medidos %d: %r"
                     % (len(u["tem"]), u["tem"]))
    d = lente.confere_defaults()
    if not d["OK"]:
        lados.append("defaults silenciosos sobrando: %r" % (d["defaults"],))
    try:
        lente.confere_pecas(None)
        lados.append("confere_pecas(None) devia levantar TypeError")
    except TypeError:
        pass
    assert not lados, "baseline G133 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_em_tmp_path_e_sem_c40_calado(tmp_path):
    """Um assert so: defeito injetado em tmp_path (nunca o repo) acusa; spec
    C30 sem declaracao sai calculado em C30 (lim_comp -21000, nunca -28000
    calado); peca antiga sem a linha reprova."""
    lados = []
    # (a) max(fck, ...) reinjetado num diretorio temporario acusa.
    inj = tmp_path / "inj_max"
    inj.mkdir()
    (inj / "galpao_concreto.py").write_text(
        "def rodar(spec):\n"
        "    fck = spec.get('fck', 30e3)\n"
        "    x = max(fck, 40e3)\n"
        "    return x\n", encoding="utf-8")
    d = lente.confere_defaults(raiz=inj)
    if d["OK"]:
        lados.append("max(fck, 40e3) injetado em tmp_path nao acusou")
    # (b) default numerico nas chaves novas acusa.
    inj2 = tmp_path / "inj_get"
    inj2.mkdir()
    (inj2 / "qualquer.py").write_text(
        "def f(spec):\n"
        "    return spec.get('fck_protendida', 40e3)\n", encoding="utf-8")
    d2 = lente.confere_defaults(raiz=inj2)
    if d2["OK"]:
        lados.append("get('fck_protendida', 40e3) injetado nao acusou")
    (inj2 / "outro.py").write_text(
        "def f(cfg):\n"
        "    return cfg.get('fckj', 25e3)\n", encoding="utf-8")
    d3 = lente.confere_defaults(raiz=inj2)
    if d3["OK"]:
        lados.append("get('fckj', 25e3) injetado nao acusou")
    # o mecanismo da ausencia dita (get com o nome fck) nao acusa.
    limpo = tmp_path / "limpo"
    limpo.mkdir()
    (limpo / "ok.py").write_text(
        "def f(cfg, fck):\n"
        "    return cfg.get('fckj', fck)\n", encoding="utf-8")
    if not lente.confere_defaults(raiz=limpo)["OK"]:
        lados.append("o mecanismo da ausencia dita acusou sem dever")
    # (c) spec C30 sem declaracao: a conta usa C30, nunca C40.
    r = _galpao_concreto()
    vp = r["viga_prot"]
    if abs(vp["fck"] - 30e3) > 1e-6 or abs(vp["fckj"] - 30e3) > 1e-6:
        lados.append("sem declaracao a conta devia usar C30: fck=%r fckj=%r"
                     % (vp.get("fck"), vp.get("fckj")))
    if abs(vp["ato"]["lim_comp"] + 21000.0) > 1e-6:
        lados.append("sem declaracao o ato devia travar em -21000 (C30), "
                     "nao -28000: %r" % (vp["ato"]["lim_comp"],))
    # (d) peca antiga (diz C30, verificada em C40, sem a linha) reprova.
    antiga = ("GALPAO DE CONCRETO PRE-MOLDADO (NBR 6118/6123/6122)\n"
              "  Vao 15,0 m x comprimento 40,0 m ; C30\n"
              "  VIGA DE COBERTURA (protendida): secao 20x60 cm ; "
              "4 cordoalhas -> ATENDE")
    if lente.contem_declaracao_protensao(antiga)["tem"]:
        lados.append("peca antiga sem a linha devia reprovar")
    if lente.confere_pecas({"antiga": antiga})["OK"]:
        lados.append("confere_pecas devia reprovar a peca antiga")
    assert not lados, "vermelho G133 reprova:\n" + "\n".join(lados)


def test_04_cada_entrada_chega_a_conta_convencao_11():
    """Um assert so (convencao 11): cada entrada que o produto aceita para
    este dado chega a conta - spec direto do galpao_concreto, payload
    turnkey.concreto e topo do project-spec (via adapter). Declarado nos
    dois lugares com valores diferentes levanta."""
    import galpao_turnkey as tk

    lados = []

    def _fck_usado_no_resultado(resultado_concreto_raw):
        prot = resultado_concreto_raw.get("protensao") or {}
        return prot.get("fck_usado"), prot.get("fckj_usado")

    # (a) spec direto do galpao_concreto.
    r = _galpao_concreto(fck_protendida=40e3, fckj_protensao=35e3)
    fu, fju = _fck_usado_no_resultado(r)
    if not (fu == 40e3 and fju == 35e3):
        lados.append("spec direto nao chegou a conta: %r" % (r.get("protensao"),))
    # (b) payload turnkey.concreto.
    pay = {"vao": 15.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
           "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
           "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
           "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo",
           "fck_protendida": 40e3, "fckj_protensao": 35e3}
    R = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 15.0,
                                "pe_direito": 6.0},
                  "concreto": pay})
    raw = R["disciplinas"]["concreto"]["raw"]
    fu, fju = _fck_usado_no_resultado(raw)
    if not (fu == 40e3 and fju == 35e3):
        lados.append("payload turnkey.concreto nao chegou a conta: %r"
                     % (raw.get("protensao"),))
    # payload sem as chaves = piso declarado.
    R0 = tk.rodar({"geometria": {"comprimento": 40.0, "vao": 15.0,
                                 "pe_direito": 6.0},
                   "concreto": {k: v for k, v in pay.items()
                                if k not in ("fck_protendida", "fckj_protensao")}})
    raw0 = R0["disciplinas"]["concreto"]["raw"]
    fu0, fju0 = _fck_usado_no_resultado(raw0)
    if not (fu0 == 30e3 and fju0 == 30e3):
        lados.append("payload sem chaves devia ser piso C30: %r"
                     % (raw0.get("protensao"),))
    # (c) topo do project-spec chega ao payload (adapter) e a conta.
    import galpao_adapter as ga
    import tempfile
    norm = {"adapter": "galpao",
            "raw_spec": {"fck": 30e3, "fck_protendida": 40e3,
                         "fckj_protensao": 35e3},
            "turnkey_spec": {"concreto": dict(pay, fck_protendida=40e3,
                                             fckj_protensao=35e3)},
            "requested_disciplines": ["concreto"]}
    with tempfile.TemporaryDirectory() as td:
        try:
            res_ad, _rec = ga._run_turnkey(norm, __import__("pathlib").Path(td))
        except Exception as e:  # noqa: BLE001 - so registra
            lados.append("adapter com topo==payload nao devia levantar: %r" % (e,))
        else:
            raw_ad = res_ad["disciplinas"]["concreto"]["raw"]
            if _fck_usado_no_resultado(raw_ad) != (40e3, 35e3):
                lados.append("adapter topo==payload nao chegou a conta: %r"
                             % (raw_ad.get("protensao"),))
    norm2 = {"adapter": "galpao",
             "raw_spec": {"fck": 30e3, "fck_protendida": 40e3},
             "turnkey_spec": {"concreto": dict(
                 {k: v for k, v in pay.items()
                  if k not in ("fck_protendida", "fckj_protensao")})},
             "requested_disciplines": ["concreto"]}
    with tempfile.TemporaryDirectory() as td:
        try:
            res_ad2, _rec2 = ga._run_turnkey(norm2, __import__("pathlib").Path(td))
        except Exception as e:  # noqa: BLE001
            lados.append("adapter devia levar o topo ao payload: %r" % (e,))
        else:
            raw_ad2 = res_ad2["disciplinas"]["concreto"]["raw"]
            prot_ad2 = raw_ad2.get("protensao") or {}
            if _fck_usado_no_resultado(raw_ad2) != (40e3, 40e3) or \
                    prot_ad2.get("fckj_origem") != lente.ORIGEM_FCKJ_PISO:
                lados.append("topo nao chegou a conta via adapter: %r"
                             % (raw_ad2.get("protensao"),))
    norm3 = {"adapter": "galpao",
             "raw_spec": {"fck": 30e3, "fck_protendida": 40e3},
             "turnkey_spec": {"concreto": dict(pay, fck_protendida=35e3)},
             "requested_disciplines": ["concreto"]}
    with tempfile.TemporaryDirectory() as td:
        try:
            ga._run_turnkey(norm3, __import__("pathlib").Path(td))
            lados.append("topo x payload divergentes deviam levantar")
        except ValueError:
            pass
    assert not lados, "convencao 11 G133 reprova:\n" + "\n".join(lados)


def test_05_casos_do_repo_antes_e_depois_na_funcao_real():
    """Um assert so: cada caso do repo que bate na protendida, com o numero
    ANTES (C40 declarado = comportamento antigo) e DEPOIS (piso C30). Os
    numeros vao para o verbete D159 um a um; aqui o portao trava a forma
    (nenhum vira C40 calado) e a igualdade do caminho declarado."""
    import viga_protendida as vp

    lados = []
    # A. galpao de concreto 15 m C30 (o caso do goal).
    antes = _galpao_concreto(fck_protendida=40e3, fckj_protensao=40e3)["viga_prot"]
    depois = _galpao_concreto()["viga_prot"]
    if abs(antes["ato"]["lim_comp"] + 28000.0) > 1e-6:
        lados.append("A antes devia travar em -28000: %r" % (antes["ato"],))
    if abs(depois["ato"]["lim_comp"] + 21000.0) > 1e-6:
        lados.append("A depois devia travar em -21000: %r" % (depois["ato"],))
    if (antes["b"], antes["h"], antes["n_cordoalhas"]) != (0.20, 0.60, 4):
        lados.append("A antes devia ser 20x60 4 cordoalhas: %r"
                     % ((antes["b"], antes["h"], antes["n_cordoalhas"]),))
    if (depois["b"], depois["h"], depois["n_cordoalhas"]) != (0.20, 0.60, 4):
        lados.append("A depois devia ser 20x60 4 cordoalhas: %r"
                     % ((depois["b"], depois["h"], depois["n_cordoalhas"]),))
    if abs(antes["elu"]["Mrd"] - 293.3) > 0.5:
        lados.append("A antes Mrd devia ser ~293: %.1f" % (antes["elu"]["Mrd"],))
    if abs(depois["elu"]["Mrd"] - 280.9) > 0.5:
        lados.append("A depois Mrd devia ser ~281: %.1f" % (depois["elu"]["Mrd"],))
    if not (antes["OK"] and depois["OK"]):
        lados.append("A devia ATENDER antes e depois (u 0,90 -> 0,93)")
    # B. galpao de concreto 20 m C30 (fixture do turnkey).
    b_antes = _galpao_concreto(vao=20.0, fck_protendida=40e3,
                               fckj_protensao=40e3)["viga_prot"]
    b_depois = _galpao_concreto(vao=20.0)["viga_prot"]
    if (b_antes["b"], b_antes["h"]) != (0.20, 0.60):
        lados.append("B antes devia ser 20x60: %r" % ((b_antes["b"], b_antes["h"]),))
    if (b_depois["b"], b_depois["h"]) != (0.25, 0.70):
        lados.append("B depois devia ser 25x70: %r" % ((b_depois["b"], b_depois["h"]),))
    if not (b_antes["OK"] and b_depois["OK"]):
        lados.append("B devia ATENDER antes e depois")
    # C. viga isolada 16 m C40 (selftest): ja era C40, numero bit a bit igual.
    c_antes = vp.dimensiona_viga_protendida({"vao": 16.0, "fck": 40e3,
                                             "fckj": 40e3, "q": 5.0})
    c_depois = vp.dimensiona_viga_protendida({"vao": 16.0, "fck": 40e3,
                                              "q": 5.0})
    if abs(c_antes["elu"]["Mrd"] - c_depois["elu"]["Mrd"]) > 1e-9:
        lados.append("C isolada C40 devia ser bit a bit igual: %.6f vs %.6f"
                     % (c_antes["elu"]["Mrd"], c_depois["elu"]["Mrd"]))
    if not (c_antes["OK"] and c_depois["OK"]):
        lados.append("C isolada devia ATENDER")
    # D. nenhum project-spec do repo declara as chaves (piso declarado).
    import pathlib
    repo = pathlib.Path(GALPAO).parent
    achados = []
    for pj in sorted((repo / "projects").glob("*/project-spec.json")):
        try:
            txt = pj.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "fck_protendida" in txt or "fckj_protensao" in txt:
            achados.append(pj.parent.name)
    if achados:
        lados.append("projects com as chaves declaradas (muda o piso): %r"
                     % (achados,))
    assert not lados, "casos G133 reprovam:\n" + "\n".join(lados)


def test_06_producao_le_a_fonte_unica():
    """Um assert so (anti-tautologia, convencao 5): cada modulo de producao
    que declara a protensao importa a fonte unica; sem parametro o
    comportamento e o piso declarado; invalida levanta em toda porta."""
    import inspect

    lados = []
    for mod in ("galpao_concreto", "viga_protendida", "desenho_concreto",
                "techdraw_concreto", "pacote_legal", "galpao_adapter",
                "entregaveis_projeto"):
        src = inspect.getsource(sys.modules.get(mod) or __import__(mod))
        if "protensao_fck_g133" not in src:
            lados.append("%s nao importa a fonte unica" % mod)
    # sem parametro = piso declarado (o comportamento de hoje, dito).
    if "nao declarado" not in lente.linha_protensao(
            {"fck_usado": 30e3, "fck_origem": lente.ORIGEM_FCK_PISO,
             "fck_explicito": False, "fckj_usado": 30e3,
             "fckj_origem": lente.ORIGEM_FCKJ_PISO, "fckj_explicito": False}):
        lados.append("sem parametro a linha devia dizer o piso")
    # invalida levanta em toda porta.
    for fn in (lambda: lente.resolver_entrada({"fck": 30e3,
                                               "fck_protendida": "XYZ"}, 30e3),
               lambda: lente.fckj_protensao_de_spec({"fckj_protensao": "XYZ"}),
               lambda: _galpao_concreto(fck_protendida="XYZ"),
               lambda: lente.protensao_da_entrega(
                   {"fck_usado": 30e3, "fck_origem": lente.ORIGEM_FCK_PISO,
                    "fck_explicito": False, "fckj_usado": 30e3,
                    "fckj_origem": lente.ORIGEM_FCKJ_PISO,
                    "fckj_explicito": False},
                   {"fck_protendida": 40e3})):
        try:
            fn()
            lados.append("porta invalida nao levantou: %r" % (fn,))
        except ValueError:
            pass
    bom = lente.confere_pecas({"a": lente.linha_protensao(
        {"fck_usado": 40e3, "fck_origem": lente.ORIGEM_FCK_DECLARADO,
         "fck_explicito": True, "fckj_usado": 40e3,
         "fckj_origem": lente.ORIGEM_FCKJ_DECLARADO, "fckj_explicito": True}),
        "b": lente.linha_protensao(None)})
    if not bom["OK"]:
        lados.append("linhas da fonte deviam passar no proprio portao")
    ruim = lente.confere_pecas({"a": "concreto sem protensao declarada"})
    if ruim["OK"]:
        lados.append("texto sem declaracao devia reprovar")
    assert not lados, "fontes G133 reprovam:\n" + "\n".join(lados)


def test_07_entrega_declara_o_que_a_conta_usou():
    """Um assert so (G131): o calculado vence; declarado x usado divergentes
    levanta; sem concreto / sem protendida / casa declaram o terceiro valor;
    o galpao real com as chaves no topo sai declarado na conta e no pacote."""
    import copy
    import json

    sys.path.insert(0, HERE)
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    lados = []
    calc = {"fck_usado": 30e3, "fck_origem": lente.ORIGEM_FCK_PISO,
            "fck_explicito": False, "fckj_usado": 30e3,
            "fckj_origem": lente.ORIGEM_FCKJ_PISO, "fckj_explicito": False}
    try:
        lente.protensao_da_entrega(calc, {"fck": 30e3, "fck_protendida": 40e3})
        lados.append("declarado 40 x usado 30 devia levantar")
    except ValueError:
        pass
    try:
        lente.protensao_da_entrega(calc, {"fck": 30e3, "fckj_protensao": 35e3})
        lados.append("fckj declarado x usado divergentes deviam levantar")
    except ValueError:
        pass
    sem_conc = lente.protensao_do_turnkey({"executadas": ["aco"],
                                           "disciplinas": {}})
    if sem_conc["origem"] != lente.ORIGEM_SEM_PROTENSAO:
        lados.append("turnkey sem concreto devia ser sem protendida: %r"
                     % (sem_conc,))
    casa = lente.linha_protensao(lente.protensao_da_entrega(None, {}, "casa"))
    if lente.contem_declaracao_protensao(casa)["origem"] != \
            lente.ORIGEM_SEM_PROTENSAO:
        lados.append("casa devia declarar sem protendida: %r" % casa)
    try:
        lente.protensao_do_turnkey({"executadas": ["concreto"],
                                    "disciplinas": {"concreto": {"raw": {
                                        "tipo_viga": "protendida",
                                        "viga_prot": {"b": 0.2}}}}})
        lados.append("protendida sem resolvido devia levantar")
    except ValueError:
        pass
    # rodada real do galpao com as chaves no topo: conta + pacote declaram.
    register_builtin_adapters()
    base = g102._spec("galpao")
    spec = copy.deepcopy(base)
    spec["fck_protendida"] = 40e3
    spec["fckj_protensao"] = 40e3
    import tempfile
    destino = os.path.join(tempfile.mkdtemp(), "galpao-prot-decl")
    run_project(spec, destino, {"generate_ifc": False, "generate_2d": False})
    with open(os.path.join(destino, "project-run.json"), encoding="utf-8") as fh:
        registro = json.load(fh)
    # o calculado viaja no pacote-legal.json (do resultado do turnkey).
    with open(os.path.join(destino, "documentos", "pacote-legal.json"),
              encoding="utf-8") as fh:
        pac_json = json.load(fh)
    prot_gate = pac_json.get("protensao") or {}
    if not (prot_gate.get("fck_usado") == 40e3
            and prot_gate.get("fckj_usado") == 40e3):
        lados.append("conta nao recebeu o declarado do topo: %r" % (prot_gate,))
    _gates_conc = registro["disciplines"]["concreto"]["gates"]
    if _gates_conc.get("viga_cobertura", {}).get("tipo") != "protendida":
        lados.append("rodada real devia cair na protendida: %r"
                     % (_gates_conc.get("viga_cobertura"),))
    for rel in ("documentos/pacote-legal.md",
                "drawings-svg/concreto-armacao.svg",
                "drawings-svg/concreto-formas.svg"):
        p = os.path.join(destino, rel)
        if not os.path.isfile(p):
            lados.append("artefato ausente na rodada real: %s" % rel)
            continue
        with open(p, encoding="utf-8") as fh:
            texto = fh.read()
        c = lente.contem_declaracao_protensao(texto)
        if c["origem"] != "declarado" or "40 MPa" not in texto:
            lados.append("%s nao declara o C40 que a conta usou: %r"
                         % (rel, c))
    assert not lados, "entrega G133 reprova:\n" + "\n".join(lados)
