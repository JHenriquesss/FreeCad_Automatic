"""G123 - o projeto declara por qual edicao da norma foi calculado.

Medido (G116/G119): o framework calcula pela NBR 6118:2014 (F016) e nenhuma
folha, pacote legal ou relatorio diz isso; 2 pontos NUMERO-MUDA (13.2.5.1-b
e 12.3.3, com C4 41032 x 49124 kN/m2 no mesmo caso do repo); 2 PROCESSO-NOVO
(5.3 ATP, 20.6 marquise) que NAO entram aqui.

Entregue:
  1. FONTE UNICA (edicao_nbr6118_g123.py, producao): EDICOES_VALIDAS,
     resolver_edicao (sem default silencioso), carimbo_edicao (a folha diz
     qual e mesmo sem o parametro), s_cimento/limite_furo (os 2 numeros que
     leem a chave), contem_declaracao/confere_pecas (peca sem declaracao
     reprova), MODULOS_COM_TROCA/USO_ESPERADO (nenhum modulo troca por conta
     propria), casos C1/C4 que chamam as funcoes REAIS nas duas edicoes.
  2. CHAVE DESLIGADA: premoldado.fckj_idade e compatibilizacao.avalia_furo_viga
     ganham edicao=None (ausente = 2014, hoje); 2023+Em1 so com forma
     circular explicita no furo (retangular fica em 12 cm, conservador).
  3. CARIMBO nas pecas de concreto (pranchas SVG, techdraw_concreto, pacote,
     memorial/relatorio), sempre da fonte unica.
  4. PORTAO (test_01): as pecas reais declaram; sem declaracao reprova.
  5. BASELINE (test_02, nos dois sentidos): 2 pontos + 11 usos + 2 edicoes.
  6. INJECAO (test_03, tmp_path, nunca o repo): peca sem declaracao e uso
     extra/faltando dao vermelho; o bom fica verde (acumuladores disparam).
  7. CASOS (test_04): C1 a_confirmar/admissivel e C4 41032/49124 no mesmo
     caso do repo, pelos literais do inventario (nao reimplementa formula).
  8. FONTES (test_05, anti-tautologia): literais escritos a mao contra as
     fontes vivas + prova de que a producao LE a fonte unica (o numero muda
     com a chave); sem parametro = hoje declarado.

O que a lente NAO cobre: 2014->2023 fora dos 2 pontos (inclui 8.2.5, segue
2014 declarado); figuras/tabelas (ver imagem, regra 3); virar a chave
(decisao do usuario); ATP/marquise (gate novo, nao troca de conta).
"""
import os
import sys
import xml.etree.ElementTree as ET

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import edicao_nbr6118_g123 as lente


def _galpao_concreto():
    import galpao_concreto as gc
    return gc.rodar({"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
                     "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
                     "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
                     "sigma_solo_adm": 250.0,
                     "travamento_longitudinal": "topo"})


def _pecas_reais():
    """As pecas de concreto que o cliente recebe, emitidas de verdade."""
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
    qua = ex.relatorio_quadro_pt(r)
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
            "executivo_concreto.relatorio_quadro_pt": qua,
            "galpao_concreto.relatorio_pt": rel,
            "techdraw_concreto.notas": notas}


