# ============================================================================
# test_varredura_descoberta_g43.py - G43: O DETECTOR FALA AS OUTRAS DISCIPLINAS.
# Cinco verticais nunca examinados por esta lente (eletrico, hidraulica,
# incendio, climatizacao, residencial) entram na varredura com vocabulario
# e sumidouros proprios. No espirito do G21, um zero so vale depois que o
# detector ja ficou vermelho com um caso injetado NAQUELA LINGUAGEM: cada
# disciplina tem seu par pre-fix (orfao na lingua dela) / pos-fix (limpo).
#   - test_detector_fala_eletrico: Icc_barra/fp_result (Icc, fp) x
#     dimensiona_protecao/corrige_fator_potencia.
#   - test_detector_fala_hidraulica: Q_teste/uhc_teste (Q_, UHC) x
#     diametro_agua/diametro_coletor_sat.
#   - test_detector_fala_incendio: pop_calc/vazao_hidrante (populacao, vazao
#     de hidrante) x dimensiona_populacao_deposito/dimensiona_hidrantes.
#   - test_detector_fala_climatizacao: V_ins_teste/capacidade_test x
#     dimensiona_duto/vazao_insuflamento.
#   - test_detector_fala_residencial: area_teste/perimetro_teste x
#     criterio_tomadas (NBR 5410 9.5.2).
#   - test_re_I_nao_caca_contadores: o re.I antigo casava N_ com n_cond
#     (n. de condutores), n_tomadas (n. de tomadas) e n_port/n_col
#     (contagens) - dois falsos positivos assim que a lente alcançou as
#     outras disciplinas. Case-sensitive: contadores fora, legitimos dentro.
#   - test_descoberta_g43_pina_baseline: o que a descoberta acha HOJE nas 9
#     tipologias (ordem estavel, molde G6->G7).
# ============================================================================
"""Guarda G43: prova que a descoberta fala as outras disciplinas."""

import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import varredura_descoberta as vd


def _nomes(orfaos):
    return sorted(d["variavel"] for d in orfaos)


def test_detector_fala_eletrico():
    # G21 espirito na lingua do eletrico: Icc na barra e fp calculados e
    # nunca verificados; o fix leva cada um ao seu sumidouro proprio.
    pre = (
        "def rodar(spec):\n"
        "    Icc_barra = 5000.0\n"
        "    fp_result = 0.80\n"
        "    return True\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    Icc_barra = 5000.0\n"
        "    fp_result = 0.80\n"
        "    prot = dimensiona_protecao(Icc_barra)\n"
        "    corr = corrige_fator_potencia(fp_result)\n"
        "    return prot\n"
    )
    nomes = _nomes(vd.descobrir_texto("elet_pre.py", pre))
    assert "Icc_barra" in nomes, "Icc orfa deveria ser achada: %r" % (nomes,)
    assert "fp_result" in nomes, "fp orfao deveria ser achado: %r" % (nomes,)
    assert _nomes(vd.descobrir_texto("elet_fix.py", fix)) == [], \
        "pos-fix eletrico deveria estar limpo"
    # E no repo real o eletrico segue fechado.
    reais = vd.descobrir_no_arquivo(GALPAO / "galpao_eletrico.py")
    assert reais == [], "eletrico reabriu em silencio: %r" % (reais,)


def test_detector_fala_hidraulica():
    # Vazao e UHC calculadas e nunca dimensionadas; o fix leva aos diametros.
    pre = (
        "def rodar(spec):\n"
        "    Q_teste = 2.5\n"
        "    uhc_teste = 10.0\n"
        "    return True\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    Q_teste = 2.5\n"
        "    uhc_teste = 10.0\n"
        "    dn = diametro_agua(Q_teste)\n"
        "    col = diametro_coletor_sat(uhc_teste)\n"
        "    return dn\n"
    )
    nomes = _nomes(vd.descobrir_texto("hid_pre.py", pre))
    assert "Q_teste" in nomes, "Q_ orfa deveria ser achada: %r" % (nomes,)
    assert "uhc_teste" in nomes, "UHC orfa deveria ser achada: %r" % (nomes,)
    assert _nomes(vd.descobrir_texto("hid_fix.py", fix)) == [], \
        "pos-fix hidraulico deveria estar limpo"
    reais = vd.descobrir_no_arquivo(GALPAO / "galpao_hidraulica.py")
    assert reais == [], "hidraulica reabriu em silencio: %r" % (reais,)
    reais_res = vd.descobrir_no_arquivo(GALPAO / "hidraulica_residencial.py")
    assert reais_res == [], "hidraulica residencial reabriu: %r" % (reais_res,)


