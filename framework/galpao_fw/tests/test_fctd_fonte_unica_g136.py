"""G136 - a fctd em fonte unica: sete copias viram uma conta.

Medido (remedicao por AST + regex antes de mudar, 2026-09-13): a conta
`0,7 * fctm / gamma_c` estava escrita em 7 sitios de producao
(base_chumbador:99 via `GC`, estaca_profunda:387, fundacao_sapata:683,
laje_concreto:440, pilar_concreto:440, viga_baldrame:46,
viga_protendida:127), todas com o mesmo numero. A Tab. 12.1 foi lida na
pagina renderizada da F016 (NBR 6118:2014 p. 71, 12.4.1): normais 1,4 /
especiais ou de construcao 1,2 / excepcionais 1,2 - o que as 7 gravavam
e o da combinacao normal; nenhum caso do repo chama estes modulos em
outra combinacao.

Entregue:
  1. FONTE (fctd_nbr6118_g136.py, producao): fctd_MPa (MPa -> MPa) +
     fctd (kN/m2 -> kN/m2, deriva da MPa) + gamma_c como parametro com
     o normal por omissao + os tres valores da Tab. 12.1 declarados.
  2. FIACAO: os 7 modulos chamam a fonte (cada um na primitiva da ordem
     que ja usava, para o numero sair bit a bit).
  3. PORTAO: so a fonte contem o literal (copia nova fora dela
     reprova); os 7 chamam a fonte (leitura por conta propria ou nome
     morto reprova).

Nao fazer do goal: mudar o gamma_c de caso nenhum (test_07 trava por
AST que nenhum dos 7 passa gamma_c: todos usam a omissao = normal).
"""
import ast
import hashlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fctd_nbr6118_g136 as fonte
import fctm_nbr6118_g127 as fonte_fctm

import base_chumbador as bc
import estaca_profunda as ep
import fundacao_sapata as fs
import laje_concreto as lj
import pilar_concreto as pc
import viga_baldrame as vb
import viga_protendida as vp

# fcks do aceite, em MPa.
FCKS = (20.0, 50.0, 55.0, 60.0, 90.0)

# Literais da fctd medidos na funcao real ANTES da migracao (2026-09-13,
# `0,7 * fctm / 1,4` sobre a fctm do G127, combinacao normal Tab. 12.1).
FCTD_MPA_ESPERADO = {
    20.0: 1.1052094495921159,
    50.0: 2.0358132124461794,
    55.0: 2.070209273833628,
    60.0: 2.1498371421298224,
    90.0: 2.532088556589204,
}
FCTD_KN_ESPERADO = {
    20.0: 1105.2094495921158,
    50.0: 2035.8132124461795,
    55.0: 2070.209273833628,
    60.0: 2149.8371421298225,
    90.0: 2532.088556589204,
}


def _fctm_literal(fck_MPa):
    """A fctm do G127 recomputada a mao (os dois ramos da 8.2.5)."""
    if fck_MPa <= 50.0:
        return 0.3 * fck_MPa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.11 * fck_MPa)


def test_01_fonte_bate_literal_e_tab_12_1():
    """Um assert so: a fonte devolve o literal bit a bit nos 5 fcks, nas
    duas unidades, com gamma_c normal por omissao; e os tres valores da
    Tab. 12.1 (F016 p. 71, 12.4.1) declarados sao os lidos na pagina."""
    quebras = []
    if fonte.GAMMA_C_NORMAL != 1.4:
        quebras.append("GAMMA_C_NORMAL=%r, Tab. 12.1 normais = 1,4"
                       % (fonte.GAMMA_C_NORMAL,))
    if fonte.GAMMA_C_ESPECIAL_CONSTRUCAO != 1.2:
        quebras.append("especial/construcao devia ser 1,2")
    if fonte.GAMMA_C_EXCEPCIONAL != 1.2:
        quebras.append("excepcional devia ser 1,2")
    for fck in FCKS:
        esp = 0.7 * _fctm_literal(fck) / 1.4
        if fonte.fctd_MPa(fck) != esp:
            quebras.append("fctd_MPa(%r)=%r, literal %r"
                           % (fck, fonte.fctd_MPa(fck), esp))
        if fonte.fctd_MPa(fck) != FCTD_MPA_ESPERADO[fck]:
            quebras.append("fctd_MPa(%r) fugiu do literal medido" % (fck,))
        if fonte.fctd(fck * 1000.0) != FCTD_KN_ESPERADO[fck]:
            quebras.append("fctd(%r) fugiu do literal medido" % (fck,))
        if fonte.fctd(fck * 1000.0) != fonte.fctd_MPa(fck) * 1000.0:
            quebras.append("fctd(%r) != fctd_MPa*1000" % (fck,))
        if fonte.fctd_MPa(fck) != fonte_fctm.fctk_inf_MPa(fck) / 1.4:
            quebras.append("fctd_MPa(%r) != fctk,inf/1,4" % (fck,))
        if fonte.fctd(fck * 1000.0, 1.2) != (
                fonte_fctm.fctk_inf_MPa(fck) / 1.2 * 1000.0):
            quebras.append("gamma_c explicito(%r) nao divide" % (fck,))
    assert not quebras, "fonte divergiu do literal:\n" + "\n".join(quebras)