def test_01_portao_pecas_reais_declaram_e_sem_declaracao_reprova():
    """Um assert so (receita G97): toda peca real declara; a mesma peca sem
    o carimbo reprova no mesmo portao (o instrumento acusa)."""
    pecas = _pecas_reais()
    r = lente.confere_pecas(pecas)
    sem_nome = {n: t.replace("NBR 6118:2014", "NORMA REMOVIDA")
                .replace("NBR 6118:2023 + Emenda 1:2026", "NORMA REMOVIDA")
                .replace("2023+Em1", "NORMA REMOVIDA")
                for n, t in pecas.items()}
    r_sem = lente.confere_pecas(sem_nome)
    lados = []
    if not r["OK"] or r["sem_declaracao"]:
        lados.append("peca real sem declaracao: %r" % (r["sem_declaracao"],))
    for nome, rr in r["por_peca"].items():
        if not rr["OK"]:
            lados.append("peca %r nao OK: %s" % (nome, rr["motivo"]))
    if r_sem["OK"] or not r_sem["sem_declaracao"]:
        lados.append("peca sem carimbo devia reprovar: %r" % (r_sem,))
    if set(r_sem["sem_declaracao"]) != set(pecas):
        lados.append("acumulador sem_declaracao nao listou todas: %r"
                     % (r_sem["sem_declaracao"],))
    # Tres aceites por folha (convencao 6) para as 2 SVG: esta certa (XML +
    # confere_folha_svg), diz o que desenha (o carimbo bate a edicao do
    # resultado). O "sai no manifesto" e dos portoes do lote (G91/G102).
    import desenho_svg_base as sb
    for nome in ("desenho_concreto.prancha_armacao_svg",
                 "desenho_concreto.planta_formas_svg"):
        svg = pecas[nome]
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            lados.append("%s malformado: %s" % (nome, exc))
            continue
        c = sb.confere_folha_svg(svg)
        if not c["ok"]:
            lados.append("%s fora da folha: %s" % (nome, c["motivo"]))
    assert not lados, "portao G123 reprova:\n" + "\n".join(lados)


def test_02_baseline_nos_dois_sentidos():
    """Baseline congelado: 2 edicoes, 2 pontos, 14 usos (G125); nada some nem nasce
    em silencio (vira a chave sem triagem = vermelho)."""
    lados = []
    if tuple(lente.EDICOES_VALIDAS) != ("2014", "2023+Em1"):
        lados.append("EDICOES_VALIDAS=%r, esperado ('2014','2023+Em1')"
                     % (lente.EDICOES_VALIDAS,))
    if lente.EDICAO_PADRAO != "2014":
        lados.append("EDICAO_PADRAO=%r, esperado '2014'" % (lente.EDICAO_PADRAO,))
    if tuple(lente.MODULOS_COM_TROCA) != (("premoldado_nbr9062", "12.3.3"),
                                          ("compatibilizacao", "13.2.5.1")):
        lados.append("MODULOS_COM_TROCA=%r (esperado os 2 pontos, sem ATP nem "
                     "marquise)" % (lente.MODULOS_COM_TROCA,))
    esp = {"edicao_nbr6118_g123.py", "premoldado_nbr9062.py",
           "compatibilizacao.py", "desenho_concreto.py",
           "techdraw_concreto.py", "pacote_legal.py", "relatorio_calculo.py",
           "executivo_concreto.py", "projeto_spec.py", "galpao_concreto.py",
           "rodar_galpao.py", "entregaveis_projeto.py",
           # G125 (auditoria do G123): planta de formas, armacao e locacao
           # da fundacao da casa e do predio saiam sem declaracao (medido em
           # rodada real); os dois emissores passam a importar a fonte unica.
           "desenho_pavimento.py", "desenho_fundacao_edificio.py"}
    if set(lente.USO_ESPERADO) != esp:
        lados.append("USO_ESPERADO mudou: so no conhecido %r, so no vivo %r"
                     % (sorted(esp - set(lente.USO_ESPERADO)),
                        sorted(set(lente.USO_ESPERADO) - esp)))
    uso = lente.confere_uso_edicao()
    if not uso["OK"] or uso["extras"] or uso["faltando"]:
        lados.append("uso real fora do baseline: extras=%r faltando=%r"
                     % (uso["extras"], uso["faltando"]))
    if lente.DECLARACAO_2014 != "NBR 6118:2014":
        lados.append("DECLARACAO_2014 mudou: %r" % (lente.DECLARACAO_2014,))
    if lente.DECLARACAO_2023_EM1 != "NBR 6118:2023 + Emenda 1:2026":
        lados.append("DECLARACAO_2023_EM1 mudou: %r"
                     % (lente.DECLARACAO_2023_EM1,))
    assert not lados, "baseline G123 reprova:\n" + "\n".join(lados)


