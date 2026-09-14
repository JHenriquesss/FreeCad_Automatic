"""G134 - a pergunta do cimento que nenhuma conta le: sai do fluxo metalico.

Medido (G131 + remedicao G134 por AST, antes de mudar): to_rodar_params
escrevia 30 chaves; 2 sem literal em rodar_galpao.py - norma_6118_edicao
(lida via edicao_de_spec, NAO morta) e cimento (ZERO leitores: grep vazio
no rodar_galpao). O rodar_galpao e o galpao METALICO (NBR 8800), sem
icamento de pre-moldado; o icamento so existe no turnkey de concreto
(entrada: project-spec topo ou turnkey.concreto, G131). A S39 conta
`p[chave] = ...` como fiado, por isso nao acusou: ela confere a escrita,
nunca a leitura.

Entregue:
  1. FONTE UNICA (chaves_to_rodar_g134.py, producao): CHAVES_ESPERADAS (29,
     sem cimento), CHAVE_REMOVIDA + MOTIVO_REMOCAO_CIMENTO (o motivo
     escrito), LEITURAS_DECLARADAS (norma_6118_edicao via
     edicao_nbr6118_g123.edicao_de_spec) + chaves_escritas_por_to_rodar /
     leituras_diretas_em_rodar / usa_leitura_declarada / chaves_sem_leitor /
     confere_censo (por AST, com `raiz` p/ injecao em tmp_path).
  2. A PERGUNTA SAI DO FLUXO METALICO: wizard sem a pergunta (resposta
     legada explicita BLOQUEIA com o motivo); ProjetoSpec sem o campo
     (legado ausente/None/"" segue OK; explicito BLOQUEIA com o caminho
     certo); to_rodar_params sem o repasse (legado que chegar ate ali
     levanta em vez de seguir morto). O cimento do project-spec do
     turnkey fica - la ele e lido (G131).
  3. PORTAO (test_01): o censo real passa (29 escritas, zero sem-leitor);
     o cimento reinjetado reprova no mesmo portao (o instrumento acusa
     por parte, convencao 7 do lote).
  4. BASELINE (test_02, nos dois sentidos): 29 chaves, motivo escrito,
     leitura declarada usada, G126 intacto (projeto_spec ainda importa a
     fonte do cimento: o legado distingue valido de desconhecido).
  5. INJECAO (test_03, tmp_path, nunca o repo): chave nova sem leitor
     reprova (extras + sem_leitor); declarada sem uso reprova; o bom passa.
  6. FLUXO (test_04, convencao 11 em cada entrada metalica): wizard,
     spec-direto e mapper bloqueiam o cimento explicito com o motivo; sem
     ele, o params nao tem a chave e o rodar segue identico (a chave nunca
     chegava a conta: remocao byte-identica por construcao).
  7. TURNKEY (test_05, o Nao fazer do goal): o cimento do concreto segue
     lido (unidade + conta real do galpao_concreto, sem re-rodar o turnkey
     pesado do G126 test_06).
  8. FONTES (test_06, anti-tautologia): os 29 literais escritos a mao
     contra as fontes vivas (AST da producao, nao a constante da lente).

O que a lente NAO cobre: a familia condicional mont_* (escrita dinamica,
lida pelo gate de montagem; triada no D162 fora do baseline estatico);
chaves aninhadas (contrato de cada gate); valores (o G134 nao move numero
nenhum); o cimento do turnkey (fonte unica do G126).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import chaves_to_rodar_g134 as lente

# Os 29 escritos a mao (anti-tautologia do test_06: contra o AST vivo).
ESPERADAS_MAO = (
    "aguas", "baldrame", "base_fixed", "calha", "cargas", "chuva_I_mm_h",
    "creditar_cortante_mesa_inclinada", "divisa", "escada", "estaca",
    "fogo", "fu", "fundacao", "fy", "geometria", "mf_sec", "neve",
    "norma_6118_edicao", "parede", "plataforma", "ponte", "secundarios",
    "tapered", "telha", "terreno", "tipo_ligacao", "tipo_portico",
    "trelica", "vento",
)


def _respostas_min(**over):
    r = {"area_lote_m2": 1200, "span": 10, "comprimento": 20, "eave": 6,
         "v0": 40, "sigma_solo": 200, "fund_tipo": "sapata"}
    r.update(over)
    return r


def test_01_portao_censo_real_passa_e_cimento_reinjetado_reprova():
    """Um assert so (receita G97): o censo vivo passa; o cimento de volta
    reprova no mesmo portao, por parte (sem_leitor nomeia a chave)."""
    lados = []
    conf = lente.confere_censo()
    if not conf["OK"] or conf["sem_leitor"] or conf["extras"] \
            or conf["faltando"]:
        lados.append("censo real devia passar zerado: %r" % (conf,))
    if len(conf["escritas"]) != 29:
        lados.append("escritas=%d, esperado 29 (30 menos o cimento)"
                     % len(conf["escritas"]))
    if "cimento" in conf["escritas"]:
        lados.append("to_rodar_params ainda escreve cimento: %r"
                     % (conf["escritas"],))
    # O mesmo portao com o cimento de volta: acusa por parte. O repo real
    # nao escreve mais cimento, entao a prova e por construcao do portao:
    # cimento nao tem leitura direta nem declarada - qualquer escrita cai
    # em sem_leitor (o caso com escrita viva esta no test_03, em tmp_path).
    if "cimento" in lente.leituras_diretas_em_rodar() \
            or "cimento" in lente.LEITURAS_DECLARADAS:
        lados.append("cimento devia seguir sem leitura direta e sem "
                     "declarada (senao a remocao nao acusaria): %r" % (
                         lente.LEITURAS_DECLARADAS,))
    # A leitura declarada e o que salva a norma: sem ela, a norma cai.
    if not lente.usa_leitura_declarada():
        lados.append("edicao_de_spec devia estar importada e chamada no "
                     "rodar_galpao (leitura declarada da norma)")
    assert not lados, "portao G134 reprova:\n" + "\n".join(lados)


def test_02_baseline_nos_dois_sentidos():
    """Baseline congelado: 29 chaves, motivo escrito, declarada usada,
    G126 intacto (projeto_spec ainda importa a fonte do cimento)."""
    lados = []
    if tuple(sorted(lente.CHAVES_ESPERADAS)) != ESPERADAS_MAO:
        lados.append("CHAVES_ESPERADAS mudou: so no conhecido %r, so no "
                     "vivo %r"
                     % (sorted(set(ESPERADAS_MAO) - set(lente.CHAVES_ESPERADAS)),
                        sorted(set(lente.CHAVES_ESPERADAS) - set(ESPERADAS_MAO))))
    if lente.CHAVE_REMOVIDA != "cimento":
        lados.append("CHAVE_REMOVIDA=%r, esperado 'cimento'"
                     % (lente.CHAVE_REMOVIDA,))
    for trecho in ("rodar_galpao", "zero leitores", "turnkey"):
        if trecho not in lente.MOTIVO_REMOCAO_CIMENTO:
            lados.append("motivo sem o trecho %r: %r"
                         % (trecho, lente.MOTIVO_REMOCAO_CIMENTO))
    if dict(lente.LEITURAS_DECLARADAS) != {
            "norma_6118_edicao": ("edicao_nbr6118_g123", "edicao_de_spec")}:
        lados.append("LEITURAS_DECLARADAS mudou: %r"
                     % (lente.LEITURAS_DECLARADAS,))
    # G126 intacto: o legado metalico ainda distingue valido de invalido.
    import cimento_nbr6118_g126 as cim
    if not cim.confere_uso_cimento()["OK"]:
        lados.append("G126 quebrou: %r" % (cim.confere_uso_cimento(),))
    if not cim.confere_defaults()["OK"]:
        lados.append("defaults de cimento reapareceram: %r"
                     % (cim.confere_defaults(),))
    assert not lados, "baseline G134 reprova:\n" + "\n".join(lados)


_FAKE_SPEC = '''\
def to_rodar_params(spec):
    p = {}
    p["alpha"] = 1
    p.setdefault("beta", 2)
    %s
    return p
'''

_FAKE_RODAR_BOM = '''\
from edicao_nbr6118_g123 import edicao_de_spec as _ed
def rodar(params):
    ed = _ed(params)
    return {"alpha": params["alpha"], "beta": params.get("beta"), "ed": ed}
'''

_FAKE_RODAR_SEM_DECLARADA = '''\
def rodar(params):
    return {"alpha": params["alpha"], "beta": params.get("beta"),
            "norma": "norma_6118_edicao sem leitor de verdade"}
'''


def _par_fake(tmp_path, extra_spec="", rodar=None):
    (tmp_path / "projeto_spec.py").write_text(
        _FAKE_SPEC % extra_spec, encoding="utf-8")
    (tmp_path / "rodar_galpao.py").write_text(
        rodar if rodar is not None else _FAKE_RODAR_BOM, encoding="utf-8")


def test_03_vermelho_por_injecao_em_tmp_path(tmp_path):
    """tmp_path, nunca o repo: chave nova sem leitor reprova; declarada
    sem uso reprova; cimento reinjetado reprova; o bom passa."""
    lados = []
    # O bom passa: escritas == esperadas, tudo lido.
    _par_fake(tmp_path)
    bom = lente.confere_censo(tmp_path, esperado={"alpha", "beta"})
    if not bom["OK"]:
        lados.append("par limpo devia passar: %r" % (bom,))
    # Chave nova sem leitor: extras + sem_leitor disparam juntos.
    _par_fake(tmp_path, extra_spec='p["gama"] = 3')
    ruim = lente.confere_censo(tmp_path, esperado={"alpha", "beta"})
    if ruim["OK"]:
        lados.append("chave nova sem leitor devia reprovar: %r" % (ruim,))
    if ruim["extras"] != ["gama"] or ruim["sem_leitor"] != ["gama"]:
        lados.append("nova sem triagem devia cair em extras E sem_leitor: "
                     "%r" % (ruim,))
    # Nome morto: esperado que sumiu do codigo tambem e vermelho.
    _par_fake(tmp_path)
    morta = lente.confere_censo(tmp_path, esperado={"alpha", "beta", "zelda"})
    if morta["OK"] or morta["faltando"] != ["zelda"]:
        lados.append("nome morto devia reprovar em faltando: %r" % (morta,))
    # Cimento reinjetado no par fake: sem_leitor nomeia.
    _par_fake(tmp_path, extra_spec='p["cimento"] = spec.get("cimento")')
    cim = lente.confere_censo(tmp_path, esperado={"alpha", "beta", "cimento"})
    if cim["OK"] or cim["sem_leitor"] != ["cimento"]:
        lados.append("cimento sem leitor devia reprovar: %r" % (cim,))
    # Declarada sem uso: string em mensagem NAO e leitura (o rigor do
    # G126) - a norma com literal solto mas sem o call cai em sem_leitor.
    _par_fake(tmp_path,
              extra_spec='p["norma_6118_edicao"] = spec.get("x")',
              rodar=_FAKE_RODAR_SEM_DECLARADA)
    sem_uso = lente.chaves_sem_leitor(tmp_path)
    if sem_uso != ["norma_6118_edicao"]:
        lados.append("norma com literal solto mas sem call devia ser "
                     "sem_leitor (string em mensagem nao e leitura): %r"
                     % (sem_uso,))
    # E com o call declarado, a mesma escrita passa.
    _par_fake(tmp_path,
              extra_spec='p["norma_6118_edicao"] = spec.get("x")',
              rodar=_FAKE_RODAR_BOM)
    com_uso = lente.chaves_sem_leitor(tmp_path)
    if "norma_6118_edicao" in com_uso:
        lados.append("norma com call declarado devia passar: %r" % (com_uso,))
    if not tmp_path.is_dir():
        lados.append("tmp_path sumiu")
    assert not lados, "injecao G134 reprova:\n" + "\n".join(lados)


def test_04_fluxo_metalico_sem_cimento_em_cada_entrada(tmp_path):
    """Convencao 11 no fluxo metalico: wizard, spec-direto e mapper. Sem o
    cimento, o params nao tem a chave e o rodar segue identico (a chave
    nunca chegava a conta: remocao byte-identica por construcao)."""
    import wizard as WZ
    import projeto_spec as PS

    lados = []
    # A pergunta saiu do formulario.
    chaves = [q[0] for q in WZ.PERGUNTAS]
    if "cimento" in chaves:
        lados.append("wizard ainda pergunta o cimento: %r" % (chaves,))
    # Sem resposta, o spec nasce sem a chave e valida.
    s = WZ.construir_spec(_respostas_min())
    if "cimento" in s:
        lados.append("construir_spec ainda escreve s[cimento]: %r" % (s.get("cimento"),))
    val = PS.validar(s)
    if not val["ok"]:
        lados.append("spec sem cimento devia validar: %r" % (val["faltando"],))
    if "cimento" in PS.novo():
        lados.append("PS.novo ainda traz a chave cimento")
    # Sem ele, o params nao tem a chave.
    p = PS.to_rodar_params(s)
    if "cimento" in p:
        lados.append("to_rodar_params ainda repassa cimento")
    # Legado ausente/None/"" segue OK (specs antigos continuam validos).
    for legado in (None, ""):
        s2 = WZ.construir_spec(_respostas_min())
        s2["cimento"] = legado
        v2 = PS.validar(s2)
        if any(f == "cimento" for f, _d in v2["faltando"]):
            lados.append("legado %r devia seguir OK: %r" % (legado, v2["faltando"]))
        try:
            p2 = PS.to_rodar_params(s2)
        except ValueError as exc:
            lados.append("legado %r nao devia levantar no mapper: %s" % (legado, exc))
        else:
            if "cimento" in p2:
                lados.append("legado %r vazou para o params" % (legado,))
    # Cada entrada com valor explicito BLOQUEIA com o motivo escrito.
    try:
        WZ.construir_spec(_respostas_min(cimento="CPII"))
        lados.append("wizard com cimento explicito devia levantar")
    except ValueError as exc:
        if "G134" not in str(exc) and "turnkey" not in str(exc).lower():
            lados.append("wizard levantou sem o motivo: %r" % (exc,))
    s3 = WZ.construir_spec(_respostas_min())
    s3["cimento"] = "CPII"
    v3 = PS.validar(s3)
    if "cimento" not in [f for f, _d in v3["faltando"]]:
        lados.append("spec-direto com CPII devia faltar em cimento: %r"
                     % (v3["faltando"],))
    else:
        msg = dict(v3["faltando"]).get("cimento", "")
        if "G134" not in msg and "turnkey" not in msg.lower():
            lados.append("validar sem o motivo escrito: %r" % (msg,))
    s4 = WZ.construir_spec(_respostas_min())
    s4["cimento"] = "XYZ"
    if "cimento" not in [f for f, _d in PS.validar(s4)["faltando"]]:
        lados.append("spec-direto com XYZ devia bloquear")
    # O rodar metalico segue de pe sem a chave (tmp_path, nunca o repo):
    # calcula e devolve o veredito global.
    import rodar_galpao as R
    res = R.rodar(p, str(tmp_path / "rodar-sem-cimento"))
    if not isinstance(res, dict) or res.get("atende_global") not in (
            True, False):
        lados.append("rodar sem cimento sem veredito global: %r"
                     % (type(res),))
    assert not lados, "fluxo G134 reprova:\n" + "\n".join(lados)


def test_05_turnkey_continua_lendo_o_cimento():
    """O Nao fazer do goal: o cimento do concreto segue lido (unidade +
    conta real do galpao_concreto; o turnkey pesado e do G126 test_06)."""
    import cimento_nbr6118_g126 as cim
    import galpao_concreto as gc

    lados = []
    if cim.cimento_de_spec({"cimento": "CPII"}) != "CPII":
        lados.append("cimento_de_spec parou de ler o turnkey")
    if cim.resolver_cimento(None)["origem"] != cim.ORIGEM_PISO:
        lados.append("piso do turnkey mudou")
    base = {"vao": 10.0, "comprimento": 40.0, "pe_direito": 6.0,
            "n_porticos": 7, "v0": 40.0, "cat": "IV", "classe": "B",
            "G_roof": 0.30, "Q_roof": 0.25, "fck": 30e3,
            "sigma_solo_adm": 250.0, "travamento_longitudinal": "topo"}
    r_sem = gc.rodar(dict(base))
    r_com = gc.rodar(dict(base, cimento="CPII"))
    if r_sem["cimento"]["origem"] != cim.ORIGEM_PISO:
        lados.append("concreto sem cimento sem piso: %r" % (r_sem["cimento"],))
    if (r_com["cimento"]["cimento"], r_com["cimento"]["origem"]) != \
            ("CPII", cim.ORIGEM_DECLARADO):
        lados.append("concreto com CPII sem declarado: %r" % (r_com["cimento"],))
    if abs(float(r_sem["icamento"]["fckj_MPa"]) - 13.7) > 0.05:
        lados.append("fckj do piso mudou: %.2f" % r_sem["icamento"]["fckj_MPa"])
    assert not lados, "turnkey G134 reprova:\n" + "\n".join(lados)


def test_06_fontes_producao_lidas_pela_lente():
    """Anti-tautologia (convencao 5): os 29 literais escritos a mao contra
    o AST vivo da producao; o motivo mora na fonte unica."""
    lados = []
    vivas = lente.chaves_escritas_por_to_rodar()
    if set(vivas) != set(ESPERADAS_MAO):
        lados.append("producao viva diverge dos 29 a mao: so na mao %r, "
                     "so na producao %r"
                     % (sorted(set(ESPERADAS_MAO) - set(vivas)),
                        sorted(set(vivas) - set(ESPERADAS_MAO))))
    if set(lente.CHAVES_ESPERADAS) != set(ESPERADAS_MAO):
        lados.append("constante da lente diverge dos 29 a mao")
    # A producao LE cada chave (acesso a params ou declarada usada):
    # senao e comentario (convencao 8) - a mesma acusacao que tirou o
    # cimento. String em mensagem nao conta (rigor do G126).
    diretas = lente.leituras_diretas_em_rodar()
    for chave in ESPERADAS_MAO:
        if chave in diretas:
            continue
        if chave in lente.LEITURAS_DECLARADAS and lente.usa_leitura_declarada():
            continue
        lados.append("chave %r sem leitor na producao (comentario?)" % (chave,))
    if not lente.MOTIVO_REMOCAO_CIMENTO.strip():
        lados.append("motivo vazio")
    assert not lados, "fontes G134 reprovam:\n" + "\n".join(lados)