def _sondas_por_modulo(fck_MPa):
    """Um escalar por modulo, proporcional a fctd (para comparar com o
    antes). fck em MPa. Mesmos casos do ANTES_MEDIDO."""
    fck = fck_MPa * 1000.0
    return {
        "base_fctd": bc.ancoragem_chumbador(10.0, 0.020, fck, 250e3)["fctd"],
        "base_fbd": bc.ancoragem_chumbador(10.0, 0.020, fck, 250e3)["fbd"],
        "base_lb": bc.ancoragem_chumbador(10.0, 0.020, fck, 250e3)["lb"],
        "estaca_fbd": ep.ancoragem_tirante(0.020, fck, 500e3)["fbd_MPa"],
        "estaca_lb": ep.ancoragem_tirante(0.020, fck, 500e3)["lb_m"],
        "sapata_fbd": fs.comprimento_ancoragem(20.0, fck_MPa)["fbd_MPa"],
        "sapata_lb": fs.comprimento_ancoragem(20.0, fck_MPa)["lb_mm"],
        "laje_tau": lj.cortante_laje(50.0, 1.0, 0.10, fck, 5e-4)["tau_rd"],
        "laje_Vrd1": lj.cortante_laje(50.0, 1.0, 0.10, fck, 5e-4)["V_rd1"],
        "pilar_Vc": pc.verifica_cortante_pilar(100.0, 0.20, 0.45, fck,
                                              500e3)["Vc"],
        "baldrame_Vc": vb._verifica_cortante(100.0, 0.20, 0.45, fck,
                                            500e3)["Vc"],
        "prot_Vc0": vp.verifica_cortante_protendida(
            200.0, 0.05, 0.20, 0.60, 0.55, fck, 100.0, 80.0)["Vc0"],
    }


# Antes (formula antiga documentada, mesmos casos, pre-migracao): o
# depois tem de ser bit a bit igual. Arredondados (fundacao/estaca) vao
# com o `round` que a funcao aplica; os demais vao com o float cheio.
ANTES_MEDIDO = {
    20.0: {"base_fctd": 1105.2094495921158, "base_fbd": 1105.2094495921158,
           "base_lb": 0.9834846436938071, "estaca_fbd": 2.49,
           "estaca_lb": 0.874, "sapata_fbd": 2.49, "sapata_lb": 874,
           "laje_tau": 276.30236239802895, "laje_Vrd1": 58.02349610358608,
           "pilar_Vc": 59.68131027797427, "baldrame_Vc": 59.68131027797427,
           "prot_Vc0": 72.94382367307965},
    50.0: {"base_fctd": 2035.8132124461795, "base_fbd": 2035.8132124461795,
           "base_lb": 0.5339176084986069, "estaca_fbd": 4.58,
           "estaca_lb": 0.475, "sapata_fbd": 4.58, "sapata_lb": 475,
           "laje_tau": 508.95330311154487, "laje_Vrd1": 106.88019365342444,
           "pilar_Vc": 109.93391347209369, "baldrame_Vc": 109.93391347209369,
           "prot_Vc0": 134.36367202144785},
    55.0: {"base_fctd": 2070.209273833628, "base_fbd": 2070.209273833628,
           "base_lb": 0.5250466875391283, "estaca_fbd": 4.66,
           "estaca_lb": 0.467, "sapata_fbd": 4.66, "sapata_lb": 467,
           "laje_tau": 517.552318458407, "laje_Vrd1": 108.68598687626546,
           "pilar_Vc": 111.7913007870159, "baldrame_Vc": 111.7913007870159,
           "prot_Vc0": 136.63381207301944},
    60.0: {"base_fctd": 2149.8371421298225, "base_fbd": 2149.8371421298225,
           "base_lb": 0.5055994709730866, "estaca_fbd": 4.84,
           "estaca_lb": 0.449, "sapata_fbd": 4.84, "sapata_lb": 449,
           "laje_tau": 537.4592855324556, "laje_Vrd1": 112.86644996181568,
           "pilar_Vc": 116.09120567501043, "baldrame_Vc": 116.09120567501043,
           "prot_Vc0": 141.8892513805683},
    90.0: {"base_fctd": 2532.088556589204, "base_fbd": 2532.088556589204,
           "base_lb": 0.4292727120110255, "estaca_fbd": 5.7,
           "estaca_lb": 0.382, "sapata_fbd": 5.7, "sapata_lb": 382,
           "laje_tau": 633.022139147301, "laje_Vrd1": 132.9346492209332,
           "pilar_Vc": 136.732782055817, "baldrame_Vc": 136.732782055817,
           "prot_Vc0": 167.11784473488748},
}


