# ============================================================================
# test_varredura_descoberta_g48.py - G48: A LENTE ALCANCA OS MODULOS CHAMADOS.
# O G43 provou que o vocabulario morde, mas so no rodar(): hidraulica
# residencial (12 atribuicoes, 0 candidatos) e incendio (22 e 1) calculam um
# nivel abaixo, contra 45 e 8 no eletrico. A descoberta agora varre o fecho
# rodar()->calculos (mesmo arquivo ou modulo irmao via import), transitivo
# com TETO (profundidade 2), tratando o retorno de cada funcao como
# fronteira e a conferencia inline com veredito como verificacao.
#   - test_lente_alcanca_modulo_chamado: o vermelho mora no CALCULO, nao no
#     orquestrador (G21: um zero so vale depois do vermelho injetado).
#   - test_retorno_e_fronteira: valor que alcanca o return atravessou para
#     o chamador (folhas como carga_iluminacao_va/diametro_agua nao sao orfas).
#   - test_veredito_inline_conferencia: `if x < LIM: violacoes.append/raise`
#     confere (idioma das verificadoras); `if x is not None: pass` nao.
#   - test_fronteira_de_estado: global publicado e consumido por leitor
#     alcancavel que verifica/retorna esta verificado; publicado e nunca
#     lido continua orfao (a fronteira nao e salvo-conduto).
#   - test_teto_transitivo: alem da profundidade 2 a lente declara que nao
#     ve (nao finge que viu).
#   - test_baseline_g48_pina: o que a lente AMPLIADA acha HOJE. Triagem:
#       "vira verificacao" (8, sem tocar producao e sem allowlist):
#         hidraulica_residencial._agua_fria/_esgoto/_pluvial, arquitetura
#         _geometria_do_ambiente/carga_iluminacao_va (retorno como fronteira);
#         extintores.capacidades, armazenamento.area_operacao/
#         area_porta_paletes/vazao_intraprateleira/area_por_chuveiro,
#         hidraulica_predial.q_normal/q_maxima, fator_potencia.fp
#         (veredito-inline); galpao_portico N_VAOS/Q_ROOF (leitor de estado:
#         analyse() agrega em results e retorna).
#       "vira ilha declarada" (3, visiveis aqui, NUNCA em PERMITIDOS):
#         (cargas_nbr6120, multiplicadores_pavimentos, area): chave de
#           agrupamento por (uso, area) com influencia em alpha via CONTROLE
#           (comparacao chave_grupo != grupo_ref), sem fluxo de dados ao
#           output e sem validacao de area ausente/negativa. PROXIMO GOAL
#           candidato: validar area ou provar conservadorismo do grupo-None.
#         (galpao_portico, configurar/reset, W_WALL_COL): publicado em estado
#           global e consumido em case_G via mutacao de fr por callback
#           (_run(case_G)) - referencia-como-callback e mutacao via parametro
#           estao FORA do alcance declarado. PROXIMO GOAL candidato: fluxo de
#           estado global/mutacao (provavelmente vale mais que os dois).
#   - test_permitidos_nao_inflados: a armadilha do G48 era inflar
#     PERMITIDOS_TERMINAIS ate o relatorio zerar - a lista continua com as
#     mesmas 5 entradas do G40, todas vivas na lente ampliada.
# ============================================================================
"""Guarda G48: prova que a descoberta enxerga os modulos chamados."""

import os
import pathlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GALPAO = pathlib.Path(os.path.dirname(HERE))
if str(GALPAO) not in sys.path:
    sys.path.insert(0, str(GALPAO))

import varredura_descoberta as vd

# Baseline G48 pinada: toda mudanca (orfao novo OU ilha curada) deixa este
# teste vermelho de proposito. Editar so com triagem escrita acima.
ILHAS_DECLARADAS_G48 = [
    ("cargas_nbr6120.py", "multiplicadores_pavimentos", "area"),
    ("galpao_portico.py", "configurar", "W_WALL_COL"),
    ("galpao_portico.py", "reset", "W_WALL_COL"),
]


def _por_funcao(orfaos):
    return {(d["funcao"], d["variavel"]) for d in orfaos}


