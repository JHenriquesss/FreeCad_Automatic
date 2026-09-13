"""G127 - a fct,m em fonte unica: onze copias viram uma conta.

Medido (G125, remedido no G127 antes da migracao, 2026-09-13): a expressao
do ramo alto (`2,12 ln (1 + 0,11 fck)`) estava escrita em 11 linhas de 10
modulos (base_chumbador:99, estaca_profunda:388, fissuracao_nbr6118:59,
fundacao_sapata:681, laje_concreto:441, pilar_concreto:407,
piso_industrial:73, premoldado_nbr9062:125, viga_baldrame:47,78,
viga_protendida:70), todas com o limiar `fck <= 50` e o mesmo numero.

Entregue:
  1. FONTE (fctm_nbr6118_g127.py, producao): fctm_MPa (MPa -> MPa) + fctm
     (kN/m2 -> kN/m2) + fctk_inf/sup nas duas unidades, com a faixa
     declarada (C20 a C90; fora dela levanta, nunca satura).
  2. FIACAO: os 10 modulos chamam a fonte (a do seu sistema de unidades).
  3. PORTAO: so a fonte contem o literal (copia nova fora dela reprova);
     os 10 chamam a fonte (leitura por conta propria ou nome morto
     reprova).

Nao fazer do goal: a conta e a da edicao 2014 (a mesma das copias). Virar
para a 2023 e decisao do usuario (G123); o test_06 prova que ela nao
entrou.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import fctm_nbr6118_g127 as fonte

import base_chumbador as bc
import estaca_profunda as ep
import fundacao_sapata as fs
import laje_concreto as lj
import pilar_concreto as pc
import piso_industrial as pi
import viga_baldrame as vb
import viga_protendida as vp
import fissuracao_nbr6118 as fis
import premoldado_nbr9062 as pm

# fcks do aceite, em MPa.
FCKS = (20.0, 50.0, 55.0, 60.0, 90.0)

# Literais medidos na funcao real ANTES da migracao (2026-09-13).
FCTM_MPA_ESPERADO = {
    20.0: 2.2104188991842317,
    50.0: 4.071626424892359,
    55.0: 4.140418547667256,
    60.0: 4.299674284259645,
    90.0: 5.064177113178408,
}


def _literal_fctm_mpa(fck_MPa):
    if fck_MPa <= 50.0:
        return 0.3 * fck_MPa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.11 * fck_MPa)


def test_01_fonte_bate_literal_nos_cinco_fcks():
    """Um assert so: a fonte devolve o literal bit a bit nos 5 fcks, nas
    duas unidades, e fctk_inf/sup sao 0,7/1,3 da fctm."""
    quebras = []
    for fck in FCKS:
        esp = _literal_fctm_mpa(fck)
        if fonte.fctm_MPa(fck) != esp:
            quebras.append("fctm_MPa(%r)=%r, literal %r"
                           % (fck, fonte.fctm_MPa(fck), esp))
        if fonte.fctm_MPa(fck) != FCTM_MPA_ESPERADO[fck]:
            quebras.append("fctm_MPa(%r) fugiu do literal medido" % (fck,))
        if fonte.fctm(fck * 1000.0) != esp * 1000.0:
            quebras.append("fctm(%r) != literal*1000" % (fck,))
        if fonte.fctk_inf_MPa(fck) != 0.7 * esp:
            quebras.append("fctk_inf_MPa(%r) != 0,7*fctm" % (fck,))
        if fonte.fctk_sup_MPa(fck) != 1.3 * esp:
            quebras.append("fctk_sup_MPa(%r) != 1,3*fctm" % (fck,))
        if fonte.fctk_inf(fck * 1000.0) != 0.7 * esp * 1000.0:
            quebras.append("fctk_inf(%r) != 0,7*fctm*1000" % (fck,))
        if fonte.fctk_sup(fck * 1000.0) != 1.3 * esp * 1000.0:
            quebras.append("fctk_sup(%r) != 1,3*fctm*1000" % (fck,))
    assert not quebras, "fonte divergiu do literal:\n" + "\n".join(quebras)


def _fctm_equivalente_por_modulo(fck):
    """Um escalar por modulo, proporcional a fctm (para comparar com o
    antes medido). fck em MPa."""
    fck_kn = fck * 1000.0
    return {
        "fissuracao": fis.fctm(fck_kn),
        "premoldado": pm._fctm(fck_kn),
        "viga_protendida": vp._fctm(fck_kn),
        "piso": pi.resistencia_flexao_projeto(fck),
        "fundacao_fbd": fs.comprimento_ancoragem(20.0, fck)["fbd_MPa"],
        "estaca_fctm": ep.ancoragem_tirante(0.020, fck_kn, 500e3)["fctm_MPa"],
        "base_fctd": bc.ancoragem_chumbador(10.0, 0.020, fck_kn, 250e3)["fctd"],
        "pilar_vc": pc.verifica_cortante_pilar(100.0, 0.20, 0.45, fck_kn,
                                               500e3)["Vc"],
        "laje_vrd1": lj.cortante_laje(50.0, 1.0, 0.10, fck_kn, 5e-4)["V_rd1"],
        "baldrame_vc": vb._verifica_cortante(100.0, 0.20, 0.45, fck_kn,
                                             500e3)["Vc"],
        "baldrame_mr": vb._flecha_alvenaria(0.20, 0.50, 0.45, 4.0, 10.0,
                                            fck_kn, 4e-4, False)["Mr"],
    }


# Antes medido (mesmos casos, funcoes reais, pre-migracao): o depois tem de
# ser bit a bit igual. Arredondados (fundacao/estaca) vao com o `round` que
# a funcao aplica; os demais vao com o float cheio.
ANTES_MEDIDO = {
    20.0: {"fissuracao": 2210.4188991842316, "premoldado": 2210.4188991842316,
           "viga_protendida": 2210.4188991842316, "piso": 1.5788706422744514,
           "fundacao_fbd": 2.49, "estaca_fctm": 2.21,
           "base_fctd": 1105.2094495921158, "pilar_vc": 59.68131027797427,
           "laje_vrd1": 58.02349610358608, "baldrame_vc": 59.68131027797427,
           "baldrame_mr": 27.63},
    50.0: {"fissuracao": 4071.626424892359, "premoldado": 4071.626424892359,
           "viga_protendida": 4071.626424892359, "piso": 2.9083045892088277,
           "fundacao_fbd": 4.58, "estaca_fctm": 4.07,
           "base_fctd": 2035.8132124461795, "pilar_vc": 109.93391347209369,
           "laje_vrd1": 106.88019365342444, "baldrame_vc": 109.93391347209369,
           "baldrame_mr": 50.9},
    55.0: {"fissuracao": 4140.418547667256, "premoldado": 4140.418547667256,
           "viga_protendida": 4140.418547667256, "piso": 2.957441819762326,
           "fundacao_fbd": 4.66, "estaca_fctm": 4.14,
           "base_fctd": 2070.209273833628, "pilar_vc": 111.7913007870159,
           "laje_vrd1": 108.68598687626546, "baldrame_vc": 111.7913007870159,
           "baldrame_mr": 51.76},
    60.0: {"fissuracao": 4299.674284259645, "premoldado": 4299.674284259645,
           "viga_protendida": 4299.674284259645, "piso": 3.0711959173283176,
           "fundacao_fbd": 4.84, "estaca_fctm": 4.3,
           "base_fctd": 2149.8371421298225, "pilar_vc": 116.09120567501043,
           "laje_vrd1": 112.86644996181568, "baldrame_vc": 116.09120567501043,
           "baldrame_mr": 53.75},
    90.0: {"fissuracao": 5064.177113178408, "premoldado": 5064.177113178408,
           "viga_protendida": 5064.177113178408, "piso": 3.617269366556006,
           "fundacao_fbd": 5.7, "estaca_fctm": 5.06,
           "base_fctd": 2532.088556589204, "pilar_vc": 136.732782055817,
           "laje_vrd1": 132.9346492209332, "baldrame_vc": 136.732782055817,
           "baldrame_mr": 63.3},
}


def test_02_modulos_batem_antes_bit_a_bit():
    """Um assert so: cada modulo, nos 5 fcks, devolve o antes medido com
    `==` (nao aproximado: a migracao nao pode mover um ulp)."""
    quebras = []
    for fck in FCKS:
        agora = _fctm_equivalente_por_modulo(fck)
        for nome, antes in sorted(ANTES_MEDIDO[fck].items()):
            if agora[nome] != antes:
                quebras.append("%s C%.0f: agora %r != antes %r"
                               % (nome, fck, agora[nome], antes))
    assert not quebras, "modulo moveu numero:\n" + "\n".join(quebras)


def test_03_vermelho_copia_nova_fora_da_fonte(tmp_path):
    """tmp_path, nunca o repo: formula colada fora da fonte unica acusa;
    so em comentario nao e conta; fonte sem a conta acusa; intacto verde."""
    quebras = []
    real = fonte.confere_copias()
    if not real["OK"]:
        quebras.append("arvore real: %r" % (real,))
    (tmp_path / "modulo_novo.py").write_text(
        "import math" + chr(10)
        + "fctm = 2.12 * math.log(1.0 + 0.11 * 60.0)" + chr(10),
        encoding="utf-8")
    (tmp_path / "fctm_nbr6118_g127.py").write_text(
        "x = 1" + chr(10), encoding="utf-8")
    copiado = fonte.confere_copias(str(tmp_path))
    if "modulo_novo" not in copiado["copias"] or copiado["OK"]:
        quebras.append("copia fora da fonte nao acusou: %r" % (copiado,))
    (tmp_path / "modulo_novo.py").write_text(
        "# fctm = 2.12 * math.log(1.0 + 0.11 * fck)" + chr(10),
        encoding="utf-8")
    if fonte.copias_fctm_fora_da_fonte(str(tmp_path)):
        quebras.append("comentario contou como conta")
    if not fonte.confere_copias(str(tmp_path))["fonte_apagada"]:
        quebras.append("fonte sem a conta nao acusou")
    assert not quebras, "G127:" + chr(10) + chr(10).join(quebras)


def test_04_uso_os_dez_chamam_a_fonte(tmp_path):
    """Um assert so: no repo real os 10 modulos + a lente chamam a fonte
    (uso esperado); em tmp_path, chamada nova sem triagem (extra) e nome
    morto (faltando) acusam."""
    quebras = []
    real = fonte.confere_uso_fctm()
    if not real["OK"]:
        quebras.append("arvore real: %r" % (real,))
    if sorted(real["tem"]) != sorted(fonte.LEITORES_ESPERADOS):
        quebras.append("leitores=%r, esperado=%r"
                       % (real["tem"], sorted(fonte.LEITORES_ESPERADOS)))
    (tmp_path / "fctm_nbr6118_g127.py").write_text("x = 1" + chr(10),
                                                   encoding="utf-8")
    (tmp_path / "modulo_novo.py").write_text(
        "import fctm_nbr6118_g127" + chr(10), encoding="utf-8")
    extra = fonte.confere_uso_fctm(str(tmp_path))
    if "modulo_novo.py" not in extra["extras"] or extra["OK"]:
        quebras.append("leitura por conta propria nao acusou: %r" % (extra,))
    (tmp_path / "modulo_morto.py").write_text("x = 1" + chr(10),
                                              encoding="utf-8")
    morto = fonte.confere_uso_fctm(
        str(tmp_path), esperado={"fctm_nbr6118_g127.py", "modulo_novo.py",
                                 "modulo_morto.py"})
    if morto["faltando"] != ["modulo_morto.py"] or morto["OK"]:
        quebras.append("nome morto nao acusou: %r" % (morto,))
    assert not quebras, "G127:" + chr(10) + chr(10).join(quebras)


def test_05_faixa_limiar_separa_ramos_e_jovem_extrapola():
    """Um assert so: o limiar em 50 MPa separa o ramo potenciado do
    logaritmico; o fckj jovem do icamento (13,74 MPa, medido no galpao de
    concreto) usa a mesma expressao por extrapolacao declarada - travar a
    producao mudaria veredito de peca real."""
    quebras = []
    if fonte.fctm_MPa(50.0) != 0.3 * 50.0 ** (2.0 / 3.0):
        quebras.append("C50 nao usa o ramo potenciado")
    if fonte.fctm_MPa(50.0001) != 2.12 * math.log(1.0 + 0.11 * 50.0001):
        quebras.append("acima de 50 nao usa o ramo logaritmico")
    jovem = 13.739545472001577
    if fonte.fctm_MPa(jovem) != 0.3 * jovem ** (2.0 / 3.0):
        quebras.append("fckj jovem fugiu da expressao declarada")
    for fck in FCKS:
        try:
            fonte.fctm_MPa(fck)
        except ValueError:
            quebras.append("fck %r devia passar" % (fck,))
    assert not quebras, "faixa do G127:\n" + "\n".join(quebras)


def test_06_edicao_2023_nao_entrou():
    """Um assert so: nenhum dos 11 arquivos contem a conta da 2023
    (`0,1 * (fck + 8)`); a fonte segue a 2014 declarada e o caso C5 segue
    2014 < 2023."""
    quebras = []
    rx2023 = re.compile(r"0\.1\s*\*\s*\(")
    alvos = list(fonte.MODULOS_VIA_FONTE) + ["fctm_nbr6118_g127"]
    for nome in sorted(alvos):
        caminho = os.path.join(GALPAO, nome + ".py")
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for i, linha in enumerate(fh, 1):
                if rx2023.search(linha.split("#", 1)[0]):
                    quebras.append("%s:%d com conta da 2023: %r"
                                   % (nome, i, linha.strip()[:90]))
    import confronto_2014_2023_g122 as lente
    c5 = lente.caso_c5_fctm_c60()
    if abs(c5["fctm_2014_MPa"] - 4.300) > 0.005:
        quebras.append("C5 2014=%.4f, esperado 4,300" % c5["fctm_2014_MPa"])
    if not (c5["fctm_2023_MPa"] > c5["fctm_2014_MPa"]):
        quebras.append("C5: 2023 devia superar 2014")
    assert not quebras, "G127:" + chr(10) + chr(10).join(quebras)