def test_02_modulos_batem_antes_bit_a_bit():
    """Um assert so: cada modulo, nos 5 fcks, devolve o antes com `==`
    (nao aproximado: a migracao nao pode mover um ulp)."""
    quebras = []
    for fck in FCKS:
        agora = _sondas_por_modulo(fck)
        for nome, antes in sorted(ANTES_MEDIDO[fck].items()):
            if agora[nome] != antes:
                quebras.append("%s C%.0f: agora %r != antes %r"
                               % (nome, fck, agora[nome], antes))
    assert not quebras, "modulo moveu numero:\n" + "\n".join(quebras)


def test_03_vermelho_copia_nova_fora_da_fonte(tmp_path):
    """tmp_path, nunca o repo: formula colada fora da fonte unica acusa
    (literal, via GC e o desvio por fctk,inf com literal); so em
    comentario nao e conta; copia em _selftest esta fora da lente por
    declaracao (prova independente); fonte sem a conta acusa; intacto
    verde."""
    quebras = []
    real = fonte.confere_copias()
    if not real["OK"]:
        quebras.append("arvore real: %r" % (real,))
    (tmp_path / "modulo_novo.py").write_text(
        "fctm = 2.5" + chr(10)
        + "fctd = 0.7 * fctm / 1.4" + chr(10),
        encoding="utf-8")
    (tmp_path / "fctd_nbr6118_g136.py").write_text(
        "x = 1" + chr(10), encoding="utf-8")
    copiado = fonte.confere_copias(str(tmp_path))
    if "modulo_novo" not in copiado["copias"] or copiado["OK"]:
        quebras.append("copia fora da fonte nao acusou: %r" % (copiado,))
    (tmp_path / "modulo_gc.py").write_text(
        "fctd = 0.7 * fctm / GC * 1000.0" + chr(10), encoding="utf-8")
    copiado_gc = fonte.confere_copias(str(tmp_path))
    if "modulo_gc" not in copiado_gc["copias"] or copiado_gc["OK"]:
        quebras.append("copia via GC nao acusou: %r" % (copiado_gc,))
    (tmp_path / "modulo_desvio.py").write_text(
        "fctd = fctk_inf_MPa(25.0) / 1.4" + chr(10), encoding="utf-8")
    copiado_desvio = fonte.confere_copias(str(tmp_path))
    if "modulo_desvio" not in copiado_desvio["copias"]:
        quebras.append("desvio por fctk,inf nao acusou: %r"
                       % (copiado_desvio,))
    (tmp_path / "modulo_novo.py").write_text(
        "# fctd = 0.7 * fctm / 1.4" + chr(10), encoding="utf-8")
    (tmp_path / "modulo_gc.py").write_text("x = 1" + chr(10),
                                           encoding="utf-8")
    (tmp_path / "modulo_desvio.py").write_text("x = 1" + chr(10),
                                               encoding="utf-8")
    (tmp_path / "modulo_selftest.py").write_text(
        "def _selftest():" + chr(10)
        + "    fctd = 0.7 * fctm / 1.4" + chr(10),
        encoding="utf-8")
    if fonte.copias_fctd_fora_da_fonte(str(tmp_path)):
        quebras.append("comentario ou _selftest contou como conta")
    if not fonte.confere_copias(str(tmp_path))["fonte_apagada"]:
        quebras.append("fonte sem a conta nao acusou")
    assert not quebras, "G136:" + chr(10) + chr(10).join(quebras)


def test_04_uso_os_sete_chamam_a_fonte(tmp_path):
    """Um assert so: no repo real os 7 modulos chamam a fonte (uso
    esperado); em tmp_path, chamada nova sem triagem (extra) e nome
    morto (faltando) acusam."""
    quebras = []
    real = fonte.confere_uso_fctd()
    if not real["OK"]:
        quebras.append("arvore real: %r" % (real,))
    if sorted(real["tem"]) != sorted(fonte.LEITORES_ESPERADOS):
        quebras.append("leitores=%r, esperado=%r"
                       % (real["tem"], sorted(fonte.LEITORES_ESPERADOS)))
    (tmp_path / "fctd_nbr6118_g136.py").write_text("x = 1" + chr(10),
                                                   encoding="utf-8")
    (tmp_path / "modulo_novo.py").write_text(
        "import fctd_nbr6118_g136" + chr(10), encoding="utf-8")
    extra = fonte.confere_uso_fctd(str(tmp_path))
    if "modulo_novo.py" not in extra["extras"] or extra["OK"]:
        quebras.append("leitura por conta propria nao acusou: %r" % (extra,))
    (tmp_path / "modulo_morto.py").write_text("x = 1" + chr(10),
                                              encoding="utf-8")
    morto = fonte.confere_uso_fctd(
        str(tmp_path), esperado={"fctd_nbr6118_g136.py", "modulo_novo.py",
                                 "modulo_morto.py"})
    if morto["faltando"] != ["modulo_morto.py"] or morto["OK"]:
        quebras.append("nome morto nao acusou: %r" % (morto,))
    assert not quebras, "G136:" + chr(10) + chr(10).join(quebras)