def test_03_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: peca sem declaracao e uso extra/faltando dao
    vermelho; o bom fica verde. Cada acumulador dispara de verdade."""
    lados = []
    # Acumulador sem_declaracao dispara; o intacto passa.
    bom = lente.confere_pecas({"a": lente.carimbo_edicao(None),
                               "b": lente.carimbo_edicao("2023+Em1")})
    if not bom["OK"] or bom["sem_declaracao"]:
        lados.append("caso bom devia passar: %r" % (bom,))
    ruim = lente.confere_pecas({"a": "concreto sem norma declarada"})
    if ruim["OK"] or ruim["sem_declaracao"] != ["a"]:
        lados.append("sem_declaracao nao disparou: %r" % (ruim,))
    # Uso: copia fiel em tmp_path passa; extra e faltando reprovam.
    uso_bom = lente.confere_uso_edicao()
    if not uso_bom["OK"]:
        lados.append("uso bom devia passar: %r" % (uso_bom,))
    (tmp_path / "edicao_probe.py").write_text(
        "import edicao_nbr6118_g123\n", encoding="utf-8")
    (tmp_path / "outro.py").write_text("x = 1\n", encoding="utf-8")
    tem = lente.arquivos_que_importam_edicao(tmp_path)
    if tem != {"edicao_probe.py"}:
        lados.append("scan em tmp_path nao isolou: %r" % (tem,))
    extra = lente.confere_uso_edicao(tmp_path, esperado=set())
    if extra["OK"] or extra["extras"] != ["edicao_probe.py"]:
        lados.append("extras nao disparou: %r" % (extra,))
    falt = lente.confere_uso_edicao(tmp_path,
                                     esperado={"edicao_probe.py", "falta.py"})
    if falt["OK"] or falt["ausentes"] != ["falta.py"]:
        lados.append("ausentes nao disparou: %r" % (falt,))
    # Entrada malformada grita (nao devolve OK sobre lixo: saturacao).
    try:
        lente.confere_pecas(None)
        lados.append("pecas None devia levantar TypeError")
    except TypeError:
        pass
    try:
        lente.normaliza_edicao("2023")
        lados.append("'2023' sem Emenda devia levantar (nao e edicao)")
    except ValueError:
        pass
    if not tmp_path.is_dir():
        lados.append("tmp_path sumiu")
    assert not lados, "injecao G123 reprova:\n" + "\n".join(lados)


def test_04_casos_mesmo_caso_nas_duas_edicoes():
    """Um assert so: C1 e C4 no mesmo caso do repo, pelos literais do
    inventario (G116 C1/C4). O numero 2014 vem da funcao REAL com a chave em
    2014; o 2023+Em1 vem da MESMA funcao REAL com a chave virada (a lente nao
    reimplementa formula: anti-tautologia)."""
    lados = []
    c1 = lente.caso_c1_furo_circular()
    if c1["veredito_2014"] != "a_confirmar":
        lados.append("C1 2014=%r, esperado a_confirmar" % (c1["veredito_2014"],))
    if c1["veredito_2023_em1"] != "admissivel":
        lados.append("C1 2023+Em1=%r, esperado admissivel"
                     % (c1["veredito_2023_em1"],))
    if "NBR 6118:2014" not in " ".join(c1["clausulas_2014"]):
        lados.append("C1 2014 sem fonte 2014: %r" % (c1["clausulas_2014"],))
    if "Emenda 1" not in " ".join(c1["clausulas_2023_em1"]):
        lados.append("C1 2023 sem fonte Emenda 1: %r"
                     % (c1["clausulas_2023_em1"],))
    c4 = lente.caso_c4_fckj_c60()
    if abs(c4["fckj_2014_kNm2"] - 41032) > 1.0:
        lados.append("C4 2014=%.1f, esperado 41032" % (c4["fckj_2014_kNm2"],))
    if abs(c4["fckj_2023_em1_kNm2"] - 49124) > 1.0:
        lados.append("C4 2023+Em1=%.1f, esperado 49124"
                     % (c4["fckj_2023_em1_kNm2"],))
    if not (c4["fckj_2023_em1_kNm2"] > c4["fckj_2014_kNm2"]):
        lados.append("C4: 2023+Em1 devia superar 2014")
    assert not lados, "casos G123 divergiram:\n" + "\n".join(lados)


def test_05_fontes_independentes_e_chave_desligada():
    """Anti-tautologia (convencao 5) + chave DESLIGADA sem default silencioso.

    Literais escritos a mao contra as fontes vivas; a producao LE a fonte
    unica (o numero MUDA com a chave: constante medida que ninguem le e
    comentario - convencao 8); sem o parametro o comportamento e o de hoje
    (2014) e a folha diz qual e; edicao invalida levanta."""
    import premoldado_nbr9062 as pm
    import compatibilizacao as co

    lados = []
    # Uma fonte so: o S da producao e o da lente (espelho do mesmo objeto).
    if dict(pm.S_CIMENTO) != dict(lente.S_CIMENTO_2014):
        lados.append("S_CIMENTO da producao diverge da fonte unica: %r vs %r"
                     % (pm.S_CIMENTO, lente.S_CIMENTO_2014))
    if pm.S_CIMENTO != {"CPIII": 0.38, "CPIV": 0.38, "CPI": 0.25,
                        "CPII": 0.25, "CPV": 0.20, "CPV-ARI": 0.20}:
        lados.append("S_CIMENTO mudou sem triagem: %r" % (pm.S_CIMENTO,))
    # A producao LE: o mesmo caso muda com a chave (senao e comentario).
    f14 = float(pm.fckj_idade(60e3, 7, cimento="CPIII", edicao="2014"))
    f23 = float(pm.fckj_idade(60e3, 7, cimento="CPIII", edicao="2023+Em1"))
    if abs(f14 - 41032) > 1.0 or abs(f23 - 49124) > 1.0:
        lados.append("producao nao le a chave no 12.3.3: %.0f/%.0f" % (f14, f23))
    # Chave DESLIGADA: sem o parametro, o comportamento e o de hoje.
    f_sem = float(pm.fckj_idade(60e3, 7, cimento="CPIII"))
    if abs(f_sem - f14) > 1e-9:
        lados.append("sem parametro devia ser hoje (2014): %.1f vs %.1f"
                     % (f_sem, f14))
    base = {"d_furo_mm": 125.0, "h_viga_mm": 600.0, "dist_apoio_mm": 1300.0,
            "zona_tracao": True, "dist_face_mm": 60.0, "cobrimento_mm": 25.0,
            "furo_unico": True, "armadura_seccionada": False}
    r_sem = co.avalia_furo_viga(**base)
    r_14 = co.avalia_furo_viga(edicao="2014", forma_furo="circular", **base)
    if r_sem["veredito"] != r_14["veredito"] != "a_confirmar":
        lados.append("furo sem parametro devia ser hoje: %r vs %r"
                     % (r_sem["veredito"], r_14["veredito"]))
    # Retangular em 2023+Em1 fica em 12 cm (conservador, nao 125).
    r_ret = co.avalia_furo_viga(edicao="2023+Em1", forma_furo="retangular",
                                **base)
    if r_ret["veredito"] != "a_confirmar":
        lados.append("retangular 125 em 2023+Em1 devia pedir verificacao: %r"
                     % (r_ret["veredito"],))
    # Sem a forma nao ha 125 (ausencia declarada, nunca passe maior).
    r_sf = co.avalia_furo_viga(edicao="2023+Em1", **base)
    if r_sf["veredito"] != "a_confirmar":
        lados.append("sem forma em 2023+Em1 devia ficar em 12 cm: %r"
                     % (r_sf["veredito"],))
    # O carimbo diz qual e mesmo sem o parametro (sem default silencioso).
    if "NBR 6118:2014" not in lente.carimbo_edicao(None):
        lados.append("carimbo sem parametro sem 2014: %r"
                     % (lente.carimbo_edicao(None),))
    if "nao declarada" not in lente.carimbo_edicao(None):
        lados.append("carimbo sem parametro esconde a ausencia: %r"
                     % (lente.carimbo_edicao(None),))
    if "NBR 6118:2023 + Emenda 1:2026" not in lente.carimbo_edicao("2023+Em1"):
        lados.append("carimbo 2023 sem Emenda 1: %r"
                     % (lente.carimbo_edicao("2023+Em1"),))
    # Edicao invalida levanta em toda porta (nao vira edicao em silencio).
    for fn in (lambda: lente.normaliza_edicao("2015"),
               lambda: pm.fckj_idade(60e3, 7, edicao="2015"),
               lambda: co.avalia_furo_viga(edicao="2015", **base)):
        try:
            fn()
            lados.append("edicao invalida devia levantar: %r" % (fn,))
        except ValueError:
            pass
    # 8.2.5 segue 2014 declarado (fora desta chave, G122 item 52): a fonte
    # unica nao o migra e nenhum modulo o migra por conta propria.
    if any("8.2.5" in str(m) for m in lente.MODULOS_COM_TROCA):
        lados.append("8.2.5 entrou na chave sem triagem: %r"
                     % (lente.MODULOS_COM_TROCA,))
    assert not lados, "fontes/chave reprovam:\n" + "\n".join(lados)


def test_06_folhas_de_concreto_da_casa_declaram_em_rodada_real(tmp_path):
    """G125 (auditoria do G123): o test_01 conferia so as pecas do GALPAO.
    Medido numa rodada real: planta de formas e locacao da fundacao da casa
    e do predio saiam sem declaracao (as de armacao e laje so passavam por
    citar "NBR 6118:2014" numa nota antiga, nao pelo carimbo).

    Roda a casa de verdade em tmp_path (~3 s) e confere TODA folha PE-CO do
    indice. O predio usa os mesmos emissores (desenho_pavimento,
    desenho_fundacao_edificio, desenho_concreto.gerar_planta_laje) - o
    confronto em rodada real do predio ficou medido na auditoria, nao aqui,
    pelo custo. Injecao: a mesma folha sem o carimbo reprova nomeada."""
    import casa_residencial as cr
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_indice_disco_rodada_g102 as g102
    from builtin_adapters import register_builtin_adapters
    from project_loop import run_project

    register_builtin_adapters()
    destino = tmp_path / "run-casa"
    run_project(g102._spec("casa"), str(destino), dict(g102._OPCOES["casa"]))
    pecas = {}
    quebras = []
    for codigo, arquivo in sorted(cr._PRANCHA_ARQUIVO_CASA.items()):
        if not codigo.startswith("PE-CO-"):
            continue
        caminho = destino / "drawings" / arquivo
        if not caminho.is_file():
            quebras.append("%s (%s) nao saiu na rodada" % (codigo, arquivo))
            continue
        pecas[arquivo] = caminho.read_text(encoding="utf-8")
    if len(pecas) != 4:
        quebras.append("folhas PE-CO conferidas=%d, esperado 4" % len(pecas))
    r = lente.confere_pecas(pecas)
    if not r["OK"]:
        quebras.append("sem declaracao: %r" % r["sem_declaracao"])
    alvo = "planta-formas.svg"
    if alvo in pecas:
        ruim = dict(pecas)
        ruim[alvo] = (ruim[alvo].replace(lente.DECLARACAO_2014, "NBR 6118")
                      .replace(lente.DECLARACAO_2023_EM1, "NBR 6118"))
        ri = lente.confere_pecas(ruim)
        if ri["OK"] or ri["sem_declaracao"] != [alvo]:
            quebras.append("folha sem carimbo nao acusou: %r"
                           % ri["sem_declaracao"])
    assert not quebras, "G125:" + chr(10) + chr(10).join(quebras)