def test_lente_alcanca_modulo_chamado():
    # Vermelho: orfao calculado num modulo chamado, invisivel ao G43.
    pre = (
        "def _dimensiona_teste(spec):\n"
        "    Q_fantasma = 2.5\n"
        "    return True\n"
        "def rodar(spec):\n"
        "    ok = _dimensiona_teste(spec)\n"
        "    return ok\n"
    )
    achados = _por_funcao(vd.descobrir_texto("pre_g48.py", pre))
    assert ("_dimensiona_teste", "Q_fantasma") in achados, \
        "orfao no modulo chamado deveria ser achado: %r" % (achados,)
    # Verde A: o calculo verifica DENTRO do modulo chamado.
    fix_dentro = (
        "def _dimensiona_teste(spec):\n"
        "    Q_fantasma = 2.5\n"
        "    dn = diametro_agua(Q_fantasma)\n"
        "    return dn\n"
        "def rodar(spec):\n"
        "    return _dimensiona_teste(spec)\n"
    )
    assert vd.descobrir_texto("fix_g48a.py", fix_dentro) == [], \
        "verificacao dentro do calculo deveria limpar: %r" % (
            vd.descobrir_texto("fix_g48a.py", fix_dentro),)
    # Verde B: o calculo RETORNA e o orquestrador verifica (fronteira).
    fix_retorno = (
        "def _calcula_teste(spec):\n"
        "    Q_fantasma = 2.5\n"
        "    return Q_fantasma\n"
        "def rodar(spec):\n"
        "    q = _calcula_teste(spec)\n"
        "    dn = diametro_agua(q)\n"
        "    return dn\n"
    )
    assert vd.descobrir_texto("fix_g48b.py", fix_retorno) == [], \
        "retorno + verificacao no chamador deveria limpar: %r" % (
            vd.descobrir_texto("fix_g48b.py", fix_retorno),)


def test_retorno_e_fronteira():
    # Folha que retorna nao e orfa: `area` chega ao return.
    folha = (
        "def carga_teste(area_m2):\n"
        "    area = float(area_m2)\n"
        "    return area\n"
        "def rodar(spec):\n"
        "    return carga_teste(spec)\n"
    )
    assert vd.descobrir_texto("folha_g48.py", folha) == [], \
        "folha que retorna deveria estar limpa: %r" % (
            vd.descobrir_texto("folha_g48.py", folha),)
    # E no repo real os calculos de um nivel abaixo seguem fechados.
    for arq, funcs in (
            ("hidraulica_residencial.py",
             ("_agua_fria", "_esgoto", "_pluvial")),
            ("arquitetura_residencial.py",
             ("_geometria_do_ambiente", "carga_iluminacao_va",
              "carga_tomadas_va", "criterio_tomadas"))):
        reais = vd.descobrir_no_arquivo(GALPAO / arq)
        achados = _por_funcao(reais)
        for func in funcs:
            assert not any(f == func for f, _v in achados), \
                "%s/%s reabriu em silencio: %r" % (arq, func, reais)


def test_veredito_inline_conferencia():
    # Verde: candidata testada com veredito no ramo esta conferida.
    confere = (
        "def verifica_teste(caso):\n"
        "    q_teste = _numero(caso)\n"
        "    if q_teste is not None and q_teste < 0.0:\n"
        "        violacoes.append(\"negativa\")\n"
        "    return not violacoes\n"
        "def rodar(spec):\n"
        "    return verifica_teste(spec)\n"
    )
    assert vd.descobrir_texto("veredito_g48.py", confere) == [], \
        "conferencia inline com veredito deveria limpar: %r" % (
            vd.descobrir_texto("veredito_g48.py", confere),)
    # Vermelho: null-check sem veredito nao confere nada.
    finge = (
        "def verifica_falso(caso):\n"
        "    Q_limbo = 1.5\n"
        "    if Q_limbo is not None:\n"
        "        pass\n"
        "    return True\n"
        "def rodar(spec):\n"
        "    return verifica_falso(spec)\n"
    )
    achados = _por_funcao(vd.descobrir_texto("finge_g48.py", finge))
    assert ("verifica_falso", "Q_limbo") in achados, \
        "check sem veredito deveria continuar orfao: %r" % (achados,)
    # E no repo real o idioma das verificadoras segue fechado.
    trios = (
        ("galpao_seguranca_incendio.py", "verifica_extintores_nbr12693",
         "capacidades"),
        ("galpao_seguranca_incendio.py", "verifica_armazenamento_nbr16981",
         "area_operacao"),
        ("galpao_hidraulica.py", "verifica_agua_quente_seguranca", "q_normal"),
        ("galpao_eletrico.py", "corrige_fator_potencia", "fp"),
    )
    for arq, _func, var in trios:
        reais = vd.descobrir_no_arquivo(GALPAO / arq)
        assert not any(d["variavel"] == var for d in reais), \
            "%s/%s reabriu em silencio: %r" % (arq, var, reais)