def _canonico(sondas_por_fck):
    """String canonica das sondas (D158: hash do resultado inteiro)."""
    return repr(sorted((fck, sorted(sondas.items()))
                       for fck, sondas in sorted(sondas_por_fck.items())))


# Hash das sondas ANTES (mesmos casos, formula antiga): o depois tem de
# render o mesmo hash (D158: numero identico ponta a ponta, nao so por
# sonda).
HASH_ANTES = "8040018e6e1265de2f0753016ca6a5d377e7ce59b83079bc2b9c98e7a34d96c7"


def test_05_hash_do_resultado_inteiro_igual_ao_antes():
    """Um assert so (D158): o sha256 das sondas de todos os modulos nos
    5 fcks e igual ao hash do antes - a migracao nao moveu um bit em
    nenhum modulo."""
    quebras = []
    agora = {fck: _sondas_por_modulo(fck) for fck in FCKS}
    h = hashlib.sha256(_canonico(agora).encode()).hexdigest()
    if h != HASH_ANTES:
        quebras.append("hash %s != antes %s" % (h, HASH_ANTES))
    assert not quebras, "G136:" + chr(10) + chr(10).join(quebras)


def test_06_vermelho_uma_reordenacao_acusa():
    """O instrumento consegue acusar (molde D158 test_04): a mesma conta
    com UMA operacao reordenada (algebricamente igual) difere do antes
    em pelo menos um fck - o `==` do test_02 pega ulp, nao so erro
    grosso."""
    quebras = []
    dif_fctd = [fck for fck in FCKS
                if 0.7 * _fctm_literal(fck) * 1000.0 / 1.4
                != 0.7 * _fctm_literal(fck) / 1.4 * 1000.0]
    dif_vc = [fck for fck in FCKS
              if 0.6 * 1000.0 * 0.20 * 0.45 * (0.7 * _fctm_literal(fck)
                                              / 1.4)
              != 0.6 * (0.7 * _fctm_literal(fck) / 1.4) * 1000.0
              * 0.20 * 0.45]
    if not dif_fctd:
        quebras.append("trocar *1000 com /1,4 nao moveu nenhum fck")
    if not dif_vc:
        quebras.append("reordenar o Vc nao moveu nenhum fck")
    assert not quebras, "G136:" + chr(10) + chr(10).join(quebras)


def test_07_gamma_c_parametro_e_normal_nos_sete(tmp_path):
    """Um assert so (o Nao fazer do goal): gamma_c e parametro (1,2
    divide certo) e NENHUM dos 7 passa gamma_c por AST - todos usam a
    omissao = normal 1,4; o gamma_c de caso nenhum mudou."""
    import inspect
    quebras = []
    for fck in FCKS:
        if fonte.fctd_MPa(fck, 1.2) != fonte_fctm.fctk_inf_MPa(fck) / 1.2:
            quebras.append("gamma_c=1,2 nao divide em C%.0f" % (fck,))
        if fonte.fctd(fck * 1000.0, 1.2) != (
                fonte.fctd_MPa(fck, 1.2) * 1000.0):
            quebras.append("gamma_c=1,2 em kN/m2 nao deriva da MPa")
    if inspect.signature(fonte.fctd_MPa).parameters["gamma_c"].default != 1.4:
        quebras.append("omissao de fctd_MPa nao e a normal")
    if inspect.signature(fonte.fctd).parameters["gamma_c"].default != 1.4:
        quebras.append("omissao de fctd nao e a normal")
    for nome in fonte.MODULOS_VIA_FONTE:
        caminho = os.path.join(GALPAO, nome + ".py")
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            arvore = ast.parse(fh.read(), filename=caminho)
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Call)
                    and isinstance(no.func, ast.Attribute)
                    and no.func.attr in ("fctd", "fctd_MPa")):
                if no.keywords or len(no.args) != 1:
                    quebras.append("%s passa gamma_c: linha %d"
                                   % (nome, no.lineno))
    assert not quebras, "G136:" + chr(10) + chr(10).join(quebras)
