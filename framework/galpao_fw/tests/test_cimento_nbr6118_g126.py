"""G126 - o cimento que ninguem declarou: piso conservador, levanta, declara.

Medido (G125 + remedicao G126 na funcao real): galpao_concreto.py:262
passava spec.get("cimento", "CPV") ao icamento e premoldado_nbr9062.py:255
repetia caso.get("cimento", "CPV"), sem campo no ProjetoSpec/wizard (o
galpao SEMPRE calculava com CPV, o `s` mais favoravel: fckj(30e3,7) CPV
24562 x CPII 23364 x CPIII 20516 kN/m2); fckj_idade tinha outro default
(cimento="CPII"); desconhecido ("XYZ") virava s = 0,25 em silencio, o mesmo
numero do CPII.

Entregue:
  1. FONTE UNICA (cimento_nbr6118_g126.py, producao): CIMENTOS_VALIDOS,
     PISO_S = 0,38 (G6: o maior `s`), normaliza_cimento (desconhecido
     LEVANTA com a lista), resolver_cimento (ausente = piso, com a origem
     dita), cimento_de_spec (sem default silencioso), linha_cimento (o que
     a folha e o memorial dizem), contem_declaracao_cimento/confere_pecas
     (peca sem declaracao reprova), defaults_de_cimento/confere_defaults
     (nenhum default CPV/CPII sobrando, por AST) e
     arquivos_que_importam_cimento/confere_uso_cimento (ninguem le por
     conta propria).
  2. PISO CONSERVADOR DECLARADO (nao bloqueio): ausente usa o maior `s` e
     a folha e o memorial dizem isso; desconhecido levanta em toda porta.
     Nao escolhe o cimento do projeto (piso nao e palpite).
  3. FIACAO: premoldado.fckj_idade (cimento=None) e verifica_icamento_pilar
     (sem get com CPV; devolve cimento/cimento_origem/s_usado),
     galpao_concreto.rodar (resolve do spec, viaja no resultado) e
     edicao_nbr6118_g123.s_cimento (ausente = piso; desconhecido levanta;
     S_PADRAO_DESCONHECIDO removido).
  4. DECLARACAO na folha e no memorial: desenho_concreto (2 SVG, bloco no
     rodape), galpao_concreto.relatorio_pt (+ executivo_concreto.memorial,
     que o compoe), techdraw_concreto notas e pacote_legal markdown.
  5. ENTRADA: ProjetoSpec.cimento (opcional, ausente = piso dito; invalido
     bloqueia) + wizard (pergunta opcional) + repasse em to_rodar_params.
  6. PORTAO (test_01): as pecas reais declaram; sem declaracao reprova.
  7. BASELINE (test_02, nos dois sentidos): 6 cimentos, piso 0,38, 8
     leitores, zero defaults.
  8. INJECAO (test_03, tmp_path, nunca o repo): spec sem cimento nao sai
     com CPV; string invalida levanta em toda porta; default novo acusa.
  9. CASOS (test_04): os casos do repo antes/depois na funcao REAL
     (nenhum vira veredito; os numeros caem) + fronteira que vira fissura.
 10. FONTES (test_05, anti-tautologia): a producao LE a fonte unica; sem
     parametro = piso declarado; invalida levanta.

O que a lente NAO cobre: os valores de `s` (fonte unica da edicao); a
regra C60+ da 2023+Em1 (mora no s_cimento); outros verticais; o PDF do
memorial (a declaracao mora no memorial em texto, que o portao confere).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import cimento_nbr6118_g126 as lente


def _galpao_concreto(**kw):
    import galpao_concreto as gc
    base = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}
    base.update(kw)
    return gc.rodar(base)


def _pecas_reais():
    """As pecas que o cliente recebe, emitidas de verdade (piso: sem cimento)."""
    import desenho_concreto as dc
    import pacote_legal as pl
    import executivo_concreto as ex
    import galpao_concreto as gc
    import techdraw_concreto as tc

    r = _galpao_concreto()
    svg_arm = dc.prancha_armacao_svg(r)
    svg_for = dc.planta_formas_svg(r)
    pac = pl.gerar_pacote(["concreto"])
    md = pl.markdown(pac)
    mem = ex.memorial(r)
    rel = gc.relatorio_pt(r)
    cfg = tc.config_de_spec(
        {"spec": {"vao": 10.0, "comprimento": 40.0, "H": 6.0, "s": 5.0,
                  "n_porticos": 7, "fck_MPa": 30.0},
         "pilar": {"hx": 0.5, "hy": 0.3, "As_cm2": 10.0, "taxa_pct": 0.6},
         "viga": {"b": 0.25, "h": 0.6, "As_inf_cm2": 5.0,
                  "arr_inf": {"phi": 16.0, "n": 3},
                  "arr_sup": {"phi": 10.0, "n": 2}},
         "gates": {"pilar": {"secao": "30x50"},
                   "viga_cobertura": {"secao": "25x60"}},
         "sapata": {"aprovado": [2.0, 2.0, 0.5]},
         "tipo_fundacao": "sapata"},
        "dummy.FCStd", "/tmp")
    notas = "\n".join(cfg["notas"])
    return {"desenho_concreto.prancha_armacao_svg": svg_arm,
            "desenho_concreto.planta_formas_svg": svg_for,
            "pacote_legal.markdown": md,
            "executivo_concreto.memorial": mem,
            "galpao_concreto.relatorio_pt": rel,
            "techdraw_concreto.notas": notas,
            "_resultado": r}


def test_01_portao_pecas_reais_declaram_e_sem_declaracao_reprova():
    """Um assert so (receita G97): toda peca real declara o cimento do fckj;
    a mesma peca sem a declaracao reprova no mesmo portao (o instrumento
    acusa por parte, convencao 7 do lote)."""
    pecas = _pecas_reais()
    reais = {k: v for k, v in pecas.items() if not k.startswith("_")}
    conf = lente.confere_pecas(reais)
    sem_nome = {n: t.replace("Cimento (NBR 6118 12.3.3", "CIMENTO REMOVIDO")
                for n, t in reais.items()}
    conf_sem = lente.confere_pecas(sem_nome)
    lados = []
    if not conf["OK"] or conf["sem_declaracao"]:
        lados.append("peca real sem declaracao de cimento: %r"
                     % (conf["sem_declaracao"],))
    for nome, rr in conf["por_peca"].items():
        if not rr["OK"]:
            lados.append("peca %r nao OK: %s" % (nome, rr["motivo"]))
        elif rr["origem"] != lente.ORIGEM_PISO:
            lados.append("peca %r sem cimento devia sair com o piso: %r"
                         % (nome, rr["origem"]))
    if conf_sem["OK"] or not conf_sem["sem_declaracao"]:
        lados.append("peca sem declaracao devia reprovar: %r" % (conf_sem,))
    if set(conf_sem["sem_declaracao"]) != set(reais):
        lados.append("acumulador sem_declaracao nao listou todas: %r"
                     % (conf_sem["sem_declaracao"],))
    # Tres aceites por folha (convencao 6) para as 2 SVG: esta certa (XML +
    # confere_folha_svg), diz o que desenha (a declaracao do cimento bate o
    # que o resultado calculou). O "sai no manifesto" e dos portoes do lote.
    import xml.etree.ElementTree as ET
    import desenho_svg_base as sb
    for nome in ("desenho_concreto.prancha_armacao_svg",
                 "desenho_concreto.planta_formas_svg"):
        svg = reais[nome]
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            lados.append("%s malformado: %s" % (nome, exc))
            continue
        c = sb.confere_folha_svg(svg)
        if not c["ok"]:
            lados.append("%s fora da folha: %s" % (nome, c["motivo"]))
    # A declaracao da folha diz o que foi calculado: sem cimento no spec, o
    # resultado viaja com o piso.
    if pecas["_resultado"]["cimento"]["origem"] != lente.ORIGEM_PISO:
        lados.append("resultado sem cimento devia viajar com o piso: %r"
                     % (pecas["_resultado"]["cimento"],))
    assert not lados, "portao G126 reprova:\n" + "\n".join(lados)


def test_02_baseline_nos_dois_sentidos():
    """Baseline congelado: 6 cimentos, piso 0,38 (CPIII/CPIV), 8 leitores,
    zero defaults. Nada some nem nasce em silencio."""
    lados = []
    if tuple(lente.CIMENTOS_VALIDOS) != ("CPI", "CPII", "CPIII", "CPIV",
                                         "CPV", "CPV-ARI"):
        lados.append("CIMENTOS_VALIDOS=%r, esperado os 6 da 12.3.3"
                     % (lente.CIMENTOS_VALIDOS,))
    if abs(lente.PISO_S - 0.38) > 1e-12:
        lados.append("PISO_S=%r, esperado 0,38 (o maior `s`)" % (lente.PISO_S,))
    if lente.PISO_ROTULO != "CPIII/CPIV":
        lados.append("PISO_ROTULO=%r" % (lente.PISO_ROTULO,))
    if lente.PREFIXO_LINHA != "Cimento (NBR 6118 12.3.3":
        lados.append("PREFIXO_LINHA mudou: %r" % (lente.PREFIXO_LINHA,))
    if lente.MARCA_DECLARADO != "(declarado no projeto)":
        lados.append("MARCA_DECLARADO mudou: %r" % (lente.MARCA_DECLARADO,))
    if lente.MARCA_PISO != "piso conservador s=0,38":
        lados.append("MARCA_PISO mudou: %r" % (lente.MARCA_PISO,))
    esp = {"cimento_nbr6118_g126.py", "edicao_nbr6118_g123.py",
           "premoldado_nbr9062.py", "galpao_concreto.py",
           "desenho_concreto.py", "techdraw_concreto.py",
           "pacote_legal.py", "projeto_spec.py",
           # G131: topo -> payload do concreto; pacote do resultado.
           "galpao_adapter.py", "entregaveis_projeto.py"}
    if set(lente.LEITORES_ESPERADOS) != esp:
        lados.append("LEITORES_ESPERADOS mudou: so no conhecido %r, so no "
                     "vivo %r"
                     % (sorted(esp - set(lente.LEITORES_ESPERADOS)),
                        sorted(set(lente.LEITORES_ESPERADOS) - esp)))
    uso = lente.confere_uso_cimento()
    if not uso["OK"] or uso["extras"] or uso["faltando"]:
        lados.append("uso real fora do baseline: extras=%r faltando=%r"
                     % (uso["extras"], uso["faltando"]))
    dflt = lente.confere_defaults()
    if not dflt["OK"] or dflt["defaults"]:
        lados.append("default de cimento sobrando: %r" % (dflt["defaults"],))
    assert not lados, "baseline G126 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: spec sem cimento nao sai com CPV; string
    invalida levanta em toda porta; default novo acusa. O bom fica verde."""
    import galpao_concreto as gc
    import premoldado_nbr9062 as pm

    lados = []
    # O bom passa: declarado e piso declaram, cada um com a sua marca.
    bom = lente.confere_pecas({"a": lente.linha_cimento("CPII"),
                               "b": lente.linha_cimento(None)})
    if not bom["OK"] or bom["sem_declaracao"]:
        lados.append("caso bom devia passar: %r" % (bom,))
    if lente.contem_declaracao_cimento(
            lente.linha_cimento("CPII"))["origem"] != lente.ORIGEM_DECLARADO:
        lados.append("linha declarada sem origem certa")
    if lente.contem_declaracao_cimento(
            lente.linha_cimento(None))["origem"] != lente.ORIGEM_PISO:
        lados.append("linha do piso sem origem certa")
    # Spec sem cimento NAO sai com CPV: o numero e o do piso (igual ao
    # CPIII explicito, diferente do CPV).
    r_sem = _galpao_concreto()
    f_sem = float(pm.fckj_idade(30e3, 7))
    f_piso = float(pm.fckj_idade(30e3, 7, cimento="CPIII"))
    f_cpv = float(pm.fckj_idade(30e3, 7, cimento="CPV"))
    if abs(f_sem - f_piso) > 1e-9:
        lados.append("sem cimento devia ser piso: %.1f vs %.1f"
                     % (f_sem, f_piso))
    if abs(f_sem - f_cpv) < 1.0:
        lados.append("sem cimento saiu com CPV: %.1f" % (f_sem,))
    if r_sem["icamento"]["cimento"] is not None:
        lados.append("icamento sem cimento devia viajar com None: %r"
                     % (r_sem["icamento"]["cimento"],))
    if r_sem["icamento"]["cimento_origem"] != lente.ORIGEM_PISO:
        lados.append("icamento sem cimento sem origem do piso: %r"
                     % (r_sem["icamento"]["cimento_origem"],))
    # Defaults novos acusam em tmp_path (o .get que virava CPV e o param
    # que virava CPII); o limpo passa.
    (tmp_path / "limpo.py").write_text("x = 1\n", encoding="utf-8")
    if not lente.confere_defaults(tmp_path)["OK"]:
        lados.append("dir limpo devia passar: %r"
                     % (lente.confere_defaults(tmp_path),))
    (tmp_path / "sujo.py").write_text(
        "def f(spec):\n"
        "    return spec.get(\"cimento\", \"CPV\")\n"
        "def g(fck, t, cimento=\"CPII\"):\n"
        "    return fck\n", encoding="utf-8")
    ruim = lente.confere_defaults(tmp_path)
    if ruim["OK"]:
        lados.append("default novo devia reprovar: %r" % (ruim,))
    formas = sorted(d["forma"] for d in ruim["defaults"])
    if formas != ['get("cimento", "CPV")', 'param cimento="CPII"']:
        lados.append("scan nao achou os 2 defaults: %r" % (ruim["defaults"],))
    # Uso: probe em tmp_path acusa extra; o esperado vazio com dir vazio passa.
    (tmp_path / "probe.py").write_text(
        "import cimento_nbr6118_g126\n", encoding="utf-8")
    tem = lente.arquivos_que_importam_cimento(tmp_path)
    if tem != {"probe.py"}:
        lados.append("scan em tmp_path nao isolou: %r" % (tem,))
    extra = lente.confere_uso_cimento(tmp_path, esperado=set())
    if extra["OK"] or extra["extras"] != ["probe.py"]:
        lados.append("extras nao disparou: %r" % (extra,))
    # String invalida levanta em TODA porta (nunca vira 0,25).
    import edicao_nbr6118_g123 as ed
    base_ica = {"L": 8.0, "b": 0.40, "h": 0.40, "As": 12.0,
                "fck": 30e3, "t_dias": 3}
    for fn in (lambda: lente.normaliza_cimento("XYZ"),
               lambda: lente.resolver_cimento("XYZ"),
               lambda: lente.cimento_de_spec({"cimento": "XYZ"}),
               lambda: pm.fckj_idade(30e3, 7, cimento="XYZ"),
               lambda: pm.verifica_icamento_pilar(
                   dict(base_ica, cimento="XYZ")),
               lambda: gc.rodar(dict(_spec_galpao(), cimento="XYZ")),
               lambda: ed.s_cimento(None, "XYZ", 30e3)):
        try:
            fn()
            lados.append("cimento invalido devia levantar: %r" % (fn,))
        except ValueError as exc:
            if "CPV-ARI" not in str(exc):
                lados.append("erro sem a lista dos validos: %r" % (exc,))
    # Entrada malformada grita (nao devolve OK sobre lixo: saturacao).
    try:
        lente.confere_pecas(None)
        lados.append("pecas None devia levantar TypeError")
    except TypeError:
        pass
    try:
        lente.normaliza_cimento(None)
        lados.append("normaliza(None) devia levantar (ausencia nao e "
                     "cimento invalido: use resolver_cimento)")
    except ValueError:
        pass
    if not tmp_path.is_dir():
        lados.append("tmp_path sumiu")
    assert not lados, "injecao G126 reprova:\n" + "\n".join(lados)