def test_fronteira_de_estado():
    # Verde: global publicado e consumido por leitor que verifica/retorna.
    publica = (
        "def configurar(valor):\n"
        "    global W_GUARDADO\n"
        "    W_GUARDADO = valor\n"
        "def analisa():\n"
        "    total = W_GUARDADO * 2.0\n"
        "    return dimensiona_viga(total)\n"
        "def rodar(spec):\n"
        "    configurar(spec)\n"
        "    return analisa()\n"
    )
    assert vd.descobrir_texto("estado_g48.py", publica) == [], \
        "estado consumido por leitor deveria limpar: %r" % (
            vd.descobrir_texto("estado_g48.py", publica),)
    # Vermelho: publicado e nunca lido continua orfao (sem salvo-conduto).
    larga = (
        "def configurar(valor):\n"
        "    global W_FANTASMA\n"
        "    W_FANTASMA = valor\n"
        "def rodar(spec):\n"
        "    configurar(spec)\n"
        "    return True\n"
    )
    achados = _por_funcao(vd.descobrir_texto("larga_g48.py", larga))
    assert ("configurar", "W_FANTASMA") in achados, \
        "estado nunca lido deveria continuar orfao: %r" % (achados,)
    # E no repo real N_VAOS/Q_ROOF seguem verificados via analyse().
    reais = vd.descobrir_no_arquivo(GALPAO / "rodar_galpao.py")
    assert not any(d["variavel"] in ("N_VAOS", "Q_ROOF") for d in reais), \
        "fronteira de estado reabriu em silencio: %r" % (reais,)


def test_teto_transitivo():
    # nivel_c esta a 3 saltos: fora do teto, a lente declara que nao ve.
    cadeia = (
        "def nivel_c(spec):\n"
        "    V_abismo = 1.0\n"
        "    return True\n"
        "def nivel_b(spec):\n"
        "    V_poco = 2.0\n"
        "    nivel_c(spec)\n"
        "    return True\n"
        "def nivel_a(spec):\n"
        "    return nivel_b(spec)\n"
        "def rodar(spec):\n"
        "    return nivel_a(spec)\n"
    )
    achados = _por_funcao(vd.descobrir_texto("teto_g48.py", cadeia))
    assert ("nivel_b", "V_poco") in achados, \
        "profundidade 2 deveria ser vista: %r" % (achados,)
    assert ("nivel_c", "V_abismo") not in achados, \
        "profundidade 3 esta fora do teto declarado: %r" % (achados,)


def test_baseline_g48_pina():
    # O que a lente AMPLIADA acha HOJE nas tipologias (ordem estavel).
    # Orfao novo -> vermelho: vira verificacao ou vira ilha declarada aqui
    # (molde G6->G7). Ilha curada -> a baseline diminui junto, nunca em
    # silencio. Jamais em PERMITIDOS_TERMINAIS (ver test_permitidos_...).
    assert vd.chaves_varridas() == ILHAS_DECLARADAS_G48, \
        "baseline G48 mudou: %r" % (vd.chaves_varridas(),)


def test_permitidos_nao_inflados():
    # A armadilha do G48: ampliar o alcance e inflar o allowlist ate zerar.
    # A lista continua exatamente a do G40 - cada ilha nova mora na
    # baseline pinada acima, a vista, nunca aqui.
    assert sorted(vd.PERMITIDOS_TERMINAIS) == sorted({
        ("estrutura_casa.py", "r_vigas"),
        ("estrutura_casa.py", "N_base"),
        ("edificio_multipavimento.py", "r_vigas"),
        ("edificio_multipavimento.py", "N_desc_total"),
        ("estrutura_casa.py", "N_desc_total"),
    }), "allowlist mudou em silencio: %r" % (vd.PERMITIDOS_TERMINAIS,)
    for arq, var in vd.PERMITIDOS_TERMINAIS:
        assert vd.permitido_ainda_valido(arq, var), \
            "permitido %s/%s virou nome morto na lente ampliada" % (arq, var)