def test_detector_fala_incendio():
    # Populacao e vazao de hidrante calculadas e nunca dimensionadas.
    pre = (
        "def rodar(spec):\n"
        "    pop_calc = 90.0\n"
        "    vazao_hidrante = 300.0\n"
        "    return True\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    pop_calc = 90.0\n"
        "    vazao_hidrante = 300.0\n"
        "    p = dimensiona_populacao_deposito(pop_calc)\n"
        "    h = dimensiona_hidrantes(vazao_hidrante)\n"
        "    return h\n"
    )
    nomes = _nomes(vd.descobrir_texto("inc_pre.py", pre))
    assert "pop_calc" in nomes, "populacao orfa deveria ser achada: %r" % (nomes,)
    assert "vazao_hidrante" in nomes, "vazao orfa deveria ser achada: %r" % (nomes,)
    assert _nomes(vd.descobrir_texto("inc_fix.py", fix)) == [], \
        "pos-fix incendio deveria estar limpo"
    reais = vd.descobrir_no_arquivo(GALPAO / "galpao_seguranca_incendio.py")
    assert reais == [], "incendio reabriu em silencio: %r" % (reais,)


def test_detector_fala_climatizacao():
    # Vazao de insuflamento e capacidade calculadas e nunca levadas ao duto.
    pre = (
        "def rodar(spec):\n"
        "    V_ins_teste = 1000.0\n"
        "    capacidade_test = 50.0\n"
        "    return True\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    V_ins_teste = 1000.0\n"
        "    capacidade_test = 50.0\n"
        "    d = dimensiona_duto(V_ins_teste)\n"
        "    v = vazao_insuflamento(capacidade_test)\n"
        "    return d\n"
    )
    nomes = _nomes(vd.descobrir_texto("cli_pre.py", pre))
    assert "V_ins_teste" in nomes, "V_ins orfa deveria ser achada: %r" % (nomes,)
    assert "capacidade_test" in nomes, \
        "capacidade orfa deveria ser achada: %r" % (nomes,)
    assert _nomes(vd.descobrir_texto("cli_fix.py", fix)) == [], \
        "pos-fix climatizacao deveria estar limpo"
    reais = vd.descobrir_no_arquivo(GALPAO / "galpao_climatizacao.py")
    assert reais == [], "climatizacao reabriu em silencio: %r" % (reais,)


def test_detector_fala_residencial():
    # Geometria que governa a NBR 5410 9.5.2 calculada e nunca conferida.
    pre = (
        "def rodar(spec):\n"
        "    area_teste = 50.0\n"
        "    perimetro_teste = 30.0\n"
        "    return True\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    area_teste = 50.0\n"
        "    perimetro_teste = 30.0\n"
        "    c = criterio_tomadas(area_teste, perimetro_teste)\n"
        "    return c\n"
    )
    nomes = _nomes(vd.descobrir_texto("res_pre.py", pre))
    assert "area_teste" in nomes, "area orfa deveria ser achada: %r" % (nomes,)
    assert "perimetro_teste" in nomes, \
        "perimetro orfao deveria ser achado: %r" % (nomes,)
    assert _nomes(vd.descobrir_texto("res_fix.py", fix)) == [], \
        "pos-fix residencial deveria estar limpo"
    reais = vd.descobrir_no_arquivo(GALPAO / "arquitetura_residencial.py")
    assert reais == [], "residencial reabriu em silencio: %r" % (reais,)


def test_re_I_nao_caca_contadores():
    # Os dois falsos positivos do re.I: N_ casava n_cond (n. de condutores
    # pluviais) e n_tomadas (n. de tomadas) - contagens, nao grandezas.
    fonte = (
        "def rodar(spec):\n"
        "    n_cond = 4\n"
        "    n_tomadas = 8\n"
        "    n_port = 5\n"
        "    return n_cond\n"
    )
    nomes = _nomes(vd.descobrir_texto("contadores.py", fonte))
    assert "n_cond" not in nomes, "n_cond e contador, nao esforco: %r" % (nomes,)
    assert "n_tomadas" not in nomes, "n_tomadas e contador: %r" % (nomes,)
    assert "n_port" not in nomes, "n_port e contador: %r" % (nomes,)
    # E os legitimos continuam pegos sem o re.I (caixa exata ja listada).
    fonte_ok = (
        "def rodar(spec):\n"
        "    N_base = 1.0\n"
        "    n_terca = 2.0\n"
        "    r_escada = 3.0\n"
        "    V_w_k = 4.0\n"
        "    return True\n"
    )
    nomes_ok = _nomes(vd.descobrir_texto("legitimos.py", fonte_ok))
    for var in ("N_base", "n_terca", "r_escada", "V_w_k"):
        assert var in nomes_ok, \
            "%s legitimo deveria continuar achado: %r" % (var, nomes_ok)


def test_descoberta_g43_pina_baseline():
    # O que a descoberta acha HOJE nas 9 tipologias (ordem estavel). Se um
    # orfao novo aparecer, este teste fica vermelho: ou vira verificacao,
    # ou vira ilha declarada para o proximo fix (molde G6->G7). Se um orfao
    # sumir, a baseline diminui junto - nunca em silencio.
    assert vd.chaves_varridas() == [], \
        "baseline G43 mudou: %r" % (vd.chaves_varridas(),)


def test_tipologias_g43_existem():
    for tipologia in ("eletrico", "hidraulica", "incendio",
                      "climatizacao", "residencial"):
        assert tipologia in vd.TIPOLOGIAS, \
            "tipologia G43 %s sumiu da varredura" % tipologia
        for arq in vd.TIPOLOGIAS[tipologia]:
            assert (GALPAO / arq).is_file(), \
                "orquestrador %s da tipologia %s sumiu" % (arq, tipologia)