def _spec_galpao():
    return {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}


def test_04_casos_do_repo_antes_e_depois_na_funcao_real():
    """Um assert so: os casos do repo sem cimento, antes (CPV, o default que
    ninguem declarou) e depois (piso), na MESMA funcao real. Nenhum vira
    veredito no repo (o OK e do aco; a fissura informa) - os numeros caem;
    a fronteira L=12 prova que o instrumento acusa quando ha o que acusar
    (convencao 7: acusar por parte)."""
    import premoldado_nbr9062 as pm

    lados = []
    # fckj(30e3, 7): o numero do goal, antes x depois.
    if abs(float(pm.fckj_idade(30e3, 7, cimento="CPV")) - 24561.9) > 0.5:
        lados.append("CPV mudou: %.1f" % pm.fckj_idade(30e3, 7, "CPV"))
    if abs(float(pm.fckj_idade(30e3, 7)) - 20515.8) > 0.5:
        lados.append("piso mudou: %.1f" % pm.fckj_idade(30e3, 7))
    if abs(float(pm.fckj_idade(30e3, 7)) - float(
            pm.fckj_idade(30e3, 7, cimento="CPIII"))) > 1e-9:
        lados.append("piso devia igualar o CPIII explicito")
    casos = [
        # (nome, caso, fckj_antes, fckj_depois, fiss_antes, fiss_depois,
        #  ok_antes, ok_depois)
        ("ica8/selftest", {"L": 8.0, "b": 0.40, "h": 0.40, "As": 12.0,
                            "fck": 30e3, "fyk": 500e3, "t_dias": 3},
         19.9, 13.7, False, False, True, True),
        ("ica10/ponto-otimo", {"L": 10.0, "b": 0.30, "h": 0.60, "As": 10.0,
                                "fck": 30e3, "t_dias": 5},
         22.8, 17.8, False, False, True, True),
        ("ica14/pilar-longo", {"L": 14.0, "b": 0.20, "h": 0.30, "As": 2.0,
                                "fck": 30e3, "t_dias": 2, "a_pega": 0.0},
         17.3, 10.6, True, True, False, False),
        ("galpao10", None, 19.9, 13.7, False, False, True, True),
        ("galpao15", None, 19.9, 13.7, False, False, True, True),
    ]
    for nome, caso, fa, fd, fia, fid, oka, okd in casos:
        if caso is None:
            vao = 10.0 if nome == "galpao10" else 15.0
            a = _galpao_concreto(vao=vao, cimento="CPV")["icamento"]
            d = _galpao_concreto(vao=vao)["icamento"]
            oka_a, okd_d = (_galpao_concreto(vao=vao, cimento="CPV")
                            ["gates"]["icamento"]["OK"],
                            _galpao_concreto(vao=vao)
                            ["gates"]["icamento"]["OK"])
        else:
            a = pm.verifica_icamento_pilar(dict(caso, cimento="CPV"))
            d = pm.verifica_icamento_pilar(dict(caso))
            oka_a, okd_d = a["OK"], d["OK"]
        if abs(a["fckj_MPa"] - fa) > 0.05 or abs(d["fckj_MPa"] - fd) > 0.05:
            lados.append("%s fckj %.1f->%.1f, esperado %.1f->%.1f"
                         % (nome, a["fckj_MPa"], d["fckj_MPa"], fa, fd))
        if (a["fissura"], d["fissura"]) != (fia, fid):
            lados.append("%s fissura %r->%r, esperado %r->%r"
                         % (nome, a["fissura"], d["fissura"], fia, fid))
        if (oka_a, okd_d) != (oka, okd):
            lados.append("%s OK %r->%r, esperado %r->%r"
                         % (nome, oka_a, okd_d, oka, okd))
    # Fronteira (fora do repo, para provar que acusa): L=12 vira fissura.
    fa = pm.verifica_icamento_pilar({"L": 12.0, "b": 0.40, "h": 0.40,
                                     "As": 12.0, "fck": 30e3, "fyk": 500e3,
                                     "t_dias": 3, "cimento": "CPV"})
    fd = pm.verifica_icamento_pilar({"L": 12.0, "b": 0.40, "h": 0.40,
                                     "As": 12.0, "fck": 30e3, "fyk": 500e3,
                                     "t_dias": 3})
    if (fa["fissura"], fd["fissura"]) != (False, True):
        lados.append("fronteira L=12 devia virar fissura: %r->%r"
                     % (fa["fissura"], fd["fissura"]))
    assert not lados, "casos G126 divergiram:\n" + "\n".join(lados)


