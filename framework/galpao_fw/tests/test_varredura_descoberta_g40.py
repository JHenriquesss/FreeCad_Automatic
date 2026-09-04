# ============================================================================
# test_varredura_descoberta_g40.py - G40: A VARREDURA PRECISA DESCOBRIR.
# O detector generico (varredura_descoberta) percorre os orquestradores
# procurando valor calculado que nunca alcanca verificacao. Estes testes
# provam, no espirito do G21, que o detector fica VERMELHO quando o caso
# conhecido e injetado - um guarda que nunca viu o bug e hipotese.
#   - test_detector_acha_orfao_injetado: injecao sintetica em memoria.
#   - test_detector_teria_achado_G39: V_w_k pre-fix orfao, pos-fix limpo.
#   - test_detector_teria_achado_G38: r_escada sem descida orfao; o fix do
#     edificio (stair -> _descer_escada -> desc -> pilar) limpa; a casa foi o
#     irmao do G38 e o G42 a curou (mesmo caminho) - ambas limpas.
#   - test_descoberta_atual_pina_baseline: o que a descoberta acha HOJE.
#   - test_permitidos_ainda_validos: filtro de nome morto no allowlist.
# ============================================================================
"""Guarda G40: prova que a descoberta generica pega orfao injetado."""

import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import varredura_descoberta as vd


def test_detector_acha_orfao_injetado():
    # G21 espirito: injeta V_w_k calculado e nunca verificado; M_w_k chega.
    fonte = (
        "def rodar(spec):\n"
        "    V_w_k = 10.0\n"
        "    M_w_k = 5.0\n"
        "    calice = dimensiona_calice(M_w_k)\n"
        "    return calice\n"
    )
    orfaos = vd.descobrir_texto("sint_g40.py", fonte)
    nomes = sorted(d["variavel"] for d in orfaos)
    assert "V_w_k" in nomes, "injetado V_w_k orfao deveria ser achado: %r" % (nomes,)
    assert "M_w_k" not in nomes, "M_w_k alcanca verificacao: %r" % (nomes,)


def test_detector_teria_achado_G39():
    # G39: V_w_k calculado e entregue ao calice/sapata, nunca ao fuste.
    pre = (
        "def rodar(spec):\n"
        "    V_w_k = 1.0\n"
        "    M_w_k = 2.0\n"
        "    pilar = dimensiona_pilar(M_w_k)\n"
        "    return pilar\n"
    )
    fix = (
        "def rodar(spec):\n"
        "    V_w_k = 1.0\n"
        "    M_w_k = 2.0\n"
        "    pilar = dimensiona_pilar(M_w_k, V_w_k)\n"
        "    return pilar\n"
    )
    assert any(d["variavel"] == "V_w_k"
               for d in vd.descobrir_texto("gc_pre.py", pre)), \
        "pre-fix G39 deveria ser orfao"
    assert not any(d["variavel"] == "V_w_k"
                   for d in vd.descobrir_texto("gc_fix.py", fix)), \
        "pos-fix G39 deveria alcancar verificacao"
    # E no repo real o G39 segue fechado: galpao_concreto sem V orfao.
    reais = vd.descobrir_no_arquivo(GALPAO / "galpao_concreto.py")
    assert not any(d["variavel"] == "V_w_k" for d in reais), \
        "G39 reabriu em silencio: %r" % (reais,)


def test_detector_teria_achado_G38():
    # G38: escada dimensionada DEPOIS da descida, reacao nunca desce.
    pre = (
        "def rodar(spec):\n"
        "    desc = descer(pavs)\n"
        "    r_escada = dimensiona(e)\n"
        "    pilares = dimensiona_pilar_continuo(lances)\n"
        "    return pilares\n"
    )
    assert any(d["variavel"] == "r_escada"
               for d in vd.descobrir_texto("em_pre.py", pre)), \
        "pre-fix G38 deveria ser orfao"
    # O fix do edificio limpa: stair -> _descer_escada -> desc -> pilar.
    ed = vd.descobrir_no_arquivo(GALPAO / "edificio_multipavimento.py")
    assert not any(d["variavel"] in ("r_escada", "stair") for d in ed), \
        "edificio reabriu o G38 em silencio: %r" % (ed,)
    # G42 curou a casa pelo mesmo caminho: o irmao do G38 que a descoberta
    # achou sem ninguem declarar agora desce aos pilares.
    casa = vd.descobrir_no_arquivo(GALPAO / "estrutura_casa.py")
    assert not any(d["variavel"] in ("r_escada", "stair") for d in casa), \
        "casa reabriu o G42 em silencio: %r" % (casa,)


def test_descoberta_atual_pina_baseline():
    # O que a descoberta acha HOJE (ordem estavel). Se um orfao novo aparecer,
    # este teste fica vermelho: ou vira verificacao, ou vira ilha declarada
    # para o proximo fix (molde G6->G7). Se um orfao sumir, a baseline tem que
    # diminuir junto - nunca em silencio.
    # G42: a casa saiu da baseline (r_escada curado) - baseline zerada.
    # G48: a lente ampliada (rodar()+calculos) declara 3 ilhas - ver triagem
    # e motivos em test_varredura_descoberta_g48.py; a fonte unica da
    # baseline e ILHAS_DECLARADAS_G48 de la (aqui, literal + ponteiro).
    assert vd.chaves_varridas() == [
        ("cargas_nbr6120.py", "multiplicadores_pavimentos", "area"),
        ("galpao_portico.py", "configurar", "W_WALL_COL"),
        ("galpao_portico.py", "reset", "W_WALL_COL"),
    ], "baseline G40/G48 mudou: %r" % (vd.chaves_varridas(),)


def test_permitidos_ainda_validos():
    # Filtro de nome morto NA LENTE AMPLIADA (G48): se o orquestrador for
    # renomeado ou a variavel sair do rodar() E dos calculos alcancaveis,
    # o allowlist morre em voz alta em vez de virar salvo-conduto vazio.
    for arq, var in vd.PERMITIDOS_TERMINAIS:
        assert vd.permitido_ainda_valido(arq, var), \
            "permitido %s/%s sem variavel no rodar() nem nos calculos: " \
            "virou salvo-conduto vazio" % (arq, var)


def test_tipologias_varridas_existem():
    for tipologia, arquivos in vd.TIPOLOGIAS.items():
        assert arquivos, "tipologia %s sem orquestrador" % tipologia
        for arq in arquivos:
            assert (GALPAO / arq).is_file(), \
                "orquestrador %s da tipologia %s sumiu" % (arq, tipologia)
