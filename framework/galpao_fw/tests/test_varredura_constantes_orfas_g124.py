"""G124 - as 51 constantes que ninguem le (remedidas: 61 no repo de hoje).

A lente (varredura_constantes_orfas.py, fonte unica) acha constantes de
modulo em MAIUSCULAS sem nenhum uso no repo (Name Load, atributo ou
from-import, em qualquer .py, incluindo tests/). A triagem das 61: 7
viraram fonte unica (rewire com numero identico), 15 residuos removidos,
39 dividas declaradas em ORFAS_TRIADAS com clausula.

Convencoes do lote: baseline nos dois sentidos (01), injecao em tmp_path
(02), instrumento tem de acusar (07, provado em 02/03/04), uma fonte so
(a lente e importada da producao, nunca copiada).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = os.path.dirname(HERE)
sys.path.insert(0, GALPAO)

import varredura_constantes_orfas as vco


ENDERECO_RE = re.compile(r"NBR|AISC|NR-|Mamede|Negrisoli|\.py:\d+")


def _escreve(tmp_path, nome, fonte):
    p = tmp_path / nome
    p.write_text(fonte, encoding="utf-8")
    return p


def test_01_baseline_repo_verde_e_fechado():
    """O repo de hoje: 39 orfas, as 39 triadas, confere OK (mensagem unica,
    receita do G97: asserts em sequencia mascaram lados independentes)."""
    res = vco.confere()
    orfas = vco.varredura()
    rel = vco.relatorio_pt(res)
    falhas = []
    if not res["OK"]:
        falhas.append("confere nao OK:\n%s" % rel)
    if len(orfas) != 39:
        falhas.append("orfas=%d, esperado 39:\n%s" % (len(orfas), rel))
    if len(vco.ORFAS_TRIADAS) != 39:
        falhas.append("triadas=%d, esperado 39" % len(vco.ORFAS_TRIADAS))
    if set(vco.chaves_orfas()) != set(vco.ORFAS_TRIADAS):
        falhas.append("chaves divergem:\n%s" % rel)
    assert not falhas, "\n---\n".join(falhas)


def test_02_vermelho_por_injecao_nova_orfa_e_verde_intacto(tmp_path):
    """O instrumento acusa (convencao 7): orfa nova em tmp_path reprova;
    modulo intacto (constante lida) passa."""
    _escreve(tmp_path, "mod_orfao.py",
             "LIMITE_NOVO_XYZ = 1.5\n\n\n"
             "def f():\n"
             "    return 1.0\n")
    res = vco.confere(raiz=tmp_path, triadas={})
    assert not res["OK"] and res["novas"] == [("mod_orfao.py", "LIMITE_NOVO_XYZ")], res
    _escreve(tmp_path, "mod_ok.py",
             "LIMITE_OK_XYZ = 1.5\n\n\n"
             "def f():\n"
             "    return LIMITE_OK_XYZ * 2.0\n")
    res2 = vco.confere(raiz=tmp_path,
                       triadas={("mod_orfao.py", "LIMITE_NOVO_XYZ"):
                                ("DIVIDA", "injetada", "NBR X")})
    assert res2["OK"], res2  # orfa triada + modulo saudavel = verde
    os.remove(str(tmp_path / "mod_orfao.py"))
    res3 = vco.confere(raiz=tmp_path, triadas={})
    assert res3["OK"], res3


def test_03_resolvida_acusa_nos_dois_sentidos(tmp_path):
    """Baseline nos dois sentidos: triada que voltou a ser lida vira nome
    morto e reprova (nao se some em silencio)."""
    _escreve(tmp_path, "mod_curado.py",
             "FOO_CURADA_XYZ = 1.5\n\n\n"
             "def f():\n"
             "    return FOO_CURADA_XYZ * 2.0\n")
    tri = {("mod_curado.py", "FOO_CURADA_XYZ"): ("DIVIDA", "m", "NBR X")}
    res = vco.confere(raiz=tmp_path, triadas=tri)
    assert not res["OK"] and res["resolvidas"] == [("mod_curado.py", "FOO_CURADA_XYZ")], res


def test_04_renomear_para_minuscula_nao_escapa_g98(tmp_path):
    """Licao do G98: renomear FOO->foo para fugir da lente mantem a suite
    vermelha (a entrada vira resolvida e pede triagem escrita)."""
    _escreve(tmp_path, "mod_renome.py",
             "foo_fugitiva_xyz = 1.5\n\n\n"
             "def f():\n"
             "    return foo_fugitiva_xyz * 2.0\n")
    tri = {("mod_renome.py", "FOO_FUGITIVA_XYZ"): ("DIVIDA", "m", "NBR X")}
    res = vco.confere(raiz=tmp_path, triadas=tri)
    assert not res["OK"] and res["resolvidas"] == [("mod_renome.py", "FOO_FUGITIVA_XYZ")], res


def test_05_isencao_sem_motivo_ou_endereco_reprova(tmp_path):
    _escreve(tmp_path, "mod_vazio.py", "X_VAZIA_XYZ = 1.0\n")
    res = vco.confere(raiz=tmp_path,
                      triadas={("mod_vazio.py", "X_VAZIA_XYZ"): ("DIVIDA", "", "")})
    assert not res["OK"] and res["sem_motivo"] and res["sem_endereco"], res


def test_06_toda_divida_tem_destino_motivo_e_endereco():
    """Nenhuma constante de norma sai da triagem sem endereco (aceite)."""
    for chave, tri in vco.ORFAS_TRIADAS.items():
        destino, motivo, endereco = tri
        assert destino == "DIVIDA", (chave, tri)
        assert (motivo or "").strip(), (chave, "motivo vazio")
        assert (endereco or "").strip(), (chave, "endereco vazio")
        assert ENDERECO_RE.search(endereco), (chave, endereco)


def test_07_fonte_unica_segura_os_7_rewires():
    """Os 7 rewires viraram leitura de verdade (a constante saiu do
    conjunto das orfas) e o numero nao mudou."""
    fonte_unica = [
        ("fundacao_sapata.py", "RHO_MIN"),
        ("alvenaria_estrutural.py", "ALTURA_VERGA_M"),
        ("fundacao_sapata.py", "_IW_RIGIDO"),
        ("madeira_nbr7190.py", "CLASSES_UMIDADE"),
        ("madeira_nbr7190.py", "CONFIGS_73"),
        ("edificio_adapter.py", "ESCOPO_FUNDACAO_ABERTO"),
        ("validacao.py", "TOL"),
    ]
    chaves = set(vco.chaves_orfas())
    for chave in fonte_unica:
        assert chave not in chaves, "%r voltou a ser orfa" % (chave,)
    import fundacao_sapata as fs
    assert fs.rho_min(25.0) == 0.0015 and fs.rho_min(20.0) == fs.RHO_MIN
    assert abs(fs.recalque_elastico(200.0, 2.0, 20e3, 0.30, 0.88)
               - 200.0 * 2.0 * (1 - 0.30 ** 2) * fs._IW_RIGIDO[1.0] / 20e3) < 1e-12
    import madeira_nbr7190 as mad
    try:
        mad._rk_madeira_aco("inexistente", 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        raise AssertionError("devia recusar config inexistente")
    except Exception as e:
        assert str(e) == ("config 'inexistente' invalida (7.3: %s)"
                          % ", ".join(mad.CONFIGS_73)), str(e)
    try:
        mad.kmod("permanente", 9)
        raise AssertionError("devia recusar umidade 9")
    except Exception as e:
        assert "classe de umidade 9 invalida (Tab.1: 1-4)" in str(e), str(e)
    import edificio_adapter as ea
    esc = ea._escopo(com_baldrame=True, com_recalque=False)
    assert esc["viga_baldrame"] == "implemented"
    assert esc["recalque_diferencial"] == "not_available"
    assert set(ea.ESCOPO_FUNDACAO_ABERTO) == {"viga_baldrame", "recalque_diferencial"}


def test_08_residuos_sumiram_do_disco():
    """Os 15 residuos removidos nao voltam sem a suite acusar (o teste 01
    quebraria por 'novas'; aqui a prova direta e a ausencia)."""
    import ast as _ast
    ausentes = [
        ("climatizacao_nbr16401.py", "TR_KCAL_H"),
        ("incendio_edificio.py", "TIPOS_ESCADA"),
        ("confronto_2014_2023_g122.py", "LIMITE_FORMULA_TABELA"),
        ("instalacao_eletrica.py", "TAXA_OCUPACAO_3MAIS"),
        ("tercas_nbr14762.py", "G_ACO"),
        ("rodar_galpao.py", "_COMB"),
        ("relatorio_calculo.py", "_SEP"),
        ("layout_eletrico_residencial.py", "_ROOM_FIELDS"),
        ("geometria_membros.py", "UNIDADE_DIMS"),
        ("geometria_membros.py", "UNIDADE_SECAO"),
        ("geometria_membros.py", "ANCORAGEM_PADRAO"),
        ("modelo_neutro.py", "UNIDADE_DIMS"),
        ("modelo_neutro.py", "UNIDADE_SECAO"),
        ("validacao_sistema_g15.py", "_SJB_SPEC_TEMPLATE"),
        ("gestao_casa.py", "_DISCIPLINAS_DA_CASA"),
    ]
    for arquivo, nome in ausentes:
        texto = open(os.path.join(GALPAO, arquivo), encoding="utf-8").read()
        arvore = _ast.parse(texto)
        definidos = {t.id for n in arvore.body
                     if isinstance(n, (_ast.Assign, _ast.AnnAssign))
                     for t in (n.targets if isinstance(n, _ast.Assign)
                               else [n.target])
                     if isinstance(t, _ast.Name)}
        assert nome not in definidos, "%s::%s voltou" % (arquivo, nome)