def test_05_fontes_producao_le_fonte_unica_e_sem_parametro_e_piso():
    """Anti-tautologia (convencao 5): literais escritos a mao contra as
    fontes vivas; a producao LE a fonte unica (o numero MUDA com o cimento:
    constante medida que ninguem le e comentario - convencao 8); sem o
    parametro o comportamento e o piso DECLARADO; a entrada declara sem
    inventar."""
    import edicao_nbr6118_g123 as ed
    import premoldado_nbr9062 as pm
    import projeto_spec as PS

    lados = []
    # Uma fonte so: o S da producao e o da edicao; o piso e o maior `s`.
    if dict(pm.S_CIMENTO) != dict(ed.S_CIMENTO_2014):
        lados.append("S_CIMENTO da producao diverge da fonte unica")
    if abs(max(pm.S_CIMENTO.values()) - lente.PISO_S) > 1e-12:
        lados.append("piso devia ser o maior `s`: %r" % (pm.S_CIMENTO,))
    if set(lente.CIMENTOS_VALIDOS) != set(pm.S_CIMENTO):
        lados.append("identidade da lente diverge da tabela: %r vs %r"
                     % (lente.CIMENTOS_VALIDOS, sorted(pm.S_CIMENTO)))
    # A producao LE: o mesmo caso muda com o cimento (senao e comentario).
    f_cpv = float(pm.fckj_idade(30e3, 7, cimento="CPV"))
    f_cpiii = float(pm.fckj_idade(30e3, 7, cimento="CPIII"))
    if abs(f_cpv - 24561.9) > 0.5 or abs(f_cpiii - 20515.8) > 0.5:
        lados.append("producao nao le o cimento: %.1f/%.1f" % (f_cpv, f_cpiii))
    if not f_cpv > f_cpiii:
        lados.append("CPV devia superar o CPIII aos 7 d")
    # Sem o parametro, o comportamento e o piso E a folha diz qual e.
    f_sem = float(pm.fckj_idade(30e3, 7))
    if abs(f_sem - f_cpiii) > 1e-9:
        lados.append("sem parametro devia ser piso: %.1f vs %.1f"
                     % (f_sem, f_cpiii))
    if lente.MARCA_PISO not in lente.linha_cimento(None):
        lados.append("linha sem cimento esconde o piso: %r"
                     % (lente.linha_cimento(None),))
    if "nao declarado" not in lente.linha_cimento(None):
        lados.append("linha sem cimento esconde a ausencia: %r"
                     % (lente.linha_cimento(None),))
    if lente.MARCA_DECLARADO not in lente.linha_cimento("cpii"):
        lados.append("linha declarada sem marca: %r"
                     % (lente.linha_cimento("cpii"),))
    # A entrada declara sem inventar: ProjetoSpec opcional, invalido
    # bloqueia, wizard repassa cru.
    if PS.novo()["cimento"] is not None:
        lados.append("ProjetoSpec.cimento devia nascer None (opcional)")
    s = PS.novo()
    s["cimento"] = "CPII"
    if any(p == "cimento" for p, _d in PS.validar(s)["faltando"]):
        lados.append("cimento valido nao devia faltar")
    s["cimento"] = "XYZ"
    if not any(p == "cimento" for p, _d in PS.validar(s)["faltando"]):
        lados.append("cimento invalido devia bloquear no validar")
    import wizard as WZ
    base_r = dict(area_lote_m2=1200, span=10, comprimento=20, eave=6,
                  v0=40, sigma_solo=200, fund_tipo="sapata")
    if WZ.construir_spec(base_r)["cimento"] is not None:
        lados.append("wizard sem resposta devia dar None (piso dito)")
    if WZ.construir_spec(dict(base_r, cimento="CPV"))["cimento"] != "CPV":
        lados.append("wizard devia repassar o cimento cru")
    if not PS.validar(WZ.construir_spec(
            dict(base_r, cimento="CPV")))["ok"]:
        lados.append("wizard com CPV devia validar")
    assert not lados, "fontes G126 reprovam:\n" + "\n".join(lados)


def test_06_entrega_declara_o_cimento_que_a_conta_usou(tmp_path):
    """G131 (auditoria do G126), parte de onde o dado e PRODUZIDO: medido
    em rodada real, o calculo lia o cimento do payload `turnkey.concreto` e
    o pacote lia do topo do projeto - CPII no topo saia "CPII (declarado)"
    no pacote com a conta no piso s=0,38, e o contrario com CPII no
    payload; a casa afirmava "piso conservador no icamento" sem icamento.
    Um assert so: a fonte da entrega levanta na divergencia; casa e sem
    concreto declaram que nao ha icamento; o galpao real com CPII no topo
    sai CPII na conta, nas 2 folhas e no pacote; topo x payload diferentes
    falham a rodada com o motivo escrito."""
    import copy
    import json

    sys.path.insert(0, HERE)
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    nl = chr(10)
    lados = []
    # A fonte da entrega: declarado x usado divergentes levanta.
    for calc, spec in (({"cimento": "CPII", "origem": lente.ORIGEM_DECLARADO},
                        {"cimento": "CPIII"}),
                       (lente.resolver_cimento(None), {"cimento": "CPII"})):
        try:
            lente.cimento_da_entrega(calc, spec)
            lados.append("declarado %r x usado %r devia levantar"
                         % (spec, calc))
        except ValueError:
            pass
    casa = lente.linha_cimento(lente.cimento_da_entrega(None, {}, "casa"))
    if lente.contem_declaracao_cimento(casa)["origem"] != \
            lente.ORIGEM_SEM_ICAMENTO or lente.MARCA_PISO in casa:
        lados.append("casa devia declarar sem icamento, sem piso: %r" % casa)
    sem_conc = lente.cimento_do_turnkey({"executadas": ["aco"],
                                         "disciplinas": {}})
    if sem_conc["origem"] != lente.ORIGEM_SEM_ICAMENTO:
        lados.append("turnkey sem concreto devia ser sem icamento: %r"
                     % (sem_conc,))
    try:
        lente.cimento_do_turnkey({"executadas": ["concreto"],
                                  "disciplinas": {"concreto": {"raw": {}}}})
        lados.append("concreto executado sem cimento resolvido devia levantar")
    except ValueError:
        pass

    # Rodada real do galpao: CPII no topo chega a conta, as folhas e o pacote.
    register_builtin_adapters()
    base = g102._spec("galpao")
    spec = copy.deepcopy(base)
    spec["cimento"] = "CPII"
    destino = str(tmp_path / "galpao-cpii-topo")
    run_project(spec, destino, {"generate_ifc": False, "generate_2d": False})
    with open(os.path.join(destino, "project-run.json"), encoding="utf-8") as fh:
        registro = json.load(fh)
    ic = registro["disciplines"]["concreto"]["gates"]["icamento"]
    if (ic.get("cimento"), ic.get("cimento_origem")) != \
            ("CPII", lente.ORIGEM_DECLARADO):
        lados.append("conta nao recebeu o CPII do topo: %r"
                     % ((ic.get("cimento"), ic.get("cimento_origem")),))
    for rel in ("documentos/pacote-legal.md",
                "drawings-svg/concreto-armacao.svg",
                "drawings-svg/concreto-formas.svg"):
        with open(os.path.join(destino, rel), encoding="utf-8") as fh:
            texto = fh.read()
        c = lente.contem_declaracao_cimento(texto)
        if c["origem"] != lente.ORIGEM_DECLARADO or "CPII" not in texto:
            lados.append("%s nao declara o CPII que a conta usou: %r"
                         % (rel, c))

    # Topo x payload diferentes: a rodada falha com o motivo escrito.
    spec = copy.deepcopy(base)
    spec["cimento"] = "CPII"
    spec["turnkey"]["concreto"]["cimento"] = "CPIII"
    destino = str(tmp_path / "galpao-conflito")
    run_project(spec, destino, {"generate_ifc": False, "generate_2d": False})
    with open(os.path.join(destino, "project-run.json"), encoding="utf-8") as fh:
        texto = fh.read()
    if "diverge do payload concreto" not in texto:
        lados.append("conflito topo x payload nao ficou escrito no registro")
    if os.path.isfile(os.path.join(destino, "documentos", "pacote-legal.md")):
        lados.append("conflito topo x payload ainda emitiu pacote")
    assert not lados, "G131 (entrega x conta):" + nl + nl.join(lados)
